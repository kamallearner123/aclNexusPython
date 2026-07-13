import json

from .base import BaseLLMProvider, LLMProviderError


class GrokProvider(BaseLLMProvider):
    provider_name = 'GROK'

    def is_configured(self):
        return bool(self.config.api_key and self.config.model and self.config.endpoint)

    def generate_response(self, system_prompt, user_payload):
        response = self._create_completion(
            system_prompt=system_prompt,
            user_payload=user_payload,
            response_format=None,
        )
        return response.choices[0].message.content

    def structured_output(self, system_prompt, user_payload, schema, schema_name):
        response = self._create_completion(
            system_prompt=system_prompt,
            user_payload=user_payload,
            response_format={'type': 'json_object'},
        )
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMProviderError('Grok returned a non-JSON response.') from exc

    def _create_completion(self, system_prompt, user_payload, response_format):
        if not self.is_configured():
            raise LLMProviderError('Grok provider is not configured. Set GROK_API_KEY or XAI_API_KEY and GROK_MODEL.')

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMProviderError('The openai package is required for the Grok provider.') from exc

        client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.endpoint,
        )
        kwargs = {
            'model': self.config.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': json.dumps(user_payload, default=str)},
            ],
            'temperature': 0.2,
        }
        if response_format:
            kwargs['response_format'] = response_format

        try:
            return client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise LLMProviderError(str(exc)) from exc
