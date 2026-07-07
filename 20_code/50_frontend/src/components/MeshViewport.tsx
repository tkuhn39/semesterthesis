"use client";

// three.js viewport for the extruded FE sector (dark, ANSA-like: light-gray hull with thin
// edges, optional scaled-Jacobian heatmap). Pure client component; geometry arrives as the
// /api/mesh/3d hull payload (deduplicated vertices + outer quad faces + per-face quality).
// Orthographic camera + CATIA mouse controls (user decision 2026-07-06).

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { CatiaControls } from "@/components/CatiaControls";
import type { Mesh3DResponse } from "@/lib/api";

function qualityColor(q: number): [number, number, number] {
  // 1.0 → light gray, 0.5 → amber, ≤0.35 → red (gate)
  if (q >= 0.7) return [0.83, 0.85, 0.88];
  if (q >= 0.5) {
    const t = (0.7 - q) / 0.2;
    return [0.83 + 0.13 * t, 0.75 - 0.1 * t, 0.88 - 0.5 * t];
  }
  if (q >= 0.35) {
    const t = (0.5 - q) / 0.15;
    return [0.96, 0.65 - 0.35 * t, 0.38 - 0.28 * t];
  }
  return [0.9, 0.2, 0.16];
}

export function MeshViewport(props: { data: Mesh3DResponse | null; heatmap: boolean }) {
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
    // orthographic ("gerade geführt") — frustum managed by CatiaControls.fit/resize
    const camera = new THREE.OrthographicCamera(-50, 50, 50, -50, 0.01, 5000);
    camera.up.set(0, 0, 1);
    scene.add(new THREE.AmbientLight(0xffffff, 0.75));
    const dir = new THREE.DirectionalLight(0xffffff, 1.4);
    dir.position.set(30, -50, 80);
    scene.add(dir);
    const controls = new CatiaControls(camera, el);
    const group = new THREE.Group();
    scene.add(group);
    state.current = { renderer, scene, camera, controls, group };

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
    const d = props.data;
    if (!d) return;

    const nVerts = d.vertices.length / 3;
    const verts: THREE.Vector3[] = [];
    for (let i = 0; i < nVerts; i++) {
      verts.push(new THREE.Vector3(d.vertices[3 * i], d.vertices[3 * i + 1], d.vertices[3 * i + 2]));
    }
    // centre the sector for orbiting
    const box = new THREE.Box3();
    verts.forEach((v) => box.expandByPoint(v));
    const centre = box.getCenter(new THREE.Vector3());

    const nFaces = d.faces.length / 4;
    const pos = new Float32Array(nFaces * 6 * 3);
    const col = new Float32Array(nFaces * 6 * 3);
    let w = 0;
    const edgePos: number[] = [];
    for (let f = 0; f < nFaces; f++) {
      const idx = [d.faces[4 * f], d.faces[4 * f + 1], d.faces[4 * f + 2], d.faces[4 * f + 3]];
      const q = props.heatmap ? d.face_quality[f] : 1.0;
      const [r, g, b] = qualityColor(q);
      const tri = [idx[0], idx[1], idx[2], idx[0], idx[2], idx[3]];
      for (const vi of tri) {
        const v = verts[vi];
        pos[w] = v.x - centre.x;
        pos[w + 1] = v.y - centre.y;
        pos[w + 2] = v.z - centre.z;
        col[w] = r;
        col[w + 1] = g;
        col[w + 2] = b;
        w += 3;
      }
      for (let k = 0; k < 4; k++) {
        const a = verts[idx[k]];
        const b2 = verts[idx[(k + 1) % 4]];
        edgePos.push(a.x - centre.x, a.y - centre.y, a.z - centre.z);
        edgePos.push(b2.x - centre.x, b2.y - centre.y, b2.z - centre.z);
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
    geo.computeVertexNormals();
    const mat = new THREE.MeshLambertMaterial({
      vertexColors: true,
      side: THREE.DoubleSide,
      polygonOffset: true,
      polygonOffsetFactor: 1,
      polygonOffsetUnits: 1,
    });
    s.group.add(new THREE.Mesh(geo, mat));

    const egeo = new THREE.BufferGeometry();
    egeo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(edgePos), 3));
    s.group.add(
      new THREE.LineSegments(
        egeo,
        new THREE.LineBasicMaterial({ color: 0x2c3644, transparent: true, opacity: 0.85 }),
      ),
    );

    const size = box.getSize(new THREE.Vector3()).length();
    s.controls.fit(new THREE.Vector3(0, 0, 0), size * 0.55);
  }, [props.data, props.heatmap]);

  return <div ref={mount} className="w-full h-full min-h-[420px] rounded-lg overflow-hidden" />;
}
