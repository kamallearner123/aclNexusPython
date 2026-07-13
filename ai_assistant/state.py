from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:
    question: str
    report_type: str
    project_id: int | None = None
    objective: str = ''
    current_plan: Any = None
    tool_outputs: list = field(default_factory=list)
    visited_tools: list = field(default_factory=list)
    observations: list = field(default_factory=list)
    reasoning_trace: list = field(default_factory=list)
    final_report: Any = None

    def add_trace(self, step, detail):
        self.reasoning_trace.append({
            'step': step,
            'detail': detail,
        })

    def add_tool_output(self, tool_name, output):
        self.visited_tools.append(tool_name)
        self.tool_outputs.append(output)
        self.observations.append({
            'tool': tool_name,
            'summary': output.get('tool', tool_name) if isinstance(output, dict) else tool_name,
        })
