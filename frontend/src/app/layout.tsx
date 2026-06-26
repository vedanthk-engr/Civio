'use client';

import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useCivioStore, DEMO_USERS } from '@/lib/store';
import { Map, ShieldAlert, Award, FileText, Database, Shield } from 'lucide-react';
import './globals.css';

const queryClient = new QueryClient();

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { currentUser, setCurrentUser } = useCivioStore();

  const navItems = [
    { label: 'Live Map', href: '/', icon: Map },
    { label: 'Civic Quests', href: '/quests', icon: Award },
    { label: 'Transparency', href: '/transparency', icon: FileText }
  ];

  // Authority only views
  const authorityNavItems = [
    { label: 'Command Center', href: '/authority/command', icon: ShieldAlert },
    { label: 'AI Intelligence', href: '/authority/intelligence', icon: Database }
  ];

  // NGO only views
  const ngoNavItems = [
    { label: 'NGO Portal', href: '/ngo', icon: ShieldAlert }
  ];

  return (
    <html lang="en">
      <body className="bg-civic-navy text-civic-text font-body min-h-screen flex flex-col antialiased">
        <QueryClientProvider client={queryClient}>
          {/* Global Navigation Header */}
          <header className="bg-civic-surface border-b border-civic-border h-16 sticky top-0 z-50 px-4 md:px-8 flex items-center justify-between">
            {/* Logo */}
            <div className="flex items-center space-x-3">
              <div className="h-9 w-9 rounded-lg bg-civic-teal flex items-center justify-center text-civic-navy font-bold text-lg shadow-[0_0_10px_rgba(20,189,188,0.5)]">
                C
              </div>
              <span className="font-display font-extrabold text-xl tracking-tight text-white">
                CIVIO<span className="text-civic-teal-light font-medium text-xs ml-1">v1.0</span>
              </span>
            </div>

            {/* Navigation Links */}
            <nav className="hidden md:flex items-center space-x-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                      isActive
                        ? 'bg-civic-teal text-civic-navy shadow-[0_0_8px_rgba(20,189,188,0.4)]'
                        : 'text-civic-text-muted hover:text-white hover:bg-civic-surface-2'
                    }`}
                  >
                    <Icon size={16} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
              
              {/* Show authority routes if role matches */}
              {currentUser.role === 'AUTHORITY' && (
                <>
                  <div className="h-6 w-[1px] bg-civic-border mx-2" />
                  {authorityNavItems.map((item) => {
                    const Icon = item.icon;
                    const isActive = pathname === item.href;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                          isActive
                            ? 'bg-civic-coral text-white shadow-[0_0_8px_rgba(231,111,81,0.4)]'
                            : 'text-civic-text-muted hover:text-white hover:bg-civic-surface-2'
                        }`}
                      >
                        <Icon size={16} />
                        <span>{item.label}</span>
                      </Link>
                    );
                  })}
                </>
              )}

              {/* Show NGO routes if role matches */}
              {currentUser.role === 'NGO' && (
                <>
                  <div className="h-6 w-[1px] bg-civic-border mx-2" />
                  {ngoNavItems.map((item) => {
                    const Icon = item.icon;
                    const isActive = pathname === item.href;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                          isActive
                            ? 'bg-[#2d5a27] text-white shadow-[0_0_8px_rgba(45,90,39,0.4)]'
                            : 'text-civic-text-muted hover:text-white hover:bg-civic-surface-2'
                        }`}
                      >
                        <Icon size={16} />
                        <span>{item.label}</span>
                      </Link>
                    );
                  })}
                </>
              )}
            </nav>

            {/* Right Side: Demo Mode Dropdown Switcher */}
            <div className="flex items-center space-x-3">
              {currentUser.role === 'AUTHORITY' && (
                <span className="hidden lg:flex items-center space-x-1 text-xs bg-civic-coral/20 text-civic-coral border border-civic-coral/30 px-2 py-1 rounded-md font-semibold animate-pulse-glow">
                  <Shield size={12} />
                  <span>Ops Mode</span>
                </span>
              )}
              {currentUser.role === 'NGO' && (
                <span className="hidden lg:flex items-center space-x-1 text-xs bg-[#2d5a27]/20 text-[#85e378] border border-[#2d5a27]/30 px-2 py-1 rounded-md font-semibold">
                  <Shield size={12} />
                  <span>NGO Mode</span>
                </span>
              )}
              
              <div className="flex flex-col text-right">
                <span className="text-xs text-civic-text-muted">Demo Mode</span>
                <select
                  value={currentUser.id}
                  onChange={(e) => {
                    const selected = DEMO_USERS.find(u => u.id === e.target.value);
                    if (selected) setCurrentUser(selected);
                  }}
                  className="bg-civic-surface-2 border border-civic-border text-white text-xs font-semibold rounded-md p-1.5 focus:outline-none focus:border-civic-teal cursor-pointer"
                >
                  {DEMO_USERS.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.displayName}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </header>

          {/* Page Content */}
          <main className="flex-1 flex flex-col relative">
            {children}
          </main>
        </QueryClientProvider>
      </body>
    </html>
  );
}
