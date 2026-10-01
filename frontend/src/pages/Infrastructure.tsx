import React, { useState } from 'react';
import { Infrastructure3D } from '../components/Infrastructure3D';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Server, Database, Shield, Layout, X } from 'lucide-react';

export function Infrastructure() {
  const [selectedNode, setSelectedNode] = useState<any>(null);

  return (
    <div className="h-full flex flex-col animate-in fade-in duration-300">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-content">Infrastructure Map</h1>
        <p className="text-[14px] text-content-secondary mt-1">Interactive 3D visualization of your cloud resources and relationships.</p>
      </div>

      <div className="flex-1 flex flex-col md:flex-row gap-6 min-h-[500px]">
        {/* Main 3D View */}
        <div className="flex-1 relative rounded-xl overflow-hidden shadow-elev-2">
          <Infrastructure3D onNodeSelect={setSelectedNode} selectedNodeId={selectedNode?.id || null} />
        </div>

        {/* Details Panel */}
        {selectedNode ? (
          <Card className="w-full md:w-80 flex flex-col animate-in slide-in-from-right-8 duration-300">
            <div className="flex items-center justify-between mb-6 pb-4 border-b border-line">
              <div className="flex items-center gap-3">
                <div 
                  className="w-10 h-10 rounded-lg flex items-center justify-center shadow-sm"
                  style={{ backgroundColor: `${selectedNode.color}20`, border: `1px solid ${selectedNode.color}50` }}
                >
                  <Server className="w-5 h-5" style={{ color: selectedNode.color }} />
                </div>
                <div>
                  <h3 className="font-bold text-content text-[15px]">{selectedNode.label}</h3>
                  <div className="text-[11px] font-bold uppercase tracking-wider text-content-muted mt-0.5">{selectedNode.type}</div>
                </div>
              </div>
              <button 
                onClick={() => setSelectedNode(null)}
                className="p-1 hover:bg-surface-3 text-content-muted hover:text-content rounded transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-6 flex-1">
              <div>
                <h4 className="text-[12px] font-bold uppercase tracking-wider text-content-secondary mb-3">Resource Info</h4>
                <div className="space-y-3">
                  <div className="flex justify-between text-[13px]">
                    <span className="text-content-muted">Identifier</span>
                    <span className="font-mono text-content">{selectedNode.id}-prod-xyz</span>
                  </div>
                  <div className="flex justify-between text-[13px]">
                    <span className="text-content-muted">Region</span>
                    <span className="text-content">ap-south-1</span>
                  </div>
                  <div className="flex justify-between text-[13px]">
                    <span className="text-content-muted">Status</span>
                    <span className="text-severity-medium font-medium">1 Warning</span>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-[12px] font-bold uppercase tracking-wider text-content-secondary mb-3">Connections</h4>
                <div className="text-[13px] text-content-muted bg-surface-2 p-3 rounded-lg border border-line">
                  Displays connected resources to {selectedNode.label}.
                </div>
              </div>
            </div>

            <div className="mt-6 pt-6 border-t border-line">
              <Button className="w-full">View Details</Button>
            </div>
          </Card>
        ) : (
          <Card className="w-full md:w-80 flex flex-col items-center justify-center text-center p-8 bg-surface-1/50 border-dashed">
            <div className="w-12 h-12 rounded-full bg-surface-3 border border-line flex items-center justify-center mb-4">
              <Layout className="w-5 h-5 text-content-muted" />
            </div>
            <h3 className="text-[15px] font-bold text-content mb-2">No Resource Selected</h3>
            <p className="text-[13px] text-content-secondary">
              Click on any node in the 3D visualization map to view its details and relationships.
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}
