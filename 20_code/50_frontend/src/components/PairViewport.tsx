"use client";

// Pair viewport (user request, M6): both meshed sectors positioned exactly like the combined
// implicit deck (ADR-021 amended — Kleingetriebeprüfstand top view: gear 1 = the stage's
// FIRST gear at the origin, on the LEFT of the default camera; gear 2 at the working centre
// distance on the RIGHT, half-pitch phase), with CO-MOVING coordinate triads at the two
// rotation nodes showing which DOFs the deck locks: DOF 1–5 fixed (gray struts + lock ring),
// DOF 6 free (green rotation arrow on the angle-driven gear, amber on the torque-loaded one).
// The hulls arrive mid-plane-symmetric (z = ±b/2) and each gear can be displaced along its
// rotation axis (parametric axial offset, mirrors the deck's axial_offset_*). A roll slider
// turns the driven gear with the correct kinematic coupling, so the triads visibly rotate
// with their gears — consistent with *BOUNDARY / *CLOAD in the .inp.

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { Mesh3DResponse } from "@/lib/api";

function buildHull(data: Mesh3DResponse, tint: number): THREE.Group {
  const group = new THREE.Group();
  const nVerts = data.vertices.length / 3;
  const verts: THREE.Vector3[] = [];
  for (let i = 0; i < nVerts; i++) {
    verts.push(
      new THREE.Vector3(data.vertices[3 * i], data.vertices[3 * i + 1], data.vertices[3 * i + 2]),
    );
  }
  const nFaces = data.faces.length / 4;
  const pos = new Float32Array(nFaces * 6 * 3);
  let w = 0;
  const edgePos: number[] = [];
  for (let f = 0; f < nFaces; f++) {
    const idx = [data.faces[4 * f], data.faces[4 * f + 1], data.faces[4 * f + 2], data.faces[4 * f + 3]];
    for (const vi of [idx[0], idx[1], idx[2], idx[0], idx[2], idx[3]]) {
      const v = verts[vi];
      pos[w] = v.x;
      pos[w + 1] = v.y;
      pos[w + 2] = v.z;
      w += 3;
    }
    for (let k = 0; k < 4; k++) {
      const a = verts[idx[k]];
      const b = verts[idx[(k + 1) % 4]];
      edgePos.push(a.x, a.y, a.z, b.x, b.y, b.z);
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geo.computeVertexNormals();
  group.add(
    new THREE.Mesh(
      geo,
      new THREE.MeshLambertMaterial({
        color: tint,
        side: THREE.DoubleSide,
        polygonOffset: true,
        polygonOffsetFactor: 1,
        polygonOffsetUnits: 1,
      }),
    ),
  );
  const egeo = new THREE.BufferGeometry();
  egeo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(edgePos), 3));
  group.add(
    new THREE.LineSegments(
      egeo,
      new THREE.LineBasicMaterial({ color: 0x2c3644, transparent: true, opacity: 0.75 }),
    ),
  );
  return group;
}

/** Rotation-node triad: locked translations/tilts in gray + lock ring, free DOF 6 as a green
 *  rotation arrow about z. `moment` colors the arrow amber (torque-loaded side). */
function buildTriad(size: number, moment: boolean): THREE.Group {
  const g = new THREE.Group();
  const locked = new THREE.Color(0x8a93a3);
  for (const [dir, axisColor] of [
    [new THREE.Vector3(1, 0, 0), 0xd8404a],
    [new THREE.Vector3(0, 1, 0), 0x39b26b],
    [new THREE.Vector3(0, 0, 1), 0x3f7bd9],
  ] as const) {
    const arrow = new THREE.ArrowHelper(dir, new THREE.Vector3(), size, axisColor, size * 0.18, size * 0.09);
    g.add(arrow);
    // locked translation marker: short gray cross-strut at the axis tip
    const strut = new THREE.Mesh(
      new THREE.BoxGeometry(size * 0.14, size * 0.02, size * 0.02),
      new THREE.MeshBasicMaterial({ color: locked }),
    );
    strut.position.copy(dir.clone().multiplyScalar(size * 1.04));
    strut.lookAt(dir.clone().multiplyScalar(2 * size));
    g.add(strut);
  }
  // lock ring: DOF 1–5 held (translations + tilts) — gray torus in the xy-plane
  const ring = new THREE.Mesh(
    new THREE.TorusGeometry(size * 0.45, size * 0.02, 8, 48),
    new THREE.MeshBasicMaterial({ color: locked }),
  );
  g.add(ring);
  // free DOF 6: rotation arrow about +z (green = driven angle, amber = resisting torque)
  const arcPts: THREE.Vector3[] = [];
  for (let k = 0; k <= 40; k++) {
    const a = (k / 40) * Math.PI * 1.5;
    arcPts.push(new THREE.Vector3(Math.cos(a) * size * 0.62, Math.sin(a) * size * 0.62, size * 0.05));
  }
  const arcGeo = new THREE.BufferGeometry().setFromPoints(arcPts);
  const freeColor = moment ? 0xf59e0b : 0x22c55e;
  g.add(new THREE.Line(arcGeo, new THREE.LineBasicMaterial({ color: freeColor, linewidth: 2 })));
  const tipDir = new THREE.Vector3(-Math.sin(Math.PI * 1.5), Math.cos(Math.PI * 1.5), 0);
  const tip = new THREE.ArrowHelper(
    tipDir,
    arcPts[arcPts.length - 1],
    size * 0.1,
    freeColor,
    size * 0.22,
    size * 0.12,
  );
  g.add(tip);
  return g;
}

export function PairViewport(props: {
  gear1: Mesh3DResponse | null; // the stage's first gear — at the origin, LEFT (rig view)
  gear2: Mesh3DResponse | null; // the second gear — at the centre distance, RIGHT
  centerDistance: number;
  teethGear1: number;
  teethGear2: number;
  drivenGear: 1 | 2; // angle-driven gear (green triad; the other carries the torque, amber)
  rollDeg: number; // driven-gear angle (the slider)
  offsetGear1Z?: number; // axial offset along the rotation axis (deck axial_offset_gear1_mm)
  offsetGear2Z?: number;
}) {
  const mount = useRef<HTMLDivElement>(null);
  const state = useRef<{
    renderer: THREE.WebGLRenderer;
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    controls: OrbitControls;
    g1: THREE.Group;
    g2: THREE.Group;
  } | null>(null);

  useEffect(() => {
    const el = mount.current;
    if (!el) return;
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setClearColor(0x10161f);
    el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 3000);
    camera.up.set(0, 0, 1);
    scene.add(new THREE.AmbientLight(0xffffff, 0.8));
    const dir = new THREE.DirectionalLight(0xffffff, 1.3);
    dir.position.set(40, -70, 90);
    scene.add(dir);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    const g1 = new THREE.Group();
    const g2 = new THREE.Group();
    scene.add(g1, g2);
    state.current = { renderer, scene, camera, controls, g1, g2 };

    let raf = 0;
    const loop = () => {
      controls.update();
      renderer.render(scene, camera);
      raf = requestAnimationFrame(loop);
    };
    const resize = () => {
      renderer.setSize(el.clientWidth, el.clientHeight);
      camera.aspect = el.clientWidth / el.clientHeight;
      camera.updateProjectionMatrix();
    };
    const obs = new ResizeObserver(resize);
    obs.observe(el);
    resize();
    loop();
    return () => {
      cancelAnimationFrame(raf);
      obs.disconnect();
      controls.dispose();
      renderer.dispose();
      el.removeChild(renderer.domElement);
      state.current = null;
    };
  }, []);

  // (re)build the two gear groups when payloads arrive
  useEffect(() => {
    const s = state.current;
    if (!s) return;
    s.g1.clear();
    s.g2.clear();
    if (!props.gear1 || !props.gear2) return;
    const a = props.centerDistance;
    const size = a * 0.16;

    // gear 1 at the origin (screen LEFT), sector rotated -90° to face +x (deck convention);
    // the hull is mid-plane symmetric, so the triad at the group origin sits at mid-width
    const hull1 = buildHull(props.gear1, 0xb9c2cf);
    hull1.rotation.z = -Math.PI / 2;
    s.g1.add(hull1, buildTriad(size, props.drivenGear !== 1));
    s.g1.position.set(0, 0, props.offsetGear1Z ?? 0);

    // gear 2 at (a, 0) (screen RIGHT), rotated +90° + half pitch (deck convention)
    const hull2 = buildHull(props.gear2, 0xd5d9df);
    hull2.rotation.z = Math.PI / 2 + Math.PI / props.teethGear2;
    s.g2.add(hull2, buildTriad(size, props.drivenGear !== 2));
    s.g2.position.set(a, 0, props.offsetGear2Z ?? 0);

    s.camera.position.set(a / 2, -a * 1.6, a * 1.1);
    s.controls.target.set(a / 2, 0, 8);
    s.controls.update();
  }, [
    props.gear1,
    props.gear2,
    props.centerDistance,
    props.teethGear2,
    props.drivenGear,
    props.offsetGear1Z,
    props.offsetGear2Z,
  ]);

  // roll coupling: the driven gear follows the slider, the other counter-rotates by the ratio
  useEffect(() => {
    const s = state.current;
    if (!s) return;
    const phi = (props.rollDeg * Math.PI) / 180;
    if (props.drivenGear === 2) {
      s.g2.rotation.z = phi;
      s.g1.rotation.z = (-phi * props.teethGear2) / props.teethGear1;
    } else {
      s.g1.rotation.z = phi;
      s.g2.rotation.z = (-phi * props.teethGear1) / props.teethGear2;
    }
  }, [props.rollDeg, props.teethGear1, props.teethGear2, props.drivenGear]);

  return <div ref={mount} className="w-full h-full min-h-[520px] rounded-lg overflow-hidden" />;
}
