'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useCivioStore } from '@/lib/store';
import { api, Issue } from '@/lib/api';
import { 
  AlertTriangle, 
  MapPin, 
  Layers, 
  Clock, 
  Wrench, 
  User, 
  CheckCircle2, 
  TrendingUp, 
  Sparkles, 
  Compass,
  ArrowRight,
  Maximize2
} from 'lucide-react';
import Link from 'next/link';
import dynamic from 'next/dynamic';

const InteractiveMap = dynamic(() => import('@/components/InteractiveMap'), { ssr: false });

export default function LiveMapPage() {
  const queryClient = useQueryClient();
  const {
    currentUser,
    activeWard,
    setActiveWard,
    mapMode,
    setMapMode,
    selectedIssueId,
    setSelectedIssueId,
    activeCategoryFilter,
    setActiveCategoryFilter,
    activeStatusFilter,
    setActiveStatusFilter
  } = useCivioStore();

  const [agentLogs, setAgentLogs] = useState<any[]>([]);
  const [runningAgentId, setRunningAgentId] = useState<string | null>(null);

  // Fetch issues
  const { data: issues = [], isLoading: issuesLoading } = useQuery({
    queryKey: ['issues', activeWard, activeCategoryFilter, activeStatusFilter],
    queryFn: () => api.getIssues({
      ward: activeWard,
      category: activeCategoryFilter || undefined,
      status: activeStatusFilter || undefined
    })
  });

  // Fetch decay forecasts for overlays
  const { data: decayForecasts = [] } = useQuery({
    queryKey: ['decayForecasts'],
    queryFn: () => api.getDecayForecasts()
  });

  // Selected Issue details
  const selectedIssue = issues.find(x => x.id === selectedIssueId);

  // Trigger Autonomous Agent mutation
  const runAgentMutation = useMutation({
    mutationFn: (id: string) => api.triggerAgent(id),
    onSuccess: (_, id) => {
      setRunningAgentId(id);
      setAgentLogs([]);
      
      // Establish SSE connection
      const sseUrl = api.getAgentStatusSSEUrl(id);
      const eventSource = new EventSource(sseUrl);
      
      eventSource.onmessage = (event) => {
        try {
          const log = JSON.parse(event.data);
          setAgentLogs(prev => [...prev, log]);
          if (log.action === 'finish' || log.error) {
            eventSource.close();
            queryClient.invalidateQueries({ queryKey: ['issues'] });
          }
        } catch (e) {
          console.error("SSE parse error", e);
        }
      };
      
      eventSource.onerror = () => {
        eventSource.close();
      };
    }
  });

  // Categories metadata
  const categories = [
    { value: 'POTHOLE', label: 'Potholes', color: '#EF233C' },
    { value: 'WATER_LEAK', label: 'Water Leaks', color: '#14BDBC' },
    { value: 'STREETLIGHT', label: 'Streetlights', color: '#F4A261' },
    { value: 'WASTE', label: 'Garbage/Waste', color: '#52B788' },
    { value: 'ROAD_DAMAGE', label: 'Road Damage', color: '#EF233C' },
    { value: 'ENCROACHMENT', label: 'Footpaths', color: '#F7C59F' },
    { value: 'SEWAGE', label: 'Sewage Lines', color: '#9d4edd' }
  ];

  const wardsList = ["Indiranagar", "Koramangala", "Whitefield", "Jayanagar", "Malleshwaram", "HSR Layout"];

  return (
    <div className="flex-1 flex flex-col md:flex-row overflow-hidden relative select-none">
      
      {/* LEFT SIDEBAR: FILTERS AND WARD STATS */}
      <div className="w-full md:w-80 bg-civic-surface border-r border-civic-border flex flex-col z-10">
        
        {/* Ward Selector & Action Banner */}
        <div className="p-4 border-b border-civic-border bg-civic-surface-2/30">
          <label className="text-xs text-civic-text-muted font-bold block mb-1.5 uppercase tracking-wider">Active Operations Ward</label>
          <select
            value={activeWard}
            onChange={(e) => setActiveWard(e.target.value)}
            className="w-full bg-civic-surface-2 border border-civic-border text-white text-sm font-semibold rounded-lg p-2 focus:outline-none focus:border-civic-teal"
          >
            {wardsList.map(ward => (
              <option key={ward} value={ward}>{ward} Ward</option>
            ))}
          </select>

          <Link href="/report" className="mt-4 w-full bg-civic-coral hover:bg-civic-coral/90 text-white font-bold py-2.5 px-4 rounded-lg flex items-center justify-center space-x-2 text-sm shadow-[0_4px_10px_rgba(231,111,81,0.2)] transition-all">
            <Sparkles size={16} />
            <span>Report Civic Issue</span>
          </Link>
        </div>

        {/* Issue Category Filters */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div>
            <h3 className="text-xs font-bold text-civic-text-muted uppercase tracking-wider mb-2">Category Filters</h3>
            <div className="space-y-1.5">
              <button
                onClick={() => setActiveCategoryFilter(null)}
                className={`w-full flex items-center justify-between text-left text-xs font-semibold px-3 py-2 rounded-lg transition-all ${
                  activeCategoryFilter === null 
                    ? 'bg-civic-teal/20 border border-civic-teal/40 text-civic-teal-light' 
                    : 'bg-civic-surface-2/40 border border-transparent text-civic-text-muted hover:text-white'
                }`}
              >
                <span>All Categories</span>
                <span className="bg-civic-surface-2 text-white px-1.5 py-0.5 rounded text-[10px]">{issues.length}</span>
              </button>
              {categories.map(cat => {
                const count = issues.filter(x => x.category === cat.value).length;
                return (
                  <button
                    key={cat.value}
                    onClick={() => setActiveCategoryFilter(cat.value)}
                    className={`w-full flex items-center justify-between text-left text-xs font-semibold px-3 py-2 rounded-lg border transition-all ${
                      activeCategoryFilter === cat.value 
                        ? 'bg-civic-teal/20 border-civic-teal/40 text-civic-teal-light' 
                        : 'bg-civic-surface-2/40 border-transparent text-civic-text-muted hover:text-white'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: cat.color }} />
                      <span>{cat.label}</span>
                    </div>
                    <span className="bg-civic-surface-2 text-white px-1.5 py-0.5 rounded text-[10px]">{count}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Status Filters */}
          <div>
            <h3 className="text-xs font-bold text-civic-text-muted uppercase tracking-wider mb-2">Status Filters</h3>
            <div className="flex flex-wrap gap-1.5">
              {['REPORTED', 'VERIFIED', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED'].map(st => {
                const isActive = activeStatusFilter === st;
                return (
                  <button
                    key={st}
                    onClick={() => setActiveStatusFilter(isActive ? null : st)}
                    className={`text-[10px] font-bold px-2 py-1 rounded-md border transition-all ${
                      isActive 
                        ? 'bg-white border-white text-civic-navy' 
                        : 'bg-civic-surface-2 text-civic-text-muted border-civic-border hover:text-white'
                    }`}
                  >
                    {st}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Floating Quick Stats */}
        <div className="p-4 border-t border-civic-border bg-civic-surface-2/20 space-y-3">
          <div className="flex justify-between items-center text-xs">
            <span className="text-civic-text-muted flex items-center space-x-1">
              <Clock size={12} className="text-severity-critical" />
              <span>SLA Breached Issues</span>
            </span>
            <span className="font-bold text-severity-critical font-mono">
              {issues.filter(x => x.slaBreached && x.status !== 'RESOLVED').length}
            </span>
          </div>
          <div className="flex justify-between items-center text-xs">
            <span className="text-civic-text-muted flex items-center space-x-1">
              <CheckCircle2 size={12} className="text-severity-low" />
              <span>Resolved Issues</span>
            </span>
            <span className="font-bold text-severity-low font-mono">
              {issues.filter(x => x.status === 'RESOLVED').length}
            </span>
          </div>
        </div>
      </div>

      {/* MAP CANVAS VIEW */}
      <div 
        className="flex-1 relative bg-[#070e17] overflow-hidden"
      >
        {/* Actual Map Canvas Integration */}
        <InteractiveMap 
          issues={issues}
          mapMode={mapMode}
          selectedIssueId={selectedIssueId}
          onSelectIssueId={setSelectedIssueId}
          activeWard={activeWard}
          decayForecasts={decayForecasts}
        />

        {/* Layer Controllers overlay */}
        <div className="absolute top-4 left-4 z-20 flex items-center space-x-2 bg-civic-surface/85 backdrop-blur-md border border-civic-border p-1.5 rounded-lg">
          <button 
            onClick={() => setMapMode('pins')}
            className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              mapMode === 'pins' ? 'bg-civic-teal text-civic-navy' : 'text-civic-text-muted hover:text-white'
            }`}
          >
            <MapPin size={14} />
            <span>Pins</span>
          </button>
          <button 
            onClick={() => setMapMode('heatmap')}
            className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              mapMode === 'heatmap' ? 'bg-civic-teal text-civic-navy' : 'text-civic-text-muted hover:text-white'
            }`}
          >
            <Layers size={14} />
            <span>Heatmap</span>
          </button>
          <button 
            onClick={() => setMapMode('decay')}
            className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              mapMode === 'decay' ? 'bg-civic-teal text-civic-navy' : 'text-civic-text-muted hover:text-white'
            }`}
          >
            <TrendingUp size={14} />
            <span>Decay Overlay</span>
          </button>
        </div>

        {/* Featured Live Banner Overlay */}
        <div className="absolute top-4 right-4 z-20 max-w-[280px] bg-civic-surface/80 backdrop-blur-md border border-civic-teal/20 p-3 rounded-lg shadow-lg flex items-start space-x-2.5">
          <div className="h-6 w-6 rounded bg-civic-teal/20 flex items-center justify-center text-civic-teal-light flex-shrink-0 animate-pulse-glow">
            <Compass size={14} />
          </div>
          <div>
            <h4 className="text-[11px] font-bold text-civic-teal-light uppercase tracking-wider">Predictive Operations Center</h4>
            <p className="text-[10px] text-civic-text-muted mt-0.5 leading-relaxed">
              Gemini monitors SLA targets, auto-escalates breaches, and forecasts road decay in real-time.
            </p>
          </div>
        </div>
      </div>

      {/* RIGHT SIDE DRAWER: SELECTED ISSUE DETAILS */}
      {selectedIssue && (
        <div className="w-full md:w-96 bg-civic-surface border-t md:border-t-0 md:border-l border-civic-border flex flex-col z-20 animate-slide-up md:animate-none">
          
          {/* Header */}
          <div className="p-4 border-b border-civic-border flex justify-between items-center">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold text-civic-text-muted font-mono">{selectedIssue.id}</span>
              <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                selectedIssue.status === 'RESOLVED' 
                  ? 'bg-severity-low/20 text-severity-low border border-severity-low/30' 
                  : selectedIssue.status === 'IN_PROGRESS'
                    ? 'bg-civic-amber/20 text-civic-amber border border-civic-amber/30'
                    : 'bg-civic-teal/20 text-civic-teal border border-civic-teal/30'
              }`}>
                {selectedIssue.status}
              </span>
            </div>
            <button 
              onClick={() => setSelectedIssueId(null)}
              className="text-civic-text-muted hover:text-white text-xs font-semibold"
            >
              Close
            </button>
          </div>

          {/* Details Scroll */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            
            {/* Title & Description */}
            <div>
              <h2 className="text-base font-display font-bold text-white leading-snug">{selectedIssue.title}</h2>
              <p className="text-xs text-civic-text-muted mt-1 leading-relaxed">
                {selectedIssue.description}
              </p>
            </div>

            {/* AI Analysis Box */}
            <div className="bg-civic-surface-2/60 border border-civic-border rounded-lg p-3 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-civic-teal-light font-bold flex items-center space-x-1">
                  <Sparkles size={13} />
                  <span>Gemini Vision Triage</span>
                </span>
                <span className="text-[10px] text-civic-text-muted font-mono">Conf: {selectedIssue.aiAnalysis.confidenceScore}%</span>
              </div>
              
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-civic-navy/40 p-2 rounded border border-civic-border">
                  <span className="text-[10px] text-civic-text-muted block">Severity (1-10)</span>
                  <span className={`font-mono text-sm font-bold ${
                    selectedIssue.aiAnalysis.severityScore >= 8 ? 'text-severity-critical' : 'text-civic-amber'
                  }`}>{selectedIssue.aiAnalysis.severityScore}/10</span>
                </div>
                <div className="bg-civic-navy/40 p-2 rounded border border-civic-border">
                  <span className="text-[10px] text-civic-text-muted block">Safety Risk</span>
                  <span className="font-bold text-white">{selectedIssue.aiAnalysis.safetyRisk}</span>
                </div>
                <div className="bg-civic-navy/40 p-2 rounded border border-civic-border">
                  <span className="text-[10px] text-civic-text-muted block">Estimated Repair</span>
                  <span className="font-bold text-white">₹{selectedIssue.aiAnalysis.estimatedRepairCost.toLocaleString()}</span>
                </div>
                <div className="bg-civic-navy/40 p-2 rounded border border-civic-border">
                  <span className="text-[10px] text-civic-text-muted block">Repair Time</span>
                  <span className="font-bold text-white">{selectedIssue.aiAnalysis.estimatedRepairTime}</span>
                </div>
              </div>
              <div className="text-[11px] leading-relaxed text-civic-text">
                <strong>Technical Assessment:</strong> {selectedIssue.aiAnalysis.geminiDescription}
              </div>
            </div>

            {/* Ward/Address */}
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-civic-border">
                <span className="text-civic-text-muted">Ward</span>
                <span className="font-semibold text-white">{selectedIssue.location.ward}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-civic-border">
                <span className="text-civic-text-muted">Zone</span>
                <span className="font-semibold text-white">{selectedIssue.location.zone}</span>
              </div>
              <div className="py-1">
                <span className="text-civic-text-muted block mb-0.5">Address</span>
                <span className="text-white leading-relaxed">{selectedIssue.location.address}</span>
              </div>
            </div>

            {/* SLA countdown indicator */}
            {selectedIssue.status !== 'RESOLVED' && (
              <div className="bg-severity-critical/10 border border-severity-critical/20 p-3 rounded-lg flex items-center space-x-3 text-xs">
                <Clock size={16} className="text-severity-critical animate-pulse" />
                <div>
                  <span className="text-severity-critical font-bold block">SLA Target Date</span>
                  <span className="text-civic-text-muted font-mono">{new Date(selectedIssue.slaDeadline).toLocaleString()}</span>
                </div>
              </div>
            )}

            {/* Social Interactivity */}
            <div className="flex items-center space-x-2 pt-2">
              <button 
                onClick={async () => {
                  await api.verifyIssue(selectedIssue.id, currentUser.id);
                  queryClient.invalidateQueries({ queryKey: ['issues'] });
                }}
                className="flex-1 bg-civic-surface-2 hover:bg-civic-surface-2/80 border border-civic-border hover:border-civic-teal text-white font-bold py-2 rounded-lg text-xs transition-colors flex items-center justify-center space-x-1"
              >
                <CheckCircle2 size={13} className="text-civic-teal-light" />
                <span>Verify ({selectedIssue.verifiedBy.length})</span>
              </button>
              <button 
                onClick={async () => {
                  await api.upvoteIssue(selectedIssue.id);
                  queryClient.invalidateQueries({ queryKey: ['issues'] });
                }}
                className="bg-civic-surface-2 hover:bg-civic-surface-2/80 border border-civic-border text-white font-bold px-3 py-2 rounded-lg text-xs transition-colors"
              >
                Upvote ({selectedIssue.upvotes})
              </button>
            </div>

            {/* Autonomous Agent Section */}
            {selectedIssue.status === 'REPORTED' && (
              <div className="pt-2 border-t border-civic-border">
                <h3 className="text-xs font-bold text-white mb-2 uppercase tracking-wide flex items-center space-x-1">
                  <Sparkles size={13} className="text-civic-coral" />
                  <span>Agentic Resolution Loop</span>
                </h3>
                <p className="text-[10px] text-civic-text-muted mb-3 leading-relaxed">
                  Trigger the Gemini resolution agent loop. The agent will autonomously route to the correct department, draft the work order, schedule the repair task, and notify the reporter.
                </p>
                <button
                  onClick={() => runAgentMutation.mutate(selectedIssue.id)}
                  disabled={runAgentMutation.isPending}
                  className="w-full bg-civic-coral hover:bg-civic-coral/95 disabled:bg-civic-border text-white font-bold py-2 px-4 rounded-lg text-xs flex items-center justify-center space-x-1 transition-all shadow-md"
                >
                  {runAgentMutation.isPending ? (
                    <span>Running Gemini Agent...</span>
                  ) : (
                    <>
                      <span>Execute Auto-Resolution</span>
                      <ArrowRight size={13} />
                    </>
                  )}
                </button>
              </div>
            )}

            {/* SSE LOG STREAM LOGGER */}
            {runningAgentId === selectedIssue.id && agentLogs.length > 0 && (
              <div className="bg-black/80 border border-civic-teal/30 rounded-lg p-3 space-y-2 mt-3 font-mono text-[10px] max-h-48 overflow-y-auto">
                <div className="text-civic-teal-light font-bold flex justify-between items-center">
                  <span>AGENT REASONING LOG</span>
                  <span className="h-1.5 w-1.5 rounded-full bg-civic-teal-light animate-ping" />
                </div>
                {agentLogs.map((log, index) => (
                  <div key={index} className="border-b border-white/5 pb-1.5 last:border-0">
                    <span className="text-civic-coral font-bold">[Step {log.step}]</span>{' '}
                    <span className="text-white font-bold">{log.action}</span>
                    <p className="text-civic-text-muted mt-0.5 leading-normal italic">
                      "{log.thought}"
                    </p>
                    <p className="text-civic-teal-light mt-0.5 font-bold">
                      &gt; {log.output}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
