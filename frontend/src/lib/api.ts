const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export interface Issue {
  id: string;
  title: string;
  description: string;
  category: string;
  subcategory: string;
  location: {
    lat: number;
    lng: number;
    address: string;
    ward: string;
    zone: string;
  };
  mediaUrls: string[];
  thumbnailUrl: string;
  aiAnalysis: {
    severityScore: number;
    confidenceScore: number;
    estimatedRepairCost: number;
    estimatedRepairTime: string;
    safetyRisk: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
    structuralDamage: boolean;
    geminiDescription: string;
    duplicateOfId?: string;
    urgencyJustification?: string;
    affectedArea?: string;
    requiredExpertise?: string;
  };
  reportedBy: string;
  verifiedBy: string[];
  upvotes: number;
  communityNotes: string[];
  status: 'REPORTED' | 'VERIFIED' | 'ASSIGNED' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED' | 'DUPLICATE';
  assignedDepartment?: string;
  assignedOfficerId?: string;
  workOrderId?: string;
  reportedAt: string;
  slaDeadline: string;
  resolvedAt?: string;
  slaBreached: boolean;
  reporterTrustScore: number;
  validationScore: number;
  assignedNgo?: string;
}

export interface WorkOrder {
  id: string;
  issueId: string;
  title: string;
  description: string;
  requiredMaterials: string[];
  estimatedCost: number;
  estimatedDuration: string;
  requiredSkills: string[];
  safetyNotes: string;
  department: string;
  assignedTo?: string;
  priority: 'P1' | 'P2' | 'P3' | 'P4';
  scheduledDate?: string;
  completedDate?: string;
  status: 'DRAFT' | 'APPROVED' | 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED';
  createdAt: string;
}

export interface User {
  id: string;
  displayName: string;
  photoURL: string;
  ward: string;
  role: 'CITIZEN' | 'AUTHORITY' | 'ADMIN';
  xp: number;
  level: number;
  badges: string[];
  completedQuests: string[];
  activeQuests: string[];
  issuesReported: number;
  issuesVerified: number;
  trustScore: number;
  dailyStreak: number;
  weeklyPatrols: number;
}

export interface DecayForecast {
  ward: string;
  score: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  maintenanceAgeDays: number;
  contractorFailureRate: number;
  topRiskCategories: string[];
  recommendedActions: string[];
  confidence: number;
  bounds: {
    north: number;
    south: number;
    east: number;
    west: number;
  };
}

export interface AuditLog {
  id: string;
  issueId: string;
  timestamp: string;
  action: string;
  description: string;
}

export const api = {
  // Issues
  async getIssues(filters?: { ward?: string; category?: string; status?: string }): Promise<Issue[]> {
    const params = new URLSearchParams();
    if (filters?.ward) params.append('ward', filters.ward);
    if (filters?.category) params.append('category', filters.category);
    if (filters?.status) params.append('status', filters.status);
    
    const res = await fetch(`${API_BASE_URL}/issues?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch issues');
    return res.json();
  },

  async getIssue(id: string): Promise<Issue> {
    const res = await fetch(`${API_BASE_URL}/issues/${id}`);
    if (!res.ok) throw new Error('Failed to fetch issue details');
    return res.json();
  },

  async triageIssue(imageData: string, lat: number, lng: number, description?: string): Promise<Partial<Issue>> {
    const res = await fetch(`${API_BASE_URL}/issues/triage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ imageData, lat, lng, description }),
    });
    if (!res.ok) throw new Error('AI Triage failed');
    return res.json();
  },

  async createIssue(issueData: Partial<Issue>): Promise<Issue> {
    const res = await fetch(`${API_BASE_URL}/issues`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(issueData),
    });
    if (!res.ok) throw new Error('Failed to submit issue');
    return res.json();
  },

  async verifyIssue(id: string, userId: string): Promise<{ success: boolean; verifiedByCount: number }> {
    const res = await fetch(`${API_BASE_URL}/issues/${id}/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ userId }),
    });
    if (!res.ok) throw new Error('Failed to verify issue');
    return res.json();
  },

  async upvoteIssue(id: string): Promise<{ success: boolean; upvotes: number }> {
    const res = await fetch(`${API_BASE_URL}/issues/${id}/upvote`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to upvote issue');
    return res.json();
  },

  async updateIssueStatus(id: string, status: string): Promise<{ success: boolean; status: string }> {
    const res = await fetch(`${API_BASE_URL}/issues/${id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    if (!res.ok) throw new Error('Failed to update status');
    return res.json();
  },

  // Agent
  async triggerAgent(id: string): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE_URL}/agent/resolve/${id}`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to trigger agent');
    return res.json();
  },

  getAgentStatusSSEUrl(id: string): string {
    return `${API_BASE_URL}/agent/status/${id}`;
  },

  // Intelligence
  async getDecayForecasts(): Promise<DecayForecast[]> {
    const res = await fetch(`${API_BASE_URL}/intelligence/decay`);
    if (!res.ok) throw new Error('Failed to fetch decay forecast');
    return res.json();
  },

  async getSLARiskIssues(): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/intelligence/sla-risk`);
    if (!res.ok) throw new Error('Failed to fetch SLA risk issues');
    return res.json();
  },

  async getBudgetSimulation(ward: string, horizon: number, categories?: string): Promise<{ summary: any; explanation: string }> {
    const params = new URLSearchParams({ ward, horizon: horizon.toString() });
    if (categories) params.append('categories', categories);
    
    const res = await fetch(`${API_BASE_URL}/intelligence/budget?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to simulate budget impact');
    return res.json();
  },

  async getGraphPatterns(): Promise<{ frequentRoads: any[]; contractorAudit: any[] }> {
    const res = await fetch(`${API_BASE_URL}/intelligence/patterns`);
    if (!res.ok) throw new Error('Failed to query knowledge graph patterns');
    return res.json();
  },

  // Gamification
  async getQuests(userId: string): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/gamification/quests?userId=${userId}`);
    if (!res.ok) throw new Error('Failed to fetch quests');
    return res.json();
  },

  async triggerQuestAction(userId: string, action: string, category?: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/gamification/progress`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ userId, action, category }),
    });
    if (!res.ok) throw new Error('Failed to register quest progress');
    return res.json();
  },

  async getLeaderboard(ward?: string): Promise<any[]> {
    const params = new URLSearchParams();
    if (ward) params.append('ward', ward);
    const res = await fetch(`${API_BASE_URL}/gamification/leaderboard?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch leaderboard');
    return res.json();
  },

  // Authority
  async getDashboardData(ward: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/authority/dashboard?ward=${ward}`);
    if (!res.ok) throw new Error('Failed to fetch dashboard data');
    return res.json();
  },

  async getWorkOrders(department?: string): Promise<WorkOrder[]> {
    const url = department ? `${API_BASE_URL}/authority/work-orders?department=${encodeURIComponent(department)}` : `${API_BASE_URL}/authority/work-orders`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch work orders');
    return res.json();
  },

  async approveWorkOrder(workOrderId: string, approvedBy: string): Promise<{ success: boolean }> {
    const res = await fetch(`${API_BASE_URL}/authority/work-orders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workOrderId, approvedBy }),
    });
    if (!res.ok) throw new Error('Failed to approve work order');
    return res.json();
  },

  async getCivicPulseReport(ward: string): Promise<{ ward: string; timestamp: string; reportHtml: string }> {
    const res = await fetch(`${API_BASE_URL}/authority/reports?ward=${ward}`);
    if (!res.ok) throw new Error('Failed to fetch pulse briefing');
    return res.json();
  },

  // Transparency
  async getAccountabilityIndex(): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/transparency/index`);
    if (!res.ok) throw new Error('Failed to fetch accountability index');
    return res.json();
  },

  async getAuditLog(issueId?: string): Promise<AuditLog[]> {
    const url = issueId ? `${API_BASE_URL}/transparency/audit?issueId=${issueId}` : `${API_BASE_URL}/transparency/audit`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch public audit log');
    return res.json();
  },

  // Patrol / Pulse Scan
  async startPatrol(userId: string): Promise<{ success: boolean; sessionId: string }> {
    const res = await fetch(`${API_BASE_URL}/pulse-scan/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ userId }),
    });
    if (!res.ok) throw new Error('Failed to start patrol session');
    return res.json();
  },

  async uploadPatrolFrame(sessionId: string, imageFrame: string, lat: number, lng: number): Promise<{ detected: boolean; issue?: any }> {
    const res = await fetch(`${API_BASE_URL}/pulse-scan/frame`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sessionId, imageFrame, lat, lng }),
    });
    if (!res.ok) throw new Error('Failed to process patrol frame');
    return res.json();
  },

  async endPatrol(sessionId: string): Promise<{ success: boolean; issuesCount: number; detectedIssues: any[] }> {
    const res = await fetch(`${API_BASE_URL}/pulse-scan/end`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sessionId }),
    });
    if (!res.ok) throw new Error('Failed to finalize patrol session');
    return res.json();
  },

  // NGO Dashboard APIs
  async getNgoOpportunities(): Promise<Issue[]> {
    const res = await fetch(`${API_BASE_URL}/ngo/opportunities`);
    if (!res.ok) throw new Error('Failed to fetch NGO opportunities');
    return res.json();
  },

  async commitToOpportunity(issueId: string, ngoId: string): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE_URL}/ngo/commit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ issueId, ngoId }),
    });
    if (!res.ok) throw new Error('Failed to commit to opportunity');
    return res.json();
  },

  async getNgoRecommendations(): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/ngo/recommendations`);
    if (!res.ok) throw new Error('Failed to fetch NGO recommendations');
    return res.json();
  },

  async getDraftComplaint(id: string, citizenName?: string): Promise<{ subject: string; body: string }> {
    const params = new URLSearchParams();
    if (citizenName) params.append('citizenName', citizenName);
    const res = await fetch(`${API_BASE_URL}/transparency/complaint/${id}?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to draft complaint letter');
    return res.json();
  },
};
