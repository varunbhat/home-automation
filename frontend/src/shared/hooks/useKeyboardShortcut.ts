import { useEffect, useCallback } from 'react'

export interface KeyboardShortcutOptions {
  ctrl?: boolean
  meta?: boolean
  shift?: boolean
  alt?: boolean
}

export function useKeyboardShortcut(
  key: string,
  callback: (event: KeyboardEvent) => void,
  options?: KeyboardShortcutOptions
): void {
  const handleKeyPress = useCallback(
    (event: KeyboardEvent) => {
      const matchesModifiers =
        (!options?.ctrl || event.ctrlKey) &&
        (!options?.meta || event.metaKey) &&
        (!options?.shift || event.shiftKey) &&
        (!options?.alt || event.altKey)

      if (event.key.toLowerCase() === key.toLowerCase() && matchesModifiers) {
        callback(event)
      }
    },
    [key, callback, options]
  )

  useEffect(() => {
    window.addEventListener('keydown', handleKeyPress)

    return () => {
      window.removeEventListener('keydown', handleKeyPress)
    }
  }, [handleKeyPress])
}

// Convenience hook for Cmd/Ctrl+Key shortcuts
export function useCmdK(callback: (event: KeyboardEvent) => void): void {
  const handleKeyPress = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === 'k' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault()
        callback(event)
      }
    },
    [callback]
  )

  useEffect(() => {
    window.addEventListener('keydown', handleKeyPress)

    return () => {
      window.removeEventListener('keydown', handleKeyPress)
    }
  }, [handleKeyPress])
}
