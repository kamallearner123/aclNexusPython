from .llm_config import DEFAULT_MODELS, get_llm_config, load_local_env
from .llm_providers import LLMFactory
from .llm_providers.base import LLMProviderError


def is_llm_configured():
    try:
        return LLMFactory.create().is_configured()
    except LLMProviderError:
        return False


def get_openai_model():
    return get_llm_config('OPENAI').model or DEFAULT_MODELS['OPENAI']


class LLMReportError(Exception):
    pass


REPORT_JSON_SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'title': {'type': 'string'},
        'executive_summary': {'type': 'string'},
        'narrative': {'type': 'string'},
        'findings': {
            'type': 'array',
            'items': {'type': 'string'},
        },
        'recommendations': {
            'type': 'array',
            'items': {'type': 'string'},
        },
        'sections': {
            'type': 'array',
            'items': {
                'type': 'object',
                'additionalProperties': False,
                'properties': {
                    'heading': {'type': 'string'},
                    'items': {
                        'type': 'array',
                        'items': {'type': 'string'},
                    },
                },
                'required': ['heading', 'items'],
            },
        },
    },
    'required': [
        'title',
        'executive_summary',
        'narrative',
        'findings',
        'recommendations',
        'sections',
    ],
}


def generate_project_report(prompt, report_type, tool_outputs, deterministic_report):
    load_local_env()

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
        data = LLMFactory.create().structured_output(
            system_prompt=system_prompt,
            user_payload=user_payload,
            schema=REPORT_JSON_SCHEMA,
            schema_name='pia_project_intelligence_report',
        )
    except LLMProviderError as exc:
        raise LLMReportError(str(exc)) from exc

    return normalize_llm_report(data, deterministic_report)


def extract_response_text(response):
    output_text = getattr(response, 'output_text', None)
    if output_text:
        return output_text

    output = getattr(response, 'output', None) or []
    chunks = []
    for item in output:
        for content_item in getattr(item, 'content', []) or []:
            text = getattr(content_item, 'text', None)
            if text:
                chunks.append(text)

    if chunks:
        return ''.join(chunks)

    raise LLMReportError('LLM provider returned an empty response.')


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
