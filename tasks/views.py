from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from core.models import AuditLog
from .models import Task
from .forms import TaskForm

@login_required
def my_tasks(request):
    """
    View to list all tasks assigned to the current user.
    """
    tasks = Task.objects.filter(assignee=request.user).order_by('due_date').select_related('project', 'requirement')
    return render(request, 'tasks/my_tasks.html', {'tasks': tasks})

@login_required
def kanban_board(request):
    """
    Kanban board view grouping tasks by status.
    """
    project_id = request.GET.get('project_id')
    
    if project_id:
        from projects.models import Project
        project = get_object_or_404(Project, pk=project_id)
        tasks = Task.objects.filter(project=project)
        context = {
            'project': project,
            'backlog': tasks.filter(status='BACKLOG'),
            'planned': tasks.filter(status='PLANNED'),
            'in_progress': tasks.filter(status='IN_PROGRESS'),
            'in_review': tasks.filter(status='IN_REVIEW'),
            'testing': tasks.filter(status='TESTING'),
            'blocked': tasks.filter(status='BLOCKED'),
            'pending_approval': tasks.filter(status='PENDING_APPROVAL'),
            'completed': tasks.filter(status='CLOSED'),
            'can_create_task': can_create_task(request.user),
        }
        return render(request, 'tasks/kanban.html', context)
    else:
        from projects.models import Project
        projects = Project.objects.all()
        return render(request, 'tasks/kanban_projects.html', {'projects': projects})

from django.contrib.auth.decorators import user_passes_test

def can_create_task(user):
    if user.is_staff or user.is_superuser:
        return True
    roles = user.roles.values_list('name', flat=True)
    if 'Project Manager' in roles or 'Architect' in roles or 'Manager' in roles:
        return True
    if user.led_teams.exists():
        return True
    return False

@login_required
@user_passes_test(can_create_task)
def task_create(request):
    """
    View for creating a new task.
    """
    if request.method == 'POST':
        initial_data = {}
        if request.GET.get('project_id'):
            initial_data['project'] = request.GET.get('project_id')
        form = TaskForm(request.POST, request.FILES, initial=initial_data)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.reporter = request.user
            task.save()
            
            # Handle attachments
            from core.models import Attachment
            from django.contrib.contenttypes.models import ContentType
            content_type = ContentType.objects.get_for_model(Task)
            
            for f in request.FILES.getlist('attachments'):
                Attachment.objects.create(
                    file=f,
                    filename=f.name,
                    uploaded_by=request.user,
                    content_type=content_type,
                    object_id=task.pk
                )
                
            if task.project:
                return redirect(f"/tasks/kanban/?project_id={task.project.pk}")
            return redirect('tasks_kanban')
    else:
        initial_data = {}
        if request.GET.get('project_id'):
            initial_data['project'] = request.GET.get('project_id')
        form = TaskForm(initial=initial_data)
    
    return render(request, 'tasks/form.html', {'form': form})

@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk)
    
    if request.method == 'POST':
        content = request.POST.get('comment_content')
        if content and content.strip() and content != '<p><br></p>':
            from .models import TaskComment
            TaskComment.objects.create(task=task, author=request.user, content=content)
            return redirect('task_detail', pk=pk)
            
    activities = AuditLog.objects.filter(
        model_name='Task', 
        object_id=str(task.pk),
        timestamp__gte=task.created_at
    ).order_by('-timestamp')
    
    from datetime import date
    return render(request, 'tasks/detail.html', {
        'task': task,
        'activities': activities,
        'today': date.today(),
    })

@login_required
def task_deactivate(request, pk):
    if request.method == 'POST':
        task = get_object_or_404(Task, pk=pk)
        task.status = 'DEACTIVATED'
        task.updated_by = request.user
        task.save()
    return redirect('task_detail', pk=pk)

@login_required
def task_update(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == 'POST':
        form = TaskForm(request.POST, request.FILES, instance=task)
        if form.is_valid():
            updated_task = form.save(commit=False)
            updated_task.updated_by = request.user
            if form.cleaned_data.get('edit_comment'):
                updated_task._edit_comment = form.cleaned_data.get('edit_comment')
            updated_task.save()
            
            # Handle attachments
            from core.models import Attachment
            from django.contrib.contenttypes.models import ContentType
            content_type = ContentType.objects.get_for_model(Task)
            
            for f in request.FILES.getlist('attachments'):
                Attachment.objects.create(
                    file=f,
                    filename=f.name,
                    uploaded_by=request.user,
                    content_type=content_type,
                    object_id=updated_task.pk
                )
                
            return redirect('task_detail', pk=task.pk)
    else:
        form = TaskForm(instance=task)
    return render(request, 'tasks/form.html', {'form': form, 'is_update': True})

@login_required
def update_task_status(request):
    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST
                
            task_id = data.get('task_id')
            new_status = data.get('status')
            
            user_roles = request.user.roles.values_list('name', flat=True)
            can_close = any(r in user_roles for r in ['Architect', 'Project Manager', 'Lead', 'Manager']) or request.user.is_superuser or request.user.is_staff
            
            if new_status == 'CLOSED' and not can_close:
                return JsonResponse({'success': False, 'error': 'Only Architects, Project Managers, or Team Leads can close tasks.'}, status=403)
                
            hours_spent = data.get('hours_spent', 0)
            
            task = get_object_or_404(Task, pk=task_id)
            task.status = new_status
            task.updated_by = request.user
            
            try:
                from decimal import Decimal
                if hours_spent:
                    task.hours_spent += Decimal(str(hours_spent))
            except (ValueError, TypeError, Exception):
                pass
                
            task.save()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
                return JsonResponse({
                    'success': True,
                    'new_status': task.status,
                    'new_status_display': task.get_status_display(),
                    'hours_spent': str(task.hours_spent)
                })
            return redirect('task_detail', pk=task.pk)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False}, status=405)

from django.contrib import messages

@login_required
def task_ai_action(request, pk):
    """
    Placeholder view for AI actions on tasks.
    """
    task = get_object_or_404(Task, pk=pk)
    action = request.GET.get('action')
    
    messages.success(request, f"AI Action '{action}' triggered for task {task.task_id}. (AI Integration Placeholder)")
    
    return redirect('task_detail', pk=task.pk)

@login_required
def user_calendar(request):
    """
    User Calendar View displaying assigned tasks using FullCalendar.
    """
    import json
    
    # Strictly query only tasks assigned to the current user by default
    user = request.user
    view_all = request.GET.get('view') == 'all'
    user_roles = user.roles.values_list('name', flat=True)
    can_view_all = user.is_superuser or user.is_staff or 'Project Manager' in user_roles
    
    if view_all and can_view_all:
        my_tasks = Task.objects.all().select_related('project')
    else:
        my_tasks = Task.objects.filter(assignee=user).select_related('project')
    
    events = []
    for task in my_tasks:
        if task.due_date:
            # Color coding based on status
            color = '#3b82f6' # Blue (default)
            if task.status == 'CLOSED':
                color = '#10b981' # Green
            elif task.status in ['BLOCKED']:
                color = '#ef4444' # Red
            elif task.status in ['IN_PROGRESS']:
                color = '#f59e0b' # Amber
                
            events.append({
                'title': f"[{task.task_id}] {task.title}",
                'start': task.due_date.isoformat(),
                'url': f"/tasks/{task.pk}/",
                'color': color,
                'allDay': True
            })
            
    context = {
        'events_json': json.dumps(events),
        'can_view_all': can_view_all,
        'view_all': view_all,
    }
    return render(request, 'tasks/calendar.html', context)
