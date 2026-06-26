from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class UserRole(str, Enum):
    CITIZEN = "CITIZEN"
    AUTHORITY = "AUTHORITY"
    ADMIN = "ADMIN"

class CivicUser(BaseModel):
    id: str
    displayName: str
    photoURL: str = ""
    ward: str
    role: UserRole = UserRole.CITIZEN
    
    # Gamification
    xp: int = 0
    level: int = 1
    badges: List[str] = []
    completedQuests: List[str] = []
    activeQuests: List[str] = []
    
    # Stats
    issuesReported: int = 0
    issuesVerified: int = 0
    issuesResolved: int = 0
    
    # Trust
    trustScore: float = 50.0  # 0-100
    reportAccuracyRate: float = 0.0  # percentage
    
    # Streaks
    dailyStreak: int = 0
    weeklyPatrols: int = 0
