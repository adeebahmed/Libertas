import { expect, test } from 'playwright/test'

function json(data: unknown) {
  return {
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(data),
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

    if (path === '/api/snapshots/current') {
      await route.fulfill(json({
        net_worth: 393070,
        delta_30d: 384559,
        delta_30d_pct: 4518.6,
        by_type: {
          brokerage: 150000,
          checking: 42000,
          savings: 65000,
          credit_card: -3500,
          mortgage: -185000,
        },
        last_updated: '2026-04-18T19:00:00Z',
      }))
      return
    }

    if (path === '/api/snapshots/net-worth') {
      await route.fulfill(json([
        { as_of: '2026-01-01', net_worth: 280000 },
        { as_of: '2026-02-01', net_worth: 302000 },
        { as_of: '2026-03-01', net_worth: 331000 },
        { as_of: '2026-04-01', net_worth: 393070 },
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
          title: 'Debt Payoff Path',
          description: 'No active debt payoff schedule detected from minimum-payment data.',
          category: 'Debt',
          priority: 'high',
          action: 'Add targeted extra principal to your highest-rate balance.',
          why: 'A focused payoff order lowers total interest and payoff duration.',
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
  await expect(page.getByTestId('dashboard-hero-shell')).toBeVisible()
})

test('collapsed-by-default divider stays above greeting', async ({ page }) => {
  const heroShell = page.getByTestId('dashboard-hero-shell')
  const greeting = page.getByTestId('overview-chat-greeting')

  await expect(heroShell).toHaveClass(/is-collapsed/)

  const shellBox = await heroShell.boundingBox()
  const greetingBox = await greeting.boundingBox()
  expect(shellBox).not.toBeNull()
  expect(greetingBox).not.toBeNull()

  const heroBottom = (shellBox?.y ?? 0) + (shellBox?.height ?? 0)
  const greetingTop = greetingBox?.y ?? 0
  expect(heroBottom).toBeLessThan(greetingTop)
})

test('collapsed chat composer stays anchored to the stage bottom border', async ({ page }) => {
  const stage = page.getByTestId('overview-chat-stage')
  const composer = page.getByTestId('overview-chat-composer')
  const toggle = page.getByTestId('dashboard-hero-toggle')

  const stageClosedBox = await stage.boundingBox()
  const composerClosedBox = await composer.boundingBox()
  expect(stageClosedBox).not.toBeNull()
  expect(composerClosedBox).not.toBeNull()

  await toggle.click()
  await expect(page.getByTestId('dashboard-hero-shell')).not.toHaveClass(/is-collapsed/)
  await page.waitForTimeout(450)

  const stageOpenBox = await stage.boundingBox()
  const composerOpenBox = await composer.boundingBox()
  expect(stageOpenBox).not.toBeNull()
  expect(composerOpenBox).not.toBeNull()

  const stageClosedBottom = (stageClosedBox?.y ?? 0) + (stageClosedBox?.height ?? 0)
  const stageOpenBottom = (stageOpenBox?.y ?? 0) + (stageOpenBox?.height ?? 0)
  const composerClosedBottom = (composerClosedBox?.y ?? 0) + (composerClosedBox?.height ?? 0)
  const composerOpenBottom = (composerOpenBox?.y ?? 0) + (composerOpenBox?.height ?? 0)

  expect(Math.abs(stageClosedBottom - stageOpenBottom)).toBeLessThanOrEqual(4)
  expect(Math.abs(composerClosedBottom - composerOpenBottom)).toBeLessThanOrEqual(4)
})

test('closed hero keeps lower cards in same position as open state', async ({ page }) => {
  const topGrid = page.getByTestId('dashboard-top-grid')
  const toggle = page.getByTestId('dashboard-hero-toggle')

  const closedTopGridBox = await topGrid.boundingBox()
  expect(closedTopGridBox).not.toBeNull()

  await toggle.click()
  await expect(page.getByTestId('dashboard-hero-shell')).not.toHaveClass(/is-collapsed/)
  await page.waitForTimeout(450)

  const openTopGridBox = await topGrid.boundingBox()
  expect(openTopGridBox).not.toBeNull()

  expect(Math.abs((closedTopGridBox?.y ?? 0) - (openTopGridBox?.y ?? 0))).toBeLessThanOrEqual(4)
})
