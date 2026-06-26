from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime

class IssueCategory(str, Enum):
    POTHOLE = "POTHOLE"
    WATER_LEAK = "WATER_LEAK"
    STREETLIGHT = "STREETLIGHT"
    WASTE = "WASTE"
    ROAD_DAMAGE = "ROAD_DAMAGE"
    ENCROACHMENT = "ENCROACHMENT"
    SEWAGE = "SEWAGE"
    OTHER = "OTHER"

class IssueStatus(str, Enum):
    REPORTED = "REPORTED"
    VERIFIED = "VERIFIED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    DUPLICATE = "DUPLICATE"

class SafetyRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class IssueLocation(BaseModel):
    lat: float
    lng: float
    address: str
    ward: str
    zone: str

class AIAnalysis(BaseModel):
    severityScore: int = Field(..., ge=1, le=10)
    confidenceScore: float = Field(..., ge=0.0, le=1.0)
    estimatedRepairCost: int  # in INR
    estimatedRepairTime: str  # e.g., "2-3 hours"
    safetyRisk: SafetyRisk
    structuralDamage: bool
    geminiDescription: str
    duplicateOfId: Optional[str] = None
    urgencyJustification: Optional[str] = None
    affectedArea: Optional[str] = None
    requiredExpertise: Optional[str] = None

class Issue(BaseModel):
    id: str
    title: str
    description: str
    category: IssueCategory
    subcategory: str
    location: IssueLocation
    mediaUrls: List[str] = []
    thumbnailUrl: str = ""
    aiAnalysis: AIAnalysis
    reportedBy: str
    verifiedBy: List[str] = []
    upvotes: int = 0
    communityNotes: List[str] = []
    status: IssueStatus = IssueStatus.REPORTED
    assignedDepartment: Optional[str] = None
    assignedOfficerId: Optional[str] = None
    workOrderId: Optional[str] = None
    reportedAt: str  # ISO string datetime
    slaDeadline: str  # ISO string datetime
    resolvedAt: Optional[str] = None
    slaBreached: bool = False
    reporterTrustScore: float = 50.0
    validationScore: float = 0.0
