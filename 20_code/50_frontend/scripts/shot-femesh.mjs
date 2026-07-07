// FE-Mesh review shot: open the Stahlritzel FE-Mesh tab, generate the mesh, screenshot —
// verifies the Zahndicke fineness dropdown, the effective-counts row and the split pane.
// Usage: node scripts/shot-femesh.mjs <outDir>
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const OUT = process.argv[2] ?? "self_shots";
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1720, height: 1000 } });
page.on("pageerror", (e) => console.log("PAGEERROR:", e.message));
await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
await page.waitForTimeout(1200);

await page.getByRole("button", { name: "Stahlritzel [8]", exact: false }).first().click();
await page.waitForTimeout(500);
await page.getByRole("button", { name: "FE-Mesh", exact: true }).first().click();
await page.waitForTimeout(700);
await page.screenshot({ path: `${OUT}/femesh_initial.png` });
console.log("shot: femesh_initial.png");

await page.getByRole("button", { name: "Mesh erzeugen", exact: false }).first().click();
await page.waitForTimeout(6000);
await page.screenshot({ path: `${OUT}/femesh_generated.png` });
console.log("shot: femesh_generated.png");

await browser.close();
console.log("done");
