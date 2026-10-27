import { Skeleton } from '@/components/ui/Skeleton'

// Root fallback while a route segment's code chunk loads.
export default function Loading() {
    return (
        <div className="container-custom py-8" aria-busy="true">
            <div className="space-y-4">
                <Skeleton height="36px" width="35%" />
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
                    {Array.from({ length: 6 }).map((_, i) => (
                        <Skeleton key={i} height="120px" />
                    ))}
                </div>
            </div>
        </div>
    )
}
