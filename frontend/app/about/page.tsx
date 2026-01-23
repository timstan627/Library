export default function AboutPage() {
    return (
        <div className="container-custom py-12">
            <div className="max-w-4xl mx-auto">
                <div className="text-center mb-16">
                    <h1 className="text-4xl font-bold text-text-primary mb-4">About Student Library</h1>
                    <p className="text-xl text-text-secondary max-w-2xl mx-auto">
                        A community-driven platform for sharing knowledge and resources.
                    </p>
                </div>

                <div className="grid md:grid-cols-2 gap-12 mb-16">
                    <div>
                        <h2 className="text-2xl font-bold text-text-primary mb-4">Our Mission</h2>
                        <p className="text-text-secondary leading-relaxed mb-4">
                            We believe that education should be accessible to everyone. The Student Library was built to help students share notes, past papers, and study materials effortlessly.
                        </p>
                        <p className="text-text-secondary leading-relaxed">
                            By fostering a culture of sharing, we can help each other succeed and make learning more collaborative and less stressful.
                        </p>
                    </div>
                    <div>
                        <h2 className="text-2xl font-bold text-text-primary mb-4">How It Works</h2>
                        <ul className="space-y-4">
                            <li className="flex items-start gap-3">
                                <div className="w-8 h-8 bg-accent-primary/10 rounded-full flex items-center justify-center shrink-0 text-accent-primary font-bold">1</div>
                                <div>
                                    <h3 className="font-medium text-text-primary">Create an Account</h3>
                                    <p className="text-sm text-text-secondary">Sign up quickly to start contributing or downloading.</p>
                                </div>
                            </li>
                            <li className="flex items-start gap-3">
                                <div className="w-8 h-8 bg-accent-primary/10 rounded-full flex items-center justify-center shrink-0 text-accent-primary font-bold">2</div>
                                <div>
                                    <h3 className="font-medium text-text-primary">Upload Resources</h3>
                                    <p className="text-sm text-text-secondary">Share your notes, assignments, or useful links.</p>
                                </div>
                            </li>
                            <li className="flex items-start gap-3">
                                <div className="w-8 h-8 bg-accent-primary/10 rounded-full flex items-center justify-center shrink-0 text-accent-primary font-bold">3</div>
                                <div>
                                    <h3 className="font-medium text-text-primary">Learn Together</h3>
                                    <p className="text-sm text-text-secondary">Access thousands of resources organized by course and department.</p>
                                </div>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    )
}
