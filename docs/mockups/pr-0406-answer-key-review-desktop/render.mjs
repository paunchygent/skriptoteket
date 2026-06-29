/**
 * Domain purpose:
 *   Render the PR-0406 desktop Exam Converter decision mockups from checked-in
 *   HTML/CSS source into PNG previews.
 */

import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
const puppeteer = require("../../../tools/puppeteer/node_modules/puppeteer");

const here = dirname(fileURLToPath(import.meta.url));
const source = join(here, "index.html");

const shots = [
  ["questions", "desktop-question-review-v1.png"],
  ["edit", "desktop-edit-facit-v1.png"],
  ["files", "desktop-files-mode-v1.png"],
  ["report", "desktop-report-mode-v1.png"],
];

const browser = await puppeteer.launch({
  headless: "new",
  args: ["--no-sandbox"],
});

try {
  const page = await browser.newPage();
  await page.setViewport({
    width: 1790,
    height: 1030,
    deviceScaleFactor: 1,
  });
  await page.goto(pathToFileURL(source).href, { waitUntil: "networkidle0" });
  for (const [id, filename] of shots) {
    const element = await page.$(`#${id}`);
    if (!element) {
      throw new Error(`Missing mockup frame: ${id}`);
    }
    await element.screenshot({ path: join(here, filename) });
  }
} finally {
  await browser.close();
}
