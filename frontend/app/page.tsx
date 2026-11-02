'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Search, Upload, FileText, Star, Download, Eye } from 'lucide-react'
import { api, apiHelpers } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { CatalogRow } from '@/components/ui/CatalogRow'
import { ResourceTile, ResourceTileData } from '@/components/ui/ResourceTile'

/**
 * Catalog homepage (Netflix-style: billboard hero + named shelves).
 *
 * Order follows docs/research/2026-11-02-netflix-catalog-homepage.md:
 * personal state first ("From your library"), then recency, popularity,
 * quality, then branch/category rows. Rows hide under 5 items; the page
 * degrades to discovery-only rows for anonymous visitors.
 */

interface Stats {
    resources: number
    users: number
    downloads: number
    courses: number
}

interface CatalogState {
    recent: ResourceTileData[]
    mostRead: ResourceTileData[]
    topRated: ResourceTileData[]
    departments: string[]
    branches: string[]
    branchRows: { name: string; items: ResourceTileData[] }[]
    tagRows: { key: string; label: string; items: ResourceTileData[] }[]
}

interface ConfiguredShelf {
    id: string
    title: string
    source_type: string
    source_value: string | null
    item_limit: number
}

interface ConfiguredRow {
    title: string
    seeAll: string
    items: ResourceTileData[]
}

/** Search params for one configured shelf (mirrors admin source_type values). */
function shelfSearchParams(def: ConfiguredShelf) {
    const size = Math.min(Math.max(def.item_limit, 1), 48)
    switch (def.source_type) {
        case 'recent': return { sort_by: 'recent', size, page: 1 }
        case 'most_read': return { sort_by: 'views', size, page: 1 }
        case 'most_downloaded': return { sort_by: 'downloads', size, page: 1 }
        case 'top_rated': return { sort_by: 'top_rated', min_ratings: 3, size, page: 1 }
        case 'tag': return { tags: def.source_value ?? '', sort_by: 'views', size, page: 1 }
        case 'branch': return { branch: def.source_value ?? '', sort_by: 'views', size, page: 1 }
        case 'subject': return { department: def.source_value ?? '', sort_by: 'views', size, page: 1 }
        default: return { sort_by: 'recent', size, page: 1 }
    }
}

function shelfSeeAllHref(def: ConfiguredShelf): string {
    switch (def.source_type) {
        case 'recent': return '/browse?sort_by=recent'
        case 'most_read': return '/browse?sort_by=views'
        case 'most_downloaded': return '/browse?sort_by=downloads'
        case 'top_rated': return '/browse?sort_by=top_rated'
        case 'tag': return `/browse?tags=${encodeURIComponent(def.source_value ?? '')}&sort_by=views`
        case 'branch': return `/browse?branch=${encodeURIComponent(def.source_value ?? '')}&sort_by=views`
        case 'subject': return `/browse?department=${encodeURIComponent(def.source_value ?? '')}&sort_by=views`
        default: return '/browse?sort_by=recent'
    }
}

interface SavedState {
    name: string
    items: ResourceTileData[]
}

const EMPTY_CATALOG: CatalogState = {
    recent: [], mostRead: [], topRated: [],
    departments: [], branches: [],
    branchRows: [], tagRows: [],
}

const TAG_ROWS = [
    { key: 'exam', label: 'Past exam papers' },
    { key: 'notes', label: 'Notes & handouts' },
] as const

const unwrapResults = (data: any): ResourceTileData[] => data?.results ?? data ?? []

function formatNumber(num: number) {
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K+`
    return num.toString()
}

export default function HomePage() {
    const [stats, setStats] = useState<Stats | null>(null)
    const [searchQuery, setSearchQuery] = useState('')
    const [catalog, setCatalog] = useState<CatalogState | null>(null) // null = still loading main rows
    const [secondaryLoading, setSecondaryLoading] = useState(true)
    const [saved, setSaved] = useState<SavedState | null>(null)
    // null = shelf config still loading; [] = not configured (built-ins render);
    // non-empty = admin-configured rows replace the built-ins.
    const [configuredRows, setConfiguredRows] = useState<ConfiguredRow[] | null>(null)
    const [greeting, setGreeting] = useState('')
    const { user } = useAuth()
    const router = useRouter()

    useEffect(() => {
        api.get('/stats')
            .then(res => setStats(res.data))
            .catch(() => setStats(null))
    }, [])

    // Admin-configured catalog shelves (public endpoint; empty/failed read
    // keeps the built-in default rows — the config is purely additive).
    useEffect(() => {
        let cancelled = false
        ;(async () => {
            let defs: ConfiguredShelf[] = []
            try {
                const res = await apiHelpers.getCatalogShelves()
                defs = Array.isArray(res.data) ? res.data : []
            } catch {
                defs = []
            }
            if (cancelled) return
            if (defs.length === 0) { setConfiguredRows([]); return }
            const settled = await Promise.allSettled(
                defs.map(def => apiHelpers.search(shelfSearchParams(def))),
            )
            if (cancelled) return
            setConfiguredRows(defs.map((def, i) => ({
                title: def.title,
                seeAll: shelfSeeAllHref(def),
                items: settled[i].status === 'fulfilled' ? unwrapResults(settled[i].value.data) : [],
            })))
        })()
        return () => { cancelled = true }
    }, [])

    // Time-based greeting set after mount (avoids SSR/CSR hydration mismatch).
    useEffect(() => {
        const h = new Date().getHours()
        setGreeting(h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening')
    }, [])

    useEffect(() => {
        let cancelled = false
        const loadPrimary = async () => {
            const settled = await Promise.allSettled([
                api.get('/search/filters'),
                api.get('/search/recent', { params: { limit: 14 } }),
                apiHelpers.search({ sort_by: 'views', size: 14, page: 1 }),
                apiHelpers.search({ sort_by: 'top_rated', min_ratings: 3, size: 14, page: 1 }),
            ])
            if (cancelled) return
            const filters = settled[0].status === 'fulfilled' ? settled[0].value.data : null
            const state: CatalogState = {
                recent: settled[1].status === 'fulfilled' ? unwrapResults(settled[1].value.data) : [],
                mostRead: settled[2].status === 'fulfilled' ? unwrapResults(settled[2].value.data) : [],
                topRated: settled[3].status === 'fulfilled' ? unwrapResults(settled[3].value.data) : [],
                departments: filters?.departments ?? [],
                branches: filters?.branches ?? [],
                branchRows: [],
                tagRows: [],
            }
            setCatalog(state)
            // Secondary shelves load after the first paint.
            const branchNames = state.branches.slice(0, 3)
            const secondary = await Promise.allSettled([
                ...branchNames.map(name =>
                    apiHelpers.search({ branch: name, sort_by: 'views', size: 12, page: 1 })),
                ...TAG_ROWS.map(tag =>
                    apiHelpers.search({ tags: tag.key, sort_by: 'views', size: 12, page: 1 })),
            ])
            if (cancelled) return
            const branchRows = branchNames.map((name, i) => ({
                name,
                items: secondary[i].status === 'fulfilled' ? unwrapResults(secondary[i].value.data) : [],
            }))
            const tagRows = TAG_ROWS.map((tag, i) => {
                const r = secondary[branchNames.length + i]
                return {
                    key: tag.key,
                    label: tag.label,
                    items: r.status === 'fulfilled' ? unwrapResults(r.value.data) : [],
                }
            })
            setCatalog(prev => (prev ? { ...prev, branchRows, tagRows } : prev))
            setSecondaryLoading(false)
        }
        loadPrimary()
        return () => { cancelled = true }
    }, [])

    // Personal row: the strongest saved-collection becomes "From your library".
    // Empty personal rows degrade silently (never render an empty shelf).
    useEffect(() => {
        if (!user) { setSaved(null); return }
        let cancelled = false
        ;(async () => {
            try {
                const res = await apiHelpers.getCollections()
                if (cancelled) return
                const collections = Array.isArray(res.data) ? res.data : []
                const best = [...collections]
                    .filter((c: any) => (c.item_count ?? 0) > 0)
                    .sort((a: any, b: any) =>
                        (b.item_count ?? 0) - (a.item_count ?? 0)
                        || Date.parse(b.updated_at ?? '') - Date.parse(a.updated_at ?? ''))[0]
                if (!best) { setSaved(null); return }
                const detail = await apiHelpers.getCollection(best.id)
                if (cancelled) return
                setSaved({
                    name: best.name,
                    items: (detail.data.items ?? []).filter((i: any) => i.slug && i.title),
                })
            } catch {
                if (!cancelled) setSaved(null)
            }
        })()
        return () => { cancelled = true }
    }, [user])

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault()
        if (searchQuery.trim()) {
            router.push(`/browse?q=${encodeURIComponent(searchQuery.trim())}`)
        }
    }

    const liveStats = [
        { value: stats ? formatNumber(stats.resources) : '—', label: stats?.resources === 1 ? 'Resource' : 'Resources' },
        { value: stats ? formatNumber(stats.users) : '—', label: stats?.users === 1 ? 'Student' : 'Students' },
        { value: stats ? formatNumber(stats.downloads) : '—', label: stats?.downloads === 1 ? 'Download' : 'Downloads' },
        { value: stats ? formatNumber(stats.courses) : '—', label: stats?.courses === 1 ? 'Course' : 'Courses' },
    ]

    const featured = catalog?.mostRead[0] ?? catalog?.recent[0] ?? null
    const firstName = user?.display_name
        ? user.display_name.split(' ')[0]
        : (user?.email ? user.email.split('@')[0] : null)

    const toTiles = useCallback(
        (items: any[]): ResourceTileData[] =>
            items.map(r => ({
                title: r.title,
                slug: r.slug,
                course_code: r.course_code,
                file_extension: r.file_extension,
                file_size: r.file_size,
                views: r.views,
                downloads: r.downloads,
                rating_count: r.rating_count,
                average_rating: r.average_rating,
            })),
        [],
    )

    return (
        <div className="min-h-screen">
            {/* Hero */}
            <section className="container-custom pt-14 pb-10">
                <div className="grid items-center gap-10 lg:grid-cols-[1.2fr_0.8fr]">
                    <div>
                        <p className="badge badge-primary mb-4">
                            Student Resource Library
                        </p>
                        <h1 className="text-4xl md:text-5xl font-bold text-text-primary mb-5 font-display">
                            {user && firstName ? (
                                <>{greeting || 'Welcome'}, <span className="text-accent-light">{firstName}</span></>
                            ) : (
                                'Find exactly what you need for class'
                            )}
                        </h1>
                        <p className="text-lg text-text-secondary mb-8">
                            Notes, exam papers and study material shared by students in your
                            courses. Search, or scroll the shelves below.
                        </p>

                        {/* Search — the retrieval anchor (most arrivals are exam-rush) */}
                        <form onSubmit={handleSearch} className="flex items-center max-w-xl mb-8">
                            <div className="relative flex-1">
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" aria-hidden="true" />
                                <input
                                    type="text"
                                    placeholder="Search notes, exams, course codes…"
                                    aria-label="Search resources"
                                    className="input pl-12 pr-4 py-3 text-lg"
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                />
                            </div>
                            <button type="submit" className="btn btn-primary ml-3 py-3 px-6">
                                Search
                            </button>
                        </form>

                        {/* Quick links */}
                        <div className="flex flex-wrap gap-4">
                            <Link href="/browse" className="btn btn-secondary">
                                <FileText className="w-4 h-4 mr-2" aria-hidden="true" />
                                Browse All
                            </Link>
                            {user && (
                                <Link href="/upload" className="btn btn-secondary">
                                    <Upload className="w-4 h-4 mr-2" aria-hidden="true" />
                                    Upload Resource
                                </Link>
                            )}
                            {!user && (
                                <Link href="/auth/register" className="btn btn-secondary">
                                    <Star className="w-4 h-4 mr-2" aria-hidden="true" />
                                    Create Account
                                </Link>
                            )}
                        </div>

                        {/* Explore chips — homepage does the filtering for you */}
                        {(catalog?.departments?.length || catalog?.branches?.length) ? (
                            <div className="mt-8 flex flex-wrap items-center gap-2">
                                <span className="text-xs text-text-muted uppercase tracking-wider mr-1">
                                    Explore
                                </span>
                                {catalog!.departments.slice(0, 4).map(name => (
                                    <Link
                                        key={`d-${name}`}
                                        href={`/browse?department=${encodeURIComponent(name)}`}
                                        className="badge badge-primary hover:bg-accent-primary/20"
                                    >
                                        {name}
                                    </Link>
                                ))}
                                {catalog!.branches.slice(0, 3).map(name => (
                                    <Link
                                        key={`b-${name}`}
                                        href={`/browse?branch=${encodeURIComponent(name)}`}
                                        className="badge hover:bg-background-tertiary"
                                    >
                                        {name}
                                    </Link>
                                ))}
                            </div>
                        ) : null}
                    </div>

                    {/* Billboard spotlight — a real library item, most-read first */}
                    {featured && (
                        <Link
                            href={`/resources/${featured.slug}`}
                            className="card card-interactive block p-6"
                        >
                            <p className="text-[11px] font-semibold uppercase tracking-widest text-warning-light mb-3">
                                {catalog!.mostRead.length > 0 ? 'Most read on campus' : 'Just added'}
                            </p>
                            <div className="flex items-start gap-4">
                                <div className="hidden sm:grid h-12 w-12 shrink-0 place-items-center rounded-lg bg-accent-primary/10">
                                    <FileText className="h-6 w-6 text-accent-primary" aria-hidden="true" />
                                </div>
                                <div className="min-w-0">
                                    <h2 className="text-xl font-semibold text-text-primary line-clamp-2 mb-2">
                                        {featured.title}
                                    </h2>
                                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-text-secondary">
                                        {featured.course_code && <span>{featured.course_code}</span>}
                                        {typeof featured.rating_count === 'number' && featured.rating_count >= 3 && (
                                            <span className="inline-flex items-center gap-1">
                                                <Star className="h-4 w-4 fill-warning text-warning" aria-hidden="true" />
                                                <span className="tabular-nums">{featured.average_rating?.toFixed(1)}</span>
                                            </span>
                                        )}
                                        <span className="inline-flex items-center gap-1 tabular-nums">
                                            <Eye className="h-4 w-4" aria-hidden="true" />
                                            {featured.views ?? 0}
                                        </span>
                                        <span className="inline-flex items-center gap-1 tabular-nums">
                                            <Download className="h-4 w-4" aria-hidden="true" />
                                            {featured.downloads ?? 0}
                                        </span>
                                    </div>
                                    <p className="mt-3 text-sm text-accent-light">
                                        Open resource →
                                    </p>
                                </div>
                            </div>
                        </Link>
                    )}
                </div>
            </section>

            {/* Catalog shelves */}
            <section className="container-custom mb-6 space-y-10" aria-label="Catalog">
                {catalog === null ? (
                    // Placeholder shelves exist from first paint (no layout jump).
                    <>
                        <CatalogRow loading title="Recently added" />
                        <CatalogRow loading title="Most read" />
                        <CatalogRow loading title="Top rated" />
                    </>
                ) : (
                    <>
                        {saved && saved.items.length >= 3 && (
                            <CatalogRow
                                title={`From your library — ${saved.name}`}
                                seeAllHref="/library"
                                loading={secondaryLoading && saved.items.length === 0}
                            >
                                {saved.items.map(item => (
                                    <ResourceTile key={item.slug} resource={item} compact />
                                ))}
                            </CatalogRow>
                        )}

                        {configuredRows !== null && configuredRows.length > 0 ? (
                            configuredRows.map(row => (
                                <CatalogRow
                                    key={`sh-${row.title}`}
                                    title={row.title}
                                    seeAllHref={row.seeAll}
                                >
                                    {toTiles(row.items).map(r => <ResourceTile key={r.slug} resource={r} />)}
                                </CatalogRow>
                            ))
                        ) : (
                            <>
                        <CatalogRow title="Recently added" seeAllHref="/browse?sort_by=recent">
                            {toTiles(catalog.recent).map(r => <ResourceTile key={r.slug} resource={r} />)}
                        </CatalogRow>

                        <CatalogRow title="Most read" seeAllHref="/browse?sort_by=views">
                            {toTiles(catalog.mostRead).map(r => <ResourceTile key={r.slug} resource={r} />)}
                        </CatalogRow>

                        <CatalogRow title="Top rated" seeAllHref="/browse?sort_by=top_rated" minItems={5}>
                            {toTiles(catalog.topRated).map(r => <ResourceTile key={r.slug} resource={r} />)}
                        </CatalogRow>

                        {catalog.branchRows.map(row => (
                            <CatalogRow
                                key={`br-${row.name}`}
                                title={`Popular in ${row.name}`}
                                seeAllHref={`/browse?branch=${encodeURIComponent(row.name)}&sort_by=views`}
                            >
                                {toTiles(row.items).map(r => <ResourceTile key={r.slug} resource={r} />)}
                            </CatalogRow>
                        ))}

                        {catalog.tagRows.map(row => (
                            <CatalogRow
                                key={`tg-${row.key}`}
                                title={row.label}
                                seeAllHref={`/browse?tags=${encodeURIComponent(row.key)}&sort_by=views`}
                            >
                                {toTiles(row.items).map(r => <ResourceTile key={r.slug} resource={r} />)}
                            </CatalogRow>
                        ))}
                            </>
                        )}
                    </>
                )}
            </section>

            {/* Live stats */}
            <section className="border-y border-border-subtle bg-background-secondary py-8">
                <div className="container-custom">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
                        {liveStats.map((stat) => (
                            <div key={stat.label}>
                                <p className="text-3xl font-bold font-display text-accent-light mb-2 tabular-nums">
                                    {stat.value}
                                </p>
                                <p className="text-text-secondary">{stat.label}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Why this library */}
            <section className="container-custom py-12">
                <div className="card p-6 md:p-10">
                    <h2 className="text-2xl font-bold text-text-primary mb-8 font-display">
                        Why Use Student Library?
                    </h2>

                    <ul className="md:grid md:grid-cols-2 md:gap-x-12 md:gap-y-0 divide-y divide-border-subtle md:divide-y-0">
                        {[
                            {
                                icon: Upload,
                                title: 'Unlimited Storage',
                                body: 'Upload your notes, exams, and study materials without worrying about storage limits.',
                            },
                            {
                                icon: Search,
                                title: 'Advanced Search',
                                body: 'Find what you need with filters by course, department, and tags.',
                            },
                            {
                                icon: Star,
                                title: 'Community Ratings',
                                body: 'Rate and review resources so the best study materials surface to everyone.',
                            },
                        ].map((feature, i) => (
                            <li
                                key={feature.title}
                                className={`flex items-start gap-4 py-6 md:py-8 ${i === 2 ? 'md:col-span-2 md:border-t md:border-border-subtle' : ''}`}
                            >
                                <feature.icon className="w-6 h-6 text-accent-primary shrink-0 mt-1" aria-hidden="true" />
                                <div>
                                    <h3 className="text-lg font-semibold text-text-primary mb-1.5 font-display">
                                        {feature.title}
                                    </h3>
                                    <p className="text-text-secondary">
                                        {feature.body}
                                    </p>
                                </div>
                            </li>
                        ))}
                    </ul>
                </div>
            </section>

            {/* Closing action */}
            <section className="container-custom py-12">
                <div className="card p-8 md:p-12 text-center">
                    {user ? (
                        <>
                            <h2 className="text-2xl md:text-3xl font-bold text-text-primary mb-4 font-display">
                                Welcome back, {(user.display_name || 'User').split(' ')[0]}
                            </h2>
                            <p className="text-text-secondary mb-8 max-w-xl mx-auto">
                                Continue where you left off. Browse new resources or contribute your own.
                            </p>
                            <div className="flex flex-wrap justify-center gap-4">
                                <Link href="/browse" className="btn btn-primary px-8 py-3">
                                    Browse Resources
                                </Link>
                                <Link href="/upload" className="btn btn-secondary px-8 py-3">
                                    Upload New
                                </Link>
                            </div>
                        </>
                    ) : (
                        <>
                            <h2 className="text-2xl md:text-3xl font-bold text-text-primary mb-4 font-display">
                                Ready to Get Started?
                            </h2>
                            <p className="text-text-secondary mb-8 max-w-xl mx-auto">
                                Join students sharing knowledge with their peers. It&apos;s free and takes less than a minute.
                            </p>
                            <div className="flex flex-wrap justify-center gap-4">
                                <Link href="/auth/register" className="btn btn-primary px-8 py-3">
                                    Create Account
                                </Link>
                                <Link href="/browse" className="btn btn-secondary px-8 py-3">
                                    Browse Resources
                                </Link>
                            </div>
                        </>
                    )}
                </div>
            </section>
        </div>
    )
}
