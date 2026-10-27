import { SkeletonProfile } from '@/components/ui/Skeleton'

// Shown while the profile loads; mirrors the profile header + two-column body.
export default function Loading() {
    return (
        <div className="container-custom py-8" aria-busy="true">
            <SkeletonProfile />
        </div>
    )
}
