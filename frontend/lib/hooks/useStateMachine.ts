'use client'

import { useState, useCallback, useMemo } from 'react'

/**
 * Type-safe finite state machine hook for UI states.
 * Prevents invalid state transitions and parallel states.
 */

export type FormState = 'IDLE' | 'VALIDATING' | 'SUBMITTING' | 'SUCCESS' | 'ERROR'

interface StateTransition {
    from: FormState[]
    to: FormState
}

// Valid state transitions for form state machine
const FORM_TRANSITIONS: StateTransition[] = [
    { from: ['IDLE'], to: 'VALIDATING' },
    { from: ['IDLE', 'VALIDATING', 'ERROR'], to: 'SUBMITTING' },
    { from: ['SUBMITTING'], to: 'SUCCESS' },
    { from: ['SUBMITTING'], to: 'ERROR' },
    { from: ['ERROR', 'SUCCESS'], to: 'IDLE' },
    { from: ['VALIDATING'], to: 'IDLE' },
    { from: ['VALIDATING'], to: 'ERROR' },
]

export interface FormStateMachineState {
    current: FormState
    error: string | null
    data: any
    history: FormState[]
}

export function useFormStateMachine() {
    const [state, setState] = useState<FormStateMachineState>({
        current: 'IDLE',
        error: null,
        data: null,
        history: ['IDLE'],
    })

    const canTransition = useCallback((to: FormState): boolean => {
        return FORM_TRANSITIONS.some(
            t => t.from.includes(state.current) && t.to === to
        )
    }, [state.current])

    const transition = useCallback((to: FormState, payload?: { error?: string; data?: any }) => {
        setState(prev => {
            // Validate transition
            const valid = FORM_TRANSITIONS.some(
                t => t.from.includes(prev.current) && t.to === to
            )

            if (!valid) {
                console.warn(`Invalid state transition: ${prev.current} → ${to}`)
                return prev
            }

            return {
                current: to,
                error: payload?.error ?? (to === 'IDLE' ? null : prev.error),
                data: payload?.data ?? prev.data,
                history: [...prev.history.slice(-9), to], // Keep last 10 states
            }
        })
    }, [])

    const reset = useCallback(() => {
        setState({
            current: 'IDLE',
            error: null,
            data: null,
            history: ['IDLE'],
        })
    }, [])

    // Derived states for convenience
    const isIdle = state.current === 'IDLE'
    const isValidating = state.current === 'VALIDATING'
    const isSubmitting = state.current === 'SUBMITTING'
    const isSuccess = state.current === 'SUCCESS'
    const isError = state.current === 'ERROR'
    const isLoading = isValidating || isSubmitting
    const isLocked = isSubmitting || isSuccess

    return {
        state: state.current,
        error: state.error,
        data: state.data,
        history: state.history,
        transition,
        canTransition,
        reset,
        // Convenience booleans
        isIdle,
        isValidating,
        isSubmitting,
        isSuccess,
        isError,
        isLoading,
        isLocked,
    }
}

/**
 * Generic state machine for custom states
 */
export function useStateMachine<T extends string>(
    initialState: T,
    transitions: { from: T[]; to: T }[]
) {
    const [current, setCurrent] = useState<T>(initialState)
    const [history, setHistory] = useState<T[]>([initialState])

    const canTransition = useCallback((to: T): boolean => {
        return transitions.some(t => t.from.includes(current) && t.to === to)
    }, [current, transitions])

    const transition = useCallback((to: T) => {
        const valid = transitions.some(t => t.from.includes(current) && t.to === to)
        if (!valid) {
            console.warn(`Invalid state transition: ${current} → ${to}`)
            return false
        }
        setCurrent(to)
        setHistory(prev => [...prev.slice(-9), to])
        return true
    }, [current, transitions])

    const reset = useCallback(() => {
        setCurrent(initialState)
        setHistory([initialState])
    }, [initialState])

    return { current, history, transition, canTransition, reset }
}
