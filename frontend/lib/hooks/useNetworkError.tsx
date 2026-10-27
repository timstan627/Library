'use client'

import { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import { X, WifiOff, RefreshCw } from 'lucide-react'

interface NetworkError {
    id: string
    message: string
    retryFn?: () => void
}

interface NetworkErrorContextType {
    errors: NetworkError[]
    addError: (message: string, retryFn?: () => void) => string
    removeError: (id: string) => void
    clearAll: () => void
}

const NetworkErrorContext = createContext<NetworkErrorContextType | undefined>(undefined)

/**
 * Provider for managing network errors with persistent banner display.
 */
export function NetworkErrorProvider({ children }: { children: ReactNode }) {
    const [errors, setErrors] = useState<NetworkError[]>([])

    const addError = useCallback((message: string, retryFn?: () => void): string => {
        const id = Math.random().toString(36).substring(7)
        setErrors(prev => {
            // Prevent duplicate errors
            if (prev.some(e => e.message === message)) {
                return prev
            }
            return [...prev, { id, message, retryFn }]
        })
        return id
    }, [])

    const removeError = useCallback((id: string) => {
        setErrors(prev => prev.filter(e => e.id !== id))
    }, [])

    const clearAll = useCallback(() => {
        setErrors([])
    }, [])

    return (
        <NetworkErrorContext.Provider value={{ errors, addError, removeError, clearAll }}>
            {children}
            <NetworkErrorBanner />
        </NetworkErrorContext.Provider>
    )
}

export function useNetworkError() {
    const context = useContext(NetworkErrorContext)
    if (!context) {
        throw new Error('useNetworkError must be used within NetworkErrorProvider')
    }
    return context
}

/**
 * Persistent banner for displaying network errors
 */
function NetworkErrorBanner() {
    const { errors, removeError } = useNetworkError()

    if (errors.length === 0) return null

    return (
        <div className="fixed bottom-0 left-0 right-0 z-50 p-4 space-y-2">
            {errors.map(error => (
                <div
                    key={error.id}
                    className="max-w-md mx-auto bg-danger text-accent-ink p-4 rounded-lg shadow-lg flex items-center gap-3 animate-slide-up"
                >
                    <WifiOff className="w-5 h-5 shrink-0" />
                    <p className="flex-1 text-sm">{error.message}</p>
                    {error.retryFn && (
                        <button
                            onClick={() => {
                                removeError(error.id)
                                error.retryFn?.()
                            }}
                            className="px-3 py-1 bg-white/20 hover:bg-white/30 rounded text-sm font-medium flex items-center gap-1 transition-colors"
                        >
                            <RefreshCw className="w-4 h-4" />
                            Retry
                        </button>
                    )}
                    <button
                        onClick={() => removeError(error.id)}
                        className="p-1 hover:bg-white/20 rounded transition-colors"
                        aria-label="Dismiss"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
            ))}
        </div>
    )
}

// CSS animation keyframe (add to globals.css)
// @keyframes slide-up {
//   from { transform: translateY(100%); opacity: 0; }
//   to { transform: translateY(0); opacity: 1; }
// }
// .animate-slide-up { animation: slide-up 0.3s ease-out; }
