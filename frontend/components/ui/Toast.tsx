'use client'

import { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react'

type ToastType = 'success' | 'error' | 'warning' | 'info'

interface Toast {
    id: string
    type: ToastType
    message: string
    duration?: number
    isPaused?: boolean
}

interface ToastContextType {
    toasts: Toast[]
    addToast: (type: ToastType, message: string, duration?: number) => string
    removeToast: (id: string) => void
    success: (message: string, duration?: number) => void
    error: (message: string, duration?: number) => void
    warning: (message: string, duration?: number) => void
    info: (message: string, duration?: number) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

const toastConfig = {
    success: { icon: CheckCircle, bg: 'bg-green-500', text: 'text-white' },
    error: { icon: AlertCircle, bg: 'bg-red-500', text: 'text-white' },
    warning: { icon: AlertTriangle, bg: 'bg-yellow-500', text: 'text-black' },
    info: { icon: Info, bg: 'bg-blue-500', text: 'text-white' },
}

/**
 * Toast notification provider.
 * - Auto-dismiss (except errors which require manual dismiss)
 * - Pause on hover
 * - Stack multiple toasts
 */
export function ToastProvider({ children }: { children: ReactNode }) {
    const [toasts, setToasts] = useState<Toast[]>([])

    const removeToast = useCallback((id: string) => {
        setToasts(prev => prev.filter(t => t.id !== id))
    }, [])

    const addToast = useCallback((type: ToastType, message: string, duration?: number): string => {
        const id = Math.random().toString(36).substring(7)
        const defaultDuration = type === 'error' ? 0 : 5000 // Errors don't auto-dismiss

        const toast: Toast = {
            id,
            type,
            message,
            duration: duration ?? defaultDuration,
        }

        setToasts(prev => [...prev, toast])

        // Auto-dismiss
        if (toast.duration && toast.duration > 0) {
            setTimeout(() => removeToast(id), toast.duration)
        }

        return id
    }, [removeToast])

    const success = useCallback((message: string, duration?: number) => {
        addToast('success', message, duration)
    }, [addToast])

    const error = useCallback((message: string, duration?: number) => {
        addToast('error', message, duration)
    }, [addToast])

    const warning = useCallback((message: string, duration?: number) => {
        addToast('warning', message, duration)
    }, [addToast])

    const info = useCallback((message: string, duration?: number) => {
        addToast('info', message, duration)
    }, [addToast])

    return (
        <ToastContext.Provider value={{ toasts, addToast, removeToast, success, error, warning, info }}>
            {children}
            <ToastContainer />
        </ToastContext.Provider>
    )
}

export function useToast() {
    const context = useContext(ToastContext)
    if (!context) {
        throw new Error('useToast must be used within ToastProvider')
    }
    return context
}

/**
 * Toast container - renders at bottom-right
 */
function ToastContainer() {
    const { toasts, removeToast } = useToast()

    return (
        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
            {toasts.map(toast => (
                <ToastItem key={toast.id} toast={toast} onDismiss={() => removeToast(toast.id)} />
            ))}
        </div>
    )
}

/**
 * Individual toast item
 */
function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: () => void }) {
    const config = toastConfig[toast.type]
    const Icon = config.icon
    const [isPaused, setIsPaused] = useState(false)

    return (
        <div
            className={`
                ${config.bg} ${config.text}
                flex items-start gap-3 p-4 rounded-lg shadow-lg
                animate-slide-in-right
                transition-opacity duration-200
                ${isPaused ? 'opacity-100' : ''}
            `}
            role="alert"
            onMouseEnter={() => setIsPaused(true)}
            onMouseLeave={() => setIsPaused(false)}
        >
            <Icon className="w-5 h-5 shrink-0 mt-0.5" />
            <p className="flex-1 text-sm font-medium">{toast.message}</p>
            <button
                onClick={onDismiss}
                className="p-1 hover:bg-white/20 rounded transition-colors"
                aria-label="Dismiss"
            >
                <X className="w-4 h-4" />
            </button>
        </div>
    )
}
