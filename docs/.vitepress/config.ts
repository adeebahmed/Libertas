import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Libertas',
  description: 'All your accounts. One private view.',
  base: '/Libertas/',

  themeConfig: {
    nav: [
      { text: 'Features', link: '/features/' },
      { text: 'Why Private', link: '/privacy/' },
      { text: 'Download', link: '/download/' },
    ],
    sidebar: false,

    socialLinks: [
      { icon: 'github', link: 'https://github.com/adeebahmed/Libertas' },
    ],

    footer: {
      message: 'Local-first personal finance for people who want control.',
    },
  },
})
