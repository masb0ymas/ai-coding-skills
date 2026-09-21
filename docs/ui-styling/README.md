# UI Styling

A skill for creating accessible, well-crafted user interfaces by combining three layers: shadcn/ui components (built on Radix UI primitives), Tailwind CSS utility-first styling, and canvas-based visual design for posters and brand materials. It ships as part of [AI Coding Skills](../..), and the guidance originates from [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (MIT, upstream author: claudekit). It solves the problem of assembling consistent, accessible UI — component selection, theming, dark mode, responsive layout, and design-system tokens — without re-deriving the patterns each time.

## When to use it

- Building UI with React-based frameworks: Next.js, Vite, Remix, or Astro.
- Implementing accessible components: dialogs, forms, tables, navigation.
- Styling with a utility-first CSS approach.
- Creating responsive, mobile-first layouts.
- Implementing dark mode and theme customization.
- Building design systems with consistent tokens.
- Generating visual designs, posters, or brand materials.
- Rapid prototyping with immediate visual feedback.
- Adding complex UI patterns: data tables, charts, command palettes.

## What it covers

### Core stack

- **Component layer — shadcn/ui**: pre-built accessible components via Radix UI primitives; copy-paste distribution model (components live in your codebase); TypeScript-first with full type safety; composable primitives; CLI-based installation and management.
- **Styling layer — Tailwind CSS**: utility-first framework; build-time processing with zero runtime overhead; mobile-first responsive design; consistent design tokens (colors, spacing, typography); automatic dead code elimination.
- **Visual design layer — canvas**: museum-quality visual compositions; philosophy-driven design; minimal text for maximum visual impact; systematic patterns and refined aesthetics.

### Component + styling setup

```bash
npx shadcn@latest init
```

The CLI prompts for framework, TypeScript paths, and theme preferences, configuring both shadcn/ui and Tailwind CSS.

```bash
npx shadcn@latest add button card dialog form
```

Components are used with Tailwind utilities in application code:

```tsx
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"

export function Dashboard() {
  return (
    <div className="container mx-auto p-6 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      <Card className="hover:shadow-lg transition-shadow">
        <CardHeader>
          <CardTitle className="text-2xl font-bold">Analytics</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-muted-foreground">View your metrics</p>
          <Button variant="default" className="w-full">
            View Details
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
```

### Tailwind-only setup (Vite)

```bash
npm install -D tailwindcss @tailwindcss/vite
```

```javascript
// vite.config.ts
import tailwindcss from '@tailwindcss/vite'
export default { plugins: [tailwindcss()] }
```

```css
/* src/index.css */
@import "tailwindcss";
```

### Component catalog

`references/shadcn-components.md` is the full component catalog with usage patterns, installation, and composition examples. It covers:

- Form and input: Button, Input, Select, Checkbox, Date Picker, Form validation.
- Layout and navigation: Card, Tabs, Accordion, Navigation Menu.
- Overlays and dialogs: Dialog, Drawer, Popover, Toast, Command.
- Feedback and status: Alert, Progress, Skeleton.
- Display: Table, Data Table, Avatar, Badge.

### Theme and customization

`references/shadcn-theming.md` covers dark mode setup with `next-themes`, the CSS variable system, color customization and palettes, component variant customization, and theme-toggle implementation.

### Accessibility patterns

`references/shadcn-accessibility.md` covers Radix UI accessibility features, keyboard navigation patterns, focus management, screen reader announcements, and form validation accessibility.

### Tailwind utilities

`references/tailwind-utilities.md` covers layout utilities (Flexbox, Grid, positioning), the spacing system (padding, margin, gap), typography (font sizes, weights, alignment, line height), colors and backgrounds, borders and shadows, and arbitrary values for custom styling.

### Responsive design

`references/tailwind-responsive.md` covers the mobile-first approach, the breakpoint system (`sm`, `md`, `lg`, `xl`, `2xl`), responsive utility patterns, container queries, max-width queries, and custom breakpoints.

### Tailwind customization

`references/tailwind-customization.md` covers the `@theme` directive for custom tokens, custom colors and fonts, spacing and breakpoint extensions, custom utility creation, custom variants, layer organization (`@layer base`, `components`, `utilities`), and the apply directive for component extraction.

### Canvas design system

`references/canvas-design-system.md` covers the design-philosophy approach, visual communication over text, systematic patterns and composition, color/form/spatial design, minimal text integration, museum-quality execution, and multi-page design systems.

### Common patterns

Form validation with react-hook-form, zod, and shadcn/ui form primitives:

```tsx
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8)
})

export function LoginForm() {
  const form = useForm({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" }
  })

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(console.log)} className="space-y-6">
        <FormField control={form.control} name="email" render={({ field }) => (
          <FormItem>
            <FormLabel>Email</FormLabel>
            <FormControl>
              <Input type="email" {...field} />
            </FormControl>
            <FormMessage />
          </FormItem>
        )} />
        <Button type="submit" className="w-full">Sign In</Button>
      </form>
    </Form>
  )
}
```

Responsive layout with dark-mode variants:

```tsx
<div className="min-h-screen bg-white dark:bg-gray-900">
  <div className="container mx-auto px-4 py-8">
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <Card className="bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700">
        <CardContent className="p-6">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
            Content
          </h3>
        </CardContent>
      </Card>
    </div>
  </div>
</div>
```

### Utility scripts

Python automation for component installation and configuration generation:

```bash
python scripts/shadcn_add.py button card dialog
```

`shadcn_add.py` adds components with dependency handling. Options: positional component names, `--all` (add every available component), `--overwrite` (overwrite existing components), `--dry-run` (show what would be done without executing), `--list` (list installed components), and `--project-root` (project root directory, default: current directory).

```bash
python scripts/tailwind_config_gen.py --colors brand:blue --fonts display:Inter
```

`tailwind_config_gen.py` generates `tailwind.config.js` with a custom theme. Options: `--framework` (`react`, `vue`, `svelte`, `nextjs`; default `react`), `--js` (generate a JavaScript config instead of TypeScript), `--output` (output file path), `--colors NAME:VALUE`, `--fonts TYPE:FAMILY`, `--spacing NAME:VALUE`, `--breakpoints NAME:WIDTH`, `--plugins` (add recommended plugins), `--validate-only` (validate without writing), and `--force` (overwrite an existing output file).

The generator refuses to create or replace a config when any sibling `tailwind.config.js`, `.cjs`, `.mjs`, or `.ts` file already exists. Review the reported config first, then pass `--force` only when the competing output is intentional:

```bash
python scripts/tailwind_config_gen.py --colors brand:blue --force
```

### Best practices

1. **Component composition** — build complex UIs from simple, composable primitives.
2. **Utility-first styling** — use Tailwind classes directly; extract components only for true repetition.
3. **Mobile-first responsive** — start with mobile styles, layer responsive variants.
4. **Accessibility-first** — leverage Radix UI primitives, add focus states, use semantic HTML.
5. **Design tokens** — use a consistent spacing scale, color palettes, and typography system.
6. **Dark mode consistency** — apply dark variants to all themed elements.
7. **Performance** — leverage automatic CSS purging, avoid dynamic class names.
8. **TypeScript** — use full type safety for better DX.
9. **Visual hierarchy** — let composition guide attention; use spacing and color intentionally.
10. **Expert craftsmanship** — every detail matters; treat UI as a craft.

## How it works

The skill is reference-driven: `SKILL.md` routes the agent to a specific reference document based on the layer being touched, and to the Python scripts for automation. The documented flow is:

1. **Detect the layer.** Component work goes to the shadcn/ui references, styling work to the Tailwind references, and poster/brand work to the canvas reference.
2. **Load only the relevant reference.** Each reference carries the concrete patterns, options, and examples for that layer rather than loading everything at once.
3. **Bootstrap via CLI or script.** `npx shadcn@latest init` / `npx shadcn@latest add` for components, or `scripts/shadcn_add.py` for scripted installation; `scripts/tailwind_config_gen.py` for config generation (with `--validate-only` and a refusal to clobber an existing config unless `--force` is passed).
4. **Compose and style.** Build from composable primitives and apply Tailwind utilities, mobile-first responsive variants, and dark-mode variants.
5. **Apply the guardrails below.**

Guardrails and rules stated by the skill:

- Paths in `SKILL.md` and its references are relative to the directory containing `SKILL.md`, not the project. `scripts/<file>` is the skill's own `scripts/` folder; `../<skill>/scripts/<file>` is a sibling sub-skill installed alongside it. Keep the working directory at the project root — scripts read and write project files such as `docs/brand-guidelines.md`, `assets/design-tokens.json`, or `src/` relative to it.
- Accessibility comes from the primitives: Radix UI supplies the accessible behavior, and the agent adds focus states and semantic HTML on top.
- Theming is token-driven: CSS variables underpin the color system so dark mode is applied by toggling theme variants rather than duplicating styles.
- Avoid dynamic class names so Tailwind's automatic CSS purging stays effective.
- `tailwind_config_gen.py` treats sibling config files as a conflict, not a silent overwrite; `--force` is an explicit opt-in.

## Files

- `SKILL.md` — the skill entry point: core-stack descriptions, quick-start setup, reference navigation, common patterns, best practices, and resources.
- `LICENSE.txt` — license file for the skill.
- `references/` — seven topic guides:
  - `shadcn-components.md` — complete component catalog with usage and composition examples.
  - `shadcn-theming.md` — theme configuration, CSS variables, dark mode, and variant customization.
  - `shadcn-accessibility.md` — ARIA patterns, keyboard navigation, focus management, and screen reader support.
  - `tailwind-utilities.md` — core utility classes for layout, spacing, typography, colors, borders, and shadows.
  - `tailwind-responsive.md` — mobile-first breakpoints and adaptive layout patterns.
  - `tailwind-customization.md` — config structure, custom utilities, plugins, and theme extensions.
  - `canvas-design-system.md` — canvas design philosophy and composition workflows.
- `scripts/` — Python automation:
  - `shadcn_add.py` — add shadcn/ui components with dependency handling.
  - `tailwind_config_gen.py` — generate `tailwind.config.js` with a custom theme.
  - `requirements.txt` — script dependencies.
  - `tests/` — test suites for both scripts (`test_shadcn_add.py`, `test_tailwind_config_gen.py`), plus `requirements.txt` and a coverage report (`coverage-ui.json`).
- `canvas-fonts/` — 81 files: 54 TTF font files across 29 families (e.g. Instrument Sans/Serif, IBM Plex Mono/Serif, JetBrains Mono, Work Sans, Crimson Pro, Bricolage Grotesque, Libre Baskerville) plus 27 `-OFL.txt` license files. Bundled for the canvas visual-design workflow.

## Example prompts

```text
Build an accessible login form with shadcn/ui, Tailwind, and dark-mode support.
```

```text
Create a responsive dashboard layout with consistent design tokens and theme customization.
```

```text
Add shadcn/ui data-table and command-palette components, then style them with Tailwind utilities and a dark theme.
```

```text
Generate a museum-quality poster composition with the canvas design system, using a bundled serif family for the headline.
```

## Install

```sh
./install.sh --target claude --skill ui-styling /path/to/project
```

`--target` defaults to `all` (install for every supported agent); `--target agents|claude|openclaude|zcode` selects one.

## Source and license

Derived from [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (MIT, upstream author: claudekit). This skill ships `LICENSE.txt` in its directory.