import factory


class TagFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("paragraph")

    class Meta:
        model = "temp.Tag"


class ProductFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("paragraph")

    class Meta:
        model = "temp.Product"

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for tag in extracted:
                self.tags.add(tag)
        else:
            self.tags.add(TagFactory(), TagFactory())
