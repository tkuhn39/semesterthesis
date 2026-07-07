// Pair-view review shots: open FE-Abwälzmodell (Ansicht), generate the pair (backend
// assembly), move the roll slider, and screenshot — verifies the phase D/E/F layout
// (per-gear fineness table, split pane, viewport with the closed assembly).
// Usage: node scripts/shot-pair.mjs <outDir>
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const OUT = process.argv[2] ?? "self_shots";
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1720, height: 1000 } });
page.on("pageerror", (e) => console.log("PAGEERROR:", e.message));
await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
await page.waitForTimeout(1200);

await page.getByRole("button", { name: "Stirnradstufe [3]", exact: false }).first().click();
await page.waitForTimeout(600);
await page.getByRole("button", { name: "FE-Abwälzmodell (Ansicht)", exact: true }).first().click();
await page.waitForTimeout(800);
await page.screenshot({ path: `${OUT}/pair_view_initial.png` });
console.log("shot: pair_view_initial.png");

await page.getByRole("button", { name: "Paar erzeugen", exact: true }).click();
// assembly + two previews — generous timeout, then wait for the slider to appear
await page.waitForSelector('input[type="range"]', { timeout: 240000 });
await page.waitForTimeout(1500);
await page.screenshot({ path: `${OUT}/pair_view_generated_start.png` });
console.log("shot: pair_view_generated_start.png");

// walk the slider to the middle and the end of the roll schedule
const slider = page.locator('input[type="range"]').first();
await slider.evaluate((el) => {
  const input = el;
  const setVal = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
  setVal.call(input, String((Number(input.max) - Number(input.min)) / 2));
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
});
await page.waitForTimeout(700);
await page.screenshot({ path: `${OUT}/pair_view_generated_mid.png` });
console.log("shot: pair_view_generated_mid.png");

await slider.evaluate((el) => {
  const input = el;
  const setVal = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
  setVal.call(input, input.max);
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
});
await page.waitForTimeout(700);
await page.screenshot({ path: `${OUT}/pair_view_generated_end.png` });
console.log("shot: pair_view_generated_end.png");

await browser.close();
console.log("done");
