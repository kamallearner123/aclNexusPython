from ai_assistant.llm_config import get_llm_config, get_llm_provider_name

from .base import LLMProviderError
from .grok_provider import GrokProvider
from .openai_provider import OpenAIProvider
from .placeholders import (
    AnthropicProvider,
    AzureOpenAIProvider,
    GeminiProvider,
    GroqProvider,
    OllamaProvider,
)


class LLMFactory:
    PROVIDERS = {
        'OPENAI': OpenAIProvider,
        'GEMINI': GeminiProvider,
        'ANTHROPIC': AnthropicProvider,
        'OLLAMA': OllamaProvider,
        'GROK': GrokProvider,
        'XAI': GrokProvider,
        'GROQ': GroqProvider,
        'AZURE': AzureOpenAIProvider,
        'AZURE_OPENAI': AzureOpenAIProvider,
    }

    @classmethod
    def create(cls, provider_name=None):
        provider = (provider_name or get_llm_provider_name()).strip().upper()
        provider_class = cls.PROVIDERS.get(provider)
        if provider_class is None:
            raise LLMProviderError(f"Unsupported LLM provider: {provider}")
        return provider_class(get_llm_config(provider))
