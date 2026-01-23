/**
 * Progress Bar Component
 * For file upload/download progress tracking
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
        default: 'bg-blue-600',
        success: 'bg-green-600',
        error: 'bg-red-600',
        warning: 'bg-yellow-600',
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
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            {label}
                        </span>
                    )}
                    {showPercentage && (
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            {Math.round(clampedValue)}%
                        </span>
                    )}
                </div>
            )}

            <div className={`w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden ${heights[size]}`}>
                <div
                    className={`${variantColors[variant]} ${heights[size]} rounded-full transition-all duration-300 ease-out`}
                    style={{ width: `${clampedValue}%` }}
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
        default: 'text-blue-600',
        success: 'text-green-600',
        error: 'text-red-600',
        warning: 'text-yellow-600',
    };

    return (
        <div className="relative inline-flex items-center justify-center">
            <svg
                width={size}
                height={size}
                className="transform -rotate-90"
            >
                {/* Background circle */}
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    stroke="currentColor"
                    strokeWidth={strokeWidth}
                    fill="none"
                    className="text-gray-200 dark:text-gray-700"
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
                    className={`${variantColors[variant]} transition-all duration-300 ease-out`}
                />
            </svg>

            {showPercentage && (
                <div className="absolute inset-0 flex items-center justify-center">
                    <span className={`text-2xl font-bold ${variantColors[variant]}`}>
                        {Math.round(clampedValue)}%
                    </span>
                </div>
            )}
        </div>
    );
};

export default ProgressBar;
