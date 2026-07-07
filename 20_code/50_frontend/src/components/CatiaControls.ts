"use client";

// CATIA mouse scheme on an ORTHOGRAPHIC camera (user decision 2026-07-06: "Ansicht nicht
// perspektivisch, sondern gerade geführt, 360 Grad schwenkbar, Mauskombinationen von CATIA"):
//   middle drag                → pan
//   middle + left/right drag   → rotate — quaternion-based free tumble, NO polar clamp
//   wheel                      → zoom (orthographic zoom factor)
// Left alone stays free (CATIA uses it for selection). Shared by PairViewport + MeshViewport.

import * as THREE from "three";

export class CatiaControls {
  readonly camera: THREE.OrthographicCamera;
  readonly target = new THREE.Vector3();
  rotateSpeed = 0.006;
  private viewHeight = 100; // world units visible vertically at zoom 1
  private aspect = 1;
  private last: { x: number; y: number } | null = null;
  private readonly el: HTMLElement;
  private readonly disposers: (() => void)[] = [];

  constructor(camera: THREE.OrthographicCamera, el: HTMLElement) {
    this.camera = camera;
    this.el = el;

    const down = (e: PointerEvent) => {
      // suppress the browser's middle-click autoscroll — MMB is the CATIA modifier
      if (e.button === 1) e.preventDefault();
      this.last = { x: e.clientX, y: e.clientY };
      el.setPointerCapture(e.pointerId);
    };
    const move = (e: PointerEvent) => {
      if (this.last == null || e.buttons === 0) return;
      const dx = e.clientX - this.last.x;
      const dy = e.clientY - this.last.y;
      this.last = { x: e.clientX, y: e.clientY };
      const middle = (e.buttons & 4) !== 0;
      const side = (e.buttons & 3) !== 0; // left (1) or right (2)
      if (middle && side) this.rotate(dx, dy);
      else if (middle) this.pan(dx, dy);
    };
    const up = (e: PointerEvent) => {
      if (e.buttons === 0) this.last = null;
    };
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      this.zoomBy(Math.exp(-e.deltaY * 0.001));
    };
    const swallow = (e: Event) => e.preventDefault();

    el.addEventListener("pointerdown", down);
    el.addEventListener("pointermove", move);
    el.addEventListener("pointerup", up);
    el.addEventListener("wheel", wheel, { passive: false });
    el.addEventListener("contextmenu", swallow);
    el.addEventListener("auxclick", swallow);
    this.disposers.push(() => {
      el.removeEventListener("pointerdown", down);
      el.removeEventListener("pointermove", move);
      el.removeEventListener("pointerup", up);
      el.removeEventListener("wheel", wheel);
      el.removeEventListener("contextmenu", swallow);
      el.removeEventListener("auxclick", swallow);
    });
  }

  dispose(): void {
    for (const d of this.disposers) d();
  }

  /** Aim the camera at `center` from the default isometric-ish direction and size the
   *  frustum so a sphere of `radius` fits comfortably. */
  fit(center: THREE.Vector3, radius: number): void {
    this.target.copy(center);
    const dir = new THREE.Vector3(0.25, -0.75, 0.61).normalize();
    this.camera.position.copy(center).addScaledVector(dir, radius * 4);
    this.camera.up.set(0, 0, 1);
    this.camera.lookAt(center);
    this.camera.near = 0.01;
    this.camera.far = Math.max(radius * 100, 1000);
    this.camera.zoom = 1;
    this.viewHeight = radius * 2.3;
    this.applyFrustum();
  }

  resize(width: number, height: number): void {
    this.aspect = height > 0 ? width / height : 1;
    this.applyFrustum();
  }

  private applyFrustum(): void {
    const h = this.viewHeight / 2;
    this.camera.top = h;
    this.camera.bottom = -h;
    this.camera.left = -h * this.aspect;
    this.camera.right = h * this.aspect;
    this.camera.updateProjectionMatrix();
  }

  /** Free tumble about the camera's own right/up axes — no gimbal, no polar clamp. */
  private rotate(dx: number, dy: number): void {
    const right = new THREE.Vector3().setFromMatrixColumn(this.camera.matrix, 0);
    const up = new THREE.Vector3().setFromMatrixColumn(this.camera.matrix, 1);
    const q = new THREE.Quaternion()
      .setFromAxisAngle(up, -dx * this.rotateSpeed)
      .multiply(new THREE.Quaternion().setFromAxisAngle(right, -dy * this.rotateSpeed));
    const offset = this.camera.position.clone().sub(this.target).applyQuaternion(q);
    this.camera.up.applyQuaternion(q);
    this.camera.position.copy(this.target).add(offset);
    this.camera.lookAt(this.target);
  }

  private pan(dx: number, dy: number): void {
    const perPixel =
      (this.camera.top - this.camera.bottom) / this.camera.zoom / Math.max(this.el.clientHeight, 1);
    const right = new THREE.Vector3().setFromMatrixColumn(this.camera.matrix, 0);
    const up = new THREE.Vector3().setFromMatrixColumn(this.camera.matrix, 1);
    const shift = right.multiplyScalar(-dx * perPixel).addScaledVector(up, dy * perPixel);
    this.camera.position.add(shift);
    this.target.add(shift);
  }

  private zoomBy(factor: number): void {
    this.camera.zoom = Math.min(Math.max(this.camera.zoom * factor, 0.02), 500);
    this.camera.updateProjectionMatrix();
  }
}
