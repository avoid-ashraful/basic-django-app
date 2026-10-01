"""Product endpoints, written as a tour of Django transaction patterns.

Each numbered feature below is imaginary and exists to show one technique:

1. retrieve        -> F() expression: an atomic update with no transaction at all
2. perform_create  -> @transaction.atomic decorator: all-or-nothing writes
                      + transaction.on_commit: side effects only after COMMIT
3. update          -> transaction.set_rollback: a "dry run" that rolls back
4. perform_update  -> optimistic locking: a version check instead of a lock
5. purchase        -> select_for_update: pessimistic row locking
                      + atomic(durable=True): must be the outermost transaction
6. import_products -> nested atomic (savepoints): partial success in one batch

Not shown in code, but worth knowing for interviews:
- ATOMIC_REQUESTS = True in DATABASES wraps every view in a transaction; opt a
  view out with @transaction.non_atomic_requests.
- Isolation level (READ COMMITTED, REPEATABLE READ, SERIALIZABLE) is a database
  setting, e.g. DATABASES["default"]["OPTIONS"]["isolation_level"] on Postgres.
- SQLite ignores select_for_update (it locks the whole database on write); the
  row lock only really happens on Postgres, MySQL or Oracle.
"""

import logging
from functools import partial
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from temp.api.serializers import ProductSerializer
from temp.models import Product, ProductActivity

logger = logging.getLogger(__name__)


class Conflict(APIException):
    """409 response for an update based on a stale version of the record."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "The product was modified by someone else. Reload and retry."
    default_code = "conflict"


def notify_warehouse(product_id, event):
    """Pretend to call an external service; it must only run after COMMIT."""
    logger.info("warehouse notified: product=%s event=%s", product_id, event)


class ProductViewSet(viewsets.ModelViewSet):
    """CRUD endpoints for Product model."""

    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_queryset(self):
        """Prefetch tags to avoid one query per product."""
        return super().get_queryset().prefetch_related("tags")

    def _validate_tags(self, tags):
        """Reject requests that attach more than two tags."""
        if len(tags) > 2:
            raise ValidationError("Too many tags")

    # 1. F() expression: no transaction needed --------------------------------
    # F("view_count") + 1 runs as one UPDATE ... SET view_count = view_count + 1
    # inside the database. Reading the value in Python, adding 1 and saving would
    # lose increments when two requests race (both read 5, both write 6).
    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Count a view, then return the product."""
        Product.objects.filter(pk=kwargs["pk"]).update(view_count=F("view_count") + 1)
        return super().retrieve(request, *args, **kwargs)

    # 2. @transaction.atomic + on_commit -------------------------------------
    # serializer.save() runs two statements (INSERT product, INSERT tag links) and
    # we add a third (INSERT activity). The decorator makes them all-or-nothing:
    # if the activity insert fails, the product is rolled back too.
    #
    # The warehouse call is an external side effect, so it is deferred with
    # on_commit. If it ran inline and the transaction then rolled back, the
    # warehouse would hear about a product that does not exist.
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Validate the tag limit, then create the product."""
        self._validate_tags(request.data.get("tags", []))
        return super().create(request, *args, **kwargs)

    @transaction.atomic
    def perform_create(self, serializer):
        """Save the product, its tags and the activity log as one unit."""
        product = serializer.save()
        ProductActivity.objects.create(
            product=product, action=ProductActivity.Action.CREATED
        )
        # Pass a callable. partial() binds the value now; a lambda in a loop
        # would late-bind and see only the last value.
        transaction.on_commit(partial(notify_warehouse, product.pk, "created"))

    # 3. transaction.set_rollback: dry run -----------------------------------
    # Everything runs for real (validation, saves, the activity log), so the
    # response shows exactly what would happen. set_rollback(True) then marks the
    # block to ROLL BACK instead of committing when it exits, which also discards
    # the on_commit callbacks registered inside it.
    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Update the product; with ?dry_run=true, preview the result and roll back."""
        with transaction.atomic():
            response = super().update(request, *args, **kwargs)
            if request.query_params.get("dry_run") == "true":
                transaction.set_rollback(True)
        return response

    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Validate the tag limit, then partially update the product."""
        self._validate_tags(request.data.get("tags", []))
        return super().partial_update(request, *args, **kwargs)

    # 4. Optimistic locking ---------------------------------------------------
    # The client sends back the "version" it last read. The conditional UPDATE is
    # a compare-and-swap: it only matches the row if nobody bumped the version in
    # the meantime, so zero rows updated means a lost-update conflict. No lock is
    # held while the user edits, which suits low-contention data. This runs inside
    # update()'s atomic block, so a failed save also undoes the version bump.
    def perform_update(self, serializer):
        """Save only if the client edited the latest version of the product."""
        product = serializer.instance
        expected = self.request.data.get("version")
        if expected is not None:
            try:
                expected = int(expected)
            except TypeError, ValueError:
                raise ValidationError({"version": "Must be an integer."}) from None
            bumped = Product.objects.filter(pk=product.pk, version=expected).update(
                version=F("version") + 1
            )
            if not bumped:
                raise Conflict()
            # The instance still holds the old version; save the new one explicitly
            # so serializer.save() does not write the stale value back.
            product = serializer.save(version=expected + 1)
        else:
            product = serializer.save()

        ProductActivity.objects.create(
            product=product,
            action=ProductActivity.Action.UPDATED,
            details={"fields": sorted(serializer.validated_data)},
        )
        transaction.on_commit(partial(notify_warehouse, product.pk, "updated"))

    # 5. select_for_update + durable -----------------------------------------
    # Without a lock, two buyers could both read stock=1, both pass the check and
    # both decrement. select_for_update() issues SELECT ... FOR UPDATE, so the
    # second buyer waits until the first commits, then reads the new stock. It
    # must run inside a transaction (the lock is released at COMMIT); outside one,
    # Django raises TransactionManagementError.
    #
    # durable=True asserts this is the outermost atomic block. If this code is
    # ever called from inside another transaction, it fails loudly instead of
    # silently becoming a savepoint that an outer rollback could undo after the
    # customer was already told the purchase succeeded.
    @action(detail=True, methods=["post"])
    def purchase(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Buy `quantity` units under a row lock so stock never goes negative."""
        try:
            quantity = int(request.data.get("quantity", 1))
        except TypeError, ValueError:
            raise ValidationError({"quantity": "Must be an integer."}) from None
        if quantity < 1:
            raise ValidationError({"quantity": "Must be at least 1."})

        with transaction.atomic(durable=True):
            product = get_object_or_404(
                Product.objects.select_for_update(), pk=kwargs["pk"]
            )
            if product.stock < quantity:
                raise ValidationError(
                    {"quantity": f"Only {product.stock} left in stock."}
                )

            product.stock -= quantity
            product.save(update_fields=["stock", "modified"])
            ProductActivity.objects.create(
                product=product,
                action=ProductActivity.Action.PURCHASED,
                details={"quantity": quantity},
            )
            # robust=True logs an exception from the callback instead of raising
            # it, so a flaky notification cannot turn a committed purchase into a 500.
            transaction.on_commit(
                partial(notify_warehouse, product.pk, "purchased"), robust=True
            )

        return Response(self.get_serializer(product).data)

    # 6. Nested atomic blocks (savepoints) -----------------------------------
    # The outer atomic() opens a transaction; each inner atomic() opens a
    # SAVEPOINT. When a row violates the unique sku constraint, only its savepoint
    # is rolled back and the loop continues with the next row.
    #
    # The inner block is required. Catching IntegrityError directly inside the
    # outer block leaves the transaction broken, and the next query raises
    # TransactionManagementError. The manual equivalent of the inner block is:
    #
    #     sid = transaction.savepoint()
    #     try:
    #         ...
    #         transaction.savepoint_commit(sid)
    #     except IntegrityError:
    #         transaction.savepoint_rollback(sid)
    @action(detail=False, methods=["post"], url_path="import")
    def import_products(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Import many products, keeping the good rows and reporting the bad ones."""
        if not isinstance(request.data, list):
            raise ValidationError("Expected a list of products.")

        created, errors = [], []
        with transaction.atomic():
            for index, row in enumerate(request.data):
                try:
                    with transaction.atomic():
                        product = Product.objects.create(
                            name=row.get("name", ""),
                            description=row.get("description", ""),
                            sku=row.get("sku"),
                            stock=row.get("stock", 0),
                        )
                        ProductActivity.objects.create(
                            product=product,
                            action=ProductActivity.Action.IMPORTED,
                            details={"row": index},
                        )
                except IntegrityError:
                    errors.append({"row": index, "error": "Duplicate sku."})
                else:
                    created.append(product.pk)

        return Response({"created": created, "errors": errors})
