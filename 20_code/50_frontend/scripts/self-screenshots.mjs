// Self-review screenshots: click through every tree node + editor tab of the running
// workbench (http://localhost:3000, backend on :8000) and save one PNG per view.
// Usage:  node scripts/self-screenshots.mjs <outDir>
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const OUT = process.argv[2] ?? "self_shots";
mkdirSync(OUT, { recursive: true });

const NODES = [
  {
    node: "Getriebeeinheit [1]",
    tabs: [
      "Berechnungsauswahl",
      "Leistungsfluss",
      "Kräfte und Momente",
      "Betriebsdaten",
      "Steuerparameter",
    ],
  },
  {
    node: "Stirnradstufe [3]",
    tabs: [
      "Auslegung",
      "Geometrie",
      "Tragfähigkeit",
      "Dynamikfaktoren",
      "Dynamisches Abwälzen (FEM)",
      "FE-Abwälzmodell (Ansicht)",
    ],
  },
  { node: "Stahlritzel [8]", tabs: ["Zahnform", "FE-Mesh"] },
  { node: "Kunststoffrad [9]", tabs: ["Zahnform", "FE-Mesh"] },
  { node: "Stufenvariation", tabs: ["Stufenvariation"] },
  { node: "Legende & Parameter", tabs: [] },
];

const slug = (s) =>
  s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-zA-Z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1720, height: 1000 } });
page.on("pageerror", (e) => console.log("PAGEERROR:", e.message));
page.on("console", (m) => {
  if (m.type() === "error") console.log("CONSOLE-ERROR:", m.text());
});
await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
await page.waitForTimeout(1500);

for (const { node, tabs } of NODES) {
  const nodeBtn = page.getByRole("button", { name: node, exact: false }).first();
  try {
    await nodeBtn.click({ timeout: 4000 });
  } catch {
    console.log(`MISSING NODE: ${node}`);
    continue;
  }
  await page.waitForTimeout(900);
  if (tabs.length === 0) {
    await page.screenshot({ path: `${OUT}/${slug(node)}.png`, fullPage: false });
    console.log(`shot: ${slug(node)}.png`);
    continue;
  }
  for (const tab of tabs) {
    const tabBtn = page.getByRole("button", { name: tab, exact: true }).first();
    try {
      await tabBtn.click({ timeout: 4000 });
    } catch {
      console.log(`MISSING TAB: ${node} -> ${tab}`);
      continue;
    }
    await page.waitForTimeout(1200);
    const file = `${OUT}/${slug(node)}__${slug(tab)}.png`;
    await page.screenshot({ path: file, fullPage: false });
    console.log(`shot: ${slug(node)}__${slug(tab)}.png`);
  }
}
await browser.close();
console.log("done");
