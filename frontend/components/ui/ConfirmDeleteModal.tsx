'use client'

import { useState, ReactNode } from 'react'
import { AlertTriangle, Loader2, X } from 'lucide-react'

interface ConfirmDeleteModalProps {
    isOpen: boolean
    onClose: () => void
    onConfirm: () => Promise<void>
    title: string
    itemName: string
    itemType: string
    cascadeWarning?: string
    cascadeCount?: number
}

/**
 * HIGH-004: Type-to-Confirm Delete Modal
 * 
 * Requires user to type the item name to confirm deletion.
 * Shows cascade warning if deleting will affect other items.
 */
export function ConfirmDeleteModal({
    isOpen,
    onClose,
    onConfirm,
    title,
    itemName,
    itemType,
    cascadeWarning,
    cascadeCount
}: ConfirmDeleteModalProps) {
    const [confirmText, setConfirmText] = useState('')
    const [isDeleting, setIsDeleting] = useState(false)
    const [error, setError] = useState('')

    const canDelete = confirmText.toLowerCase() === itemName.toLowerCase()

    const handleConfirm = async () => {
        if (!canDelete) return

        setIsDeleting(true)
        setError('')

        try {
            await onConfirm()
            setConfirmText('')
            onClose()
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Deletion failed')
        } finally {
            setIsDeleting(false)
        }
    }

    const handleClose = () => {
        if (isDeleting) return
        setConfirmText('')
        setError('')
        onClose()
    }

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="card w-full max-w-md p-0 shadow-2xl overflow-hidden animate-scale-in">
                {/* Header */}
                <div className="bg-red-500/10 p-6 border-b border-red-500/20">
                    <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-red-500/20 rounded-full flex items-center justify-center">
                                <AlertTriangle className="w-5 h-5 text-red-500" />
                            </div>
                            <div>
                                <h2 className="text-lg font-bold text-text-primary">{title}</h2>
                                <p className="text-sm text-text-secondary">This action cannot be undone</p>
                            </div>
                        </div>
                        <button
                            onClick={handleClose}
                            disabled={isDeleting}
                            className="text-text-muted hover:text-text-primary disabled:opacity-50"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {/* Body */}
                <div className="p-6 space-y-4">
                    <p className="text-text-secondary">
                        You are about to permanently delete the {itemType}:
                    </p>

                    <div className="p-3 bg-background-tertiary rounded-lg border border-border-subtle">
                        <p className="font-mono font-bold text-text-primary">{itemName}</p>
                    </div>

                    {cascadeWarning && (
                        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                            <p className="text-sm text-red-600 dark:text-red-400 font-medium">
                                ⚠️ {cascadeWarning}
                            </p>
                            {cascadeCount !== undefined && cascadeCount > 0 && (
                                <p className="text-xs text-red-500 mt-1">
                                    {cascadeCount} item(s) will be deleted
                                </p>
                            )}
                        </div>
                    )}

                    <div>
                        <label className="label text-xs">
                            Type <span className="font-mono font-bold">{itemName}</span> to confirm:
                        </label>
                        <input
                            type="text"
                            value={confirmText}
                            onChange={(e) => setConfirmText(e.target.value)}
                            placeholder={itemName}
                            className="input mt-1"
                            disabled={isDeleting}
                            autoFocus
                        />
                    </div>

                    {error && (
                        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-600 text-sm">
                            {error}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-6 bg-background-secondary border-t border-border-subtle flex justify-end gap-3">
                    <button
                        onClick={handleClose}
                        disabled={isDeleting}
                        className="btn btn-secondary"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleConfirm}
                        disabled={!canDelete || isDeleting}
                        className="btn bg-red-500 hover:bg-red-600 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isDeleting ? (
                            <span className="flex items-center gap-2">
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Deleting...
                            </span>
                        ) : (
                            'Delete Permanently'
                        )}
                    </button>
                </div>
            </div>
        </div>
    )
}

/**
 * Simple loading button wrapper for async actions
 */
interface LoadingButtonProps {
    onClick: () => Promise<void>
    disabled?: boolean
    className?: string
    children: ReactNode
    loadingText?: string
}

export function LoadingButton({
    onClick,
    disabled,
    className = '',
    children,
    loadingText = 'Processing...'
}: LoadingButtonProps) {
    const [isLoading, setIsLoading] = useState(false)

    const handleClick = async () => {
        if (isLoading || disabled) return
        setIsLoading(true)
        try {
            await onClick()
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <button
            onClick={handleClick}
            disabled={isLoading || disabled}
            className={`${className} ${isLoading ? 'cursor-not-allowed' : ''}`}
        >
            {isLoading ? (
                <span className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    {loadingText}
                </span>
            ) : (
                children
            )}
        </button>
    )
}
