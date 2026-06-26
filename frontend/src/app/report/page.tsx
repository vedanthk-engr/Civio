'use client';

import React, { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCivioStore } from '@/lib/store';
import { api, Issue } from '@/lib/api';
import { 
  Camera, 
  MapPin, 
  Sparkles, 
  Mic, 
  MicOff, 
  Check, 
  ArrowLeft, 
  ArrowRight, 
  RefreshCw,
  Loader2
} from 'lucide-react';

const MOCK_IMAGES = [
  { url: 'https://images.unsplash.com/photo-1515162305285-0293e4767cc2?q=80&w=600', label: 'Severe Road Pothole' },
  { url: 'https://images.unsplash.com/photo-1508138221679-760a23a2285b?q=80&w=600', label: 'Clogged Sewage Leakage' },
  { url: 'https://images.unsplash.com/photo-1558981806-ec527fa84c39?q=80&w=600', label: 'Broken Lighting Pole' }
];

export default function ReportWizardPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { currentUser } = useCivioStore();

  const [step, setStep] = useState(1);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [coordinates, setCoordinates] = useState({ lat: 12.971897, lng: 77.641151 }); // defaults to Indiranagar
  const [description, setDescription] = useState('');
  
  // Voice recording simulation states
  const [isRecording, setIsRecording] = useState(false);
  const [voiceText, setVoiceText] = useState('');
  
  // Triage details from Gemini
  const [triageData, setTriageData] = useState<any | null>(null);

  // Trigger Gemini Triage
  const triageMutation = useMutation({
    mutationFn: () => {
      // Send base64 image or a mock URL from MOCK_IMAGES
      const img = capturedImage || MOCK_IMAGES[0].url;
      return api.triageIssue(img, coordinates.lat, coordinates.lng, description);
    },
    onSuccess: (data) => {
      setTriageData(data);
      setStep(3);
    }
  });

  // Submit Issue
  const submitMutation = useMutation({
    mutationFn: (finalData: any) => api.createIssue(finalData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['issues'] });
      // Award quest progress for citizen!
      api.triggerQuestAction(currentUser.id, 'REPORT', triageData?.category);
      router.push('/');
    }
  });

  // Voice recording simulation
  const startRecording = () => {
    setIsRecording(true);
    setVoiceText('Recording...');
    setTimeout(() => {
      const texts = [
        "Deep pothole near Indiranagar Metro pillar 132, causing bikes to slip.",
        "Major water leak from pavement joint, clean water flowing on roads.",
        "Electrical box is open and hanging, wires are exposed. Streetlights are dark."
      ];
      const selectedText = texts[Math.floor(Math.random() * texts.length)];
      setVoiceText(selectedText);
      setDescription(selectedText);
      setIsRecording(false);
    }, 3000);
  };

  const handleCapture = () => {
    // For local convenience, we select a random mock infrastructure failure image
    const randomImg = MOCK_IMAGES[Math.floor(Math.random() * MOCK_IMAGES.length)].url;
    setCapturedImage(randomImg);
    setStep(2);
  };

  const handleTriageConfirm = () => {
    if (!triageData) return;
    
    // Package final model values
    const finalIssue = {
      title: triageData.title,
      description: description || triageData.subcategory,
      category: triageData.category,
      subcategory: triageData.subcategory,
      location: triageData.location,
      aiAnalysis: triageData.aiAnalysis,
      reportedBy: currentUser.id,
      mediaUrls: [capturedImage || MOCK_IMAGES[0].url],
      thumbnailUrl: capturedImage || MOCK_IMAGES[0].url
    };

    submitMutation.mutate(finalIssue);
  };

  return (
    <div className="flex-1 flex flex-col justify-center items-center p-4 bg-[#070e17]">
      <div className="w-full max-w-lg bg-civic-surface border border-civic-border rounded-2xl overflow-hidden shadow-2xl flex flex-col">
        
        {/* Wizard Steps indicator */}
        <div className="px-6 py-4 border-b border-civic-border bg-civic-surface-2/30 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <button 
              onClick={() => step > 1 ? setStep(step - 1) : router.push('/')}
              className="text-civic-text-muted hover:text-white p-1"
            >
              <ArrowLeft size={16} />
            </button>
            <h1 className="font-display font-bold text-white text-sm">Report Community Issue</h1>
          </div>
          <span className="text-xs text-civic-teal-light font-mono font-bold">Step {step} of 4</span>
        </div>

        {/* STEP 1: CAPTURE MEDIA */}
        {step === 1 && (
          <div className="p-6 space-y-6 flex-1 flex flex-col justify-center">
            <div className="text-center space-y-2">
              <h2 className="text-base font-bold text-white">Capture Infrastructure Damage</h2>
              <p className="text-xs text-civic-text-muted">Take a photo of the pothole, water leak, or broken streetlight.</p>
            </div>

            {/* Camera View mockup */}
            <div className="relative h-64 w-full bg-black rounded-xl border border-civic-border overflow-hidden flex flex-col items-center justify-center group">
              <div className="absolute inset-0 grid grid-cols-3 grid-rows-3 border border-white/10 opacity-20 pointer-events-none">
                {Array.from({ length: 9 }).map((_, i) => (
                  <div key={i} className="border-r border-b border-white/20" />
                ))}
              </div>
              <Camera size={44} className="text-civic-text-muted group-hover:text-civic-teal-light transition-colors duration-200" />
              <span className="text-[10px] text-civic-text-muted mt-2 font-mono">Camera Viewfinder ready</span>
            </div>

            <button
              onClick={handleCapture}
              className="w-full bg-civic-coral hover:bg-civic-coral/95 text-white font-bold py-3 px-6 rounded-xl flex items-center justify-center space-x-2 text-sm transition-all"
            >
              <Camera size={18} />
              <span>Simulate Snapshot</span>
            </button>
          </div>
        )}

        {/* STEP 2: PLACE AR PIN */}
        {step === 2 && (
          <div className="p-6 space-y-6 flex-1 flex flex-col">
            <div className="text-center space-y-2">
              <h2 className="text-base font-bold text-white">Adjust AR Location Pin</h2>
              <p className="text-xs text-civic-text-muted">Drag the map pin to verify the exact coordinates of the issue.</p>
            </div>

            {/* Interactive coordinates locator */}
            <div className="h-48 bg-[#09121d] rounded-xl border border-civic-border overflow-hidden relative flex flex-col justify-center items-center">
              <div className="absolute inset-0 grid grid-cols-6 grid-rows-6 border border-civic-teal/5 opacity-30">
                {Array.from({ length: 36 }).map((_, i) => (
                  <div key={i} className="border-r border-b border-civic-teal/10" />
                ))}
              </div>
              <div className="relative z-10 flex flex-col items-center animate-bounce">
                <MapPin size={32} className="text-severity-critical" />
                <span className="bg-civic-navy text-white text-[9px] font-bold px-1.5 py-0.5 rounded border border-civic-border mt-1">
                  GPS Position
                </span>
              </div>
              <div className="absolute bottom-2 right-2 bg-civic-surface/90 border border-civic-border p-1.5 rounded text-[9px] font-mono text-civic-text-muted">
                Lat: {coordinates.lat.toFixed(5)}, Lng: {coordinates.lng.toFixed(5)}
              </div>
            </div>

            {/* Custom description text or simulated voice */}
            <div className="space-y-3">
              <label className="text-xs font-bold text-civic-text-muted block">Tell us what's wrong (optional voice memo)</label>
              <div className="flex items-center space-x-2">
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Broken pavement flooding street..."
                  className="flex-1 bg-civic-surface-2 border border-civic-border text-white text-xs rounded-lg p-2.5 focus:outline-none focus:border-civic-teal"
                />
                <button
                  type="button"
                  onClick={startRecording}
                  disabled={isRecording}
                  className={`p-2.5 rounded-lg border transition-all flex items-center justify-center ${
                    isRecording 
                      ? 'bg-severity-critical/20 border-severity-critical text-severity-critical' 
                      : 'bg-civic-surface-2 border-civic-border text-civic-text-muted hover:text-white'
                  }`}
                >
                  {isRecording ? <MicOff size={16} className="animate-pulse" /> : <Mic size={16} />}
                </button>
              </div>
              {voiceText && (
                <div className="text-[10px] italic text-civic-teal-light font-semibold">
                  Transcript: "{voiceText}"
                </div>
              )}
            </div>

            <button
              onClick={() => triageMutation.mutate()}
              disabled={triageMutation.isPending}
              className="w-full bg-civic-teal hover:bg-civic-teal/95 disabled:bg-civic-border text-civic-navy font-bold py-3 px-6 rounded-xl flex items-center justify-center space-x-2 text-sm transition-all"
            >
              {triageMutation.isPending ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  <span>Gemini Triaging Photo...</span>
                </>
              ) : (
                <>
                  <Sparkles size={18} />
                  <span>Execute AI Triage</span>
                </>
              )}
            </button>
          </div>
        )}

        {/* STEP 3: CONFIRM AI ASSESSMENT */}
        {step === 3 && triageData && (
          <div className="p-6 space-y-6 flex-1 flex flex-col overflow-y-auto max-h-[460px]">
            <div className="text-center space-y-2">
              <h2 className="text-base font-bold text-white flex items-center justify-center space-x-1.5">
                <Sparkles size={18} className="text-civic-teal-light animate-pulse" />
                <span>AI Diagnostics Completed</span>
              </h2>
              <p className="text-xs text-civic-text-muted">Gemini Vision analyzed your photo. Verify details before submission.</p>
            </div>

            {/* Photo preview */}
            <div 
              className="h-32 w-full bg-cover bg-center rounded-xl border border-civic-border"
              style={{ backgroundImage: `url(${capturedImage || MOCK_IMAGES[0].url})` }}
            />

            {/* Diagnostic Fields */}
            <div className="space-y-3">
              <div className="bg-civic-surface-2/60 border border-civic-border rounded-xl p-3.5 space-y-3">
                <div className="flex justify-between py-1 border-b border-civic-border text-xs">
                  <span className="text-civic-text-muted">Detected Category</span>
                  <span className="font-bold text-white">{triageData.category}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-civic-border text-xs">
                  <span className="text-civic-text-muted">Specific Hazard</span>
                  <span className="font-bold text-white text-right">{triageData.subcategory}</span>
                </div>
                
                <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                  <div className="bg-civic-navy/40 p-2 rounded border border-civic-border">
                    <span className="text-[10px] text-civic-text-muted block font-semibold">Severity Rating</span>
                    <span className="font-mono text-sm font-bold text-severity-critical">{triageData.aiAnalysis.severityScore}/10</span>
                  </div>
                  <div className="bg-civic-navy/40 p-2 rounded border border-civic-border">
                    <span className="text-[10px] text-civic-text-muted block font-semibold">Safety Danger</span>
                    <span className="font-bold text-white">{triageData.aiAnalysis.safetyRisk}</span>
                  </div>
                  <div className="bg-civic-navy/40 p-2 rounded border border-civic-border">
                    <span className="text-[10px] text-civic-text-muted block font-semibold">Est. Repair Cost</span>
                    <span className="font-bold text-white">₹{triageData.aiAnalysis.estimatedRepairCost.toLocaleString()}</span>
                  </div>
                  <div className="bg-civic-navy/40 p-2 rounded border border-civic-border">
                    <span className="text-[10px] text-civic-text-muted block font-semibold">Resolution Window</span>
                    <span className="font-bold text-white">{triageData.aiAnalysis.estimatedRepairTime}</span>
                  </div>
                </div>

                <div className="text-[11px] text-civic-text leading-relaxed pt-2 border-t border-civic-border">
                  <strong>Technical Summary:</strong> {triageData.aiAnalysis.geminiDescription}
                </div>
              </div>
            </div>

            {/* Submit buttons */}
            <div className="flex items-center space-x-3 pt-2">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="flex-1 bg-civic-surface-2 hover:bg-civic-surface-2/80 border border-civic-border text-white font-bold py-3 rounded-xl text-xs transition-colors flex items-center justify-center space-x-1"
              >
                <RefreshCw size={12} />
                <span>Re-Triage</span>
              </button>
              <button
                type="button"
                onClick={handleTriageConfirm}
                disabled={submitMutation.isPending}
                className="flex-1 bg-civic-coral hover:bg-civic-coral/95 disabled:bg-civic-border text-white font-bold py-3 rounded-xl text-xs transition-all flex items-center justify-center space-x-1.5"
              >
                {submitMutation.isPending ? (
                  <span>Submitting...</span>
                ) : (
                  <>
                    <Check size={14} />
                    <span>Confirm & File Report</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
