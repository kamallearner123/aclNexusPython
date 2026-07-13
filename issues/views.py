from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Issue
from .forms import IssueForm

from django.db.models import Q

@login_required
def issue_tracker(request):
    """
    Issue Tracker view displaying issues for user's projects.
    """
    user = request.user
    if user.is_superuser or user.is_staff:
        issues = Issue.objects.all().order_by('-created_at')
    else:
        q = Q(project__owner=user) | Q(project__tasks__assignee=user)
        if user.team:
            q |= Q(project__team=user.team)
        issues = Issue.objects.filter(q).distinct().order_by('-created_at')
        
    return render(request, 'issues/list.html', {'issues': issues})

@login_required
def issue_create(request):
    """
    View for creating a new issue.
    """
    if request.method == 'POST':
        form = IssueForm(request.POST)
        if form.is_valid():
            issue = form.save(commit=False)
            issue.created_by = request.user
            issue.save()
            return redirect('issue_tracker')
    else:
        form = IssueForm()
    
    return render(request, 'issues/form.html', {'form': form})

from django.shortcuts import get_object_or_404
from core.models import AuditLog

@login_required
def issue_detail(request, pk):
    issue = get_object_or_404(Issue, pk=pk)
    
    if request.method == 'POST':
        content = request.POST.get('comment_content')
        if content and content.strip() and content != '<p><br></p>':
            from .models import IssueComment
            IssueComment.objects.create(issue=issue, author=request.user, content=content)
            return redirect('issue_detail', pk=pk)
            
    activities = AuditLog.objects.filter(
        model_name='Issue', 
        object_id=str(issue.pk)
    ).order_by('-timestamp')
    
    return render(request, 'issues/detail.html', {
        'issue': issue,
        'activities': activities
    })

@login_required
def issue_update(request, pk):
    issue = get_object_or_404(Issue, pk=pk)
    if request.method == 'POST':
        form = IssueForm(request.POST, instance=issue)
        if form.is_valid():
            updated_issue = form.save(commit=False)
            updated_issue.updated_by = request.user
            if form.cleaned_data.get('edit_comment'):
                updated_issue._edit_comment = form.cleaned_data.get('edit_comment')
            updated_issue.save()
            return redirect('issue_detail', pk=issue.pk)
    else:
        form = IssueForm(instance=issue)
    return render(request, 'issues/form.html', {'form': form, 'is_update': True})
