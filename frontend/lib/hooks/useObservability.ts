'use client'

import { useCallback, useRef, useEffect } from 'react'

interface ClickEvent {
    timestamp: number
    target: string
    action: string
}

interface ApiTiming {
    endpoint: string
    method: string
    duration: number
    status: number
    timestamp: number
}

/**
 * Frontend observability hook for tracking user interactions.
 * Detects rage clicks, API timings, and failed submissions.
 */
export function useObservability() {
    const clickBuffer = useRef<ClickEvent[]>([])
    const apiTimings = useRef<ApiTiming[]>([])

    // Track click
    const trackClick = useCallback((target: string, action: string) => {
        const now = Date.now()
        clickBuffer.current.push({ timestamp: now, target, action })

        // Keep only last 50 clicks
        if (clickBuffer.current.length > 50) {
            clickBuffer.current = clickBuffer.current.slice(-50)
        }

        // Detect rage clicks (3+ clicks on same target within 500ms)
        const recentClicks = clickBuffer.current.filter(
            c => c.target === target && now - c.timestamp < 500
        )

        if (recentClicks.length >= 3) {
            console.warn(`[Observability] Rage click detected on: ${target}`)
            // In production, send to analytics
        }
    }, [])

    // Track API timing
    const trackApiTiming = useCallback((
        endpoint: string,
        method: string,
        duration: number,
        status: number
    ) => {
        apiTimings.current.push({
            endpoint,
            method,
            duration,
            status,
            timestamp: Date.now(),
        })

        // Keep only last 100 timings
        if (apiTimings.current.length > 100) {
            apiTimings.current = apiTimings.current.slice(-100)
        }

        // Warn on slow requests
        if (duration > 3000) {
            console.warn(`[Observability] Slow API request: ${method} ${endpoint} took ${duration}ms`)
        }

        // Track failed requests
        if (status >= 400) {
            console.warn(`[Observability] Failed request: ${method} ${endpoint} - ${status}`)
        }
    }, [])

    // Get average API response time
    const getAverageResponseTime = useCallback((endpoint?: string): number => {
        const relevant = endpoint
            ? apiTimings.current.filter(t => t.endpoint === endpoint)
            : apiTimings.current

        if (relevant.length === 0) return 0

        const total = relevant.reduce((sum, t) => sum + t.duration, 0)
        return Math.round(total / relevant.length)
    }, [])

    // Get error rate
    const getErrorRate = useCallback((): number => {
        if (apiTimings.current.length === 0) return 0

        const errors = apiTimings.current.filter(t => t.status >= 400).length
        return Math.round((errors / apiTimings.current.length) * 100)
    }, [])

    return {
        trackClick,
        trackApiTiming,
        getAverageResponseTime,
        getErrorRate,
        recentClicks: clickBuffer.current,
        recentApiTimings: apiTimings.current,
    }
}

/**
 * Higher-order function to wrap API calls with timing
 */
export function withTiming<T>(
    fn: () => Promise<T>,
    onTiming: (duration: number) => void
): Promise<T> {
    const start = Date.now()
    return fn().finally(() => {
        onTiming(Date.now() - start)
    })
}
