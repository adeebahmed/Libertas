<script setup lang="ts">
import { ref } from 'vue'

type FAQItem = {
  q: string
  a: string
}

const props = defineProps<{ items: FAQItem[] }>()
const openIndex = ref(0)

function toggle(index: number) {
  openIndex.value = openIndex.value === index ? -1 : index
}
</script>

<template>
  <section class="lp-faq">
    <div class="lp-section-head">
      <p class="lp-kicker">FAQ</p>
      <h2>Short answers before you install.</h2>
    </div>

    <div class="lp-faq-list">
      <article
        v-for="(item, index) in props.items"
        :key="item.q"
        class="lp-faq-item"
        :class="{ open: openIndex === index }"
      >
        <button
          class="lp-faq-q"
          type="button"
          :aria-expanded="openIndex === index"
          @click="toggle(index)"
        >
          <span>{{ item.q }}</span>
          <span aria-hidden="true">{{ openIndex === index ? '−' : '+' }}</span>
        </button>
        <div class="lp-faq-a">
          <p>{{ item.a }}</p>
        </div>
      </article>
    </div>
  </section>
</template>
