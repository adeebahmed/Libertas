<script setup lang="ts">
import { computed } from 'vue'
import { withBase } from 'vitepress'

interface HeroProps {
  eyebrow?: string
  headline: string
  sub: string
  ctaPrimaryText: string
  ctaPrimaryLink: string
  ctaSecondaryText: string
  ctaSecondaryLink: string
  screenshot: string
  screenshotAlt?: string
  trustItems?: string[]
}

const props = withDefaults(defineProps<HeroProps>(), {
  eyebrow: 'Local-first personal finance',
  screenshotAlt: 'Libertas dashboard screenshot',
  trustItems: () => ['100% local', 'No account linking', 'Open source', 'MIT'],
})

const heroImage = computed(() => withBase(props.screenshot))
</script>

<template>
  <section class="lp-hero">
    <div class="lp-hero-inner">
      <div class="lp-hero-copy">
        <p class="lp-eyebrow">{{ eyebrow }}</p>
        <h1 class="lp-hero-title">{{ headline }}</h1>
        <p class="lp-hero-sub">{{ sub }}</p>

        <div class="lp-hero-actions">
          <a class="lp-btn lp-btn-primary" :href="ctaPrimaryLink">{{ ctaPrimaryText }}</a>
          <a class="lp-btn lp-btn-secondary" :href="ctaSecondaryLink">{{ ctaSecondaryText }}</a>
        </div>

        <ul class="lp-trust-strip" aria-label="Trust and privacy highlights">
          <li v-for="item in trustItems" :key="item" class="lp-trust-item">{{ item }}</li>
        </ul>
      </div>

      <div class="lp-hero-shot-wrap" aria-hidden="true">
        <img class="lp-hero-shot" :src="heroImage" :alt="screenshotAlt" loading="eager" decoding="async" />
      </div>
    </div>
  </section>
</template>
