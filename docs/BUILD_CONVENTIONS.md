# CloudGuard — build conventions

The contract every part of this codebase is written against. Read this before
touching a file. If something here disagrees with what you were about to do,
this document wins.

---

## 1. What we are building

An enterprise cloud-security scanner console. **Frontend only.** No AWS SDK, no
Boto3, no FastAPI, no database, no auth. All data comes from `src/data/*` through
the mock client in `src/api/client.ts`.

The product has two distinct surfaces:

| Surface | Route | Character |
|---|---|---|
| Marketing site | `/` | Cinematic, spacious, 3D-led. 16–18px body. Sells the product. |
| Product console | `/app/*` | Dense, calm, information-first. 13–14px body. Used for hours daily. |

These must not look like the same page with different content. The console is
quiet so the data is loud; the marketing page can be dramatic.

---

## 2. Visual language

### Depth
Depth comes from **surface steps + hairlines + a top rim highlight**, in that
order. Drop shadows are a last resort and only for genuinely floating layers
(popover, modal, drawer, toast).

```
canvas          the page plane, deepest
surface-1       panels sitting on the page
surface-2       raised elements inside a panel (table header, inset blocks)
surface-3       hover / input / active fill
```

Use `.panel` for the standard container. It applies `surface-1`, a hairline, and
`shadow-rim`. **Do not** add a shadow to a panel.

### Radii
Tight and technical: `rounded` (6px) for controls, `rounded-lg` (8px) for panels,
`rounded-sm` (4px) for chips and small marks. Nothing pill-shaped except status
dots and avatars. No `rounded-2xl` on cards.

### Not everything is a card
This is the single biggest tell of a generated dashboard. Vary the containers:

- Full-bleed sections divided by `.rule-fade` or a plain `border-t border-line`
- Bare content on the canvas with only a heading for structure
- Tables that sit directly on the canvas, not inside a rounded box
- Inset blocks (`surface-inset`) for code, config and diff-like content
- Split panels with an internal vertical hairline

A page made of six equal rounded boxes in a grid is wrong. Rework it.

### Colour discipline
- Accent (`accent-9`) is for **interactive** things and the single most important
  data mark. It is not decoration.
- Severity colours are a **reserved status palette**. Never use them for a chart
  series that isn't about severity. Never render one without a text label beside
  it — High (amber) and Medium (yellow) are the closest pair in the ramp, and the
  label is what actually separates them.
- No gradient larger than a subtle wash. No glowing borders. No neon. No purple.
- Text always wears `content-*` tokens. **Never colour body text with a series
  colour.** A coloured dot beside the text carries identity instead.

### Typography
Inter Variable for everything; JetBrains Mono for technical values only —
resource ids, ARNs, regions, ports, CIDRs, config values, CLI. Sizes come from
the scale in `tailwind.config.js` (`text-micro` … `text-display-lg`). Never write
an arbitrary `text-[15px]`.

Use `.eyebrow` for the 11px uppercase label above a metric or section.

---

## 3. Tokens

**Never write a raw hex value in a component.** Everything is a Tailwind token
backed by a CSS variable in `src/index.css`.

| Purpose | Classes |
|---|---|
| Planes | `bg-canvas` `bg-surface-1` `bg-surface-2` `bg-surface-3` `bg-surface-inset` |
| Hairlines | `border-line` `border-line-subtle` `border-line-strong` |
| Ink | `text-content-primary` `-secondary` `-tertiary` `-muted` `-inverse` |
| Accent | `bg-accent` `text-accent-11` `border-accent-border` `bg-accent-subtle` |
| Severity mark | `bg-severity-critical` `-high` `-medium` `-low` `-secure` |
| Severity text | `text-severity-ink-critical` … `-secure` |
| Depth | `shadow-rim` `shadow-e1` `shadow-e2` `shadow-e3` `shadow-e4` |
| Motion | `duration-fast` `duration-base` `duration-slow`, `ease-standard` `ease-entrance` |

For Three.js and Recharts (which cannot read classes) import from
`@/design/tokens`: `SEVERITY_COLOR`, `SEVERITY_INK`, `ACCENT`, `PLANES`,
`chartChrome()`, `SPRING`, `EASE`, `DURATION`, `readCssVar()`, `currentTheme()`.

Severity presentation metadata (`badge`, `chip`, `text`, `dot`, `rail`, `label`,
`weight`) comes from `SEVERITY_META` in `@/utils/severity`. Do not re-derive it.

---

## 4. File layout

```
src/
  api/client.ts            mock API; one function per future endpoint
  components/
    ui/                    primitives (Button, Input, Modal, …)
    charts/                Recharts wrappers
    three/                 all WebGL; nothing else imports three directly
    findings/  resources/  scan/  dashboard/  marketing/   feature components
  data/                    mock datasets
  design/tokens.ts         typed token mirror
  hooks/                   data + behaviour hooks
  layouts/AppShell.tsx     console chrome
  pages/                   one file per route
  types/index.ts           domain model
  utils/                   pure helpers
```

Import with the `@/` alias only. No deep relative chains (`../../..`).

---

## 5. Data layer

`src/data/mock-data.ts` is the single public surface and re-exports everything:

```ts
mockAccounts, primaryAccount        // CloudAccount[]  , CloudAccount
mockResources, resourceCategories   // CloudResource[] , category summary rows
mockFindings                        // Finding[]
mockScans                           // Scan[]  (newest first)
mockSummary                         // SecuritySummary
mockGraph                           // InfrastructureGraph
mockReports                         // Report[]
defaultSettings                     // AppSettings
SCAN_STAGES                         // ScanStage[]
REGIONS                             // { id, label }[]
```

Components **never** import from `@/data/*` directly. They go through hooks,
which go through `@/api/client`. The only exception is `src/api/client.ts`.

### The mock client
Every function is `async`, has a realistic latency, and carries a comment naming
the endpoint that will replace it:

```ts
/** GET /api/dashboard */
async getDashboard(): Promise<SecuritySummary>
/** GET /api/findings */
async getFindings(filters?: FindingFilters): Promise<Finding[]>
/** GET /api/findings/:id */         async getFinding(id: string)
/** PATCH /api/findings/:id */       async updateFindingStatus(id, status)
/** GET /api/resources */            async getResources(filters?)
/** GET /api/resources/:id */        async getResource(id)
/** GET /api/infrastructure */       async getInfrastructureGraph()
/** GET /api/scans */                async getScans()
/** GET /api/scans/:id */            async getScan(id)
/** POST /api/scans */               async createScan(req: ScanRequest)
/** GET /api/reports */              async getReports()
/** POST /api/reports/:id/export */  async generateReport(id, format)
/** GET /api/settings */             async getSettings()
/** PATCH /api/settings */           async updateSettings(patch)
/** GET /api/accounts */             async getAccounts()
```

### Mutable session state
`AppDataProvider` (`src/hooks/useAppData.tsx`) holds the working copy of
findings / resources / summary / scans for the session and exposes mutations so a
scan or a "mark resolved" visibly updates every page:

```ts
useAppData(): {
  findings, resources, summary, scans, account
  loading, stale
  resolveFinding(id): void
  setFindingStatus(id, status): void
  applyScanResult(result: ScanResult): void
  refresh(): void
}
```

---

## 6. Shared component APIs — implement exactly these

Consumers are written against these signatures in parallel with the
implementations. Do not rename props. Extra optional props are fine.

### `ui/Button.tsx`
```ts
variant: 'primary' | 'secondary' | 'ghost' | 'danger' | 'link'   // default 'secondary'
size: 'sm' | 'md' | 'lg'                                          // default 'md'
icon?: LucideIcon        iconRight?: LucideIcon
loading?: boolean        fullWidth?: boolean
// forwards ref + all native button props; `asChild` not needed
```
`primary` = accent fill, inverse text. `secondary` = surface-2 fill + hairline.
`ghost` = transparent, surface-3 on hover. `danger` = critical fill.
Hover changes background one step and nothing else — no scale, no glow.
Active state: `translate-y-[0.5px]`.

### `ui/Input.tsx`, `ui/Select.tsx`, `ui/Textarea.tsx`
```ts
label?: string  hint?: string  error?: string  icon?: LucideIcon
// Select: options: { value: string; label: string }[]  + placeholder?
```
Native `<select>` for reliability; style the wrapper, add a chevron.

### `ui/SearchInput.tsx`
```ts
value: string  onChange(v: string): void  placeholder?: string
shortcut?: string   // renders a Kbd hint, e.g. '/'
```

### `ui/Badge.tsx`
```ts
tone: 'neutral' | 'accent' | 'critical' | 'high' | 'medium' | 'low' | 'secure'
variant: 'solid' | 'soft'   // default 'soft'
size: 'sm' | 'md'
icon?: LucideIcon  mono?: boolean
```

### `ui/SeverityBadge.tsx`
```ts
severity: Severity            // renders icon + uppercase label, always both
variant?: 'solid' | 'soft'    // default 'soft'
size?: 'sm' | 'md'
```
Icons: critical `ShieldAlert`, high `AlertTriangle`, medium `AlertCircle`,
low `Info`, secure `ShieldCheck`.

### `ui/StatusDot.tsx`
```ts
status: Severity | 'connected' | 'disconnected' | 'pending'
pulse?: boolean   // only for 'connected' and live scans
label?: string
```

### `ui/Tabs.tsx`
```ts
items: { id: string; label: string; count?: number }[]
value: string   onChange(id: string): void
variant?: 'underline' | 'segmented'   // default 'underline'
```
Underline tabs: 1px accent rule under the active item, `content-secondary` →
`content-primary` on activate. Keyboard: arrow keys move, roving tabindex.

### `ui/Modal.tsx`
```ts
open: boolean  onClose(): void
title: string  description?: string
size?: 'sm' | 'md' | 'lg' | 'xl'
footer?: ReactNode          // right-aligned action row
dismissible?: boolean       // default true (Esc + scrim click)
```
Renders in a portal. Traps focus, restores it on close, locks body scroll,
`aria-modal`, labelled by the title. Scrim uses `--scrim`.

### `ui/Drawer.tsx`
Same contract as Modal plus `width?: 'md' | 'lg' | 'xl'`. Slides from the right,
full height, hairline on the left edge. This is what a finding or resource opens
into from a table.

### `ui/ConfirmDialog.tsx`
```ts
open, onClose, onConfirm
title: string  message: string
confirmLabel?: string  tone?: 'danger' | 'default'  loading?: boolean
```

### `ui/Tooltip.tsx`
```ts
content: ReactNode  side?: 'top'|'right'|'bottom'|'left'  delay?: number
children: ReactElement
```
Opens on hover **and** focus. Portal-rendered, flips when it would clip.

### `ui/InfoTip.tsx`
A `HelpCircle` glyph wrapped in a Tooltip — use it on every piece of security
jargon (IMDSv1, permission boundary, CIDR, block public access, …).

### `ui/Toast.tsx` + `hooks/useToast.tsx`
```ts
useToast(): { toast(t: ToastInput): string; dismiss(id: string): void }
ToastInput = {
  title: string
  description?: string
  tone?: 'default' | 'success' | 'warning' | 'critical'
  duration?: number            // ms, default 4500; 0 = sticky
  action?: { label: string; onClick(): void }
}
```
Bottom-right stack, max 3 visible, hairline + `shadow-e3`, spring entry.

### `ui/DataTable.tsx`
The one table used by every list in the console.
```ts
columns: Column<T>[]         // { id, header, width?, align?, sortable?, cell(row), headerHint? }
rows: T[]
rowKey(row: T): string
onRowClick?(row: T): void
sort?: SortState  onSortChange?(s: SortState): void
loading?: boolean            // skeleton rows on first load only
stale?: boolean              // hold previous render at reduced opacity
empty?: ReactNode            // EmptyState
rowAccent?(row: T): string   // Tailwind class for the 2px left rail
density?: 'comfortable' | 'compact'
stickyHeader?: boolean
/** Below `md`, each row renders through this instead of as a <tr>. */
mobileCard?(row: T): ReactNode
```
Header: `surface-2`, `eyebrow` styling, sticky. Rows: hairline separators,
`surface-2` on hover, cursor-pointer when clickable. Selected row keeps a
`bg-accent-subtle` tint. Never horizontally scroll on mobile — use `mobileCard`.

### `ui/EmptyState.tsx`
```ts
icon: LucideIcon  title: string  description?: string
action?: { label: string; onClick(): void }
variant?: 'default' | 'success'   // 'success' for "no findings" — that's good news
```

### `ui/Skeleton.tsx`
```ts
variant?: 'text' | 'block' | 'circle'   width?: string  height?: string  lines?: number
```
A single quiet sweep; never a pulsing opacity flash.

### `ui/Meter.tsx`
```ts
value: number  max?: number   // default 100
tone?: Severity | 'accent'
label?: string  showValue?: boolean  size?: 'sm' | 'md'
```
Track is a lighter step of the fill's own ramp, not a grey.

### `ui/Metric.tsx`
The console stat tile.
```ts
label: string                 // sentence case, no trailing colon
value: string | number
unit?: string
delta?: { value: number; goodDirection: 'up' | 'down'; period?: string }
icon?: LucideIcon
tone?: Severity | 'accent' | 'neutral'
sparkline?: number[]
onClick?(): void              // becomes a real button when present
hint?: string                 // InfoTip content
```

### `ui/Kbd.tsx`, `ui/Segmented.tsx`, `ui/Switch.tsx`, `ui/Checkbox.tsx`, `ui/Pagination.tsx`, `ui/CopyButton.tsx`
Straightforward; keep them token-driven and accessible. `Switch` and `Checkbox`
take `checked` / `onChange(next: boolean)` / `label` / `description` / `disabled`.

### `charts/*`
```ts
SecurityScoreDial   { score, delta, band, size?: 'sm'|'md'|'lg', animate? }
DomainScoreRing     { domains: DomainScore[], score, onSelect?(d) }
ScoreTrendChart     { data: TrendPoint[], height?, showBrush? }
SeverityBreakdown   { counts: SeverityCounts, variant?: 'donut'|'bar', onSelect?(s) }
ServiceBreakdownChart { data: { service: ServiceId; counts: SeverityCounts }[] }
Sparkline           { data: number[], tone?, height? }
```
Chart rules — these are not optional:
- Gridlines and axes are **solid hairlines**, one step off the surface. Never dashed.
- Line marks 2px, round cap/join. End marker ≥8px with a 2px surface-coloured ring.
- Donut segments separated by a 2px surface-coloured stroke, never a border.
- A legend is present for ≥2 series; a single series gets none (the title names it).
- Direct-label selectively — the endpoint or the extreme, never every point.
- Every chart has a hover tooltip (crosshair for line, per-mark otherwise) and a
  keyboard-reachable equivalent. A tooltip is never the only way to read a value.
- One y-axis. Never a dual axis.
- Tooltips are custom components using `chartChrome()`; never Recharts defaults.

### `three/*`
See §8.

---

## 7. Behaviour rules

- **Loading**: skeletons on *first* load only. On refetch set `stale` and hold the
  previous render at 50% opacity — never flash a skeleton, never jump the layout.
- **Empty**: every list has a designed empty state. "No critical findings" is
  good news and uses `variant="success"`, not a sad grey box.
- **Errors**: inline, actionable, with a retry. No `alert()`.
- **Destructive actions** go through `ConfirmDialog`. Deleting an API key,
  disconnecting an account, suppressing a finding.
- **Toasts** confirm every mutation. Where the mock has no real effect (PDF
  export, webhook test) say so plainly in the toast description — do not pretend
  the backend exists.
- **Keyboard**: `/` focuses search, `Esc` closes the top layer, `⌘K`/`Ctrl+K`
  opens the command palette if present. Tables are arrow-navigable.
- **Every interactive element** has a visible focus ring, an accessible name, and
  a ≥24px hit target (≥44px on touch).
- **URL is state**: findings filters, the active tab and the selected finding all
  live in the query string so a view is linkable and back/forward works.

### Motion
Purposeful, short, and never looping in the background. Springs from
`SPRING.firm` (UI feedback) and `SPRING.soft` (layout, camera). Page transitions
are a 180ms fade + 4px rise — no slide-in carousels. Respect
`prefers-reduced-motion` everywhere: `useDeviceTier().prefersReducedMotion`
disables 3D idle motion, parallax and scroll animation, keeping opacity changes.

---

## 8. 3D rules

All WebGL lives in `src/components/three/`. Nothing outside that folder imports
`three`, `@react-three/fiber` or `@react-three/drei`.

**The 3D is an information display, not an ornament.** Every mesh maps to a real
resource, relationship or scan stage in the mock data. If a mesh doesn't
represent data, delete it.

Aesthetic: enterprise infrastructure visualisation. Matte or lightly metallic
surfaces, soft studio lighting, thin luminous connection lines, generous empty
space. **No** neon wireframes, no matrix rain, no particle storms, no chrome
spheres, no lens flares, no bloom cranked past subtle.

Required plumbing:
- `<SceneCanvas>` wraps every `<Canvas>`: sets `dpr={[1, tier.maxDpr]}`,
  `gl={{ antialias, powerPreference: 'high-performance' }}`, `frameloop`
  (`'demand'` for static scenes, `'always'` only while something moves),
  a `<Suspense>` fallback, and an error boundary that renders the 2D fallback.
- `useDeviceTier()` returns `{ tier: 'high'|'balanced'|'low'|'off', maxDpr,
  prefersReducedMotion, isTouch, enable3d }`. Decide from
  `navigator.hardwareConcurrency`, `deviceMemory`, pointer type, viewport width
  and the reduced-motion query. `tier: 'off'` ⇒ render the 2D fallback and never
  mount a Canvas.
- **Every scene has a real 2D fallback**, not a blank box: the infrastructure map
  falls back to a readable SVG/DOM tier diagram, the hero to a composed static
  panel. The console must be fully usable with WebGL disabled.
- Instance repeated geometry (`<Instances>` / `InstancedMesh`). Share geometries
  and materials via `useMemo`. Dispose anything created imperatively on unmount.
- Pause the frameloop when the canvas is offscreen (`IntersectionObserver`) or
  the tab is hidden.
- Cap pixel ratio at 2. No postprocessing on `balanced` or `low`.
- Node labels use `<Html>` from drei sparingly, or are drawn in the DOM layer
  above the canvas — never as 3D text meshes for body copy.

Interaction contract for the graph scenes:
- Hover a node → it lifts slightly, its edges brighten, a DOM tooltip shows
  name / type / region / status / finding count.
- Select a node → camera eases to frame it (`SPRING.soft`), related nodes and
  edges highlight, unrelated ones drop to ~25% opacity, and a detail panel opens.
- Drag rotates within a clamped range (never a free tumble), scroll zooms within
  clamped limits, double-click resets. On touch, one finger orbits, two pinch.
- Idle motion is a very slow drift — a few degrees over several seconds — and it
  stops entirely on `prefers-reduced-motion`.

---

## 9. Responsive

Breakpoints: `sm` 640 · `md` 768 · `lg` 1024 · `xl` 1280 · `2xl` 1536. Design at
1440 first, then verify 1280, 1024, tablet and 390px mobile.

- Sidebar: full at `xl`, icon-rail at `lg`, off-canvas sheet below `lg`.
- Tables: `mobileCard` below `md`. Never a horizontal scrollbar on a phone.
- 3D: `tier` drops to `low` on touch and narrow viewports; hero 3D becomes a
  static composed panel below `md`.
- Console content max width `max-w-shell`, page gutters `px-4 md:px-6 xl:px-8`.

---

## 10. The bar

Before finishing any page, check it against this list:

- [ ] Does it look like one coherent product with the pages beside it?
- [ ] Is there a clear single focal point, or does everything shout equally?
- [ ] Are there containers other than rounded boxes on this page?
- [ ] Is every 3D element carrying information?
- [ ] Would this stay comfortable after five hours of use?
- [ ] Real loading, empty and error states — not just the happy path?
- [ ] Any raw hex, arbitrary font size, or inline magic number left behind?
- [ ] Keyboard-navigable end to end, with visible focus?
- [ ] Does anything animate that nobody asked to animate?
