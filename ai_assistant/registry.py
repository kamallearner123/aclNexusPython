from dataclasses import dataclass
from typing import Callable

from . import tools


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    execute: Callable


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, tool):
        self._tools[tool.name] = tool

    def get(self, name):
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ValueError(f"Unknown PIA tool: {name}") from exc

    def execute(self, name, parameters, context):
        tool = self.get(name)
        return tool.execute(parameters or {}, context)

    def list_tools(self):
        return list(self._tools.values())


def _portfolio_overview(parameters, context):
    return tools.portfolio_overview(context['user'])


def _project_health(parameters, context):
    return tools.project_health(parameters.get('project_id'), context['user'])


def _workload_analysis(parameters, context):
    return tools.workload_analysis(context['user'], project_id=parameters.get('project_id'))


def _issue_risk_analysis(parameters, context):
    return tools.issue_risk_analysis(context['user'], project_id=parameters.get('project_id'))


def _sprint_report(parameters, context):
    return tools.sprint_report(context['user'], parameters.get('project_id'))


def _weekly_activity(parameters, context):
    return tools.weekly_activity(context['user'], project_id=parameters.get('project_id'))


def build_default_registry():
    registry = ToolRegistry()

    optional_project_schema = {
        'type': 'object',
        'properties': {
            'project_id': {
                'type': ['integer', 'null'],
                'description': 'Optional project primary key used to scope the analysis.',
            }
        },
    }
    required_project_schema = {
        'type': 'object',
        'properties': {
            'project_id': {
                'type': 'integer',
                'description': 'Project primary key used to scope the analysis.',
            }
        },
        'required': ['project_id'],
    }

    registry.register(Tool(
        name='portfolio_overview',
        description='Return portfolio-level project, task, issue, and risk counts for projects the user can access.',
        parameters={'type': 'object', 'properties': {}},
        execute=_portfolio_overview,
    ))
    registry.register(Tool(
        name='project_health',
        description='Return deterministic project health metrics, task status counts, issue counts, and top risks.',
        parameters=required_project_schema,
        execute=_project_health,
    ))
    registry.register(Tool(
        name='workload_analysis',
        description='Return workload distribution, open work, blocked work, overdue work, and unassigned tasks.',
        parameters=optional_project_schema,
        execute=_workload_analysis,
    ))
    registry.register(Tool(
        name='issue_risk_analysis',
        description='Return open issues, high-priority risks, and issue/risk summary counts.',
        parameters=optional_project_schema,
        execute=_issue_risk_analysis,
    ))
    registry.register(Tool(
        name='sprint_report',
        description='Return current or latest sprint progress and sprint task details for a project.',
        parameters=required_project_schema,
        execute=_sprint_report,
    ))
    registry.register(Tool(
        name='weekly_activity',
        description='Return task and issue activity updated during the last seven days.',
        parameters=optional_project_schema,
        execute=_weekly_activity,
    ))

    return registry


default_tool_registry = build_default_registry()
