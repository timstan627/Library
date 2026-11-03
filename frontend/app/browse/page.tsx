'use client'

/**
 * Catalog-style browse page (two modes, one URL contract).
 *
 * - Bare `/browse` → discovery shelves, mirroring the homepage catalog
 *   (Recently added / Most read / Top rated / per-branch / tag shelves).
 * - Any parameter — `q`, `department`, `branch`, `tags`, `semester`,
 *   `file_type`, or an explicit `sort_by` (even `recent`) → results mode:
 *   a titled result section with a grid/list toggle and a "Load more"
 *   pager (24 per page). Explicit params always mean "show me exactly
 *   this", so homepage See-all links land on correctly ordered rows.
 *
 * Everything the old page did is preserved: URL params, search box,
 * branch/department/tags/sort filtering, uploader/course-code/size/
 * description/tags on cards, error + empty states, total count. Added
 * on top: semester/file_type filters, shareable chip URLs via
 * `router.replace`, and the grid/list presentation. The API contract
 * in `lib/api.ts` is untouched.
 */

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Search, FileText, Download, Eye, Star, X, LayoutGrid, List, SlidersHorizontal, Loader2 } from 'lucide-react'
import { api, apiHelpers } from '@/lib/api'
import { CatalogRow } from '@/components/ui/CatalogRow'
import { ResourceTile, ResourceTileSkeleton, formatSize, ResourceTileData } from '@/components/ui/ResourceTile'
import FetchError from '@/components/ui/FetchError'

const PAGE_SIZE = 24

/**
 * Shape of a search hit (`ResourceResponse` in the backend). Everything
 * optional except the fields the list/grid always render.
 */
interface Resource {
    id: string
    title: string
    slug: string
    description?: string
    course_code?: string
    semester?: string
    branch?: string
    file_name?: string
    file_size: number
    file_extension?: string
    downloads: number
    views: number
    average_rating?: number | null
    rating_count: number
    tags?: string[]
    uploader_name?: string
}

interface Facets {
    departments: string[]
    semesters: string[]
    branches: string[]
    programs: string[]
    file_types: string[]
    tags: string[]
}

interface DiscoveryState {
    recent: Resource[]
    mostRead: Resource[]
    topRated: Resource[]
    branchRows: { name: string; items: Resource[] }[]
    tagRows: { key: string; label: string; items: Resource[] }[]
}

const SORT_OPTIONS = [
    { value: 'recent', label: 'Recently added' },
    { value: 'views', label: 'Most read' },
    { value: 'downloads', label: 'Most downloaded' },
    { value: 'rating', label: 'Highest rated' },
    { value: 'top_rated', label: 'Top rated' },
    { value: 'relevance', label: 'Relevance' },
]

// The same static tag list the backend `/search/filters` facet returns —
// tag chips stay usable even when the facets fetch fails.
const STATIC_TAG_OPTIONS = ['notes', 'exam', 'syllabus', 'assignments', 'lecture', 'tutorial', 'solved']

// Discovery shelf tag rows (same labels as the homepage).
const TAG_SHELF_ROWS = [
    { key: 'exam', label: 'Past exam papers' },
    { key: 'notes', label: 'Notes & handouts' },
] as const

const unwrapResults = (data: unknown): Resource[] => {
    const d = data as { results?: unknown } | null
    return Array.isArray(d?.results) ? (d.results as Resource[]) : Array.isArray(data) ? (data as Resource[]) : []
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
    items: Resource[]
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

function ChipRow({ label, options, isOptionActive, onSelect }: {
    label: string
    options: { value: string; label: string }[]
    isOptionActive: (value: string) => boolean
    onSelect: (value: string) => void
}) {
    return (
        <div className="flex items-center gap-2">
            <span className="w-16 shrink-0 text-[11px] font-medium uppercase tracking-wider text-text-muted sm:w-20">
                {label}
            </span>
            <div className="flex gap-1.5 overflow-x-auto no-scrollbar py-1">
                {options.map(option => {
                    const active = isOptionActive(option.value)
                    return (
                        <button
                            key={option.value}
                            type="button"
                            aria-pressed={active}
                            onClick={() => onSelect(option.value)}
                            className={`badge whitespace-nowrap transition-colors duration-150 ${
                                active
                                    ? 'badge-primary hover:bg-accent-primary/20'
                                    : 'hover:bg-background-tertiary'
                            }`}
                        >
                            {option.label}
                        </button>
                    )
                })}
            </div>
        </div>
    )
}

function ResultsTileGridSkeleton() {
    return (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4" aria-hidden="true">
            {Array.from({ length: 8 }).map((_, i) => <ResourceTileSkeleton key={i} />)}
        </div>
    )
}

function ResultsListSkeleton() {
    return (
        <div className="space-y-3" aria-hidden="true">
            {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="card space-y-3 p-4 skeleton">
                    <div className="flex gap-3">
                        <div className="h-10 w-10 shrink-0 rounded-lg bg-background-tertiary" />
                        <div className="flex-1 space-y-2">
                            <div className="h-4 w-2/3 rounded bg-background-tertiary" />
                            <div className="h-3 w-1/2 rounded bg-background-tertiary" />
                        </div>
                    </div>
                    <div className="h-3 w-full rounded bg-background-tertiary" />
                    <div className="h-3 w-3/4 rounded bg-background-tertiary" />
                </div>
            ))}
        </div>
    )
}

/** Full-width, detail-rich row for list view. */
function ResultListItem({ resource }: { resource: Resource }) {
    const showRating = typeof resource.rating_count === 'number'
        && resource.rating_count >= 3
        && typeof resource.average_rating === 'number'
    const tags = resource.tags ?? []
    return (
        <Link href={`/resources/${resource.slug}`} className="card card-interactive block p-4">
            <div className="flex items-start gap-3">
                <div className="hidden h-10 w-10 shrink-0 place-items-center rounded-lg bg-accent-primary/10 sm:grid">
                    <FileText className="h-5 w-5 text-accent-primary" aria-hidden="true" />
                </div>
                <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-3">
                        <h3 className="min-w-0 break-words text-base font-medium text-text-primary">
                            <span className="line-clamp-2">{resource.title}</span>
                        </h3>
                        {showRating && (
                            <span className="mt-0.5 inline-flex shrink-0 items-center gap-1 text-xs font-medium text-warning-light">
                                <Star className="h-3.5 w-3.5 fill-warning text-warning" aria-hidden="true" />
                                <span className="tabular-nums">{resource.average_rating!.toFixed(1)}</span>
                            </span>
                        )}
                    </div>

                    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs tabular-nums text-text-muted">
                        {resource.uploader_name && (
                            <span className="font-medium normal-nums text-text-secondary">{resource.uploader_name}</span>
                        )}
                        {resource.course_code && <span>{resource.course_code}</span>}
                        {resource.branch && <span>{resource.branch}</span>}
                        {resource.semester && <span>Semester {resource.semester}</span>}
                        <span>{(resource.file_extension || 'file').toUpperCase()}</span>
                        {formatSize(resource.file_size) && <span>{formatSize(resource.file_size)}</span>}
                        <span className="inline-flex items-center gap-1">
                            <Eye className="h-3 w-3" aria-hidden="true" />
                            {resource.views}
                        </span>
                        <span className="inline-flex items-center gap-1">
                            <Download className="h-3 w-3" aria-hidden="true" />
                            {resource.downloads}
                        </span>
                    </div>

                    {resource.description && (
                        <p className="mt-2 break-words text-sm text-text-muted line-clamp-2">{resource.description}</p>
                    )}

                    {tags.length > 0 && (
                        <div className="mt-2.5 flex flex-wrap gap-1.5">
                            {tags.slice(0, 5).map(tag => (
                                <span key={tag} className="badge max-w-full truncate text-xs">{tag}</span>
                            ))}
                            {tags.length > 5 && <span className="self-center text-xs text-text-muted">+{tags.length - 5}</span>}
                        </div>
                    )}
                </div>
            </div>
        </Link>
    )
}

function BrowseContent() {
    const searchParams = useSearchParams()
    const router = useRouter()

    // ---- URL is the single source of truth for filters ----
    const qParam = searchParams.get('q') ?? ''
    const departmentParam = searchParams.get('department') ?? ''
    const branchParam = searchParams.get('branch') ?? ''
    const programParam = searchParams.get('program') ?? ''
    const tagsParam = searchParams.get('tags') ?? ''
    const semesterParam = searchParams.get('semester') ?? ''
    const fileTypeParam = searchParams.get('file_type') ?? ''
    const sortByParam = searchParams.get('sort_by') ?? ''

    const activeTags = useMemo(
        () => tagsParam.split(',').map(t => t.trim()).filter(Boolean),
        [tagsParam],
    )

    // Text searches default to relevance only when no explicit sort exists.
    const effectiveSort = sortByParam || (qParam ? 'relevance' : 'recent')

    const isResultsMode = Boolean(
        qParam || departmentParam || branchParam || programParam || tagsParam || semesterParam || fileTypeParam || sortByParam,
    )

    // ---- Local state ----
    const [query, setQuery] = useState(qParam)
    useEffect(() => { setQuery(qParam) }, [qParam])

    const [facets, setFacets] = useState<Facets | null>(null)
    const [facetsError, setFacetsError] = useState(false)

    const [results, setResults] = useState<Resource[]>([])
    const [total, setTotal] = useState(0)
    const [page, setPage] = useState(1)
    const [resultsLoading, setResultsLoading] = useState(false)
    const [loadingMore, setLoadingMore] = useState(false)
    const [resultsError, setResultsError] = useState('')
    const [resultsNonce, setResultsNonce] = useState(0)

    const [discovery, setDiscovery] = useState<DiscoveryState | null>(null)
    // Admin-configured catalog shelves; null = still loading, [] = not
    // configured (built-in discovery rows render), non-empty = configured
    // rows replace the built-ins.
    const [configured, setConfigured] = useState<ConfiguredRow[] | null>(null)

    const [view, setView] = useState<'grid' | 'list'>('grid')
    const [showMoreFilters, setShowMoreFilters] = useState(false)

    // ---- URL mutation (chips share links via router.replace; the form pushes) ----
    // Note: on first navigation after a dev-server recompile the RSC fetch
    // can take real seconds — QA probes need generous waits (prod is fast).
    const navigateToParams = useCallback((mutate: (sp: URLSearchParams) => void, push = false) => {
        const sp = new URLSearchParams(searchParams.toString())
        mutate(sp)
        const qs = sp.toString()
        const url = qs ? `/browse?${qs}` : '/browse'
        if (push) router.push(url, { scroll: false })
        else router.replace(url, { scroll: false })
    }, [router, searchParams])

    const setParam = useCallback(
        (key: string, value: string | null) =>
            navigateToParams(sp => { if (value) sp.set(key, value); else sp.delete(key) }),
        [navigateToParams],
    )

    const clearAllParams = useCallback(() => {
        router.replace('/browse', { scroll: false })
    }, [router])

    const toggleFilterParam = (key: 'department' | 'branch' | 'program' | 'semester' | 'file_type', value: string) => {
        setParam(key, (searchParams.get(key) ?? '') === value ? null : value)
    }

    const toggleTag = (tag: string) => {
        const lower = tag.toLowerCase()
        const list = tagsParam.split(',').map(t => t.trim()).filter(Boolean)
        const next = list.some(t => t.toLowerCase() === lower)
            ? list.filter(t => t.toLowerCase() !== lower)
            : [...list, tag]
        setParam('tags', next.join(',') || null)
    }

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault()
        navigateToParams(sp => {
            const trimmed = query.trim()
            if (trimmed) sp.set('q', trimmed); else sp.delete('q')
        }, true)
    }

    // ---- Facets for the chip strip (same endpoint the homepage uses) ----
    const loadFacets = useCallback(async () => {
        setFacetsError(false)
        try {
            const res = await api.get('/search/filters')
            const d = res.data ?? {}
            setFacets({
                departments: d.departments ?? [],
                semesters: d.semesters ?? [],
                branches: d.branches ?? [],
                programs: d.programs ?? [],
                file_types: d.file_types ?? [],
                tags: d.tags ?? [],
            })
        } catch {
            setFacetsError(true)
        }
    }, [])
    useEffect(() => { loadFacets() }, [loadFacets])

    // ---- Results mode: fetch page 1 whenever the filter key changes ----
    // Load more reads the freshest base params through this ref, so a click
    // can never page with params from before the last filter change.
    const baseRef = useRef<Record<string, string | undefined>>({})

    useEffect(() => {
        if (!isResultsMode) return
        let cancelled = false
        const searchObj = {
            q: qParam || undefined,
            department: departmentParam || undefined,
            branch: branchParam || undefined,
            program: programParam || undefined,
            tags: activeTags.length ? activeTags.join(',') : undefined,
            semester: semesterParam || undefined,
            file_type: fileTypeParam || undefined,
            sort_by: effectiveSort,
        }
        // Load more reads the freshest base params through this ref.
        baseRef.current = searchObj

        setResultsLoading(true)
        setResultsError('')
        setResults([])
        setTotal(0)
        setPage(1)
        ;(async () => {
            try {
                const response = await apiHelpers.search({ ...searchObj, page: 1, size: PAGE_SIZE })
                if (cancelled) return
                const list = unwrapResults(response.data)
                setResults(list)
                setTotal(typeof response.data?.total === 'number' ? response.data.total : list.length)
            } catch (error) {
                if (cancelled) return
                setResultsError(extractErrorMessage(error, 'Failed to load resources. Please try again.'))
            } finally {
                if (!cancelled) setResultsLoading(false)
            }
        })()
        return () => { cancelled = true }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [qParam, departmentParam, branchParam, programParam, tagsParam, semesterParam, fileTypeParam, effectiveSort, resultsNonce])

    const loadMore = useCallback(async () => {
        if (loadingMore || resultsLoading) return
        setLoadingMore(true)
        setResultsError('')
        try {
            const response = await apiHelpers.search({ ...baseRef.current, page: page + 1, size: PAGE_SIZE })
            setResults(prev => [...prev, ...unwrapResults(response.data)])
            setPage(p => p + 1)
        } catch (error) {
            setResultsError(extractErrorMessage(error, 'Failed to load more resources. Please try again.'))
        } finally {
            setLoadingMore(false)
        }
    }, [page, loadingMore, resultsLoading])

    // ---- Discovery mode: the same shelves the homepage assembles ----
    useEffect(() => {
        if (isResultsMode) return
        let cancelled = false
        setDiscovery(null)
        ;(async () => {
            const settled = await Promise.allSettled([
                api.get('/search/recent', { params: { limit: 24 } }),
                apiHelpers.search({ sort_by: 'views', size: 24, page: 1 }),
                apiHelpers.search({ sort_by: 'top_rated', min_ratings: 3, size: 24, page: 1 }),
            ])
            if (cancelled) return
            setDiscovery({
                recent: settled[0].status === 'fulfilled' ? unwrapResults(settled[0].value.data) : [],
                mostRead: settled[1].status === 'fulfilled' ? unwrapResults(settled[1].value.data) : [],
                topRated: settled[2].status === 'fulfilled' ? unwrapResults(settled[2].value.data) : [],
                branchRows: [],
                tagRows: [],
            })
        })()
        return () => { cancelled = true }
    }, [isResultsMode])

    // Branch + tag shelves arrive after the facet fetch lands.
    useEffect(() => {
        if (isResultsMode || !facets) return
        let cancelled = false
        const branchNames = facets.branches.slice(0, 6)
        ;(async () => {
            const secondary = await Promise.allSettled([
                ...branchNames.map(name => apiHelpers.search({ branch: name, sort_by: 'views', size: 12, page: 1 })),
                ...TAG_SHELF_ROWS.map(tag => apiHelpers.search({ tags: tag.key, sort_by: 'views', size: 12, page: 1 })),
            ])
            if (cancelled) return
            setDiscovery(prev => {
                if (!prev) return prev
                const branchRows = branchNames.map((name, i) => ({
                    name,
                    items: secondary[i].status === 'fulfilled' ? unwrapResults(secondary[i].value.data) : [],
                }))
                const tagOffset = branchNames.length
                const tagRows = TAG_SHELF_ROWS.map((tag, i) => {
                    const r = secondary[tagOffset + i]
                    return {
                        key: tag.key,
                        label: tag.label,
                        items: r.status === 'fulfilled' ? unwrapResults(r.value.data) : [],
                    }
                })
                return { ...prev, branchRows, tagRows }
            })
        })()
        return () => { cancelled = true }
    }, [isResultsMode, facets])

    // ---- Admin-configured catalog rows (discovery mode only) ----
    useEffect(() => {
        if (isResultsMode) { setConfigured(null); return }
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
            if (defs.length === 0) { setConfigured([]); return }
            const settled = await Promise.allSettled(
                defs.map(def => apiHelpers.search(shelfSearchParams(def))),
            )
            if (cancelled) return
            setConfigured(defs.map((def, i) => ({
                title: def.title,
                seeAll: shelfSeeAllHref(def),
                items: settled[i].status === 'fulfilled' ? unwrapResults(settled[i].value.data) : [],
            })))
        })()
        return () => { cancelled = true }
    }, [isResultsMode])

    // ---- Derived UI data ----
    const branchChips = useMemo(
        () => (facets?.branches ?? []).map(b => ({ value: b, label: b })),
        [facets],
    )
    const programChips = useMemo(
        () => (facets?.programs ?? []).map(p => ({ value: p, label: p })),
        [facets],
    )
    const subjectChips = useMemo(
        () => (facets?.departments ?? []).map(d => ({ value: d, label: d })),
        [facets],
    )
    const tagChips = useMemo(
        () => (facets?.tags?.length ? facets.tags : STATIC_TAG_OPTIONS).map(t => ({ value: t, label: `#${t}` })),
        [facets],
    )

    const titleParts = [
        qParam && `“${qParam}”`,
        branchParam,
        programParam,
        departmentParam,
        activeTags.length > 0 && activeTags.map(t => `#${t}`).join(' '),
        semesterParam && `Semester ${semesterParam}`,
        fileTypeParam && fileTypeParam.toUpperCase(),
    ].filter(Boolean) as string[]
    const resultTitle = titleParts.join(' · ') || 'All resources'

    const resultsSubtitle = resultsLoading
        ? 'Loading…'
        : `${total.toLocaleString()} material${total === 1 ? '' : 's'}`

    const hasMore = !resultsLoading && total > results.length && results.length > 0

    const pills: { key: string; label: string; onRemove: () => void }[] = []
    if (qParam) pills.push({ key: 'q', label: `“${qParam}”`, onRemove: () => setParam('q', null) })
    if (branchParam) pills.push({ key: 'branch', label: branchParam, onRemove: () => setParam('branch', null) })
    if (programParam) pills.push({ key: 'program', label: programParam, onRemove: () => setParam('program', null) })
    if (departmentParam) pills.push({ key: 'department', label: departmentParam, onRemove: () => setParam('department', null) })
    if (activeTags.length > 0) {
        pills.push({
            key: 'tags',
            label: activeTags.map(t => `#${t}`).join(', '),
            onRemove: () => setParam('tags', null),
        })
    }
    if (semesterParam) pills.push({ key: 'semester', label: `Semester ${semesterParam}`, onRemove: () => setParam('semester', null) })
    if (fileTypeParam) pills.push({ key: 'file_type', label: fileTypeParam.toUpperCase(), onRemove: () => setParam('file_type', null) })
    if (sortByParam) {
        const sortLabel = SORT_OPTIONS.find(s => s.value === effectiveSort)?.label ?? effectiveSort
        pills.push({ key: 'sort', label: `Sorted: ${sortLabel}`, onRemove: () => setParam('sort_by', null) })
    }

    const toTile = (r: Resource, decorated: boolean): ResourceTileData => ({
        title: r.title,
        slug: r.slug,
        course_code: r.course_code,
        file_extension: r.file_extension,
        file_size: r.file_size,
        views: r.views,
        downloads: r.downloads,
        rating_count: r.rating_count,
        average_rating: r.average_rating,
        ...(decorated
            ? { description: r.description, tags: r.tags, uploader_name: r.uploader_name }
            : {}),
    })

    const hasConfiguredItems = !!configured?.some(row => row.items.length > 0)
    const emptyLibrary = discovery !== null
        && discovery.recent.length === 0
        && discovery.mostRead.length === 0
        && discovery.topRated.length === 0
        && !hasConfiguredItems

    const moreFilterCount = (semesterParam ? 1 : 0) + (fileTypeParam ? 1 : 0)

    return (
        <div className="container-custom py-8">
            {/* Header */}
            <div className="mb-6">
                <h1 className="mb-2 text-3xl font-bold font-display text-text-primary">Browse</h1>
                <p className="text-text-secondary">
                    {isResultsMode
                        ? 'Refine with the filters below or start a new search.'
                        : 'Everything in the library — search, filter, or scroll the shelves.'}
                </p>
            </div>

            {/* Search — shares the old page's URL contract; branch/tags survive a re-search */}
            <form onSubmit={handleSearch} className="mb-6 flex max-w-2xl items-center">
                <div className="relative flex-1">
                    <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-text-muted" aria-hidden="true" />
                    <input
                        type="text"
                        aria-label="Search resources"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search by title, course code, or description…"
                        className="input pl-12"
                    />
                </div>
                <button type="submit" className="btn btn-primary ml-3">Search</button>
            </form>

            {/* Filter strip */}
            <div role="group" aria-label="Filters" className="mb-8 space-y-1">
                <ChipRow
                    label="Sort by"
                    options={SORT_OPTIONS}
                    isOptionActive={v => v === effectiveSort}
                    onSelect={v => setParam('sort_by', v)}
                />
                {facetsError && !facets?.branches.length && (
                    <FetchError
                        message="Filter options could not be loaded."
                        onRetry={loadFacets}
                        className="mt-2"
                    />
                )}
                {facets === null && !facetsError && (
                    <>
                        <div className="mt-1.5 ml-[4.5rem] h-6 w-64 rounded-full skeleton sm:ml-[5.5rem]" aria-hidden="true" />
                        <div className="ml-[4.5rem] h-6 w-48 rounded-full skeleton sm:ml-[5.5rem]" aria-hidden="true" />
                    </>
                )}
                {branchChips.length > 0 && (
                    <ChipRow
                        label="Branch"
                        options={branchChips}
                        isOptionActive={v => v === branchParam}
                        onSelect={v => toggleFilterParam('branch', v)}
                    />
                )}
                {programChips.length > 0 && (
                    <ChipRow
                        label="Program"
                        options={programChips}
                        isOptionActive={v => v === programParam}
                        onSelect={v => toggleFilterParam('program', v)}
                    />
                )}
                {subjectChips.length > 0 && (
                    <ChipRow
                        label="Subject"
                        options={subjectChips}
                        isOptionActive={v => v === departmentParam}
                        onSelect={v => toggleFilterParam('department', v)}
                    />
                )}
                <ChipRow
                    label="Tags"
                    options={tagChips}
                    isOptionActive={v => activeTags.some(t => t.toLowerCase() === v.toLowerCase())}
                    onSelect={toggleTag}
                />
                <div className="pt-1">
                    <button
                        type="button"
                        onClick={() => setShowMoreFilters(v => !v)}
                        aria-expanded={showMoreFilters}
                        className="inline-flex items-center gap-1.5 text-xs font-medium text-text-secondary hover:text-text-primary"
                    >
                        <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
                        More filters{moreFilterCount > 0 ? ` · ${moreFilterCount}` : ''}
                    </button>
                    {showMoreFilters && (
                        <div className="mt-3 grid animate-fade-in grid-cols-1 gap-3 border-t border-border-subtle pt-3 sm:grid-cols-2">
                            <div>
                                <label htmlFor="browse-semester" className="label">Semester</label>
                                <select
                                    id="browse-semester"
                                    value={semesterParam}
                                    onChange={e => setParam('semester', e.target.value || null)}
                                    className="input"
                                >
                                    <option value="">All semesters</option>
                                    {(facets?.semesters ?? []).map(s => (
                                        <option key={s} value={s}>Semester {s}</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label htmlFor="browse-filetype" className="label">File type</label>
                                <select
                                    id="browse-filetype"
                                    value={fileTypeParam}
                                    onChange={e => setParam('file_type', e.target.value || null)}
                                    className="input"
                                >
                                    <option value="">All file types</option>
                                    {(facets?.file_types ?? []).map(f => (
                                        <option key={f} value={f}>{f.toUpperCase()}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Active filter pills */}
            {isResultsMode && pills.length > 0 && (
                <div className="mb-6 flex flex-wrap items-center gap-2">
                    <span className="text-[11px] uppercase tracking-wider text-text-muted">Filters</span>
                    {pills.map(pill => (
                        <span key={pill.key} className="badge badge-primary gap-1.5">
                            {pill.label}
                            <button
                                type="button"
                                onClick={pill.onRemove}
                                aria-label={`Remove filter ${pill.label}`}
                                className="opacity-80 transition-opacity hover:opacity-100"
                            >
                                <X className="h-3 w-3" aria-hidden="true" />
                            </button>
                        </span>
                    ))}
                    <button
                        type="button"
                        onClick={clearAllParams}
                        className="text-xs text-text-secondary underline underline-offset-2 hover:text-text-primary"
                    >
                        Clear all
                    </button>
                </div>
            )}

            {isResultsMode ? (
                /* ---------- Results mode ---------- */
                <section aria-label={`Results for: ${resultTitle}`} className="min-h-[20rem]">
                    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
                        <div className="min-w-0">
                            <h2 className="break-words text-xl font-semibold font-display text-text-primary">
                                {resultTitle}
                            </h2>
                            <p className="mt-0.5 text-sm text-text-secondary">{resultsSubtitle}</p>
                        </div>
                        <div
                            className="flex items-center gap-0.5 rounded-lg border border-border-subtle p-0.5"
                            role="group"
                            aria-label="Result layout"
                        >
                            <button
                                type="button"
                                aria-pressed={view === 'grid'}
                                aria-label="Grid view"
                                onClick={() => setView('grid')}
                                className={`rounded-md p-1.5 transition-colors ${
                                    view === 'grid'
                                        ? 'bg-background-tertiary text-text-primary'
                                        : 'text-text-muted hover:text-text-primary'
                                }`}
                            >
                                <LayoutGrid className="h-4 w-4" aria-hidden="true" />
                            </button>
                            <button
                                type="button"
                                aria-pressed={view === 'list'}
                                aria-label="List view"
                                onClick={() => setView('list')}
                                className={`rounded-md p-1.5 transition-colors ${
                                    view === 'list'
                                        ? 'bg-background-tertiary text-text-primary'
                                        : 'text-text-muted hover:text-text-primary'
                                }`}
                            >
                                <List className="h-4 w-4" aria-hidden="true" />
                            </button>
                        </div>
                    </div>

                    {resultsError && (
                        <FetchError
                            message={resultsError}
                            onRetry={() => setResultsNonce(n => n + 1)}
                            className="mb-4"
                        />
                    )}

                    {resultsLoading ? (
                        view === 'grid' ? <ResultsTileGridSkeleton /> : <ResultsListSkeleton />
                    ) : results.length === 0 ? (
                        <div className="py-16 text-center">
                            <FileText className="mx-auto mb-4 h-16 w-16 text-text-muted" aria-hidden="true" />
                            <h3 className="mb-2 text-xl font-medium text-text-primary">No resources found</h3>
                            <p className="mb-6 text-text-secondary">Try adjusting your search or filters</p>
                            <div className="flex flex-wrap justify-center gap-3">
                                <button type="button" onClick={clearAllParams} className="btn btn-secondary">
                                    Clear filters
                                </button>
                                <Link href="/upload" className="btn btn-primary">Upload First Resource</Link>
                            </div>
                        </div>
                    ) : (
                        <>
                            {view === 'grid' ? (
                                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                                    {results.map(r => (
                                        <ResourceTile key={r.slug} resource={toTile(r, true)} variant="browse" />
                                    ))}
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {results.map(r => <ResultListItem key={r.slug} resource={r} />)}
                                </div>
                            )}
                            {hasMore && (
                                <div className="mt-8 flex justify-center">
                                    <button
                                        type="button"
                                        onClick={loadMore}
                                        disabled={loadingMore}
                                        className="btn btn-secondary inline-flex items-center gap-2 px-6"
                                    >
                                        {loadingMore && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
                                        {loadingMore
                                            ? 'Loading…'
                                            : `Load more (${results.length.toLocaleString()} of ${total.toLocaleString()})`}
                                    </button>
                                </div>
                            )}
                        </>
                    )}
                </section>
            ) : (
                /* ---------- Discovery mode ---------- */
                <section className="space-y-10" aria-label="Catalog">
                    {discovery === null ? (
                        <>
                            <CatalogRow loading title="Recently added" />
                            <CatalogRow loading title="Most read" />
                            <CatalogRow loading title="Top rated" />
                        </>
                    ) : (
                        <>
                            {configured !== null && configured.length > 0 ? (
                                configured.map(row => (
                                    <CatalogRow
                                        key={`sh-${row.title}`}
                                        title={row.title}
                                        seeAllHref={row.seeAll}
                                    >
                                        {row.items.map(r => <ResourceTile key={r.slug} resource={toTile(r, false)} />)}
                                    </CatalogRow>
                                ))
                            ) : (
                                <>
                            <CatalogRow title="Recently added">
                                {discovery.recent.map(r => <ResourceTile key={r.slug} resource={toTile(r, false)} />)}
                            </CatalogRow>

                            <CatalogRow title="Most read" seeAllHref="/browse?sort_by=views">
                                {discovery.mostRead.map(r => <ResourceTile key={r.slug} resource={toTile(r, false)} />)}
                            </CatalogRow>

                            <CatalogRow title="Top rated" seeAllHref="/browse?sort_by=top_rated" minItems={5}>
                                {discovery.topRated.map(r => <ResourceTile key={r.slug} resource={toTile(r, false)} />)}
                            </CatalogRow>

                            {discovery.branchRows.map(row => (
                                <CatalogRow
                                    key={`br-${row.name}`}
                                    title={`Popular in ${row.name}`}
                                    seeAllHref={`/browse?branch=${encodeURIComponent(row.name)}&sort_by=views`}
                                >
                                    {row.items.map(r => <ResourceTile key={r.slug} resource={toTile(r, false)} />)}
                                </CatalogRow>
                            ))}

                            {discovery.tagRows.map(row => (
                                <CatalogRow
                                    key={`tg-${row.key}`}
                                    title={row.label}
                                    seeAllHref={`/browse?tags=${encodeURIComponent(row.key)}&sort_by=views`}
                                >
                                    {row.items.map(r => <ResourceTile key={r.slug} resource={toTile(r, false)} />)}
                                </CatalogRow>
                            ))}
                                </>
                            )}

                            {emptyLibrary && (
                                <div className="card p-8 text-center md:p-12">
                                    <FileText className="mx-auto mb-4 h-14 w-14 text-text-muted" aria-hidden="true" />
                                    <h2 className="mb-2 text-xl font-semibold font-display text-text-primary">
                                        The library is empty so far
                                    </h2>
                                    <p className="mb-6 text-text-secondary">
                                        Be the first to share a resource and it will appear on these shelves.
                                    </p>
                                    <Link href="/upload" className="btn btn-primary">Upload First Resource</Link>
                                </div>
                            )}
                        </>
                    )}
                </section>
            )}
        </div>
    )
}

function extractErrorMessage(error: unknown, fallback: string): string {
    const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
    if (typeof detail === 'string' && detail) return detail
    return fallback
}

export default function BrowsePage() {
    return (
        <Suspense fallback={<div className="container-custom py-20 text-center">Loading...</div>}>
            <BrowseContent />
        </Suspense>
    )
}
