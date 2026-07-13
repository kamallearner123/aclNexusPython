from .base import BaseLLMProvider, LLMProviderError


class PlaceholderProvider(BaseLLMProvider):
    provider_name = 'PLACEHOLDER'

    def is_configured(self):
        return bool(self.config.api_key or self.config.endpoint)

    def generate_response(self, system_prompt, user_payload):
        raise LLMProviderError(f"{self.provider_name} provider is registered but not implemented yet.")

    def structured_output(self, system_prompt, user_payload, schema, schema_name):
        raise LLMProviderError(f"{self.provider_name} provider is registered but not implemented yet.")


class GeminiProvider(PlaceholderProvider):
    provider_name = 'GEMINI'


class AnthropicProvider(PlaceholderProvider):
    provider_name = 'ANTHROPIC'


class OllamaProvider(PlaceholderProvider):
    provider_name = 'OLLAMA'


class GroqProvider(PlaceholderProvider):
    provider_name = 'GROQ'


class AzureOpenAIProvider(PlaceholderProvider):
    provider_name = 'AZURE_OPENAI'
