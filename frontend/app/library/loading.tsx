import { Skeleton, SkeletonGrid } from '@/components/ui/Skeleton'

// Shown while the library loads; mirrors the collections card grid.
export default function Loading() {
    return (
        <div className="container-custom py-6 sm:py-8 px-4 sm:px-6" aria-busy="true">
            <div className="space-y-6">
                <div className="space-y-2">
                    <Skeleton height="36px" width="25%" />
                    <Skeleton height="16px" width="40%" />
                </div>
                <SkeletonGrid count={4} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4" />
            </div>
        </div>
    )
}
