// Self-review of the Stufenvariation 4-step flow: walk the wizard end to end,
// verify persistence (back-navigation without recompute) and Übernehmen (SSOT).
// Usage:  node scripts/shot-variation.mjs <outDir>
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const OUT = process.argv[2] ?? "var_shots";
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

// step 1 — attributes
await page.getByRole("button", { name: "Stufenvariation", exact: false }).first().click();
await page.waitForTimeout(900);
await shot("01_step1_attribute");

// open the collapsed extension section, set Fußform (used later for the contour overlay)
await page
  .getByRole("button", { name: "Werkstoff, Fußform & Sicherheiten (Erweiterung)", exact: false })
  .click();
await page.waitForTimeout(300);
const fuss = page.locator("label", { hasText: "Fußform" }).locator("select");
await fuss.selectOption("bionic");
await page.waitForTimeout(300);
await shot("01b_step1_erweiterung");

// run the sweep
await page.getByRole("button", { name: "Weiter > (berechnen)", exact: true }).click();
await page.waitForSelector("text=erfolgreich", { timeout: 60000 });
await page.waitForTimeout(500);
await shot("02_step3_filter");

// set a filter: S_F Rad 2 >= 0.3 → count line must shrink but keep variants
const sfRow = page.locator("tr", { hasText: "Sicherheitsfaktor Fuß Rad 2" });
await sfRow.locator("input").first().fill("0.3");
await page.waitForTimeout(400);
await shot("03_step3_filter_sf1");

// step 4 — results
await page.getByRole("button", { name: "Weiter >", exact: true }).click();
await page.waitForTimeout(1200);
await shot("04_step4_ergebnisse");

// select two variants for comparison → contour overlay + PC grey/colour behaviour
const boxes = page.locator("table >> input[type=checkbox]");
await boxes.nth(0).check();
await page.waitForTimeout(1500);
await boxes.nth(1).check();
await page.waitForTimeout(2000);
await shot("05_step4_vergleich_overlay");

// back to filters — results must persist WITHOUT recompute (no spinner, counts intact)
await page.getByRole("button", { name: "< Zurück", exact: true }).click();
await page.waitForTimeout(500);
await shot("06_step3_zurueck_persistent");

// away to another node and back — step + results must survive the tab switch
await page.getByRole("button", { name: "Getriebeeinheit [1]", exact: false }).first().click();
await page.waitForTimeout(700);
await page.getByRole("button", { name: "Stufenvariation", exact: false }).first().click();
await page.waitForTimeout(700);
await shot("07_persistenz_nach_tabwechsel");

// forward again and apply the first variant (Übernehmen → SSOT)
await page.getByRole("button", { name: "Weiter >", exact: true }).click();
await page.waitForTimeout(900);
const before = await page
  .locator("table tbody tr")
  .first()
  .locator("td")
  .nth(2)
  .innerText()
  .catch(() => "?");
console.log("first variant z1 =", before);
await page.getByRole("button", { name: "Übernehmen", exact: true }).first().click();
await page.waitForTimeout(600);

// Geometrie tab must now show the variant's z values (single source of truth)
await page.getByRole("button", { name: "Stirnradstufe [3]", exact: false }).first().click();
await page.waitForTimeout(600);
await page.getByRole("button", { name: "Geometrie", exact: true }).first().click();
await page.waitForTimeout(1500);
await shot("08_geometrie_nach_uebernehmen");

await browser.close();
console.log("done");
