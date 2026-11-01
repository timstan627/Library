'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Search, X, FileText, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { apiHelpers } from '@/lib/api'

interface SearchResult {
    id: string
    title: string
    slug: string
    course_code: string
}

export function SearchAutocomplete() {
    const router = useRouter()
    const [query, setQuery] = useState('')
    const [results, setResults] = useState<SearchResult[]>([])
    const [loading, setLoading] = useState(false)
    const [open, setOpen] = useState(false)
    const inputRef = useRef<HTMLInputElement>(null)
    const containerRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
                setOpen(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    useEffect(() => {
        const debounce = setTimeout(async () => {
            if (query.length >= 2) {
                setLoading(true)
                try {
                    const response = await apiHelpers.search({ q: query, size: 5 })
                    setResults(response.data.results)
                    setOpen(true)
                } catch (error) {
                    console.error('Search failed:', error)
                } finally {
                    setLoading(false)
                }
            } else {
                setResults([])
                setOpen(false)
            }
        }, 300)

        return () => clearTimeout(debounce)
    }, [query])

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        if (query.trim()) {
            setOpen(false)
            router.push(`/browse?q=${encodeURIComponent(query.trim())}`)
        }
    }

    return (
        <div ref={containerRef} className="relative w-full max-w-xl">
            <form onSubmit={handleSubmit}>
                <div className="relative">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                    <input
                        ref={inputRef}
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onFocus={() => results.length > 0 && setOpen(true)}
                        placeholder="Search resources..."
                        className="input pl-12 pr-10"
                    />
                    {loading ? (
                        <Loader2 className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted animate-spin" />
                    ) : query && (
                        <button
                            type="button"
                            onClick={() => {
                                setQuery('')
                                setResults([])
                                inputRef.current?.focus()
                            }}
                            className="absolute right-4 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    )}
                </div>
            </form>

            {/* Dropdown */}
            {open && results.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-2 bg-background-secondary border border-border-subtle rounded-md shadow-lg z-50 animate-fade-in">
                    {results.map((result) => (
                        <Link
                            key={result.id}
                            href={`/resources/${result.slug}`}
                            onClick={() => setOpen(false)}
                            className="flex items-center gap-3 px-4 py-3 hover:bg-background-tertiary transition-colors first:rounded-t-md last:rounded-b-md"
                        >
                            <FileText className="w-4 h-4 text-text-muted shrink-0" />
                            <div className="min-w-0">
                                <p className="text-text-primary text-sm truncate">{result.title}</p>
                                {result.course_code && <p className="text-text-muted text-xs">{result.course_code}</p>}
                            </div>
                        </Link>
                    ))}
                    <Link
                        href={`/browse?q=${encodeURIComponent(query)}`}
                        onClick={() => setOpen(false)}
                        className="block px-4 py-2 text-center text-sm text-accent-light hover:bg-background-tertiary border-t border-border-subtle"
                    >
                        View all results
                    </Link>
                </div>
            )}
        </div>
    )
}
