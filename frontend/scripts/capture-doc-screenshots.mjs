import { chromium } from 'playwright'
import fs from 'node:fs/promises'
import path from 'node:path'

const outDir = path.resolve(process.cwd(), '..', 'docs', 'public', 'screenshots')

async function ensureDir(dir) {
  await fs.mkdir(dir, { recursive: true })
}

async function captureOverview(theme, filename) {
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1720, height: 1024 } })
  const page = await context.newPage()

  await page.goto('http://127.0.0.1:5173/', { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(2200)

  if (theme === 'retro') {
    await page.goto('http://127.0.0.1:5173/settings', { waitUntil: 'domcontentloaded' })
    await page.waitForSelector('select')
    await page.selectOption('select', 'retro')
    await page.waitForTimeout(700)
    await page.goto('http://127.0.0.1:5173/', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2200)
  }

  await page.screenshot({ path: path.join(outDir, filename), fullPage: true })
  await browser.close()
}

await ensureDir(outDir)
await captureOverview('onyx', 'overview-onyx.png')
await captureOverview('retro', 'overview-retro.png')
