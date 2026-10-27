import { Skeleton } from '@/components/ui/Skeleton'
import { SkeletonResourceGrid } from '@/components/ui/Skeleton'

// Shown while the browse route loads; matches the page's filter + grid layout.
export default function Loading() {
    return (
        <div className="container-custom py-8" aria-busy="true">
            <div className="space-y-6">
                <div className="space-y-2">
                    <Skeleton height="36px" width="30%" />
                    <Skeleton height="16px" width="45%" />
                </div>
                <div className="card p-4 space-y-3">
                    <div className="flex flex-wrap gap-2">
                        {Array.from({ length: 5 }).map((_, i) => (
                            <Skeleton key={i} height="32px" width="110px" className="rounded-full" />
                        ))}
                    </div>
                </div>
                <SkeletonResourceGrid count={6} />
            </div>
        </div>
    )
}
