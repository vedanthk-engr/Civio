'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, AuditLog } from '@/lib/api';
import { 
  FileText, 
  Search, 
  TrendingUp, 
  CheckCircle, 
  AlertTriangle, 
  Clock, 
  Award,
  ChevronDown
} from 'lucide-react';

export default function TransparencyPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [logFilter, setLogFilter] = useState<string | null>(null);
  
  const [advocacyIssueId, setAdvocacyIssueId] = useState('');
  const [citizenName, setCitizenName] = useState('');
  const [complaintLetter, setComplaintLetter] = useState<{ subject: string; body: string } | null>(null);
  const [isDrafting, setIsDrafting] = useState(false);
  const [isSending, setIsSending] = useState(false);

  const handleDraftComplaint = async () => {
    if (!advocacyIssueId) return;
    setIsDrafting(true);
    try {
      const letter = await api.getDraftComplaint(advocacyIssueId, citizenName || undefined);
      setComplaintLetter(letter);
    } catch (err: any) {
      alert("Failed to draft letter: " + err.message);
    } finally {
      setIsDrafting(false);
    }
  };

  const handleSendEmail = async () => {
    if (!advocacyIssueId) return;
    setIsSending(true);
    try {
      const result = await api.sendComplaintEmail(advocacyIssueId, citizenName || undefined);
      if (result.success) {
        alert(`✉️ Complaint dispatched successfully to ${result.recipient} via Resend!`);
      } else {
        alert(`⚠️ Failed to send complaint: ${result.result?.error || 'Resend API Key is not configured in this sandbox environment. Simulating dispatch logs.'}`);
      }
    } catch (err: any) {
      alert("Failed to send complaint: " + err.message);
    } finally {
      setIsSending(false);
    }
  };

  // Fetch ward accountability index
  const { data: indexList = [], isLoading: indexLoading } = useQuery({
    queryKey: ['accountabilityIndex'],
    queryFn: () => api.getAccountabilityIndex()
  });

  // Fetch public audit log
  const { data: auditLog = [] } = useQuery({
    queryKey: ['auditLog'],
    queryFn: () => api.getAuditLog()
  });

  // Filter logs by search term
  const filteredLogs = auditLog.filter((log: AuditLog) => {
    const matchesSearch = log.issueId.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          log.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          log.action.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = logFilter ? log.action.includes(logFilter) : true;
    return matchesSearch && matchesFilter;
  });

  return (
    <div className="flex-1 p-6 bg-[#070e17] overflow-y-auto space-y-6">
      
      {/* Page Header */}
      <div>
        <h1 className="text-xl font-display font-extrabold text-white flex items-center space-x-2">
          <FileText size={20} className="text-civic-teal-light animate-pulse" />
          <span>WARD ACCOUNTABILITY & AUDIT PORTAL</span>
        </h1>
        <p className="text-xs text-civic-text-muted mt-0.5">Public audits of department response times, contractor compliance, and SLA logs.</p>
      </div>

      {/* Row 1: Accountability Cards Grid */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wide">Ward Accountability Ranking Index</h3>
        {indexLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-44 bg-civic-surface rounded-2xl animate-pulse border border-civic-border" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {indexList.map((idxData: any, index: number) => {
              const compliance = idxData.slaComplianceRate;
              const isExcellent = compliance >= 90;
              const isWarning = compliance < 70;
              
              return (
                <div key={idxData.ward} className="bg-civic-surface border border-civic-border rounded-2xl p-5 space-y-3 hover:border-civic-teal/30 transition-colors">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-[10px] text-civic-text-muted font-bold font-mono">RANK #{index + 1}</span>
                      <h4 className="font-bold text-sm text-white mt-0.5">{idxData.ward} Ward</h4>
                    </div>
                    <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded ${
                      idxData.trend === 'IMPROVING' ? 'bg-severity-low/25 text-severity-low' : 'bg-civic-amber/20 text-civic-amber'
                    }`}>{idxData.trend}</span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs py-1 border-t border-b border-civic-border/50">
                    <div>
                      <span className="text-[10px] text-civic-text-muted block">SLA Compliance</span>
                      <span className={`font-mono font-extrabold text-sm ${
                        isExcellent ? 'text-severity-low' : isWarning ? 'text-severity-critical' : 'text-civic-amber'
                      }`}>{compliance}%</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-civic-text-muted block">Avg Resolution</span>
                      <span className="font-mono font-bold text-white text-sm">{idxData.averageResolutionDays} Days</span>
                    </div>
                  </div>

                  <div className="flex justify-between items-center text-xs">
                    <div className="flex items-center space-x-1.5">
                      <span className="text-civic-text-muted">Citizen Rating:</span>
                      <span className="font-bold text-white font-mono">{idxData.citizenSatisfaction} ★</span>
                    </div>
                    <div className="text-right">
                      <span className="text-civic-text-muted block text-[10px]">Open Backlogs</span>
                      <span className="font-mono text-white font-bold">{idxData.openIssuesCount} issues</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Row 2: Public Audit Log */}
      <div className="bg-civic-surface border border-civic-border rounded-2xl p-5 space-y-4">
        
        {/* Log Control Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center space-y-4 md:space-y-0">
          <div>
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">Public Operations Audit Log</h3>
            <p className="text-[10px] text-civic-text-muted mt-0.5">Cryptographically logged audit history of every civic resolution step.</p>
          </div>

          <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
            {/* Search Input */}
            <div className="relative flex-1 md:flex-none">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search audit ledger..."
                className="w-full md:w-60 bg-civic-surface-2 border border-civic-border text-white text-xs rounded-lg pl-8 pr-3 py-2 focus:outline-none focus:border-civic-teal"
              />
              <Search size={14} className="text-civic-text-muted absolute left-2.5 top-2.5" />
            </div>

            {/* Filter tags */}
            <div className="flex gap-1.5 text-[9px] font-bold">
              {['AUTO_ASSIGNED', 'WORK_ORDER_APPROVED', 'STATUS_UPDATED'].map(action => (
                <button
                  key={action}
                  onClick={() => setLogFilter(logFilter === action ? null : action)}
                  className={`px-2 py-1.5 rounded border transition-colors ${
                    logFilter === action 
                      ? 'bg-white border-white text-civic-navy' 
                      : 'bg-civic-surface-2 border-civic-border text-civic-text-muted hover:text-white'
                  }`}
                >
                  {action}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Audit List Table */}
        <div className="border border-civic-border rounded-xl overflow-hidden overflow-y-auto max-h-96">
          <table className="w-full text-left border-collapse text-xs select-none">
            <thead>
              <tr className="border-b border-civic-border text-civic-text-muted font-bold text-[10px] uppercase bg-civic-surface-2/20">
                <th className="p-3 w-32">Timestamp</th>
                <th className="p-3 w-28">Issue ID</th>
                <th className="p-3 w-40">Action Tag</th>
                <th className="p-3">Ledger Description</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="p-8 text-center text-xs text-civic-text-muted italic">
                    No matching audit ledgers found.
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log: AuditLog) => (
                  <tr key={log.id} className="border-b border-civic-border/50 hover:bg-civic-surface-2/15 transition-colors">
                    <td className="p-3 font-mono text-[10px] text-civic-text-muted">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="p-3 font-mono text-[10px] text-civic-teal-light font-bold">
                      {log.issueId}
                    </td>
                    <td className="p-3">
                      <span className={`text-[8px] font-mono font-bold px-1.5 py-0.5 rounded ${
                        log.action.includes('AUTO') ? 'bg-civic-coral/20 text-civic-coral border border-civic-coral/25'
                        : log.action.includes('APPROVED') ? 'bg-severity-low/20 text-severity-low border border-severity-low/25'
                        : 'bg-civic-teal/20 text-civic-teal border border-civic-teal/25'
                      }`}>
                        {log.action}
                      </span>
                    </td>
                    <td className="p-3 text-civic-text leading-relaxed">
                      {log.description}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

      </div>

      {/* Row 3: Citizen Advocacy & Grievance Drafting */}
      <div className="bg-civic-surface border border-civic-border rounded-2xl p-5 space-y-4">
        <div>
          <h3 className="text-xs font-bold text-white uppercase tracking-wider">Citizen Advocacy & Official Grievance Scribe</h3>
          <p className="text-[10px] text-civic-text-muted mt-0.5">Use Gemini 2.0 Flash to draft formal, print-optimized complaint letters directly to Bengaluru municipal authorities.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <div>
            <label className="text-[10px] text-civic-text-muted font-bold block mb-1">Issue Reference ID</label>
            <input
              type="text"
              value={advocacyIssueId}
              onChange={(e) => setAdvocacyIssueId(e.target.value)}
              placeholder="e.g., ISS-FE4501"
              className="w-full bg-civic-surface-2 border border-civic-border text-white text-xs rounded-lg px-3 py-2.5 focus:outline-none focus:border-civic-teal"
            />
          </div>
          <div>
            <label className="text-[10px] text-civic-text-muted font-bold block mb-1">Your Display Name</label>
            <input
              type="text"
              value={citizenName}
              onChange={(e) => setCitizenName(e.target.value)}
              placeholder="e.g., Rohan Sharma"
              className="w-full bg-civic-surface-2 border border-civic-border text-white text-xs rounded-lg px-3 py-2.5 focus:outline-none focus:border-civic-teal"
            />
          </div>
          <button
            onClick={handleDraftComplaint}
            disabled={isDrafting || !advocacyIssueId}
            className="bg-civic-teal hover:bg-civic-teal-light disabled:bg-civic-border disabled:text-civic-text-muted text-civic-navy text-xs font-bold py-2.5 px-4 rounded-lg transition-all"
          >
            {isDrafting ? 'Drafting with Gemini...' : 'Draft Grievance Letter'}
          </button>
        </div>

        {complaintLetter && (
          <div className="mt-6 border border-civic-border bg-white text-gray-900 rounded-xl p-6 md:p-8 space-y-6 shadow-xl max-w-2xl mx-auto font-serif">
            
            {/* Letterhead */}
            <div className="flex justify-between items-start border-b border-gray-200 pb-4 text-xs font-sans text-gray-500">
              <div>
                <span className="font-extrabold text-gray-800 tracking-wider">CIVIO ADVOCACY INITIATIVE</span>
                <span className="block">Automated Scribe Service v1.0</span>
              </div>
              <span className="text-right">Ref: {advocacyIssueId}</span>
            </div>

            {/* Letter Content */}
            <div className="text-sm leading-relaxed whitespace-pre-wrap">
              {complaintLetter.body}
            </div>

            {/* Action buttons */}
            <div className="flex justify-end space-x-3 pt-6 border-t border-gray-100 font-sans text-xs font-bold">
              <button
                onClick={() => {
                  const printContent = complaintLetter.body;
                  const win = window.open('', '', 'width=600,height=600');
                  if (win) {
                    win.document.write(`<pre style="font-family:serif;font-size:14px;white-space:pre-wrap;padding:40px;">${printContent}</pre>`);
                    win.document.close();
                    win.print();
                  }
                }}
                className="bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-lg transition-all"
              >
                Print / Save PDF
              </button>
              <button
                onClick={handleSendEmail}
                disabled={isSending}
                className="bg-civic-teal hover:bg-civic-teal-light disabled:bg-civic-border disabled:text-civic-text-muted text-civic-navy px-4 py-2 rounded-lg transition-all"
              >
                {isSending ? 'Sending...' : 'Email Grievance'}
              </button>
            </div>

          </div>
        )}

      </div>

    </div>
  );
}
