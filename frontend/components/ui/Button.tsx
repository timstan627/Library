'use client'

import React, { forwardRef } from 'react'
import { Loader2, Check, AlertCircle } from 'lucide-react'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'success'
export type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: ButtonVariant
    size?: ButtonSize
    isLoading?: boolean
    isSuccess?: boolean
    isError?: boolean
    loadingText?: string
    successText?: string
    leftIcon?: React.ReactNode
    rightIcon?: React.ReactNode
    fullWidth?: boolean
}

const variantClasses: Record<ButtonVariant, string> = {
    primary: 'bg-accent-primary hover:bg-accent-hover text-accent-ink border-transparent',
    secondary: 'bg-background-tertiary hover:bg-background-secondary text-text-primary border-border-medium hover:border-border-strong',
    ghost: 'bg-transparent hover:bg-background-tertiary text-text-secondary hover:text-text-primary border-transparent',
    danger: 'bg-danger hover:bg-danger-hover text-accent-ink border-transparent',
    success: 'bg-success hover:bg-success text-accent-ink border-transparent',
}

const sizeClasses: Record<ButtonSize, string> = {
    sm: 'px-3 py-1.5 text-sm gap-1.5',
    md: 'px-4 py-2 text-sm gap-2',
    lg: 'px-6 py-3 text-base gap-2.5',
}

/**
 * Universal Button component implementing all required interaction states.
 * 
 * Features:
 * - Loading state with spinner
 * - Success state with checkmark
 * - Error state styling
 * - Disabled state
 * - Keyboard support
 * - Touch feedback
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
    (
        {
            children,
            variant = 'primary',
            size = 'md',
            isLoading = false,
            isSuccess = false,
            isError = false,
            loadingText,
            successText,
            leftIcon,
            rightIcon,
            fullWidth = false,
            disabled,
            className = '',
            onClick,
            type = 'button',
            ...props
        },
        ref
    ) => {
        const isDisabled = disabled || isLoading

        // Handle click with protection
        const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
            if (isDisabled) {
                e.preventDefault()
                return
            }
            onClick?.(e)
        }

        // Determine what to show
        let content: React.ReactNode = children
        let icon: React.ReactNode = leftIcon

        if (isLoading) {
            icon = <Loader2 className="w-4 h-4 animate-spin" />
            content = loadingText || children
        } else if (isSuccess) {
            icon = <Check className="w-4 h-4" />
            content = successText || children
        } else if (isError) {
            icon = <AlertCircle className="w-4 h-4" />
        }

        return (
            <button
                ref={ref}
                type={type}
                disabled={isDisabled}
                onClick={handleClick}
                aria-busy={isLoading}
                aria-disabled={isDisabled}
                className={`
                    inline-flex items-center justify-center font-medium rounded-lg border
                    transition-[background-color,border-color,color,box-shadow,transform] duration-150 ease-expo
                    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary focus-visible:ring-offset-0
                    active:scale-[0.98]
                    disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100
                    ${variantClasses[isError ? 'danger' : isSuccess ? 'success' : variant]}
                    ${sizeClasses[size]}
                    ${fullWidth ? 'w-full' : ''}
                    ${className}
                `}
                {...props}
            >
                {icon && <span className="shrink-0">{icon}</span>}
                <span>{content}</span>
                {rightIcon && !isLoading && <span className="shrink-0">{rightIcon}</span>}
            </button>
        )
    }
)

Button.displayName = 'Button'

/**
 * Form-specific button that shows "Submitting..." text during loading
 */
export const FormButton = forwardRef<HTMLButtonElement, ButtonProps>(
    ({ loadingText = 'Submitting...', type = 'submit', ...props }, ref) => {
        return <Button ref={ref} type={type} loadingText={loadingText} {...props} />
    }
)

FormButton.displayName = 'FormButton'
