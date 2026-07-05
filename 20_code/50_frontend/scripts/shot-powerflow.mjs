// Self-review of the powerflow SSOT rebuild: shaft-1/2 columns, one torque entered on
// either shaft (other side locked+converted), clear=reset, Antrieb/Abtrieb exclusivity,
// and the torque propagating into Dynamikfaktoren + Stufenvariation.
// Usage:  node scripts/shot-powerflow.mjs <outDir>
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const OUT = process.argv[2] ?? "pf_shots";
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1720, height: 1100 } });
page.on("pageerror", (e) => console.log("PAGEERROR:", e.message));
page.on("console", (m) => {
  if (m.type() === "error") console.log("CONSOLE-ERROR:", m.text());
});
await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
await page.waitForTimeout(1200);

const shot = async (name) => {
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
  console.log(`shot: ${name}.png`);
};

// open Getriebeeinheit → Leistungsfluss
await page.getByRole("button", { name: "Getriebeeinheit [1]", exact: false }).first().click();
await page.waitForTimeout(500);
await page.getByRole("button", { name: "Leistungsfluss", exact: true }).click();
await page.waitForTimeout(800);
await shot("01_default_welle2_8nm");

// torque row: cell inputs (Welle 1 | Welle 2)
const torqueRow = page.locator("tr", { hasText: "Drehmoment" }).first();
const tIn = torqueRow.locator("input");
const v1 = async () => ({
  w1: await tIn.nth(0).inputValue(),
  w1dis: await tIn.nth(0).isDisabled(),
  w2: await tIn.nth(1).inputValue(),
  w2dis: await tIn.nth(1).isDisabled(),
});
console.log("default:", JSON.stringify(await v1())); // expect w1 locked 7.8462, w2 editable 8

// clear shaft 2 → both empty + editable
await tIn.nth(1).fill("");
await tIn.nth(1).blur();
await page.waitForTimeout(400);
console.log("cleared:", JSON.stringify(await v1()));
await shot("02_geleert_beide_frei");

// enter 10 at shaft 1 → shaft 2 locked with 10*52/51 = 10.1961
await tIn.nth(0).fill("10");
await tIn.nth(0).blur();
await page.waitForTimeout(400);
console.log("shaft1=10:", JSON.stringify(await v1()));
await shot("03_welle1_10nm");

// back to kst-E: clear shaft 1, enter 8 at shaft 2
await tIn.nth(0).fill("");
await tIn.nth(0).blur();
await page.waitForTimeout(300);
await tIn.nth(1).fill("8");
await tIn.nth(1).blur();
await page.waitForTimeout(400);
console.log("restored:", JSON.stringify(await v1()));

// Antrieb/Abtrieb exclusivity: flip Typ of shaft 1 to Antrieb → shaft 2 must flip
const typeRow = page.locator("tr", { hasText: "Typ" }).first();
const sel = typeRow.locator("select");
console.log("types before:", await sel.nth(0).inputValue(), await sel.nth(1).inputValue());
await sel.nth(0).selectOption("antrieb");
await page.waitForTimeout(400);
console.log("types after :", await sel.nth(0).inputValue(), await sel.nth(1).inputValue());
await shot("04_typ_exklusiv");
// flip back
await sel.nth(1).selectOption("antrieb");
await page.waitForTimeout(300);

// Dynamikfaktoren: T1 must show 7.8462 grey
await page.getByRole("button", { name: "Stirnradstufe [3]", exact: false }).first().click();
await page.waitForTimeout(500);
await page.getByRole("button", { name: "Dynamikfaktoren", exact: true }).click();
await page.waitForTimeout(1500);
await shot("05_dynamik_t1_aus_leistungsfluss");

// Stufenvariation extension: T1 grey display
await page.getByRole("button", { name: "Stufenvariation", exact: false }).first().click();
await page.waitForTimeout(600);
await page
  .getByRole("button", { name: "Werkstoff, Fußform & Sicherheiten (Erweiterung)", exact: false })
  .click();
await page.waitForTimeout(400);
await shot("06_variation_t1_aus_leistungsfluss");

await browser.close();
console.log("done");
