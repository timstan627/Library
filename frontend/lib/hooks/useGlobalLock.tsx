'use client'

import { createContext, useContext, useState, useCallback, ReactNode, useEffect } from 'react'

interface GlobalLockState {
    isLocked: boolean
    lockReason: string | null
    lockOwner: string | null
}

interface GlobalLockContextType {
    state: GlobalLockState
    acquireLock: (owner: string, reason?: string) => boolean
    releaseLock: (owner: string) => void
    isLocked: boolean
}

const GlobalLockContext = createContext<GlobalLockContextType | undefined>(undefined)

/**
 * Provider for global UI lock during critical operations.
 * Disables navigation, forms, and interactive elements.
 */
export function GlobalLockProvider({ children }: { children: ReactNode }) {
    const [state, setState] = useState<GlobalLockState>({
        isLocked: false,
        lockReason: null,
        lockOwner: null,
    })

    const acquireLock = useCallback((owner: string, reason?: string): boolean => {
        // Can't acquire if already locked by someone else
        if (state.isLocked && state.lockOwner !== owner) {
            console.warn(`Lock already held by ${state.lockOwner}, cannot acquire for ${owner}`)
            return false
        }

        setState({
            isLocked: true,
            lockReason: reason || 'Processing...',
            lockOwner: owner,
        })
        return true
    }, [state.isLocked, state.lockOwner])

    const releaseLock = useCallback((owner: string) => {
        setState(prev => {
            // Only release if owner matches
            if (prev.lockOwner !== owner) {
                console.warn(`Cannot release lock: owner mismatch (${owner} vs ${prev.lockOwner})`)
                return prev
            }
            return {
                isLocked: false,
                lockReason: null,
                lockOwner: null,
            }
        })
    }, [])

    // Handle browser back/forward during lock
    useEffect(() => {
        if (!state.isLocked) return

        const handlePopState = (e: PopStateEvent) => {
            if (state.isLocked) {
                // Prevent navigation during lock
                window.history.pushState(null, '', window.location.href)
            }
        }

        window.addEventListener('popstate', handlePopState)
        return () => window.removeEventListener('popstate', handlePopState)
    }, [state.isLocked])

    return (
        <GlobalLockContext.Provider value={{
            state,
            acquireLock,
            releaseLock,
            isLocked: state.isLocked,
        }}>
            {children}
            {/* Global lock overlay */}
            {state.isLocked && (
                <div
                    className="fixed inset-0 bg-black/20 z-[9999] pointer-events-auto cursor-wait"
                    aria-hidden="true"
                />
            )}
        </GlobalLockContext.Provider>
    )
}

export function useGlobalLock() {
    const context = useContext(GlobalLockContext)
    if (!context) {
        throw new Error('useGlobalLock must be used within GlobalLockProvider')
    }
    return context
}

/**
 * Hook for components to check if they should be disabled
 */
export function useIsGloballyLocked() {
    const { isLocked } = useGlobalLock()
    return isLocked
}
