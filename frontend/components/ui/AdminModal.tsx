'use client'

import { useEffect, useId, useRef, type ReactNode } from 'react'
import { X } from 'lucide-react'

interface AdminModalProps {
    isOpen: boolean
    onClose: () => void
    title: ReactNode
    /** Muted line under the title, e.g. "This action cannot be undone". */
    description?: ReactNode
    /** Small icon tile rendered left of the title (e.g. the AlertTriangle circle). */
    icon?: ReactNode
    maxWidth?: 'sm' | 'md' | 'lg' | 'xl'
    /** 'danger' tints the header for destructive confirmations. */
    headerTone?: 'default' | 'danger'
    children: ReactNode
}

const WIDTHS = { sm: 'max-w-sm', md: 'max-w-md', lg: 'max-w-lg', xl: 'max-w-xl' } as const

const getFocusable = (root: HTMLElement): HTMLElement[] =>
    Array.from(
        root.querySelectorAll<HTMLElement>(
            'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )
    )

/**
 * Shared dialog scaffold for admin modals: role="dialog" + aria-modal,
 * Escape to close, backdrop-click close, focus trap, scroll lock, and
 * focus returned to the trigger on close. Every admin modal should
 * render through this so the console has exactly one close glyph (X)
 * and one interaction pattern (HIGH-004 companion).
 */
export function AdminModal({
    isOpen,
    onClose,
    title,
    description,
    icon,
    maxWidth = 'lg',
    headerTone = 'default',
    children,
}: AdminModalProps) {
    const titleId = useId()
    const shellRef = useRef<HTMLDivElement>(null)
    // Hold the latest onClose in a ref so the opening effect does not
    // re-run (and steal focus again) when callers pass inline handlers.
    const onCloseRef = useRef(onClose)
    useEffect(() => {
        onCloseRef.current = onClose
    })

    useEffect(() => {
        if (!isOpen) return
        const shell = shellRef.current
        const previousOverflow = document.body.style.overflow
        const previouslyFocused = document.activeElement as HTMLElement | null
        document.body.style.overflow = 'hidden'

        if (shell) {
            // Focus the first control inside the body (inputs, then buttons);
            // the header close button deliberately stays second in line.
            const bodyFocusables = getFocusable(shell).slice(1)
            bodyFocusables[0]?.focus()
        }

        const onKeyDown = (event: KeyboardEvent) => {
            const active = shellRef.current
            if (!active) return
            if (event.key === 'Escape') {
                event.preventDefault()
                onCloseRef.current()
            } else if (event.key === 'Tab') {
                const items = getFocusable(active)
                if (items.length === 0) return
                const first = items[0]
                const last = items[items.length - 1]
                if (event.shiftKey && document.activeElement === first) {
                    event.preventDefault()
                    last.focus()
                } else if (!event.shiftKey && document.activeElement === last) {
                    event.preventDefault()
                    first.focus()
                }
            }
        }
        document.addEventListener('keydown', onKeyDown)

        return () => {
            document.removeEventListener('keydown', onKeyDown)
            document.body.style.overflow = previousOverflow
            previouslyFocused?.focus()
        }
    }, [isOpen])

    if (!isOpen) return null

    const headerClass =
        headerTone === 'danger'
            ? 'bg-danger/10 border-b border-danger/20'
            : 'bg-background-secondary border-b border-border-subtle'

    return (
        <div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onMouseDown={(event) => {
                if (event.target === event.currentTarget) onCloseRef.current()
            }}
        >
            <div
                ref={shellRef}
                role="dialog"
                aria-modal="true"
                aria-labelledby={titleId}
                tabIndex={-1}
                className={`card w-full ${WIDTHS[maxWidth]} p-0 animate-scale-in shadow-2xl overflow-hidden outline-none`}
            >
                <div className={`p-6 ${headerClass} flex justify-between items-center`}>
                    <div className="flex items-start gap-3">
                        {icon}
                        <div>
                            <h2 id={titleId} className="text-xl font-bold text-text-primary">
                                {title}
                            </h2>
                            {description && (
                                <p className={`text-sm mt-1 ${headerTone === 'danger' ? 'text-danger' : 'text-text-secondary'}`}>
                                    {description}
                                </p>
                            )}
                        </div>
                    </div>
                    <button
                        onClick={() => onCloseRef.current()}
                        className="text-text-muted hover:text-text-primary shrink-0"
                        aria-label="Close dialog"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>
                {children}
            </div>
        </div>
    )
}
