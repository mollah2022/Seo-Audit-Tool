from django.contrib import admin

from .models import Audit, CheckResult


class CheckResultInline(admin.TabularInline):
    model = CheckResult
    extra = 0
    readonly_fields = ("category", "name", "status", "detail")
    can_delete = False


@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    list_display = ("domain", "url", "status", "overall_score", "score_band", "created_at")
    list_filter = ("status", "score_band")
    search_fields = ("url", "domain")
    readonly_fields = ("created_at", "updated_at")
    inlines = [CheckResultInline]


@admin.register(CheckResult)
class CheckResultAdmin(admin.ModelAdmin):
    list_display = ("audit", "category", "name", "status")
    list_filter = ("category", "status")
