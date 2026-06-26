'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useCivioStore } from '@/lib/store';
import { 
  Award, 
  Sparkles, 
  TrendingUp, 
  Flame, 
  CheckCircle, 
  Trophy, 
  ShieldCheck, 
  User,
  Compass,
  ArrowRight
} from 'lucide-react';
import Link from 'next/link';

export default function QuestsPage() {
  const queryClient = useQueryClient();
  const { currentUser, activeWard } = useCivioStore();
  const [activeTab, setActiveTab] = useState<'QUESTS' | 'LEADERBOARD'>('QUESTS');

  // Fetch active quests
  const { data: quests = [] } = useQuery({
    queryKey: ['quests', currentUser.id],
    queryFn: () => api.getQuests(currentUser.id)
  });

  // Fetch leaderboard
  const { data: leaderboard = [] } = useQuery({
    queryKey: ['leaderboard', activeWard],
    queryFn: () => api.getLeaderboard(activeWard)
  });

  // Fetch user stats
  const { data: userStats = null } = useQuery({
    queryKey: ['userStats', currentUser.id],
    queryFn: async () => {
      const users = await api.getLeaderboard();
      return users.find((x: any) => x.userId === currentUser.id) || null;
    }
  });

  // Trigger quest action mutation (simulate actions like Patrol or Verify for review)
  const actionMutation = useMutation({
    mutationFn: ({ action, category }: { action: string, category?: string }) => 
      api.triggerQuestAction(currentUser.id, action, category),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quests'] });
      queryClient.invalidateQueries({ queryKey: ['leaderboard'] });
      queryClient.invalidateQueries({ queryKey: ['userStats'] });
    }
  });

  // Level progress bar
  const xpCurrent = userStats?.xp || 0;
  const level = userStats?.level || 1;
  const xpNeeded = level * 500;
  const xpPercent = Math.min(100, (xpCurrent / xpNeeded) * 100);

  return (
    <div className="flex-1 p-6 bg-[#070e17] overflow-y-auto space-y-6">
      
      {/* Page Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center space-y-4 md:space-y-0">
        <div>
          <h1 className="text-xl font-display font-extrabold text-white flex items-center space-x-2">
            <Award size={20} className="text-civic-teal-light" />
            <span>CIVIC QUESTS & LEADERBOARDS</span>
          </h1>
          <p className="text-xs text-civic-text-muted mt-0.5">Gamifying citizen participation to drive high-density infrastructure audits.</p>
        </div>

        <div className="flex items-center bg-civic-surface p-1 rounded-lg border border-civic-border">
          <button
            onClick={() => setActiveTab('QUESTS')}
            className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              activeTab === 'QUESTS' ? 'bg-civic-teal text-civic-navy' : 'text-civic-text-muted hover:text-white'
            }`}
          >
            <Compass size={14} />
            <span>Missions</span>
          </button>
          <button
            onClick={() => setActiveTab('LEADERBOARD')}
            className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              activeTab === 'LEADERBOARD' ? 'bg-civic-teal text-civic-navy' : 'text-civic-text-muted hover:text-white'
            }`}
          >
            <Trophy size={14} />
            <span>Leaderboard</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Left Profile stats & Right tab details */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
        
        {/* Left Side: Citizen Profile widget */}
        <div className="bg-civic-surface border border-civic-border rounded-2xl p-5 space-y-5 lg:col-span-1">
          <div className="flex items-center space-x-3">
            <div className="h-12 w-12 rounded-full bg-civic-teal/20 border border-civic-teal flex items-center justify-center text-civic-teal-light font-bold text-lg">
              {currentUser.displayName.charAt(0)}
            </div>
            <div>
              <h3 className="font-bold text-sm text-white">{currentUser.displayName}</h3>
              <span className="text-[10px] text-civic-text-muted block">Citizen level {level}</span>
            </div>
          </div>

          {/* Level Progress */}
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between font-semibold">
              <span className="text-civic-text-muted">Level Progress</span>
              <span className="font-mono text-white">{xpCurrent} / {xpNeeded} XP</span>
            </div>
            <div className="w-full bg-civic-surface-2 rounded-full h-2 overflow-hidden border border-civic-border">
              <div 
                className="bg-civic-teal-light h-full rounded-full transition-all duration-500 shadow-[0_0_8px_rgba(20,189,188,0.5)]" 
                style={{ width: `${xpPercent}%` }}
              />
            </div>
          </div>

          {/* Citizen Stats */}
          <div className="grid grid-cols-2 gap-2 text-center text-xs">
            <div className="bg-civic-surface-2/45 p-2 rounded-lg border border-civic-border">
              <span className="text-[9px] text-civic-text-muted block font-semibold">Audits Filed</span>
              <span className="font-mono font-bold text-white text-sm">{currentUser.id === 'cit_3' ? 32 : 18}</span>
            </div>
            <div className="bg-civic-surface-2/45 p-2 rounded-lg border border-civic-border">
              <span className="text-[9px] text-civic-text-muted block font-semibold">Trust Score</span>
              <span className="font-mono font-bold text-civic-teal-light text-sm">{userStats?.trustScore || 85.0}/100</span>
            </div>
          </div>

          {/* Badges shelves */}
          <div className="space-y-2">
            <span className="text-[10px] text-civic-text-muted font-bold block uppercase tracking-wider">Earned Badges</span>
            <div className="grid grid-cols-3 gap-2">
              {['Pothole Hunter', 'Water Guardian', 'Patrol Pioneer'].map(badge => (
                <div key={badge} className="bg-civic-navy/40 border border-civic-border rounded-lg p-2 flex flex-col items-center justify-center text-center">
                  <Award size={18} className="text-civic-amber mb-1" />
                  <span className="text-[8px] text-white font-semibold truncate max-w-16">{badge}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Patrol Simulator Shortcut */}
          <Link href="/pulse-scan" className="w-full bg-civic-coral hover:bg-civic-coral/90 text-white font-bold py-2.5 px-4 rounded-xl flex items-center justify-center space-x-2 text-xs transition-colors shadow-[0_3px_8px_rgba(231,111,81,0.2)]">
            <Flame size={14} />
            <span>Launch Neighborhood Patrol</span>
          </Link>
        </div>

        {/* Right Side: Quests Grid or Leaderboard rankings */}
        <div className="lg:col-span-3 space-y-4">
          
          {activeTab === 'QUESTS' ? (
            <div className="space-y-4">
              
              {/* Info panel */}
              <div className="bg-civic-surface border border-civic-border p-4 rounded-2xl flex items-start space-x-3 text-xs leading-normal">
                <div className="h-6 w-6 rounded bg-civic-teal/20 text-civic-teal-light flex items-center justify-center flex-shrink-0">
                  <Compass size={14} />
                </div>
                <div>
                  <h4 className="font-bold text-white">Active Auditing Missions</h4>
                  <p className="text-civic-text-muted mt-0.5">
                    Participating in civic quests triggers local data densities, helping Vertex predict decay curves. Completing quests earns badges, XP modifiers, and improves your Citizen Trust rating.
                  </p>
                </div>
              </div>

              {/* Quests Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {quests.map((q: any) => (
                  <div key={q.quest.id} className="bg-civic-surface border border-civic-border rounded-2xl p-4 flex flex-col justify-between space-y-4 hover:border-civic-teal/50 transition-colors">
                    <div>
                      <div className="flex justify-between items-start">
                        <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded ${
                          q.quest.difficulty === 'HARD' ? 'bg-severity-critical/20 text-severity-critical'
                          : q.quest.difficulty === 'MEDIUM' ? 'bg-civic-amber/20 text-civic-amber'
                          : 'bg-severity-low/20 text-severity-low'
                        }`}>{q.quest.difficulty}</span>
                        <span className="text-[10px] text-civic-teal-light font-bold font-mono">+{q.quest.reward.xp} XP</span>
                      </div>
                      <h3 className="font-bold text-sm text-white mt-1.5">{q.quest.title}</h3>
                      <p className="text-xs text-civic-text-muted mt-1 leading-normal">{q.quest.description}</p>
                    </div>

                    {/* Progress tracking */}
                    <div className="space-y-1">
                      <div className="flex justify-between text-[10px] font-semibold text-civic-text-muted">
                        <span>Progress</span>
                        <span>{q.progress} / {q.target}</span>
                      </div>
                      <div className="w-full bg-civic-surface-2 rounded-full h-1.5 overflow-hidden">
                        <div 
                          className="bg-civic-teal h-full rounded-full transition-all duration-300"
                          style={{ width: `${(q.progress / q.target) * 100}%` }}
                        />
                      </div>
                    </div>

                    {/* Simulate completing Quest */}
                    {!q.completed ? (
                      <button
                        onClick={() => actionMutation.mutate({ 
                          action: q.quest.requirements.action, 
                          category: q.quest.requirements.category 
                        })}
                        className="w-full bg-civic-surface-2 hover:bg-civic-surface-2/80 border border-civic-border hover:border-civic-teal text-white font-bold py-1.5 rounded-lg text-[10px] flex items-center justify-center space-x-1 transition-all"
                      >
                        <span>Simulate {q.quest.requirements.action === 'REPORT' ? 'Reporting' : 'Verifying'} Action</span>
                        <ArrowRight size={10} />
                      </button>
                    ) : (
                      <div className="flex items-center space-x-1 text-[10px] text-severity-low font-bold py-1">
                        <CheckCircle size={12} />
                        <span>Completed! Badges awarded.</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>

            </div>
          ) : (
            
            /* LEADERBOARD TABLE */
            <div className="bg-civic-surface border border-civic-border rounded-2xl overflow-hidden shadow-lg">
              
              <div className="p-4 border-b border-civic-border flex justify-between items-center bg-civic-surface-2/20">
                <span className="font-bold text-xs text-white uppercase tracking-wider">Top Citizens: {activeWard} Ward</span>
                <span className="text-[10px] text-civic-text-muted">Weekly reset in 3 days</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-civic-border text-civic-text-muted font-bold text-[10px] uppercase">
                      <th className="p-3 text-center w-12">Rank</th>
                      <th className="p-3">Citizen</th>
                      <th className="p-3">Level</th>
                      <th className="p-3 text-right">XP Points</th>
                      <th className="p-3 text-right">Trust Score</th>
                      <th className="p-3 text-center">Badges</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leaderboard.map((user: any) => (
                      <tr 
                        key={user.userId} 
                        className={`border-b border-civic-border/50 transition-colors hover:bg-civic-surface-2/20 ${
                          user.userId === currentUser.id ? 'bg-civic-teal/5 font-semibold text-civic-teal-light' : 'text-civic-text'
                        }`}
                      >
                        <td className="p-3 text-center font-mono">
                          {user.rank === 1 ? '🥇' : user.rank === 2 ? '🥈' : user.rank === 3 ? '🥉' : user.rank}
                        </td>
                        <td className="p-3 flex items-center space-x-2">
                          <div className="h-6 w-6 rounded-full bg-civic-surface-2 flex items-center justify-center font-bold text-[10px] border border-civic-border">
                            {user.displayName.charAt(0)}
                          </div>
                          <span>{user.displayName}</span>
                        </td>
                        <td className="p-3 font-mono">Lv. {user.level}</td>
                        <td className="p-3 text-right font-mono font-semibold">{user.xp.toLocaleString()} XP</td>
                        <td className="p-3 text-right font-mono text-civic-teal-light">{user.trustScore}/100</td>
                        <td className="p-3 text-center font-mono">{user.badgesCount} 🏆</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

            </div>
          )}

        </div>

      </div>

    </div>
  );
}
