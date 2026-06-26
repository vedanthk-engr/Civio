'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useCivioStore } from '@/lib/store';
import { 
  Sparkles, 
  TrendingUp, 
  DollarSign, 
  AlertTriangle, 
  Clock, 
  Compass, 
  Database,
  Users
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  BarChart,
  Bar
} from 'recharts';

// Mock historical trend data
const HISTORICAL_DATA = [
  { name: 'Jul 2025', reported: 45, resolved: 38, decayRisk: 42 },
  { name: 'Aug 2025', reported: 68, resolved: 52, decayRisk: 50 },
  { name: 'Sep 2025', reported: 89, resolved: 70, decayRisk: 61 },
  { name: 'Oct 2025', reported: 72, resolved: 65, decayRisk: 59 },
  { name: 'Nov 2025', reported: 55, resolved: 50, decayRisk: 52 },
  { name: 'Dec 2025', reported: 40, resolved: 48, decayRisk: 48 },
  { name: 'Jan 2026', reported: 32, resolved: 41, decayRisk: 43 },
  { name: 'Feb 2026', reported: 50, resolved: 44, decayRisk: 47 },
  { name: 'Mar 2026', reported: 61, resolved: 58, decayRisk: 52 },
  { name: 'Apr 2026', reported: 78, resolved: 62, decayRisk: 63 },
  { name: 'May 2026', reported: 95, resolved: 71, decayRisk: 72 },
  { name: 'Jun 2026', reported: 110, resolved: 80, decayRisk: 81 }
];

export default function IntelligencePage() {
  const { activeWard, setActiveWard } = useCivioStore();
  const [horizon, setHorizon] = useState(3);
  const [selectedCats, setSelectedCats] = useState<string[]>(['POTHOLE', 'WATER_LEAK', 'SEWAGE']);

  // Fetch decay forecast data
  const { data: decayForecasts = [] } = useQuery({
    queryKey: ['decayForecasts'],
    queryFn: () => api.getDecayForecasts()
  });

  // Fetch budget simulator
  const { data: budgetSim = null, isLoading: budgetLoading } = useQuery({
    queryKey: ['budget', activeWard, horizon, selectedCats.join(',')],
    queryFn: () => api.getBudgetSimulation(activeWard, horizon, selectedCats.join(','))
  });

  // Fetch knowledge graph patterns
  const { data: patterns = { frequentRoads: [], contractorAudit: [] } } = useQuery({
    queryKey: ['patterns'],
    queryFn: () => api.getGraphPatterns()
  });

  const activeDecay = decayForecasts.find(x => x.ward === activeWard);

  const toggleCategory = (cat: string) => {
    setSelectedCats(prev => 
      prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]
    );
  };

  const wardsList = ["Indiranagar", "Koramangala", "Whitefield", "Jayanagar", "Malleshwaram", "HSR Layout"];
  const categoriesList = ['POTHOLE', 'WATER_LEAK', 'STREETLIGHT', 'WASTE', 'ROAD_DAMAGE', 'SEWAGE'];

  return (
    <div className="flex-1 p-6 bg-[#070e17] overflow-y-auto space-y-6">
      
      {/* Page Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center space-y-4 md:space-y-0">
        <div>
          <h1 className="text-xl font-display font-extrabold text-white flex items-center space-x-2">
            <Database size={20} className="text-civic-teal-light" />
            <span>AI INFRASTRUCTURE INTELLIGENCE</span>
          </h1>
          <p className="text-xs text-civic-text-muted mt-0.5">Vertex AI decay predictions and cost impact simulation tools.</p>
        </div>
        
        <div className="flex items-center space-x-2">
          <label className="text-xs text-civic-text-muted font-bold font-mono">Select Ward:</label>
          <select
            value={activeWard}
            onChange={(e) => setActiveWard(e.target.value)}
            className="bg-civic-surface border border-civic-border text-white text-xs font-semibold rounded-lg p-2 focus:outline-none"
          >
            {wardsList.map(ward => (
              <option key={ward} value={ward}>{ward} Ward</option>
            ))}
          </select>
        </div>
      </div>

      {/* Row 1: Decay Score card & Budget Simulator */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Ward Decay Forecast Detail Card */}
        <div className="bg-civic-surface border border-civic-border rounded-2xl p-5 space-y-4">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-[10px] text-civic-teal-light font-bold uppercase tracking-wider block">Decay Prediction</span>
              <h2 className="text-base font-bold text-white mt-0.5">{activeWard} Ward</h2>
            </div>
            {activeDecay && (
              <span className={`text-xs font-extrabold px-2.5 py-1 rounded-full ${
                activeDecay.riskLevel === 'CRITICAL' ? 'bg-severity-critical/20 text-severity-critical animate-pulse-glow'
                : activeDecay.riskLevel === 'HIGH' ? 'bg-severity-high/20 text-severity-high'
                : 'bg-severity-low/20 text-severity-low'
              }`}>
                {activeDecay.riskLevel} RISK
              </span>
            )}
          </div>

          {activeDecay ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between py-2 border-b border-civic-border/50">
                <span className="text-xs text-civic-text-muted">Dynamic Decay Index</span>
                <span className="text-xl font-display font-extrabold text-white font-mono">{activeDecay.score}%</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-civic-border/50">
                <span className="text-xs text-civic-text-muted">Avg Maintenance Age</span>
                <span className="text-xs font-bold text-white">{activeDecay.maintenanceAgeDays} Days</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-civic-border/50">
                <span className="text-xs text-civic-text-muted">Contractor Red-Zone Rate</span>
                <span className="text-xs font-bold text-white">{(activeDecay.contractorFailureRate * 100).toFixed(0)}%</span>
              </div>

              <div>
                <span className="text-[10px] text-civic-text-muted font-bold block mb-1.5 uppercase">Primary Risk Abstractions</span>
                <div className="flex flex-wrap gap-1.5">
                  {activeDecay.topRiskCategories.map((cat, i) => (
                    <span key={i} className="text-[10px] bg-civic-surface-2 border border-civic-border text-white px-2 py-0.5 rounded-md font-semibold">
                      {cat}
                    </span>
                  ))}
                </div>
              </div>

              <div className="bg-civic-surface-2/45 p-3 rounded-lg border border-civic-border/60 text-[10px] text-civic-text leading-relaxed">
                <strong>Recommended Plan:</strong> {activeDecay.recommendedActions[0]}
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-xs text-civic-text-muted italic">
              Calculating decay matrices...
            </div>
          )}
        </div>

        {/* Budget Impact Simulator Container */}
        <div className="bg-civic-surface border border-civic-border rounded-2xl p-5 space-y-4 lg:col-span-2">
          <div>
            <span className="text-[10px] text-civic-coral font-bold uppercase tracking-wider block">Preventative Cost Optimizer</span>
            <h2 className="text-base font-bold text-white mt-0.5">Budget Delay Impact Simulator</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            {/* Input Controls */}
            <div className="space-y-4">
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="text-civic-text-muted">Delay Horizon</span>
                  <span className="font-bold text-white font-mono">{horizon} Months</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="12"
                  value={horizon}
                  onChange={(e) => setHorizon(parseInt(e.target.value))}
                  className="w-full h-1.5 bg-civic-surface-2 rounded-lg appearance-none cursor-pointer accent-civic-coral focus:outline-none"
                />
              </div>

              <div>
                <span className="text-xs text-civic-text-muted block mb-2">Simulate Categories</span>
                <div className="grid grid-cols-3 gap-1.5">
                  {categoriesList.map(cat => {
                    const isChecked = selectedCats.includes(cat);
                    return (
                      <button
                        key={cat}
                        type="button"
                        onClick={() => toggleCategory(cat)}
                        className={`text-[9px] font-bold p-1.5 rounded border transition-colors ${
                          isChecked 
                            ? 'bg-civic-coral/20 border-civic-coral text-white' 
                            : 'bg-civic-surface-2 border-civic-border text-civic-text-muted hover:text-white'
                        }`}
                      >
                        {cat}
                      </button>
                    );
                  })}
                </div>
              </div>

              {budgetSim && (
                <div className="bg-civic-surface-2 border border-civic-border rounded-xl p-3 grid grid-cols-3 gap-2 text-center text-xs">
                  <div>
                    <span className="text-[9px] text-civic-text-muted block">Immediate Repair</span>
                    <span className="font-mono font-bold text-white text-sm">₹{budgetSim.summary.immediate_cost} Cr</span>
                  </div>
                  <div>
                    <span className="text-[9px] text-civic-text-muted block">Deferred Cost</span>
                    <span className="font-mono font-bold text-severity-critical text-sm">₹{budgetSim.summary.deferred_cost} Cr</span>
                  </div>
                  <div>
                    <span className="text-[9px] text-civic-text-muted block">Loss due to delay</span>
                    <span className="font-mono font-bold text-severity-high text-sm">₹{budgetSim.summary.loss} Cr</span>
                  </div>
                </div>
              )}
            </div>

            {/* AI Narrative justification output */}
            <div className="bg-[#09121d] rounded-xl border border-civic-border p-4 flex flex-col justify-between">
              <div className="space-y-1">
                <span className="text-[10px] text-civic-teal-light font-bold uppercase tracking-wider flex items-center space-x-1">
                  <Sparkles size={11} className="animate-pulse" />
                  <span>Gemini Financial Explanation</span>
                </span>
                {budgetLoading ? (
                  <p className="text-xs text-civic-text-muted italic animate-pulse py-2">
                    CFO model analyzing delay depreciation curve...
                  </p>
                ) : (
                  <p className="text-[11px] text-civic-text leading-relaxed mt-1 italic">
                    "{budgetSim?.explanation}"
                  </p>
                )}
              </div>
              <div className="text-[9px] text-civic-text-muted mt-2 border-t border-civic-border/40 pt-2 flex items-center space-x-1">
                <DollarSign size={10} className="text-severity-low" />
                <span>Immediate repairs prevent exponential road subgrade erosion.</span>
              </div>
            </div>

          </div>
        </div>

      </div>

      {/* Row 2: Analytics Trend Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Historical line chart - Recharts */}
        <div className="bg-civic-surface border border-civic-border rounded-2xl p-5 lg:col-span-2 space-y-3">
          <div>
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">Historical Trend Curve</h3>
            <p className="text-[10px] text-civic-text-muted mt-0.5">Comparison of monthly reported issues versus resolution outputs.</p>
          </div>
          <div className="h-64 w-full text-xs">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={HISTORICAL_DATA} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="name" stroke="rgba(255,255,255,0.3)" />
                <YAxis stroke="rgba(255,255,255,0.3)" />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#162840', borderColor: 'rgba(255,255,255,0.1)', color: '#fff' }}
                  itemStyle={{ color: '#fff' }}
                />
                <Legend />
                <Line type="monotone" dataKey="reported" name="Issues Filed" stroke="#E76F51" strokeWidth={2} activeDot={{ r: 6 }} />
                <Line type="monotone" dataKey="resolved" name="Issues Resolved" stroke="#14BDBC" strokeWidth={2} />
                <Line type="monotone" dataKey="decayRisk" name="Decay Index Trend" stroke="#F4A261" strokeWidth={1} strokeDasharray="4 4" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Knowledge Graph analytics indicators */}
        <div className="bg-civic-surface border border-civic-border rounded-2xl p-5 flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">Knowledge Graph Hotspots</h3>
            <p className="text-[10px] text-civic-text-muted mt-0.5">Duplicate failures linked to assets and contractors.</p>
          </div>

          <div className="space-y-4 my-3 flex-1 overflow-y-auto max-h-56 pr-1">
            
            {/* Frequent Roads */}
            <div>
              <span className="text-[9px] text-civic-teal-light font-bold block uppercase tracking-wider mb-1">Top Recurring Failures</span>
              <div className="space-y-1.5">
                {patterns.frequentRoads && patterns.frequentRoads.map((road: any, i: number) => (
                  <div key={i} className="flex justify-between items-center text-xs bg-civic-surface-2/45 border border-civic-border p-2 rounded">
                    <span className="truncate max-w-48 text-white">{road.address}</span>
                    <span className="font-mono text-[10px] font-bold text-severity-critical bg-severity-critical/15 px-1.5 rounded">
                      {road.potholeCount} times
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Contractor Audits */}
            <div>
              <span className="text-[9px] text-civic-coral font-bold block uppercase tracking-wider mb-1">Contractor Audit Logs</span>
              <div className="space-y-1.5">
                {patterns.contractorAudit && patterns.contractorAudit.map((dept: any, i: number) => (
                  <div key={i} className="flex justify-between items-center text-xs bg-civic-surface-2/45 border border-civic-border p-2 rounded">
                    <div className="flex flex-col">
                      <span className="font-semibold text-white truncate max-w-32">{dept.department}</span>
                      <span className="text-[8px] text-civic-text-muted">Assigned: {dept.totalAssigned}</span>
                    </div>
                    <div className="flex items-center space-x-1.5">
                      <span className="font-mono text-[10px] font-bold text-white">Breaches: {dept.slaBreaches}</span>
                      {dept.flaggedForAudit && (
                        <span className="text-[8px] bg-severity-critical/20 text-severity-critical font-bold px-1 rounded animate-pulse">
                          Audit
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>

          <div className="text-[9px] text-civic-text-muted leading-relaxed border-t border-civic-border/40 pt-2 flex items-center space-x-1.5">
            <AlertTriangle size={11} className="text-civic-amber" />
            <span>Multiple issues in same corridor triggers automatic resurfacing ticket.</span>
          </div>
        </div>

      </div>

    </div>
  );
}
