<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    title?: string
    sub?: string
    installCmd?: string
    primaryText?: string
    primaryHref?: string
    secondaryText?: string
    secondaryHref?: string
  }>(),
  {
    title: 'Ready to try Libertas?',
    sub: 'Install locally and get your full financial view in minutes.',
    installCmd: 'git clone https://github.com/adeebahmed/Libertas && cd Libertas && ./start.sh',
    primaryText: 'Download',
    primaryHref: 'https://github.com/adeebahmed/Libertas',
    secondaryText: 'Install guide',
    secondaryHref: '/download/',
  },
)
</script>

<template>
  <section class="lp-cta-block">
    <h2>{{ title }}</h2>
    <p>{{ sub }}</p>
    <code>{{ installCmd }}</code>
    <div class="lp-hero-actions">
      <a class="lp-btn lp-btn-primary" :href="primaryHref">{{ primaryText }}</a>
      <a class="lp-btn lp-btn-secondary" :href="secondaryHref">{{ secondaryText }}</a>
    </div>
  </section>
</template>
