'use client'

import { useCallback, useRef, useEffect } from 'react'

/**
 * Focus management utilities for accessibility and UX
 */

/**
 * Hook to focus an element on mount or condition
 */
export function useFocusOnMount(shouldFocus: boolean = true) {
    const ref = useRef<HTMLElement>(null)

    useEffect(() => {
        if (shouldFocus && ref.current) {
            // Small delay to ensure DOM is ready
            setTimeout(() => {
                ref.current?.focus()
            }, 50)
        }
    }, [shouldFocus])

    return ref
}

/**
 * Hook to focus on error - returns a function to call with field ref
 */
export function useFocusOnError<T extends HTMLElement>() {
    const ref = useRef<T>(null)

    const focusOnError = useCallback(() => {
        if (ref.current) {
            ref.current.focus()
            ref.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }
    }, [])

    return { ref, focusOnError }
}

/**
 * Hook for scroll position management
 */
export function useScrollPosition() {
    const savedPosition = useRef<number>(0)

    const savePosition = useCallback(() => {
        savedPosition.current = window.scrollY
    }, [])

    const restorePosition = useCallback(() => {
        window.scrollTo({ top: savedPosition.current, behavior: 'smooth' })
    }, [])

    const scrollToTop = useCallback(() => {
        window.scrollTo({ top: 0, behavior: 'smooth' })
    }, [])

    const scrollToElement = useCallback((element: HTMLElement | null, block: ScrollLogicalPosition = 'start') => {
        element?.scrollIntoView({ behavior: 'smooth', block })
    }, [])

    const scrollToFirstError = useCallback(() => {
        const firstError = document.querySelector('[data-error="true"], .error, [aria-invalid="true"]')
        if (firstError) {
            (firstError as HTMLElement).scrollIntoView({ behavior: 'smooth', block: 'center' })
                ; (firstError as HTMLElement).focus?.()
        }
    }, [])

    return {
        savePosition,
        restorePosition,
        scrollToTop,
        scrollToElement,
        scrollToFirstError,
    }
}

/**
 * Hook for tracking form dirtiness (unsaved changes)
 */
export function useFormDirty(initialValues: Record<string, any> = {}) {
    const originalValues = useRef(initialValues)
    const currentValues = useRef(initialValues)

    const setOriginalValues = useCallback((values: Record<string, any>) => {
        originalValues.current = { ...values }
        currentValues.current = { ...values }
    }, [])

    const updateValue = useCallback((key: string, value: any) => {
        currentValues.current = { ...currentValues.current, [key]: value }
    }, [])

    const isDirty = useCallback((): boolean => {
        return JSON.stringify(originalValues.current) !== JSON.stringify(currentValues.current)
    }, [])

    const reset = useCallback(() => {
        currentValues.current = { ...originalValues.current }
    }, [])

    return {
        isDirty,
        updateValue,
        setOriginalValues,
        reset,
        originalValues: originalValues.current,
        currentValues: currentValues.current,
    }
}

/**
 * Hook to warn before leaving page with unsaved changes
 */
export function useBeforeUnload(shouldWarn: boolean, message?: string) {
    useEffect(() => {
        if (!shouldWarn) return

        const handler = (e: BeforeUnloadEvent) => {
            e.preventDefault()
            e.returnValue = message || 'You have unsaved changes. Are you sure you want to leave?'
            return e.returnValue
        }

        window.addEventListener('beforeunload', handler)
        return () => window.removeEventListener('beforeunload', handler)
    }, [shouldWarn, message])
}
