import json

from .base import BaseLLMProvider, LLMProviderError


class OpenAIProvider(BaseLLMProvider):
    provider_name = 'OPENAI'

    def is_configured(self):
        return bool(self.config.api_key)

    def generate_response(self, system_prompt, user_payload):
        response = self._create_response(
            system_prompt=system_prompt,
            user_payload=user_payload,
            text_config=None,
        )
        return self._extract_response_text(response)

    def structured_output(self, system_prompt, user_payload, schema, schema_name):
        response = self._create_response(
            system_prompt=system_prompt,
            user_payload=user_payload,
            text_config={
                'format': {
                    'type': 'json_schema',
                    'name': schema_name,
                    'schema': schema,
                    'strict': True,
                }
            },
        )
        content = self._extract_response_text(response)
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMProviderError('OpenAI returned a non-JSON response.') from exc

    def _create_response(self, system_prompt, user_payload, text_config):
        if not self.is_configured():
            raise LLMProviderError('OPENAI_API_KEY is not configured.')

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMProviderError('The openai package is not installed.') from exc

        client = OpenAI(api_key=self.config.api_key)
        kwargs = {
            'model': self.config.model,
            'instructions': system_prompt,
            'input': json.dumps(user_payload, default=str),
            'temperature': 0.2,
        }
        if text_config:
            kwargs['text'] = text_config

        try:
            return client.responses.create(**kwargs)
        except Exception as exc:
            raise LLMProviderError(str(exc)) from exc

    def _extract_response_text(self, response):
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

        raise LLMProviderError('OpenAI returned an empty response.')
