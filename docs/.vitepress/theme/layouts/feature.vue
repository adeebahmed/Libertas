<script setup lang="ts">
import { computed } from 'vue'
import { useData, withBase } from 'vitepress'

const { frontmatter } = useData()

const heroImage = computed(() => withBase(String(frontmatter.value.heroImage ?? '/screenshots/placeholder.png')))
const heroAlt = computed(() => String(frontmatter.value.heroAlt ?? 'Feature screenshot'))
const tagline = computed(() => String(frontmatter.value.tagline ?? ''))
const what = computed(() => (Array.isArray(frontmatter.value.what) ? frontmatter.value.what : []))
const how = computed(() => (Array.isArray(frontmatter.value.how) ? frontmatter.value.how : []))
const privateByDesign = computed(() => String(frontmatter.value.privateByDesign ?? ''))
const gallery = computed(() => (Array.isArray(frontmatter.value.gallery) ? frontmatter.value.gallery : []))
const ctaTitle = computed(() => String(frontmatter.value.ctaTitle ?? 'Run Libertas locally. Keep full control.'))
const ctaSub = computed(() => String(frontmatter.value.ctaSub ?? 'No account linking required. No cloud lock-in.'))
</script>

<template>
  <main class="lp-feature-layout">
    <p class="lp-feature-back"><a href="/features/">← All features</a></p>

    <section class="lp-feature-hero">
      <div>
        <p class="lp-kicker">Feature</p>
        <h1 class="lp-feature-title">{{ frontmatter.title }}</h1>
        <p class="lp-feature-tagline">{{ tagline }}</p>
        <div class="lp-hero-actions">
          <a class="lp-btn lp-btn-primary" href="/download/">Download</a>
          <a class="lp-btn lp-btn-secondary" href="https://github.com/adeebahmed/Libertas">GitHub</a>
        </div>
      </div>
      <div class="lp-feature-shot-wrap" aria-hidden="true">
        <img class="lp-feature-shot" :src="heroImage" :alt="heroAlt" loading="eager" decoding="async" />
      </div>
    </section>

    <section class="lp-feature-content-grid">
      <article class="lp-feature-panel">
        <p class="lp-kicker">What it does</p>
        <p v-for="line in what" :key="line" class="lp-feature-copy">{{ line }}</p>
      </article>

      <article class="lp-feature-panel">
        <p class="lp-kicker">How it works</p>
        <ol class="lp-feature-steps">
          <li v-for="step in how" :key="step">{{ step }}</li>
        </ol>
      </article>

      <article class="lp-feature-panel">
        <p class="lp-kicker">Private by design</p>
        <p class="lp-feature-copy">{{ privateByDesign }}</p>
      </article>
    </section>

    <section class="lp-feature-gallery">
      <img
        v-for="(image, index) in gallery"
        :key="`${image}-${index}`"
        :src="withBase(String(image))"
        :alt="`${frontmatter.title} supporting screenshot ${index + 1}`"
        loading="lazy"
        decoding="async"
      />
    </section>

    <CTABlock :title="ctaTitle" :sub="ctaSub" />
  </main>
</template>
