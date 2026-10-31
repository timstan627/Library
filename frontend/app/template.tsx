// Re-mounts on every navigation, giving each page the committed entrance:
// opacity fade over 280 ms, exponential ease-out (see .animate-page-enter in
// globals.css — this wrapper must never animate transform, or it becomes the
// containing block for every position:fixed descendant and breaks modal
// overlays). Reduced motion collapses this to an instant fade via the
// global guard in globals.css.
export default function Template({ children }: { children: React.ReactNode }) {
    return <div className="animate-page-enter">{children}</div>
}
