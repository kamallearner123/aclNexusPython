from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from core.models import AuditLog
from .models import Project, Requirement
from .forms import ProjectForm, RequirementForm
from tasks.models import Task

from django.db.models import Q

@login_required
def project_list(request):
    """
    View displaying all projects depending on role.
    """
    user = request.user
    if user.is_superuser or user.is_staff:
        projects = Project.objects.all()
    elif user.roles.filter(name='Project Manager').exists():
        projects = Project.objects.filter(
            Q(owner=user) | 
            Q(created_by=user) | 
            Q(teams__members__user=user)
        ).distinct()
    elif user.roles.filter(name='Architect').exists():
        projects = Project.objects.filter(
            Q(tasks__assignee=user) | 
            Q(teams__members__user=user)
        ).distinct()
    else:
        projects = Project.objects.filter(
            Q(tasks__assignee=user) |
            Q(teams__members__user=user)
        ).distinct()
        
    projects = projects.order_by('-created_at')
    return render(request, 'projects/list.html', {'projects': projects})

from django.contrib.auth.decorators import user_passes_test

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
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
            form.save_m2m()
            
            # Handle attachments
            from core.models import Attachment
            from django.contrib.contenttypes.models import ContentType
            content_type = ContentType.objects.get_for_model(Project)
            for f in request.FILES.getlist('attachments'):
                Attachment.objects.create(
                    file=f,
                    filename=f.name,
                    uploaded_by=request.user,
                    content_type=content_type,
                    object_id=project.pk
                )
                
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
        'requirements': project.requirements.all().order_by('-created_at'),
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
            form.save_m2m()
            
            # Handle attachments
            from core.models import Attachment
            from django.contrib.contenttypes.models import ContentType
            content_type = ContentType.objects.get_for_model(Project)
            for f in request.FILES.getlist('attachments'):
                Attachment.objects.create(
                    file=f,
                    filename=f.name,
                    uploaded_by=request.user,
                    content_type=content_type,
                    object_id=updated_project.pk
                )
                
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
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        # Log the deletion and reason
        from core.models import AuditLog
        AuditLog.objects.create(
            action='DELETE',
            model_name='Project',
            object_id=str(project.pk),
            user=request.user,
            changes={'reason': reason, 'project_name': project.name, 'project_code': project.code}
        )
        
        project.delete()
        return redirect('project_list')
        
    return render(request, 'projects/confirm_delete.html', {'project': project})

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

@login_required
def requirement_create(request, project_id):
    """
    Allow Client or Admin to add requirements for a project.
    """
    project = get_object_or_404(Project, pk=project_id)
    # Basic permission check: allow admins, owners, or clients assigned to the team
    # (assuming Client role is represented either by user.roles or just anyone in the team for now)
    
    if request.method == 'POST':
        form = RequirementForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.project = project
            req.created_by = request.user
            req.save()
            return redirect('project_detail', pk=project.pk)
    else:
        form = RequirementForm()
        
    return render(request, 'projects/requirement_form.html', {'form': form, 'project': project})

@login_required
def requirement_update(request, pk):
    req = get_object_or_404(Requirement, pk=pk)
    project = req.project
    
    if request.method == 'POST':
        form = RequirementForm(request.POST, instance=req)
        if form.is_valid():
            updated_req = form.save(commit=False)
            updated_req.updated_by = request.user
            updated_req.save()
            return redirect('project_detail', pk=project.pk)
    else:
        form = RequirementForm(instance=req)
        
    return render(request, 'projects/requirement_form.html', {'form': form, 'project': project, 'is_update': True})

@login_required
def requirement_convert_to_task(request, pk):
    """
    Architect/Manager can convert requirement to tasks/stories.
    """
    req = get_object_or_404(Requirement, pk=pk)
    project = req.project
    
    user_roles = request.user.roles.values_list('name', flat=True)
    is_architect_manager = request.user.is_superuser or request.user.is_staff or 'Architect' in user_roles or 'Project Manager' in user_roles
    
    if not is_architect_manager:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Only Architects or Managers can convert requirements to tasks.")

    if request.method == 'POST':
        titles = request.POST.getlist('task_title')
        descriptions = request.POST.getlist('task_description')
        priorities = request.POST.getlist('task_priority')
        
        date_str = req.created_at.strftime('%m%y')
        
        for idx, title in enumerate(titles):
            if title.strip():
                # Count current tasks to generate ID
                task_count = Task.objects.filter(project=project).count() + 1
                task_id = f"REQ{project.pk}{date_str}_Task_{task_count}"
                
                desc = descriptions[idx] if idx < len(descriptions) else ''
                priority = priorities[idx] if idx < len(priorities) else 'MEDIUM'
                
                Task.objects.create(
                    task_id=task_id,
                    project=project,
                    requirement=req,
                    title=title,
                    description=desc,
                    priority=priority,
                    status='BACKLOG',
                    created_by=request.user,
                    updated_by=request.user
                )
        
        req.status = 'CONVERTED'
        req.save()
        return redirect('project_detail', pk=project.pk)
        
    return render(request, 'projects/requirement_convert.html', {'requirement': req, 'project': project})

