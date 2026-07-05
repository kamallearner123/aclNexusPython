from django.contrib import admin
from .models import Risk

@admin.register(Risk)
class RiskAdmin(admin.ModelAdmin):
    list_display = ('risk_id', 'title', 'project', 'risk_level', 'risk_score', 'owner')
    list_filter = ('risk_level', 'probability', 'impact', 'project')
    search_fields = ('risk_id', 'title')
