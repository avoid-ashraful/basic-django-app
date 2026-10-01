import factory
from factory import fuzzy

from common.models import Sample


class SampleFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("paragraph")
    status = fuzzy.FuzzyChoice(Sample.Status.values)
    quantity = fuzzy.FuzzyInteger(0, 100)
    is_active = True

    class Meta:
        model = "common.Sample"
