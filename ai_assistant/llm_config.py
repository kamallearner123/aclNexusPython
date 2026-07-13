import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PROVIDER = 'OPENAI'
DEFAULT_MODELS = {
    'OPENAI': 'gpt-4o-mini',
    'AZURE_OPENAI': '',
    'GEMINI': 'gemini-1.5-pro',
    'ANTHROPIC': 'claude-3-5-sonnet-latest',
    'OLLAMA': 'llama3.1',
    'GROQ': 'llama3-8b-8192',
    'GROK': 'grok-code-fast-1',
    'XAI': 'grok-code-fast-1',
}


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    api_key: str = ''
    model: str = ''
    endpoint: str = ''
    api_version: str = ''


def load_local_env():
    """
    Lightweight .env loader for local development.

    Existing environment variables win over values stored in .env.
    """
    env_path = BASE_DIR / '.env'
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def get_llm_provider_name():
    load_local_env()
    return (os.environ.get('LLM_PROVIDER') or DEFAULT_PROVIDER).strip().upper()


def get_llm_config(provider_name=None):
    load_local_env()
    provider = (provider_name or get_llm_provider_name()).strip().upper()

    if provider in ('AZURE', 'AZURE_OPENAI'):
        return LLMConfig(
            provider='AZURE_OPENAI',
            api_key=os.environ.get('AZURE_OPENAI_API_KEY', ''),
            model=os.environ.get('AZURE_OPENAI_DEPLOYMENT') or os.environ.get('AZURE_OPENAI_MODEL', ''),
            endpoint=os.environ.get('AZURE_OPENAI_ENDPOINT', ''),
            api_version=os.environ.get('AZURE_OPENAI_API_VERSION', ''),
        )

    if provider in ('GROK', 'XAI'):
        return LLMConfig(
            provider='GROK',
            api_key=(
                os.environ.get('GROK_API_KEY')
                or os.environ.get('XAI_API_KEY')
                or os.environ.get('GROQ_API_KEY', '')
            ),
            model=(
                os.environ.get('GROK_MODEL')
                or os.environ.get('XAI_MODEL')
                or os.environ.get('GROQ_MODEL')
                or DEFAULT_MODELS['GROK']
            ),
            endpoint=(
                os.environ.get('GROK_BASE_URL')
                or os.environ.get('XAI_BASE_URL')
                or 'https://api.x.ai/v1'
            ),
        )

    env_prefix = provider
    return LLMConfig(
        provider=provider,
        api_key=os.environ.get(f'{env_prefix}_API_KEY', ''),
        model=os.environ.get(f'{env_prefix}_MODEL') or DEFAULT_MODELS.get(provider, ''),
        endpoint=os.environ.get(f'{env_prefix}_BASE_URL') or os.environ.get(f'{env_prefix}_ENDPOINT', ''),
    )
