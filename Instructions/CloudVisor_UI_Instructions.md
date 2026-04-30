# CloudVisor — UI Design & Build Prompt
> **Version:** 4.0 (AWS Console visual language)
> **Purpose:** This is the complete UI engineering brief for the CloudVisor CNAPP platform.
> Read it fully before writing a single line of code or making a single design decision.
> Every section is binding. This prompt works alongside the Master Engineering Prompt
> (CloudVisor_Instructions_v3.md) — the two documents together define the complete product.
>
> **v4.0 Changes:** Visual language rebuilt on **AWS Cloudscape Design System** (the
> open-source system AWS uses to build the AWS Management Console). Typography, spacing,
> border radii, elevation, layout (AppLayout), navigation (top service bar + side
> navigation + breadcrumbs + tools panel + split panel), component shapes, and interaction
> patterns all follow Cloudscape conventions. **The color palette is UNCHANGED from v3.0**
> — the brand colors (Deep Blue navy, Bright Blue, Coral, Sunset, severity palette, cloud
> provider brand colors) are retained verbatim. Only color-adjacent styling is updated.
> The Cloudscape Visual Refresh (2024) principles apply: thin 1–2px strokes instead of
> drop shadows on containers, shadows reserved for transient elements, stronger typographic
> hierarchy, labels more prominent in form fields, clearer dark-mode differentiation.

---

## 0. How to Use This Document

This prompt is given to the LLM UI engineer at the start of every frontend session.
It provides the complete design system, page specifications, component library rules,
UX interaction patterns, and reference context needed to build a production-grade
CNAPP dashboard that feels native to engineers who already live inside the AWS
Management Console.

**Before writing any component, the assistant must:**
1. Read this document fully
2. Understand the design system (Section 2) — do not deviate from it
3. Locate the specific page spec (Section 5) for the page being built
4. Apply all component rules (Section 3) and UX patterns (Section 4)
5. Reference Cloudscape patterns (Section 6) to understand what "native AWS" looks like

**The output of every session must be:**
- Production-ready React + TypeScript components
- Fully responsive (desktop 1440px, laptop 1280px, tablet 768px, mobile 375px)
- Light mode by default, dark mode via `[data-theme="dark"]` attribute on `<html>`
- WCAG 2.1 AA accessible
- Connected to real API endpoints (never hardcoded mock data in production components)
- Covered by Storybook stories for every new component

---

## 1. Product & User Context

### What CloudVisor is

CloudVisor is a B2B SaaS CNAPP (Cloud-Native Application Protection Platform).
It is used exclusively by security professionals inside companies to protect their
cloud infrastructure across AWS, Azure, GCP, and OCI.

This is not a consumer app. The people using it are experts under pressure.
They manage hundreds of cloud accounts, thousands of resources, and tens of thousands
of security findings. The UI must help them cut through complexity — not add to it.

### Who uses the UI and what they need

Every design decision must serve one of these five users. When in doubt, design for
the Security Engineer first — they are the primary daily user.

| User | Job | What they open CloudVisor for | What frustrates them |
|---|---|---|---|
| **Security Engineer** | Cloud security team | Daily: triage findings, write rules, track remediation | Alert fatigue, too many clicks to get context, slow dashboards |
| **SOC Analyst** | Security operations | Real-time: investigate incidents, correlate CDR alerts | Missing context, switching between tools, noise drowning signal |
| **DevOps Engineer** | Platform / infra team | Weekly: check CI/CD scan results, IaC security, K8s posture | Security tools that block pipelines with false positives |
| **CISO / VP Security** | Leadership | Monthly: posture score, compliance status, executive reports | Dashboards that show numbers without telling a story |
| **Compliance Officer** | GRC team | Quarterly: compliance audits, evidence export, framework gaps | Manual evidence collection, outdated compliance data |

### Emotional design target

Users should feel:
- **In control** — "I can see everything, nothing is hiding from me"
- **Confident** — "I trust this data, the numbers are accurate"
- **Fast** — "I got to the answer in 2 clicks"
- **Calm** — "This is serious data presented without panic"

Users must never feel:
- Overwhelmed by visual noise
- Lost in navigation
- Uncertain about what a number means
- Anxious that data might be stale or wrong

---

## 2. Design System

This section defines every visual decision. Do not introduce colors, fonts, spacing,
or components that are not defined here.

### 2.1 Design philosophy

CloudVisor's aesthetic is **"Cloudscape-native"** — the exact visual language AWS uses
to build the AWS Management Console via its open-source Cloudscape Design System.
Cloudscape is the single visual reference for this product. Do not blend in patterns
from Wiz, Prisma Cloud, Lacework, Orca, or generic SaaS dashboards. Engineers who
spend all day in the AWS Console should feel at home the moment CloudVisor loads —
same density, same typographic rhythm, same page structure, same interaction grammar.

**Study the AWS Management Console before building anything. The signatures to replicate:**

- **AppLayout as the canonical page frame.** Every authenticated page uses the Cloudscape
  AppLayout: a thin dark top navigation bar across the full width, a collapsible left
  side navigation panel, breadcrumbs immediately below the top nav, a content area, an
  optional right tools panel (help / inline context), and an optional bottom split panel
  (details without leaving the list). This is the shape of AWS.
- **Top navigation is a thin dark bar.** Full-width, ~40px tall, dark (uses the brand
  navy). Hosts product logo, global search / resource lookup, region/account switcher,
  notifications, and the user avatar menu. It is dark in both light and dark modes.
- **Side navigation is a LIGHT panel on light mode** (white, ~280px) with chevron-based
  expand/collapse groups and a 2px left indicator on the active link. This inverts in
  dark mode. It is NOT the dark navy of the top bar — the top bar and the side nav have
  different backgrounds. This is the specific AWS signature.
- **Breadcrumbs on every interior page.** `Home / Findings / S3 public bucket` — always
  directly below the top nav, above the page title. Cloudscape users rely on breadcrumbs
  to backtrack; never omit them.
- **Container component is the primary content wrapper.** Header (title + actions) +
  body + optional footer, 1px border at `var(--border-default)`, radius 16px, NO drop
  shadow. Cloudscape's Visual Refresh replaced shadows on containers with thin strokes.
  Use shadows only for transient/interactive surfaces (modals, popovers, dropdowns,
  tooltips, toasts).
- **Table is the default data surface.** Dense, sortable, with a header bar above
  (title + counter + primary/secondary actions) and a filter row (text filter + property
  filter tokens). Row height defaults to 40px (comfortable) with a 32px compact density
  toggle. Single-row hover, checkbox multi-select, pagination at the bottom.
- **Form fields stack label → control → description → error.** Label is prominent
  (14px, weight 700). Inputs are 32px tall, 8px radius, 1px border. This is Cloudscape's
  post-Visual-Refresh treatment — labels read louder than before.
- **Flashbar for page-level status.** Stack of Cloudscape-style Flash messages at the
  top of the content area (below breadcrumbs) for success / error / warning / info and
  in-progress notifications. Each message: icon + title + optional description +
  dismiss. Do not use toast for page-level status — Flashbar is the AWS pattern.
- **StatusIndicator (icon + label) is how state is displayed.** Never just a colored
  dot. Success = green check + "Success"; Error = red cross + "Failed"; In-progress =
  spinner + "In progress"; Warning = amber triangle + "Warning"; Info = blue info +
  "Info"; Stopped = gray square + "Stopped". Used in every table cell that shows state.
- **Buttons are pill-shaped (radius 20px).** Four variants: `primary` (filled brand
  blue), `normal` (white with 1px border), `link` (text-only, brand blue, underlined on
  hover), `icon` (square icon-only, subtle). Button heights: 32px default. Button labels
  are sentence case, not ALL CAPS.
- **Typography is Open Sans.** Cloudscape's default. Monospace (for IDs, ARNs, code)
  is the Cloudscape mono stack. Type hierarchy is strong — H1 is noticeably larger than
  H2 is noticeably larger than body. Body is 14px.
- **Content density toggle is a global user preference.** "Comfortable" (default) and
  "Compact" — compact reduces row heights, vertical paddings, and some font sizes.
  Persist selection to localStorage.
- **Help and context live in the right Tools panel.** Opened with a "ⓘ Info" link next
  to any field, section header, or column header. Never open help in a separate page.
- **Split panel for quick detail.** On list pages (Findings, Assets), clicking a row
  opens a bottom-anchored split panel by default (not a right drawer) — the selected
  row's key details below, the full table still visible above. Users can switch the
  split panel to side-anchored. This is how AWS does resource detail views.
- **Minimal decoration.** No gradients, no illustrated empty states with marketing copy,
  no hero cards. Empty states are a small icon + short message + single primary action,
  centered, in a Container. The aesthetic is quietly professional — like a terminal with
  a great UI around it.

**What this means concretely:**
- Light mode is the DEFAULT. Dark mode is a user toggle, never the default.
- Top navigation is always dark (brand navy) in both modes. Side nav follows the mode.
- Containers have 1px strokes, NO shadows. Shadows are only on modals/popovers/toasts.
- Every state indicator is a StatusIndicator (icon + label) — never just a colored dot.
- Every interior page has breadcrumbs, a page title, and usually a Container wrapping
  the main content. These three are the AWS Console skeleton.
- Page-level status goes in a Flashbar, not a toast. Toasts are for transient feedback
  only (e.g., "Link copied").
- Info links are inline ("ⓘ Info") and open the right Tools panel — they do not navigate.

**NOT:** Dark sidebar on light content. Not large risk-score hero gauges as the page's
primary visual. Not finding cards with thick colored left borders scattered across the
page. Not purple-gradient marketing aesthetics. Not glassmorphism. Not "customizable
widget grid" dashboards where every tile is a draggable widget.

### 2.2 Color system

**Light mode is the default** — matching the AWS Management Console. Dark mode is a
user setting toggled via `[data-theme="dark"]` on `<html>`. Never build a page in dark
mode first. **The color palette below is unchanged from v3 — CloudVisor retains its
brand identity (navy + bright blue + coral + sunset) even though the rest of the
visual language now follows AWS Cloudscape.** These CSS custom properties are the only
color values permitted in the product; hard-coded hex values outside this block are
forbidden.

```css
/* ─── DEFAULT: Light mode (AWS Console style) ───────────────────── */
:root {
  /* Backgrounds */
  --bg-base:        #f5f7fa;   /* Page background — Cloudscape light gray */
  --bg-surface:     #ffffff;   /* Containers, cards, panels, modals, side nav */
  --bg-elevated:    #f8fafc;   /* Hover states, selected rows, expanded row bg */
  --bg-overlay:     #ffffff;   /* Drawers, popovers, tools panel */
  --bg-sidebar:     #0b1e3f;   /* Brand navy — used on the TOP NAV bar (dark, full width) */
  --bg-sidebar-hover: #152a54; /* Top nav hover state */
  --bg-sidebar-active: #1e3a6b;/* Top nav active state */
  --bg-header:      #ffffff;   /* Breadcrumb/secondary bar, page header area */
  --bg-sidenav:     #ffffff;   /* Side navigation panel — LIGHT in light mode */
  --bg-sidenav-hover: #f1f5f9; /* Side nav item hover */
  --bg-sidenav-active: #e8f0fe;/* Side nav item active (accent tint) */

  /* Borders */
  --border-faint:   #eef1f6;
  --border-default: #dde3ec;
  --border-strong:  #b8c4d4;
  --border-accent:  rgba(26,115,232,0.40);

  /* Text */
  --text-primary:   #0b1e3f;   /* Deep navy for primary body text and headings */
  --text-secondary: #4a5568;
  --text-tertiary:  #8898aa;
  --text-on-sidebar: #c8d3e0;  /* Text on dark top nav */
  --text-on-sidebar-active: #ffffff;
  --text-inverse:   #ffffff;

  /* Brand accent — Bright Blue (primary interactive color, per Cloudscape Visual Refresh) */
  --accent:         #1a73e8;   /* Primary CTA, active nav indicator, links */
  --accent-hover:   #1557b0;
  --accent-dim:     rgba(26,115,232,0.08);
  --accent-light:   #e8f0fe;

  /* Brand warm accents — use SPARINGLY, for risk emphasis only */
  --brand-coral:    #ff6b6b;   /* Critical-severity emphasis, risk summary cards */
  --brand-sunset:   #ff9a56;   /* High-severity emphasis */
  --brand-gradient: linear-gradient(135deg, #ff9a56 0%, #ff6b6b 100%);
                               /* Sunset → Coral, reserved for risk-summary surfaces only */

  /* ─── Severity — NON-NEGOTIABLE across every component ───────── */
  /* Semantic severity mapping — Red for critical, Orange for high, Amber for medium, Blue for low */
  --critical:       #dc2626;   /* Red — immediate danger */
  --critical-bg:    #fef2f2;   /* Light red background for cards */
  --critical-border: #fca5a5;  /* Red border for finding cards */
  --critical-dim:   rgba(220,38,38,0.10);

  --high:           #ea580c;   /* Orange — significant risk */
  --high-bg:        #fff7ed;
  --high-border:    #fdba74;
  --high-dim:       rgba(234,88,12,0.10);

  --medium:         #d97706;   /* Amber — moderate risk */
  --medium-bg:      #fffbeb;
  --medium-border:  #fcd34d;
  --medium-dim:     rgba(217,119,6,0.10);

  --low:            #2563eb;   /* Blue — low risk */
  --low-bg:         #eff6ff;
  --low-border:     #93c5fd;
  --low-dim:        rgba(37,99,235,0.10);

  --info:           #6b7280;   /* Gray — informational */
  --info-bg:        #f9fafb;
  --info-border:    #d1d5db;
  --info-dim:       rgba(107,114,128,0.10);

  /* Status */
  --status-open:        var(--critical);
  --status-in-progress: var(--medium);
  --status-resolved:    #16a34a;
  --status-suppressed:  var(--info);
  --status-accepted:    #7c3aed;

  /* Semantic */
  --success:        #16a34a;
  --success-bg:     #f0fdf4;
  --success-dim:    rgba(22,163,74,0.10);
  --warning:        #d97706;
  --warning-dim:    rgba(217,119,6,0.10);
  --danger:         #dc2626;
  --danger-dim:     rgba(220,38,38,0.10);

  /* Cloud providers — exact brand colors */
  --aws:            #f97316;   /* AWS Orange */
  --aws-bg:         #fff7ed;
  --azure:          #0078d4;   /* Azure Blue — exact Microsoft brand */
  --azure-bg:       #eff6ff;
  --gcp:            #1a73e8;   /* GCP Blue — exact Google brand */
  --gcp-bg:         #eff4ff;
  --oci:            #c74634;   /* OCI Red — exact Oracle brand */
  --oci-bg:         #fff1f0;
}

/* ─── Dark mode override ─────────────────────────────────────────── */
/* Applied via [data-theme="dark"] on <html> — user-toggleable                 */
/* Matches AWS Console dark mode: deep charcoal surfaces, subtle borders       */
[data-theme="dark"] {
  --bg-base:        #0d1117;   /* Page background */
  --bg-surface:     #161b22;   /* Containers, cards, side nav */
  --bg-elevated:    #1c2433;   /* Row hover, expanded rows */
  --bg-overlay:     #21293a;   /* Modals, popovers, tools panel */
  --bg-sidebar:     #0d1117;   /* Top nav — even darker in dark mode */
  --bg-sidebar-hover: #161b22;
  --bg-sidebar-active: #1c2433;
  --bg-header:      #161b22;   /* Breadcrumb/secondary bar */
  --bg-sidenav:     #161b22;   /* Side nav panel — INVERTS to dark in dark mode */
  --bg-sidenav-hover: #1c2433;
  --bg-sidenav-active: rgba(26,115,232,0.14);
  --border-faint:   rgba(255,255,255,0.05);
  --border-default: rgba(255,255,255,0.09);
  --border-strong:  rgba(255,255,255,0.16);
  --text-primary:   #e2e8f0;
  --text-secondary: #8899b4;
  --text-tertiary:  #4a5568;
  --text-on-sidebar: #c8d3e0;
  --text-on-sidebar-active: #ffffff;
  --critical-bg:    rgba(220,38,38,0.12);
  --critical-border: rgba(220,38,38,0.30);
  --high-bg:        rgba(234,88,12,0.12);
  --high-border:    rgba(234,88,12,0.30);
  --medium-bg:      rgba(217,119,6,0.12);
  --medium-border:  rgba(217,119,6,0.30);
  --low-bg:         rgba(37,99,235,0.12);
  --low-border:     rgba(37,99,235,0.30);
  --accent-light:   rgba(37,99,235,0.12);
  --success-bg:     rgba(22,163,74,0.12);
}
```

### 2.3 Typography

CloudVisor uses **Open Sans**, Cloudscape's default typeface. This is what engineers
see in the AWS Management Console — keeping it identical is deliberate. Monospace is
reserved for IDs, ARNs, resource identifiers, numeric metrics, timestamps, and code.

```css
/* Import in global CSS */
@import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --font-sans:  'Open Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  --font-mono:  'JetBrains Mono', 'Monaco', Consolas, 'Courier New', monospace;

  /* Font weights — Cloudscape uses 4 weights, not 8 */
  --weight-regular: 400;   /* body text, table cells */
  --weight-semibold: 600;  /* table headers, labels, small section headers */
  --weight-bold: 700;      /* page titles, container headers, form labels */
  --weight-heavy: 800;     /* display metrics only (rare) */
}

/* ─── Type scale (Cloudscape Visual Refresh hierarchy) ────────── */
/* Use these classes only. Do not invent other font sizes.        */
/* Body default is 14px — noticeably larger than the v3 dense scale. */

.text-display  { font-size: 32px; line-height: 40px; font-weight: 800; }  /* Rare hero numbers */
.text-h1       { font-size: 24px; line-height: 32px; font-weight: 700; }  /* Page title */
.text-h2       { font-size: 20px; line-height: 28px; font-weight: 700; }  /* Container header */
.text-h3       { font-size: 18px; line-height: 24px; font-weight: 700; }  /* Sub-section header */
.text-h4       { font-size: 16px; line-height: 22px; font-weight: 700; }  /* Small section header */
.text-h5       { font-size: 14px; line-height: 20px; font-weight: 700; }  /* Minor heading / prominent label */
.text-body     { font-size: 14px; line-height: 22px; font-weight: 400; }  /* DEFAULT body */
.text-body-bold{ font-size: 14px; line-height: 22px; font-weight: 700; }  /* Form labels */
.text-small    { font-size: 12px; line-height: 18px; font-weight: 400; }  /* Description, helper text, table-cell secondary */
.text-xsmall   { font-size: 11px; line-height: 16px; font-weight: 400; }  /* Timestamps, footnotes */

/* ─── Typography rules ─────────────────────────────────────────── */
/* Page titles (H1): text-h1 weight 700, text-primary. Always paired with a
   breadcrumb above and an optional description below (text-small, text-secondary). */
/* Container headers (H2): text-h2 weight 700, with optional counter "(47)" in
   text-secondary weight 400 inline after the title. */
/* Table column headers: text-small weight 600, text-secondary, letter-spacing 0 (NO
   uppercase, NO wide tracking — Cloudscape is sentence case). */
/* Form labels: text-body-bold (14px / 700) — prominent, per Visual Refresh. */
/* Form helper text: text-small, text-secondary, placed BELOW the input. */
/* Inline "ⓘ Info" links: text-small, var(--accent), underline on hover. */
/* Links in body copy: var(--accent), underline on hover only (not by default). */
/* Code, IDs, ARNs, fingerprints, IP addresses, UUIDs: font-mono, text-small. */
/* Numeric metrics (counts, percentages): font-mono, preserves alignment in tables. */
/* NEVER use font-mono for labels, titles, or body prose. */
/* NEVER use ALL CAPS or letter-spacing for section labels — Cloudscape is sentence case. */
```

### 2.4 Spacing system

CloudVisor uses Cloudscape's **4px base grid** (not 8px). Every padding, margin, and
gap resolves to a multiple of 4. Cloudscape follows a soft-grid approach — elements
are positioned relative to each other via line-height, not snapped to a baseline grid.

```
Spacing scale (use these tokens, never raw values):
  --space-xxxs:  2px    — hairline gap (icon-to-adjacent-icon in a dense control)
  --space-xxs:   4px    — badge internal padding, dot-to-label gap
  --space-xs:    8px    — icon-to-label gap, checkbox-to-label gap
  --space-s:    12px    — compact component internal padding, button horizontal padding
  --space-m:    16px    — default component internal padding, form-field vertical gap
  --space-l:    20px    — Container body padding (default)
  --space-xl:   24px    — Container body padding (spacious), section vertical gap
  --space-xxl:  32px    — section separation
  --space-xxxl: 40px    — major section break
  --space-4xl:  48px    — page-level section separation

AppLayout structural dimensions:
  Top navigation bar height:       40px (Cloudscape TopNavigation)
  Breadcrumb / secondary bar:      40px
  Side navigation width:          280px (expanded) · 36px (collapsed, icon-only rail)
  Tools panel width (right):      290px (when open; hidden by default)
  Split panel default height:     360px (bottom-anchored) · 320px (side-anchored)
  Content max-width:             1440px (centered, with --space-xl horizontal gutter)
  Content horizontal padding:      40px on desktop, 24px on laptop, 16px on mobile
  Content top padding:             24px below breadcrumbs

Component dimensions:
  Button height (default):         32px
  Button height (small):           24px
  Input / Select / Textarea height: 32px (single-line)
  Table row (comfortable):         40px  ← DEFAULT
  Table row (compact):             32px  ← density toggle
  Container header height:         52px (title + actions row)
  Tab bar height:                  44px
  Flashbar item min-height:        44px
```

### 2.5 Border radius

Cloudscape assigns border radius by element purpose — not by size. Small interactive
elements have one radius, form controls have another, Containers have a larger radius,
and Buttons are pill-shaped. This radius hierarchy is the Cloudscape Visual Refresh
signature.

```
--radius-badge:    2px    — severity badges, status pills, token chips (very tight)
--radius-input:    8px    — inputs, selects, textareas, checkboxes, radio labels
--radius-button:  20px    — BUTTONS (all variants — primary, normal, icon: pill shape)
--radius-item:    12px    — small cards, side nav items, dropdown items, table row-group
--radius-container:16px   — Container, Modal, Flashbar, Popover, Tooltip card
--radius-alert:   12px    — Alert / Flash messages
--radius-table:    0px    — table row borders (horizontal separators only, no row radius)

Rules of hierarchy:
- An input (8px) inside a Container (16px) reads as a child of the container
  because its radius is smaller. Preserve this ratio — never round children more
  than their parent.
- Buttons are ALWAYS pill-shaped (20px). A square-cornered button is wrong.
- Cards inside a Container use --radius-item (12px), never the Container's 16px.
- Tables have zero row radius. Container wraps the table; the outer radius lives
  on the Container.
```

### 2.6 Shadow and elevation

Cloudscape's 2024 Visual Refresh **removed drop shadows from Containers, Cards, and
other layout wrappers** and replaced them with thin 1px strokes. Shadows are now
reserved for transient and interactive overlay surfaces — modals, popovers, dropdowns,
tooltips, toasts, and the split-panel divider. Applying a shadow to a Container is
explicitly wrong.

```css
/* Layout surfaces: NO shadow — use a 1px border at var(--border-default) */
.container { border: 1px solid var(--border-default); box-shadow: none; }

/* Overlay surfaces: Cloudscape-style soft shadows */
--shadow-popover:  0 1px 4px -1px rgba(0,28,36,0.10), 0 4px 16px -4px rgba(0,28,36,0.18);
--shadow-dropdown: 0 1px 4px -1px rgba(0,28,36,0.10), 0 4px 16px -4px rgba(0,28,36,0.18);
--shadow-modal:    0 1px 4px -1px rgba(0,28,36,0.10), 0 6px 36px -6px rgba(0,28,36,0.30);
--shadow-toast:    0 1px 4px -1px rgba(0,28,36,0.10), 0 4px 20px -6px rgba(0,28,36,0.25);

/* Split-panel dividing edge — a shadow ABOVE the panel to lift it off the content */
--shadow-split:    0 -2px 12px -4px rgba(0,28,36,0.14);

/* Focus shadow — visible 2px ring in accent color (keyboard focus indicator) */
--shadow-focus:    0 0 0 2px var(--bg-surface), 0 0 0 4px var(--accent);

/* Dark mode — shadows become almost invisible; rely on borders + slightly elevated bg */
[data-theme="dark"] {
  --shadow-popover:  0 2px 8px rgba(0,0,0,0.50);
  --shadow-dropdown: 0 2px 8px rgba(0,0,0,0.50);
  --shadow-modal:    0 8px 32px rgba(0,0,0,0.70);
  --shadow-toast:    0 4px 16px rgba(0,0,0,0.55);
  --shadow-split:    0 -2px 12px rgba(0,0,0,0.40);
}

/* Rules */
/* 1. NEVER apply box-shadow to Container, Card, Side nav, Top nav, Flashbar, Table. */
/* 2. Apply --shadow-modal only to Modal.    Apply --shadow-popover to Popover, Help panel. */
/* 3. Never use colored glows. Shadows are neutral and subtle — the Cloudscape way. */
/* 4. Focus rings use --shadow-focus. Never use outline: for focus — use this box-shadow. */
```

### 2.7 Motion and animation

Cloudscape's motion system is restrained — short durations, linear-ish easing, no
playful overshoot. The goal is "instant acknowledgment," not delight. Motion is a
signal, not a flourish.

```css
/* Transition durations — Cloudscape scale */
--duration-rapid:    90ms;   /* instant feedback: button press, checkbox toggle */
--duration-fast:    135ms;   /* default: hover, color/border change, link */
--duration-moderate:165ms;   /* dropdown open, accordion expand */
--duration-slow:    240ms;   /* modal open, split-panel resize, drawer slide */

/* Easing — Cloudscape defaults */
--ease-default:  cubic-bezier(0.25, 0.1, 0.25, 1);      /* standard ease-in-out */
--ease-entrance: cubic-bezier(0.0, 0.0, 0.2, 1);        /* elements entering the viewport */
--ease-exit:     cubic-bezier(0.4, 0.0, 1, 1);          /* elements leaving */

/* Rules */
/* 1. All interactive elements transition background, border, and color on hover/focus. */
/* 2. Page-level transitions: fade (opacity 0 → 1) at 165ms. NO translate/slide on pages. */
/* 3. Split panel resize: height/width transitions at 240ms. */
/* 4. Modal open: fade backdrop + scale content 0.96 → 1.0 at 240ms. */
/* 5. Flashbar items: slide-in from top (translateY -8px → 0) + fade, 165ms. */
/* 6. Number counters do NOT animate by default (Cloudscape shows values immediately). */
/*    Only animate counters when the previous value is visible AND the delta matters. */
/* 7. Charts animate on mount: 240ms ease-entrance (bars grow, lines draw). */
/* 8. NO bounce, NO spring, NO elastic easing. This is professional enterprise software. */
/* 9. All animations must respect prefers-reduced-motion. */
/* 10. Skeleton loaders on all data-dependent components (never spinners alone, except */
/*     for in-flight button-submit state which shows an inline spinner inside the button). */

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### 2.8 Icons

CloudVisor uses **Lucide React** as its icon library (Cloudscape's own icon set is
not distributable outside Cloudscape, so Lucide — which matches the same clean
outline style — is the closest acceptable match). Icons are stroked, never filled,
and always use `currentColor`.

```tsx
import { Shield, AlertTriangle, CheckCircle2, XCircle, Info,
         Cloud, Server, Database, Key, Lock, Unlock,
         GitBranch, Terminal, Globe, Eye, EyeOff,
         ChevronRight, ChevronDown, ChevronLeft, ChevronUp,
         MoreHorizontal, MoreVertical, X,
         Filter, Search, Download, Upload, RefreshCw, Settings,
         TrendingUp, TrendingDown, Minus, Plus,
         ExternalLink, Copy, Edit2, Trash2, HelpCircle } from 'lucide-react';

/* Icon sizes — Cloudscape uses 4 display sizes */
/* 16px — DEFAULT: inline in text, table-cell icons, inside buttons */
/* 20px — medium: section header icons, StatusIndicator in Flashbar */
/* 24px — large: card header icons, tab icons */
/* 32px — extra-large: empty-state illustrations only */

/* Stroke width rules (Lucide supports stroke-width prop) */
/* stroke-width 2   — DEFAULT (matches Cloudscape's weight) */
/* stroke-width 1.5 — for 20px+ icons (lighter appearance at larger sizes) */

/* Icons always use currentColor — never hardcode fill or stroke colors. */
/* Icons inside buttons: 16px, 4px gap to label (--space-xxs). */
/* Icons in StatusIndicator: 16px, 4px gap to label. */
/* Icons in side nav items: 16px, 8px gap to label (--space-xs). */
/* Icons in tab labels: 16px, 8px gap to label. */
/* Info "ⓘ" link: use HelpCircle at 16px inline, same color as text. */
```

**Cloud provider icons are distinct from UI icons.** For AWS / Azure / GCP / OCI
resource types, use the **official provider SVG icons** stored in
`public/icons/{provider}/`. These render at 16px in table cells, 20px in detail
headers, 24px in graph nodes. See Section 6 Pattern 14 for the full spec.

---

## 3. Component Library

Every component listed here must be built in `packages/ui/` as a reusable
Storybook-documented component before being used in any page.

### 3.1 SeverityBadge

A Cloudscape-style `Badge` is a compact token used on every findings table, every
alert, every notification. It is a small pill — uppercase text, no icon.

```tsx
// Usage
<SeverityBadge severity="CRITICAL" />
<SeverityBadge severity="HIGH" />
<SeverityBadge severity="MEDIUM" />
<SeverityBadge severity="LOW" />
<SeverityBadge severity="INFO" />

// Spec — matches Cloudscape Badge component
// Shape: rounded corners, border-radius var(--radius-badge) = 2px
// Padding: 2px 6px
// Font: font-sans, 12px (text-small), weight 700, UPPERCASE, letter-spacing 0
//       (Cloudscape's Badge uses sentence case internally but severity names are
//       CRITICAL / HIGH / MEDIUM / LOW / INFO — these stay uppercase as proper nouns
//       of a severity enum, not as a stylistic choice)
// Colors: text = var(--{severity}) ON background = var(--{severity}-dim)
//         No border, background fill only
// Width: fit-content
// Optional: size prop ("small" | "normal") — small: 11px font, 1px 4px padding
// Optional: withIcon prop — prepends a 12px severity icon (AlertTriangle, AlertCircle)

// CRITICAL: bg var(--critical-dim),  text var(--critical)
// HIGH:     bg var(--high-dim),      text var(--high)
// MEDIUM:   bg var(--medium-dim),    text var(--medium)
// LOW:      bg var(--low-dim),       text var(--low)
// INFO:     bg var(--info-dim),      text var(--info)
```

### 3.1b StatusIndicator (new — Cloudscape core pattern)

Separately from SeverityBadge, Cloudscape's `StatusIndicator` is the canonical way
to show **state** (success, error, warning, in-progress, stopped, pending, info,
loading). It is an inline icon + label pair — NEVER just a colored dot. Used in
every table cell that shows state, inside every Flashbar message, next to every
scan/connector/job status.

```tsx
<StatusIndicator type="success">   Available </StatusIndicator>
<StatusIndicator type="error">     Failed    </StatusIndicator>
<StatusIndicator type="warning">   Degraded  </StatusIndicator>
<StatusIndicator type="info">      Starting </StatusIndicator>
<StatusIndicator type="loading">   In progress </StatusIndicator>
<StatusIndicator type="pending">   Pending   </StatusIndicator>
<StatusIndicator type="stopped">   Stopped   </StatusIndicator>

// Spec
// Shape: inline-flex, 4px gap between icon and label
// Icon: 16px, colored per type, stroke-width 2
// Label: text-body (14px, weight 400), colored to match icon for stronger types
//        (error, warning) or neutral text-primary (success, info, stopped)
// NO background, NO border, NO padding — StatusIndicator is inline content, not a pill
// NO icon-only version — label is always present (accessibility)

// type → icon → color:
// success  → CheckCircle2  → var(--success)  (green)
// error    → XCircle       → var(--danger)   (red)
// warning  → AlertTriangle → var(--warning)  (amber)
// info     → Info          → var(--accent)   (blue)
// loading  → spinning Loader2 → var(--accent)
// pending  → Clock         → var(--text-secondary)
// stopped  → MinusSquare   → var(--text-secondary)
```

### 3.2 StatusBadge

For finding lifecycle status (open, in-progress, resolved, suppressed, accepted).
This is implemented as a `StatusIndicator` (see 3.1b) with the finding-specific
type mapping below — NOT as a colored dot + label hand-roll.

```tsx
<StatusBadge status="open" />          // StatusIndicator type="error"   label="Open"
<StatusBadge status="in_progress" />   // StatusIndicator type="warning" label="In progress"
<StatusBadge status="resolved" />      // StatusIndicator type="success" label="Resolved"
<StatusBadge status="suppressed" />    // StatusIndicator type="stopped" label="Suppressed"
<StatusBadge status="accepted_risk" /> // Custom "accepted" variant — purple CheckCircle2
                                       //   (type="accepted": icon CheckCircle2, color #7c3aed)

// Rules
// - ALWAYS icon + label — never a bare dot, never a bare label.
// - Labels are sentence case: "Open", "In progress", "Resolved", "Suppressed", "Accepted".
// - In a table cell, StatusBadge is the only content — no wrapping, no additional styling.
// - Suppressed findings render with text-secondary color AND strikethrough on the
//   parent row's title column (see Section 6 Pattern 17).
```

### 3.3 ProviderBadge

```tsx
<ProviderBadge provider="aws" />    // Provider-branded pill with AWS icon
<ProviderBadge provider="azure" />  // Provider-branded pill with Azure icon
<ProviderBadge provider="gcp" />    // Provider-branded pill with GCP icon
<ProviderBadge provider="oci" />    // Provider-branded pill with OCI icon

// Spec — Cloudscape Badge with tinted background
// Shape: inline-flex, border-radius var(--radius-badge) = 2px, padding 2px 6px
// Background: var(--{provider}-bg)
// Text: var(--{provider}), text-small (12px), weight 700
// Icon: 12px official provider SVG (not a color dot)
// Labels: "AWS", "Azure", "GCP", "OCI" (acronyms uppercase as proper nouns)
// Gap between icon and label: 4px (--space-xxs)
```

### 3.4 RiskScore

Displays a numeric risk score (0–100). In the AWS-native CloudVisor visual system the
score is rendered as a **labeled numeric KeyValuePair** inside a Container, not as a
circular gauge hero — this matches the AWS Console pattern for summary statistics.

```tsx
<RiskScore score={87} />                // Inline: colored number + "/100" suffix in text-secondary
<RiskScore score={87} size="large" />   // Large: font-size 32px, paired with a horizontal bar indicator
<RiskScore score={87} size="small" />   // Small: inline in a table cell

// Score → color mapping (uses existing severity tokens):
// 80–100: var(--critical)  — Critical risk
// 60–79:  var(--high)      — High risk
// 40–59:  var(--medium)    — Medium risk
// 20–39:  var(--low)       — Low risk
// 0–19:   var(--success)   — Low/passing

// Layout inside a summary Container:
//   <KeyValuePair label="Risk score">
//     <RiskScore score={87} size="large" />
//     <ProgressBar value={87} variant="flash" color={severityColor} />
//   </KeyValuePair>
//
// The ProgressBar below the number provides the visual weight — a 6px horizontal bar,
// full width of the KeyValuePair, filled to 87% in the severity color, with
// var(--border-default) as the track.
//
// Large format: number in font-mono, 32px, weight 700, colored by severity.
//               Below: a "Critical risk" StatusIndicator with the matching severity color.
// Small format: colored number (font-mono, 14px, weight 700) in a table cell.
// Inline format: same as small, but followed by " / 100" in text-secondary.
//
// NEVER show the score as a circular gauge hero. The KeyValuePair + ProgressBar
// pattern is the AWS-native way to surface a metric with a magnitude.
```

### 3.5 DataTable

The Cloudscape `Table` is the primary UI pattern for dense data. Every Findings,
Assets, Policies, Accounts list uses this component. It lives inside (or wraps as)
a Container and follows a very specific anatomy: **Header bar → Filter row → Table
body → Pagination**.

```tsx
interface DataTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  isLoading?: boolean;
  onRowClick?: (row: T) => void;
  selectable?: boolean;
  onSelectionChange?: (selected: T[]) => void;
  emptyState?: ReactNode;
  stickyHeader?: boolean;       // default true
  variant?: "container" | "embedded" | "borderless";
  header?: {
    title: string;              // e.g. "Findings"
    counter?: string;           // e.g. "(1,247)" — shown next to title in text-secondary
    description?: string;       // text-small below title
    actions?: ReactNode;        // right-aligned buttons: Export, Bulk actions, etc.
  };
  filter?: {
    textFilter?: boolean;       // full-text search input
    propertyFilter?: PropertyFilterProps;  // Cloudscape-style tokenized filter
  };
  pagination?: {
    currentPage: number;
    totalPages: number;
    onChange: (page: number) => void;
  };
  preferences?: {               // opens a right-drawer modal, AWS-style
    pageSize: number[];
    visibleColumns: string[];
    contentDensity: "comfortable" | "compact";
    wrapLines: boolean;
  };
}

// Anatomy (top to bottom inside the Container):
// 1. HEADER BAR (52px):
//    Left: title (text-h2) + counter in text-secondary weight 400 + optional description.
//    Right: primary action button + overflow "..." for secondary actions.
// 2. FILTER ROW (48px): full-width. Text-filter input (left, 240px) + PropertyFilter
//    tokens row. "Preferences" gear icon far right opens the preferences modal.
// 3. TABLE BODY:
//    - Header row: sticky, background var(--bg-elevated), text-small weight 600,
//      text-secondary, sentence-case column labels, 40px tall. Sortable columns show
//      chevron on hover + active chevron when sorted.
//    - Data rows: background transparent, border-bottom 1px var(--border-faint).
//      Height 40px (comfortable) / 32px (compact density). Hover: var(--bg-elevated).
//    - Selected row: background var(--accent-dim), NO colored left border
//      (Cloudscape selected state uses background tint only).
//    - Checkbox column (if selectable): 40px wide, checkbox at 8px radius.
//    - Clickable rows: entire row is the click target; cursor pointer on hover.
//      NO chevron-on-hover — in Cloudscape, clicking a row opens a Split panel below.
// 4. PAGINATION (48px): centered; "‹ 1 2 3 ... 10 ›" links, text-body, 32px tall.
//    Left of pagination: "Showing 1–50 of 1,247" in text-small text-secondary.
//
// Loading: skeleton rows that shimmer (opacity 0.5 → 1.0 → 0.5, 1.5s loop).
// Empty state: vertical stack — 32px icon, text-h3 title, text-body description,
//   primary action button. Centered in the table body area, min-height 320px.
// NO vertical column separators anywhere.
// Row click → opens the default Split panel at the bottom with row detail (see 3.8).
```

### 3.6 PropertyFilter (replaces FilterBar)

Cloudscape's **PropertyFilter** is the canonical filtering UI above every table. It
is a single tokenized input where users type property names and values as structured
tokens — this is the pattern used throughout the AWS Console (e.g., EC2 instance
filtering, CloudWatch log filtering).

```tsx
// Usage inside DataTable's filter prop:
<PropertyFilter
  query={query}
  onChange={setQuery}
  filteringProperties={[
    { key: 'severity', label: 'Severity', groupValues: ['CRITICAL','HIGH','MEDIUM','LOW','INFO'] },
    { key: 'status',   label: 'Status',   groupValues: ['open','in_progress','resolved','suppressed'] },
    { key: 'provider', label: 'Cloud',    groupValues: ['aws','azure','gcp','oci'] },
    { key: 'module',   label: 'Module',   groupValues: ['CSPM','CWPP','CDR','CIEM'] },
    { key: 'age',      label: 'Age (days)', operators: ['>', '<', '=', '!='] },
  ]}
  filteringOptions={/* dynamic values */}
  filteringPlaceholder="Filter findings"
/>

// Appearance:
// - Single input with a text filter on the left side and tokens that appear as
//   the user types property:operator:value (e.g., "severity = CRITICAL").
// - Each token: pill shape (radius-button = 20px), background var(--accent-light),
//   text var(--accent), dismiss "×" on right. Sentence-case labels.
// - Autocomplete dropdown opens as user types, grouped by property.
// - Active filters persist as tokens; "Clear filters" link at the end of the row.
// - Above the token row, a text-search input provides free-text matching across
//   all searchable fields.
//
// Row layout: single horizontal row below the DataTable header bar.
//   [🔍 Text filter input (240px)] [Property filter tokens (flex)] [Preferences ⚙]
//
// Rules
// - Do NOT use dropdown filters above the table (the v3 FilterBar pattern). The single
//   PropertyFilter replaces them.
// - The persistent left-sidebar filter pattern (v3 Pattern 6) is also RETIRED — it
//   is not how the AWS Console filters work.
// - Density, column-visibility, and page-size preferences live in a separate
//   "Preferences" modal opened by the gear icon.
```

### 3.7 MetricCard (Container + KeyValuePair)

The AWS Console surfaces key numbers using a Container with KeyValuePair content —
not a bordered colored "metric card." CloudVisor's `<MetricCard>` component composes
these primitives but keeps the Cloudscape look: subtle 1px border, no shadow, quiet
typography, no chromatic chrome around the number.

```tsx
interface MetricCardProps {
  label: string;           // e.g. "Critical findings"  (sentence case)
  value: number | string;  // e.g. 47
  trend?: {
    value: number;         // percentage change
    direction: 'up' | 'down' | 'flat';
    period: string;        // "vs. last 7 days"
    isPositive?: boolean;  // true = desirable direction (green), false = concerning (red)
  };
  description?: string;    // optional text-small below value
  color?: 'critical' | 'high' | 'medium' | 'low' | 'success' | 'accent' | 'neutral';
  onClick?: () => void;    // makes the whole Container clickable
  isLoading?: boolean;
}

// Design — Container with KeyValuePair:
// Wrapper: Container component (1px border var(--border-default), radius 16px, bg var(--bg-surface), NO shadow).
// Internal padding: --space-l = 20px.
// Content: KeyValuePair layout
//   - Label row: icon (16px, optional) + label (text-small, text-secondary, weight 600, sentence case)
//   - Value row: font-mono, 32px (text-display), weight 700, colored if `color` prop given
//     (default color: var(--text-primary) — Cloudscape defaults to neutral)
//   - Trend row (optional): StatusIndicator-style inline icon + text-small
//     · up + isPositive → green TrendingUp + "+12% vs. last 7 days"
//     · up + !isPositive → red TrendingUp (up is bad for finding counts)
//     · down + isPositive → green TrendingDown
//     · down + !isPositive → red TrendingDown
//     · flat → neutral Minus + "No change"
// Hover (if onClick): border-color becomes var(--accent), cursor pointer. NO scale transform.
// Loading: Cloudscape skeleton — gray pill placeholders for label and value.
```

### 3.8 SplitPanel (replaces DetailDrawer)

Cloudscape's **SplitPanel** is the canonical way to show a selected row's details
without leaving the list. It docks to the bottom of the content area by default
(user can switch to side-dock). Clicking a row opens the SplitPanel with that row's
summary; users keep the table visible above and can arrow through rows.

```tsx
interface SplitPanelProps {
  isOpen: boolean;
  onClose: () => void;
  header: string;                     // e.g., "S3 bucket — my-app-data"
  position?: 'bottom' | 'side';       // default: 'bottom'
  defaultSize?: number;               // px — bottom: 360, side: 320
  resizable?: boolean;                // default: true
  children: ReactNode;
  preferencesLabel?: string;
}

// Anatomy — bottom-docked (default):
// - Bar at the top: drag handle (horizontal grab), header title (text-h3),
//   "Dock to side" icon button, close "×" button. Height 44px.
// - Above the bar: --shadow-split elevates the panel off the table content.
// - Body: scrollable, padding --space-l = 20px. NO tabs inside the panel by default
//   (tabs live in the full Modal view — see 3.8b).
// - Typical content: KeyValuePair grid of key attributes, inline StatusIndicators,
//   relevant links.
// - Width: matches content area width minus side-nav and tools-panel.
// - Resize: user drags the top bar vertically to resize; range 200–640px.
// Animation: slide-up from bottom, --duration-slow (240ms), --ease-entrance.
// Keyboard: Escape closes. Arrow keys Up/Down move selection in the table above
// and update the SplitPanel content.
// Dark mode: bg var(--bg-surface), border-top 1px var(--border-default).
```

### 3.8b FullPageModal (for deep triage)

Used when the user clicks "Open full details" from a SplitPanel, or when navigating
directly to `/findings/{id}`. This is a Cloudscape Modal — **80vw × 90vh**, with
tabs inside for Overview / Audit trail / Evidence / Remediation.

```tsx
// Modal spec:
// Backdrop: rgba(0,0,0,0.5), NO blur (Cloudscape uses a flat backdrop).
// Modal: bg var(--bg-surface), radius var(--radius-container) = 16px,
//        box-shadow var(--shadow-modal).
// Header: 56px, title (text-h2) + close "×" on right. Border-bottom.
// Tabs: horizontal bar below header, 44px, active tab = 2px bottom accent border.
// Body: scrollable, padding --space-xl (24px).
// Footer (optional): 56px, border-top, right-aligned button stack
//   (primary + normal, 8px gap).
// Animation: fade backdrop + scale content 0.96 → 1.0, --duration-slow.
// Focus trap: Tab/Shift+Tab stays within the modal.
// Close on: backdrop click (if not destructive), Escape key, "×" button.
```

### 3.9 ResourceSearch (global search modal)

A Cloudscape-style global search overlay — opened with **⌘K** (Mac) or **Ctrl+K**
(Windows) or by clicking the search input in the top navigation. Matches the AWS
Console resource-lookup pattern: typed input, grouped results, keyboard navigation.

```tsx
// Opens with Cmd+K / Ctrl+K, or click on the top-nav search input
// Overlay: Modal-shaped (radius 16px, --shadow-modal), 640px wide × auto height,
//          centered near top of viewport (top: 96px)
// Backdrop: rgba(0,0,0,0.4)
// Header: search input (40px, radius 8px, 1px border), autofocus
//         placeholder "Search findings, assets, policies, accounts, or pages"
// Results: grouped by type — "Findings", "Assets", "Policies", "Accounts", "Pages", "Actions"
//   - Group header: text-small weight 600, text-secondary, sentence case
//   - Result row: 40px tall, icon (16px) + title (text-body) + subtitle (text-small, text-secondary)
//     + optional right-side keyboard hint (text-xsmall, in a bordered pill)
//   - Active row: bg var(--bg-elevated), NO accent tint
// Keyboard: ↑/↓ move, Enter selects, Esc closes
// No borders between rows — just hover/active background.
// Empty state: "No results for '<query>'. Try…" with 3 suggested starter searches.

// Actions available (last group "Actions"):
//   - "Go to Dashboard"
//   - "Open Findings (Critical)"
//   - "Trigger scan on <account>"
//   - "Generate compliance report (SOC 2)"
//   - "Connect new cloud account"
//   - Recent findings (last 5 viewed)
```

### 3.10 ComplianceBar (Cloudscape ProgressBar)

Rendered as a Cloudscape `ProgressBar` with a labeled KeyValuePair wrapper — used on
the compliance page and inside KPI Containers.

```tsx
<ComplianceBar framework="SOC 2" percentage={78} total={115} passing={89} />

// Anatomy (top to bottom):
// - Label row: framework name (text-body-bold, weight 700) on left,
//              percentage on right (font-mono, text-body, weight 700, severity-colored)
// - Progress track: full width, 4px tall, radius 2px
//     Background: var(--border-default)
//     Fill: colored by percentage
//       ≥ 80% → var(--success)
//       60–79% → var(--warning)
//       < 60% → var(--danger)
//     Animated on mount: width 0 → target, 240ms --ease-entrance
// - Subtext (text-small, text-secondary): "89 of 115 controls passing"
// - Optional "ⓘ Info" link after the framework name opens Tools panel with details.
```

### 3.11 AttackPathGraph

Interactive graph visualization for attack paths and resource relationships — used
in the Aiops / Assets pages and inside a Finding's detail. Rendered inside a
Container, never full-bleed.

```tsx
// Library: React Flow (reactflow)
// Wrapper: Container with header "Attack path" + actions (Fit-to-view, Export PNG, Reset).
//          Graph surface fills the Container body; min-height 480px.
// Background: var(--bg-base), NO dot grid (Cloudscape keeps backgrounds plain).
// Nodes: Cloudscape-style — rounded rectangles (radius 8px), 1px border var(--border-default),
//        bg var(--bg-surface), padding --space-s. Icon (20px provider SVG) + text-body label
//        + text-small secondary label (resource type).
// Node risk indicator: left-side 3px colored bar (tight integration with severity tokens)
//        — var(--critical) for exposed entry points, var(--high) for intermediate, etc.
// Edges: 1.5px stroke, rounded, var(--border-strong) for neutral, var(--danger) for risk
//        edges (e.g., PUBLIC_ACCESS). Arrowheads at 70% along the path.
// Interaction:
//   - Pan: click-drag the background
//   - Zoom: scroll wheel / pinch; zoom level displayed in bottom-left corner pill
//   - Click node: focus the node (var(--accent) ring), highlight first-degree
//     neighbors, dim everything else to 30% opacity
//   - Hover edge: show inline tooltip (Cloudscape Tooltip, radius 8px, --shadow-popover)
//     with the relationship type label
// Controls (bottom-left): zoom +/−, fit-to-view, lock/unlock layout
// Legend (top-right): collapsible Container — node color meanings + edge types
// Mini-map (bottom-right): Cloudscape-style, 160×120px, same 1px border as Containers
```

### 3.12 NotificationToast (transient only)

Cloudscape distinguishes **Flashbar** (page-level persistent status — see 3.13) from
**transient toasts** (ephemeral acknowledgments like "Link copied"). CloudVisor
follows this distinction strictly.

```tsx
// Library: Sonner (bottom-right, stacked)
// Position: bottom-right, 16px from edges, stack spacing --space-s
// Use ONLY for transient, dismissible feedback with no persistent business impact:
//   "Link copied"
//   "Finding ID copied to clipboard"
//   "Preferences saved"
//   "Filter saved as favorite"
// Use Flashbar (3.13) for everything else — scan results, finding status changes,
// errors that require user action, long-running jobs.

// Design — Cloudscape-aligned:
// Background: var(--bg-overlay), 1px border var(--border-default),
//             radius var(--radius-item) = 12px, --shadow-toast
// Max width: 360px, padding --space-m = 16px
// Left: 16px StatusIndicator icon (success/error/info)
// Middle: text-body title (weight 600) + optional text-small description
// Right: close "×" icon button (shows on hover)
// Types: success / error / warning / info — colors via StatusIndicator
// Auto-dismiss: success/info 4s, warning 6s, error stays until dismissed
```

### 3.13 Flashbar (new — page-level status)

The Cloudscape **Flashbar** is the canonical surface for page-level operational
status. It sits directly below the breadcrumbs and above the page title, spans the
content area width, and stacks when there are multiple active messages.

```tsx
<Flashbar items={[
  {
    type: 'success',
    header: 'Scan completed',
    content: 'AWS Production scanned — 47 new findings detected.',
    action: <Button variant="normal">View findings</Button>,
    dismissible: true,
    onDismiss: () => {},
  },
  {
    type: 'error',
    header: 'Azure connector failed',
    content: 'Authentication error — credentials expired.',
    action: <Button variant="normal">Fix credentials</Button>,
    dismissible: true,
  },
  {
    type: 'in-progress',
    header: 'Scan in progress',
    content: 'AWS Production — 24,847 of 42,000 resources scanned.',
    loading: true,
  },
]} />

// Spec — per Cloudscape Flashbar:
// Wrapper: vertical stack, gap --space-s between items, full content-area width
// Item: 1px border + bg tint in the type's color family
//       Success: border var(--success), bg var(--success-bg)
//       Error:   border var(--danger),  bg var(--critical-bg)
//       Warning: border var(--warning), bg var(--medium-bg)
//       Info:    border var(--accent),  bg var(--accent-light)
//       In-progress: border var(--accent), bg var(--accent-light), shows inline spinner
// Radius: var(--radius-alert) = 12px
// Layout: 16px icon (StatusIndicator-style, matching type) + header (text-body-bold)
//         + content (text-body) + optional action button + dismiss "×"
// Min-height: 44px; grows with content
// Animation on add: slide-in from top (translateY -8px → 0) + fade, 165ms
// Animation on dismiss: collapse height + fade, 165ms
// Limit: max 5 items visible; older in-progress / info auto-dismiss after the task.
```

### 3.14 Container (new — Cloudscape primitive)

The Container is the base wrapper for nearly every content block. Title + actions
header on top, body below, optional footer. 1px border, NO shadow.

```tsx
<Container
  header={
    <Header
      variant="h2"
      counter="(47)"
      description="Findings detected in the last 24 hours"
      actions={<SpaceBetween direction="horizontal" size="xs">
        <Button variant="normal">Export</Button>
        <Button variant="primary">Run scan</Button>
      </SpaceBetween>}
    >
      Recent findings
    </Header>
  }
  footer="Last scan completed 4 minutes ago"
>
  {/* body content */}
</Container>

// Spec:
// Background: var(--bg-surface)
// Border: 1px solid var(--border-default)
// Radius: var(--radius-container) = 16px
// Shadow: NONE (Cloudscape Visual Refresh replaced shadows with strokes)
// Header: 52px tall, padding --space-l horizontal, border-bottom 1px var(--border-faint)
//   Left: title (text-h2) + optional counter (text-body, weight 400, text-secondary)
//         + optional description (text-small, below title)
//   Right: actions (SpaceBetween horizontal with Buttons)
// Body: padding --space-l (20px) vertical, --space-l horizontal
// Footer (optional): border-top 1px var(--border-faint), padding --space-m, text-small text-secondary

// Variants:
//   default   — standard 1px border
//   stacked   — vertical stack of containers; 0 gap; shared borders
//   embedded  — no border, no radius (used inside another Container)
```

---

## 4. UX Patterns

These are the interaction rules for the entire platform. Every page must follow them.

### 4.1 Navigation structure — Cloudscape AppLayout

CloudVisor uses **Cloudscape's AppLayout** — the canonical page shell for the AWS
Management Console. It has six parts:

1. **Top navigation** (dark bar across the full width, ~40px)
2. **Side navigation** (light panel on the left, ~280px, collapsible)
3. **Breadcrumbs** (below top nav, above page title)
4. **Content area** (center, max-width 1440px)
5. **Tools panel** (right, ~290px, hidden by default, opens on "ⓘ Info" click)
6. **Split panel** (bottom-docked by default, 360px, opens on row click)

```
┌─ Top navigation (dark, var(--bg-sidebar), 40px, full width) ──────────────────────────┐
│  [CloudVisor ▼]    [🔍 Search or type to filter... (center, 480px)]    [Account ▼] [Region ▼] [🔔] [⚙] [Avatar ▼] │
└───────────────────────────────────────────────────────────────────────────────────────┘
┌────────────────┬──────────────────────────────────────────────────────────┬──────────┐
│                │ Home / Findings / S3 bucket public...  ← breadcrumbs      │          │
│ SIDE           ├──────────────────────────────────────────────────────────┤ TOOLS    │
│ NAVIGATION     │ [Flashbar messages, if any]                               │ PANEL    │
│ (light, 280px) ├──────────────────────────────────────────────────────────┤ (right,  │
│                │                                                            │  290px,  │
│ ▾ Overview     │ Page title (text-h1)     [normal-btn] [primary-btn]       │  hidden  │
│   Dashboard    │ Optional description text-body text-secondary              │  by      │
│   Risk map     │                                                            │  default)│
│                │ <Container>                                                │          │
│ ▾ Cloud        │   <Table header>                                           │          │
│   security     │   <PropertyFilter>                                         │          │
│   Findings [47]│   <table rows ...>                                         │          │
│   Incidents[2] │   <pagination>                                             │          │
│   Assets       │ </Container>                                               │          │
│   Compliance   │                                                            │          │
│                │                                                            │          │
│ ▾ Protection   │                                                            │          │
│   CSPM     [31]│                                                            │          │
│   CWPP     [12]│                                                            │          │
│   Identity     │                                                            │          │
│   Kubernetes   ├──────────────────────────────────────────────────────────┤          │
│   Data         │ SPLIT PANEL (bottom-docked, resizable, opens on row click) │          │
│   CI/CD        │ [drag handle]  S3 bucket — my-app-data        [↗ Open] [×]│          │
│   Detection[2] │ KeyValuePair grid: Severity, Status, Resource, Region...   │          │
│                │                                                            │          │
│ ▾ Intelligence │                                                            │          │
│   Aiops        │                                                            │          │
│   Copilot [NEW]│                                                            │          │
│                │                                                            │          │
│ ─────────────  │                                                            │          │
│ ▾ Settings     │                                                            │          │
│   Accounts     │                                                            │          │
│   Notifications│                                                            │          │
│   Team         │                                                            │          │
│   API keys     │                                                            │          │
│   Billing      │                                                            │          │
│                │                                                            │          │
└────────────────┴──────────────────────────────────────────────────────────┴──────────┘

TOP NAVIGATION rules:
- Background: var(--bg-sidebar) (dark brand navy in both light and dark modes)
- Height: 40px
- Text color: var(--text-on-sidebar) for links; var(--text-inverse) for brand
- Product identity: left — CloudVisor wordmark, click for product menu
- Global search: center, 480px max, 32px tall, bg rgba(255,255,255,0.10),
  radius var(--radius-input) = 8px, placeholder text var(--text-on-sidebar)
- Utility menu (right, right-to-left): Account switcher, Region scope, Notifications
  bell, Settings gear, User avatar — each opens a Cloudscape-style dropdown
  (radius 16px, --shadow-dropdown, light bg)
- Hover: bg var(--bg-sidebar-hover); Active (dropdown open): bg var(--bg-sidebar-active)

SIDE NAVIGATION rules:
- Background: var(--bg-sidenav) — LIGHT in light mode (white), dark in dark mode.
  NEVER the same navy as the top nav — this difference is the AWS signature.
- Width: 280px expanded, 36px collapsed (icon-only rail)
- Border-right: 1px var(--border-default)
- Group headers: text-body-bold (14px, weight 700), text-primary, sentence case
  (NOT uppercase — Cloudscape uses sentence case). Padding 8px 16px.
  Expand/collapse chevron (ChevronDown / ChevronRight) on the right.
- Nav items: 36px tall, text-body (14px, weight 400), text-primary
  Padding: 8px 16px 8px 40px (extra left padding to indent under group)
  Icons: optional, 16px, 8px gap to label
- Hover: bg var(--bg-sidenav-hover)
- Active item: bg var(--bg-sidenav-active), left border 2px var(--accent),
  text weight 600
- Count badge (e.g., "[47]"): right-aligned, text-small, text-secondary,
  bg var(--critical-dim) + text var(--critical) for critical counts
- Collapse toggle: "‹" icon in the footer of the side nav (36px tall footer row)
- Section divider: 1px var(--border-faint), 8px vertical margin
- "[NEW]" tag: inline after the label, Badge component with accent-light bg
  + accent text, radius var(--radius-badge)

BREADCRUMBS rules (Cloudscape BreadcrumbGroup):
- Height: 40px
- Padding: 0 --space-xl (24px)
- Items: text-small, text-primary, separated by "/" in text-tertiary
- Last item (current page): text-small, weight 700, no link
- Hover on earlier items: underline
- Always present on every interior page (NEVER on the dashboard root)

CONTENT AREA rules:
- Background: var(--bg-base)
- Max width: 1440px, centered; horizontal padding --space-xl on desktop,
  --space-l on laptop, --space-m on mobile
- Top padding: --space-xl (24px) below breadcrumbs
- Vertical gap between sections: --space-xl (24px)

TOOLS PANEL (right) rules:
- Width: 290px when open; 0 when closed
- Background: var(--bg-surface)
- Border-left: 1px var(--border-default)
- Opens when the user clicks an inline "ⓘ Info" link in the page
- Header: 44px — title ("Info") + close "×"
- Body: scrollable, padding --space-l, contains help markdown / inline docs
- NEVER render fully-interactive forms here — it is contextual reading material

SPLIT PANEL (bottom) rules:
- Covered in component spec 3.8
- Opens when a table row is clicked
- Bottom-docked by default; user can re-dock to right side
```

### 4.2 Page layout structure

```
Every interior page follows this exact structure (inside AppLayout's content area):

┌─ Breadcrumbs (40px) ────────────────────────────────────────────┐
│ Home / Findings                                                  │
├─────────────────────────────────────────────────────────────────┤
│ Flashbar (optional, stacks, only if active messages)             │
├─────────────────────────────────────────────────────────────────┤
│ Page header (auto height, --space-xl top margin)                 │
│ [Page title — text-h1]                 [normal-btn] [primary-btn]│
│ Optional description — text-body text-secondary                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ Page content — Container(s), stacked with --space-xl gap          │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

Page header rules:
- Title: text-h1 (24px, weight 700), text-primary
- Description: text-body, text-secondary (what this page is for, links to docs)
- Actions (right-aligned): at most 2 buttons — a secondary "normal" button on the
  left of the pair, a "primary" button on the right. Use a ButtonDropdown for 3+ actions.
- Info link ("ⓘ Info"): appears inline after the title (or beside it, separated by
  --space-xs); opens the Tools panel on click
- NO context bar — Cloudscape does not use a separate account/date-range strip below
  the title. Account scope lives in the top navigation; date range lives inside the
  specific Container's header where it applies.

Content composition:
- Use Containers to group related content. A simple page = one Container.
  A complex page = a SpaceBetween(direction="vertical", size="l") of Containers.
- Never put raw tables, raw charts, or raw form fields directly on the page bg —
  always wrap them in a Container.
- Never stack content to a depth of more than 2 Containers nested
  (Cloudscape's Visual Refresh explicitly flattens visual hierarchy).
```

### 4.3 Data loading states

Every component that fetches data must handle these 4 states. Cloudscape treats
loading, empty, error, and stale as first-class UX concerns — the happy path is
never enough.

```
1. Loading:  Cloudscape skeleton placeholders — not spinners
             Skeleton shapes match the real content (rows for tables, bars for charts)
             Pulse animation: opacity 0.5 → 1.0 → 0.5, 1.5s infinite
             For a submitting button: inline Loader2 (spinning) + "Loading" label

2. Empty:    Centered stack inside the Container body (min-height 320px):
               - 32px icon (Lucide), text-tertiary
               - text-h3 title  (e.g. "No critical findings")
               - text-body text-secondary description (one sentence)
               - Primary button (if applicable — e.g. "Connect cloud account")
             Empty ≠ error: use neutral, calm wording. No illustrations with
             marketing copy.

3. Error:    Flashbar item at the top of the content area (type: "error")
               header: "Couldn't load findings"
               content: short description + correlation_id in font-mono
               action: <Button variant="normal">Retry</Button>
             Inside the affected Container, show an inline error state:
               icon (AlertTriangle) + "Data unavailable" + "Try again" link.
             Never block the whole page on a partial error — other Containers
             keep rendering.

4. Stale:    Flashbar item (type: "warning", dismissible: false)
               header: "Data is X minutes old"
               content: "Automatic refresh paused — last synced at HH:MM"
               action: <Button variant="normal">Refresh now</Button>
             Also show a subtle indicator inside the Container header:
               a Clock icon + "Updated 18 min ago" in text-small text-secondary.
             Never silently show stale data without surfacing it.
```

### 4.4 Finding triage flow (most important UX flow)

This is the primary workflow of every Security Engineer. Optimize every click.

```
Entry points → Findings table → Row click → Split panel (bottom) → "Open full"  → Full-page modal

Split panel (bottom, 360px) shows the quick triage view:
1. Header: finding title + SeverityBadge + StatusBadge + age (text-small text-secondary)
2. Actions row — SpaceBetween(horizontal, xs):
   [Mark in progress] [Suppress] [Accept risk] [Assign] [Open full ↗]
3. KeyValuePair grid (2 columns):
   - Resource: name + ProviderBadge + resource-type icon  (link → /assets/{id})
   - Account: account name + provider dot
   - Region: region code
   - Module: CSPM / CWPP / CDR etc.
   - Compliance: affected framework pills (SOC 2, CIS AWS, PCI-DSS)
   - Priority score: RiskScore (small, inline)
4. Impact statement — Alert component (type="warning", dismissible=false):
   "This S3 bucket is publicly readable — anyone on the internet can download
    all objects without authentication. Contains files tagged 'customer-data'."
5. "Open full details" link at the bottom opens the FullPageModal (3.8b)

Full-page modal (80vw × 90vh) is the deep triage surface, with tabs:
  [Overview] [Audit trail] [Evidence] [Remediation]

Overview tab:
  - Same KeyValuePair grid as the split panel, but with more fields
  - Impact statement (Alert component, warning type)
  - AI explanation (if Aiops available) — separate Container, header "AI explanation"
  - Related findings on the same resource (embedded Table)

Audit trail tab:
  - Vertical timeline — each entry is a Container (variant="stacked") with:
      StatusIndicator + actor avatar + text-body description + timestamp (text-small)
  - Newest at top; oldest at bottom

Evidence tab:
  - Raw resource configuration that triggered the policy
  - JSON viewer with syntax highlighting (font-mono, text-small)
  - Copy-to-clipboard button (icon Copy, 16px) in top-right of the code block
  - "View in provider console ↗" link (opens AWS/Azure/GCP console in new tab)

Remediation tab:
  - Step-by-step numbered instructions (ordered list, text-body)
  - Each command/snippet in a code block with copy button
  - "Apply automatic fix" primary button (if Aiops can generate a PR)
  - "Open as pull request" secondary button
  - Runbook link (if the policy has an associated internal runbook)

Keyboard shortcuts in findings table:
  j / k         — move selection up/down
  Enter / Space — open Split panel for selected row
  o             — open Full-page modal for selected finding
  s             — suppress selected finding
  a             — assign selected finding
  r             — mark as resolved
  Escape        — close Split panel / close Modal / deselect

On every action, status confirmation appears as a Flashbar at the top of the page
(NOT a toast) — "Finding suppressed. 1 finding removed from view. [Undo]"
```

### 4.5 Global account/scope selector

```
Lives in the TOP NAVIGATION (right utility area), NOT in a context bar below the header.
This matches the AWS Console's region/account switcher pattern.

Component: Cloudscape ButtonDropdown in the top-nav utility area.
Button label: "All accounts" | "<account-name>" | "<environment-tag>"
Button icon: small cloud icon (Cloud from Lucide) + dropdown chevron

Dropdown content (on open):
  - "Scope" section header
  - Radio-group options: "All accounts", "By cloud", "By environment", "Specific account"
  - Below: searchable list of accounts (with provider icon + name + status dot)
  - Footer: "Manage accounts" link → /settings/connectors

On change: all data-fetching queries re-fetch scoped to the new selection
Persistence: selection saved to localStorage; restored on next session
```

### 4.6 Time range selector

```
Used on trend charts, detection feeds, and any Container whose data is time-bounded.
Component: Cloudscape SegmentedControl (not a dropdown for the presets).

Lives in the Container header (right side), next to the Container's actions.
Options: "1h" | "24h" | "7d" | "30d" | "90d" | "Custom ▾"
Default: "7d" on most pages; "24h" on CDR live feed.
"Custom" opens a Cloudscape DateRangePicker in a popover.

Spec:
  Height: 32px (matches buttons)
  Radius: var(--radius-button) = 20px  (pill, like buttons)
  Segments: 32px tall each, text-small, weight 600
  Active segment: bg var(--accent), text var(--text-inverse)
  Inactive: bg transparent, text var(--text-secondary), hover bg var(--bg-elevated)
  Border: 1px var(--border-default) around the whole control
```

### 4.7 Bulk actions pattern

```
Follows the Cloudscape Table bulk-selection pattern.

When rows are selected in any DataTable:
1. The Table header bar updates:
   - Title changes to "<N> selected" (replaces the title + counter)
   - "Deselect all" link appears on the right of the title
2. Primary action area transforms into a bulk-action row:
   Available actions as Buttons (variant="normal"): Assign · Suppress · Change status · Export
   Plus a ButtonDropdown for less-common actions.
3. Checkbox column stays visible in each row.
4. A subtle top-border accent (2px var(--accent)) appears on the Table header bar
   to signal selection mode.
5. Destructive bulk actions (>10 items) open a confirmation Modal with:
   - Title: "Suppress 47 findings?"
   - Body: list of up to 5 affected items + "…and 42 more"
   - Required reason textarea (min 20 chars, same pattern as single-action)
   - Footer: [Cancel] [Suppress findings] (primary button disabled until reason valid)
6. During execution: primary button shows inline Loader2 + "Processing" label,
   all inputs disabled.
7. Result: Flashbar at top of page — "47 findings suppressed. [Undo]"
   (success type; auto-dismisses after 8s unless undone)
```

### 4.8 Real-time updates

```
New findings and alerts appear without page refresh.
Implementation: WebSocket connection to the backend event stream.

Visual indicators:
- NEW FINDING (table row) — row slides in at top of table with a brief
  bg tint of var(--accent-light) fading out over 1.5s (matches Cloudscape's
  "new row highlight" pattern).
- SIDE NAV COUNT — badge increments with a 165ms opacity flash. Avoid
  counting up animation; Cloudscape shows final values immediately.
- METRIC CARD — value updates with a crossfade (opacity 0 → 1, 165ms);
  NO count-up animation.
- FLASHBAR — for newly-arrived critical findings, a stacked Flashbar item
  appears at the top of the page:
    type: "warning", dismissible: true
    header: "3 new critical findings"
    content: "Detected in AWS Production in the last minute."
    action: <Button variant="normal">View findings</Button>

Connection status:
- Live indicator lives in the TOP NAVIGATION utility area — a small
  StatusIndicator (type="success", label="Live") when connected.
- Reconnecting: StatusIndicator(type="loading", label="Reconnecting").
- Disconnected: Flashbar (type="warning", dismissible: false)
    "Live updates paused" + content "Last update N minutes ago"
    action: [Retry now]
```

---

## 5. Page Specifications

Every page is specified here with exact layout, components, and data requirements.
Build pages in the order listed — each builds on components from the previous.

---

### Page 1: Dashboard `/dashboard`

**Purpose:** First page after login. Must communicate the security posture story
in under 10 seconds. Designed for the CISO who has 2 minutes and the Security
Engineer who uses this as their daily starting point.

**Layout:** No breadcrumbs on `/dashboard` (it is the root of authenticated content).
Page header + a vertical stack of Containers. No circular gauge hero, no widget-grid
— just Cloudscape Containers with clear purpose.

```
(no breadcrumbs on root dashboard)
┌─ Flashbar (if any page-level events) ─────────────────────────────┐
└────────────────────────────────────────────────────────────────────┘

┌─ Page header (no Container wrapper) ──────────────────────────────┐
│ Security overview                              [Refresh] [Run scan]│
│ Last scanned 4 min ago · 42,847 resources evaluated                │
└────────────────────────────────────────────────────────────────────┘

┌─ Container: "Posture at a glance" ────────────────────────────────┐
│ Header: "Posture at a glance"                       right: [ⓘ Info]│
│ Body: ColumnLayout columns={5}                                      │
│  [MetricCard Posture  72 · bar: 72%]                                │
│  [MetricCard Critical 47 · ↑12% vs. 7d (concern/red arrow)]         │
│  [MetricCard High    183 · ↓8%  vs. 7d (good/green arrow)]          │
│  [MetricCard Accounts 12 · 4 providers connected]                   │
│  [MetricCard SOC 2  78%  · ↑3% vs. 30d (good/green arrow)]          │
└────────────────────────────────────────────────────────────────────┘

┌─ Container: "Findings trend" (Grid col 8) ─┬─ Container: "Top risks" (col 4) ─┐
│ Header: "Findings trend"                    │ Header: "Top 5 riskiest assets"   │
│   right: SegmentedControl 7d · 30d · 90d    │   right: [View all ↗]             │
│                                              │                                   │
│ [Area chart, stacked by severity, 240px     │ [Embedded Table: 5 rows]          │
│  tall, animates on mount]                   │   Resource · RiskScore · Findings │
│                                              │   (row click → Split panel)       │
└──────────────────────────────────────────────┴───────────────────────────────────┘

┌─ Container: "Compliance" (col 6) ──────────┬─ Container: "Activity" (col 6) ──┐
│ Header: "Compliance by framework"            │ Header: "Recent activity"         │
│   right: [View all ↗]                        │   right: SegmentedControl 24h·7d  │
│                                              │                                   │
│ ColumnLayout columns={1}:                    │ Vertical list of activity rows:   │
│   ComplianceBar SOC 2     78%                │   StatusIndicator + actor         │
│   ComplianceBar CIS AWS   64%                │     + description (text-body)     │
│   ComplianceBar PCI-DSS   43%                │     + timestamp (text-small)      │
│   ComplianceBar HIPAA     71%                │ (row dividers 1px border-faint)   │
└──────────────────────────────────────────────┴───────────────────────────────────┘

┌─ Container: "Protection modules" ─────────────────────────────────┐
│ Header: "Protection modules"                   right: [Configure ↗]│
│ Body: ColumnLayout columns={6}                                      │
│   For each module (CSPM, CWPP, CI/CD, CIEM, KSPM, CDR):             │
│     Embedded Container (no outer border) with:                      │
│       · Module name (text-h5)                                       │
│       · Critical count (font-mono 24px, weight 700)                 │
│       · Last-scan timestamp (text-small text-secondary)             │
│       · StatusIndicator (scan status: success/in-progress/warning)  │
│     Whole tile is clickable → navigates to that module's page.      │
└────────────────────────────────────────────────────────────────────┘
```

**API calls this page makes:**
```
GET /v1/posture/score              — overall posture score + trend
GET /v1/findings/stats             — counts by severity, trend vs previous period
GET /v1/accounts?status=active     — connected accounts count
GET /v1/compliance/summary         — compliance percentage per framework
GET /v1/findings/trends?days=30    — time series data for area chart
GET /v1/assets/top-risks?limit=5   — top riskiest assets
GET /v1/activity?limit=20          — recent activity feed
GET /v1/modules/summary            — per-module finding counts + last scan
```

**Key interactions:**
- Click posture score Container → `/cspm` (CSPM module)
- Click critical findings Container → `/findings?filter[severity]=CRITICAL`
- Click compliance framework → `/compliance/{framework}`
- Click riskiest asset row → opens the bottom-docked SplitPanel with asset summary
- Click "Run scan" → triggers scan, Flashbar (type="in-progress") appears with
  live progress percentage; on completion switches to type="success"

---

### Page 2: Findings `/findings`

**Purpose:** The primary daily-use page for Security Engineers and SOC Analysts.
This is where 80% of their time is spent. Every interaction must be fast and keyboard-friendly.

**Layout:**

```
Home / Findings                                      ← breadcrumbs (40px)

┌─ Flashbar (if any page-level events) ─────────────────────────────────┐
└───────────────────────────────────────────────────────────────────────┘

┌─ Page header ─────────────────────────────────────────────────────────┐
│ Findings                                  [Export ↓] [Bulk actions ▼] │
│ 1,247 total in the current scope                                       │
└───────────────────────────────────────────────────────────────────────┘

┌─ Container wrapping the Table ────────────────────────────────────────┐
│ Table header bar:                                                      │
│   "Findings (1,247)"                      [Preferences ⚙]              │
│   Severity filter tabs — Tabs component:                               │
│   [ All 1,247 ] [ CRITICAL 47 ] [ HIGH 183 ] [ MEDIUM 691 ] [ LOW 326 ]│
│                                                                        │
│ Filter row:                                                            │
│   [🔍 text-filter (240px)]  [PropertyFilter tokens... flex]  [⚙]      │
│   Active tokens: severity = CRITICAL × · status = open ×               │
│                                                                        │
│ Table body (40px rows, sortable headers):                              │
│   ☐  Severity     Title                Resource     Age  Status        │
│   ────────────────────────────────────────────────────────────────     │
│   ☐  [CRITICAL]   S3 bucket public...  my-app-data  2d   ● Open        │
│   ☐  [CRITICAL]   IAM root MFA…        AWS/prod     5d   ● Open        │
│   ☐  [HIGH]       RDS publicly expo…   payments-db  1d   ● Open        │
│                                                                        │
│ Pagination:                                                            │
│   Showing 1–50 of 1,247        ‹  1  2  3  ...  25  ›                 │
└───────────────────────────────────────────────────────────────────────┘

┌─ SplitPanel (bottom, opens on row click, 360px tall) ─────────────────┐
│ [drag handle] S3 bucket — my-app-data      [↗ Open full] [Dock ⇥] [×] │
│ KeyValuePair grid + Impact Alert + quick actions (see 4.4)             │
└───────────────────────────────────────────────────────────────────────┘
```

**Table columns:**

| Column | Width | Content |
|---|---|---|
| Checkbox | 40px | Multi-select |
| Severity | 100px | SeverityBadge component |
| Title | flexible | Finding title, truncated, full on hover |
| Resource | 200px | Resource name + type icon |
| Account | 120px | ProviderBadge + account name |
| Module | 80px | CSPM / CWPP / CDR etc. |
| Age | 80px | "2d", "5h", "12m" (relative) |
| Status | 110px | StatusBadge |
| Assignee | 32px | Avatar only (tooltip with name) |
| Actions | 40px | … button: suppress, assign, resolve |

**Finding detail (SplitPanel — opens at bottom on row click):**

Full spec defined in Section 4.4. Default dock: bottom, 360px tall.
Clicking "Open full ↗" in the split panel header opens the FullPageModal
(80vw × 90vh) with the four tabs: Overview, Audit trail, Evidence, Remediation.

**API calls:**
```
GET /v1/findings?filter[severity]=CRITICAL&filter[status]=open&sort=-priority_score
GET /v1/findings/{id}     — on row click, for full detail
```

---

### Page 3: Assets `/assets`

**Purpose:** Complete inventory of all cloud resources. Used to understand the
attack surface, find specific resources, and see resource-level risk.

**Layout:**

```
Home / Assets                                        ← breadcrumbs

┌─ Page header ─────────────────────────────────────────────────────┐
│ Asset inventory                              [Export ↓] [⚙]       │
│ 48,291 resources across 4 providers                                │
└───────────────────────────────────────────────────────────────────┘

┌─ Container: "By provider" (compact summary) ──────────────────────┐
│ Header: "By provider"                                              │
│ ColumnLayout columns={4}                                           │
│   [ProviderBadge AWS 31,402] [ProviderBadge Azure 9,847]           │
│   [ProviderBadge GCP 5,821]  [ProviderBadge OCI 1,221]             │
│ Below (text-small, text-secondary):                                │
│   EC2: 4,201 · S3: 2,847 · IAM: 8,991 · RDS: 441 · Lambda: 1,204  │
└───────────────────────────────────────────────────────────────────┘

┌─ Container wrapping view toggle + Table or Graph ─────────────────┐
│ Header: "Resources"                                                │
│   right: SegmentedControl [Table] [Graph]   [Preferences ⚙]       │
│                                                                    │
│ Filter row:                                                        │
│   [🔍 text filter]  [PropertyFilter: provider, type, region, tags]│
│                                                                    │
│ ── TABLE VIEW ───────────────────────────────────────────────────  │
│   Name           Type         Provider  Region     Risk  Findings  │
│   my-app-bucket  S3 bucket    [AWS]     us-east-1  87    12        │
│   payments-db    RDS instance [AWS]     eu-west-1  94    3         │
│   ...                                                              │
│                                                                    │
│ ── GRAPH VIEW ───────────────────────────────────────────────────  │
│   AttackPathGraph (see 3.11), filling the Container body           │
│   Nodes: cloud resources, left-bar colored by risk score           │
│   Edges: relationships (HAS_ACCESS_TO, CONNECTS_TO, etc.)          │
│   Click node → SplitPanel (bottom) with resource detail            │
└───────────────────────────────────────────────────────────────────┘
```

---

### Page 4: Compliance `/compliance`

**Purpose:** Compliance officers and CISOs need this page. It answers
"Are we compliant with SOC 2?" with evidence, not just percentages.

**Layout:**

```
┌─ Page Header ──────────────────────────────────────────────────────┐
│ Compliance                                 [Generate Report PDF ↓] │
└────────────────────────────────────────────────────────────────────┘

┌─ Framework selector tabs ──────────────────────────────────────────┐
│ [CIS AWS] [CIS Azure] [CIS GCP] [SOC 2] [PCI-DSS] [HIPAA] [NIST] │
└────────────────────────────────────────────────────────────────────┘

── SOC 2 selected ───────────────────────────────────────────────────

┌─ Summary ──────────────────────────────────────────────────────────┐
│  78% compliant    89 passing    25 failing    1 not applicable     │
│  [ComplianceBar — large, animated]                                  │
└────────────────────────────────────────────────────────────────────┘

┌─ Control domain heatmap ───────────────────────────────────────────┐
│  CC1 — Control Environment      [██████████] 95%                   │
│  CC2 — Communication            [████████░░] 82%                   │
│  CC3 — Risk Assessment          [██████░░░░] 64%  ← click to drill │
│  CC4 — Monitoring               [████░░░░░░] 43%  ← failing        │
│  CC5 — Logical Access           [███░░░░░░░] 38%  ← failing        │
│  CC6 — System Operations        [████████░░] 81%                   │
│  CC7 — Change Management        [███████░░░] 74%                   │
└────────────────────────────────────────────────────────────────────┘

── Click CC5 to drill in ────────────────────────────────────────────

┌─ CC5 — Logical Access controls ────────────────────────────────────┐
│  CC5.1  Implement logical access controls            ● PASS         │
│  CC5.2  Restrict logical access to authorized users  ● FAIL  → 12 findings │
│  CC5.3  Manage user access                           ● FAIL  → 8 findings  │
│  CC5.4  Remove access on termination                 ● PASS         │
└────────────────────────────────────────────────────────────────────┘

── Click failing control → list of findings causing failure ─────────
```

---

### Page 5: CSPM `/cspm`

**Purpose:** CSPM module view — show misconfiguration findings, provider coverage,
rule compliance. This is the main module for Security Engineers.

**Layout:**

```
┌─ Page Header ─────────────────────────────────────────────────────┐
│ CSPM — Cloud Security Posture                    [Run Scan ▶]     │
│ Last full scan: 47 min ago · 42,847 resources evaluated           │
└───────────────────────────────────────────────────────────────────┘

┌─ Provider posture cards ───────────────────────────────────────────┐
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│  │ AWS             │  │ Azure           │  │ GCP             │   │
│  │ 64% compliant   │  │ 71% compliant   │  │ 83% compliant   │   │
│  │ 31 CRITICAL     │  │ 12 CRITICAL     │  │ 4 CRITICAL      │   │
│  │ 8 accounts      │  │ 3 subscriptions │  │ 2 projects      │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘   │
└───────────────────────────────────────────────────────────────────┘

┌─ Category breakdown ───────────────────────────────────────────────┐
│ IAM & Identity    [████░░░░░░] 43%  · 28 failing controls          │
│ Data Protection   [██████░░░░] 62%  · 15 failing controls          │
│ Network Security  [████████░░] 78%  ·  9 failing controls          │
│ Logging & Audit   [███░░░░░░░] 34%  · 33 failing controls          │
│ Encryption        [█████████░] 91%  ·  4 failing controls          │
└───────────────────────────────────────────────────────────────────┘

┌─ Findings table (CSPM-filtered) ──────────────────────────────────┐
│ [Same DataTable as /findings, pre-filtered to module:cspm]         │
└───────────────────────────────────────────────────────────────────┘
```

---

### Page 6: CI/CD Security `/cicd`

**Purpose:** DevOps engineers need this. Show pipeline scan results, CLI usage,
secrets exposure trends, dependency vulnerabilities over time.

**Layout:**

```
┌─ Page Header ──────────────────────────────────────────────────────┐
│ CI/CD Pipeline Security          [Install CLI] [View Docs]         │
└────────────────────────────────────────────────────────────────────┘

┌─ Getting started banner (shown until first scan is connected) ─────┐
│ Install the CloudVisor CLI in your pipeline to start scanning      │
│ [Copy install command]  [View GitHub Action]  [View GitLab CI]     │
└────────────────────────────────────────────────────────────────────┘

┌─ Scan type breakdown (4 metric cards) ─────────────────────────────┐
│ SAST Findings: 84   Secrets Found: 12   SCA Vulns: 247   IaC: 156 │
└────────────────────────────────────────────────────────────────────┘

┌─ Recent pipeline scans ────────────────────────────────────────────┐
│ Repository           Branch    Status     Findings  Duration  Time  │
│ my-app              main      ✓ Pass     0 critical  1m 23s   5m   │
│ payments-service    feature   ✗ Blocked  2 critical  2m 11s  12m   │
│ infra-terraform     main      ⚠ Warn    4 medium    0m 45s   8m   │
└────────────────────────────────────────────────────────────────────┘

┌─ Secrets exposure (high urgency section) ──────────────────────────┐
│ ⚠ 12 secrets detected in code history                              │
│ [Table: file, secret type, commit, author, repository, actions]    │
│ Action: [Revoke secret] [Mark as false positive] [View commit]     │
└────────────────────────────────────────────────────────────────────┘
```

---

### Page 7: CDR — Cloud Detection & Response `/cdr`

**Purpose:** SOC Analysts live here during incidents. Design for high urgency
and fast triage. This page has a different visual weight — more red, more urgency.

**Layout:**

```
┌─ Page Header ──────────────────────────────────────────────────────┐
│ Detection & Response          ● Live    [Detections] [Incidents]   │
└────────────────────────────────────────────────────────────────────┘

┌─ Active threat banner (shown when active incidents exist) ─────────┐
│ ⚠  2 ACTIVE INCIDENTS require investigation                        │
│ [View incidents →]                                                  │
└────────────────────────────────────────────────────────────────────┘

┌─ Detection timeline ───────────────────────────────────────────────┐
│ Last 24 hours — [Area chart showing detection volume by MITRE tactic]│
│ Tactics detected: Initial Access, Privilege Escalation, Exfiltration│
└────────────────────────────────────────────────────────────────────┘

┌─ Live detection feed ──────────────────────────────────────────────┐
│ (Streams new detections in real-time via WebSocket)                 │
│                                                                     │
│ ● NOW  CRITICAL  Unusual mass S3 data access       john@company.com │
│ ● 3m   HIGH      IAM role assumption from new geo  svc-payments     │
│ ● 12m  MEDIUM    Off-hours API activity detected   alice@company.com│
│ ● 1h   HIGH      New IAM user created by root      root             │
└────────────────────────────────────────────────────────────────────┘

┌─ Incidents ────────────────────────────────────────────────────────┐
│ [Incident cards — grouped correlated detections]                    │
│ Each card: incident title, severity, affected identity,             │
│            detection count, time open, assignee, MITRE tactics]    │
└────────────────────────────────────────────────────────────────────┘
```

---

### Page 8: AIOps Copilot `/copilot`

**Purpose:** Natural language security interface. Feels like talking to a security
expert who knows your entire cloud environment. This is CloudVisor's signature feature —
make it feel premium.

**Layout:**

```
┌─ Page Header ──────────────────────────────────────────────────────┐
│ Security Copilot                               Powered by Claude AI │
└────────────────────────────────────────────────────────────────────┘

┌─ Conversation area ────────────────────────────────────────────────┐
│                                                                     │
│  ╔════════════════════════════════════════════════════════════╗    │
│  ║  How can I help you with CloudVisor today?                 ║    │
│  ║  Ask me anything about your security posture,             ║    │
│  ║  findings, assets, compliance, or threats.                ║    │
│  ╚════════════════════════════════════════════════════════════╝    │
│                                                                     │
│  [Suggested queries as pill buttons:]                               │
│  "What are my top 5 critical risks?"                               │
│  "Show me all public S3 buckets with PII"                          │
│  "Generate SOC 2 evidence report"                                  │
│  "What changed in the last 24 hours?"                              │
│                                                                     │
│  ── After first message ──────────────────────────────────────    │
│                                                                     │
│   You: Which prod workloads have critical CVEs and public IPs?     │
│                                                                     │
│   CloudVisor AI:                                                    │
│   I found 3 production workloads matching your query:              │
│   [Embedded results table with resource name, CVE, risk score]     │
│   Based on EPSS scores, payments-api (CVE-2024-1234, EPSS: 0.94) │
│   is most likely to be exploited. [View finding →]                 │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘

┌─ Input bar (sticky bottom) ────────────────────────────────────────┐
│ [Ask anything about your security posture...           ] [Send ▶]  │
│ Scoped to: All accounts ▼   Context: 48,291 assets · 1,247 findings│
└────────────────────────────────────────────────────────────────────┘
```

**Design notes:**
- Copilot responses stream token by token (typewriter effect)
- Responses can embed: tables, charts, code blocks, finding cards, asset cards
- Conversation history persists in the session (sidebar with past chats)
- Each response includes: cited sources (asset IDs, finding IDs, rule IDs)
- Thumbs up / thumbs down feedback on each response
- "Open as report" button on any response to save as PDF

---

### Page 9: Settings — Cloud Accounts `/settings/connectors`

**Purpose:** Connect and manage cloud accounts. This is the onboarding page.
The first experience must be exceptional — this is where deals are won or lost
in the 30-minute POC window.

**Layout:**

```
┌─ Page Header ──────────────────────────────────────────────────────┐
│ Cloud Accounts                                 [+ Connect Account] │
└────────────────────────────────────────────────────────────────────┘

┌─ Connected accounts list ──────────────────────────────────────────┐
│  ┌─── AWS Account ────────────────────────────────────────────┐    │
│  │  ● Active   AWS Production     123456789012               │    │
│  │  12 regions  ·  31,402 resources  ·  Last sync: 4 min ago  │    │
│  │  47 CRITICAL  183 HIGH  [View findings] [Sync now] [...]  │    │
│  └────────────────────────────────────────────────────────────┘    │
│  ┌─── Azure Account ──────────────────────────────────────────┐    │
│  │  ⚠ Auth Error   Azure Dev     sub-xxxx-yyyy               │    │
│  │  Last sync: 2 hours ago — [Fix credentials]               │    │
│  └────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────┘

┌─ Connect Account modal / guided wizard ────────────────────────────┐
│  Step 1: Choose provider   [AWS] [Azure] [GCP] [OCI]              │
│  Step 2: Provider-specific setup instructions                      │
│  Step 3: Paste credentials / role ARN                              │
│  Step 4: Validate connection ✓                                     │
│  Step 5: Initial scan in progress...                               │
│          "Discovered 31,402 resources. Running security scan..."   │
│          [View results →]                                          │
└────────────────────────────────────────────────────────────────────┘
```

---

### Page 10: Settings — Team `/settings/team`

**Purpose:** User and access management. Used by Admins and Owners.

**Layout:**

```
┌─ Invite members banner ────────────────────────────────────────────┐
│ [Email address input]            [Role ▼]    [Send Invite]         │
└────────────────────────────────────────────────────────────────────┘

┌─ Members table ────────────────────────────────────────────────────┐
│ User              Role                MFA    Last login   Actions  │
│ [avatar] Alice    Admin               ✓ On   2 hours ago  [Edit]   │
│ [avatar] Bob      Security Engineer   ✗ Off  1 day ago   [Edit]   │
│ [avatar] Carol    Viewer              ✓ On   5 days ago  [Edit]   │
└────────────────────────────────────────────────────────────────────┘

┌─ Pending invites ──────────────────────────────────────────────────┐
│ dave@company.com   Security Engineer   Sent 3d ago   [Resend] [✕]  │
└────────────────────────────────────────────────────────────────────┘

┌─ Role permissions matrix ──────────────────────────────────────────┐
│ [Expandable section showing what each role can/cannot do]           │
└────────────────────────────────────────────────────────────────────┘
```


---

## 6. Cloudscape Patterns — Implement Exactly

This section is the most important reference in the document. Every pattern here
is taken directly from the AWS Cloudscape Design System and proven in the AWS
Management Console. Implement them precisely — do not improvise alternatives.

---

### 6.1 Cloudscape — Design patterns to implement exactly

**Pattern 1: AppLayout is the page shell — use it on every authenticated page**
```
Every interior route mounts inside the Cloudscape AppLayout. The six regions
(TopNavigation, SideNavigation, Breadcrumbs, Content, ToolsPanel, SplitPanel)
are the canonical page shell. Never build a page that bypasses AppLayout.

Use the Cloudscape AppLayout React component (or a faithful reimplementation
in `components/layout/AppShell.tsx`) with these slots:
  - topNavigation:   <TopNavigation />       (dark navy, 40px)
  - navigation:      <SideNavigation />      (light panel, 280px)
  - breadcrumbs:     <BreadcrumbGroup />     (40px, above page content)
  - content:         the page itself
  - tools:           <HelpPanel />           (right, 290px, hidden by default)
  - splitPanel:      <SplitPanel />          (bottom, 360px, hidden by default)

Responsive behavior:
  - ≥ 1280px: all regions can be visible simultaneously
  - 1024–1279px: ToolsPanel auto-hides; user opens it explicitly
  - 768–1023px: SideNavigation collapses to the icon rail (36px)
  - < 768px: SideNavigation becomes a drawer (opens on hamburger tap);
             SplitPanel becomes full-height modal
```

**Pattern 2: Container is the primary content wrapper**
```
Every piece of content on a page lives inside a Container. Tables are wrapped
by a Container whose header doubles as the table header. Forms are wrapped by
a Container whose header is the form title. Charts are wrapped by a Container
whose header includes the chart title and time-range selector.

A page with multiple content blocks is a vertical SpaceBetween(size="l") of
Containers — never a custom grid of bordered divs.

Visual: 1px border at var(--border-default), radius 16px, background
var(--bg-surface), NO drop shadow. Header = 52px with title + actions.
```

**Pattern 3: StatusIndicator is how state is displayed everywhere**
```
Every cell, field, or inline surface that communicates state uses the
Cloudscape StatusIndicator (icon + label). Never a bare colored dot, never
a colored word alone, never a custom icon-only badge.

In a table:
  Status column → <StatusIndicator type="error">Open</StatusIndicator>
                  <StatusIndicator type="success">Resolved</StatusIndicator>
                  <StatusIndicator type="loading">Scanning…</StatusIndicator>

In the side nav: count badge uses a Badge component, NOT a StatusIndicator.
In a Flashbar: the Flashbar item itself carries an icon — don't add a second
StatusIndicator inside the message.
```

**Pattern 4: Flashbar carries page-level status**
```
Operational messages (scan complete, connector failed, data stale, feature
announcement, destructive action confirmation) live in a Flashbar directly
below the breadcrumbs and above the page title. Multiple messages stack.

Each message: type (success/error/warning/info/in-progress) + header +
content + optional action Button + dismiss "×".

Do NOT use toasts for these. Toasts are for transient feedback only
("Link copied"). Do NOT use a yellow Alert at the top of a Container for
page-level status — use the Flashbar.
```

**Pattern 5: SplitPanel for row detail, FullPageModal for deep triage**
```
Clicking a row in the Findings/Assets/Policies table opens a bottom-docked
SplitPanel with key summary fields. Users can re-dock to side.

From inside the SplitPanel, an "Open full ↗" link opens the FullPageModal
(80vw × 90vh) with tabs: Overview, Audit trail, Evidence, Remediation.

The SplitPanel is NOT a right-side drawer. The v3 "DetailDrawer from right"
pattern is retired.
```

**Pattern 6: PropertyFilter replaces multi-dropdown filters and sidebar filters**
```
Every table has a single PropertyFilter input above it. This is a tokenized
text input where users type `property:operator:value` and see dropdown
suggestions (e.g., "severity = CRITICAL", "age > 7", "provider = aws").

Tokens appear as pill chips (radius 20px) to the right of the search input.
Free text search matches across all searchable fields.

The v3 "persistent 240px left filter sidebar" pattern is retired.
```

**Pattern 7: Form fields — label above, prominent label weight**
```
Every form field stacks vertically in this order:
  1. Label          (text-body-bold, 14px / 700, text-primary)
  2. Optional "ⓘ Info" link beside the label (opens Tools panel)
  3. Description    (text-small, text-secondary) — describes the field's purpose
  4. Input          (32px tall, 8px radius, 1px border var(--border-default))
  5. Helper / Error (text-small; red var(--danger) if error)

Field gap (between label stack and next field): --space-m (16px).
Labels are prominent — Cloudscape's Visual Refresh made labels read louder
than before. NEVER use placeholder-as-label.
```

**Pattern 8: Buttons are pill-shaped with four variants**
```
All buttons use border-radius var(--radius-button) = 20px. Four variants:

  <Button variant="primary">Run scan</Button>
    bg var(--accent), text var(--text-inverse), no border
    hover bg var(--accent-hover)
    Use for: the single most important action on the page (at most ONE primary
    button per page header; at most ONE per form).

  <Button variant="normal">Export</Button>
    bg var(--bg-surface), 1px border var(--border-strong), text var(--text-primary)
    hover bg var(--bg-elevated)
    Use for: all secondary actions.

  <Button variant="link">Learn more</Button>
    no bg, no border, text var(--accent), underline on hover only
    Use for: navigation, supplementary actions.

  <Button variant="icon" aria-label="…"><Settings /></Button>
    32px square, no bg, icon-only (24px square in table rows)
    Use for: compact toolbar actions.

Height: 32px default; 24px small (dense toolbars).
Labels are sentence case. NEVER all caps, NEVER title case.
```

**Pattern 9: Tabs for sub-navigation inside a page**
```
When a page has multiple views of the same data (e.g., /cspm: Overview /
Compliance / Misconfigurations / Policies / Reports), use a Cloudscape Tabs
component directly below the page title.

Spec:
  - Horizontal tab bar, 44px tall
  - Active tab: 2px bottom border var(--accent), text weight 700 var(--text-primary)
  - Inactive: text-body var(--text-secondary), hover text-primary
  - NO background change on tabs — only the underline indicator
  - Tab content swaps without full page navigation (URL query param: ?tab=compliance)
  - Maximum depth: ONE level of tabs per page. Never tabs-inside-tabs.
```

**Pattern 10: Help panel and "ⓘ Info" links**
```
Help lives in the Cloudscape Tools panel (right drawer, 290px wide). Help is
contextual: each page section, each form field, each column header can carry
an inline "ⓘ Info" link that opens the panel to the relevant entry.

Visual of "ⓘ Info" link:
  text-small, var(--accent), inline next to the title or label
  Icon: HelpCircle (Lucide), 16px, currentColor
  Clicking: opens Tools panel if closed; scrolls to anchor if already open

Help content format: markdown with sections — Summary, How it works, Examples,
Related actions. NEVER open help in a new page or new modal.
```

**Pattern 11: Breadcrumbs are mandatory on every interior page**
```
Every page except /dashboard (the root) has a BreadcrumbGroup directly below
the top navigation. Users rely on breadcrumbs to navigate back one level.

Examples:
  Home / Findings
  Home / Findings / S3 bucket public access
  Home / Settings / Cloud accounts / AWS Production

Last item (current page) is weight 700, not a link. Earlier items are links,
text-small, text-primary, separator "/" in text-tertiary.
```

**Pattern 12: Content density is a user preference, not a prop**
```
Cloudscape applies content density globally. Users choose "Comfortable" (40px
rows, --space-l padding) or "Compact" (32px rows, --space-m padding) in the
top-nav Settings menu. Persist to localStorage.

Component code reads density from a ThemeProvider context — NEVER hardcode
row heights or paddings. A custom component that takes a `size="compact"`
prop is wrong; it should read the density value.
```

**Pattern 13: Dark mode via [data-theme="dark"]**
```
User toggles between Light / Dark / System in the top-nav Settings menu.
Applied to <html> as `data-theme="light"` or `data-theme="dark"`. System
follows prefers-color-scheme via a MutationObserver.

Components use CSS custom properties exclusively — no JS-based theme lookups.
SVG illustrations and charts must work in both modes: use currentColor where
possible, use design tokens where color is specific.
```

**Pattern 14: Resource-type icon system**
```
Every cloud resource type has an official provider icon — never a generic icon.
AWS S3 → AWS S3 SVG. Azure VM → Azure VM SVG. GCP BigQuery → GCP BigQuery SVG.
OCI Object Storage → OCI Object Storage SVG.

Store under public/icons/{aws|azure|gcp|oci}/{resource-type}.svg.
Render at 16px in table cells, 20px in detail headers, 24px in graph nodes.
Always paired with the ProviderBadge (3.3) for clarity.

Generic Lucide icons (Database, Server, Cloud) are only for provider-agnostic
surfaces — never as a stand-in for a specific resource type.
```

**Pattern 15: Connected-accounts health lives in the top navigation**
```
The top nav utility area shows a compact "scope" ButtonDropdown with a
StatusIndicator summary: " ● AWS (3)  ● Azure (1)  ⚠ GCP (1 error) ".

Clicking any provider row filters /settings/connectors to that provider.
Yellow warning triangle on a provider = at least one connector is in error
or stale state.
```

**Pattern 16: Evidence-based compliance — one-click export for every control**
```
On every compliance control row (and framework summary), a "Download
evidence" Button (variant="normal") downloads a CSV of resources +
pass/fail + last-checked timestamp. This is what auditors actually need;
the percentage is secondary.

The /compliance page also exposes a "Generate report" primary button that
creates a PDF evidence package for the current framework.
```

**Pattern 17: "Suppress" vs "Accepted risk" — distinct visual treatments**
```
Both actions require a mandatory reason field (min 20 characters) submitted
through a Cloudscape Modal (not an inline textarea). Both expose different
visual states afterward:

  Suppressed findings:
    - StatusBadge shows "Suppressed" (StatusIndicator type="stopped")
    - Row title column renders with strikethrough + text-secondary color
    - Excluded from the default "Open" severity counts
    - Visible only when filter includes status=suppressed

  Accepted-risk findings:
    - StatusBadge shows "Accepted" with custom purple CheckCircle2
    - Row renders normally (no strikethrough)
    - KEPT in the risk score and severity counts — the risk still exists,
      the business has just acknowledged it
    - A purple CheckCircle2 (16px) appears beside the title as a permanent marker
```

---

### 6.2 Cloudscape Visual Refresh specifics (2024 update)

The AWS Management Console's late-2024 Visual Refresh is the current state of
Cloudscape. Key changes CloudVisor inherits:

- **Thinner strokes replaced drop shadows on containers.** Containers,
  Flashbars, Cards, Panels no longer cast shadows — they are bounded by a
  1px var(--border-default) stroke instead. Shadows are reserved for
  modals, popovers, dropdowns, tooltips, and toasts.
- **Blue is the single interactive color.** Secondary buttons, links, tokens,
  and interactive states across components are the same bright blue
  (var(--accent)). The v3 "orange accents for hover" pattern is retired.
- **Stronger typographic hierarchy.** H1 24px, H2 20px, H3 18px, body 14px.
  Labels in form fields are weight 700, making them scan faster.
- **Improved dark mode differentiation.** Container backgrounds, input
  backgrounds, and elevated-row backgrounds step up more distinctly in
  dark mode so that nested surfaces read clearly.

---

### 6.3 What NOT to build

- **No circular "risk score gauge" hero.** The v3 RiskScoreGauge pattern is
  retired. Risk scores render as KeyValuePair + ProgressBar inside a Container.
- **No customizable draggable widget grid.** The dashboard is a fixed composition
  of Containers. The v3 "50+ interchangeable widgets" model is retired.
- **No 4px left-border severity cards for findings.** Findings render as
  DataTable rows with a SeverityBadge cell — not as severity-tinted cards
  scattered across the page. The v3 "finding card with colored left border"
  pattern is retired.
- **No attack-surface tile grid with heat-colored account tiles.** Cloud
  accounts on /settings/connectors are a DataTable (one row per account)
  with StatusIndicator + RiskScore + finding counters.
- **No dark navy sidebar on light content.** Side nav is light in light mode
  and dark in dark mode — it inverts with the theme. The dark TopNavigation
  is the only always-dark surface.
- **No marketing-style empty states with illustrations and marketing copy.**
  Empty states are Cloudscape-plain: 32px icon + text-h3 title + one-line
  text-body description + one primary action.
- **No gradient fills, glassmorphism, glows, or decorative animations.**

---

## 7. Technical Implementation Rules

### 7.1 Tech stack (frontend)

```
Framework:    Next.js 15 (App Router) — matches CloudVisor backend prompt v3.0
Language:     TypeScript 5.x (strict mode — no 'any', no type assertions without comment)
Styling:      Tailwind CSS v4 + CSS custom properties (design tokens in Section 2.2)
State:        TanStack Query v5 (server state) + Zustand (client UI state)
Charts:       Recharts (bar, line, area, pie charts) + custom SVG for small inline indicators
Graph viz:    React Flow v12 (attack path graph, asset relationship graph)
Tables:       TanStack Table v8 (sorting, filtering, virtualization)
Forms:        React Hook Form v7 + Zod v3 (validation)
Icons:        Lucide React (UI icons) + custom SVG sprite for cloud provider icons
Dates:        date-fns v3
Toast:        Sonner (bottom-right, transient only — page-level status goes in Flashbar)
Animations:   Framer Motion v11 (page fades, SplitPanel slide, chart mounts)
Modals:       Radix UI Dialog (accessible, headless)
Dropdowns:    Radix UI DropdownMenu + Select (accessible, headless)
Storybook:    Storybook 8 (every component requires stories — enforced in CI)
Testing:      Vitest + React Testing Library v15 (80%+ coverage gate in CI)
E2E:          Playwright (critical flows: login, finding triage, compliance report)
```

**Additional libraries specifically for Cloudscape-aligned UI:**
```
AppLayout primitives: custom (components/layout/AppShell.tsx) — implements the six
  regions (TopNavigation, SideNavigation, Breadcrumbs, Content, ToolsPanel, SplitPanel)
SplitPanel: custom (components/layout/SplitPanel.tsx) — bottom/side dock + resize
Flashbar: custom (components/ui/Flashbar.tsx) — stacked message surface
PropertyFilter: react-aria + custom (tokenized input + autocomplete per property)
StatusIndicator: custom (components/ui/StatusIndicator.tsx) — icon + label pairing
Container + Header: custom (components/ui/Container.tsx) — 1px-stroke wrapper
JSON viewer (Evidence tab): react-json-view with custom Cloudscape theme (mono font,
  muted neutrals, 12px)
Cloud provider icons: download from official AWS/Azure/GCP/OCI icon packs; store
  as individual SVGs under public/icons/{provider}/
```

### 7.2 File structure

```
apps/web/
├── app/                          # Next.js App Router pages
│   ├── (dashboard)/              # Auth-required routes
│   │   ├── dashboard/page.tsx
│   │   ├── findings/page.tsx
│   │   ├── assets/page.tsx
│   │   ├── compliance/page.tsx
│   │   ├── cspm/page.tsx
│   │   ├── cwpp/page.tsx
│   │   ├── cicd/page.tsx
│   │   ├── ciem/page.tsx
│   │   ├── kspm/page.tsx
│   │   ├── dspm/page.tsx
│   │   ├── cdr/page.tsx
│   │   ├── aiops/page.tsx
│   │   ├── copilot/page.tsx
│   │   ├── settings/
│   │   │   ├── connectors/page.tsx
│   │   │   ├── notifications/page.tsx
│   │   │   ├── team/page.tsx
│   │   │   ├── api-keys/page.tsx
│   │   │   └── billing/page.tsx
│   │   └── layout.tsx            # Sidebar + page shell
│   ├── (auth)/                   # Public routes
│   │   ├── login/page.tsx
│   │   ├── register/page.tsx
│   │   └── layout.tsx
│   ├── layout.tsx                # Root layout (fonts, theme, providers)
│   └── globals.css               # CSS variables + global resets
├── components/
│   ├── layout/                   # AppShell, Sidebar, PageHeader
│   ├── ui/                       # Re-exports from packages/ui
│   └── [page-name]/              # Page-specific components
├── hooks/                        # Custom React hooks
│   ├── useFindings.ts            # React Query hooks for findings API
│   ├── useAssets.ts
│   ├── useCompliance.ts
│   └── ...
├── lib/
│   ├── api.ts                    # Axios instance + interceptors
│   ├── auth.ts                   # Auth helpers, token management
│   └── utils.ts                  # Utility functions
└── types/                        # TypeScript types (import from packages/types when available)
```

### 7.3 API integration rules

```typescript
// All API calls go through a single configured Axios instance
// Never use fetch() directly — always use the api client

// lib/api.ts
import axios from 'axios';

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL + '/v1',
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: inject auth token
api.interceptors.request.use((config) => {
  const token = getAccessToken(); // from secure storage
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response interceptor: handle 401 (auto-refresh), unwrap envelope
api.interceptors.response.use(
  (response) => response.data.data,  // unwrap { data, meta, errors }
  async (error) => {
    if (error.response?.status === 401) {
      await refreshAccessToken();
      return api(error.config); // retry once
    }
    throw error;
  }
);

// Every API call uses React Query — never useState + useEffect for server data
const { data: findings, isLoading } = useQuery({
  queryKey: ['findings', filters],
  queryFn: () => api.get('/findings', { params: filters }),
  staleTime: 30_000,      // 30 seconds
  refetchInterval: 60_000, // refresh every 60 seconds
});
```

### 7.4 Accessibility rules

```
- All interactive elements reachable by keyboard (Tab, Shift+Tab)
- All icons have aria-label when used as buttons
- All images have meaningful alt text (or alt="" if decorative)
- Color is never the ONLY indicator of state — always pair with text or icon
  (SeverityBadge shows "CRITICAL" text, not just red color)
- Focus rings: visible, using --border-accent color, 2px outline
- Modals, SplitPanel, and popovers trap focus (use focus-trap-react for modals;
  SplitPanel retains native keyboard nav but Escape returns focus to the triggering row)
- Tables have proper thead/tbody/th[scope] structure
- Form inputs have associated labels (never placeholder as only label)
- Screen reader announcements for: new findings loaded, scan completed, bulk action result
- Contrast ratios: text on backgrounds ≥ 4.5:1 (AA), large text ≥ 3:1
```

### 7.5 Performance rules

```
- Dashboard initial load: < 2 seconds on 4G connection
- No layout shift (CLS = 0) — always set explicit dimensions on images and charts
- All charts: render with skeleton, then animate in data
- Tables: virtualize rows for > 200 items (use @tanstack/react-virtual)
- Images: Next.js <Image> component always — never raw <img>
- Code splitting: each page is a separate chunk (Next.js App Router does this automatically)
- API calls: parallel fetching with Promise.all — never waterfall sequential calls
- Heavy components (graph visualization, PDF viewer): lazy-loaded
  import dynamic from 'next/dynamic';
  const AttackPathGraph = dynamic(() => import('./AttackPathGraph'), { ssr: false });
- Bundle size: run `next build --analyze` — no single chunk > 200KB gzipped
```

### 7.6 Authentication flow

```
Login page (/login):
  - Email + password form
  - "Continue with Google" OAuth button
  - "Use SSO" link (enterprise — prompts for company email, redirects to IdP)
  - Error states: "Invalid credentials", "Account locked", "MFA required"

MFA step (/login/mfa):
  - 6-digit TOTP input (auto-focus, auto-submit on 6th digit)
  - "Use backup code" link

Post-login:
  - Redirect to /dashboard (or originally requested URL)
  - Store access token in memory (NOT localStorage)
  - Store refresh token in httpOnly cookie (server sets this)
  - Access token auto-refreshed 60s before expiry

Session expiry:
  - Show modal: "Your session has expired. Sign in to continue."
  - Re-authenticate without losing current page state
```

---

## 8. LLM Coder Rules for UI (Apply Every Session)

1. **Light mode is default.** The app loads in light mode matching the AWS
   Management Console. Dark mode is a user-toggleable setting via
   `[data-theme="dark"]` on `<html>`. Never build a page in dark mode first.
   All design tokens in Section 2.2 define light-mode values; dark mode is the
   override block.

2. **Top navigation is always dark navy; side navigation follows the theme.**
   `var(--bg-sidebar)` (dark navy) applies to the top nav bar in both light and
   dark modes. `var(--bg-sidenav)` applies to the left side-nav and INVERTS
   between modes (white in light, dark in dark). Do not confuse the two —
   the top bar and the side nav are different surfaces with different roles.

3. **Use the design system tokens, never hardcode colors.** Writing `color: #dc2626`
   is wrong. Writing `color: var(--critical)` is correct. The only exception is
   external library overrides where CSS variables cannot be used.

4. **Every page uses AppLayout.** TopNavigation, SideNavigation, BreadcrumbGroup,
   content, optional ToolsPanel, optional SplitPanel. Interior pages always have
   breadcrumbs. The dashboard root does not. Do not build a page that bypasses
   AppLayout — that is a wrong-shape page.

5. **Container is the primary wrapper.** Tables, charts, forms, and KPI blocks
   live inside a Container with a Header. Containers have a 1px border, radius
   16px, and NO shadow (Cloudscape Visual Refresh replaced shadows with strokes).
   Shadows are reserved for Modals, Popovers, Dropdowns, Tooltips, and Toasts.

6. **StatusIndicator is how state is shown — never a colored dot alone.** Icon
   + label, always. Table cells, Flashbar messages, scan status, connector
   status, finding state — all of them render through StatusIndicator with the
   appropriate type (success / error / warning / info / loading / pending / stopped).

7. **Flashbar carries page-level status. Toasts are transient only.** New findings
   arrived? Flashbar. Scan completed? Flashbar. Auth error? Flashbar. "Link
   copied"? Toast. When in doubt, Flashbar — toasts are for ephemeral
   acknowledgments.

8. **PropertyFilter is the filter UI above every table.** Single tokenized input.
   NOT a dropdown-per-property. NOT a persistent left sidebar of filters. The
   single PropertyFilter matches how the AWS Console filters EC2 instances,
   CloudWatch logs, and every other resource list.

9. **Row click → SplitPanel (bottom).** Clicking a table row opens the bottom-
   docked SplitPanel with quick-triage KeyValuePair content. The FullPageModal
   (80vw × 90vh, with Overview / Audit trail / Evidence / Remediation tabs)
   opens from the SplitPanel's "Open full details" link or direct URL
   navigation. Two detail levels, same data.

10. **Risk score is a KeyValuePair + ProgressBar, never a circular gauge hero.**
    The number + a horizontal bar inside a Container is the AWS-native way to
    show magnitude. The circular gauge is explicitly retired in v4.

11. **Every data-fetching component has 4 states.** Loading (Cloudscape
    skeletons), Empty (centered icon + title + body + action inside the
    Container), Error (Flashbar + inline Container error), Stale (Flashbar +
    subtle timestamp in Container header). Happy-path-only components are
    incomplete.

12. **Finding detail starts with the impact statement.** Inside the SplitPanel
    and the FullPageModal Overview tab, the first content block after the
    KeyValuePair grid is an Alert component (type="warning") with the plain-
    English impact. Never start with the technical description.

13. **Use official cloud provider icons, not generic icons.** AWS S3 bucket →
    AWS S3 SVG. Azure VM → Azure VM SVG. Store in `public/icons/aws/`,
    `public/icons/azure/`, `public/icons/gcp/`, `public/icons/oci/`. Never use
    a generic database icon for an RDS instance.

14. **Sentence case everywhere.** Page titles, Container headers, button labels,
    side-nav labels, table column headers, form labels. "Run scan" not "RUN SCAN"
    and not "Run Scan". Acronyms remain uppercase (AWS, SOC 2, CIS, CSPM).

15. **Buttons are pill-shaped (radius 20px).** Four variants: `primary`, `normal`,
    `link`, `icon`. Never square-cornered buttons.

16. **Accessibility is not optional.** Run axe checks in CI. Any violation blocks
    the PR. Enterprise customers have accessibility requirements in procurement
    contracts. Focus rings use `--shadow-focus`, not `outline:`.

---

*CloudVisor UI Design & Build Prompt — Version 4.0*
*Design language: AWS Cloudscape Design System — AppLayout page shell (dark top nav,*
*light side nav, breadcrumbs, content, tools panel, split panel), Container as the*
*primary content wrapper with 1px strokes and no shadows, Flashbar for page-level*
*status, StatusIndicator (icon + label) for state, PropertyFilter for table*
*filtering, bottom-docked SplitPanel for row detail, KeyValuePair + ProgressBar for*
*risk scores, pill-shaped buttons, Open Sans at 14px body, 4px spacing grid.*
*Brand color palette (navy, bright blue, coral, sunset, severity) retained from v3.*
*This document is the authoritative UI specification for the CloudVisor platform.*
*Use alongside CloudVisor_Instructions_v3.md (backend spec).*
