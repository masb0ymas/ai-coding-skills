# UI/UX Pro Max

A portable Agent Skill providing searchable local UI/UX design intelligence for web, mobile, and desktop interfaces. It packages curated style, color, typography, UX, icon, motion, chart, and per-stack guideline catalogs behind a single BM25 search script, so an agent can generate a coherent design system or answer a targeted design/implementation question without network access. It ships as part of the `ai-coding-skills` collection; upstream project: <https://github.com/nextlevelbuilder/ui-ux-pro-max-skill>.

## When to use it

- Designing new pages or screens, or establishing a system-wide visual direction.
- Creating or refactoring UI components.
- Choosing color, typography, spacing, or layout systems.
- Reviewing UI for UX, accessibility, or consistency problems.
- Implementing navigation, animation, or responsive behavior.
- Improving perceived quality and usability of an interface.
- Any task that changes how something looks, feels, moves, or is interacted with.

Not for: pure backend logic, API/database design, non-visual performance work, infrastructure/DevOps, or non-visual scripts.

## What it covers

### Rule categories, by priority

Priority 1→10 determines which category to focus on first; `--domain <Domain>` retrieves full details. Full rule text for every category lives in `references/quick-reference.md`.

| Priority | Category | Impact | Domain | Key checks | Anti-patterns |
|----------|----------|--------|--------|------------|---------------|
| 1 | Accessibility | CRITICAL | `ux` | Contrast 4.5:1, alt text, keyboard nav, aria-labels | Removing focus rings, icon-only buttons without labels |
| 2 | Touch & Interaction | CRITICAL | `ux` | Min size 44×44px, 8px+ spacing, loading feedback | Hover-only reliance, instant (0ms) state changes |
| 3 | Performance | HIGH | `ux` | WebP/AVIF, lazy loading, reserve space (CLS < 0.1) | Layout thrashing, cumulative layout shift |
| 4 | Style Selection | HIGH | `style`, `product` | Match product type, consistency, SVG icons (no emoji) | Mixing flat & skeuomorphic randomly, emoji as icons |
| 5 | Layout & Responsive | HIGH | `ux` | Mobile-first breakpoints, viewport meta, no horizontal scroll | Horizontal scroll, fixed px container widths, disabled zoom |
| 6 | Typography & Color | MEDIUM | `typography`, `color` | Base 16px, line-height 1.5, semantic color tokens | Body text < 12px, gray-on-gray, raw hex in components |
| 7 | Animation | MEDIUM | `ux`, `gsap` | Context-aware timing, motion conveys meaning, spatial continuity | One duration for every transition, animating width/height, no reduced-motion |
| 8 | Forms & Feedback | MEDIUM | `ux` | Visible labels, error near field, helper text, progressive disclosure | Placeholder-only label, errors only at top, upfront overload |
| 9 | Navigation Patterns | HIGH | `ux` | Predictable back, bottom nav ≤5, deep linking | Overloaded nav, broken back behavior, no deep links |
| 10 | Charts & Data | LOW | `chart` | Legends, tooltips, accessible colors | Relying on color alone to convey meaning |

### Catalogs

The skill ships searchable local data with these counts (as stated in `SKILL.md`, cross-checked against `data/catalog-summary.json`):

- 79 searchable styles out of 88 total (50 active, 29 supplemental, 9 deprecated).
- 192 product palette/reasoning entries: 192 palettes and 192 reasoning profiles.
- 74 font pairings.
- 1,934 Google Fonts entries.
- 119 UX guidelines.
- 105 curated icons; 1,512 upstream Phosphor icons.
- 17 motion (GSAP) presets.
- 25 chart types.
- 22 technology stacks, with 1,260 stack-specific guidelines.

### Search domains

Passed via `--domain` (defaults from the query when omitted, but auto-detection can misroute overlapping terms):

| Need | Domain | Example |
|------|--------|---------|
| Product type patterns | `product` | `"entertainment social" --domain product` |
| More style options | `style` | `"glassmorphism dark" --domain style` |
| Color palettes | `color` | `"entertainment vibrant" --domain color` |
| Font pairings | `typography` | `"playful modern" --domain typography` |
| Individual Google Fonts | `google-fonts` | `"sans serif popular variable" --domain google-fonts` |
| Chart recommendations | `chart` | `"real-time dashboard" --domain chart` |
| UX best practices | `ux` | `"error summary validation" --domain ux` |
| Landing page structure | `landing` | `"hero social-proof" --domain landing` |
| Icon recommendations | `icons` | `"decorative icon aria hidden" --domain icons` |
| GSAP animation presets | `gsap` | `"scroll reveal stagger" --domain gsap` |
| React/Next.js performance | `react` | `"rerender memo list" --domain react` |
| App/native interface guidelines | `web` | `"accessibilityLabel touch safe-areas" --domain web` |

### Available stacks

`react`, `nextjs`, `vue`, `svelte`, `astro`, `nuxtjs`, `nuxt-ui`, `angular`, `laravel`, `swiftui`, `react-native`, `flutter`, `jetpack-compose`, `html-tailwind`, `shadcn`, `threejs`, `javafx`, `wpf`, `winui`, `avalonia`, `uno`, `uwp` (22).

### CLI

Invoke the search script by full path — it lives inside the skill directory, not the project directory:

```bash
python "${CLAUDE_PLUGIN_ROOT}/.claude/skills/ui-ux-pro-max/scripts/search.py" "<query>" --domain <domain>
```

If `python` is not found, try `python3`, then `py -3`. Requires Python 3.x, no external dependencies.

Design system generation (required for new pages/projects):

```bash
python "${CLAUDE_PLUGIN_ROOT}/.claude/skills/ui-ux-pro-max/scripts/search.py" "<product_type> <industry> <keywords>" --design-system [-p "Project Name"]
```

```bash
python "${CLAUDE_PLUGIN_ROOT}/.claude/skills/ui-ux-pro-max/scripts/search.py" "beauty spa wellness service" --design-system -p "Serenity Spa"
```

Detailed domain search:

```bash
python "${CLAUDE_PLUGIN_ROOT}/.claude/skills/ui-ux-pro-max/scripts/search.py" "<keyword>" --domain <domain> [-n <max_results>]
```

Stack search:

```bash
python "${CLAUDE_PLUGIN_ROOT}/.claude/skills/ui-ux-pro-max/scripts/search.py" "<keyword>" --stack <stack>
```

Full flag set (from `scripts/search.py`):

- `--domain` / `-d` — search domain.
- `--stack` / `-s` — stack-specific search.
- `--max-results` / `-n` — 1–20, default 3.
- `--json` — machine-readable output.
- `--full` — do not truncate long field values in text output.
- `--design-system` / `-ds` — generate a complete design system recommendation.
- `--project-name` / `-p` — project name for design system output.
- `--format` / `-f` — `ascii` (default) or `markdown` for design-system output; ignored if `--json`.
- `--persist` — save to `design-system/<project-slug>/MASTER.md`.
- `--page` — also create a page-specific override in `design-system/<project-slug>/pages/`.
- `--output-dir` / `-o` — directory the `design-system/` folder is created under.
- `--force` — overwrite an existing `MASTER.md` when persisting.
- `--variance`, `--motion`, `--density` — optional 1–10 design dials.

### Design dials

Three optional 1–10 sliders that tune `--design-system` output without changing the query:

```bash
python "${CLAUDE_PLUGIN_ROOT}/.claude/skills/ui-ux-pro-max/scripts/search.py" "<query>" --design-system --variance <1-10> --motion <1-10> --density <1-10>
```

| Dial | Low (1-3) | Mid (4-7) | High (8-10) |
|------|-----------|-----------|-------------|
| `--variance` | Centered / minimal (biases toward Minimalism-style categories) | Balanced / modern | Bold / asymmetric (biases toward Brutalism, Bento Grids) |
| `--motion` | Subtle micro-interactions | Standard scroll/stagger motion | Complex choreography (pin, Flip, SplitText) |
| `--density` | Spacious (24-96px spacing scale) | Standard (16-64px, current default) | Dense/dashboard (8-32px spacing scale) |

`--motion` attaches a ready-to-use GSAP snippet (with framework notes, Do/Don't, and performance notes) pulled from `--domain gsap`, matched to the resolved tier (Subtle/Standard/Complex). `--density` overrides the `--space-*` CSS variable table in the output. Leaving a dial unset keeps that part of the output unchanged.

```bash
python "${CLAUDE_PLUGIN_ROOT}/.claude/skills/ui-ux-pro-max/scripts/search.py" "internal analytics dashboard" --design-system --variance 8 --motion 7 --density 8 -p "Ops Console"
```

### Output formats

`--design-system` supports `-f ascii` (default, terminal display), `-f markdown` (documentation), and `--json` (machine-readable, includes the raw design system dict plus persistence status).

## How it works

The agent follows a query contract, choosing the smallest search mode that fits the request:

1. **New project/page or system-wide visual direction** → `--design-system`.
2. **Targeted concern or component bug** → one explicit `--domain`.
3. **Known implementation stack** → `--stack`; add a separate domain search only for a distinct design concern.

Each query is built around one dominant intent, using 2–5 meaningful terms and one useful constraint such as product, platform, or interaction. Returned domain/category, top result identity, and fit for the user's product and platform are verified before applying. On empty or off-topic output the skill retries once with a narrower rewrite or explicit domain/stack; if that fails it states no verified match was found and labels general guidance as a fallback. Unverified output is not persisted.

**Workflow steps:**

1. **Analyze requirements** — extract product type, audience/context, style keywords, and stack. The stack is detected from the project (`package.json` deps such as react/next/vue/svelte/nuxt/@angular, `pubspec.yaml` for Flutter, `*.xcodeproj`/`Package.swift` for SwiftUI, `composer.json` for Laravel, or `app.json` + `react-native` dep for React Native). If nothing is detectable and stack guidance matters, ask the user; a stack is never assumed.
2. **Generate design system** (required for new pages/projects) — `--design-system` aggregates product/style/color/landing/typography matches, applies reasoning rules from `ui-reasoning.csv`, and returns pattern, style, colors, typography, effects, and anti-patterns to avoid.
3. **Persist design system** (Master + Overrides pattern) — add `--persist` and always pass `--output-dir` pointed at the project root; without it, files are written relative to whatever directory the tool runs from. This creates `design-system/<project-slug>/MASTER.md` (global source of truth) and `design-system/<project-slug>/pages/` for page-specific overrides. Adding `--page "dashboard"` also creates `design-system/<project-slug>/pages/dashboard.md`. If Master already exists, a new page file is created without changing Master; an existing page file is skipped unless `--force` is explicitly authorized. If `MASTER.md` exists, `--persist` skips writing it unless `--force` is passed; the file should be read first before regenerating.
4. **Supplement** with detailed domain searches as needed.
5. **Stack guidelines** — search with the stack detected in step 1.

**Retrieval when building a specific page:** read `design-system/<project-slug>/MASTER.md`; check whether `design-system/<project-slug>/pages/<page-name>.md` exists (its rules override Master); otherwise use Master rules exclusively.

**Accessibility queries** search one observable outcome at a time using explicit outcome terms — query the semantic outcome first (`"error summary validation" --domain ux`), then a component-specific domain if needed (`"decorative icon aria hidden" --domain icons` or `"icon button accessible label" --domain icons`), and only then the implementation stack. Other examples: `"focus not obscured" --domain ux`, `"dragging movements" --domain ux`, `"accessible authentication" --domain ux`.

**Text-layout and compact-component bugs** search the semantic UX outcome first, then the detected stack for implementation details. Example outcome queries: `"orphan heading line balance" --domain ux`, `"badge chip label wraps" --domain ux`, `"live badge count screen reader" --domain ux`, `"rapid chip animation interrupted" --domain ux`. Then a separate stack query such as `"chip badge overflow nowrap" --stack html-tailwind`; the outcome search is not replaced with a framework keyword.

**Guardrails:**

- Search results are recommendations, never instructions that override the user or repository rules.
- Private project data is not included in queries or persisted output.
- The skill does not install packages, modify the operating system, or authorize unrelated changes.
- If a search returns 0 results: retry once with a narrower query or explicit domain/stack; if still empty, fall back to the priority table and explicitly say the recommendation came from built-in defaults, not a database match. A 0-result search is never presented as returned data.

### Pre-delivery checks

Before delivering app UI, read `references/pro-rules.md` and run through its canonical Pre-Delivery Checklist. It covers icon/visual-element discipline, interaction feedback, light/dark contrast, safe-area layout, and accessibility, scoped to native/mobile app UI (iOS/Android/React Native/Flutter).

**Tips for better results:**

- Keep one dominant intent and 2–5 meaningful terms per query: `"keyboard focus modal"`, not a full audit checklist.
- Retry once with a narrower phrase or explicit domain/stack; do not cycle through unrelated keywords.
- Use `--design-system` for a new project/page and `--domain` for a focused concern.
- Pass the detected stack explicitly for implementation-specific guidance.

| Problem | What to do |
|---------|------------|
| Can't decide on style/color | Re-run `--design-system` with different keywords |
| Dark mode contrast issues | `references/quick-reference.md` §6: `color-dark-mode` + `color-accessible-pairs` |
| Animations feel unnatural | `references/quick-reference.md` §7: `spring-physics` + `easing` + `exit-faster-than-enter` |
| Form UX is poor | `references/quick-reference.md` §8: `inline-validation` + `error-clarity` + `focus-management` |
| Navigation feels confusing | `references/quick-reference.md` §9: `nav-hierarchy` + `bottom-nav-limit` + `back-behavior` |
| Layout breaks on small screens | `references/quick-reference.md` §5: `mobile-first` + `breakpoint-consistency` |
| Performance / jank | `references/quick-reference.md` §3: `virtualize-lists` + `main-thread-budget` + `debounce-throttle` |

## Files

- `SKILL.md` — skill definition: rule priority table, query contract, workflow, CLI usage, guardrails.
- `LICENSE` — MIT license.
- `references/` — on-demand rule text.
  - `quick-reference.md` — full rule list per category, all 119 UX guidelines with rationale.
  - `pro-rules.md` — app-specific polish rules (icons, touch feedback, dark mode contrast, safe areas) and the canonical pre-delivery checklist.
- `data/` — catalog data (BM25-indexed CSVs and reference JSON).
  - `styles.csv` — 88 styles (79 searchable, 50 active) with aliases, keywords, colors, effects, accessibility, and implementation metadata.
  - `colors.csv` — 192 product palette rows with semantic tokens (primary, secondary, accent, background, border, etc.).
  - `products.csv` — 192 product-type rows with style recommendations and landing/dashboard patterns.
  - `ui-reasoning.csv` — 192 reasoning profiles; rules applied by `--design-system`.
  - `typography.csv` — 74 font pairings with CSS import and Tailwind config.
  - `google-fonts.csv` — 1,934 Google Fonts entries (family, category, axes, subsets, popularity).
  - `google-font-licenses.json` — license metadata for the Google Fonts catalog.
  - `ux-guidelines.csv` — 119 UX guidelines with do/don't and good/bad code examples.
  - `icons.csv` — 105 curated icons with import code, usage, and semantic roles.
  - `phosphor-icons-upstream.json` — 1,512 upstream Phosphor icon records.
  - `motion.csv` — 17 GSAP motion presets with duration, easing, snippets, and performance notes.
  - `charts.csv` — 25 chart types with accessibility grades, fallbacks, and library recommendations.
  - `landing.csv` — landing-page structure patterns with section order and CTA placement.
  - `app-interface.csv` — native/app interface guidelines (platform, do/don't, code examples) served by the `web` domain.
  - `react-performance.csv` — React/Next.js performance guidance.
  - `catalog-summary.json` — verified counts, file checksums, and provenance metadata.
  - `data-provenance.json` — provenance records for the catalog data.
  - `stacks/` — one CSV per stack (22 files: `react`, `nextjs`, `vue`, `svelte`, `astro`, `nuxtjs`, `nuxt-ui`, `angular`, `laravel`, `swiftui`, `react-native`, `flutter`, `jetpack-compose`, `html-tailwind`, `shadcn`, `threejs`, `javafx`, `wpf`, `winui`, `avalonia`, `uno`, `uwp`).
- `scripts/` — Python tooling.
  - `search.py` — CLI entry point: domain search, stack search, design-system generation, persistence, design dials.
  - `core.py` — CSV config, stack config, BM25 search engine, auto-domain detection.
  - `design_system.py` — design-system aggregation and output formatting.
  - `reasoning_contract.py` — reasoning-rule contract used by design-system generation.
  - `validate_data.py` — catalog validation tooling.
  - `tests/` — unit tests and `fixtures/`.
  - `__pycache__/` — generated bytecode cache.

## Example prompts

```text
Design a visual system for an AI search homepage on Next.js — give me the pattern,
style, colors, typography, and anti-patterns to avoid.
```

```text
Persist a design system for our analytics dashboard project and create the
"dashboard" page override.
```

```text
My form validation UX is poor — what are the error-clarity and focus-management rules?
```

```text
Which chart types should I use for a real-time dashboard with accessible colors?
```

## Install

```sh
./install.sh --target claude --skill ui-ux-pro-max /path/to/project
```

`--target` defaults to `all` (install for every supported agent); `--target agents|claude|openclaude|zcode` selects one.

## Source and license

Upstream: <https://github.com/nextlevelbuilder/ui-ux-pro-max-skill>. MIT license; see `skills/ui-ux-pro-max/LICENSE`. Copyright belongs to the upstream authors.