from django.core.exceptions import PermissionDenied

from . import tools
from .plan import Plan, ToolCall


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


class Planner:
    def __init__(self, user):
        self.user = user

    def plan(self, state):
        report_type = state.report_type or self.infer_report_type(state.question)
        preset = REPORT_PRESETS.get(report_type, REPORT_PRESETS['project_health'])

        if preset.get('requires_project') and not state.project_id:
            project = tools.get_accessible_projects(self.user).first()
            if not project:
                raise PermissionDenied('No accessible project is available for this report.')
            state.project_id = project.pk

        state.report_type = report_type
        state.objective = preset['label']

        required_tools = [
            ToolCall(name=tool_name, parameters=self._parameters_for_tool(tool_name, state.project_id))
            for tool_name in preset['tool_names']
        ]

        reasoning = self._build_reasoning(state.question, preset, state.project_id)
        plan = Plan(
            objective=preset['label'],
            required_tools=required_tools,
            reasoning=reasoning,
            status='ready',
        )
        state.current_plan = plan
        state.add_trace('Reason', reasoning)
        return plan

    def infer_report_type(self, prompt):
        text = (prompt or '').lower()
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
        tool_names = ', '.join(preset['tool_names'])
        return f"Understand request: {requested}. Plan required data for {scope}: {tool_names}."

    def _parameters_for_tool(self, tool_name, project_id):
        if tool_name == 'portfolio_overview':
            return {}
        if project_id:
            return {'project_id': project_id}
        return {}
