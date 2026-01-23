export default function PrivacyPage() {
    return (
        <div className="container-custom py-12 max-w-4xl min-h-screen">
            <h1 className="text-3xl md:text-4xl font-bold text-text-primary mb-2">Privacy Policy</h1>
            <p className="text-text-muted mb-8">Last Updated: January 2026</p>

            <div className="space-y-8 text-text-secondary">
                <section>
                    <h2 className="text-xl font-semibold text-text-primary mb-3">1. Information We Collect</h2>
                    <p>
                        We collect minimal information necessary to provide our services. This includes:
                    </p>
                    <ul className="list-disc pl-5 mt-2 space-y-1">
                        <li>Account information (name, email address)</li>
                        <li>Usage data (resources viewed, downloaded, uploaded)</li>
                        <li>Cookies and technical data for site functionality</li>
                    </ul>
                </section>

                <section>
                    <h2 className="text-xl font-semibold text-text-primary mb-3">2. How We Use Your Information</h2>
                    <p>
                        We use your information to:
                    </p>
                    <ul className="list-disc pl-5 mt-2 space-y-1">
                        <li>Provide and improve the Student Resource Library</li>
                        <li>Process uploads and downloads</li>
                        <li>Ensure security and prevent abuse</li>
                        <li>Communicate important updates</li>
                    </ul>
                </section>

                <section>
                    <h2 className="text-xl font-semibold text-text-primary mb-3">3. Data Sharing</h2>
                    <p>
                        We do not sell your personal data. We may share data with:
                    </p>
                    <ul className="list-disc pl-5 mt-2 space-y-1">
                        <li>Service providers (e.g., hosting, database services)</li>
                        <li>Legal authorities when required by law</li>
                    </ul>
                </section>

                <section>
                    <h2 className="text-xl font-semibold text-text-primary mb-3">4. Security</h2>
                    <p>
                        We implement reasonable security measures to protect your data. However, no internet transmission is completely secure, and we cannot guarantee absolute security.
                    </p>
                </section>

                <section>
                    <h2 className="text-xl font-semibold text-text-primary mb-3">5. Your Rights</h2>
                    <p>
                        You have the right to access, correct, or delete your personal data. Contact us at support@studentlibrary.com for assistance.
                    </p>
                </section>
            </div>
        </div>
    )
}
