from django.contrib import admin

from quality.models import LotAnalysis


@admin.register(LotAnalysis)
class LotAnalysisAdmin(admin.ModelAdmin):
    list_display = ("created_at", "lot_code", "brand", "package_format", "decision", "final_decision", "user", "final_by")
    list_filter = ("decision", "final_decision", "brand")
    search_fields = ("lot_code",)
    readonly_fields = ("created_at", "user", "lot_code", "brand", "package_format", "measurements", "result", "decision",
                       "final_decision", "final_comment", "final_by", "final_at")
