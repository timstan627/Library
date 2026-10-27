import { Skeleton, SkeletonTable } from '@/components/ui/Skeleton'

// Shown while an admin section loads; the shared admin section nav above
// persists, so orientation is never lost.
export default function Loading() {
    return (
        <div className="container-custom py-8" aria-busy="true">
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <div className="space-y-2">
                        <Skeleton height="36px" width="220px" />
                        <Skeleton height="16px" width="280px" />
                    </div>
                    <Skeleton height="64px" width="220px" />
                </div>
                <SkeletonTable rows={6} columns={5} />
            </div>
        </div>
    )
}
