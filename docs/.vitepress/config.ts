import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Libertas',
  description: 'Locally-hosted personal finance dashboard. No cloud. No account linking. Your data stays on your machine.',
  base: '/Libertas/',

  themeConfig: {
    nav: [
      { text: 'Home', link: '/' },
      { text: 'ADRs', link: '/adr/001-finance-dashboard-design' },
    ],

    sidebar: [
      {
        text: 'Architecture Decisions',
        items: [
          { text: 'ADR-001 — Finance Dashboard Design', link: '/adr/001-finance-dashboard-design' },
        ],
      },
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/adeebahmed/Libertas' },
    ],

    footer: {
      message: 'Privacy as a feature. No SaaS, no cloud, no account linking.',
    },
  },
})
