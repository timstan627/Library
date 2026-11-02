'use client'

import { useState, type ReactNode } from 'react'
import { AlertTriangle, Loader2 } from 'lucide-react'
import { AdminModal } from '@/components/ui/AdminModal'

interface ConfirmDeleteModalProps {
    isOpen: boolean
    onClose: () => void
    onConfirm: () => Promise<void>
    title: string
    itemName: string
    itemType: string
    cascadeWarning?: string
    cascadeCount?: number
    /** Header line under the title. Defaults to "This action cannot be undone". */
    subtitle?: string
    /** When false the confirm button is enabled immediately (no typing). */
    typeToConfirm?: boolean
    /** The token the user must type; defaults to itemName. */
    confirmToken?: string
    /** Optional replacement for the item-name display box (e.g. a bulk summary). */
    itemLabel?: ReactNode
}

/**
 * HIGH-004: Type-to-Confirm Delete Modal
 *
 * Requires the user to type the item name to confirm deletion.
 * Shows cascade warning if deleting will affect other items.
 * Renders through AdminModal for one shared dialog scaffold.
 */
export function ConfirmDeleteModal({
    isOpen,
    onClose,
    onConfirm,
    title,
    itemName,
    itemType,
    cascadeWarning,
    cascadeCount,
    subtitle = 'This action cannot be undone',
    typeToConfirm = true,
    confirmToken,
    itemLabel,
}: ConfirmDeleteModalProps) {
    const [confirmText, setConfirmText] = useState('')
    const [isDeleting, setIsDeleting] = useState(false)
    const [error, setError] = useState('')

    const token = confirmToken ?? itemName
    const canDelete = !typeToConfirm || confirmText.toLowerCase() === token.toLowerCase()

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

    return (
        <AdminModal
            isOpen={isOpen}
            onClose={handleClose}
            title={title}
            description={subtitle}
            maxWidth="md"
            headerTone="danger"
            icon={
                <div className="w-10 h-10 bg-danger/20 rounded-full flex items-center justify-center shrink-0">
                    <AlertTriangle className="w-5 h-5 text-danger" />
                </div>
            }
        >
            <div className="p-6 space-y-4">
                <p className="text-text-secondary">
                    You are about to permanently delete the {itemType}:
                </p>

                <div className="p-3 bg-background-tertiary rounded-lg border border-border-subtle">
                    {itemLabel ?? <p className="font-mono font-bold text-text-primary">{itemName}</p>}
                </div>

                {cascadeWarning && (
                    <div className="p-4 bg-danger/10 border border-danger/30 rounded-lg">
                        <p className="text-sm text-danger font-medium">
                            {cascadeWarning}
                        </p>
                        {cascadeCount !== undefined && cascadeCount > 0 && (
                            <p className="text-xs text-danger mt-1">
                                {cascadeCount} item(s) will be deleted
                            </p>
                        )}
                    </div>
                )}

                {typeToConfirm && (
                    <div>
                        <label className="label text-xs">
                            Type <span className="font-mono font-bold">{token}</span> to confirm:
                        </label>
                        <input
                            type="text"
                            value={confirmText}
                            onChange={(e) => setConfirmText(e.target.value)}
                            placeholder={token}
                            className="input mt-1"
                            disabled={isDeleting}
                            autoFocus
                        />
                    </div>
                )}

                {isDeleting && !typeToConfirm && (
                    <p className="text-sm text-text-muted">Deleting…</p>
                )}

                {error && (
                    <div className="p-3 bg-danger/10 border border-danger/30 rounded-lg text-danger text-sm" role="alert">
                        {error}
                    </div>
                )}
            </div>

            <div className="px-6 py-6 bg-background-secondary border-t border-border-subtle flex justify-end gap-3">
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
                    className="btn btn-danger disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {isDeleting ? (
                        <span className="flex items-center gap-2">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Deleting...
                        </span>
                    ) : (
                        typeToConfirm ? 'Delete Permanently' : 'Delete'
                    )}
                </button>
            </div>
        </AdminModal>
    )
}
