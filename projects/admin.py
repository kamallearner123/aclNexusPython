from django.contrib import admin
from .models import Project, Milestone, Sprint

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'project_type', 'status', 'priority', 'owner')
    list_filter = ('status', 'project_type', 'priority')
    search_fields = ('code', 'name', 'client')

@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ('project', 'name', 'target_date', 'is_completed')
    list_filter = ('project', 'is_completed')

@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ('project', 'name', 'start_date', 'end_date', 'capacity')
    list_filter = ('project',)
