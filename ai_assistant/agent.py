from .executor import Executor
from .planner import REPORT_PRESETS, Planner
from .response_generator import ResponseGenerator
from .result import AgentResult
from .state import AgentState


class ProjectIntelligenceAgent:
    """
    ReAct-style project analyst.

    The agent can reason about which business tools are needed, but each tool is
    a deterministic ORM-backed function. Tool responses are JSON-serializable
    dictionaries, so an LLM provider can be added later without direct DB access.
    """

    def __init__(self, user):
        self.user = user
        self.planner = Planner(user)
        self.executor = Executor(user)
        self.response_generator = ResponseGenerator()

    def analyze(self, prompt, report_type='project_health', project_id=None, use_llm=True):
        prompt = (prompt or '').strip()
        state = AgentState(
            question=prompt,
            report_type=report_type,
            project_id=project_id,
        )
        plan = self.planner.plan(state)
        self.executor.execute(plan, state)
        return self.response_generator.generate(state, use_llm=use_llm)
