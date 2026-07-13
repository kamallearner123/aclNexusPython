from abc import ABC, abstractmethod


class LLMProviderError(Exception):
    pass


class BaseLLMProvider(ABC):
    provider_name = 'BASE'

    def __init__(self, config):
        self.config = config

    @abstractmethod
    def is_configured(self):
        raise NotImplementedError

    @abstractmethod
    def generate_response(self, system_prompt, user_payload):
        raise NotImplementedError

    @abstractmethod
    def structured_output(self, system_prompt, user_payload, schema, schema_name):
        raise NotImplementedError
