import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Libertas',
  description: 'Private, local-first personal finance command center. No cloud lock-in, no mandatory account linking.',
  base: '/Libertas/',

  themeConfig: {
    nav: [
      { text: 'Overview', link: '/' },
      { text: 'User Guide', link: '/guide/user-guide' },
      { text: 'Technical', link: '/technical' },
      { text: 'ADRs', link: '/adr/' },
      { text: 'Security', link: '/security' },
      { text: 'GitHub', link: 'https://github.com/adeebahmed/Libertas' },
    ],

    sidebar: [
      {
        text: 'Get Started',
        items: [
          { text: 'Product Overview', link: '/' },
          { text: 'User Guide (Happy Path)', link: '/guide/user-guide' },
          { text: 'API Keys & Integrations', link: '/guide/api-keys-and-integrations' },
        ],
      },
      {
        text: 'Engineering',
        items: [
          { text: 'Technical Overview', link: '/technical' },
          { text: 'Security & Encryption', link: '/security' },
          { text: 'ADR Index', link: '/adr/' },
        ],
      },
      {
        text: 'Architecture Decisions',
        items: [
          { text: 'ADR-001 — Finance Dashboard Design', link: '/adr/001-finance-dashboard-design' },
          { text: 'ADR-002 — Data Ingestion Strategy', link: '/adr/002-data-ingestion-strategy' },
          { text: 'ADR-002 — Taxes Page', link: '/adr/002-taxes-page' },
          { text: 'ADR-003 — News Feed', link: '/adr/003-news-feed' },
          { text: 'ADR-004 — User Profile + AI Guidance', link: '/adr/004-user-profile-and-ai-guidance' },
          { text: 'ADR-005 — Versioned Backups', link: '/adr/005-versioned-backups' },
          { text: 'ADR-006 — Tier-1 Dashboard Completion', link: '/adr/006-tier1-dashboard-completion' },
          { text: 'ADR-007 — Terminal Design System', link: '/adr/007-terminal-design-system' },
          { text: 'ADR-008 — Command Palette + Keyboard Nav', link: '/adr/008-command-palette-keyboard-nav' },
          { text: 'ADR-009 — Plaid + Sheets Integration', link: '/adr/009-optional-plaid-and-sheets-integration' },
          { text: 'ADR-010 — At-Rest Encryption', link: '/adr/010-at-rest-encryption' },
        ],
      },
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/adeebahmed/Libertas' },
    ],

    darkModeSwitchLabel: 'Theme',
    lightModeSwitchTitle: 'Switch to Onyx',
    darkModeSwitchTitle: 'Switch to Retro',

    footer: {
      message: 'Privacy as a feature. Local-first by default.',
    },
  },
})
