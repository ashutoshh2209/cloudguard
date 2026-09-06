import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { CopilotDrawer } from './CopilotDrawer';

export function Layout() {
  const [copilotOpen, setCopilotOpen] = useState(false);
  return (
    <div className="flex h-screen bg-canvas text-gray-100 font-sans overflow-hidden selection:bg-blue-500/30">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        <TopBar onOpenCopilot={() => setCopilotOpen(true)} />
        <main className="flex-1 overflow-y-auto">
          <div className="px-4 py-4 md:px-8 md:py-8 max-w-[1400px] mx-auto w-full">
            <Outlet />
          </div>
        </main>
        
        <CopilotDrawer 
          isOpen={copilotOpen} 
          onClose={() => setCopilotOpen(false)} 
        />
      </div>
    </div>
  );
}
