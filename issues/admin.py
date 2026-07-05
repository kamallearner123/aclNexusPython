from django.contrib import admin
from .models import Issue

@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ('title', 'issue_type', 'severity', 'status', 'project')
    list_filter = ('issue_type', 'severity', 'status')
    search_fields = ('title',)
