// FEM-results review shot: open Stirnradstufe → Ergebnisse (3D), upload a fem_results.json,
// switch field + walk the position slider, screenshot the 3-D stress viewer.
// Usage: node scripts/shot-femresults.mjs <outDir> <fem_results.json>
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const OUT = process.argv[2] ?? "self_shots";
const FILE = process.argv[3];
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1720, height: 1000 } });
page.on("pageerror", (e) => console.log("PAGEERROR:", e.message));
await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
await page.waitForTimeout(1200);

await page.getByRole("button", { name: "Stirnradstufe [3]", exact: false }).first().click();
await page.waitForTimeout(500);
await page.getByRole("button", { name: "Ergebnisse (3D)", exact: true }).first().click();
await page.waitForTimeout(700);
await page.screenshot({ path: `${OUT}/femresults_empty.png` });
console.log("shot: femresults_empty.png");

await page.setInputFiles('input[type="file"]', FILE);
await page.waitForSelector('input[type="range"]', { timeout: 30000 });
await page.waitForTimeout(1500);
await page.screenshot({ path: `${OUT}/femresults_loaded.png` });
console.log("shot: femresults_loaded.png");

// walk the position slider to the middle
const slider = page.locator('input[type="range"]').first();
await slider.evaluate((el) => {
  const setVal = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
  setVal.call(el, String(Math.floor(Number(el.max) / 2)));
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
});
await page.waitForTimeout(700);
await page.screenshot({ path: `${OUT}/femresults_mid.png` });
console.log("shot: femresults_mid.png");

await browser.close();
console.log("done");
