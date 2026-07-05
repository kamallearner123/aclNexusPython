from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from core.models import AuditLog
from .models import Task
from .forms import TaskForm

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
            'completed': tasks.filter(status='COMPLETED'),
        }
        return render(request, 'tasks/kanban.html', context)
    else:
        from projects.models import Project
        projects = Project.objects.all()
        return render(request, 'tasks/kanban_projects.html', {'projects': projects})

@login_required
def task_create(request):
    """
    View for creating a new task.
    """
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.reporter = request.user
            task.save()
            return redirect('tasks_kanban')
    else:
        form = TaskForm()
    
    return render(request, 'tasks/form.html', {'form': form})

@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk)
    activities = AuditLog.objects.filter(
        model_name='Task', 
        object_id=str(task.pk)
    ).order_by('-timestamp')
    
    return render(request, 'tasks/detail.html', {
        'task': task,
        'activities': activities
    })

@login_required
def task_update(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            updated_task = form.save(commit=False)
            updated_task.updated_by = request.user
            if form.cleaned_data.get('edit_comment'):
                updated_task._edit_comment = form.cleaned_data.get('edit_comment')
            updated_task.save()
            return redirect('task_detail', pk=task.pk)
    else:
        form = TaskForm(instance=task)
    return render(request, 'tasks/form.html', {'form': form, 'is_update': True})

@login_required
def update_task_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            task_id = data.get('task_id')
            new_status = data.get('status')
            
            task = get_object_or_404(Task, pk=task_id)
            task.status = new_status
            task.updated_by = request.user
            task.save()
            
            return JsonResponse({'success': True})
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
