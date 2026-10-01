from rest_framework.routers import DefaultRouter

from common.api.views import SampleViewSet

app_name = "common"

router = DefaultRouter()
router.register("samples", SampleViewSet, basename="sample")

urlpatterns = router.urls
