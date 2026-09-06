from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from enum import Enum

class Priority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"

class CategoryScore(BaseModel):
    score: int
    findings: int
    critical: int = 0
    high: int = 0
    status: str
