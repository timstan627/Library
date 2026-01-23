'use client'

import { useState, useCallback, useRef, useEffect, createContext, useContext } from 'react'
import { usePathname } from 'next/navigation'

interface NavigationState {
    isNavigating: boolean
    fromPath: string | null
    toPath: string | null
}

interface NavigationContextType {
    state: NavigationState
    startNavigation: (to: string) => void
    endNavigation: () => void
    preventDuplicateNavigation: (to: string) => boolean
}

const NavigationContext = createContext<NavigationContextType | undefined>(undefined)

/**
 * Provider for managing navigation state across the app.
 * Prevents duplicate navigation and provides loading indicators.
 */
export function NavigationProvider({ children }: { children: React.ReactNode }) {
    const pathname = usePathname()
    const lastNavigationRef = useRef<string | null>(null)
    const navigationTimeoutRef = useRef<NodeJS.Timeout | null>(null)

    const [state, setState] = useState<NavigationState>({
        isNavigating: false,
        fromPath: null,
        toPath: null,
    })

    // Reset navigation state when path changes
    useEffect(() => {
        if (state.isNavigating && pathname === state.toPath) {
            endNavigation()
        }
    }, [pathname])

    // Cleanup timeouts
    useEffect(() => {
        return () => {
            if (navigationTimeoutRef.current) {
                clearTimeout(navigationTimeoutRef.current)
            }
        }
    }, [])

    const startNavigation = useCallback((to: string) => {
        lastNavigationRef.current = to
        setState({
            isNavigating: true,
            fromPath: pathname,
            toPath: to,
        })

        // Fallback timeout - reset after 10 seconds if navigation doesn't complete
        navigationTimeoutRef.current = setTimeout(() => {
            endNavigation()
        }, 10000)
    }, [pathname])

    const endNavigation = useCallback(() => {
        if (navigationTimeoutRef.current) {
            clearTimeout(navigationTimeoutRef.current)
        }
        setState({
            isNavigating: false,
            fromPath: null,
            toPath: null,
        })
    }, [])

    const preventDuplicateNavigation = useCallback((to: string): boolean => {
        // Prevent navigation to same path
        if (to === pathname) {
            return true
        }

        // Prevent duplicate clicks during navigation
        if (state.isNavigating && state.toPath === to) {
            return true
        }

        return false
    }, [pathname, state])

    return (
        <NavigationContext.Provider value={{
            state,
            startNavigation,
            endNavigation,
            preventDuplicateNavigation,
        }}>
            {children}
        </NavigationContext.Provider>
    )
}

export function useNavigation() {
    const context = useContext(NavigationContext)
    if (!context) {
        throw new Error('useNavigation must be used within NavigationProvider')
    }
    return context
}

/**
 * Hook for creating safe navigation links that prevent duplicates
 */
export function useSafeNavigation() {
    const { startNavigation, preventDuplicateNavigation, state } = useNavigation()

    const safeNavigate = useCallback((
        href: string,
        navigateFn: () => void
    ) => {
        if (preventDuplicateNavigation(href)) {
            return false
        }

        startNavigation(href)
        navigateFn()
        return true
    }, [startNavigation, preventDuplicateNavigation])

    return {
        safeNavigate,
        isNavigating: state.isNavigating,
        toPath: state.toPath,
    }
}
