// One-off: capture the 2D section view of the FE mesh (self-review helper).
import { chromium } from "playwright";

const out = process.argv[2] ?? "mesh2d.png";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1720, height: 1000 } });
page.on("console", (m) => {
  if (m.type() === "error") console.log("CONSOLE-ERROR:", m.text());
});
await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
await page.waitForTimeout(1200);
await page.getByRole("button", { name: "Kunststoffrad [9]", exact: false }).first().click();
await page.waitForTimeout(600);
await page.getByRole("button", { name: "FE-Mesh", exact: true }).first().click();
await page.waitForTimeout(600);
await page.locator("select").filter({ hasText: "3D-Ansicht" }).selectOption("2d");
await page.getByRole("button", { name: "Mesh erzeugen", exact: true }).click();
// wait for the mesh statistics (generation done) instead of a fixed sleep
await page.waitForSelector("text=/min J|Quads/", { timeout: 60000 }).catch(() => console.log("TIMEOUT waiting for mesh"));
await page.waitForTimeout(800);
await page.screenshot({ path: out });
console.log("shot:", out);
await browser.close();
