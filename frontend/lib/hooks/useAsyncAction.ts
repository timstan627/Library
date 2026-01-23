'use client'

import { useState, useCallback, useRef } from 'react'

interface AsyncActionState<T> {
    isLoading: boolean
    isSuccess: boolean
    isError: boolean
    error: string | null
    data: T | null
}

interface UseAsyncActionOptions {
    /** Timeout in milliseconds (default: 30000) */
    timeout?: number
    /** Reset success/error state after this many ms */
    resetAfter?: number
    /** Callback on success */
    onSuccess?: (data: any) => void
    /** Callback on error */
    onError?: (error: string) => void
}

/**
 * Hook for managing async actions with proper loading, error, and success states.
 * Prevents duplicate calls and handles timeouts.
 */
export function useAsyncAction<T = any>(options: UseAsyncActionOptions = {}) {
    const { timeout = 30000, resetAfter, onSuccess, onError } = options

    const [state, setState] = useState<AsyncActionState<T>>({
        isLoading: false,
        isSuccess: false,
        isError: false,
        error: null,
        data: null,
    })

    // Prevent duplicate calls
    const isExecutingRef = useRef(false)
    const abortControllerRef = useRef<AbortController | null>(null)

    const execute = useCallback(async (
        asyncFn: (signal?: AbortSignal) => Promise<T>
    ): Promise<T | null> => {
        // Prevent duplicate execution
        if (isExecutingRef.current) {
            console.warn('Action already in progress, ignoring duplicate call')
            return null
        }

        isExecutingRef.current = true

        // Cancel any previous request
        if (abortControllerRef.current) {
            abortControllerRef.current.abort()
        }
        abortControllerRef.current = new AbortController()

        setState({
            isLoading: true,
            isSuccess: false,
            isError: false,
            error: null,
            data: null,
        })

        // Setup timeout
        const timeoutId = setTimeout(() => {
            abortControllerRef.current?.abort()
        }, timeout)

        try {
            const result = await asyncFn(abortControllerRef.current.signal)

            clearTimeout(timeoutId)

            setState({
                isLoading: false,
                isSuccess: true,
                isError: false,
                error: null,
                data: result,
            })

            onSuccess?.(result)

            // Auto-reset after success if configured
            if (resetAfter) {
                setTimeout(() => {
                    setState(prev => ({
                        ...prev,
                        isSuccess: false,
                    }))
                }, resetAfter)
            }

            return result
        } catch (err: any) {
            clearTimeout(timeoutId)

            const errorMessage = err.name === 'AbortError'
                ? 'Request timed out. Please try again.'
                : err.response?.data?.detail || err.message || 'An error occurred'

            setState({
                isLoading: false,
                isSuccess: false,
                isError: true,
                error: errorMessage,
                data: null,
            })

            onError?.(errorMessage)

            // Auto-reset after error if configured
            if (resetAfter) {
                setTimeout(() => {
                    setState(prev => ({
                        ...prev,
                        isError: false,
                        error: null,
                    }))
                }, resetAfter)
            }

            return null
        } finally {
            isExecutingRef.current = false
        }
    }, [timeout, resetAfter, onSuccess, onError])

    const reset = useCallback(() => {
        setState({
            isLoading: false,
            isSuccess: false,
            isError: false,
            error: null,
            data: null,
        })
    }, [])

    return {
        ...state,
        execute,
        reset,
    }
}
