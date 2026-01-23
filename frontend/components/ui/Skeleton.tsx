/**
 * Skeleton Loader Components
 * Production-grade loading states with shimmer animations
 */

import React from 'react';

// Shimmer keyframes
const shimmerStyles = `
  @keyframes shimmer {
    0% {
      background-position: -1000px 0;
    }
    100% {
      background-position: 1000px 0;
    }
  }
`;

interface SkeletonProps {
    className?: string;
    width?: string;
    height?: string;
    variant?: 'text' | 'circular' | 'rectangular';
}

export const Skeleton: React.FC<SkeletonProps> = ({
    className = '',
    width,
    height,
    variant = 'rectangular',
}) => {
    const baseClasses = 'animate-pulse bg-gradient-to-r from-gray-200 via-gray-300 to-gray-200 bg-[length:1000px_100%]';

    const variantClasses = {
        text: 'rounded',
        circular: 'rounded-full',
        rectangular: 'rounded-lg',
    };

    const style: React.CSSProperties = {
        width: width || '100%',
        height: height || (variant === 'text' ? '1em' : '100%'),
        animation: 'shimmer 2s infinite linear',
    };

    return (
        <>
            <style>{shimmerStyles}</style>
            <div
                className={`${baseClasses} ${variantClasses[variant]} ${className}`}
                style={style}
                role="status"
                aria-label="Loading..."
            />
        </>
    );
};

// Resource Card Skeleton
export const SkeletonResourceCard = () => (
    <div className="card overflow-hidden h-full flex flex-col border border-border-subtle">
        <Skeleton height="180px" />
        <div className="p-5 flex-1 flex flex-col gap-3">
            <Skeleton height="24px" width="80%" />
            <Skeleton height="16px" width="100%" />
            <Skeleton height="16px" width="60%" />
            <div className="mt-auto flex justify-between items-center">
                <Skeleton height="14px" width="60px" />
                <Skeleton height="32px" width="80px" className="rounded-lg" />
            </div>
        </div>
    </div>
);

// Resource Grid Skeleton
export const SkeletonResourceGrid: React.FC<{ count?: number }> = ({ count = 6 }) => {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: count }).map((_, i) => (
                <SkeletonResourceCard key={i} />
            ))}
        </div>
    );
};

// Generic Grid Skeleton
export const SkeletonGrid: React.FC<{ count?: number; className?: string }> = ({ count = 4, className = "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4" }) => {
    return (
        <div className={className}>
            {Array.from({ length: count }).map((_, i) => (
                <Skeleton key={i} height="120px" className="rounded-xl border border-border-subtle" />
            ))}
        </div>
    );
};

// Resource Detail Skeleton
export const SkeletonResourceDetail: React.FC = () => {
    return (
        <div className="space-y-8 animate-fade-in">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 space-y-6">
                    <div className="card p-0 overflow-hidden border border-border-subtle">
                        <Skeleton height="400px" />
                    </div>
                    <div className="card p-6 border border-border-subtle space-y-4">
                        <Skeleton height="32px" width="40%" />
                        <div className="flex gap-4">
                            <Skeleton height="20px" width="100px" />
                            <Skeleton height="20px" width="100px" />
                        </div>
                        <div className="pt-4 space-y-2">
                            <Skeleton height="16px" />
                            <Skeleton height="16px" />
                            <Skeleton height="16px" width="80%" />
                        </div>
                    </div>
                </div>
                <div className="space-y-6">
                    <div className="card p-6 border border-border-subtle space-y-4">
                        <Skeleton height="48px" className="rounded-lg" />
                        <div className="grid grid-cols-2 gap-3">
                            <Skeleton height="40px" className="rounded-lg" />
                            <Skeleton height="40px" className="rounded-lg" />
                        </div>
                    </div>
                    <div className="card p-6 border border-border-subtle space-y-4">
                        <Skeleton height="24px" width="50%" />
                        <div className="space-y-4">
                            {[1, 2, 3].map(i => (
                                <div key={i} className="flex gap-3">
                                    <Skeleton variant="circular" width="40px" height="40px" />
                                    <div className="flex-1 space-y-2">
                                        <Skeleton height="14px" width="40%" />
                                        <Skeleton height="12px" />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

// Profile Skeleton
export const SkeletonProfile: React.FC = () => {
    return (
        <div className="space-y-8 animate-fade-in">
            <div className="card p-8 border border-border-subtle">
                <div className="flex flex-col md:flex-row items-center gap-8">
                    <Skeleton variant="circular" width="120px" height="120px" />
                    <div className="flex-1 space-y-3 text-center md:text-left">
                        <Skeleton height="32px" width="200px" />
                        <Skeleton height="20px" width="150px" />
                        <div className="flex gap-2 justify-center md:justify-start">
                            <Skeleton height="24px" width="80px" className="rounded-full" />
                            <Skeleton height="24px" width="80px" className="rounded-full" />
                        </div>
                    </div>
                </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="md:col-span-1 space-y-6">
                    <div className="card p-6 border border-border-subtle space-y-4">
                        <Skeleton height="24px" width="60%" />
                        <div className="space-y-4">
                            <Skeleton height="40px" />
                            <Skeleton height="40px" />
                            <Skeleton height="40px" />
                        </div>
                    </div>
                </div>
                <div className="md:col-span-2 space-y-6">
                    <div className="card p-6 border border-border-subtle space-y-4">
                        <div className="flex justify-between items-center">
                            <Skeleton height="24px" width="30%" />
                            <Skeleton height="32px" width="120px" className="rounded-lg" />
                        </div>
                        <div className="space-y-4 pt-4">
                            {[1, 2, 3].map(i => (
                                <div key={i} className="flex items-center justify-between p-4 border border-border-subtle rounded-lg">
                                    <div className="space-y-2">
                                        <Skeleton height="16px" width="180px" />
                                        <Skeleton height="12px" width="100px" />
                                    </div>
                                    <Skeleton height="24px" width="60px" className="rounded" />
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

// Table Row Skeleton
export const SkeletonTableRow: React.FC<{ columns?: number }> = ({ columns = 4 }) => {
    return (
        <div className="flex items-center gap-4">
            {Array.from({ length: columns }).map((_, i) => (
                <div key={i} className="flex-1">
                    <Skeleton height="20px" width="90%" />
                </div>
            ))}
        </div>
    );
};

// Table Skeleton
export const SkeletonTable: React.FC<{ rows?: number; columns?: number }> = ({
    rows = 5,
    columns = 4
}) => {
    return (
        <div className="card overflow-hidden border border-border-subtle">
            <div className="bg-background-secondary p-4 border-b border-border-subtle">
                <div className="flex gap-4">
                    {Array.from({ length: columns }).map((_, i) => (
                        <div key={i} className="flex-1">
                            <Skeleton height="16px" width="60%" />
                        </div>
                    ))}
                </div>
            </div>
            <div className="divide-y divide-border-subtle">
                {Array.from({ length: rows }).map((_, i) => (
                    <div key={i} className="p-4">
                        <SkeletonTableRow columns={columns} />
                    </div>
                ))}
            </div>
        </div>
    );
};

// Search Results Skeleton
export const SkeletonSearchResults: React.FC = () => {
    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <Skeleton height="24px" width="200px" />
                <Skeleton height="32px" width="150px" className="rounded-lg" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[...Array(6)].map((_, i) => (
                    <SkeletonResourceCard key={i} />
                ))}
            </div>
        </div>
    );
};

export default Skeleton;
