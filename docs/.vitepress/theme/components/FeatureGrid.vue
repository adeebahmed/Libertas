<script setup lang="ts">
type Feature = {
  icon?: string
  title: string
  oneLine: string
  href: string
}

const props = defineProps<{ features: Feature[] }>()
</script>

<template>
  <section class="lp-feature-grid-section">
    <div class="lp-section-head">
      <p class="lp-kicker">Features</p>
      <h2>Built for clarity, speed, and control.</h2>
    </div>

    <div class="lp-feature-grid">
      <a v-for="feature in props.features" :key="feature.title" :href="feature.href" class="lp-feature-card">
        <span class="lp-feature-icon" aria-hidden="true">{{ feature.icon ?? '•' }}</span>
        <h3>{{ feature.title }}</h3>
        <p>{{ feature.oneLine }}</p>
      </a>
    </div>
  </section>
</template>
