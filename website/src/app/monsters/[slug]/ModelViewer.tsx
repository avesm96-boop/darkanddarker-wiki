"use client";

import { Suspense, useRef, useEffect, useState, useCallback } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Environment } from "@react-three/drei";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import * as THREE from "three";
import type { ComboPlayback } from "./MonsterDetail";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AnimDef {
  id: string;
  label: string;
  file: string;
  loop: boolean;
}

interface ModelViewerProps {
  modelUrl: string;
  animationsBasePath?: string;
  comboPlayback?: ComboPlayback | null;
  animDefs?: AnimDef[];
  activeAnim?: AnimDef | null;
}

// ---------------------------------------------------------------------------
// Scene
// ---------------------------------------------------------------------------

function Scene({
  modelUrl,
  animationsBasePath,
  activeAnim,
  comboPlayback,
  animDefs,
}: {
  modelUrl: string;
  animationsBasePath: string | undefined;
  activeAnim: AnimDef | null;
  comboPlayback: ComboPlayback | null;
  animDefs: AnimDef[];
}) {
  const mixerRef = useRef<THREE.AnimationMixer | null>(null);
  const clipCache = useRef<Map<string, THREE.AnimationClip>>(new Map());
  const [model, setModel] = useState<THREE.Group | null>(null);
  const controlsRef = useRef<any>(null);
  const comboQueueRef = useRef<string[]>([]);
  const comboCallbackRef = useRef<(() => void) | undefined>(undefined);
  const { camera } = useThree();

  // ── Load model ─────────────────────────────────────────────────────────
  useEffect(() => {
    const loader = new GLTFLoader();
    let cancelled = false;
    loader.load(modelUrl, (gltf) => {
      if (cancelled) return;
      const scene = gltf.scene;
      const box = new THREE.Box3().setFromObject(scene);
      const center = box.getCenter(new THREE.Vector3());
      const size = box.getSize(new THREE.Vector3());
      const scale = 3.5 / Math.max(size.x, size.y, size.z);
      scene.scale.setScalar(scale);
      scene.position.set(-center.x * scale, -box.min.y * scale, -center.z * scale);
      // Clear animation cache when model changes (new skeleton)
      clipCache.current.clear();
      if (mixerRef.current) {
        mixerRef.current.stopAllAction();
        mixerRef.current = null;
      }
      setModel(scene);
    }, undefined, (err) => console.error("[ModelViewer] model load error:", err));
    return () => { cancelled = true; };
  }, [modelUrl]);

  // ── Camera setup ──────────────────────────────────────────────────────
  useEffect(() => {
    if (!model) return;
    const box = new THREE.Box3().setFromObject(model);
    const midY = (box.min.y + box.max.y) / 2;
    camera.position.set(0, midY, 6);
    camera.lookAt(0, midY, 0);
    if (controlsRef.current) {
      controlsRef.current.target.set(0, midY, 0);
      controlsRef.current.update();
    }
  }, [model, camera]);

  // ── AnimationMixer lifecycle ────────────────────────────────────────────
  useEffect(() => {
    if (!model) return;
    mixerRef.current = new THREE.AnimationMixer(model);
    return () => { mixerRef.current?.stopAllAction(); mixerRef.current = null; };
  }, [model]);

  // ── Helper: load clip by animation ID ──────────────────────────────────
  const loadClip = useCallback((animId: string): Promise<THREE.AnimationClip | null> => {
    const cache = clipCache.current;
    if (cache.has(animId)) return Promise.resolve(cache.get(animId)!);

    const def = animDefs.find((d) => d.id === animId);
    if (!def || !animationsBasePath) return Promise.resolve(null);

    return new Promise((resolve) => {
      new GLTFLoader().load(
        `${animationsBasePath}/${def.file}`,
        (gltf) => {
          if (!gltf.animations.length) { resolve(null); return; }
          const clip = gltf.animations[0];
          cache.set(animId, clip);
          resolve(clip);
        },
        undefined,
        () => resolve(null),
      );
    });
  }, [animDefs, animationsBasePath]);

  // ── Play single animation ──────────────────────────────────────────────
  useEffect(() => {
    if (!activeAnim || !animationsBasePath || !mixerRef.current || !model) return;
    const mixer = mixerRef.current;

    const play = (clip: THREE.AnimationClip) => {
      mixer.stopAllAction();
      const action = mixer.clipAction(clip, model);
      action.setLoop(activeAnim.loop ? THREE.LoopRepeat : THREE.LoopOnce, activeAnim.loop ? Infinity : 1);
      action.clampWhenFinished = true;
      action.reset().play();
    };

    loadClip(activeAnim.id).then((clip) => { if (clip) play(clip); });
  }, [activeAnim, animationsBasePath, model, loadClip]);

  useEffect(() => {
    if (!activeAnim) mixerRef.current?.stopAllAction();
  }, [activeAnim]);

  // ── Combo playback: chain animations ───────────────────────────────────
  useEffect(() => {
    if (!comboPlayback || !mixerRef.current || !model) return;
    const mixer = mixerRef.current;

    // Store the queue and callback
    comboQueueRef.current = [...comboPlayback.animations];
    comboCallbackRef.current = comboPlayback.onComplete;

    const playNext = () => {
      const nextId = comboQueueRef.current.shift();
      if (!nextId) {
        comboCallbackRef.current?.();
        return;
      }

      loadClip(nextId).then((clip) => {
        if (!clip) { playNext(); return; }
        mixer.stopAllAction();
        const action = mixer.clipAction(clip, model);
        action.setLoop(THREE.LoopOnce, 1);
        action.clampWhenFinished = true;
        action.reset().play();

        // Listen for animation finish to chain next
        const onFinished = (e: { action: THREE.AnimationAction }) => {
          if (e.action === action) {
            mixer.removeEventListener("finished", onFinished);
            playNext();
          }
        };
        mixer.addEventListener("finished", onFinished);
      });
    };

    playNext();

    return () => {
      comboQueueRef.current = [];
    };
  }, [comboPlayback, model, loadClip]);

  // ── Per-frame: advance mixer ──────────────────────────────────────────
  useFrame((_, delta) => {
    mixerRef.current?.update(delta);
  });

  return (
    <>
      {model && <primitive object={model} />}
      <OrbitControls
        ref={controlsRef}
        enablePan={false}
        enableZoom={true}
        minDistance={1}
        maxDistance={30}
        minPolarAngle={0.05}
        maxPolarAngle={Math.PI * 0.88}
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// ModelViewer
// ---------------------------------------------------------------------------

export default function ModelViewer({ modelUrl, animationsBasePath, comboPlayback, animDefs: externalAnimDefs, activeAnim: externalActiveAnim }: ModelViewerProps) {
  const animDefs = externalAnimDefs ?? [];
  const activeAnim = externalActiveAnim ?? null;

  return (
    <div>
      {/* Viewport — nearly-square aspect ratio */}
      <div style={{
        width: "100%", aspectRatio: "1 / 0.9",
        background: "radial-gradient(ellipse at 50% 60%, #1a2030 0%, #0d0f14 100%)",
        overflow: "hidden", position: "relative",
      }}>
        <Canvas
          camera={{ fov: 40, near: 0.1, far: 200, position: [0, 2, 6] }}
          onCreated={({ gl }) => {
            gl.toneMapping = THREE.ACESFilmicToneMapping;
            gl.toneMappingExposure = 1.6;
          }}
        >
          <Suspense fallback={null}>
            <Environment preset="warehouse" environmentIntensity={0.9} />
          </Suspense>
          <ambientLight intensity={0.4} />
          <directionalLight position={[3, 8, 5]} intensity={1.3} />
          <directionalLight position={[-4, 2, -3]} intensity={0.4} color="#5588bb" />

          <Suspense fallback={null}>
            <Scene
              modelUrl={modelUrl}
              animationsBasePath={animationsBasePath}
              activeAnim={activeAnim}
              comboPlayback={comboPlayback ?? null}
              animDefs={animDefs}
            />
          </Suspense>
        </Canvas>

        <div style={{
          position: "absolute", bottom: "8px", right: "10px",
          fontSize: "0.5625rem", color: "rgba(201,168,76,0.35)",
          fontFamily: "var(--font-heading)", letterSpacing: "0.12em",
          textTransform: "uppercase", pointerEvents: "none",
        }}>
          Drag · Scroll to zoom
        </div>
        {activeAnim && (
          <div style={{
            position: "absolute", top: "10px", left: "12px",
            fontSize: "0.625rem", color: "rgba(201,168,76,0.7)",
            fontFamily: "var(--font-heading)", letterSpacing: "0.18em",
            textTransform: "uppercase", pointerEvents: "none",
          }}>
            {activeAnim.label}
          </div>
        )}
      </div>
    </div>
  );
}
