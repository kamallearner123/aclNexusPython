from datetime import date, timedelta

from django.db.models import Count, Q, Sum

from issues.models import Issue
from projects.models import Project
from risks.models import Risk
from tasks.models import Task
from teams.models import Team

from .metrics import calculate_health_score, calculate_workload_metrics


def _user_label(user):
    if not user:
        return None
    full_name = user.get_full_name().strip()
    return full_name or user.email


def _project_accessible_queryset(user):
    if user.is_staff or user.is_superuser:
        return Project.objects.all()
    if user.roles.filter(name='Project Manager').exists():
        return Project.objects.filter(owner=user)
    return Project.objects.filter(
        Q(tasks__assignee=user) |
        Q(team__members__user=user)
    ).distinct()


def get_accessible_projects(user):
    return _project_accessible_queryset(user).order_by('name')


def portfolio_overview(user):
    projects = list(_project_accessible_queryset(user).select_related('owner', 'team'))
    project_ids = [project.id for project in projects]
    tasks = Task.objects.filter(project_id__in=project_ids)
    issues = Issue.objects.filter(project_id__in=project_ids)
    risks = Risk.objects.filter(project_id__in=project_ids)

    return {
        'tool': 'portfolio_overview',
        'generated_on': date.today().isoformat(),
        'totals': {
            'projects': len(projects),
            'active_projects': sum(1 for project in projects if project.status == 'ACTIVE'),
            'open_tasks': tasks.exclude(status='COMPLETED').count(),
            'completed_tasks': tasks.filter(status='COMPLETED').count(),
            'open_issues': issues.filter(status__in=['OPEN', 'IN_PROGRESS']).count(),
            'high_risks': risks.filter(risk_level__in=['HIGH', 'CRITICAL']).count(),
        },
        'projects': [
            {
                'id': project.id,
                'code': project.code,
                'name': project.name,
                'status': project.get_status_display(),
                'priority': project.get_priority_display(),
                'type': project.get_project_type_display(),
                'owner': _user_label(project.owner),
                'team': project.team.name if project.team else None,
            }
            for project in projects
        ],
    }


def project_health(project_id, user):
    project = _project_accessible_queryset(user).get(pk=project_id)
    tasks = list(project.tasks.select_related('assignee', 'sprint').all())
    issues = list(project.issues.all())
    risks = list(project.risks.select_related('owner').all())
    health = calculate_health_score(project, tasks, issues, risks)

    status_counts = (
        project.tasks.values('status')
        .annotate(count=Count('id'))
        .order_by('status')
    )
    issue_counts = (
        project.issues.values('status', 'severity')
        .annotate(count=Count('id'))
        .order_by('status', 'severity')
    )

    return {
        'tool': 'project_health',
        'project': {
            'id': project.id,
            'code': project.code,
            'name': project.name,
            'status': project.get_status_display(),
            'priority': project.get_priority_display(),
            'type': project.get_project_type_display(),
            'owner': _user_label(project.owner),
            'team': project.team.name if project.team else None,
            'start_date': project.start_date.isoformat() if project.start_date else None,
            'end_date': project.end_date.isoformat() if project.end_date else None,
        },
        'health': health,
        'task_status_counts': list(status_counts),
        'issue_counts': list(issue_counts),
        'top_risks': [
            {
                'risk_id': risk.risk_id,
                'title': risk.title,
                'level': risk.risk_level,
                'score': risk.risk_score,
                'owner': _user_label(risk.owner),
                'mitigation_plan': risk.mitigation_plan,
            }
            for risk in sorted(risks, key=lambda item: item.risk_score, reverse=True)[:5]
        ],
    }


def workload_analysis(user, project_id=None):
    projects = _project_accessible_queryset(user)
    if project_id:
        projects = projects.filter(pk=project_id)

    tasks = list(
        Task.objects
        .filter(project__in=projects)
        .select_related('assignee', 'project')
        .order_by('due_date', '-priority')
    )

    return {
        'tool': 'workload_analysis',
        'scope': 'project' if project_id else 'portfolio',
        'workload': calculate_workload_metrics(tasks),
        'unassigned_tasks': [
            {
                'id': task.id,
                'task_id': task.task_id,
                'title': task.title,
                'project': task.project.code,
                'priority': task.get_priority_display(),
                'status': task.get_status_display(),
                'due_date': task.due_date.isoformat() if task.due_date else None,
            }
            for task in tasks
            if task.assignee_id is None and task.status != 'COMPLETED'
        ][:10],
    }


def issue_risk_analysis(user, project_id=None):
    projects = _project_accessible_queryset(user)
    if project_id:
        projects = projects.filter(pk=project_id)

    issues = Issue.objects.filter(project__in=projects).select_related('project', 'task')
    risks = Risk.objects.filter(project__in=projects).select_related('project', 'owner')

    return {
        'tool': 'issue_risk_analysis',
        'open_issues': [
            {
                'id': issue.id,
                'title': issue.title,
                'project': issue.project.code,
                'type': issue.get_issue_type_display(),
                'severity': issue.get_severity_display(),
                'status': issue.get_status_display(),
                'impact': issue.impact,
                'root_cause': issue.root_cause,
            }
            for issue in issues.filter(status__in=['OPEN', 'IN_PROGRESS']).order_by('severity', '-created_at')[:10]
        ],
        'critical_risks': [
            {
                'risk_id': risk.risk_id,
                'title': risk.title,
                'project': risk.project.code,
                'level': risk.get_risk_level_display(),
                'score': risk.risk_score,
                'owner': _user_label(risk.owner),
                'mitigation_plan': risk.mitigation_plan,
            }
            for risk in risks.filter(risk_level__in=['HIGH', 'CRITICAL']).order_by('-risk_score')[:10]
        ],
        'summary': {
            'open_issue_count': issues.filter(status__in=['OPEN', 'IN_PROGRESS']).count(),
            'critical_or_major_issue_count': issues.filter(
                status__in=['OPEN', 'IN_PROGRESS'],
                severity__in=['CRITICAL', 'MAJOR'],
            ).count(),
            'high_or_critical_risk_count': risks.filter(risk_level__in=['HIGH', 'CRITICAL']).count(),
        },
    }


def sprint_report(user, project_id):
    project = _project_accessible_queryset(user).get(pk=project_id)
    today = date.today()
    sprint = (
        project.sprints
        .filter(start_date__lte=today, end_date__gte=today)
        .order_by('end_date')
        .first()
    ) or project.sprints.order_by('-end_date').first()

    if not sprint:
        return {
            'tool': 'sprint_report',
            'project': project.code,
            'sprint': None,
            'message': 'No sprint records are available for this project.',
        }

    tasks = sprint.tasks.select_related('assignee').all()
    completed_points = tasks.filter(status='COMPLETED').aggregate(total=Sum('story_points'))['total'] or 0
    total_points = tasks.aggregate(total=Sum('story_points'))['total'] or 0

    return {
        'tool': 'sprint_report',
        'project': project.code,
        'sprint': {
            'name': sprint.name,
            'goal': sprint.goal,
            'start_date': sprint.start_date.isoformat(),
            'end_date': sprint.end_date.isoformat(),
            'capacity': float(sprint.capacity),
            'total_story_points': total_points,
            'completed_story_points': completed_points,
            'completion_percent': round((completed_points / total_points) * 100, 1) if total_points else 0,
        },
        'tasks': [
            {
                'task_id': task.task_id,
                'title': task.title,
                'status': task.get_status_display(),
                'priority': task.get_priority_display(),
                'assignee': _user_label(task.assignee),
                'story_points': task.story_points,
                'due_date': task.due_date.isoformat() if task.due_date else None,
            }
            for task in tasks.order_by('status', 'due_date')
        ],
    }


def weekly_activity(user, project_id=None):
    since = date.today() - timedelta(days=7)
    projects = _project_accessible_queryset(user)
    if project_id:
        projects = projects.filter(pk=project_id)

    recent_tasks = Task.objects.filter(project__in=projects, updated_at__date__gte=since).select_related('project', 'assignee')
    recent_issues = Issue.objects.filter(project__in=projects, updated_at__date__gte=since).select_related('project')

    return {
        'tool': 'weekly_activity',
        'since': since.isoformat(),
        'tasks_updated': [
            {
                'task_id': task.task_id,
                'title': task.title,
                'project': task.project.code,
                'status': task.get_status_display(),
                'assignee': _user_label(task.assignee),
                'updated_at': task.updated_at.isoformat(),
            }
            for task in recent_tasks.order_by('-updated_at')[:15]
        ],
        'issues_updated': [
            {
                'title': issue.title,
                'project': issue.project.code,
                'severity': issue.get_severity_display(),
                'status': issue.get_status_display(),
                'updated_at': issue.updated_at.isoformat(),
            }
            for issue in recent_issues.order_by('-updated_at')[:10]
        ],
    }


AVAILABLE_TOOLS = {
    'portfolio_overview': portfolio_overview,
    'project_health': project_health,
    'workload_analysis': workload_analysis,
    'issue_risk_analysis': issue_risk_analysis,
    'sprint_report': sprint_report,
    'weekly_activity': weekly_activity,
}
