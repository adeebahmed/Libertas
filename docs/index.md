---
title: false
layout: doc
outline: false
aside: false
---

<div class="lp-shell">
  <Hero
    eyebrow="Private personal finance"
    headline="All your accounts. One private view."
    sub="Twelve logins. Five spreadsheets. None of it has to touch the cloud. Consolidate, understand trajectory, and act with confidence from one local-first dashboard."
    cta-primary-text="Download"
    cta-primary-link="/download/"
    cta-secondary-text="See features"
    cta-secondary-link="/features/"
    screenshot="/screenshots/placeholder.png"
    screenshot-alt="Libertas dashboard showing net worth trend, allocation, and account balances"
    :trust-items="['100% local', 'No account linking', 'Open source', 'MIT']"
  />

  <section class="lp-problem" aria-label="Problem statement">
    <p>Twelve logins.</p>
    <p>Five spreadsheets.</p>
    <p>Zero clarity.</p>
  </section>

  <ProductWalkthrough
    :steps="[
      {
        title: 'Dashboard',
        body: 'Net worth, allocation, and trajectory in one screen. Open the app and see where you stand in seconds.',
        screenshot: '/screenshots/placeholder.png',
        alt: 'Dashboard walkthrough screenshot'
      },
      {
        title: 'Accounts',
        body: 'Fidelity, Schwab, Coinbase, Chase, Vanguard. Side by side. No OAuth, no account-link dependency.',
        screenshot: '/screenshots/placeholder.png',
        alt: 'Accounts walkthrough screenshot'
      },
      {
        title: 'Import',
        body: 'Drop CSVs into data/watch and Libertas does the parsing. First import teaches. Next imports get faster.',
        screenshot: '/screenshots/placeholder.png',
        alt: 'Import workflow screenshot'
      },
      {
        title: 'Real Estate',
        body: 'Track Zillow estimates, manual overrides, and equity in the same place as your investments.',
        screenshot: '/screenshots/placeholder.png',
        alt: 'Real estate workflow screenshot'
      },
      {
        title: 'Projections',
        body: 'Model decade-scale outcomes from contribution and return assumptions before you commit to a strategy.',
        screenshot: '/screenshots/placeholder.png',
        alt: 'Projections workflow screenshot'
      },
      {
        title: 'Insights',
        body: 'Catch drift, concentration risk, and debt signals early. Optional Claude chat stays opt-in.',
        screenshot: '/screenshots/placeholder.png',
        alt: 'Insights workflow screenshot'
      }
    ]"
  />

  <FeatureGrid
    :features="[
      { icon: '◎', title: 'Dashboard', oneLine: 'Net worth at a glance.', href: '/features/dashboard' },
      { icon: '◫', title: 'Accounts', oneLine: 'All of them. One roof.', href: '/features/accounts' },
      { icon: '↥', title: 'Import', oneLine: 'Drop a CSV. Done.', href: '/features/import' },
      { icon: '⌂', title: 'Real Estate', oneLine: 'Zillow + override.', href: '/features/real-estate' },
      { icon: '◷', title: 'Projections', oneLine: 'Today\'s choice. Ten-year view.', href: '/features/projections' },
      { icon: '✦', title: 'Insights', oneLine: 'Drift. Risk. Caught early.', href: '/features/insights' }
    ]"
  />

  <section class="lp-proof-slot" aria-label="Proof section placeholder">
    Proof section reserved for v2
  </section>

  <PrivacyStrip
    :bullets="[
      'No account linking required',
      'No cloud sync dependency for core value',
      'Optional AI chat is explicit opt-in'
    ]"
    link-href="/privacy/"
    link-text="Why local-first matters"
  />

  <FAQ
    :items="[
      { q: 'Is Libertas free?', a: 'Yes. Libertas is MIT licensed and self-hosted.' },
      { q: 'What platforms are supported?', a: 'Mac first, Linux tested, and Windows via WSL.' },
      { q: 'Where is my data stored?', a: 'In data/libertas.db on your machine.' },
      { q: 'Where does price data come from?', a: 'yfinance for stocks and CoinGecko for crypto, no paid API required.' },
      { q: 'How do backups work?', a: 'Copy your .db file or use built-in backup checkpoints.' },
      { q: 'Does Libertas use Plaid?', a: 'No. CSV and Excel imports are the default workflow.' }
    ]"
  />

  <CTABlock
    title="Download Libertas and start fresh with one private financial view."
    sub="Install locally, import your files, and get a reliable command center for your money decisions."
    install-cmd="git clone https://github.com/adeebahmed/Libertas && cd Libertas && ./start.sh"
    primary-text="Download"
    primary-href="/download/"
    secondary-text="GitHub"
    secondary-href="https://github.com/adeebahmed/Libertas"
  />
</div>
