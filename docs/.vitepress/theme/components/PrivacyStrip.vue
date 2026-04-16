<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    bullets?: string[]
    linkHref?: string
    linkText?: string
  }>(),
  {
    bullets: () => [
      'No account linking required',
      'No cloud sync dependency',
      'You control your data lifecycle',
    ],
    linkHref: '/privacy/',
    linkText: 'Read the privacy model',
  },
)
</script>

<template>
  <section class="lp-privacy-strip">
    <div class="lp-privacy-inner">
      <div>
        <p class="lp-kicker">Why private</p>
        <h2>Privacy is the product, not a settings toggle.</h2>
      </div>
      <ul>
        <li v-for="bullet in bullets" :key="bullet">{{ bullet }}</li>
      </ul>
      <a :href="linkHref" class="lp-text-link">{{ linkText }}</a>
    </div>
  </section>
</template>
