from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class SecurityReportBase(BaseModel):
    title: str
    scan_id: str

class SecurityReportCreate(SecurityReportBase):
    pass

class SecurityReportResponse(SecurityReportBase):
    id: str
    report_type: str
    status: str
    
    security_score: Optional[int]
    security_rating: Optional[str]
    
    finding_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    
    resource_count: int
    coverage_percentage: int
    
    generated_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True

class SecurityReportList(BaseModel):
    items: List[SecurityReportResponse]
    total: int
