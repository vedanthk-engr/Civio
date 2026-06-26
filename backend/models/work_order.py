from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class WorkOrderPriority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"

class WorkOrderStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

class WorkOrder(BaseModel):
    id: str
    issueId: str
    title: str
    description: str
    requiredMaterials: List[str] = []
    estimatedCost: float
    estimatedDuration: str
    requiredSkills: List[str] = []
    safetyNotes: str
    department: str
    assignedTo: Optional[str] = None
    priority: WorkOrderPriority = WorkOrderPriority.P4
    scheduledDate: Optional[str] = None
    completedDate: Optional[str] = None
    status: WorkOrderStatus = WorkOrderStatus.DRAFT
    createdAt: str
    approvedBy: Optional[str] = None
