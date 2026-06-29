/**
 * Domain purpose:
 *   Render the PR-0406 small-screen Exam Converter decision mockup from the
 *   checked-in HTML/CSS source into the canonical PNG preview.
 */

import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
const puppeteer = require("../../../tools/puppeteer/node_modules/puppeteer");

const here = dirname(fileURLToPath(import.meta.url));
const source = join(here, "index.html");
const output = join(here, "approved-small-screen-answer-key-review-v1.png");

const browser = await puppeteer.launch({
  headless: "new",
  args: ["--no-sandbox"],
});

try {
  const page = await browser.newPage();
  await page.setViewport({
    width: 1768,
    height: 960,
    deviceScaleFactor: 1,
  });
  await page.goto(pathToFileURL(source).href, { waitUntil: "networkidle0" });
  await page.screenshot({ path: output, fullPage: false });
} finally {
  await browser.close();
}
