from rest_framework.routers import DefaultRouter

from temp.api.views import ProductViewSet

app_name = "temp"

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")

urlpatterns = router.urls
