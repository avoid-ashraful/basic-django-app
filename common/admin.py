from django.contrib import admin

from common.models import Sample


@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "status", "quantity", "is_active", "created")
    list_filter = ("status", "is_active")
    search_fields = ("name",)
