'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useCivioStore } from '@/lib/store';
import { 
  Sparkles, 
  MapPin, 
  Camera, 
  Check, 
  AlertTriangle, 
  Play, 
  Square,
  ChevronRight,
  ShieldCheck,
  Compass,
  Loader2
} from 'lucide-react';

const MOCK_PATROL_HAZARDS = [
  {
    title: 'Cracked Road Grid',
    category: 'ROAD_DAMAGE',
    subcategory: 'Eroded asphalt grid',
    severityScore: 5,
    safetyRisk: 'MEDIUM',
    estimatedRepairCost: 4000,
    estimatedRepairTime: '2 hours',
    description: 'Auto-detected by scan: Surface cracking with minor subgrade separation.',
    mediaUrl: 'https://images.unsplash.com/photo-1515162305285-0293e4767cc2?q=80&w=300'
  },
  {
    title: 'Overflowing Pavement Dumpster',
    category: 'WASTE',
    subcategory: 'Overflowing domestic dumpster',
    severityScore: 6,
    safetyRisk: 'MEDIUM',
    estimatedRepairCost: 2000,
    estimatedRepairTime: '1 hour',
    description: 'Auto-detected by scan: Garbage overflowing onto pedestrian sidewalk.',
    mediaUrl: 'https://images.unsplash.com/photo-1530587191325-3db32d826c18?q=80&w=300'
  },
  {
    title: 'Broken Pole Streetlight',
    category: 'STREETLIGHT',
    subcategory: 'Damaged mercury light pole',
    severityScore: 8,
    safetyRisk: 'HIGH',
    estimatedRepairCost: 8000,
    estimatedRepairTime: '4 hours',
    description: 'Auto-detected by scan: Pole bent at 30 degrees, wiring exposed.',
    mediaUrl: 'https://images.unsplash.com/photo-1508138221679-760a23a2285b?q=80&w=300'
  }
];

export default function PulseScanPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { currentUser } = useCivioStore();

  const [patrolState, setPatrolState] = useState<'IDLE' | 'PATROLLING' | 'REVIEW'>('IDLE');
  const [patrolTime, setPatrolTime] = useState(0);
  const [capturedFramesCount, setCapturedFramesCount] = useState(0);
  const [detectedIssues, setDetectedIssues] = useState<any[]>([]);
  const [approvedIssues, setApprovedIssues] = useState<string[]>([]);
  
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const patrolSessionId = useRef<string | null>(null);

  // GPS Tracking coordinates simulation
  const [currentCoords, setCurrentCoords] = useState({ lat: 12.9718, lng: 77.6411 });

  // Bulk submit mutation
  const bulkSubmitMutation = useMutation({
    mutationFn: async (issuesToSubmit: any[]) => {
      const promises = issuesToSubmit.map(issue => {
        const payload = {
          title: issue.title,
          description: issue.description,
          category: issue.category,
          subcategory: issue.subcategory,
          location: {
            lat: issue.location.lat,
            lng: issue.location.lng,
            address: issue.location.address,
            ward: 'Indiranagar',
            zone: 'East Zone'
          },
          aiAnalysis: {
            severityScore: issue.severityScore,
            confidenceScore: 0.88,
            estimatedRepairCost: issue.estimatedRepairCost,
            estimatedRepairTime: issue.estimatedRepairTime,
            safetyRisk: issue.safetyRisk,
            structuralDamage: issue.severityScore >= 8,
            geminiDescription: issue.description
          },
          reportedBy: currentUser.id,
          mediaUrls: [issue.mediaUrl],
          thumbnailUrl: issue.mediaUrl
        };
        return api.createIssue(payload);
      });
      return Promise.all(promises);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['issues'] });
      // Award special quest patrol bonus
      api.triggerQuestAction(currentUser.id, 'PATROL');
      router.push('/quests');
    }
  });

  // Start patrol handler
  const startPatrol = async () => {
    try {
      const res = await api.startPatrol(currentUser.id);
      patrolSessionId.current = res.sessionId;
      setPatrolState('PATROLLING');
      setPatrolTime(0);
      setCapturedFramesCount(0);
      setDetectedIssues([]);
      
      // Coordinate shift simulation interval
      timerRef.current = setInterval(() => {
        setPatrolTime(prev => {
          const nextTime = prev + 1;
          
          // Move GPS coordinates slightly to simulate walking
          setCurrentCoords(c => ({
            lat: c.lat + 0.00015 * Math.sin(nextTime / 5),
            lng: c.lng + 0.00015 * Math.cos(nextTime / 5)
          }));

          // Trigger frame captures every 8 seconds
          if (nextTime % 8 === 0 && capturedFramesCount < 3) {
            captureFrame();
          }

          // Stop after 25 seconds for a fast mock demo experience
          if (nextTime >= 24) {
            endPatrol();
          }

          return nextTime;
        });
      }, 1000);
    } catch (e) {
      console.error(e);
    }
  };

  // Simulate capturing frame and triaging via Gemini
  const captureFrame = () => {
    setCapturedFramesCount(count => {
      const nextCount = count + 1;
      
      // Fetch mock hazard that aligns with the capture index
      const mockHazard = MOCK_PATROL_HAZARDS[nextCount - 1];
      if (mockHazard) {
        setDetectedIssues(prev => [
          ...prev, 
          {
            ...mockHazard,
            id: `DET-${nextCount}`,
            location: {
              lat: currentCoords.lat,
              lng: currentCoords.lng,
              address: `Indiranagar 100ft Road Corridor, frame #${nextCount}`
            }
          }
        ]);
        setApprovedIssues(prev => [...prev, `DET-${nextCount}`]);
      }
      return nextCount;
    });
  };

  const endPatrol = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    setPatrolState('REVIEW');
  };

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const toggleApprove = (id: string) => {
    setApprovedIssues(prev => 
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleBulkSubmit = () => {
    const selected = detectedIssues.filter(x => approvedIssues.includes(x.id));
    bulkSubmitMutation.mutate(selected);
  };

  return (
    <div className="flex-1 flex flex-col justify-center items-center p-4 bg-[#070e17]">
      <div className="w-full max-w-lg bg-civic-surface border border-civic-border rounded-2xl overflow-hidden shadow-2xl flex flex-col min-h-[480px]">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-civic-border bg-civic-surface-2/30 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <Compass size={16} className="text-civic-coral" />
            <h1 className="font-display font-bold text-white text-sm">Neighbourhood Pulse Scan</h1>
          </div>
          {patrolState === 'PATROLLING' && (
            <span className="text-xs text-severity-critical font-bold flex items-center space-x-1 animate-pulse">
              <span className="h-2 w-2 rounded-full bg-severity-critical inline-block" />
              <span>ACTIVE SCAN: {patrolTime}s</span>
            </span>
          )}
        </div>

        {/* IDLE SCREEN: START PATROL */}
        {patrolState === 'IDLE' && (
          <div className="p-8 space-y-6 flex-1 flex flex-col justify-center text-center">
            <div className="mx-auto h-16 w-16 bg-civic-coral/20 border border-civic-coral/30 text-civic-coral rounded-full flex items-center justify-center animate-pulse-glow">
              <Compass size={32} />
            </div>
            <div className="space-y-2">
              <h2 className="text-base font-bold text-white">Interactive Mobile Patrol</h2>
              <p className="text-xs text-civic-text-muted leading-relaxed">
                Walk your block with camera active. The platform silently polls frames every 8 seconds, triaging community hazards autonomously via Gemini Vision.
              </p>
            </div>

            <button
              onClick={startPatrol}
              className="w-full bg-civic-teal hover:bg-civic-teal/95 text-civic-navy font-bold py-3 px-6 rounded-xl flex items-center justify-center space-x-2 text-sm transition-all"
            >
              <Play size={18} fill="currentColor" />
              <span>Begin Walk Audit</span>
            </button>
          </div>
        )}

        {/* PATROLLING SCREEN */}
        {patrolState === 'PATROLLING' && (
          <div className="p-6 space-y-6 flex-1 flex flex-col justify-between">
            
            {/* Camera Viewfinder overlay */}
            <div className="relative h-48 w-full bg-black rounded-xl border border-civic-border overflow-hidden flex flex-col items-center justify-center">
              <div className="absolute inset-0 grid grid-cols-4 grid-rows-4 border border-white/5 opacity-10 pointer-events-none">
                {Array.from({ length: 16 }).map((_, i) => (
                  <div key={i} className="border-r border-b border-white/20" />
                ))}
              </div>
              
              {/* Walker coordinates mock */}
              <div className="absolute top-2 left-2 bg-black/60 border border-civic-border px-2 py-0.5 rounded text-[8px] font-mono text-civic-text-muted">
                WALKER POS: {currentCoords.lat.toFixed(5)}, {currentCoords.lng.toFixed(5)}
              </div>

              {/* Ping flashing frame capture */}
              {patrolTime % 8 >= 7 && (
                <div className="absolute inset-0 bg-white/20 flex items-center justify-center animate-ping text-xs font-bold text-white uppercase">
                  Capturing Frame
                </div>
              )}

              <Camera size={32} className="text-civic-text-muted animate-pulse" />
              <span className="text-[9px] text-civic-text-muted mt-2 uppercase tracking-widest font-mono">Silent Camera Frame Grab active</span>
            </div>

            {/* AI scan log details */}
            <div className="bg-[#09121d] rounded-xl border border-civic-border p-3.5 space-y-2 text-[10px] font-mono flex-1 overflow-y-auto max-h-36">
              <div className="text-civic-teal-light font-bold">BACKGROUND SCAN MATRIX:</div>
              <div className="text-civic-text-muted">&gt; Patrol session established: {patrolSessionId.current}</div>
              <div className="text-civic-text-muted">&gt; Walking Corridor, 100ft road GPS ping verified.</div>
              {detectedIssues.map((issue, i) => (
                <div key={i} className="text-civic-coral font-semibold animate-pulse">
                  &gt; Frame #{i+1} capture triaged: {issue.category} hazard detected (Severity: {issue.severityScore}/10)
                </div>
              ))}
              {patrolTime % 8 < 3 && patrolTime > 0 && (
                <div className="text-civic-text-muted animate-pulse">
                  &gt; Analysing frame metadata...
                </div>
              )}
            </div>

            <button
              onClick={endPatrol}
              className="w-full bg-severity-critical hover:bg-severity-critical/90 text-white font-bold py-3 px-6 rounded-xl flex items-center justify-center space-x-2 text-sm transition-all"
            >
              <Square size={16} fill="currentColor" />
              <span>Complete Walk Patrol</span>
            </button>
          </div>
        )}

        {/* REVIEW AND BULK SUBMIT */}
        {patrolState === 'REVIEW' && (
          <div className="p-6 space-y-6 flex-1 flex flex-col max-h-[500px] overflow-y-auto">
            <div className="text-center space-y-1">
              <h2 className="text-base font-bold text-white flex items-center justify-center space-x-1.5">
                <Sparkles size={18} className="text-civic-teal-light" />
                <span>Patrol Audit Findings ({detectedIssues.length})</span>
              </h2>
              <p className="text-xs text-civic-text-muted">Review Gemini Vision detections. Approve hazards to bulk submit.</p>
            </div>

            {/* Detected grid list */}
            <div className="space-y-3">
              {detectedIssues.map((issue) => {
                const isApproved = approvedIssues.includes(issue.id);
                return (
                  <div 
                    key={issue.id} 
                    onClick={() => toggleApprove(issue.id)}
                    className={`flex items-center space-x-3 bg-civic-surface-2/45 border p-3 rounded-xl cursor-pointer transition-all ${
                      isApproved ? 'border-civic-teal ring-1 ring-civic-teal/50' : 'border-civic-border opacity-60'
                    }`}
                  >
                    {/* Thumbnail */}
                    <div 
                      className="h-12 w-12 rounded-lg bg-cover bg-center flex-shrink-0"
                      style={{ backgroundImage: `url(${issue.mediaUrl})` }}
                    />

                    {/* Meta */}
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-center text-[10px] text-civic-text-muted">
                        <span className="font-bold text-civic-teal-light">{issue.category}</span>
                        <span className="font-mono text-severity-critical">Sev: {issue.severityScore}</span>
                      </div>
                      <h4 className="font-bold text-xs text-white truncate mt-0.5">{issue.title}</h4>
                      <p className="text-[10px] text-civic-text-muted truncate mt-0.5">{issue.description}</p>
                    </div>

                    {/* Toggle check */}
                    <div className={`h-5 w-5 rounded-full flex items-center justify-center border transition-colors ${
                      isApproved ? 'bg-civic-teal border-civic-teal text-civic-navy font-bold' : 'border-civic-border'
                    }`}>
                      {isApproved && <Check size={12} />}
                    </div>
                  </div>
                );
              })}
            </div>

            <button
              onClick={handleBulkSubmit}
              disabled={bulkSubmitMutation.isPending || approvedIssues.length === 0}
              className="w-full bg-civic-coral hover:bg-civic-coral/95 disabled:bg-civic-border text-white font-bold py-3 px-6 rounded-xl flex items-center justify-center space-x-2 text-sm transition-all"
            >
              {bulkSubmitMutation.isPending ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Filing bulk reports...</span>
                </>
              ) : (
                <>
                  <Check size={18} />
                  <span>Submit {approvedIssues.length} Audited Issues</span>
                </>
              )}
            </button>
          </div>
        )}

      </div>
    </div>
  );
}
