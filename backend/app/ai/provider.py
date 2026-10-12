from abc import ABC, abstractmethod
import json
import logging
import re
from typing import TypeVar, Type, Any, Dict, List, Optional

from app.core.config import settings
from app.ai.exceptions import (
    AIError,
    AIProviderUnavailableError,
    AIRateLimitError,
    AIAnalysisTimeoutError,
    AIResponseFormatError,
)
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
    name: str = "base"

    @abstractmethod
    async def generate_structured(self, prompt: str, schema: Type[T]) -> T:
        pass
        
    @abstractmethod
    async def chat(self, system_prompt: str, messages: List[Dict[str, str]]) -> str:
        pass


class OpenAIProvider(AIProvider):
    name: str = "openai"

    def __init__(self):
        if not OPENAI_AVAILABLE:
            raise AIProviderUnavailableError("OpenAI SDK is not installed in the environment.")
            
        if not settings.AI_API_KEY:
            raise AIProviderUnavailableError("OpenAI API key is missing (AI_API_KEY is not configured).")
            
        self.client = AsyncOpenAI(api_key=settings.AI_API_KEY)
        if settings.AI_BASE_URL:
            self.client.base_url = settings.AI_BASE_URL
        self.model = settings.AI_MODEL or "gpt-4o-mini"

    async def generate_structured(self, prompt: str, schema: Type[T]) -> T:
        try:
            response = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are CloudGuard AI Copilot, a cloud-security expert. "
                            "Output strictly valid JSON matching the requested schema. "
                            "Never modify security scores or rule results."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format=schema,
            )
            parsed = response.choices[0].message.parsed
            if not parsed:
                raise AIResponseFormatError("OpenAI returned empty structured response.")
            return parsed
        except openai.RateLimitError as e:
            logger.error(f"OpenAI Rate Limit: {e}")
            raise AIRateLimitError(f"OpenAI rate limit exceeded: {str(e)}")
        except openai.APITimeoutError as e:
            logger.error(f"OpenAI Timeout: {e}")
            raise AIAnalysisTimeoutError(f"OpenAI request timed out: {str(e)}")
        except (openai.AuthenticationError, openai.APIConnectionError) as e:
            logger.error(f"OpenAI Connection/Auth Error: {e}")
            raise AIProviderUnavailableError(f"OpenAI provider unavailable: {str(e)}")
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
                messages=api_messages,
            )
            return response.choices[0].message.content or ""
        except openai.RateLimitError as e:
            logger.error(f"OpenAI Rate Limit: {e}")
            raise AIRateLimitError(f"OpenAI rate limit exceeded: {str(e)}")
        except openai.APITimeoutError as e:
            logger.error(f"OpenAI Timeout: {e}")
            raise AIAnalysisTimeoutError(f"OpenAI request timed out: {str(e)}")
        except (openai.AuthenticationError, openai.APIConnectionError) as e:
            logger.error(f"OpenAI Connection/Auth Error: {e}")
            raise AIProviderUnavailableError(f"OpenAI provider unavailable: {str(e)}")
        except Exception as e:
            logger.error(f"OpenAI API Error: {str(e)}")
            raise AIProviderUnavailableError(f"OpenAI request failed: {str(e)}")


class MockAIProvider(AIProvider):
    """
    Deterministic Mock AI Provider for automated tests and offline environments.
    Guarantees zero paid API calls, strict adherence to CloudGuard data,
    and prompt injection resistance.
    """
    name: str = "mock"
    
    async def generate_structured(self, prompt: str, schema: Type[T]) -> T:
        if schema == FindingExplanation:
            # Check prompt context for specific finding title/service
            title_match = re.search(r"Finding Title:\s*(.*)", prompt)
            title = title_match.group(1).strip() if title_match else "Security Misconfiguration"
            
            return FindingExplanation(
                summary=f"Analysis of finding '{title}': The resource exhibits configuration that violates security baselines.",
                why_it_matters="Improperly configured resources can allow unauthorized actors to enumerate services, escalate permissions, or access sensitive data.",
                potential_impact="Exposure of internal infrastructure, unauthorized data access, and non-compliance with CIS benchmarks.",
                attack_scenario="An external attacker discovers this configuration and attempts unauthorized access through exposed endpoints or excessive privileges.",
                recommended_actions=[
                    "Inspect the resource in the AWS Console or CloudFormation/Terraform template.",
                    "Apply least-privilege access controls and verify security group ingress rules.",
                    "Enable encryption and audit logging to verify access patterns.",
                ],
                caveats=[
                    "Verify dependent internal systems before restricting traffic or modifying permissions.",
                    "CloudGuard deterministic scanner remains the source of truth for all checks.",
                ]
            )
        elif schema == ScanAISummary:
            # Check if prompt contains score
            score_match = re.search(r"Security Score:\s*(\d+)", prompt)
            score_str = score_match.group(1) if score_match else "N/A"

            return ScanAISummary(
                summary=f"The automated assessment completed with a security score of {score_str}/100. Evaluated configurations were checked against deterministic security rules.",
                key_risks=[
                    "Critical and high-severity misconfigurations on exposed network or storage resources.",
                    "Identity access configurations without multi-factor authentication or least-privilege boundaries.",
                ],
                recommended_actions=[
                    "Prioritize P1 and Critical findings first to immediately improve security posture.",
                    "Restrict unrestricted CIDR (0.0.0.0/0) ingress rules on administrative and database ports.",
                    "Enable default encryption and public access blocks across all storage buckets.",
                ],
                observations=[
                    "Discovered resources span core AWS infrastructure services.",
                    "Deterministic security rules identified actionable posture improvements.",
                ],
                caveats=[
                    "Assessment is scoped to discovered AWS services and active permissions.",
                    "Ensure production dependencies are validated before applying network restrictions.",
                ]
            )
        else:
            raise AIResponseFormatError(f"Mock provider does not support schema: {schema}")
            
    async def chat(self, system_prompt: str, messages: List[Dict[str, str]]) -> str:
        last_msg = messages[-1]["content"] if messages else ""
        msg_lower = last_msg.lower()

        # Check for prompt injection attempts
        if "ignore previous" in msg_lower or "prompt override" in msg_lower or "system instructions" in msg_lower:
            return (
                "**Security Notice:** I operate strictly under CloudGuard security boundaries. "
                "I treat all resource names, tags, and queries as untrusted data and cannot follow prompt overrides or alter scanner results."
            )

        if "critical" in msg_lower or "risk" in msg_lower or "what should i fix" in msg_lower:
            return (
                "### Recommended Remediation Priority\n\n"
                "Based on your CloudGuard assessment data:\n"
                "1. **Address Critical (P1) findings immediately:** Focus on public network exposures (e.g. SSH/RDP open to `0.0.0.0/0`) and publicly accessible S3 buckets.\n"
                "2. **Address High (P2) findings next:** Remediate unencrypted RDS instances and privileged IAM roles.\n"
                "3. **Review Medium/Low issues:** Address logging gaps and missing tags in scheduled maintenance windows.\n\n"
                "CloudGuard's deterministic scanner will recalculate your score upon the next scan."
            )
        elif "score" in msg_lower or "why is my security score" in msg_lower:
            return (
                "### Security Score Explanation\n\n"
                "Your CloudGuard security score is calculated deterministically by the Risk Engine. "
                "Scores decrease based on failed checks weighted by severity (Critical: -20 to -25, High: -10 to -15, Medium: -5). "
                "To increase your score, resolve open Critical and High findings and trigger a new scan."
            )
        elif "s3" in msg_lower:
            return (
                "### S3 Security Guidance\n\n"
                "For AWS S3 buckets:\n"
                "- Ensure **S3 Block Public Access** is enabled at both the bucket and account levels.\n"
                "- Verify **Server-Side Encryption** (AES-256 or AWS KMS) is active by default.\n"
                "- Restrict bucket policies to enforce TLS (`aws:SecureTransport`: true)."
            )
        else:
            return (
                f"### CloudGuard Copilot Guidance\n\n"
                f"You asked: *\"{last_msg}\"*\n\n"
                "CloudGuard Copilot provides advisory analysis based strictly on your deterministic scan results. "
                "I cannot alter scores, modify cloud resources, or invent findings. Please review the Findings Explorer for specific remediation steps."
            )


def get_ai_provider() -> AIProvider:
    """
    Factory resolving the active AI provider based on environment configuration.
    Falls back gracefully to MockAIProvider when AI is disabled or keys are absent.
    """
    if not settings.AI_ENABLED:
        logger.info("AI_ENABLED is False; using MockAIProvider")
        return MockAIProvider()
        
    if settings.AI_PROVIDER.lower() == "openai":
        try:
            return OpenAIProvider()
        except AIProviderUnavailableError as e:
            logger.warning(f"OpenAIProvider unavailable ({e}); falling back to MockAIProvider.")
            return MockAIProvider()
            
    return MockAIProvider()
