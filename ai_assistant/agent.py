from dataclasses import dataclass

from django.core.exceptions import PermissionDenied

from . import tools
from .llm import LLMReportError, generate_project_report, is_llm_configured


REPORT_PRESETS = {
    'portfolio': {
        'label': 'Portfolio Summary',
        'tool_names': ['portfolio_overview', 'issue_risk_analysis', 'workload_analysis', 'weekly_activity'],
    },
    'project_health': {
        'label': 'Project Health Assessment',
        'tool_names': ['project_health', 'issue_risk_analysis', 'workload_analysis', 'weekly_activity'],
        'requires_project': True,
    },
    'weekly': {
        'label': 'Weekly Project Report',
        'tool_names': ['project_health', 'weekly_activity', 'issue_risk_analysis', 'workload_analysis'],
        'requires_project': True,
    },
    'sprint': {
        'label': 'Sprint Report',
        'tool_names': ['sprint_report', 'workload_analysis', 'issue_risk_analysis'],
        'requires_project': True,
    },
    'workload': {
        'label': 'Workload Analysis',
        'tool_names': ['workload_analysis'],
    },
    'risk_issue': {
        'label': 'Issue and Risk Analysis',
        'tool_names': ['issue_risk_analysis'],
    },
}


@dataclass
class AgentResult:
    title: str
    executive_summary: str
    narrative: str
    findings: list
    recommendations: list
    sections: list
    trace: list
    tool_outputs: list
    generation_mode: str = 'Deterministic Engine'
    llm_error: str = ''


class ProjectIntelligenceAgent:
    """
    ReAct-style project analyst.

    The agent can reason about which business tools are needed, but each tool is
    a deterministic ORM-backed function. Tool responses are JSON-serializable
    dictionaries, so an LLM provider can be added later without direct DB access.
    """

    def __init__(self, user):
        self.user = user

    def analyze(self, prompt, report_type='project_health', project_id=None, use_llm=True):
        prompt = (prompt or '').strip()
        report_type = report_type or self._infer_report_type(prompt)
        preset = REPORT_PRESETS.get(report_type, REPORT_PRESETS['project_health'])

        if preset.get('requires_project') and not project_id:
            project = tools.get_accessible_projects(self.user).first()
            if not project:
                raise PermissionDenied('No accessible project is available for this report.')
            project_id = project.pk

        trace = [
            {
                'step': 'Reason',
                'detail': self._build_reasoning(prompt, preset, project_id),
            }
        ]

        tool_outputs = []
        for tool_name in preset['tool_names']:
            trace.append({
                'step': 'Act',
                'detail': f"Invoke business tool `{tool_name}` through the Django ORM.",
            })
            tool_outputs.append(self._invoke_tool(tool_name, project_id))

        trace.append({
            'step': 'Observe',
            'detail': 'Use verified JSON tool outputs to prepare an analyst-grade response.',
        })

        deterministic_result = self._compose_report(preset['label'], prompt, tool_outputs, trace)
        if not use_llm:
            return deterministic_result

        return self._enhance_with_llm(
            deterministic_result=deterministic_result,
            prompt=prompt,
            report_type=report_type,
            tool_outputs=tool_outputs,
        )

    def _infer_report_type(self, prompt):
        text = prompt.lower()
        if 'sprint' in text:
            return 'sprint'
        if 'workload' in text or 'capacity' in text or 'overload' in text:
            return 'workload'
        if 'risk' in text or 'issue' in text or 'blocker' in text:
            return 'risk_issue'
        if 'portfolio' in text or 'all project' in text:
            return 'portfolio'
        if 'week' in text or 'weekly' in text:
            return 'weekly'
        return 'project_health'

    def _build_reasoning(self, prompt, preset, project_id):
        requested = prompt or preset['label']
        scope = f"project #{project_id}" if project_id else 'accessible portfolio'
        return (
            f"Understand request: {requested}. Plan required data for {scope}: "
            f"{', '.join(preset['tool_names'])}."
        )

    def _invoke_tool(self, tool_name, project_id):
        if tool_name == 'portfolio_overview':
            return tools.portfolio_overview(self.user)
        if tool_name == 'project_health':
            return tools.project_health(project_id, self.user)
        if tool_name == 'workload_analysis':
            return tools.workload_analysis(self.user, project_id=project_id)
        if tool_name == 'issue_risk_analysis':
            return tools.issue_risk_analysis(self.user, project_id=project_id)
        if tool_name == 'sprint_report':
            return tools.sprint_report(self.user, project_id)
        if tool_name == 'weekly_activity':
            return tools.weekly_activity(self.user, project_id=project_id)
        raise ValueError(f"Unknown PIA tool: {tool_name}")

    def _compose_report(self, title, prompt, tool_outputs, trace):
        project_health = self._find_tool(tool_outputs, 'project_health')
        portfolio = self._find_tool(tool_outputs, 'portfolio_overview')
        workload = self._find_tool(tool_outputs, 'workload_analysis')
        issue_risk = self._find_tool(tool_outputs, 'issue_risk_analysis')
        sprint = self._find_tool(tool_outputs, 'sprint_report')
        weekly = self._find_tool(tool_outputs, 'weekly_activity')

        findings = []
        recommendations = []
        sections = []

        if project_health:
            health = project_health['health']
            project = project_health['project']
            findings.append(
                f"{project['code']} is currently {health['label']} with a health score of {health['score']}/100 "
                f"and estimated completion of {health['completion_percent']}%."
            )
            signals = health['signals']
            if signals['blocked_tasks'] or signals['overdue_tasks']:
                findings.append(
                    f"Delivery pressure is visible: {signals['blocked_tasks']} blocked task(s) and "
                    f"{signals['overdue_tasks']} overdue task(s)."
                )
                recommendations.append('Review blocked and overdue tasks first; assign owners and next actions before the next standup.')
            if signals['severe_open_issues']:
                recommendations.append('Create a focused resolution plan for critical and major open issues.')
            if signals['high_or_critical_risks']:
                recommendations.append('Revalidate high and critical risk mitigation plans with accountable owners.')
            sections.append({
                'heading': 'Project Health',
                'items': [
                    f"Status: {project['status']}",
                    f"Priority: {project['priority']}",
                    f"Owner: {project['owner'] or 'Not assigned'}",
                    f"Team: {project['team'] or 'Not assigned'}",
                ],
            })

        if portfolio:
            totals = portfolio['totals']
            findings.append(
                f"The accessible portfolio has {totals['projects']} project(s), including "
                f"{totals['active_projects']} active project(s), {totals['open_tasks']} open task(s), "
                f"{totals['open_issues']} open issue(s), and {totals['high_risks']} high/critical risk(s)."
            )
            if totals['high_risks'] or totals['open_issues']:
                recommendations.append('Use the portfolio review to prioritize risk burn-down and issue closure across active projects.')
            sections.append({
                'heading': 'Portfolio Snapshot',
                'items': [
                    f"{project['code']} - {project['name']} ({project['status']}, {project['priority']})"
                    for project in portfolio['projects'][:8]
                ] or ['No accessible projects found.'],
            })

        if workload:
            overloaded = [
                person for person in workload['workload']
                if person['open_tasks'] >= 5 or person['blocked_tasks'] or person['overdue_tasks']
            ]
            if workload['workload']:
                busiest = workload['workload'][0]
                findings.append(
                    f"Highest visible workload is with {busiest['assignee']}: {busiest['open_tasks']} open task(s), "
                    f"{busiest['story_points_open']} open story point(s), {busiest['blocked_tasks']} blocked task(s)."
                )
            if overloaded:
                recommendations.append('Balance workload by moving lower-priority open tasks away from overloaded assignees.')
            if workload['unassigned_tasks']:
                recommendations.append('Assign owners to unassigned tasks so accountability is clear.')
            sections.append({
                'heading': 'Workload',
                'items': [
                    f"{item['assignee']}: {item['open_tasks']} open, {item['completed_tasks']} completed, "
                    f"{item['story_points_open']} open points"
                    for item in workload['workload'][:8]
                ] or ['No task workload found.'],
            })

        if issue_risk:
            summary = issue_risk['summary']
            findings.append(
                f"Risk/issue posture: {summary['open_issue_count']} open issue(s), "
                f"{summary['critical_or_major_issue_count']} critical/major issue(s), and "
                f"{summary['high_or_critical_risk_count']} high/critical risk(s)."
            )
            sections.append({
                'heading': 'Risks and Issues',
                'items': self._risk_issue_items(issue_risk),
            })

        if sprint:
            sprint_data = sprint.get('sprint')
            if sprint_data:
                findings.append(
                    f"Sprint {sprint_data['name']} is {sprint_data['completion_percent']}% complete by story points "
                    f"({sprint_data['completed_story_points']}/{sprint_data['total_story_points']})."
                )
                if sprint_data['capacity'] and sprint_data['total_story_points'] > sprint_data['capacity']:
                    recommendations.append('Sprint scope exceeds recorded capacity; consider de-scoping or adding capacity.')
                sections.append({
                    'heading': 'Sprint Progress',
                    'items': [
                        f"Goal: {sprint_data['goal'] or 'No goal recorded'}",
                        f"Window: {sprint_data['start_date']} to {sprint_data['end_date']}",
                        f"Capacity: {sprint_data['capacity']}",
                    ],
                })
            else:
                findings.append(sprint.get('message', 'No sprint data is available.'))

        if weekly:
            findings.append(
                f"Weekly activity includes {len(weekly['tasks_updated'])} task update(s) and "
                f"{len(weekly['issues_updated'])} issue update(s) since {weekly['since']}."
            )
            sections.append({
                'heading': 'Recent Activity',
                'items': [
                    f"{task['project']} / {task['task_id']}: {task['title']} moved/updated as {task['status']}"
                    for task in weekly['tasks_updated'][:6]
                ] or ['No recent task activity found.'],
            })

        if not recommendations:
            recommendations.append('Continue monitoring delivery signals and keep project data current for sharper intelligence.')

        executive_summary = self._executive_summary(title, findings)
        return AgentResult(
            title=title,
            executive_summary=executive_summary,
            narrative='',
            findings=findings[:8],
            recommendations=list(dict.fromkeys(recommendations))[:8],
            sections=sections,
            trace=trace,
            tool_outputs=tool_outputs,
        )

    def _enhance_with_llm(self, deterministic_result, prompt, report_type, tool_outputs):
        if not is_llm_configured():
            deterministic_result.trace.append({
                'step': 'Write',
                'detail': 'OpenAI API key was not found, so PIA used the deterministic report writer.',
            })
            return deterministic_result

        deterministic_result.trace.append({
            'step': 'Write',
            'detail': 'Send verified JSON tool outputs to OpenAI for professional report writing.',
        })

        try:
            llm_report = generate_project_report(
                prompt=prompt,
                report_type=report_type,
                tool_outputs=tool_outputs,
                deterministic_report=deterministic_result,
            )
        except LLMReportError as exc:
            deterministic_result.llm_error = str(exc)
            deterministic_result.trace.append({
                'step': 'Fallback',
                'detail': 'OpenAI report writing failed, so PIA returned the deterministic report.',
            })
            return deterministic_result

        return AgentResult(
            title=llm_report['title'],
            executive_summary=llm_report['executive_summary'],
            narrative=llm_report['narrative'],
            findings=llm_report['findings'][:10],
            recommendations=llm_report['recommendations'][:10],
            sections=llm_report['sections'],
            trace=deterministic_result.trace,
            tool_outputs=tool_outputs,
            generation_mode='OpenAI Enhanced',
        )

    def _find_tool(self, outputs, tool_name):
        return next((item for item in outputs if item.get('tool') == tool_name), None)

    def _risk_issue_items(self, issue_risk):
        items = []
        for risk in issue_risk['critical_risks'][:5]:
            items.append(f"{risk['project']} risk {risk['risk_id']}: {risk['title']} ({risk['level']}, score {risk['score']})")
        for issue in issue_risk['open_issues'][:5]:
            items.append(f"{issue['project']} issue: {issue['title']} ({issue['severity']}, {issue['status']})")
        return items or ['No high-priority risks or open issues found in this scope.']

    def _executive_summary(self, title, findings):
        if findings:
            return f"{title}: {findings[0]}"
        return f"{title}: PIA did not find enough data to produce a detailed assessment yet."
