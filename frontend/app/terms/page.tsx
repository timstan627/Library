export default function TermsPage() {
    return (
        <div className="container-custom py-12 max-w-4xl min-h-screen">
            <h1 className="text-3xl md:text-4xl font-bold text-text-primary mb-2">Terms of Service</h1>
            <p className="text-text-muted mb-8">Last Updated: January 2026</p>

            <div className="space-y-8 text-text-secondary">
                <section>
                    <h2 className="text-xl font-semibold text-text-primary mb-3">1. Acceptance of Terms</h2>
                    <p>
                        By accessing or using the Student Resource Library, you agree to these Terms of Service. If you do not agree, strictly do not use our services.
                    </p>
                </section>

                <section>
                    <h2 className="text-xl font-semibold text-text-primary mb-3">2. User Conduct</h2>
                    <p>
                        You agree NOT to:
                    </p>
                    <ul className="list-disc pl-5 mt-2 space-y-1">
                        <li>Upload malicious, illegal, or infringing content</li>
                        <li>Harass or harm other users</li>
                        <li>Attempt to hack or disrupt our services</li>
                        <li>Use automated bots to scrape data</li>
                    </ul>
                </section>

                <section>
                    <h2 className="text-xl font-semibold text-text-primary mb-3">3. Content Ownership</h2>
                    <p>
                        You retain ownership of content you upload. By uploading, you grant us a non-exclusive license to host and share it within the platform.
                    </p>
                </section>

                <section>
                    <h2 className="text-xl font-semibold text-text-primary mb-3">4. Termination</h2>
                    <p>
                        We reserve the right to suspend or terminate your account at any time for violation of these terms or any other reason.
                    </p>
                </section>

                <section>
                    <h2 className="text-xl font-semibold text-text-primary mb-3">5. Disclaimer</h2>
                    <p>
                        The service is provided "as is" without warranties of any kind. We are not responsible for the accuracy of user-uploaded content.
                    </p>
                </section>
            </div>
        </div>
    )
}
