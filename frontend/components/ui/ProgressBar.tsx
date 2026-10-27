/**
 * Progress Bar Component
 * For file upload/download progress tracking.
 * Linear bars animate via transform: scaleX (composited, no layout thrash).
 */

import React from 'react';

interface ProgressBarProps {
    value: number; // 0-100
    label?: string;
    variant?: 'default' | 'success' | 'error' | 'warning';
    showPercentage?: boolean;
    size?: 'sm' | 'md' | 'lg';
    className?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
    value,
    label,
    variant = 'default',
    showPercentage = true,
    size = 'md',
    className = '',
}) => {
    // Clamp value between 0-100
    const clampedValue = Math.min(100, Math.max(0, value));

    const variantColors = {
        default: 'bg-accent-primary',
        success: 'bg-success',
        error: 'bg-danger',
        warning: 'bg-warning',
    };

    const heights = {
        sm: 'h-1',
        md: 'h-2',
        lg: 'h-3',
    };

    return (
        <div className={`w-full ${className}`}>
            {(label || showPercentage) && (
                <div className="flex justify-between items-center mb-2">
                    {label && (
                        <span className="text-sm font-medium text-text-secondary tabular-nums">
                            {label}
                        </span>
                    )}
                    {showPercentage && (
                        <span className="text-sm font-medium text-text-secondary tabular-nums">
                            {Math.round(clampedValue)}%
                        </span>
                    )}
                </div>
            )}

            <div className={`w-full bg-background-tertiary rounded-full overflow-hidden ${heights[size]}`}>
                <div
                    className={`w-full ${variantColors[variant]} h-full rounded-full transform-gpu origin-left transition-transform duration-300 ease-out`}
                    style={{ transform: `scaleX(${clampedValue / 100})` }}
                    role="progressbar"
                    aria-valuenow={clampedValue}
                    aria-valuemin={0}
                    aria-valuemax={100}
                />
            </div>
        </div>
    );
};

interface CircularProgressProps {
    value: number; // 0-100
    size?: number;
    strokeWidth?: number;
    variant?: 'default' | 'success' | 'error' | 'warning';
    showPercentage?: boolean;
}

export const CircularProgress: React.FC<CircularProgressProps> = ({
    value,
    size = 120,
    strokeWidth = 8,
    variant = 'default',
    showPercentage = true,
}) => {
    const clampedValue = Math.min(100, Math.max(0, value));
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (clampedValue / 100) * circumference;

    const variantColors = {
        default: 'text-accent-primary',
        success: 'text-success',
        error: 'text-danger',
        warning: 'text-warning',
    };

    return (
        <div className="relative inline-flex items-center justify-center">
            <svg
                width={size}
                height={size}
                viewBox={`0 0 ${size} ${size}`}
                className="transform -rotate-90"
                aria-hidden="true"
                focusable="false"
            >
                {/* Background circle */}
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    stroke="currentColor"
                    strokeWidth={strokeWidth}
                    fill="none"
                    className="text-background-tertiary"
                />
                {/* Progress circle */}
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    stroke="currentColor"
                    strokeWidth={strokeWidth}
                    fill="none"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    strokeLinecap="round"
                    className={`${variantColors[variant]} transition-[stroke-dashoffset] duration-300 ease-out`}
                />
            </svg>

            {showPercentage && (
                <div className="absolute inset-0 flex items-center justify-center">
                    <span className={`text-2xl font-bold tabular-nums ${variantColors[variant]}`}>
                        {Math.round(clampedValue)}%
                    </span>
                </div>
            )}
        </div>
    );
};

export default ProgressBar;
