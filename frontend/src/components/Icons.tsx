type IconProps = { size?: number; className?: string }

const defaults = { size: 16, strokeWidth: 1.5 }

export function IconGrid({ size = defaults.size }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={defaults.strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="2" width="5" height="5" rx="1" />
      <rect x="9" y="2" width="5" height="5" rx="1" />
      <rect x="2" y="9" width="5" height="5" rx="1" />
      <rect x="9" y="9" width="5" height="5" rx="1" />
    </svg>
  )
}

export function IconWallet({ size = defaults.size }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={defaults.strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 5a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V5z" />
      <path d="M10 9.5a.5.5 0 1 0 1 0 .5.5 0 0 0-1 0z" fill="currentColor" />
      <path d="M5 4V3a1 1 0 0 1 1-1h5" />
    </svg>
  )
}

export function IconTrendDown({ size = defaults.size }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={defaults.strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 4l4 5 3-3 5 6" />
      <path d="M10 12h4V8" />
    </svg>
  )
}

export function IconBarChart({ size = defaults.size }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={defaults.strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 13V9M6 13V6M10 13V3M14 13V7" />
      <path d="M1 13h14" />
    </svg>
  )
}

export function IconHouse({ size = defaults.size }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={defaults.strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 7.5L8 2l6 5.5V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7.5z" />
      <path d="M6 15V9.5h4V15" />
    </svg>
  )
}

export function IconReceipt({ size = defaults.size }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={defaults.strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 2h8a1 1 0 0 1 1 1v10l-2-1-2 1-2-1-2 1V3a1 1 0 0 1 1-1z" />
      <path d="M6 6h4M6 9h3" />
    </svg>
  )
}

export function IconSpark({ size = defaults.size }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={defaults.strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.2 3.2l1.4 1.4M11.4 11.4l1.4 1.4M3.2 12.8l1.4-1.4M11.4 4.6l1.4-1.4" />
      <circle cx="8" cy="8" r="3" />
    </svg>
  )
}

export function IconUpload({ size = defaults.size }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={defaults.strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 10V3M5 6l3-3 3 3" />
      <path d="M3 11v1.5A1.5 1.5 0 0 0 4.5 14h7a1.5 1.5 0 0 0 1.5-1.5V11" />
    </svg>
  )
}

export function IconGear({ size = defaults.size }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={defaults.strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="8" r="2.5" />
      <path d="M8 1.5v1M8 13.5v1M1.5 8h1M13.5 8h1M3.4 3.4l.7.7M11.9 11.9l.7.7M3.4 12.6l.7-.7M11.9 4.1l.7-.7" />
    </svg>
  )
}

export function IconChevronLeft({ size = defaults.size }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={defaults.strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 12L6 8l4-4" />
    </svg>
  )
}

export function IconRefresh({ size = defaults.size }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={defaults.strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M13.5 8A5.5 5.5 0 1 1 10 3.07" />
      <path d="M10 1v3h3" />
    </svg>
  )
}
