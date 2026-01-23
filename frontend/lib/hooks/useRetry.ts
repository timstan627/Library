'use client'

import { useCallback, useRef, useEffect } from 'react'

interface RetryOptions {
    maxRetries?: number
    retryDelay?: number
    shouldRetry?: (error: any) => boolean
}

const DEFAULT_OPTIONS: Required<RetryOptions> = {
    maxRetries: 3,
    retryDelay: 1000,
    shouldRetry: (error: any) => {
        // Only retry on network errors, timeouts, and 5xx server errors
        if (!error.response) return true // Network error
        if (error.code === 'ECONNABORTED') return true // Timeout
        const status = error.response?.status
        return status >= 500 && status < 600 // Server errors
    },
}

/**
 * Hook for smart retry logic with exponential backoff.
 * Only retries on appropriate error types.
 */
export function useRetry() {
    const abortControllerRef = useRef<AbortController | null>(null)
    const retriesRef = useRef(0)

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            abortControllerRef.current?.abort()
        }
    }, [])

    const executeWithRetry = useCallback(async <T>(
        fn: (signal: AbortSignal) => Promise<T>,
        options: RetryOptions = {}
    ): Promise<T> => {
        const opts = { ...DEFAULT_OPTIONS, ...options }
        retriesRef.current = 0

        // Abort any previous request
        abortControllerRef.current?.abort()
        abortControllerRef.current = new AbortController()

        const attempt = async (): Promise<T> => {
            try {
                return await fn(abortControllerRef.current!.signal)
            } catch (error: any) {
                // Don't retry on abort
                if (error.name === 'AbortError') {
                    throw error
                }

                // Check if we should retry
                if (retriesRef.current < opts.maxRetries && opts.shouldRetry(error)) {
                    retriesRef.current++

                    // Exponential backoff
                    const delay = opts.retryDelay * Math.pow(2, retriesRef.current - 1)
                    await new Promise(resolve => setTimeout(resolve, delay))

                    return attempt()
                }

                throw error
            }
        }

        return attempt()
    }, [])

    const abort = useCallback(() => {
        abortControllerRef.current?.abort()
    }, [])

    return {
        executeWithRetry,
        abort,
        retryCount: retriesRef.current,
    }
}

/**
 * Utility to check if an error is retryable
 */
export function isRetryableError(error: any): boolean {
    if (!error.response) return true // Network error
    if (error.code === 'ECONNABORTED') return true // Timeout
    const status = error.response?.status
    if (status >= 500 && status < 600) return true // Server error
    return false
}

/**
 * Utility to check if an error should NOT be retried
 */
export function isNonRetryableError(error: any): boolean {
    const status = error.response?.status
    return (
        status === 400 || // Validation error
        status === 401 || // Auth error
        status === 403 || // Permission error
        status === 404 || // Not found
        status === 422    // Unprocessable entity
    )
}
