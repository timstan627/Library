'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const sections = [
    { href: '/admin', label: 'Dashboard' },
    { href: '/admin/moderation', label: 'Moderation' },
    { href: '/admin/resources', label: 'Resources' },
    { href: '/admin/users', label: 'Users' },
    { href: '/admin/departments', label: 'Departments' },
    { href: '/admin/courses', label: 'Courses' },
    { href: '/admin/reports', label: 'Reports' },
    { href: '/admin/audit', label: 'Audit' },
]

export default function AdminLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname()

    return (
        <div>
            <nav aria-label="Admin sections" className="border-b border-border-subtle bg-background-secondary">
                <div className="container-custom">
                    <div className="flex gap-1 overflow-x-auto py-2">
                        {sections.map((section) => {
                            const active = section.href === '/admin'
                                ? pathname === '/admin'
                                : pathname.startsWith(section.href)
                            return (
                                <Link
                                    key={section.href}
                                    href={section.href}
                                    aria-current={active ? 'page' : undefined}
                                    className={`px-3 py-1.5 rounded-md text-sm font-medium whitespace-nowrap transition-[background-color,color] ${active
                                        ? 'bg-accent-primary text-accent-ink'
                                        : 'text-text-secondary hover:text-text-primary hover:bg-background-tertiary'
                                        }`}
                                >
                                    {section.label}
                                </Link>
                            )
                        })}
                    </div>
                </div>
            </nav>
            {children}
        </div>
    )
}
