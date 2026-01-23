export default function DMCAPage() {
    return (
        <div className="container-custom py-12 max-w-4xl min-h-screen">
            <h1 className="text-3xl md:text-4xl font-bold text-text-primary mb-2">DMCA Policy</h1>
            <p className="text-text-muted mb-8">Digital Millennium Copyright Act Notice</p>

            <div className="space-y-8 text-text-secondary">
                <section>
                    <h2 className="text-xl font-semibold text-text-primary mb-3">Copyright Infringement</h2>
                    <p>
                        We respect the intellectual property rights of others. It is our policy to respond to any claim that Content posted on the Service infringes on the copyright or other intellectual property rights of any person or entity.
                    </p>
                </section>

                <section>
                    <h2 className="text-xl font-semibold text-text-primary mb-3">Reporting a Violation</h2>
                    <p>
                        If you are a copyright owner, or authorized on behalf of one, and you believe that the copyrighted work has been copied in a way that constitutes copyright infringement, please submit your claim via email to:
                    </p>
                    <p className="mt-2 font-medium text-text-primary">dmca@studentlibrary.com</p>
                    <p className="mt-2">
                        You must include in your email a detailed description of the alleged infringement as detailed under the DMCA.
                    </p>
                </section>

                <section>
                    <h2 className="text-xl font-semibold text-text-primary mb-3">DMCA Notice Requirements</h2>
                    <ul className="list-disc pl-5 mt-2 space-y-1">
                        <li>An electronic or physical signature of the person authorized to act on behalf of the owner of the copyright's interest.</li>
                        <li>A description of the copyrighted work that you claim has been infringed, including the URL (i.e., web page address) of the location where the copyrighted work exists or a copy of the copyrighted work.</li>
                        <li>Identification of the URL or other specific location on the Service where the material that you claim is infringing is located.</li>
                        <li>Your address, telephone number, and email address.</li>
                        <li>A statement by you that you have a good faith belief that the disputed use is not authorized by the copyright owner, its agent, or the law.</li>
                    </ul>
                </section>

                <div className="bg-background-secondary p-4 rounded-lg border border-border-subtle mt-8">
                    <p className="text-sm">
                        Upon receipt of a notification, we will take whatever action, in our sole discretion, we deem appropriate, including removal of the challenged content from the Service.
                    </p>
                </div>
            </div>
        </div>
    )
}
