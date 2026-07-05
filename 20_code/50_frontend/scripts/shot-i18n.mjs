// Self-review of the i18n pass: key views in EN and DE (numbers: comma in DE, dot in EN).
// Usage:  node scripts/shot-i18n.mjs <outDir>
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const OUT = process.argv[2] ?? "i18n_shots";
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1720, height: 1100 } });
page.on("pageerror", (e) => console.log("PAGEERROR:", e.message));
await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
await page.waitForTimeout(1200);

const shot = async (name) => {
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
  console.log(`shot: ${name}.png`);
};

// DE first: Geometrie (numbers must show comma decimals now)
await page.getByRole("button", { name: "Stirnradstufe [3]", exact: false }).first().click();
await page.waitForTimeout(500);
await page.getByRole("button", { name: "Geometrie", exact: true }).first().click();
await page.waitForTimeout(1800);
await shot("01_de_geometrie");

// switch to EN via the header locale select (the only select with an "en" option)
await page
  .locator("select", { has: page.locator('option[value="en"]') })
  .first()
  .selectOption("en");
await page.waitForTimeout(1500);
await shot("02_en_geometry");

// EN: stage variation step 1 (labels + extension section)
await page.getByRole("button", { name: "Stage variation", exact: false }).first().click();
await page.waitForTimeout(700);
await page
  .getByRole("button", { name: "Material, root fillet & safeties (extension)", exact: false })
  .click();
await page.waitForTimeout(400);
await shot("03_en_variation_step1");

// EN: capacity results (Auslegung's sibling — Tragfähigkeit tab is schema-driven,
// the analytic card lives in the own extras tab)
await page.getByRole("button", { name: "[3]", exact: false }).first().click();
await page.waitForTimeout(500);
await page.getByRole("button", { name: "Load capacity", exact: true }).first().click();
await page.waitForTimeout(1800);
await shot("04_en_capacity");

await browser.close();
console.log("done");
