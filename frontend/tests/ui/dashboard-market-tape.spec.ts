import { expect, test } from 'playwright/test'

function json(data: unknown) {
  return {
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(data),
  }
}

function makeTapePayload() {
  const news = Array.from({ length: 10 }, (_, i) => ({
    id: `news-${i + 1}`,
    label: `Market headline ${i + 1}`,
    url: `https://news.example.com/article-${i + 1}`,
    source: 'Reuters',
    published_at: '2026-04-19T12:00:00Z',
  }))

  const tickers = [
    { id: 'sym-AAPL', symbol: 'AAPL', price: 212.44, market_value: 85210, portfolio_weight_pct: 22.7, last_updated: '2026-04-19T12:00:00Z' },
    { id: 'sym-MSFT', symbol: 'MSFT', price: 425.1, market_value: 72210, portfolio_weight_pct: 19.2, last_updated: '2026-04-19T12:00:00Z' },
  ]

  const personal = [
    { id: 'p-top-insight', label: 'Insight: Concentration risk elevated in one position.', tone: 'negative', route: '/insights' },
    { id: 'p-stale-accounts', label: 'Account freshness: 1/4 accounts may be stale (7d+).', tone: 'neutral', route: '/accounts' },
  ]

  return {
    generated_at: '2026-04-19T22:10:00Z',
    segments: { news, tickers, personal },
    sequence: [
      ...news.slice(0, 8).map((item) => ({ kind: 'news', ref_id: item.id })),
      ...tickers.map((item) => ({ kind: 'ticker', ref_id: item.id })),
      ...personal.map((item) => ({ kind: 'personal', ref_id: item.id })),
      ...news.slice(8).map((item) => ({ kind: 'news', ref_id: item.id })),
      ...tickers.map((item) => ({ kind: 'ticker', ref_id: item.id })),
      ...personal.map((item) => ({ kind: 'personal', ref_id: item.id })),
    ],
  }
}

test.beforeEach(async ({ page }) => {
  await page.route('**/*', async (route) => {
    const requestUrl = new URL(route.request().url())
    const path = requestUrl.pathname
    if (!path.startsWith('/api/')) {
      await route.continue()
      return
    }

    if (path === '/api/dashboard/tape') {
      await route.fulfill(json(makeTapePayload()))
      return
    }

    if (path === '/api/snapshots/current') {
      await route.fulfill(json({
        net_worth: 393070,
        delta_30d: 384559,
        delta_30d_pct: 4518.6,
        by_type: { brokerage: 150000, checking: 42000 },
        last_updated: '2026-04-18T19:00:00Z',
      }))
      return
    }

    if (path === '/api/snapshots/net-worth') {
      await route.fulfill(json([
        { as_of: '2026-01-01', net_worth: 280000 },
        { as_of: '2026-02-01', net_worth: 302000 },
      ]))
      return
    }

    if (path === '/api/accounts') {
      await route.fulfill(json([]))
      return
    }

    if (path === '/api/insights') {
      await route.fulfill(json([
        {
          title: 'Concentration Risk',
          description: 'Portfolio concentration is elevated.',
          category: 'Risk',
          priority: 'high',
          action: 'Rebalance across holdings.',
          why: 'Diversification reduces drawdown risk.',
        },
      ]))
      return
    }

    if (path === '/api/settings') {
      await route.fulfill(json({ username: 'Adeeb' }))
      return
    }

    await route.fulfill(json({}))
  })

  await page.goto('/', { waitUntil: 'domcontentloaded' })
})

test('market tape is visible only while hero is collapsed', async ({ page }) => {
  const tape = page.getByTestId('dashboard-market-tape')
  const toggle = page.getByTestId('dashboard-hero-toggle')

  await expect(tape).toBeVisible()
  await toggle.click()
  await expect(page.getByTestId('dashboard-hero-shell')).not.toHaveClass(/is-collapsed/)
  await expect(tape).toHaveCount(0)
  await toggle.click()
  await expect(page.getByTestId('dashboard-hero-shell')).toHaveClass(/is-collapsed/)
  await expect(page.getByTestId('dashboard-market-tape')).toBeVisible()
})

test('market tape does not overlap the hero toggle control', async ({ page }) => {
  const tape = page.getByTestId('dashboard-market-tape')
  const toggle = page.getByTestId('dashboard-hero-toggle')

  await expect(tape).toBeVisible()
  const tapeBox = await tape.boundingBox()
  const toggleBox = await toggle.boundingBox()
  expect(tapeBox).not.toBeNull()
  expect(toggleBox).not.toBeNull()
  expect((tapeBox?.x ?? 0) + (tapeBox?.width ?? 0)).toBeLessThanOrEqual((toggleBox?.x ?? 0) + 2)
})

test('news items render as clickable headline links', async ({ page }) => {
  const firstNews = page.getByTestId('market-tape-news-link').first()
  await expect(firstNews).toBeVisible()
  await expect(firstNews).toHaveAttribute('href', /https:\/\/news\.example\.com\/article-/)
})

test.describe('reduced motion', () => {
  test('disables marquee animation and keeps tape readable', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.goto('/', { waitUntil: 'domcontentloaded' })

    const reduceMatches = await page.evaluate(() => {
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches
    })
    expect(reduceMatches).toBeTruthy()

    const animationName = await page.locator('.dashboard-market-tape-track').evaluate((node) => {
      return window.getComputedStyle(node).animationName
    })
    expect(animationName).toBe('none')
  })
})
