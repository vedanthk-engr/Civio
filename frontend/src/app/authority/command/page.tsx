'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useCivioStore } from '@/lib/store';
import { api, Issue, WorkOrder } from '@/lib/api';
import { 
  Shield, 
  Clock, 
  Wrench, 
  User, 
  TrendingUp, 
  Plus, 
  Check, 
  MapPin, 
  ArrowRight,
  ShieldAlert,
  FolderSync
} from 'lucide-react';

export default function CommandCenterPage() {
  const queryClient = useQueryClient();
  const { activeWard, currentUser } = useCivioStore();
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null);

  // Fetch issues
  const { data: issues = [] } = useQuery({
    queryKey: ['issues', activeWard],
    queryFn: () => api.getIssues({ ward: activeWard })
  });

  // Fetch dashboard stats
  const { data: dashboard = {} } = useQuery({
    queryKey: ['dashboard', activeWard],
    queryFn: () => api.getDashboardData(activeWard)
  });

  // Fetch work orders
  const { data: workOrders = [] } = useQuery({
    queryKey: ['workOrders'],
    queryFn: () => api.getWorkOrders()
  });

  // Approve Work Order mutation
  const approveMutation = useMutation({
    mutationFn: (woId: string) => api.approveWorkOrder(woId, currentUser.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['issues'] });
      queryClient.invalidateQueries({ queryKey: ['workOrders'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    }
  });

  // Transition issue status mutation
  const transitionMutation = useMutation({
    mutationFn: ({ id, status }: { id: string, status: string }) => api.updateIssueStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['issues'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    }
  });

  // Selected issue + active work order
  const selectedIssue = issues.find(x => x.id === selectedIssueId);
  const activeWorkOrder = workOrders.find(wo => wo.issueId === selectedIssueId);

  // Kanban Columns
  const columns = [
    { id: 'REPORTED', title: 'New Reports', color: 'border-t-severity-medium bg-civic-surface/40' },
    { id: 'VERIFIED', title: 'Citizen Verified', color: 'border-t-civic-teal bg-civic-surface/40' },
    { id: 'ASSIGNED', title: 'Assigned / Drafted', color: 'border-t-civic-amber bg-civic-surface/40' },
    { id: 'IN_PROGRESS', title: 'In Repair', color: 'border-t-civic-coral bg-civic-surface/40' },
    { id: 'RESOLVED', title: 'Resolved', color: 'border-t-severity-low bg-civic-surface/40' }
  ];

  // Calculate SLA remaining hours
  const getSLADetails = (deadlineStr: string, isResolved: boolean) => {
    if (isResolved) return { label: 'Resolved within target', isBreached: false, color: 'text-severity-low' };
    
    const deadline = new Date(deadlineStr);
    const now = new Date();
    
    const diffMs = deadline.getTime() - now.getTime();
    const diffHours = diffMs / (1000 * 60 * 60);
    
    if (diffHours < 0) {
      return {
        label: `BREACHED by ${Math.abs(Math.floor(diffHours))}h`,
        isBreached: true,
        color: 'text-severity-critical font-bold'
      };
    } else {
      return {
        label: `${Math.floor(diffHours)}h remaining`,
        isBreached: false,
        color: diffHours < 24 ? 'text-civic-amber font-semibold' : 'text-civic-text-muted'
      };
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      
      {/* Top operational summary stats */}
      <div className="bg-civic-surface border-b border-civic-border p-4 px-6 flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
        <div>
          <h1 className="text-base font-display font-extrabold text-white flex items-center space-x-2">
            <ShieldAlert size={18} className="text-civic-coral" />
            <span>AUTHORITY COMMAND CENTER & KANBAN</span>
          </h1>
          <p className="text-xs text-civic-text-muted mt-0.5">Real-time triage queue and contractor auditing for {activeWard} Ward.</p>
        </div>

        {/* Load indicators for departments */}
        <div className="flex flex-wrap gap-4 items-center">
          {/* Admin CSV Exports */}
          <div className="flex items-center space-x-2 border-r border-civic-border/50 pr-4 mr-2">
            <a 
              href={api.getRealCSVUrl()} 
              download
              className="bg-civic-teal/15 border border-civic-teal/30 hover:bg-civic-teal/25 text-civic-teal-light font-bold py-1.5 px-3 rounded-lg text-[10px] transition-all"
            >
              Export Real CSV
            </a>
            <a 
              href={api.getSpamCSVUrl()} 
              download
              className="bg-civic-coral/15 border border-civic-coral/30 hover:bg-civic-coral/25 text-civic-coral font-bold py-1.5 px-3 rounded-lg text-[10px] transition-all"
            >
              Export Spam CSV
            </a>
          </div>

          {dashboard.departmentWorkloads && Object.entries(dashboard.departmentWorkloads).map(([name, data]: [string, any]) => (
            <div key={name} className="bg-civic-surface-2 border border-civic-border p-2 rounded-lg text-xs min-w-32 flex flex-col justify-between">
              <span className="text-[10px] text-civic-text-muted font-bold truncate max-w-28">{name}</span>
              <div className="flex items-center justify-between mt-1">
                <span className="font-bold text-white font-mono">{data.activeCount} active</span>
                <span className={`text-[8px] font-extrabold px-1 rounded ${
                  data.status === 'CRITICAL' ? 'bg-severity-critical/20 text-severity-critical' : 'bg-severity-low/20 text-severity-low'
                }`}>{data.status}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Kanban Container */}
      <div className="flex-1 overflow-x-auto p-6 flex space-x-4 bg-[#070e17] items-start select-none">
        {columns.map(col => {
          const colIssues = issues.filter(x => x.status === col.id);
          return (
            <div key={col.id} className={`w-72 flex-shrink-0 border-t-2 border-civic-border rounded-xl flex flex-col max-h-[85vh] shadow-lg ${col.color}`}>
              {/* Column Header */}
              <div className="p-3 border-b border-civic-border flex justify-between items-center">
                <span className="font-bold text-xs text-white uppercase tracking-wider">{col.title}</span>
                <span className="bg-civic-surface-2 text-civic-text-muted text-[10px] px-2 py-0.5 rounded font-mono font-bold">
                  {colIssues.length}
                </span>
              </div>

              {/* Column Items */}
              <div className="flex-1 overflow-y-auto p-2 space-y-2">
                {colIssues.length === 0 ? (
                  <div className="text-center py-8 text-[10px] text-civic-text-muted italic">
                    No active issues
                  </div>
                ) : (
                  colIssues.map(issue => {
                    const sla = getSLADetails(issue.slaDeadline, issue.status === 'RESOLVED');
                    return (
                      <div
                        key={issue.id}
                        onClick={() => setSelectedIssueId(issue.id)}
                        className={`bg-civic-surface-2/80 hover:bg-civic-surface-2 border rounded-xl p-3 cursor-pointer transition-all ${
                          selectedIssueId === issue.id 
                            ? 'ring-2 ring-civic-teal shadow-[0_0_8px_rgba(20,189,188,0.3)]' 
                            : sla.isBreached 
                              ? 'border-severity-critical/40 shadow-[0_0_6px_rgba(239,35,60,0.1)] hover:border-severity-critical'
                              : 'border-civic-border hover:border-civic-text-muted'
                        }`}
                      >
                        <div className="flex justify-between items-start">
                          <span className="text-[9px] font-mono text-civic-text-muted">{issue.id}</span>
                          <span className="text-[9px] bg-civic-navy px-1.5 py-0.5 rounded text-civic-teal-light font-bold">
                            Sev: {issue.aiAnalysis.severityScore}
                          </span>
                        </div>
                        <h4 className="font-bold text-xs text-white mt-1.5 leading-snug truncate">{issue.title}</h4>
                        <div className="flex items-center space-x-1 mt-2 text-[10px] text-civic-text-muted">
                          <MapPin size={10} />
                          <span className="truncate max-w-44">{issue.location.address}</span>
                        </div>

                        {/* SLA timer */}
                        <div className="flex items-center justify-between mt-3 pt-2 border-t border-civic-border/40 text-[9px]">
                          <span className="text-[8px] bg-civic-navy text-white px-1 py-0.2 rounded uppercase">
                            {issue.category}
                          </span>
                          <span className={`font-mono flex items-center space-x-0.5 ${sla.color}`}>
                            <Clock size={9} />
                            <span>{sla.label}</span>
                          </span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          );
        })}

        {/* Selected Issue Drawer / Work Order inspector */}
        {selectedIssue && (
          <div className="w-96 flex-shrink-0 bg-civic-surface border border-civic-border rounded-xl flex flex-col max-h-[85vh] shadow-xl animate-slide-up">
            
            {/* Header */}
            <div className="p-3 border-b border-civic-border flex justify-between items-center bg-civic-surface-2/45">
              <h3 className="font-bold text-xs text-white flex items-center space-x-1">
                <Shield size={12} className="text-civic-coral" />
                <span>Ops Dispatch Inspector</span>
              </h3>
              <button 
                onClick={() => setSelectedIssueId(null)}
                className="text-civic-text-muted hover:text-white text-xs"
              >
                Close
              </button>
            </div>

            {/* Info Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              <div>
                <span className="text-[9px] font-mono text-civic-text-muted block">{selectedIssue.id} &bull; {selectedIssue.category}</span>
                <h4 className="font-bold text-sm text-white leading-snug mt-0.5">{selectedIssue.title}</h4>
                <p className="text-xs text-civic-text-muted mt-1 leading-normal">{selectedIssue.description}</p>
              </div>

              {/* Work Order Container */}
              <div className="bg-civic-surface-2/60 border border-civic-border rounded-xl p-3.5 space-y-3">
                <div className="flex items-center justify-between border-b border-civic-border/50 pb-2">
                  <span className="text-xs font-bold text-civic-coral flex items-center space-x-1">
                    <Wrench size={13} />
                    <span>AI Technical Work Order</span>
                  </span>
                  {activeWorkOrder && (
                    <span className={`text-[9px] font-extrabold px-1.5 py-0.5 rounded ${
                      activeWorkOrder.status === 'APPROVED' ? 'bg-severity-low/20 text-severity-low' : 'bg-civic-amber/20 text-civic-amber'
                    }`}>{activeWorkOrder.status}</span>
                  )}
                </div>

                {activeWorkOrder ? (
                  <div className="space-y-3 text-xs">
                    <div>
                      <span className="text-[10px] text-civic-text-muted block">Work Title</span>
                      <span className="font-bold text-white leading-normal">{activeWorkOrder.title}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-civic-text-muted block">Step Instruction</span>
                      <span className="text-civic-text leading-relaxed text-[11px] block mt-0.5">
                        {activeWorkOrder.description}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-civic-text-muted block font-semibold mb-1">Required Materials</span>
                      <div className="flex flex-wrap gap-1">
                        {activeWorkOrder.requiredMaterials.map((mat, i) => (
                          <span key={i} className="text-[9px] bg-civic-navy border border-civic-border px-1.5 py-0.5 rounded text-white font-mono">
                            {mat}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2 pt-1 border-t border-civic-border/30">
                      <div>
                        <span className="text-[9px] text-civic-text-muted block">Est. Materials Cost</span>
                        <span className="font-bold text-white font-mono">₹{activeWorkOrder.estimatedCost.toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-[9px] text-civic-text-muted block">Est. Duration</span>
                        <span className="font-bold text-white">{activeWorkOrder.estimatedDuration}</span>
                      </div>
                    </div>
                    <div className="text-[10px] text-severity-critical/95 leading-normal pt-2 border-t border-civic-border/30">
                      <strong>Safety Precaution:</strong> {activeWorkOrder.safetyNotes}
                    </div>

                    {/* Action buttons */}
                    {activeWorkOrder.status === 'DRAFT' && (
                      <button
                        onClick={() => approveMutation.mutate(activeWorkOrder.id)}
                        disabled={approveMutation.isPending}
                        className="w-full bg-civic-teal text-civic-navy font-bold py-2.5 rounded-lg text-xs mt-3 flex items-center justify-center space-x-1.5 transition-all shadow-[0_3px_8px_rgba(20,189,188,0.25)]"
                      >
                        <Check size={14} />
                        <span>Approve Work Dispatch</span>
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-6 text-[10px] text-civic-text-muted italic">
                    No work order drafted yet for this issue.
                  </div>
                )}
              </div>

              {/* Status Transitions */}
              <div className="space-y-2 border-t border-civic-border pt-4">
                <span className="text-[10px] font-bold text-civic-text-muted block uppercase tracking-wide">Update Operational Status</span>
                <div className="flex flex-wrap gap-1.5">
                  {selectedIssue.status === 'ASSIGNED' && (
                    <button
                      onClick={() => transitionMutation.mutate({ id: selectedIssue.id, status: 'IN_PROGRESS' })}
                      className="bg-civic-coral hover:bg-civic-coral/90 text-white font-bold py-1.5 px-3 rounded text-[10px] flex items-center space-x-1 transition-colors"
                    >
                      <FolderSync size={11} />
                      <span>Dispatch (In-Progress)</span>
                    </button>
                  )}
                  {selectedIssue.status === 'IN_PROGRESS' && (
                    <button
                      onClick={() => transitionMutation.mutate({ id: selectedIssue.id, status: 'RESOLVED' })}
                      className="bg-severity-low hover:bg-severity-low/90 text-white font-bold py-1.5 px-3 rounded text-[10px] flex items-center space-x-1 transition-colors"
                    >
                      <Check size={11} />
                      <span>Complete Work (Resolve)</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
