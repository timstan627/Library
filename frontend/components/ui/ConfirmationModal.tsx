'use client'

import { useEffect, useRef, useState, useCallback, ReactNode } from 'react'
import { X, AlertTriangle, Trash2, LogOut, AlertCircle } from 'lucide-react'
import { Button } from './Button'

interface ConfirmationModalProps {
    isOpen: boolean
    onClose: () => void
    onConfirm: () => void
    title: string
    message: string | ReactNode
    confirmText?: string
    cancelText?: string
    variant?: 'danger' | 'warning' | 'info'
    isLoading?: boolean
}

const variantConfig = {
    danger: {
        icon: Trash2,
        iconBg: 'bg-danger/10',
        iconColor: 'text-danger',
        confirmVariant: 'danger' as const,
    },
    warning: {
        icon: AlertTriangle,
        iconBg: 'bg-warning/10',
        iconColor: 'text-warning',
        confirmVariant: 'primary' as const,
    },
    info: {
        icon: AlertCircle,
        iconBg: 'bg-accent-primary/10',
        iconColor: 'text-accent-primary',
        confirmVariant: 'primary' as const,
    },
}

/**
 * Confirmation modal with focus trapping and accessibility.
 * - Traps focus inside modal
 * - Escape key closes
 * - Default focus on cancel button for destructive actions
 * - Disables background interaction
 */
export function ConfirmationModal({
    isOpen,
    onClose,
    onConfirm,
    title,
    message,
    confirmText = 'Confirm',
    cancelText = 'Cancel',
    variant = 'danger',
    isLoading = false,
}: ConfirmationModalProps) {
    const modalRef = useRef<HTMLDivElement>(null)
    const cancelRef = useRef<HTMLButtonElement>(null)
    const config = variantConfig[variant]
    const Icon = config.icon

    // Focus trap and escape handler
    useEffect(() => {
        if (!isOpen) return

        // Focus cancel button by default (safer for destructive actions)
        setTimeout(() => cancelRef.current?.focus(), 50)

        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && !isLoading) {
                onClose()
                return
            }

            // Focus trap
            if (e.key === 'Tab' && modalRef.current) {
                const focusable = modalRef.current.querySelectorAll(
                    'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
                )
                const first = focusable[0] as HTMLElement
                const last = focusable[focusable.length - 1] as HTMLElement

                if (e.shiftKey && document.activeElement === first) {
                    e.preventDefault()
                    last.focus()
                } else if (!e.shiftKey && document.activeElement === last) {
                    e.preventDefault()
                    first.focus()
                }
            }
        }

        // Prevent background scroll
        document.body.style.overflow = 'hidden'
        document.addEventListener('keydown', handleKeyDown)

        return () => {
            document.body.style.overflow = ''
            document.removeEventListener('keydown', handleKeyDown)
        }
    }, [isOpen, isLoading, onClose])

    if (!isOpen) return null

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
        >
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fade-in"
                onClick={() => !isLoading && onClose()}
            />

            {/* Modal */}
            <div
                ref={modalRef}
                className="relative bg-background-secondary rounded-xl shadow-xl max-w-md w-full p-6 animate-scale-in"
            >
                {/* Close button */}
                <button
                    onClick={onClose}
                    disabled={isLoading}
                    className="absolute top-4 right-4 p-1 text-text-muted hover:text-text-primary transition-colors disabled:opacity-50"
                    aria-label="Close"
                >
                    <X className="w-5 h-5" />
                </button>

                {/* Icon */}
                <div className={`w-12 h-12 ${config.iconBg} rounded-full flex items-center justify-center mb-4`}>
                    <Icon className={`w-6 h-6 ${config.iconColor}`} />
                </div>

                {/* Title */}
                <h2 id="modal-title" className="text-xl font-bold text-text-primary mb-2">
                    {title}
                </h2>

                {/* Message */}
                <div className="text-text-secondary mb-6">
                    {message}
                </div>

                {/* Actions */}
                <div className="flex gap-3 justify-end">
                    <Button
                        ref={cancelRef}
                        variant="secondary"
                        onClick={onClose}
                        disabled={isLoading}
                    >
                        {cancelText}
                    </Button>
                    <Button
                        variant={config.confirmVariant}
                        onClick={onConfirm}
                        isLoading={isLoading}
                        loadingText="Processing..."
                    >
                        {confirmText}
                    </Button>
                </div>
            </div>
        </div>
    )
}

/**
 * Hook for managing confirmation modal state
 */
export function useConfirmation() {
    const [isOpen, setIsOpen] = useState(false)
    const [config, setConfig] = useState<Omit<ConfirmationModalProps, 'isOpen' | 'onClose' | 'onConfirm'> | null>(null)
    const resolveRef = useRef<(confirmed: boolean) => void>()

    const confirm = useCallback((
        options: Omit<ConfirmationModalProps, 'isOpen' | 'onClose' | 'onConfirm'>
    ): Promise<boolean> => {
        setConfig(options)
        setIsOpen(true)
        return new Promise(resolve => {
            resolveRef.current = resolve
        })
    }, [])

    const handleClose = useCallback(() => {
        setIsOpen(false)
        resolveRef.current?.(false)
    }, [])

    const handleConfirm = useCallback(() => {
        setIsOpen(false)
        resolveRef.current?.(true)
    }, [])

    const ConfirmModal = config ? (
        <ConfirmationModal
            {...config}
            isOpen={isOpen}
            onClose={handleClose}
            onConfirm={handleConfirm}
        />
    ) : null

    return { confirm, ConfirmModal }
}


