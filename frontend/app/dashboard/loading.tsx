import { Skeleton, SkeletonGrid } from '@/components/ui/Skeleton'

// Shown while the student dashboard loads.
export default function Loading() {
    return (
        <div className="container-custom py-8" aria-busy="true">
            <div className="space-y-6">
                <div className="space-y-2">
                    <Skeleton height="36px" width="40%" />
                    <Skeleton height="16px" width="50%" />
                </div>
                <SkeletonGrid count={4} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4" />
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {Array.from({ length: 3 }).map((_, i) => (
                        <Skeleton key={i} height="160px" />
                    ))}
                </div>
            </div>
        </div>
    )
}
