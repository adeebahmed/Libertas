import type { Insight } from '../types'

type InsightCopy = Pick<Insight, 'title' | 'description' | 'action' | 'why'>
type InsightCardCopy = {
  title: string
  summary: string
  action: string
}

const PHRASE_REPLACEMENTS: Array<[RegExp, string]> = [
  [/\b401k\b/gi, '401(k)'],
  [/\bIRA\b/gi, 'IRA'],
  [/\bDTI\b/gi, 'debt-to-income ratio'],
  [/\bLTV\b/gi, 'loan-to-value ratio'],
  [/\bAPR\b/gi, 'interest rate'],
  [/\bROI\b/gi, 'return'],
  [/\bvolatility\b/gi, 'ups and downs'],
  [/\bliquidity\b/gi, 'cash you can use now'],
  [/\bconcentration risk\b/gi, 'too-much-in-one-place risk'],
  [/\bdiversification\b/gi, 'spreading your money out'],
  [/\bharvesting\b/gi, 'tax-loss harvesting'],
  [/\brebalance\b/gi, 'rebalance (move money back to your target mix)'],
  [/\boptimi[sz]e\b/gi, 'improve'],
  [/\bprioriti[sz]e\b/gi, 'focus on'],
  [/\belevated\b/gi, 'high'],
  [/\bmitigate\b/gi, 'lower'],
  [/\butili[sz]ation\b/gi, 'usage'],
  [/\btrajectory\b/gi, 'path'],
  [/\bamplifies\b/gi, 'boosts'],
  [/\bconsistency\b/gi, 'staying steady'],
  [/\bthreshold\b/gi, 'limit'],
  [/\bposition\b/gi, 'amount'],
  [/\basset class(?:es)?\b/gi, 'money buckets'],
  [/\bequities\b/gi, 'stocks'],
  [/\bliabilities\b/gi, 'debt'],
  [/\bcontributions?\b/gi, 'money you add'],
  [/\brecurring monthly contributions?\b/gi, 'monthly adds'],
  [/\bpassive income\b/gi, 'income that comes in without extra work'],
  [/\bretirement readiness\b/gi, 'retirement progress'],
  [/\bfire timeline\b/gi, 'freedom timeline'],
  [/\btrajectory\b/gi, 'direction'],
  [/\bcompound(?:ing)?\b/gi, 'growth over time'],
  [/\bannual limits?\b/gi, 'yearly limits'],
  [/\bunsystematic\b/gi, 'single-stock'],
]

function toSingleLine(text: string) {
  return text.replace(/\s+/g, ' ').trim()
}

function addFinalPeriod(text: string) {
  if (!text) return text
  return /[.!?]$/.test(text) ? text : `${text}.`
}

function simplifyText(raw: string) {
  let text = toSingleLine(raw)

  for (const [pattern, replacement] of PHRASE_REPLACEMENTS) {
    text = text.replace(pattern, replacement)
  }

  text = text
    .replace(/\bmaintain\b/gi, 'keep')
    .replace(/\bapproximately\b/gi, 'about')
    .replace(/\bsufficient\b/gi, 'enough')
    .replace(/\bcurrently\b/gi, 'right now')
    .replace(/\btherefore\b/gi, 'so')

  return addFinalPeriod(text)
}

function stripSectionHeaders(text: string) {
  return text
    .replace(/^what it is[:\s-]*/i, '')
    .replace(/^what to do[:\s-]*/i, '')
    .replace(/^why it matters[:\s-]*/i, '')
}

function tightenSentence(raw: string, maxWords: number) {
  let text = stripSectionHeaders(simplifyText(raw))
    .replace(/\([^)]*\)/g, '')
    .replace(/\s*;\s*/g, ', ')
    .replace(/\bset\s+w-2\s+and\s+1099\s+income\s+in\s+settings\s+to\s+compute\s+debt-to-income ratio\s+accurately\b/gi, 'Add income in Settings so we can check your debt load')
    .replace(/\bestimated\b/gi, '')
    .replace(/\byou currently\b/gi, 'you')
    .replace(/\brepresents\b/gi, 'is')
    .replace(/\bmaintain\b/gi, 'keep')
    .replace(/\bprioritize\b/gi, 'focus on')
    .replace(/\baccelerate\b/gi, 'speed up')
    .replace(/\bmaximize\b/gi, 'grow')
    .replace(/\butilize\b/gi, 'use')
    .replace(/\bapproximately\b/gi, 'about')
    .replace(/\bvs\b/gi, 'compared to')
    .replace(/\bdebt-to-income ratio\b/gi, 'debt load')
    .replace(/\bloan-to-value ratio\b/gi, 'loan size vs home value')
    .replace(/\bdiversifier\b/gi, 'backup holding')
    .replace(/\bregime\b/gi, 'market cycle')
    .replace(/\bvolatility\b/gi, 'bumpy moves')
    .replace(/\s+/g, ' ')
    .trim()

  const firstSentence = text.split(/[.!?]/).map((s) => s.trim()).filter(Boolean)[0] ?? text
  const words = firstSentence.split(' ').filter(Boolean)
  const shortened = words.length > maxWords ? `${words.slice(0, maxWords).join(' ')}…` : firstSentence
  return addFinalPeriod(shortened)
}

function simplifyAction(raw: string) {
  const text = simplifyText(raw)
  if (!text) return ''
  if (/^(do this:|next step:)/i.test(text)) return text
  return `Next step: ${text.charAt(0).toLowerCase()}${text.slice(1)}`
}

function simplifyTitle(raw: string) {
  let text = toSingleLine(raw)
  for (const [pattern, replacement] of PHRASE_REPLACEMENTS) {
    text = text.replace(pattern, replacement)
  }
  return text
}

export function simplifyInsightCopy(insight: Insight): InsightCopy {
  return {
    title: simplifyTitle(insight.title),
    description: simplifyText(insight.description),
    action: insight.action ? simplifyAction(insight.action) : '',
    why: simplifyText(insight.why),
  }
}

export function simplifyInsightCardCopy(insight: Insight): InsightCardCopy {
  const simple = simplifyInsightCopy(insight)
  const actionSource = simple.action.replace(/^next step:\s*/i, '') || simple.why || simple.description
  return {
    title: simple.title,
    summary: tightenSentence(simple.description, 8),
    action: tightenSentence(actionSource, 8),
  }
}
