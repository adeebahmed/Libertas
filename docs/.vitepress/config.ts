import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Libertas',
  description: 'Private, local-first personal finance command center. No cloud lock-in, no mandatory account linking.',
  base: '/Libertas/',

  themeConfig: {
    nav: [
      { text: 'Product', link: '/' },
      { text: 'Technical Docs', link: '/technical' },
      { text: 'GitHub', link: 'https://github.com/adeebahmed/Libertas' },
    ],

    sidebar: [
      {
        text: 'Libertas',
        items: [
          { text: 'Product Overview', link: '/' },
          { text: 'Technical Docs', link: '/technical' },
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
        ],
      },
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/adeebahmed/Libertas' },
    ],

    footer: {
      message: 'Privacy as a feature. Local-first by default.',
    },
  },
})
