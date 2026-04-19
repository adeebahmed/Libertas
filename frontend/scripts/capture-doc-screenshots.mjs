import { chromium } from 'playwright'
import fs from 'node:fs/promises'
import path from 'node:path'

const outDir = path.resolve(process.cwd(), '..', 'docs', 'public', 'screenshots')
const candidateBaseUrls = [
  process.env.FRONTEND_URL,
  'http://127.0.0.1:5173',
  'http://127.0.0.1:5174',
].filter(Boolean)

async function resolveBaseUrl(browser) {
  const page = await browser.newPage()
  for (const url of candidateBaseUrls) {
    try {
      const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 3500 })
      if (response && response.ok()) {
        await page.close()
        return url
      }
    } catch {
      // try next URL
    }
  }
  await page.close()
  throw new Error(`No reachable frontend URL. Tried: ${candidateBaseUrls.join(', ')}`)
}

async function ensureDir(dir) {
  await fs.mkdir(dir, { recursive: true })
}

async function captureOverview(theme, filename) {
  const browser = await chromium.launch({ headless: true })
  const baseUrl = await resolveBaseUrl(browser)
  const context = await browser.newContext({ viewport: { width: 1720, height: 1024 } })
  const page = await context.newPage()

  await page.goto(`${baseUrl}/`, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(2200)

  if (theme === 'retro') {
    await page.goto(`${baseUrl}/settings`, { waitUntil: 'domcontentloaded' })
    await page.waitForSelector('select')
    await page.selectOption('select', 'retro')
    await page.waitForTimeout(700)
    await page.goto(`${baseUrl}/`, { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2200)
  }

  await page.screenshot({ path: path.join(outDir, filename), fullPage: true })
  await browser.close()
}

await ensureDir(outDir)
await captureOverview('onyx', 'overview-onyx.png')
await captureOverview('retro', 'overview-retro.png')
