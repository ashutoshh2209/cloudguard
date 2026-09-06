from abc import ABC, abstractmethod
import json
import logging
from typing import TypeVar, Type, Any, Dict, List

from app.core.config import settings
from app.ai.exceptions import AIProviderUnavailableError, AIResponseFormatError
from app.ai.schemas import FindingExplanation, ScanAISummary

try:
    from openai import AsyncOpenAI
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)
T = TypeVar('T')

class AIProvider(ABC):
    @abstractmethod
    async def generate_structured(self, prompt: str, schema: Type[T]) -> T:
        pass
        
    @abstractmethod
    async def chat(self, system_prompt: str, messages: List[Dict[str, str]]) -> str:
        pass


class OpenAIProvider(AIProvider):
    def __init__(self):
        if not OPENAI_AVAILABLE:
            raise AIProviderUnavailableError("OpenAI SDK is not installed.")
            
        if not settings.AI_API_KEY:
            raise AIProviderUnavailableError("OpenAI API key is missing.")
            
        self.client = AsyncOpenAI(api_key=settings.AI_API_KEY)
        if settings.AI_BASE_URL:
            self.client.base_url = settings.AI_BASE_URL
        self.model = settings.AI_MODEL

    async def generate_structured(self, prompt: str, schema: Type[T]) -> T:
        try:
            # Using openai's beta parse for structured outputs if available,
            # otherwise fallback to JSON mode.
            response = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful security assistant that outputs strictly in JSON matching the requested schema."},
                    {"role": "user", "content": prompt}
                ],
                response_format=schema,
            )
            return response.choices[0].message.parsed
        except Exception as e:
            logger.error(f"OpenAI API Error: {str(e)}")
            raise AIProviderUnavailableError(f"OpenAI request failed: {str(e)}")
            
    async def chat(self, system_prompt: str, messages: List[Dict[str, str]]) -> str:
        try:
            api_messages = [{"role": "system", "content": system_prompt}]
            for msg in messages:
                api_messages.append({"role": msg["role"], "content": msg["content"]})
                
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=api_messages
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI API Error: {str(e)}")
            raise AIProviderUnavailableError(f"OpenAI request failed: {str(e)}")


class MockAIProvider(AIProvider):
    """Fallback mock provider for local development without an API key."""
    
    async def generate_structured(self, prompt: str, schema: Type[T]) -> T:
        if schema == FindingExplanation:
            return FindingExplanation(
                summary="[MOCK] This finding indicates a potential misconfiguration that exposes the resource.",
                why_it_matters="[MOCK] Attackers could exploit this to gain unauthorized access or exfiltrate data.",
                attack_scenario="[MOCK] An external actor scanning public IPs could discover this resource.",
                recommended_actions=["[MOCK] Update the configuration to restrict access.", "[MOCK] Review IAM roles."],
                caveats=["[MOCK] AI-generated guidance. Verify changes against your architecture."]
            )
        elif schema == ScanAISummary:
            return ScanAISummary(
                summary="[MOCK] The assessment completed with some critical findings that need attention.",
                key_risks=["[MOCK] Publicly accessible storage", "[MOCK] Over-permissive IAM roles"],
                recommended_actions=["[MOCK] Fix critical issues first", "[MOCK] Review network boundaries"],
                observations=["[MOCK] Resources are generally well-tagged", "[MOCK] Identity management needs improvement"],
                caveats=["[MOCK] AI-generated guidance. Verify changes against your architecture."]
            )
        else:
            raise AIResponseFormatError(f"Mock does not support schema {schema}")
            
    async def chat(self, system_prompt: str, messages: List[Dict[str, str]]) -> str:
        last_msg = messages[-1]["content"] if messages else ""
        return f"[MOCK COPILOT] You asked: '{last_msg}'. This is a mock response because AI is disabled or the API key is missing. Please verify your CloudGuard data directly."


def get_ai_provider() -> AIProvider:
    if not settings.AI_ENABLED:
        logger.info("AI is disabled, using MockAIProvider")
        return MockAIProvider()
        
    if settings.AI_PROVIDER == "openai":
        try:
            return OpenAIProvider()
        except AIProviderUnavailableError as e:
            logger.warning(f"OpenAIProvider initialization failed: {e}. Falling back to MockAIProvider.")
            return MockAIProvider()
            
    logger.warning(f"Unknown AI_PROVIDER '{settings.AI_PROVIDER}'. Falling back to MockAIProvider.")
    return MockAIProvider()
