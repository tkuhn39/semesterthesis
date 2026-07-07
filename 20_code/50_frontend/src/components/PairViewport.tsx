"use client";

// Pair viewport (user points 1–3, 2026-07-06): renders THE deck assembly from
// /api/mesh/pair — vertices arrive in absolute assembly coordinates at the closed, centered
// configuration (backlash-closing rotation baked in by the backend; NO viewport-local
// positioning math). The roll slider walks the REAL Wälzstellungen of the deck schedule:
// each gear rotates about its own axis by start_angle_rad + k · step_angle_rad (edge-tooth
// start, kinematic coupling — both from the backend). Camera is ORTHOGRAPHIC with CATIA
// mouse controls (MMB pan, MMB+LMB/RMB free 360° tumble, wheel zoom). CO-MOVING DOF triads
// at the rotation nodes show the deck BCs: DOF 1–5 locked (gray + lock ring), DOF 6 free
// (green = angle-driven, amber = torque side).

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { CatiaControls } from "@/components/CatiaControls";
import type { PairAssemblyResponse, PairGearOut } from "@/lib/api";

/** Hull/shell group in GEAR-LOCAL coordinates (assembly vertices minus the gear center),
 *  so rotating the parent group about z rolls the gear about its own axis. */
function buildGear(data: PairGearOut, tint: number): THREE.Group {
  const group = new THREE.Group();
  const [cx, cy] = data.center;
  const nVerts = data.vertices.length / 3;
  const verts: THREE.Vector3[] = [];
  for (let i = 0; i < nVerts; i++) {
    verts.push(
      new THREE.Vector3(
        data.vertices[3 * i] - cx,
        data.vertices[3 * i + 1] - cy,
        data.vertices[3 * i + 2],
      ),
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
        // rigid Außenhülle: render the open lateral shell semi-transparent so the
        // missing end faces (deliberate — ideally stiff R3D4 mantle) read as such
        transparent: data.rigid_shell,
        opacity: data.rigid_shell ? 0.8 : 1.0,
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
  pair: PairAssemblyResponse | null; // THE deck assembly (backend SSOT)
  position: number; // Wälzstellung k, continuous 0 … n_positions−1 (the slider)
}) {
  const mount = useRef<HTMLDivElement>(null);
  const state = useRef<{
    renderer: THREE.WebGLRenderer;
    scene: THREE.Scene;
    camera: THREE.OrthographicCamera;
    controls: CatiaControls;
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
    // orthographic ("gerade geführt") — frustum managed by CatiaControls.fit/resize
    const camera = new THREE.OrthographicCamera(-50, 50, 50, -50, 0.01, 5000);
    camera.up.set(0, 0, 1);
    scene.add(new THREE.AmbientLight(0xffffff, 0.8));
    const dir = new THREE.DirectionalLight(0xffffff, 1.3);
    dir.position.set(40, -70, 90);
    scene.add(dir);
    const controls = new CatiaControls(camera, el);
    const g1 = new THREE.Group();
    const g2 = new THREE.Group();
    scene.add(g1, g2);
    state.current = { renderer, scene, camera, controls, g1, g2 };

    let raf = 0;
    const loop = () => {
      renderer.render(scene, camera);
      raf = requestAnimationFrame(loop);
    };
    const resize = () => {
      renderer.setSize(el.clientWidth, el.clientHeight);
      controls.resize(el.clientWidth, el.clientHeight);
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

  // (re)build the two gear groups when the assembly arrives — geometry as delivered,
  // each group at its gear's rotation axis so group.rotation.z = the deck angle
  useEffect(() => {
    const s = state.current;
    if (!s) return;
    s.g1.clear();
    s.g2.clear();
    const p = props.pair;
    if (!p) return;
    const a = p.center_distance_mm;
    const size = a * 0.16;

    for (const [group, gear, tint] of [
      [s.g1, p.gear1, 0xb9c2cf],
      [s.g2, p.gear2, 0xd5d9df],
    ] as const) {
      group.add(buildGear(gear, tint));
      const triad = buildTriad(size, gear.gear !== p.driven_gear);
      triad.position.set(0, 0, gear.z_mid_mm);
      group.add(triad);
      group.position.set(gear.center[0], gear.center[1], 0);
    }
    s.controls.fit(new THREE.Vector3(a / 2, 0, 0), a * 0.95);
  }, [props.pair]);

  // roll schedule: position k rotates each gear by its backend angle law (edge start +
  // kinematic coupling — the same numbers the .inp uses)
  useEffect(() => {
    const s = state.current;
    const p = props.pair;
    if (!s || !p) return;
    s.g1.rotation.z = p.gear1.start_angle_rad + props.position * p.gear1.step_angle_rad;
    s.g2.rotation.z = p.gear2.start_angle_rad + props.position * p.gear2.step_angle_rad;
  }, [props.position, props.pair]);

  return <div ref={mount} className="w-full h-full min-h-[520px] rounded-lg overflow-hidden" />;
}
