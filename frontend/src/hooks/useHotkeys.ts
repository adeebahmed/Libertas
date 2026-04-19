import { useEffect, useRef } from 'react'

type Chord = {
  keys: string[]
  run: () => void
}

function isEditableTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false
  const tag = target.tagName.toLowerCase()
  return tag === 'input' || tag === 'textarea' || tag === 'select' || target.isContentEditable
}

export function useCommandPaletteHotkeys(onOpen: () => void) {
  const latestOpen = useRef(onOpen)

  useEffect(() => {
    latestOpen.current = onOpen
  }, [onOpen])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey || isEditableTarget(event.target)) return
      if (event.key !== '/') return

      event.preventDefault()
      latestOpen.current()
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])
}

export function useChordHotkeys(chords: Chord[], enabled = true) {
  const chordsRef = useRef(chords)
  const sequenceRef = useRef<string[]>([])
  const timerRef = useRef<number | null>(null)

  useEffect(() => {
    chordsRef.current = chords
  }, [chords])

  useEffect(() => {
    if (!enabled) return undefined

    const reset = () => {
      sequenceRef.current = []
      if (timerRef.current) window.clearTimeout(timerRef.current)
      timerRef.current = null
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey || isEditableTarget(event.target)) return
      const key = event.key.toLowerCase()
      if (key.length !== 1 && key !== '?') return

      sequenceRef.current = [...sequenceRef.current, key].slice(-2)
      if (timerRef.current) window.clearTimeout(timerRef.current)
      timerRef.current = window.setTimeout(reset, 900)

      const match = chordsRef.current.find((chord) => (
        chord.keys.length === sequenceRef.current.length &&
        chord.keys.every((expected, index) => expected === sequenceRef.current[index])
      ))

      if (!match) return
      event.preventDefault()
      reset()
      match.run()
    }

    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      reset()
    }
  }, [enabled])
}
