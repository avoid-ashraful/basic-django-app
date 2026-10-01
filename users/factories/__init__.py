import factory

DEFAULT_PASSWORD = "123456"


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", DEFAULT_PASSWORD)
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")

    class Meta:
        model = "users.User"
        django_get_or_create = ("username",)
        skip_postgeneration_save = True

    @factory.post_generation
    def save_password(self, create, extracted, **kwargs):
        """Persist the password hashed by the set_password post-generation call."""
        if create:
            self.save(update_fields=["password"])
