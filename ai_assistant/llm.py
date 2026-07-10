import json
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = 'gpt-4o-mini'


def load_local_env():
    """
    Lightweight .env loader for local development.

    This keeps the project independent from python-dotenv while still allowing
    OPENAI_API_KEY and OPENAI_MODEL to be stored in the project-level .env file.
    Existing environment variables always win.
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


def is_llm_configured():
    load_local_env()
    return bool(os.environ.get('OPENAI_API_KEY'))


def get_openai_model():
    load_local_env()
    return os.environ.get('OPENAI_MODEL') or DEFAULT_MODEL


class LLMReportError(Exception):
    pass


def generate_project_report(prompt, report_type, tool_outputs, deterministic_report):
    load_local_env()

    if not os.environ.get('OPENAI_API_KEY'):
        raise LLMReportError('OPENAI_API_KEY is not configured.')

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise LLMReportError('The openai package is not installed.') from exc

    model = get_openai_model()
    client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

    system_prompt = (
        "You are PIA, the AI Project Intelligence Agent for a Django-based "
        "Project Portfolio & Engineering Delivery Platform. You are not a chatbot. "
        "You are a senior project analyst writing professional delivery intelligence reports. "
        "Use only the verified JSON tool outputs and deterministic baseline report provided. "
        "Do not invent project data, dates, names, metrics, owners, risks, issues, or task counts. "
        "Never mention SQL or claim database access. If data is missing, state that it is not recorded. "
        "Return valid JSON only with keys: title, executive_summary, narrative, findings, recommendations, sections. "
        "sections must be an array of objects with heading and items keys. findings, recommendations, and items must be arrays of strings."
    )

    user_payload = {
        'user_request': prompt,
        'report_type': report_type,
        'verified_tool_outputs': tool_outputs,
        'deterministic_baseline_report': {
            'title': deterministic_report.title,
            'executive_summary': deterministic_report.executive_summary,
            'findings': deterministic_report.findings,
            'recommendations': deterministic_report.recommendations,
            'sections': deterministic_report.sections,
        },
        'writing_requirements': [
            'Write like a professional project analyst for PMs, architects, team leads, and engineers.',
            'Start with a clear executive summary.',
            'Explain what the numbers mean for delivery, risk, workload, and next actions.',
            'Keep recommendations actionable and tied to the provided data.',
            'Use concise business language, not casual chat.',
        ],
    }

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': json.dumps(user_payload, default=str)},
            ],
            response_format={'type': 'json_object'},
            temperature=0.2,
        )
    except Exception as exc:
        raise LLMReportError(str(exc)) from exc

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMReportError('OpenAI returned a non-JSON report.') from exc

    return normalize_llm_report(data, deterministic_report)


def normalize_llm_report(data, fallback):
    def string_list(value, default):
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        return default

    sections = data.get('sections')
    normalized_sections = []
    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict):
                continue
            heading = str(section.get('heading') or '').strip()
            items = string_list(section.get('items'), [])
            if heading and items:
                normalized_sections.append({'heading': heading, 'items': items})

    return {
        'title': str(data.get('title') or fallback.title),
        'executive_summary': str(data.get('executive_summary') or fallback.executive_summary),
        'narrative': str(data.get('narrative') or ''),
        'findings': string_list(data.get('findings'), fallback.findings),
        'recommendations': string_list(data.get('recommendations'), fallback.recommendations),
        'sections': normalized_sections or fallback.sections,
    }
