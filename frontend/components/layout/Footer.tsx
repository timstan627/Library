import Link from 'next/link'

export function Footer() {
    const currentYear = new Date().getFullYear()

    return (
        <footer className="bg-background-secondary border-t border-border-subtle">
            <div className="container-custom py-8">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
                    {/* Brand */}
                    <div className="md:col-span-2">
                        <div className="flex items-center gap-2 mb-4">
                            <div className="w-8 h-8 bg-accent-primary rounded-md flex items-center justify-center">
                                <span className="text-white font-bold text-lg">S</span>
                            </div>
                            <span className="font-semibold text-text-primary">
                                Student Library
                            </span>
                        </div>
                        <p className="text-text-secondary text-sm max-w-md">
                            A shared library where students trade notes, exams, and study materials with their peers. Free to use, unlimited storage.
                        </p>
                    </div>

                    {/* Quick Links */}
                    <div>
                        <h4 className="text-text-primary font-medium mb-4">Quick Links</h4>
                        <ul className="space-y-2">
                            <li>
                                <Link href="/browse" className="text-text-secondary text-sm hover:text-text-primary">
                                    Browse Resources
                                </Link>
                            </li>
                            <li>
                                <Link href="/upload" className="text-text-secondary text-sm hover:text-text-primary">
                                    Upload
                                </Link>
                            </li>
                            <li>
                                <Link href="/about" className="text-text-secondary text-sm hover:text-text-primary">
                                    About
                                </Link>
                            </li>
                        </ul>
                    </div>

                    {/* Legal */}
                    <div>
                        <h4 className="text-text-primary font-medium mb-4">Legal</h4>
                        <ul className="space-y-2">
                            <li>
                                <Link href="/privacy" className="text-text-secondary text-sm hover:text-text-primary">
                                    Privacy Policy
                                </Link>
                            </li>
                            <li>
                                <Link href="/terms" className="text-text-secondary text-sm hover:text-text-primary">
                                    Terms of Service
                                </Link>
                            </li>
                            <li>
                                <Link href="/dmca" className="text-text-secondary text-sm hover:text-text-primary">
                                    DMCA
                                </Link>
                            </li>
                        </ul>
                    </div>
                </div>

                {/* Bottom bar */}
                <div className="flex flex-col sm:flex-row items-center justify-center sm:justify-between mt-8 pt-8 border-t border-border-subtle gap-3">
                    <p className="text-text-muted text-sm text-center sm:text-left">
                        © {currentYear} Student Library. Built by students, for students.
                    </p>
                </div>
            </div>
        </footer>
    )
}
