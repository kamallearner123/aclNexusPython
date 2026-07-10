from datetime import date


TASK_STATUS_WEIGHTS = {
    'BACKLOG': 0,
    'PLANNED': 10,
    'IN_PROGRESS': 45,
    'IN_REVIEW': 70,
    'TESTING': 85,
    'BLOCKED': 20,
    'COMPLETED': 100,
}


def calculate_completion_percent(tasks):
    if not tasks:
        return 0
    total = sum(TASK_STATUS_WEIGHTS.get(task.status, 0) for task in tasks)
    return round(total / len(tasks), 1)


def calculate_workload_metrics(tasks):
    users = {}
    for task in tasks:
        assignee = task.assignee
        key = assignee.email if assignee else 'Unassigned'
        if key not in users:
            users[key] = {
                'assignee': key,
                'open_tasks': 0,
                'completed_tasks': 0,
                'blocked_tasks': 0,
                'story_points_open': 0,
                'overdue_tasks': 0,
            }

        if task.status == 'COMPLETED':
            users[key]['completed_tasks'] += 1
        else:
            users[key]['open_tasks'] += 1
            users[key]['story_points_open'] += task.story_points or 0

        if task.status == 'BLOCKED':
            users[key]['blocked_tasks'] += 1
        if task.due_date and task.due_date < date.today() and task.status != 'COMPLETED':
            users[key]['overdue_tasks'] += 1

    return sorted(
        users.values(),
        key=lambda item: (item['blocked_tasks'], item['overdue_tasks'], item['story_points_open']),
        reverse=True,
    )


def calculate_health_score(project, tasks, issues, risks):
    score = 100
    open_tasks = [task for task in tasks if task.status != 'COMPLETED']
    overdue_tasks = [
        task for task in open_tasks
        if task.due_date and task.due_date < date.today()
    ]
    blocked_tasks = [task for task in open_tasks if task.status == 'BLOCKED']
    severe_issues = [
        issue for issue in issues
        if issue.status in ('OPEN', 'IN_PROGRESS') and issue.severity in ('CRITICAL', 'MAJOR')
    ]
    high_risks = [risk for risk in risks if risk.risk_level in ('HIGH', 'CRITICAL')]

    score -= min(len(overdue_tasks) * 4, 20)
    score -= min(len(blocked_tasks) * 6, 24)
    score -= min(len(severe_issues) * 7, 28)
    score -= min(len(high_risks) * 6, 24)

    if project.status == 'ON_HOLD':
        score -= 15
    elif project.status == 'CANCELLED':
        score -= 35
    elif project.status == 'COMPLETED':
        score += 5

    score = max(0, min(100, score))
    if score >= 80:
        label = 'Healthy'
    elif score >= 60:
        label = 'Watch'
    elif score >= 40:
        label = 'At Risk'
    else:
        label = 'Critical'

    return {
        'score': score,
        'label': label,
        'completion_percent': calculate_completion_percent(tasks),
        'signals': {
            'open_tasks': len(open_tasks),
            'overdue_tasks': len(overdue_tasks),
            'blocked_tasks': len(blocked_tasks),
            'severe_open_issues': len(severe_issues),
            'high_or_critical_risks': len(high_risks),
        },
    }
