import { useCallback, useEffect, useState } from 'react'
import { api } from '../lib/api'

/** Polls /health (+ corpus stats and config) so the header never shows stale or fake values. */
export function useStatus(intervalMs = 20000) {
  const [state, setState] = useState({ health: null, chunks: null, config: null, unreachable: false })

  const refresh = useCallback(async () => {
    try {
      const [health, chunks, config] = await Promise.all([api.health(), api.chunks(), api.config()])
      setState({ health, chunks, config, unreachable: false })
    } catch {
      setState((s) => ({ ...s, unreachable: true }))
    }
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, intervalMs)
    return () => clearInterval(id)
  }, [refresh, intervalMs])

  return { ...state, refresh }
}
