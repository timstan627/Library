// Collection cover icons.
//
// The API stores the cover as a short string (the "emoji" field, max 10
// chars). New collections store an icon name from this map; collections
// created before the icon picker still hold an emoji literal and fall
// back to the folder icon when rendering.
import {
    Folder, BookOpen, FileText, FlaskConical, BarChart3, GraduationCap,
    Laptop, Microscope, Compass, Palette, Bookmark, Layers,
    type LucideIcon,
} from 'lucide-react'

export const COVER_ICONS: Record<string, LucideIcon> = {
    folder: Folder,
    book: BookOpen,
    file: FileText,
    flask: FlaskConical,
    chart: BarChart3,
    'grad-cap': GraduationCap,
    laptop: Laptop,
    micro: Microscope,
    compass: Compass,
    palette: Palette,
    bookmark: Bookmark,
    layers: Layers,
}

export const DEFAULT_COVER_ICON = 'folder'

export function CollectionCoverIcon({ name, className }: { name: string; className?: string }) {
    const Icon = COVER_ICONS[name] || Folder
    return <Icon className={className} aria-hidden="true" />
}
