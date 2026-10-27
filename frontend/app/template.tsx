// Re-mounts on every navigation, giving each page the committed entrance:
// fade up 8 px over 280 ms, exponential ease-out. Reduced motion collapses
// this to an instant opacity fade via the global guard in globals.css.
export default function Template({ children }: { children: React.ReactNode }) {
    return <div className="animate-slide-up">{children}</div>
}
