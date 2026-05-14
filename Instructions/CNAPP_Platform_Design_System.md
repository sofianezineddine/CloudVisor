# CNAPP Platform — LLM Coder Prompt Guide



## 1. Platform Architecture

### Concept
multi-service security platform console (CNAPP) — think **AWS Console, but for cloud-native security**.
Not a cloud provider, but a security platform with dedicated modules: CSPM, CWPP, CICD, and more.

### Routing
```
/:serviceName             → service landing page  (e.g. /cspm)
/:serviceName/:tabName    → tab inside a service  (e.g. /cspm/findings)
```

### Layout Structure
```
┌─────────────────────────────────────────────────────┐
│                   TOP NAVBAR                        │
├──────────────┬──────────────────────────────────────┤
│              │                                       │
│   SIDEBAR    │           MAIN CONTENT                │
│   (220px)    │           (flex 1)                    │
│              │                                       │
│  [Service    │                                       │
│   Tabs]      │                                       │
│              │                                       │
└──────────────┴──────────────────────────────────────┘
```

- **Top Navbar** — persistent, platform-wide. Contains branding, service switcher, user menu.
- **Left Sidebar** — changes per service. Renders the tab list of the active service only.
- **Main Content** — renders the active tab page.

### Services Data Model
```js
const services = [
  {
    id: "cspm",
    label: "CSPM",
    icon: "shield",
    tabs: [
      { id: "findings",   label: "Findings"   },
      { id: "policies",   label: "Policies"   },
      { id: "compliance", label: "Compliance" },
    ]
  },
  {
    id: "cwpp",
    label: "CWPP",
    icon: "server",
    tabs: [
      { id: "runtime",         label: "Runtime"         },
      { id: "vulnerabilities", label: "Vulnerabilities" },
    ]
  },
  {
    id: "cicd",
    label: "CI/CD",
    icon: "git-branch",
    tabs: [
      { id: "pipelines", label: "Pipelines" },
      { id: "secrets",   label: "Secrets"   },
      { id: "iac",       label: "IaC Scan"  },
    ]
  },
  // ...add more services following the same shape
]
```

### Key Rules
- Switching services → replaces the sidebar entirely with that service's tabs
- Each service's tabs are self-contained — no cross-service tab bleed
- Active service and active tab are always visually highlighted
- Sidebar section label (service name) is shown above the tab list as a group header

---

## 2. Unified Design System

> **Rule #1:** Every component — tables, buttons, inputs, sidebars, badges — must use the same design tokens below. No one-off hardcoded colors, spacings, or font sizes anywhere.

---

### 2.1 Design Tokens (CSS Variables)

```css
:root {
  /* ── Backgrounds ── */
  --color-bg-base:    #0f1117;   /* app-level background          */
  --color-bg-surface: #1a1d27;   /* cards, sidebar, panels        */
  --color-bg-raised:  #21242f;   /* dropdowns, tooltips, inputs   */
  --color-bg-hover:   #2a2d3a;   /* row/item hover state          */

  /* ── Borders ── */
  --color-border:       #2e3140; /* all dividers and borders      */
  --color-border-focus: #4a90d9; /* focused input / select        */

  /* ── Brand & Semantic Colors ── */
  --color-primary:       #4a90d9;
  --color-primary-hover: #5ba3f5;
  --color-danger:        #e05252;
  --color-warning:       #e8a838;
  --color-success:       #3db87a;
  --color-info:          #4a90d9;

  /* ── Text ── */
  --color-text-primary:   #e8eaf0;
  --color-text-secondary: #9099b0;
  --color-text-disabled:  #50566a;
  --color-text-inverse:   #ffffff;

  /* ── Spacing Scale ── */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;

  /* ── Typography ── */
  --font-sans: 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  --text-xs:   11px;
  --text-sm:   13px;
  --text-base: 14px;
  --text-md:   15px;
  --text-lg:   18px;
  --text-xl:   22px;
  --font-normal:   400;
  --font-medium:   500;
  --font-semibold: 600;

  /* ── Borders & Radius ── */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --border: 1px solid var(--color-border);

  /* ── Shadows ── */
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.30);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.40);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.50);

  /* ── Transitions ── */
  --transition: 150ms ease;
}
```

---

### 2.2 Sidebar

| Property        | Value                                               |
|-----------------|-----------------------------------------------------|
| Width           | 220px, fixed                                        |
| Background      | `--color-bg-surface`                                |
| Right border    | `--border`                                          |
| Section label   | `text-xs`, uppercase, letter-spacing, `color-text-secondary` — shown above tabs |
| Nav item size   | full width, `text-sm`, `font-medium`, padding `space-2 space-3`, `radius-md` |
| Default state   | `color-text-secondary`, transparent background      |
| Hover state     | `color-text-primary`, bg `color-bg-hover`           |
| Active state    | `color-primary`, bg `rgba(primary, 0.12)`, left border `2px solid color-primary` |

---



### 2.4 Buttons

All buttons: `height: 32px`, `padding: space-2 space-4`, `radius-md`, `text-sm`, `font-medium`, `transition: var(--transition)`

| Variant    | Background          | Text                    | Border       |
|------------|---------------------|-------------------------|--------------|
| Primary    | `color-primary`     | white                   | none         |
| Secondary  | transparent         | `color-text-primary`    | `--border`   |
| Danger     | `color-danger`      | white                   | none         |
| Ghost      | transparent         | `color-primary`         | none         |
| Disabled   | any (opacity: 0.4)  | —                       | cursor: not-allowed |

---

### 2.5 Tables

| Property       | Value                                                                 |
|----------------|-----------------------------------------------------------------------|
| Background     | `color-bg-surface`                                                    |
| Outer border   | `--border`, `radius-lg`                                               |
| Header row     | bg `color-bg-raised`, `text-xs` uppercase, `color-text-secondary`, `font-semibold` |
| Body row       | `text-sm`, `color-text-primary`, bottom border `--border`            |
| Row hover      | bg `color-bg-hover`                                                   |
| Cell padding   | `space-3 space-4`                                                     |
| Selected row   | bg `rgba(primary, 0.08)`, left border `2px solid color-primary`      |
| Empty state    | centered icon + message in `color-text-secondary`                    |

---

### 2.6 Inputs & Selectors

| Property       | Value                                                        |
|----------------|--------------------------------------------------------------|
| Height         | 32px                                                         |
| Background     | `color-bg-raised`                                            |
| Border         | `--border`, `radius-md`                                      |
| Font           | `text-sm`, `color-text-primary`                              |
| Placeholder    | `color-text-disabled`                                        |
| Focus state    | border `color-border-focus`, outline none, box-shadow `0 0 0 2px rgba(primary, 0.2)` |
| Dropdown menu  | bg `color-bg-raised`, border `--border`, `shadow-md`, `radius-md` |
| Dropdown hover | bg `color-bg-hover`                                          |

---

### 2.7 Badges / Status Pills

All badges: `text-xs`, `font-medium`, `padding: 2px 8px`, `border-radius: 99px`

| Severity  | Background                   | Text color          |
|-----------|------------------------------|---------------------|
| Critical  | `rgba(color-danger, 0.15)`   | `color-danger`      |
| Warning   | `rgba(color-warning, 0.15)`  | `color-warning`     |
| Success   | `rgba(color-success, 0.15)`  | `color-success`     |
| Info      | `rgba(color-primary, 0.15)`  | `color-primary`     |
| Neutral   | `color-bg-raised`            | `color-text-secondary` |

---

### 2.8 Cards / Panels

| Property         | Value                                  |
|------------------|----------------------------------------|
| Background       | `color-bg-surface`                     |
| Border           | `--border`, `radius-lg`                |
| Padding          | `space-6`                              |
| Shadow           | `shadow-sm`                            |
| Internal divider | `--border` horizontal rule             |

---

### 2.9 Page Layout

| Property        | Value                                                        |
|-----------------|--------------------------------------------------------------|
| Page title      | `text-xl`, `font-semibold`, `color-text-primary`            |
| Page subtitle   | `text-sm`, `color-text-secondary`                           |
| Page header     | flex row — title left, actions right — `margin-bottom: space-6` |
| Content width   | max `1280px`, centered with auto margins                    |
| Block spacing   | `space-6` between major sections                            |

---

## 3. Golden Rules

1. **Never hardcode a color or spacing value** — always use a CSS token.
2. **One source of truth** — define each component once, import everywhere.
3. **No service-specific overrides** — CSPM and CWPP tables look identical.
4. **Density over decoration** — this is a data-heavy security tool, not a marketing site.
5. **All interactive states are mandatory** — every element must have `active`, `hover`, `focus`, and `disabled` states explicitly defined.
6. **Consistency beats creativity** — when in doubt, reuse an existing component instead of creating a new one.
