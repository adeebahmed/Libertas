import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

export type Theme = 'onyx' | 'retro'

const STORAGE_KEY = 'libertas-theme'

function readStoredTheme(): Theme {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (raw === 'onyx' || raw === 'retro') return raw
  return 'onyx'
}

type ThemeContextValue = {
  theme: Theme
  setTheme: (t: Theme) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(readStoredTheme)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem(STORAGE_KEY, theme)
  }, [theme])

  useEffect(() => {
    const toggle = () => setTheme(t => t === 'onyx' ? 'retro' : 'onyx')
    window.addEventListener('libertas:theme-toggle', toggle)
    return () => window.removeEventListener('libertas:theme-toggle', toggle)
  }, [])

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}
