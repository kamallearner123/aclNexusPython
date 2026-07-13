from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolCall:
    name: str
    parameters: dict = field(default_factory=dict)


@dataclass
class Plan:
    objective: str
    required_tools: list
    reasoning: str
    status: str = 'planned'
