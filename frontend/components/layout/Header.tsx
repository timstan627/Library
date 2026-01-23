'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { Search, Upload, User, LogIn, Menu, X } from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '@/lib/auth-context'

export function Header() {
    const pathname = usePathname()
    const router = useRouter()
    const { user, isAuthenticated, logout } = useAuth()
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
    const [searchQuery, setSearchQuery] = useState('')

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault()
        if (searchQuery.trim()) {
            router.push(`/browse?q=${encodeURIComponent(searchQuery.trim())}`)
            setSearchQuery('')
        }
    }

    const navItems = [
        { href: '/', label: 'Home' },
        { href: '/browse', label: 'Browse' },
        { href: '/upload', label: 'Upload', requiresAuth: true },
    ]

    return (
        <header className="sticky top-0 z-50 bg-background-secondary/80 backdrop-blur-md border-b border-border-subtle">
            <div className="container-custom">
                <div className="flex items-center justify-between h-16">
                    {/* Logo */}
                    <Link href="/" className="flex items-center gap-2">
                        <div className="w-8 h-8 bg-accent-primary rounded-md flex items-center justify-center">
                            <span className="text-white font-bold text-lg">S</span>
                        </div>
                        <span className="font-semibold text-text-primary hidden sm:inline">
                            Student Library
                        </span>
                    </Link>

                    {/* Desktop Navigation */}
                    <nav className="hidden md:flex items-center gap-6">
                        {navItems.map((item) => {
                            if (item.requiresAuth && !isAuthenticated) return null
                            const isActive = pathname === item.href
                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    className={`text-sm font-medium transition-colors ${isActive
                                        ? 'text-text-primary'
                                        : 'text-text-secondary hover:text-text-primary'
                                        }`}
                                >
                                    {item.label}
                                </Link>
                            )
                        })}
                    </nav>

                    {/* Search & Actions */}
                    <div className="flex items-center gap-4">
                        <form onSubmit={handleSearch} className="hidden sm:flex items-center relative group">
                            <Search className="absolute left-3 w-4 h-4 text-text-secondary z-10" />
                            <input
                                type="text"
                                placeholder="Search..."
                                className="input h-9 py-1 pl-9 pr-4 w-48 focus:w-64 transition-all bg-background-tertiary border-transparent focus:border-accent-primary focus:bg-background-secondary text-sm"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                            />
                        </form>

                        {/* Mobile Search Icon */}
                        <Link
                            href="/browse"
                            className="sm:hidden p-2 text-text-secondary hover:text-text-primary transition-colors"
                            aria-label="Search"
                        >
                            <Search className="w-5 h-5" />
                        </Link>

                        {isAuthenticated ? (
                            <div className="flex items-center gap-3">
                                <Link
                                    href="/upload"
                                    className="hidden sm:flex btn btn-primary text-sm"
                                >
                                    <Upload className="w-4 h-4 mr-2" />
                                    Upload
                                </Link>
                                <Link
                                    href="/profile"
                                    className="flex items-center gap-2 p-2 rounded-md hover:bg-background-tertiary transition-colors"
                                >
                                    <div className="w-8 h-8 bg-background-tertiary rounded-full flex items-center justify-center">
                                        <User className="w-4 h-4 text-text-secondary" />
                                    </div>
                                </Link>
                            </div>
                        ) : (
                            <Link
                                href={`/auth/login?returnUrl=${encodeURIComponent(pathname)}`}
                                className="btn btn-primary text-sm"
                            >
                                <LogIn className="w-4 h-4 mr-2" />
                                Login
                            </Link>
                        )}

                        {/* Mobile menu button */}
                        <button
                            className="md:hidden p-2 text-text-secondary hover:text-text-primary"
                            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                            aria-label="Toggle menu"
                        >
                            {mobileMenuOpen ? (
                                <X className="w-5 h-5" />
                            ) : (
                                <Menu className="w-5 h-5" />
                            )}
                        </button>
                    </div>
                </div>

                {/* Mobile Navigation */}
                {mobileMenuOpen && (
                    <nav className="md:hidden py-4 border-t border-border-subtle animate-fade-in">
                        {navItems.map((item) => {
                            if (item.requiresAuth && !isAuthenticated) return null
                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    className="block py-2 text-text-secondary hover:text-text-primary"
                                    onClick={() => setMobileMenuOpen(false)}
                                >
                                    {item.label}
                                </Link>
                            )
                        })}
                    </nav>
                )}
            </div>
        </header>
    )
}
