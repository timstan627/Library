'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { WifiOff, Wifi } from 'lucide-react'

interface OfflineState {
    isOnline: boolean
    wasOffline: boolean
}

const OfflineContext = createContext<OfflineState>({
    isOnline: true,
    wasOffline: false,
})

/**
 * Provider for detecting offline state and showing banner.
 * Disables submit buttons and shows reconnection notification.
 */
export function OfflineProvider({ children }: { children: ReactNode }) {
    const [state, setState] = useState<OfflineState>({
        isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
        wasOffline: false,
    })

    useEffect(() => {
        const handleOnline = () => {
            setState(prev => ({
                isOnline: true,
                wasOffline: prev.wasOffline || !prev.isOnline,
            }))
        }

        const handleOffline = () => {
            setState(prev => ({
                ...prev,
                isOnline: false,
            }))
        }

        window.addEventListener('online', handleOnline)
        window.addEventListener('offline', handleOffline)

        return () => {
            window.removeEventListener('online', handleOnline)
            window.removeEventListener('offline', handleOffline)
        }
    }, [])

    // Clear wasOffline after showing reconnection message
    useEffect(() => {
        if (state.isOnline && state.wasOffline) {
            const timer = setTimeout(() => {
                setState(prev => ({ ...prev, wasOffline: false }))
            }, 3000)
            return () => clearTimeout(timer)
        }
    }, [state.isOnline, state.wasOffline])

    return (
        <OfflineContext.Provider value={state}>
            {children}
            <OfflineBanner />
        </OfflineContext.Provider>
    )
}

export function useOffline() {
    return useContext(OfflineContext)
}

/**
 * Offline/reconnected banner component
 */
function OfflineBanner() {
    const { isOnline, wasOffline } = useOffline()

    if (isOnline && !wasOffline) return null

    return (
        <div className={`fixed top-0 left-0 right-0 z-50 px-4 py-2 text-center text-sm font-medium transition-[background-color] duration-300 ${isOnline
                ? 'bg-success text-accent-ink'
                : 'bg-danger text-accent-ink'
            }`}>
            {isOnline ? (
                <span className="inline-flex items-center gap-2">
                    <Wifi className="w-4 h-4" />
                    You're back online!
                </span>
            ) : (
                <span className="inline-flex items-center gap-2">
                    <WifiOff className="w-4 h-4" />
                    You're offline. Some features may not work.
                </span>
            )}
        </div>
    )
}
