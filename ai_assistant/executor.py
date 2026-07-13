from .registry import default_tool_registry


class Executor:
    def __init__(self, user, registry=None):
        self.user = user
        self.registry = registry or default_tool_registry

    def execute(self, plan, state):
        context = {
            'user': self.user,
            'state': state,
        }

        for tool_call in plan.required_tools:
            state.add_trace(
                'Act',
                f"Invoke business tool `{tool_call.name}` through the Django ORM.",
            )
            output = self.registry.execute(tool_call.name, tool_call.parameters, context)
            state.add_tool_output(tool_call.name, output)

        state.add_trace(
            'Observe',
            'Use verified JSON tool outputs to prepare an analyst-grade response.',
        )
        return state.tool_outputs
