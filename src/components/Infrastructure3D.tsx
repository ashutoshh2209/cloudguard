import React, { useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Sphere, Line, Html, OrbitControls, Environment } from '@react-three/drei';
import * as THREE from 'three';

const NODES = [
  { id: 'aws', label: 'AWS Account', position: [0, 4, 0], color: '#3b82f6', type: 'root' },
  { id: 'vpc', label: 'VPC', position: [0, 2, 0], color: '#60a5fa', type: 'network' },
  { id: 'sg', label: 'Security Group', position: [-2, 0, 0], color: '#f59e0b', type: 'security' },
  { id: 'ec2', label: 'EC2 Instances', position: [-3, -2, 0], color: '#f97316', type: 'compute' },
  { id: 'rds', label: 'RDS Database', position: [-1, -2, 0], color: '#ef4444', type: 'database' },
  { id: 's3', label: 'S3 Buckets', position: [2, 0, -1], color: '#10b981', type: 'storage' },
  { id: 'iam', label: 'IAM Roles', position: [3, 2, 1], color: '#8b5cf6', type: 'identity' },
  { id: 'trail', label: 'CloudTrail', position: [4, 0, 0], color: '#64748b', type: 'monitoring' }
];

const CONNECTIONS = [
  { source: 'aws', target: 'vpc' },
  { source: 'aws', target: 'iam' },
  { source: 'aws', target: 'trail' },
  { source: 'vpc', target: 'sg' },
  { source: 'vpc', target: 's3' },
  { source: 'sg', target: 'ec2' },
  { source: 'sg', target: 'rds' },
];

function Node({ data, isSelected, onClick }: { data: any, isSelected: boolean, onClick: () => void }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHover] = useState(false);

  useFrame((state) => {
    if (meshRef.current && (hovered || isSelected)) {
      meshRef.current.rotation.y += 0.02;
    }
  });

  return (
    <group position={data.position as [number, number, number]}>
      <mesh
        ref={meshRef}
        onClick={(e) => { e.stopPropagation(); onClick(); }}
        onPointerOver={() => setHover(true)}
        onPointerOut={() => setHover(false)}
      >
        <sphereGeometry args={[0.4, 32, 32]} />
        <meshStandardMaterial 
          color={data.color} 
          emissive={data.color}
          emissiveIntensity={hovered || isSelected ? 0.8 : 0.2}
          roughness={0.2}
          metalness={0.8}
        />
      </mesh>
      
      {/* Outer Glow for selection */}
      {isSelected && (
        <mesh>
          <sphereGeometry args={[0.55, 32, 32]} />
          <meshBasicMaterial color={data.color} transparent opacity={0.2} side={THREE.BackSide} />
        </mesh>
      )}

      {/* Label */}
      <Html position={[0, -0.7, 0]} center style={{ pointerEvents: 'none' }}>
        <div className={`px-2 py-1 rounded text-[11px] font-bold tracking-wider whitespace-nowrap transition-colors ${
          isSelected || hovered ? 'bg-surface-2 text-content border border-line shadow-elev-2' : 'text-content-secondary'
        }`}>
          {data.label}
        </div>
      </Html>
    </group>
  );
}

function Edges() {
  return (
    <>
      {CONNECTIONS.map((conn, idx) => {
        const sourceNode = NODES.find(n => n.id === conn.source);
        const targetNode = NODES.find(n => n.id === conn.target);
        if (!sourceNode || !targetNode) return null;
        
        return (
          <Line
            key={idx}
            points={[sourceNode.position as [number, number, number], targetNode.position as [number, number, number]]}
            color="rgba(255,255,255,0.15)"
            lineWidth={1}
            dashed={false}
          />
        );
      })}
    </>
  );
}

interface Infrastructure3DProps {
  onNodeSelect: (node: any) => void;
  selectedNodeId: string | null;
}

export function Infrastructure3D({ onNodeSelect, selectedNodeId }: Infrastructure3DProps) {
  return (
    <div className="w-full h-full bg-canvas/50 rounded-lg border border-line overflow-hidden relative">
      <Canvas camera={{ position: [0, 0, 10], fov: 50 }}>
        <color attach="background" args={['#020617']} />
        <ambientLight intensity={0.4} />
        <directionalLight position={[10, 10, 10]} intensity={1} />
        
        <Edges />
        
        {NODES.map((node) => (
          <Node 
            key={node.id} 
            data={node} 
            isSelected={selectedNodeId === node.id}
            onClick={() => onNodeSelect(node)}
          />
        ))}
        
        <OrbitControls 
          enablePan={true} 
          enableZoom={true} 
          enableRotate={true}
          autoRotate={!selectedNodeId}
          autoRotateSpeed={0.5}
        />
        <Environment preset="city" />
      </Canvas>
      
      {/* Overlay controls hint */}
      <div className="absolute bottom-4 left-4 text-[11px] font-bold text-content-muted uppercase tracking-wider pointer-events-none">
        Drag to rotate • Scroll to zoom
      </div>
    </div>
  );
}
