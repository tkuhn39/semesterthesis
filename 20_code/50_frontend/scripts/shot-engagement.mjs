// Self-review of the Zahneingriff zoom + line of action (T1–A–B–C–D–E–T2 overlay).
// Usage:  node scripts/shot-engagement.mjs <outDir>
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const OUT = process.argv[2] ?? "eng_shots";
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1720, height: 1100 } });
page.on("pageerror", (e) => console.log("PAGEERROR:", e.message));
await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
await page.waitForTimeout(1200);

await page.getByRole("button", { name: "Stirnradstufe [3]", exact: false }).first().click();
await page.waitForTimeout(500);
await page.getByRole("button", { name: "Geometrie", exact: true }).first().click();
await page.waitForTimeout(2200);

// pause the animation for a stable screenshot
await page.getByRole("button", { name: "⏸ Pause", exact: true }).click();
await page.waitForTimeout(300);
await page.screenshot({ path: `${OUT}/01_zoom_eingriffszone.png` });
console.log("shot: 01_zoom_eingriffszone.png");

// crop-level shot of the engagement card alone
const card = page.locator("div", { hasText: /^Zahneingriff/ }).locator("xpath=ancestor-or-self::div[contains(@class,'rounded-lg')]").first();
await card.screenshot({ path: `${OUT}/02_zoom_karte.png` }).catch(async () => {
  console.log("card locator fallback");
});

// toggle to full view
await page.getByRole("button", { name: "Gesamtansicht", exact: true }).click();
await page.waitForTimeout(400);
await page.screenshot({ path: `${OUT}/03_gesamtansicht.png` });
console.log("shot: 03_gesamtansicht.png");

await browser.close();
console.log("done");
