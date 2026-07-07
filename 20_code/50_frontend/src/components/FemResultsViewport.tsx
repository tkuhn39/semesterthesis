"use client";

// 3-D stress/strain viewer of ONE flank set (phase G, user goal 2026-07-06): axis 1 = the
// path-of-contact coordinate ξ relative to the pitch point C (backend-unwrapped from the
// node radii, range beyond A/E down to d_Nf … d_Na), axis 2 = the face width z, axis 3 =
// the selected field (σ, ε, CPRESS, u) as height + color. The A…E markers are drawn on
// the ξ axis; the frame's maximum is flagged with a marker sphere. Structured flank bands
// (n_z × n_xi grid) render as a vertex-colored surface, anything else as points.
// Orthographic camera + CATIA mouse controls, consistent with the pair viewport.

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { CatiaControls } from "@/components/CatiaControls";
import type { FemField, FemFrame, FlankFrameData, LineOfActionMarkers } from "@/lib/api";

/** Blue → cyan → green → yellow → red, t in [0, 1]. */
function heat(t: number): [number, number, number] {
  const x = Math.min(Math.max(t, 0), 1) * 4;
  if (x < 1) return [0, 0.35 + 0.65 * x, 1];
  if (x < 2) return [0, 1, 1 - (x - 1)];
  if (x < 3) return [x - 2, 1, 0];
  return [1, 1 - 0.85 * (x - 3), 0];
}

function buildFlank(
  data: FlankFrameData,
  field: FemField,
  scale: { xi0: number; xiSpan: number; z0: number; zSpan: number; vMax: number; h: number },
): THREE.Group {
  const group = new THREE.Group();
  const n = data.xi.length;
  const values = data[field];
  const px = (i: number) => ((data.xi[i] - scale.xi0) / scale.xiSpan) * 100;
  const py = (i: number) => ((data.z[i] - scale.z0) / Math.max(scale.zSpan, 1e-9)) * 60;
  const pz = (i: number) => (scale.vMax > 0 ? (values[i] / scale.vMax) * scale.h : 0);

  const positions = new Float32Array(n * 3);
  const colors = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    positions[3 * i] = px(i);
    positions[3 * i + 1] = py(i);
    positions[3 * i + 2] = pz(i);
    const [r, g, b] = heat(scale.vMax > 0 ? values[i] / scale.vMax : 0);
    colors[3 * i] = r;
    colors[3 * i + 1] = g;
    colors[3 * i + 2] = b;
  }

  const structured = data.n_xi > 1 && data.n_z > 1 && data.n_z * data.n_xi === n;
  if (structured) {
    // nodes arrive sorted (z, r) → row-major grid: row = z plane, column = ξ station
    const idx: number[] = [];
    for (let iz = 0; iz < data.n_z - 1; iz++) {
      for (let ix = 0; ix < data.n_xi - 1; ix++) {
        const a = iz * data.n_xi + ix;
        const b = a + 1;
        const c = a + data.n_xi;
        const d = c + 1;
        idx.push(a, b, d, a, d, c);
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    geo.setIndex(idx);
    geo.computeVertexNormals();
    group.add(
      new THREE.Mesh(
        geo,
        new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide }),
      ),
    );
    // wireframe of the grid rows for readability
    const linePos: number[] = [];
    for (let iz = 0; iz < data.n_z; iz++) {
      for (let ix = 0; ix < data.n_xi - 1; ix++) {
        const a = iz * data.n_xi + ix;
        linePos.push(
          positions[3 * a], positions[3 * a + 1], positions[3 * a + 2],
          positions[3 * a + 3], positions[3 * a + 4], positions[3 * a + 5],
        );
      }
    }
    const lg = new THREE.BufferGeometry();
    lg.setAttribute("position", new THREE.BufferAttribute(new Float32Array(linePos), 3));
    group.add(
      new THREE.LineSegments(
        lg,
        new THREE.LineBasicMaterial({ color: 0x1c2430, transparent: true, opacity: 0.4 }),
      ),
    );
  } else {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    group.add(new THREE.Points(geo, new THREE.PointsMaterial({ vertexColors: true, size: 2 })));
  }

  // maximum marker (user request: "Maxima je Position markiert")
  let iMax = 0;
  for (let i = 1; i < n; i++) if (values[i] > values[iMax]) iMax = i;
  if (values[iMax] > 0) {
    const marker = new THREE.Mesh(
      new THREE.SphereGeometry(1.6, 12, 12),
      new THREE.MeshBasicMaterial({ color: 0xff4b3e }),
    );
    marker.position.set(px(iMax), py(iMax), pz(iMax) + 2);
    group.add(marker);
  }
  return group;
}

function buildAxes(markers: LineOfActionMarkers, scale: { xi0: number; xiSpan: number }): THREE.Group {
  const g = new THREE.Group();
  const toX = (xi: number) => ((xi - scale.xi0) / scale.xiSpan) * 100;
  // base plane frame
  const frame = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(0, 0, 0),
    new THREE.Vector3(100, 0, 0),
    new THREE.Vector3(100, 60, 0),
    new THREE.Vector3(0, 60, 0),
    new THREE.Vector3(0, 0, 0),
  ]);
  g.add(new THREE.Line(frame, new THREE.LineBasicMaterial({ color: 0x5a6474 })));
  // A…E markers on the ξ axis (ISO 21771 letters; C = pitch point)
  for (const [key, color] of [
    ["a", 0x9aa4b5],
    ["b", 0x9aa4b5],
    ["c", 0x22c55e],
    ["d", 0x9aa4b5],
    ["e", 0x9aa4b5],
  ] as const) {
    const x = toX(markers[key]);
    const lg = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(x, 0, 0),
      new THREE.Vector3(x, 60, 0),
    ]);
    g.add(
      new THREE.Line(lg, new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.8 })),
    );
    const tick = new THREE.Mesh(
      new THREE.BoxGeometry(0.6, 3, 0.6),
      new THREE.MeshBasicMaterial({ color }),
    );
    tick.position.set(x, -2.5, 0);
    g.add(tick);
  }
  return g;
}

export function FemResultsViewport(props: {
  frame: FemFrame | null;
  tag: string | null; // the selected G{g}T{ttt}F{f} flank set
  field: FemField;
  markers: LineOfActionMarkers | null;
  vMax: number; // field maximum over ALL frames of this tag (stable color scale)
}) {
  const mount = useRef<HTMLDivElement>(null);
  const state = useRef<{
    renderer: THREE.WebGLRenderer;
    scene: THREE.Scene;
    camera: THREE.OrthographicCamera;
    controls: CatiaControls;
    group: THREE.Group;
  } | null>(null);

  useEffect(() => {
    const el = mount.current;
    if (!el) return;
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setClearColor(0x10161f);
    el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-60, 60, 60, -60, 0.01, 5000);
    camera.up.set(0, 0, 1);
    scene.add(new THREE.AmbientLight(0xffffff, 0.85));
    const dir = new THREE.DirectionalLight(0xffffff, 1.2);
    dir.position.set(60, -80, 120);
    scene.add(dir);
    const controls = new CatiaControls(camera, el);
    const group = new THREE.Group();
    scene.add(group);
    state.current = { renderer, scene, camera, controls, group };
    controls.fit(new THREE.Vector3(50, 30, 10), 70);

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

  useEffect(() => {
    const s = state.current;
    if (!s) return;
    s.group.clear();
    if (!props.frame || !props.tag || !props.markers) return;
    const data = props.frame.flanks[props.tag];
    if (!data) return;
    const markers = props.markers;
    const xi0 = markers.xi_min;
    const xiSpan = Math.max(markers.xi_max - markers.xi_min, 1e-9);
    const z0 = Math.min(...data.z);
    const zSpan = Math.max(...data.z) - z0;
    s.group.add(buildAxes(markers, { xi0, xiSpan }));
    s.group.add(buildFlank(data, props.field, { xi0, xiSpan, z0, zSpan, vMax: props.vMax, h: 35 }));
  }, [props.frame, props.tag, props.field, props.markers, props.vMax]);

  return <div ref={mount} className="w-full h-full min-h-[520px] rounded-lg overflow-hidden" />;
}
