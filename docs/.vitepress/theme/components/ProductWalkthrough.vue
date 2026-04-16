<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { ComponentPublicInstance } from 'vue'
import { withBase } from 'vitepress'

type Step = {
  title: string
  body: string
  screenshot: string
  alt?: string
}

const props = defineProps<{ steps: Step[] }>()

const activeIndex = ref(0)
const stepEls = ref<(HTMLElement | null)[]>([])
let observer: IntersectionObserver | null = null

const normalized = computed(() =>
  props.steps.map((step) => ({
    ...step,
    alt: step.alt ?? `${step.title} screenshot`,
    src: withBase(step.screenshot),
  })),
)

function setStepRef(el: Element | ComponentPublicInstance | null, index: number) {
  stepEls.value[index] = (el as HTMLElement | null) ?? null
}

function focusStep(index: number) {
  const el = stepEls.value[index]
  if (!el) return
  activeIndex.value = index
  el.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

onMounted(() => {
  if (!normalized.value.length) return
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const threshold = reducedMotion ? 0.2 : 0.55

  observer = new IntersectionObserver(
    (entries) => {
      let best: { idx: number; ratio: number } | null = null
      for (const entry of entries) {
        const idx = Number((entry.target as HTMLElement).dataset.stepIndex)
        if (Number.isNaN(idx)) continue
        if (!best || entry.intersectionRatio > best.ratio) {
          best = { idx, ratio: entry.intersectionRatio }
        }
      }
      if (best && best.ratio >= threshold) {
        activeIndex.value = best.idx
      }
    },
    {
      rootMargin: '-15% 0px -35% 0px',
      threshold: [0.15, 0.35, 0.55, 0.75],
    },
  )

  stepEls.value.forEach((el, index) => {
    if (!el) return
    el.dataset.stepIndex = String(index)
    observer?.observe(el)
  })
})

onBeforeUnmount(() => {
  observer?.disconnect()
})
</script>

<template>
  <section id="how-it-works" class="lp-walkthrough">
    <header class="lp-walk-header">
      <p class="lp-kicker">How it works</p>
      <h2>One private system for your full financial picture.</h2>
    </header>

    <div class="lp-walk-body">
      <ol class="lp-walk-steps">
        <li
          v-for="(step, index) in normalized"
          :key="step.title"
          :ref="(el) => setStepRef(el, index)"
          class="lp-walk-step"
          :class="{ active: index === activeIndex }"
        >
          <button
            class="lp-walk-step-button"
            type="button"
            :aria-current="index === activeIndex ? 'step' : undefined"
            @click="focusStep(index)"
          >
            <span class="lp-walk-dot" aria-hidden="true"></span>
            <span class="lp-walk-step-content">
              <span class="lp-walk-step-title">{{ step.title }}</span>
              <span class="lp-walk-step-body">{{ step.body }}</span>
            </span>
          </button>
        </li>
      </ol>

      <aside class="lp-walk-media" aria-live="polite">
        <div class="lp-walk-media-frame">
          <img
            v-for="(step, index) in normalized"
            :key="`${step.title}-${index}`"
            class="lp-walk-image"
            :class="{ active: index === activeIndex }"
            :src="step.src"
            :alt="step.alt"
            loading="lazy"
            decoding="async"
          />
        </div>
      </aside>
    </div>
  </section>
</template>
