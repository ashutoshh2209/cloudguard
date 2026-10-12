from pydantic import BaseModel, Field
from typing import List, Optional

class FindingExplanation(BaseModel):
    summary: str = Field(..., description="A concise explanation of what the finding means.")
    why_it_matters: str = Field(..., description="Explanation of the risk and potential business/security impact.")
    potential_impact: Optional[str] = Field(None, description="Potential impact if exploited.")
    attack_scenario: Optional[str] = Field(None, description="A hypothetical attack scenario if applicable.")
    recommended_actions: List[str] = Field(default_factory=list, description="Actionable remediation steps.")
    caveats: List[str] = Field(default_factory=list, description="Important caveats and prerequisites.")

class ScanAISummary(BaseModel):
    summary: str = Field(..., description="Overall executive summary of the scan posture.")
    key_risks: List[str] = Field(default_factory=list, description="The most critical risks identified.")
    recommended_actions: List[str] = Field(default_factory=list, description="Top prioritized actions to improve security score.")
    observations: List[str] = Field(default_factory=list, description="General patterns or observations about the infrastructure.")
    caveats: List[str] = Field(default_factory=list, description="Caveats about the assessment scope.")

class CopilotMessage(BaseModel):
    role: str = Field(..., description="Role of the message sender, 'user' or 'assistant'")
    content: str = Field(..., description="The content of the message")

class CopilotRequest(BaseModel):
    message: str = Field(..., description="The current user question")
    scan_id: Optional[str] = Field(None, description="Optional context: scan ID")
    workspace_id: Optional[str] = Field(None, description="Optional context: workspace ID")
    history: List[CopilotMessage] = Field(default_factory=list, description="Recent conversation history")

class CopilotResponse(BaseModel):
    answer: str = Field(..., description="The AI assistant's response")
    provider: str = Field("mock", description="The underlying AI provider that generated this response")
    scan_id: Optional[str] = Field(None, description="Scan ID context if provided")
    status: str = Field("success", description="Status of the AI Copilot generation")
