'use client'

/**
 * Client-side PDF preview via pdf.js — one rendering path everywhere.
 *
 * Why this exists: desktop Chrome renders PDFs inside an <iframe> (its
 * built-in viewer), but mobile browsers don't — Android Chrome falls back
 * to a blank shell with just an "Open" button and a blob UUID. pdf.js
 * renders actual pages inside the same modal on every device, so the
 * mobile experience matches desktop instead of dead-ending.
 *
 * The worker is served same-origin from /vendor/pdfjs/ for zero bundler
 * risk (no `import.meta.url` worker resolution, no CDN dependency).
 * The heavy library is dynamically imported — nothing lands in the
 * resource page bundle until a PDF preview is actually opened.
 *
 * Pages render one at a time (cheap memory on large documents) with a
 * prev/next navigator, page-fit width and manual zoom controls.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { ChevronLeft, ChevronRight, FileText, ZoomIn, ZoomOut } from 'lucide-react'
import type { PDFDocumentProxy, PDFPageProxy, RenderTask } from 'pdfjs-dist'

interface PdfPreviewProps {
    blobUrl: string
    fileName: string
    /** Password for encrypted PDFs (the same one the resource preview endpoint already required). */
    password?: string
}

const ZOOM_MIN = 0.6
const ZOOM_MAX = 2.4

export function PdfPreview({ blobUrl, fileName, password }: PdfPreviewProps) {
    const [status, setStatus] = useState<'loading' | 'error' | 'ready'>('loading')
    const [errorMessage, setErrorMessage] = useState('')
    const [document, setDocument] = useState<PDFDocumentProxy | null>(null)
    const [title, setTitle] = useState(fileName)
    const [pageNumber, setPageNumber] = useState(1)
    const [pageCount, setPageCount] = useState(0)
    const [zoom, setZoom] = useState(1)
    const [containerWidth, setContainerWidth] = useState(0)

    const containerRef = useRef<HTMLDivElement>(null)
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const renderTaskRef = useRef<RenderTask | null>(null)

    /* Load the document once, from the blob: URL bytes */
    useEffect(() => {
        let cancelled = false
        ;(async () => {
            try {
                const pdfjs = await import('pdfjs-dist')
                pdfjs.GlobalWorkerOptions.workerSrc = '/vendor/pdfjs/pdf.worker.min.mjs'
                const response = await fetch(blobUrl)
                if (!response.ok) throw new Error(`failed to read file (${response.status})`)
                const bytes = new Uint8Array(await response.arrayBuffer())
                const doc = await pdfjs.getDocument(password ? { data: bytes, password } : { data: bytes }).promise
                if (cancelled) {
                    void doc.destroy()
                    return
                }
                setDocument(doc)
                setPageCount(doc.numPages)
                const props = await doc.getMetadata().catch(() => null)
                const metaTitle = (props?.info as Record<string, unknown> | undefined)?.Title
                if (typeof metaTitle === 'string' && metaTitle.trim()) setTitle(metaTitle.trim())
                setStatus('ready')
            } catch (err) {
                console.error('[PdfPreview] failed to load PDF:', err)
                if (cancelled) return
                const name = err instanceof Error ? err.name : ''
                setErrorMessage(
                    name === 'PasswordException'
                        ? 'This PDF is encrypted and the password didn’t open it. Download it and open it in your PDF app instead.'
                        : 'This PDF could not be rendered on your device.',
                )
                setStatus('error')
            }
        })()
        return () => {
            cancelled = true
        }
    }, [blobUrl, password])

    /* Destroy the pdf.js document on unmount */
    useEffect(() => {
        return () => {
            renderTaskRef.current?.cancel()
            renderTaskRef.current = null
            void document?.destroy()
        }
        // Only when the document object itself changes/unmounts.
    }, [document])

    /* Track the available width for fit-to-width rendering */
    useEffect(() => {
        const el = containerRef.current
        if (!el) return
        const observer = new ResizeObserver(entries => {
            for (const entry of entries) {
                setContainerWidth(entry.contentRect.width)
            }
        })
        observer.observe(el)
        setContainerWidth(el.clientWidth)
        return () => observer.disconnect()
    }, [])

    /* Render the current page (cancelling any in-flight render first) */
    useEffect(() => {
        if (!document || !canvasRef.current || containerWidth === 0) return
        let cancelled = false

        const render = async () => {
            try {
                const page: PDFPageProxy = await document.getPage(pageNumber)
                if (cancelled || !canvasRef.current) return

                const baseViewport = page.getViewport({ scale: 1 })
                // Fit page width into the container minus padding, then scale.
                const fitScale = Math.min((containerWidth - 16) / baseViewport.width, 1.6)
                const dpr = window.devicePixelRatio || 1
                const viewport = page.getViewport({ scale: fitScale * zoom * dpr })

                if (renderTaskRef.current) {
                    try { renderTaskRef.current.cancel() } catch { /* already done */ }
                    renderTaskRef.current = null
                }

                const canvas = canvasRef.current
                const context = canvas.getContext('2d')
                if (!context) throw new Error('canvas 2d context unavailable')

                canvas.width = Math.floor(viewport.width)
                canvas.height = Math.floor(viewport.height)
                canvas.style.width = `${Math.floor(viewport.width / dpr)}px`
                canvas.style.height = `${Math.floor(viewport.height / dpr)}px`

                const task = page.render({ canvasContext: context, viewport })
                renderTaskRef.current = task
                await task.promise
            } catch (err) {
                // Cancelled renders (page flip / unmount) are expected, not errors.
                const name = err instanceof Error ? err.name : ''
                if (!cancelled && name !== 'RenderingCancelledException') {
                    console.warn('[PdfPreview] page render failed:', err)
                }
            } finally {
                if (!cancelled) renderTaskRef.current = null
            }
        }

        void render()
        return () => { cancelled = true }
    }, [document, pageNumber, zoom, containerWidth])

    const goToPage = useCallback(
        (target: number) => setPageNumber(p => Math.min(Math.max(target, 1), Math.max(pageCount, 1) || 1)),
        [pageCount],
    )
    const clampZoom = useCallback(
        (multiplier: number) => setZoom(z => Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, Math.round(z * multiplier * 10) / 10))),
        [],
    )

    if (status === 'loading') {
        return (
            <div className="w-full h-full min-h-[50vh] flex items-center justify-center p-8">
                <div className="text-center">
                    <div className="w-8 h-8 border-2 border-accent-primary border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                    <p className="text-sm text-text-secondary">Rendering PDF…</p>
                </div>
            </div>
        )
    }

    if (status === 'error') {
        return (
            <div className="text-center p-8 bg-background-secondary border border-border-subtle rounded-lg max-w-md">
                <FileText className="w-16 h-16 text-text-muted mx-auto mb-4" aria-hidden="true" />
                <p className="text-lg font-medium text-text-primary mb-2">{fileName}</p>
                <p className="text-sm text-text-secondary mb-6">{errorMessage}</p>
                <p className="text-xs text-text-muted">Use the download button above to view it in your PDF app.</p>
            </div>
        )
    }

    return (
        <div className="flex flex-col w-full h-full min-h-0" data-testid="pdf-preview">
            {/* Controls — sticky to the top of the scroll area */}
            <div className="flex items-center justify-between gap-2 px-2 sm:px-4 py-2 border-b border-border-subtle bg-background-tertiary/60 rounded-t-lg text-xs text-text-secondary shrink-0">
                <div className="flex items-center gap-1 sm:gap-2 min-w-0">
                    <button
                        type="button"
                        onClick={() => goToPage(pageNumber - 1)}
                        disabled={pageNumber <= 1}
                        className="p-1.5 rounded hover:bg-background-secondary disabled:opacity-40 disabled:cursor-default"
                        aria-label="Previous page"
                    >
                        <ChevronLeft className="w-4 h-4" />
                    </button>
                    <span className="tabular-nums whitespace-nowrap" aria-live="polite">
                        {pageNumber} / {pageCount}
                    </span>
                    <button
                        type="button"
                        onClick={() => goToPage(pageNumber + 1)}
                        disabled={pageNumber >= pageCount}
                        className="p-1.5 rounded hover:bg-background-secondary disabled:opacity-40 disabled:cursor-default"
                        aria-label="Next page"
                    >
                        <ChevronRight className="w-4 h-4" />
                    </button>
                    {title !== fileName && (
                        <span className="hidden sm:inline truncate text-text-muted pl-2" title={title}>{title}</span>
                    )}
                </div>
                <div className="flex items-center gap-1 sm:gap-2">
                    <button
                        type="button"
                        onClick={() => clampZoom(1 / 1.25)}
                        className="p-1.5 rounded hover:bg-background-secondary"
                        aria-label="Zoom out"
                    >
                        <ZoomOut className="w-4 h-4" />
                    </button>
                    <span className="tabular-nums w-12 text-center">{Math.round(zoom * 100)}%</span>
                    <button
                        type="button"
                        onClick={() => clampZoom(1.25)}
                        className="p-1.5 rounded hover:bg-background-secondary"
                        aria-label="Zoom in"
                    >
                        <ZoomIn className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Page — vertical scroll, centered */}
            <div ref={containerRef} className="flex-1 overflow-auto p-2 flex flex-col items-center gap-4 bg-background-primary min-h-0">
                <canvas ref={canvasRef} role="img" aria-label={`Page ${pageNumber} of ${fileName}`} className="shadow-lg bg-white max-w-none" />
            </div>
        </div>
    )
}
