'use client'

/**
 * Client-side file preview renderers.
 *
 * Every heavy library (mammoth, SheetJS, @aiden0z/pptx-renderer, fflate,
 * marked) is dynamically imported inside its component so it lands in a
 * separate lazy-loaded chunk — the resource page bundle stays unchanged
 * until a renderer is actually used.
 *
 * Renderers receive a blob: URL of the file bytes (already fetched with the
 * user's auth token by the resource page via /resources/{id}/preview).
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import type { WorkBook } from 'xlsx'
// Type-only: erased at runtime, so the library stays behind the dynamic
// import inside PptxPreview.
import type { PptxViewer } from '@aiden0z/pptx-renderer'

/* ─────────────────────────── shared shell ─────────────────────────── */

function RenderState({ children }: { children: React.ReactNode }) {
    return (
        <div className="w-full flex items-center justify-center p-8">
            {children}
        </div>
    )
}

function LoadingNote({ label }: { label: string }) {
    return (
        <RenderState>
            <div className="text-center">
                <div className="w-8 h-8 border-2 border-accent-primary border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                <p className="text-sm text-text-secondary">{label}</p>
            </div>
        </RenderState>
    )
}

function ErrorNote({ message, retry }: { message: string; retry: () => void }) {
    return (
        <RenderState>
            <div className="text-center max-w-sm">
                <p className="text-sm text-error mb-4">{message}</p>
                <button onClick={retry} className="btn btn-outline px-4 py-2 text-sm">
                    Try again
                </button>
            </div>
        </RenderState>
    )
}

/** Fetch the blob: URL back as bytes for the JS renderers. */
async function fetchBytes(blobUrl: string): Promise<ArrayBuffer> {
    const res = await fetch(blobUrl)
    if (!res.ok) throw new Error(`failed to read file (${res.status})`)
    return res.arrayBuffer()
}

/* ─────────────────────────── DOCX ─────────────────────────── */

export function DocxPreview({ blobUrl }: { blobUrl: string }) {
    const [status, setStatus] = useState<'loading' | 'error' | 'ready'>('loading')
    const [errorMessage, setErrorMessage] = useState('')
    const [html, setHtml] = useState('')
    const [warningCount, setWarningCount] = useState(0)

    const run = useCallback(() => {
        let cancelled = false
        setStatus('loading')
        ;(async () => {
            try {
                const [{ default: mammoth }, { default: DOMPurify }] = await Promise.all([
                    import('mammoth'),
                    import('dompurify'),
                ])
                const bytes = await fetchBytes(blobUrl)
                const result = await mammoth.convertToHtml({ arrayBuffer: bytes })
                if (cancelled) return
                setHtml(DOMPurify.sanitize(result.value, { USE_PROFILES: { html: true } }))
                setWarningCount(result.messages.length)
                setStatus('ready')
            } catch (e: any) {
                if (!cancelled) {
                    setErrorMessage(`Could not render document: ${e?.message || e}`)
                    setStatus('error')
                }
            }
        })()
        return () => { cancelled = true }
    }, [blobUrl])

    useEffect(() => run(), [run])

    if (status === 'loading') return <LoadingNote label="Rendering document…" />
    if (status === 'error') return <ErrorNote message={errorMessage} retry={run} />

    return (
        <div className="w-full max-w-4xl h-fit bg-white dark:bg-gray-900 rounded-lg shadow-lg border border-gray-200 dark:border-gray-800">
            {warningCount > 0 && (
                <p className="px-4 py-1.5 text-xs text-text-muted border-b border-gray-100 dark:border-gray-800">
                    {warningCount} unsupported formatting element{warningCount === 1 ? '' : 's'} skipped
                </p>
            )}
            <div
                className="docx-body p-6 sm:p-10 text-gray-900 dark:text-gray-100 overflow-auto
                    [&_h1]:text-2xl [&_h1]:font-bold [&_h1]:mb-4 [&_h1]:mt-6
                    [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:mb-3 [&_h2]:mt-5
                    [&_h3]:text-lg [&_h3]:font-semibold [&_h3]:mb-2 [&_h3]:mt-4
                    [&_p]:mb-3 [&_p]:leading-relaxed
                    [&_ul]:list-disc [&_ul]:pl-6 [&_ul]:mb-3
                    [&_ol]:list-decimal [&_ol]:pl-6 [&_ol]:mb-3
                    [&_li]:mb-1
                    [&_table]:border-collapse [&_table]:w-full [&_table]:my-4 [&_table]:text-sm
                    [&_td]:border [&_td]:border-gray-300 dark:[&_td]:border-gray-700 [&_td]:px-2.5 [&_td]:py-1.5
                    [&_th]:border [&_th]:border-gray-300 dark:[&_th]:border-gray-700 [&_th]:px-2.5 [&_th]:py-1.5 [&_th]:bg-gray-100 dark:[&_th]:bg-gray-800 [&_th]:font-semibold
                    [&_img]:max-w-full [&_img]:h-auto [&_img]:my-3 [&_img]:rounded
                    [&_a]:text-accent-primary [&_a]:underline
                    [&_strong]:font-semibold [&_em]:italic
                    [&_blockquote]:border-l-2 [&_blockquote]:border-gray-300 dark:[&_blockquote]:border-gray-700 [&_blockquote]:pl-4 [&_blockquote]:my-3 [&_blockquote]:text-gray-600 dark:[&_blockquote]:text-gray-400"
                dangerouslySetInnerHTML={{ __html: html }}
            />
        </div>
    )
}

/* ─────────────────────────── XLSX ─────────────────────────── */

const XLSX_MAX_ROWS = 500

export function XlsxPreview({ blobUrl }: { blobUrl: string }) {
    const [status, setStatus] = useState<'loading' | 'error' | 'ready'>('loading')
    const [errorMessage, setErrorMessage] = useState('')
    const [sheets, setSheets] = useState<string[]>([])
    const [current, setCurrent] = useState<string | null>(null)
    const [tableHtml, setTableHtml] = useState('')
    const [truncated, setTruncated] = useState(false)
    const workbookRef = useRef<WorkBook | null>(null)

    // Parse once; sheet switching re-uses the parsed workbook.
    const load = useCallback(() => {
        let cancelled = false
        setStatus('loading')
        ;(async () => {
            try {
                const XLSX = await import('xlsx')
                const bytes = await fetchBytes(blobUrl)
                const workbook = XLSX.read(bytes, { type: 'array' })
                if (cancelled) return
                workbookRef.current = workbook
                const names = workbook.SheetNames
                setSheets(names)
                setCurrent(names[0] ?? null)
                if (!names.length) setStatus('ready')
            } catch (e: any) {
                if (!cancelled) {
                    setErrorMessage(`Could not open spreadsheet: ${e?.message || e}`)
                    setStatus('error')
                }
            }
        })()
        return () => { cancelled = true }
    }, [blobUrl])

    useEffect(() => load(), [load])

    // Render the selected sheet's table.
    useEffect(() => {
        const workbook = workbookRef.current
        if (!workbook || !current) return
        let cancelled = false
        ;(async () => {
            const [XLSX, { default: DOMPurify }] = await Promise.all([
                import('xlsx'),
                import('dompurify'),
            ])
            const ws = workbook.Sheets[current]
            if (!ws) return
            let trunc = false
            const ref = ws['!ref']
            if (ref) {
                const range = XLSX.utils.decode_range(ref)
                if (range.e.r - range.s.r + 1 > XLSX_MAX_ROWS) {
                    range.e.r = range.s.r + XLSX_MAX_ROWS - 1
                    ws['!ref'] = XLSX.utils.encode_range(range)
                    trunc = true
                }
            }
            const html = DOMPurify.sanitize(XLSX.utils.sheet_to_html(ws, { header: '', footer: '' }))
            if (!cancelled) {
                setTableHtml(html)
                setTruncated(trunc)
                setStatus('ready')
            }
        })()
        return () => { cancelled = true }
    }, [current])

    if (status === 'loading') return <LoadingNote label="Opening spreadsheet…" />
    if (status === 'error') return <ErrorNote message={errorMessage} retry={load} />

    return (
        <div className="w-full max-w-5xl h-fit bg-white dark:bg-gray-900 rounded-lg shadow-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
            {/* Sheet tabs */}
            <div className="flex items-center gap-1 px-2 pt-2 border-b border-gray-200 dark:border-gray-800 overflow-x-auto">
                {sheets.map(name => (
                    <button
                        key={name}
                        onClick={() => setCurrent(name)}
                        className={`px-3 py-1.5 text-xs whitespace-nowrap rounded-t-md transition-colors ${
                            name === current
                                ? 'bg-accent-primary/10 text-accent-primary font-semibold border-b-2 border-accent-primary'
                                : 'text-text-secondary hover:bg-background-tertiary'
                        }`}
                    >
                        {name}
                    </button>
                ))}
            </div>
            {truncated && (
                <p className="px-4 py-1.5 bg-warning/10 text-warning-light text-xs">
                    Showing first {XLSX_MAX_ROWS.toLocaleString()} rows — download for the full sheet
                </p>
            )}
            <div className="overflow-auto max-h-[70vh]">
                <div
                    className="xlsx-table [&_table]:border-collapse [&_table]:text-xs sm:[&_table]:text-sm [&_table]:min-w-full
                        [&_td]:border [&_td]:border-gray-200 dark:[&_td]:border-gray-800 [&_td]:px-2.5 [&_td]:py-1 [&_td]:whitespace-nowrap [&_td]:text-gray-900 dark:[&_td]:text-gray-100
                        [&_tr:first-child_td]:bg-gray-100 dark:[&_tr:first-child_td]:bg-gray-800 [&_tr:first-child_td]:font-semibold"
                    dangerouslySetInnerHTML={{ __html: tableHtml }}
                />
            </div>
        </div>
    )
}

/* ─────────────────────────── PPTX ─────────────────────────── */

export function PptxPreview({ blobUrl }: { blobUrl: string }) {
    const containerRef = useRef<HTMLDivElement>(null)
    const viewerRef = useRef<PptxViewer | null>(null)
    const [nonce, setNonce] = useState(0)
    const [status, setStatus] = useState<'loading' | 'error' | 'done'>('loading')
    const [errorMessage, setErrorMessage] = useState('')
    const [slideCount, setSlideCount] = useState(0)
    const [slideErrors, setSlideErrors] = useState(0)
    // Mirror of `status` for the unhandledrejection guard below (kept in
    // sync via effect so the listener doesn't need re-subscribing).
    const statusRef = useRef<'loading' | 'error' | 'done'>('loading')

    useEffect(() => { statusRef.current = status }, [status])

    useEffect(() => {
        const container = containerRef.current
        if (!container) return
        const abort = new AbortController()
        let disposed = false
        let cleanupFallback: (() => void) | undefined
        setStatus('loading')
        setErrorMessage('')
        setSlideErrors(0)
        setSlideCount(0)

        // Belt-and-braces: the previous renderer crashed via a detached
        // promise chain, escaping every try/catch. This renderer resolves
        // everything through catchable promises and isolates per-node
        // errors, but a crash in an internal detached chain would still
        // surface as an unhandled rejection (full-screen error overlay in
        // dev). While this preview is mounted, suppress rejections that
        // plausibly belong to the renderer; anything else passes through.
        const onUnhandledRejection = (event: PromiseRejectionEvent) => {
            const reason = event.reason
            const stack = reason instanceof Error ? reason.stack || '' : String(reason ?? '')
            if (statusRef.current !== 'done' || /pptx/i.test(stack)) {
                event.preventDefault()
                console.warn('[PptxPreview] suppressed renderer rejection:', reason)
            }
        }
        window.addEventListener('unhandledrejection', onUnhandledRejection)

        ;(async () => {
            try {
                const [{ PptxViewer, RECOMMENDED_ZIP_LIMITS }, bytes] = await Promise.all([
                    import('@aiden0z/pptx-renderer'),
                    fetchBytes(blobUrl),
                ])
                if (disposed || !container) return

                // open() resolves after the render chain is queued, not after
                // the first paint — flipping status there shows the spinner
                // alongside a half-rendered list. The renderer emits
                // `rendercomplete` when the initial render settles, so wait
                // for it (pre-wired via the option so an event fired during
                // open() can't be missed), with a fallback timer so a missed
                // event can never leave the spinner up forever.
                let settled = false
                const viewer = await PptxViewer.open(bytes, container, {
                    renderMode: 'list',
                    zipLimits: RECOMMENDED_ZIP_LIMITS,
                    // The container itself is the scroller (overflow-y-auto
                    // below): slide wrappers are normal-flow children, and
                    // windowed mounting observes intersections against this
                    // element. Without it the renderer roots its observers at
                    // the browser viewport and the modal can cut off the last
                    // slide's scroll extent.
                    scrollContainer: container,
                    // Decks reach tens of MB: defer slide-node parsing and
                    // media decoding until a slide actually scrolls into
                    // view, and keep off-screen slides out of the DOM.
                    lazySlides: true,
                    lazyMedia: true,
                    signal: abort.signal,
                    listOptions: {
                        windowed: true,
                        initialSlides: 4,
                        batchSize: 8,
                        overscanViewport: 1.5,
                    },
                    // Decks are user-uploaded: block external image/media
                    // relationships so previewing never contacts third-party
                    // servers. Embedded media is unaffected.
                    externalMedia: 'block',
                    // Per-node error isolation: a failed shape renders as a
                    // placeholder instead of killing the slide.
                    onSlideError: () => setSlideErrors(n => n + 1),
                    onRenderComplete: () => { settled = true },
                })

                if (disposed) { viewer.destroy(); return }
                viewerRef.current = viewer
                setSlideCount(viewer.slideCount)

                const finish = () => { if (!disposed) setStatus('done') }
                if (settled) {
                    finish()
                } else {
                    const fallback = setTimeout(finish, 2500)
                    viewer.on('rendercomplete', () => {
                        clearTimeout(fallback)
                        finish()
                    })
                    cleanupFallback = () => clearTimeout(fallback)
                }
            } catch (e: any) {
                if (disposed || abort.signal.aborted) return
                setErrorMessage(`Could not render presentation: ${e?.message || e}`)
                setStatus('error')
            }
        })()

        return () => {
            disposed = true
            abort.abort()
            cleanupFallback?.()
            window.removeEventListener('unhandledrejection', onUnhandledRejection)
            // Revokes blob URLs, disconnects observers, clears DOM.
            viewerRef.current?.destroy()
            viewerRef.current = null
            if (container) container.innerHTML = ''
        }
    }, [blobUrl, nonce])

    return (
        <div className="w-full h-full flex flex-col">
            {status === 'loading' && <LoadingNote label="Rendering slides…" />}
            {status === 'error' && (
                <ErrorNote message={errorMessage} retry={() => setNonce(n => n + 1)} />
            )}
            {status === 'done' && (slideCount > 0 || slideErrors > 0) && (
                <div className="shrink-0 flex items-center gap-3 px-3 py-1.5 text-xs text-text-secondary">
                    {slideCount > 0 && <span className="tabular-nums">{slideCount} slides</span>}
                    {slideErrors > 0 && (
                        <span className="text-warning-light">
                            {slideErrors} slide{slideErrors === 1 ? '' : 's'} had unsupported elements
                        </span>
                    )}
                </div>
            )}
            <div
                ref={containerRef}
                data-pptx-scroll
                className={`flex-1 min-h-0 w-full overflow-y-auto overscroll-contain ${status === 'error' ? 'hidden' : ''}`}
            />
        </div>
    )
}

/* ─────────────────────────── ZIP ─────────────────────────── */

const ZIP_MAX_ENTRIES = 500

export function ZipPreview({ blobUrl }: { blobUrl: string }) {
    const [status, setStatus] = useState<'loading' | 'error' | 'ready'>('loading')
    const [errorMessage, setErrorMessage] = useState('')
    const [entries, setEntries] = useState<{ name: string; size: number }[]>([])
    const [hidden, setHidden] = useState(0)
    const [totalSize, setTotalSize] = useState(0)

    const run = useCallback(() => {
        let cancelled = false
        setStatus('loading')
        ;(async () => {
            try {
                const { unzipSync } = await import('fflate')
                const bytes = await fetchBytes(blobUrl)
                // unzipSync decodes the whole archive in one pass — fine at
                // the 50MB upload cap; listing is an explicit user action.
                const files = unzipSync(new Uint8Array(bytes))
                const all = Object.keys(files)
                    .filter(name => !name.endsWith('/'))
                    .map(name => ({ name, size: files[name].length }))
                    .sort((a, b) => a.name.localeCompare(b.name))
                if (cancelled) return
                setEntries(all.slice(0, ZIP_MAX_ENTRIES))
                setHidden(Math.max(0, all.length - ZIP_MAX_ENTRIES))
                setTotalSize(all.reduce((sum, e) => sum + e.size, 0))
                setStatus('ready')
            } catch (e: any) {
                if (!cancelled) {
                    setErrorMessage(`Could not open archive: ${e?.message || e}`)
                    setStatus('error')
                }
            }
        })()
        return () => { cancelled = true }
    }, [blobUrl])

    useEffect(() => run(), [run])

    if (status === 'loading') return <LoadingNote label="Opening archive…" />
    if (status === 'error') return <ErrorNote message={errorMessage} retry={run} />

    return (
        <div className="w-full max-w-3xl h-fit bg-white dark:bg-gray-900 rounded-lg shadow-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-800 text-xs text-text-secondary">
                <span>{entries.length + hidden} files · uncompressed total {formatSize(totalSize)}</span>
                {hidden > 0 && <span className="text-warning-light">+{hidden} more not shown</span>}
            </div>
            <div className="overflow-auto max-h-[60vh]">
                <ul className="divide-y divide-gray-100 dark:divide-gray-800">
                    {entries.map(entry => (
                        <li key={entry.name} className="flex items-center gap-3 px-4 py-1.5 text-sm">
                            <span className="truncate flex-1 font-mono text-xs sm:text-sm text-gray-900 dark:text-gray-100">
                                {entry.name}
                            </span>
                            <span className="tabular-nums text-xs text-text-secondary shrink-0">
                                {formatSize(entry.size)}
                            </span>
                        </li>
                    ))}
                </ul>
            </div>
        </div>
    )
}

function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/* ─────────────────────────── Markdown ─────────────────────────── */

export function MarkdownPreview({ content }: { content: string }) {
    const [status, setStatus] = useState<'loading' | 'error' | 'ready'>('loading')
    const [errorMessage, setErrorMessage] = useState('')
    const [html, setHtml] = useState('')

    const run = useCallback(() => {
        let cancelled = false
        setStatus('loading')
        ;(async () => {
            try {
                const [{ marked }, { default: DOMPurify }] = await Promise.all([
                    import('marked'),
                    import('dompurify'),
                ])
                const raw = await marked.parse(content, { async: true })
                if (cancelled) return
                setHtml(DOMPurify.sanitize(raw, { USE_PROFILES: { html: true } }))
                setStatus('ready')
            } catch (e: any) {
                if (!cancelled) {
                    setErrorMessage(`Could not render markdown: ${e?.message || e}`)
                    setStatus('error')
                }
            }
        })()
        return () => { cancelled = true }
    }, [content])

    useEffect(() => run(), [run])

    if (status === 'loading') return <LoadingNote label="Rendering markdown…" />
    if (status === 'error') return <ErrorNote message={errorMessage} retry={run} />

    return (
        <div className="w-full max-w-4xl h-fit bg-white dark:bg-gray-900 rounded-lg shadow-lg border border-gray-200 dark:border-gray-800">
            <div
                className="md-body p-6 sm:p-10 text-gray-900 dark:text-gray-100 overflow-auto
                    [&_h1]:text-2xl [&_h1]:font-bold [&_h1]:mb-4 [&_h1]:mt-6 [&_h1]:pb-2 [&_h1]:border-b [&_h1]:border-gray-200 dark:[&_h1]:border-gray-800
                    [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:mb-3 [&_h2]:mt-5 [&_h2]:pb-1.5 [&_h2]:border-b [&_h2]:border-gray-100 dark:[&_h2]:border-gray-800
                    [&_h3]:text-lg [&_h3]:font-semibold [&_h3]:mb-2 [&_h3]:mt-4
                    [&_p]:mb-3 [&_p]:leading-relaxed
                    [&_ul]:list-disc [&_ul]:pl-6 [&_ul]:mb-3
                    [&_ol]:list-decimal [&_ol]:pl-6 [&_ol]:mb-3
                    [&_li]:mb-1
                    [&_code]:bg-gray-100 dark:[&_code]:bg-gray-800 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-sm [&_code]:font-mono
                    [&_pre]:bg-gray-950 [&_pre]:text-gray-100 [&_pre]:p-4 [&_pre]:rounded-lg [&_pre]:overflow-x-auto [&_pre]:my-4 [&_pre]:text-sm [&_pre_code]:bg-transparent [&_pre_code]:p-0
                    [&_table]:border-collapse [&_table]:w-full [&_table]:my-4 [&_table]:text-sm
                    [&_td]:border [&_td]:border-gray-300 dark:[&_td]:border-gray-700 [&_td]:px-2.5 [&_td]:py-1.5
                    [&_th]:border [&_th]:border-gray-300 dark:[&_th]:border-gray-700 [&_th]:px-2.5 [&_th]:py-1.5 [&_th]:bg-gray-100 dark:[&_th]:bg-gray-800
                    [&_img]:max-w-full [&_img]:rounded
                    [&_a]:text-accent-primary [&_a]:underline
                    [&_blockquote]:border-l-2 [&_blockquote]:border-gray-300 dark:[&_blockquote]:border-gray-700 [&_blockquote]:pl-4 [&_blockquote]:my-3 [&_blockquote]:text-gray-600 dark:[&_blockquote]:text-gray-400
                    [&_hr]:my-6 [&_hr]:border-gray-200 dark:[&_hr]:border-gray-800"
                dangerouslySetInnerHTML={{ __html: html }}
            />
        </div>
    )
}
