'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, Issue } from '@/lib/api';
import { useCivioStore } from '@/lib/store';
import { 
  ShieldCheck, 
  MapPin, 
  AlertTriangle, 
  Calendar, 
  Compass, 
  Flame, 
  Check, 
  Bookmark, 
  TrendingUp 
} from 'lucide-react';

export default function NgoPortalPage() {
  const queryClient = useQueryClient();
  const { currentUser } = useCivioStore();
  const [activeTab, setActiveTab] = useState<'OPPORTUNITIES' | 'AI_RECOMMENDATIONS'>('OPPORTUNITIES');

  // Query: Get all unresolved opportunities
  const { data: opportunities = [], isLoading: isLoadingOps } = useQuery({
    queryKey: ['ngoOpportunities'],
    queryFn: () => api.getNgoOpportunities(),
  });

  // Query: Get AI recommendations based on decay forecasts
  const { data: recommendations = [], isLoading: isLoadingRecs } = useQuery({
    queryKey: ['ngoRecommendations'],
    queryFn: () => api.getNgoRecommendations(),
  });

  // Mutation: Commit to an opportunity
  const commitMutation = useMutation({
    mutationFn: (issueId: string) => api.commitToOpportunity(issueId, currentUser.displayName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ngoOpportunities'] });
      queryClient.invalidateQueries({ queryKey: ['ngoRecommendations'] });
      alert("✅ You have successfully committed to resolve this issue!");
    },
    onError: (err) => {
      alert("❌ Failed to commit: " + err.message);
    }
  });

  return (
    <div className="flex-1 p-6 bg-[#09150b] overflow-y-auto space-y-6">
      
      {/* Portal Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center space-y-4 md:space-y-0 border-b border-[#2d5a27]/30 pb-4">
        <div>
          <h1 className="text-xl font-display font-extrabold text-[#c8ffc2] flex items-center space-x-2">
            <ShieldCheck size={24} className="text-[#85e378]" />
            <span>NGO COLLABORATIVE PORTAL</span>
          </h1>
          <p className="text-xs text-[#a2cba0] mt-0.5">
            Connecting community organizations with high-priority infrastructure resolution opportunities.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center bg-[#142d17] p-1 rounded-lg border border-[#2d5a27]/40">
          <button
            onClick={() => setActiveTab('OPPORTUNITIES')}
            className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              activeTab === 'OPPORTUNITIES' ? 'bg-[#85e378] text-[#09150b]' : 'text-[#a2cba0] hover:text-white'
            }`}
          >
            <Compass size={14} />
            <span>Opportunities ({opportunities.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('AI_RECOMMENDATIONS')}
            className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              activeTab === 'AI_RECOMMENDATIONS' ? 'bg-[#85e378] text-[#09150b]' : 'text-[#a2cba0] hover:text-white'
            }`}
          >
            <TrendingUp size={14} />
            <span>AI Recommendations ({recommendations.length})</span>
          </button>
        </div>
      </div>

      {/* Opportunities View */}
      {activeTab === 'OPPORTUNITIES' && (
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-[#85e378] tracking-wider uppercase">Open Work Opportunities</h2>
          
          {isLoadingOps ? (
            <div className="text-center py-12 text-[#a2cba0]">Loading opportunities...</div>
          ) : opportunities.length === 0 ? (
            <div className="text-center py-12 bg-[#142d17]/40 border border-[#2d5a27]/20 rounded-lg text-[#a2cba0]">
              No open opportunities found at this moment. All reported issues are assigned or resolved!
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {opportunities.map((opp) => (
                <div key={opp.id} className="bg-[#102413] border border-[#2d5a27]/30 rounded-xl p-5 hover:border-[#85e378]/50 transition-all flex flex-col justify-between">
                  <div className="space-y-3">
                    <div className="flex justify-between items-start">
                      <span className="text-[10px] font-bold bg-[#2d5a27]/40 text-[#85e378] px-2 py-0.5 rounded-full border border-[#2d5a27]/60">
                        {opp.category.replace('_', ' ')}
                      </span>
                      <span className="text-[10px] text-[#a2cba0] flex items-center space-x-1">
                        <Calendar size={10} />
                        <span>{new Date(opp.reportedAt).toLocaleDateString()}</span>
                      </span>
                    </div>

                    <div>
                      <h3 className="font-display font-bold text-white text-base">{opp.title}</h3>
                      <p className="text-xs text-[#a2cba0] mt-1 line-clamp-3">{opp.description}</p>
                    </div>

                    <div className="flex items-center space-x-2 text-xs text-[#a2cba0] bg-[#0c1a0e] p-2.5 rounded-lg border border-[#2d5a27]/10">
                      <MapPin size={14} className="text-[#85e378]" />
                      <span>{opp.location.address} (Ward: {opp.location.ward})</span>
                    </div>

                    {/* Metadata indicators */}
                    <div className="flex space-x-4 text-[11px] text-[#a2cba0] pt-1">
                      <div className="flex items-center space-x-1">
                        <AlertTriangle size={12} className="text-amber-400" />
                        <span>Severity: <strong>{opp.aiAnalysis.severityScore}/10</strong></span>
                      </div>
                      <div>
                        <span>Est. Cost: <strong>₹{opp.aiAnalysis.estimatedRepairCost.toLocaleString()}</strong></span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 pt-4 border-t border-[#2d5a27]/20 flex justify-between items-center">
                    {opp.assignedNgo ? (
                      <span className="text-xs text-[#85e378] flex items-center space-x-1 font-semibold">
                        <Check size={14} />
                        <span>Assigned to {opp.assignedNgo}</span>
                      </span>
                    ) : (
                      <>
                        <span className="text-xs text-amber-300 font-semibold animate-pulse">Needs Deployment</span>
                        <button
                          onClick={() => commitMutation.mutate(opp.id)}
                          disabled={commitMutation.isPending}
                          className="bg-[#85e378] hover:bg-[#a1f396] text-[#09150b] text-xs font-bold px-3 py-1.5 rounded-lg transition-all flex items-center space-x-1"
                        >
                          <Bookmark size={12} />
                          <span>Commit to Project</span>
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* AI Recommendations View */}
      {activeTab === 'AI_RECOMMENDATIONS' && (
        <div className="space-y-6">
          <div>
            <h2 className="text-sm font-semibold text-[#85e378] tracking-wider uppercase flex items-center space-x-1.5">
              <Flame size={16} className="text-orange-400" />
              <span>Decay Risk Ward Recommendations</span>
            </h2>
            <p className="text-xs text-[#a2cba0] mt-1">
              AI prioritizes geographic wards by infrastructure decay risk over the next 30 days. Targeting these locations yields maximum community impact.
            </p>
          </div>

          {isLoadingRecs ? (
            <div className="text-center py-12 text-[#a2cba0]">Analyzing decay risk...</div>
          ) : (
            <div className="space-y-6">
              {recommendations.map((rec: any) => (
                <div key={rec.ward} className="bg-[#102413] border border-[#2d5a27]/30 rounded-xl p-5 space-y-4">
                  
                  {/* Ward Header */}
                  <div className="flex flex-col md:flex-row justify-between items-start md:items-center space-y-2 md:space-y-0">
                    <div className="space-y-1">
                      <h3 className="text-lg font-display font-extrabold text-white">{rec.ward} Ward</h3>
                      <div className="flex items-center space-x-2 text-xs text-[#a2cba0]">
                        <span>Top Risks:</span>
                        {rec.topRisks.map((risk: string) => (
                          <span key={risk} className="bg-[#2d5a27]/30 text-[#85e378] px-2 py-0.5 rounded border border-[#2d5a27]/40 text-[10px]">
                            {risk}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="flex items-center space-x-3 bg-[#0c1a0e] p-2.5 rounded-lg border border-[#2d5a27]/20">
                      <div className="text-right">
                        <span className="text-[10px] text-[#a2cba0] block">Decay Forecast</span>
                        <span className="text-sm font-bold text-white">{rec.decayRiskScore}%</span>
                      </div>
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        rec.riskLevel === 'HIGH' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                      }`}>
                        {rec.riskLevel} RISK
                      </span>
                    </div>
                  </div>

                  {/* Recommendations */}
                  <div className="bg-[#0c1a0e] p-3 rounded-lg border border-[#2d5a27]/20 text-xs">
                    <span className="font-semibold text-[#85e378] block mb-1">Recommended Action:</span>
                    <p className="text-[#a2cba0]">{rec.actions[rec.topRisks[0]] || "Perform preemptive maintenance checks."}</p>
                  </div>

                  {/* Matching Open Issues */}
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold text-white">Matching Issues in {rec.ward} ({rec.matchingIssuesCount}):</h4>
                    {rec.matchingIssuesCount === 0 ? (
                      <p className="text-[11px] text-[#a2cba0] italic">No active reports matching these categories. Ready for proactive survey patrols!</p>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
                        {rec.issues.map((opp: Issue) => (
                          <div key={opp.id} className="bg-[#142d17]/50 border border-[#2d5a27]/20 rounded-lg p-3.5 space-y-2.5 flex flex-col justify-between">
                            <div>
                              <div className="flex justify-between items-center text-[10px]">
                                <span className="text-[#85e378] font-bold">{opp.category}</span>
                                <span className="text-amber-400 font-semibold">Sev: {opp.aiAnalysis.severityScore}</span>
                              </div>
                              <h5 className="font-semibold text-white text-xs mt-1 truncate">{opp.title}</h5>
                              <p className="text-[10px] text-[#a2cba0] line-clamp-2 mt-0.5">{opp.description}</p>
                            </div>
                            <button
                              onClick={() => commitMutation.mutate(opp.id)}
                              className="w-full bg-[#2d5a27] hover:bg-[#3d7a36] text-white text-[10px] font-bold py-1 px-2 rounded transition-all mt-2"
                            >
                              Commit to Project
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                </div>
              ))}
            </div>
          )}
        </div>
      )}

    </div>
  );
}
