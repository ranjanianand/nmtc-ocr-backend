"""
Enterprise AI Client - Universal AI Provider Interface
Supports plug-and-play architecture for OpenAI, Azure OpenAI, and future providers
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import os
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class AIProvider(Enum):
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    LOCAL_LLM = "local_llm"

@dataclass
class AIUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)

@dataclass
class AIResponse:
    content: str
    model: str
    usage: AIUsage
    provider: str
    response_time_seconds: float
    timestamp: str
    raw_response: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "usage": self.usage.to_dict(),
            "provider": self.provider,
            "response_time_seconds": self.response_time_seconds,
            "timestamp": self.timestamp
        }

class AIClientError(Exception):
    """Base exception for AI client errors"""
    pass

class AIClientInterface(ABC):
    """Abstract interface for all AI providers"""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.logger = logging.getLogger(f"{__name__}.{provider_name}")

    @abstractmethod
    def chat_completion(self,
                       messages: List[Dict[str, str]],
                       model: str = None,
                       temperature: float = 0.7,
                       max_tokens: Optional[int] = None,
                       **kwargs) -> AIResponse:
        """
        Generate chat completion using the AI provider

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name to use
            temperature: Randomness (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Returns:
            AIResponse with standardized format

        Raises:
            AIClientError: If the request fails
        """
        pass

    def get_available_models(self) -> List[str]:
        """Get list of available models for this provider"""
        return []

    def validate_config(self) -> bool:
        """Validate provider configuration"""
        return True

class OpenAIClient(AIClientInterface):
    """OpenAI API client implementation"""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", organization: Optional[str] = None):
        super().__init__("openai")

        try:
            import openai
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url=base_url,
                organization=organization
            )
            self.api_key = api_key
            self.base_url = base_url

            self.logger.info(f"OpenAI client initialized with base_url: {base_url}")

        except ImportError:
            raise AIClientError("OpenAI package not installed. Run: pip install openai")
        except Exception as e:
            raise AIClientError(f"Failed to initialize OpenAI client: {str(e)}")

    def chat_completion(self, messages, model="gpt-4", temperature=0.7, max_tokens=None, **kwargs):
        start_time = datetime.now()

        try:
            self.logger.debug(f"Making OpenAI request with model: {model}, messages: {len(messages)}")

            # Filter out None values
            params = {
                "model": model,
                "messages": messages,
                "temperature": temperature
            }

            if max_tokens is not None:
                params["max_tokens"] = max_tokens

            # Add any additional parameters
            params.update({k: v for k, v in kwargs.items() if v is not None})

            response = self.client.chat.completions.create(**params)

            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()

            # Extract usage information
            usage = AIUsage(
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0
            )

            ai_response = AIResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage=usage,
                provider=self.provider_name,
                response_time_seconds=response_time,
                timestamp=end_time.isoformat(),
                raw_response=response
            )

            self.logger.info(f"OpenAI request successful: {usage.total_tokens} tokens, {response_time:.2f}s")
            return ai_response

        except Exception as e:
            self.logger.error(f"OpenAI request failed: {str(e)}")
            raise AIClientError(f"OpenAI request failed: {str(e)}")

    def get_available_models(self) -> List[str]:
        """Get available OpenAI models"""
        return [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4-turbo-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k"
        ]

    def validate_config(self) -> bool:
        """Validate OpenAI configuration"""
        try:
            # Simple test request
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            self.logger.error(f"OpenAI config validation failed: {str(e)}")
            return False

class AzureOpenAIClient(AIClientInterface):
    """Azure OpenAI API client implementation"""

    def __init__(self, api_key: str, endpoint: str, api_version: str = "2024-02-01"):
        super().__init__("azure_openai")

        try:
            from openai import AzureOpenAI
            self.client = AzureOpenAI(
                api_key=api_key,
                azure_endpoint=endpoint,
                api_version=api_version
            )
            self.api_key = api_key
            self.endpoint = endpoint
            self.api_version = api_version

            self.logger.info(f"Azure OpenAI client initialized with endpoint: {endpoint}")

        except ImportError:
            raise AIClientError("OpenAI package not installed. Run: pip install openai")
        except Exception as e:
            raise AIClientError(f"Failed to initialize Azure OpenAI client: {str(e)}")

    def chat_completion(self, messages, model="gpt-4", temperature=0.7, max_tokens=None, **kwargs):
        start_time = datetime.now()

        try:
            self.logger.debug(f"Making Azure OpenAI request with model: {model}, messages: {len(messages)}")

            # Filter out None values
            params = {
                "model": model,
                "messages": messages,
                "temperature": temperature
            }

            if max_tokens is not None:
                params["max_tokens"] = max_tokens

            # Add any additional parameters
            params.update({k: v for k, v in kwargs.items() if v is not None})

            response = self.client.chat.completions.create(**params)

            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()

            # Extract usage information
            usage = AIUsage(
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0
            )

            ai_response = AIResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage=usage,
                provider=self.provider_name,
                response_time_seconds=response_time,
                timestamp=end_time.isoformat(),
                raw_response=response
            )

            self.logger.info(f"Azure OpenAI request successful: {usage.total_tokens} tokens, {response_time:.2f}s")
            return ai_response

        except Exception as e:
            self.logger.error(f"Azure OpenAI request failed: {str(e)}")
            raise AIClientError(f"Azure OpenAI request failed: {str(e)}")

    def get_available_models(self) -> List[str]:
        """Get available Azure OpenAI models"""
        return [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-35-turbo",
            "gpt-35-turbo-16k"
        ]

    def validate_config(self) -> bool:
        """Validate Azure OpenAI configuration"""
        try:
            # Simple test request
            response = self.client.chat.completions.create(
                model="gpt-35-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            self.logger.error(f"Azure OpenAI config validation failed: {str(e)}")
            return False

class AIClientFactory:
    """Factory for creating AI clients based on configuration"""

    _clients = {}  # Cache for initialized clients

    @staticmethod
    def create_client(provider: Union[AIProvider, str] = None, **config_overrides) -> AIClientInterface:
        """
        Create AI client based on provider and configuration

        Args:
            provider: AI provider to use (defaults to environment variable)
            **config_overrides: Override default configuration

        Returns:
            Configured AI client instance

        Raises:
            AIClientError: If configuration is invalid or provider unsupported
        """

        # Determine provider
        if provider is None:
            provider_str = os.getenv("AI_PROVIDER", "openai")
        elif isinstance(provider, AIProvider):
            provider_str = provider.value
        else:
            provider_str = str(provider)

        # Create cache key
        config_key = f"{provider_str}_{hash(str(sorted(config_overrides.items())))}"

        # Return cached client if available
        if config_key in AIClientFactory._clients:
            return AIClientFactory._clients[config_key]

        try:
            if provider_str == AIProvider.OPENAI.value:
                client = AIClientFactory._create_openai_client(**config_overrides)
            elif provider_str == AIProvider.AZURE_OPENAI.value:
                client = AIClientFactory._create_azure_openai_client(**config_overrides)
            else:
                raise AIClientError(f"Unsupported AI provider: {provider_str}")

            # Validate configuration
            if not client.validate_config():
                raise AIClientError(f"Invalid configuration for provider: {provider_str}")

            # Cache the client
            AIClientFactory._clients[config_key] = client

            logger.info(f"Successfully created AI client for provider: {provider_str}")
            return client

        except Exception as e:
            logger.error(f"Failed to create AI client for provider {provider_str}: {str(e)}")
            raise AIClientError(f"Failed to create AI client: {str(e)}")

    @staticmethod
    def _create_openai_client(**overrides) -> OpenAIClient:
        """Create OpenAI client with environment configuration"""
        config = {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "organization": os.getenv("OPENAI_ORGANIZATION")
        }
        config.update(overrides)

        if not config["api_key"]:
            raise AIClientError("OPENAI_API_KEY environment variable not set")

        return OpenAIClient(**{k: v for k, v in config.items() if v is not None})

    @staticmethod
    def _create_azure_openai_client(**overrides) -> AzureOpenAIClient:
        """Create Azure OpenAI client with environment configuration"""
        config = {
            "api_key": os.getenv("AZURE_OPENAI_KEY"),
            "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "api_version": os.getenv("AZURE_OPENAI_VERSION", "2024-02-01")
        }
        config.update(overrides)

        if not config["api_key"]:
            raise AIClientError("AZURE_OPENAI_KEY environment variable not set")
        if not config["endpoint"]:
            raise AIClientError("AZURE_OPENAI_ENDPOINT environment variable not set")

        return AzureOpenAIClient(**config)

    @staticmethod
    def clear_cache():
        """Clear client cache"""
        AIClientFactory._clients.clear()

# Convenience function for simple usage
def get_ai_client(provider: Union[AIProvider, str] = None) -> AIClientInterface:
    """
    Get AI client instance with default configuration

    Usage:
        client = get_ai_client()
        response = client.chat_completion([{"role": "user", "content": "Hello"}])
    """
    return AIClientFactory.create_client(provider)

# Export main classes and functions
__all__ = [
    "AIProvider",
    "AIResponse",
    "AIUsage",
    "AIClientInterface",
    "OpenAIClient",
    "AzureOpenAIClient",
    "AIClientFactory",
    "AIClientError",
    "get_ai_client"
]