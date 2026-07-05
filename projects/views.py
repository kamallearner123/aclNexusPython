from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from core.models import AuditLog
from .models import Project
from .forms import ProjectForm

@login_required
def project_list(request):
    """
    View displaying all projects.
    """
    projects = Project.objects.all().order_by('-created_at')
    return render(request, 'projects/list.html', {'projects': projects})

@login_required
def project_create(request):
    """
    View for creating a new project.
    """
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            return redirect('project_list')
    else:
        form = ProjectForm()
    
    return render(request, 'projects/form.html', {'form': form})

@login_required
def project_detail(request, pk):
    """
    Detailed view of a project, including activity history.
    """
    project = get_object_or_404(Project, pk=pk)
    # Fetch audit logs where object_id matches project.pk
    activities = AuditLog.objects.filter(
        model_name='Project', 
        object_id=str(project.pk)
    ).order_by('-timestamp')
    
    return render(request, 'projects/detail.html', {
        'project': project,
        'activities': activities,
        'tasks': project.tasks.all().order_by('-created_at'),
        'issues': project.issues.all().order_by('-created_at'),
    })

@login_required
def project_update(request, pk):
    """
    Update an existing project.
    """
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            updated_project = form.save(commit=False)
            updated_project.updated_by = request.user
            updated_project.save()
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)
        
    return render(request, 'projects/form.html', {'form': form, 'is_update': True})

from django.contrib.auth.decorators import user_passes_test
def is_admin(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_admin)
def project_delete(request, pk):
    if request.method == 'POST':
        project = get_object_or_404(Project, pk=pk)
        project.delete()
    return redirect('system_admin_dashboard')

@login_required
def automotive_process_board(request, pk):
    project = get_object_or_404(Project, pk=pk)
    
    if project.project_type != 'AUTOMOTIVE':
        return redirect('project_detail', pk=pk)
        
    milestones = project.milestones.all().order_by('id')
    
    aspice_milestones = milestones.filter(name__startswith='[ASPICE]')
    cyber_milestones = milestones.filter(name__startswith='[Cybersecurity]')
    autosar_milestones = milestones.filter(name__startswith='[AUTOSAR]')
    pm_milestones = milestones.filter(name__startswith='[Project Management]')
    
    context = {
        'project': project,
        'aspice_milestones': aspice_milestones,
        'cyber_milestones': cyber_milestones,
        'autosar_milestones': autosar_milestones,
        'pm_milestones': pm_milestones,
    }
    
    return render(request, 'projects/automotive_board.html', context)
