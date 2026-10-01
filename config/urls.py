from django.contrib import admin
from django.urls import include, path, re_path

v1_urls = [
    path("", include("users.urls")),
    path("common/", include("common.urls")),
    path("temp/", include("temp.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include([re_path("(?P<version>(v1))/", include(v1_urls))])),
]
