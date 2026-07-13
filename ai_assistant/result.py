from dataclasses import dataclass


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
