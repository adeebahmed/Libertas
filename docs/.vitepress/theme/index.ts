import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'

import Hero from './components/Hero.vue'
import ProductWalkthrough from './components/ProductWalkthrough.vue'
import FeatureGrid from './components/FeatureGrid.vue'
import PrivacyStrip from './components/PrivacyStrip.vue'
import FAQ from './components/FAQ.vue'
import CTABlock from './components/CTABlock.vue'
import FeatureLayout from './layouts/feature.vue'

import './custom.css'

const theme: Theme = {
  ...DefaultTheme,
  enhanceApp(ctx) {
    DefaultTheme.enhanceApp?.(ctx)
    ctx.app.component('Hero', Hero)
    ctx.app.component('ProductWalkthrough', ProductWalkthrough)
    ctx.app.component('FeatureGrid', FeatureGrid)
    ctx.app.component('PrivacyStrip', PrivacyStrip)
    ctx.app.component('FAQ', FAQ)
    ctx.app.component('CTABlock', CTABlock)
    ctx.app.component('feature', FeatureLayout)
  },
}

export default theme
