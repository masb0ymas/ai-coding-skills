# TypeSafe AI

Guidance for building AI-powered software with [TypeSafe](https://docs.typesafe.ai/), which packages units of AI intelligence as programming primitives: small judgments that compose into larger capabilities. TypeSafe's System One models return fast, focused judgments that software can consume directly, and Jev is TypeSafe's flagship and first System One model. Instead of generating text or reasoning explanations, the models understand natural language and return typed answers and probabilities. Code owns the workflow; the model supplies programmable common sense where ordinary code needs semantic understanding. This skill directs the agent to the live TypeSafe docs, which are the source of truth for concepts, prompting guidance, API contracts, SDK usage, models, limits, and worked examples.

## When to use it

- A feature needs programmable common sense — semantic understanding that ordinary code cannot supply.
- Brainstorming what AI could make possible in an app, or choosing an architecture that goes beyond classification.
- An LLM prompt-and-parse step should become a structured decision: routing, ranking, extraction, verification, or interactive experiences.
- Preparing inputs and questions, or deciding how to handle uncertainty in an existing integration.
- Writing API or SDK code, or updating an older integration via the migration guide.

These applications are starting points, not limits; combine primitives around the user's goal, including ideas that do not fit an established recipe. For an open-ended request, offer the few directions that best serve the user's goal and recommend a starting point. For a concrete request, choose the relevant pattern and build — a brainstorm is not a mandatory detour.

## What it covers

### The System One programming model

TypeSafe's System One models turn natural language and application state into typed judgments and probabilities that code can combine. The model does not own the workflow: code owns the workflow, keeps known rules, calculations, exact lookups, and execution, and calls the model only where semantic understanding helps. The skill instructs the agent to preserve the user's chosen stack and scope.

Start from the behavior the user wants — what will the application show, select, change, or hand off? — and work backward to the judgments it needs.

### Read the live docs

The live TypeSafe docs are the source of truth and are read as part of the task. The skill gives direction; the docs carry current concepts, prompting guidance, API contracts, SDK usage, models, limits, and worked examples.

- Start with the [documentation index](https://docs.typesafe.ai/llms.txt) to discover relevant pages and cookbooks. Use targeted reads rather than loading the entire site.
- Mintlify serves Markdown by appending `.md` to a page path, for example `https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md`. Follow links from the index; convert extensionless documentation page links to `.md` when useful. Resolve relative links against `https://docs.typesafe.ai`.
- Before writing an integration, read the current API or chosen SDK page and the question guidance relevant to the design. For a new workflow, also inspect the closest cookbook: it often shows a better decomposition than a generic classifier.
- If the index is unavailable, use the direct links in the routing table or the site's navigation. If Markdown fetching fails, try the normal page. If live access is unavailable, use available local docs or installed SDK types, state that limitation, and avoid inventing version-dependent details.

Per-task starting points:

| Task | Start here; follow the relevant details |
| --- | --- |
| Understand the programming model | [System One](https://docs.typesafe.ai/concepts/system-one.md), [building guide](https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md) |
| Explore what to build | [Use-case map](https://docs.typesafe.ai/concepts/use-case-map.md), then relevant cookbooks from the index |
| Prepare inputs and questions | [State](https://docs.typesafe.ai/concepts/state.md), [primitives](https://docs.typesafe.ai/primitives.md), then the chosen primitive's page |
| Decide how to handle uncertainty | [Confidence](https://docs.typesafe.ai/confidence.md) |
| Write API code | [HTTP API](https://docs.typesafe.ai/api.md), [Python SDK](https://docs.typesafe.ai/sdk/python.md), or [JavaScript SDK](https://docs.typesafe.ai/sdk/javascript.md) |
| Update an older integration | [Migration guide](https://docs.typesafe.ai/migrating-to-v1.md) and the installed SDK's current reference |

### Primitives

Choose by what the answer means, then read the relevant primitive page.

| Need | Primitive | Important distinction |
| --- | --- | --- |
| One of a defined set | [Choice](https://docs.typesafe.ai/primitives/choice.md) | Picks one option; its distribution compares competing options |
| Whether a condition holds | [Noul](https://docs.typesafe.ai/primitives/noul.md) | Probability of yes; no separate confidence; use one per label when several may apply |
| Degree along a described dimension | [Score](https://docs.typesafe.ai/primitives/score.md) | Probability-weighted position on ordered levels; use comparable per-item Scores for graded ranking |

### Designing judgments

Give each question enough relevant **state** to answer: source text, identities, relationships, policies, and current facts. Prefer named JSON fields when context has several parts. Put the judgment in **instructions** and define its possible answers in **criteria**.

- Question IDs are for code and are not sent to the model; include complete meaning in the question.
- Reference nested state with backticked paths such as `` `ticket.messages[0].text` ``.
- Ask one narrow, coherent judgment per question. Split independently useful dimensions, without destroying the relationship being judged. A bounded action selection or contextual interpretation is valid; atomic does not mean literal fact extraction or a one-sentence limit.
- Strings work for simple questions. Use structured objects or arrays when definitions, contrasts, exclusions, or examples clarify instructions or criteria.
- Score levels must describe concrete situations and stand on their own.
- Keep the needed answers available. Include a no-match outcome when nothing may fit; use a separate presence judgment when it is independently useful. For source-value selection, check candidate coverage: the model cannot choose an omitted value.

### Application patterns

- **Route and fill known arguments.** A request can select a handler and its typed parameters. Ask useful branch-specific questions up front and consume only the relevant answers. Explore [function calling](https://docs.typesafe.ai/cookbooks/function_calling.md) and [speculative fan-out](https://docs.typesafe.ai/patterns/fan-out.md).
- **Select instead of generate.** Find candidate values or source spans in code, use a judgment to select the intended one, then copy or normalize it. Code can also assemble source text into a formatted document or reading guide. Explore [value extraction](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook.md) and [structure recovery](https://docs.typesafe.ai/cookbooks/autoformat.md).
- **Find and judge evidence.** Retrieve candidates, compare their relevance to a query, and select useful context. Explore [reranking](https://docs.typesafe.ai/cookbooks/rerank_typesafe.md) and [hierarchical classification](https://docs.typesafe.ai/cookbooks/hierarchical_classification.md).
- **Turn judgments into reusable data.** Score dimensions once, then let code or user controls change weights, thresholds, rankings, and views. With labeled outcomes, those signals can become classical ML features. Explore [composite scoring](https://docs.typesafe.ai/patterns/composite-scoring.md) and [feature discovery](https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery.md).
- **Verify and escalate.** Check specific claims or fields against their evidence; send uncertain or failing cases to a person or reasoning model. Explore [citation checks](https://docs.typesafe.ai/cookbooks/citation_check.md) and [extraction cascades](https://docs.typesafe.ai/cookbooks/sde_cascade.md).
- **Respond to changing state.** Code can retain goals and observations while fresh judgments guide the next bounded step. Keep inferred state distinct from observed facts, and check freshness before applying a result to a changed situation.

### Uncertainty and confidence

Use probabilities and confidence to guide behavior, with thresholds evaluated on the user's data and consequences.

- Choice/Score confidence summarizes distribution concentration, not overall workflow correctness or permission to act.
- A Noul near 0.5 means similar probability for yes and no, not medium intensity.
- Several acceptable alternatives can also spread probability; low confidence need not invalidate a harmless preference choice.
- Ignore uncertainty on unused branches.

### Composition, verification, and policy

- **Ask independent questions over the same state together**, including useful speculative questions. They run in parallel and cannot see one another's answers. State each speculative premise explicitly; code consumes the applicable answers.
- A second request is warranted when an earlier answer is needed to fetch evidence, construct new state, or determine the next options.
- Extra questions still use tokens; measure actual request budgets, cost, and end-to-end latency.
- Keep policy explicit and raw judgments reusable. Weighted scores suit compensating preferences; an "any serious violation" rule needs separate conditions.
- Changing a weight or display filter need not rerun inference when evidence and question meanings are unchanged.
- Typed output guarantees the interface, not truth. System One models are trained for calibrated decisions; validate their performance in the target domain.
- Test representative cases and the resulting application behavior. For failures, inspect the exact state, questions, candidates, answers, composition, and observed outcome. Separate missing evidence, model errors, code errors, and service failures.
- Treat cookbook thresholds and demo results as examples to evaluate, not universal rules or permanent model limitations.
- Keep API credentials server-side in web apps.

## How it works

The skill drives the agent through a design-and-build loop rather than a fixed script:

1. **Read the live docs first.** Start from the documentation index, fetch the pages relevant to the task, and inspect the closest cookbook for a new workflow.
2. **Find the useful shape.** Start from the behavior the user wants, work backward to the judgments it needs, and add TypeSafe only where semantic understanding helps.
3. **Design the judgments.** Choose the primitive by what the answer means, supply the necessary state, put the judgment in instructions, and define possible answers in criteria as one narrow, coherent question.
4. **Compose and verify.** Ask independent questions over the same state together, batch speculative questions with explicit premises, escalate or re-request only when an earlier answer is needed, and validate on representative cases.

Guardrails the skill imposes: keep known rules, calculations, exact lookups, and execution in code; preserve the user's stack and scope; state the limitation if live docs are unavailable instead of inventing version-dependent details; use thresholds and cookbook results as examples to evaluate, not universal rules.

## Files

- `SKILL.md` — the full skill: programming model, live-docs routing table, primitives table, judgment design rules, application patterns, and composition/verification guidance.
- `LICENSE` — MIT License, Copyright (c) 2026 TypeSafe AI.

## Example prompts

```text
Design TypeSafe judgments for routing support tickets by intent, urgency, and required arguments.
```

```text
Replace this prompt-and-parse LLM step with a structured TypeSafe Choice plus confidence-based escalation.
```

```text
Use TypeSafe Score to rate candidate documents and rerank them for this query.
```

```text
Brainstorm what TypeSafe could make possible in this app, then recommend one pattern to start with.
```

## Install

```sh
./install.sh --target claude --skill typesafe-ai /path/to/project
```

`--target` defaults to `all` (install for every supported agent); `--target agents|claude|openclaude|zcode` selects one.

## Source and license

Upstream documentation: [https://docs.typesafe.ai/](https://docs.typesafe.ai/). This skill is distributed under the MIT License, declared as `license: MIT` in the skill frontmatter, with the bundled `LICENSE` file included in `skills/typesafe-ai/`.