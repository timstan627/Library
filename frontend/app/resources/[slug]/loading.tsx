import { SkeletonResourceDetail } from '@/components/ui/Skeleton'

// Shown while a resource detail page loads; mirrors the two-column detail layout.
export default function Loading() {
    return (
        <div className="container-custom py-8" aria-busy="true">
            <SkeletonResourceDetail />
        </div>
    )
}
