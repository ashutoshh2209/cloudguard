import React, { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Sphere, MeshDistortMaterial, Stars, Environment, Float } from '@react-three/drei';
import * as THREE from 'three';

function AnimatedSphere() {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.x = state.clock.getElapsedTime() * 0.1;
      meshRef.current.rotation.y = state.clock.getElapsedTime() * 0.15;
    }
  });

  return (
    <Float speed={2} rotationIntensity={0.5} floatIntensity={1}>
      <Sphere ref={meshRef} args={[1, 64, 64]} scale={1.8}>
        <MeshDistortMaterial
          color="#00d2ff"
          emissive="#3a7bd5"
          emissiveIntensity={0.8}
          envMapIntensity={1}
          clearcoat={1}
          clearcoatRoughness={0.1}
          metalness={0.8}
          roughness={0.2}
          distort={0.4}
          speed={2}
          wireframe={true}
        />
      </Sphere>
    </Float>
  );
}

function GlowingParticles() {
  return (
    <Stars radius={10} depth={50} count={1500} factor={4} saturation={1} fade speed={1.5} />
  );
}

export function Globe3D() {
  return (
    <div className="absolute inset-0 z-0 opacity-40 pointer-events-none mix-blend-screen">
      <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 5]} intensity={1.5} color="#00d2ff" />
        <pointLight position={[-10, -10, -5]} intensity={1} color="#ff2a5f" />
        <AnimatedSphere />
        <GlowingParticles />
        <Environment preset="city" />
      </Canvas>
    </div>
  );
}
