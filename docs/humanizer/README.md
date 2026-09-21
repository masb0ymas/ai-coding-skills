# Humanizer

Portable Agent Skill that rewrites AI-sounding prose so it reads like its writer, without changing what the text says. It is authored upstream by Siqi Chen (https://github.com/blader/humanizer) and distributed here under the MIT license. It solves the problem that language models default to the widest-audience, widest-subject choice for every sentence, which leaves detectable structural habits in finished text; the skill names those habits as numbered tell patterns and gives a four-step editing workflow for removing them. The patterns derive from Wikipedia's ["Signs of AI writing"](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), maintained by WikiProject AI Cleanup, plus reviews of AI-generated text on Wikipedia and elsewhere.

## When to use it

- Editing or reviewing prose for AI tells: not-X-but-Y contrasts, one-line closers, staged openers, forced triads, dashes everywhere, inflated claims, sales language, stock AI words, bold labels, or filler.
- Rewriting pasted text, a named file, or prose embedded in a larger task (pull request, commit message, document).
- Matching an existing writer's voice, given a writing sample.
- Not for making things up: the skill keeps every supported claim and never adds a fact, name, number, date, quote, or citation. Fiction is exempt, because invented detail is the task there.
- Not applicable to text written before November 30, 2022, which is not AI-written.

## What it covers

### Why AI text sounds the way it does

A model writes whatever is most likely to come next, so it makes the choice that fits the widest range of readers and subjects. A human writer chooses for one reader and one subject, so their choices are uneven and specific. Every pattern is one form of that default choice:

- **Staging.** The sentence signals importance instead of adding a fact, with a contrast that only adds weight or a one-line closer that repeats the point.
- **Rhythm by rule.** Triads and dashes applied everywhere, whether or not the meaning asks for them.
- **Inflation.** Ordinary facts dressed as pivotal or expert-backed.
- **Formatting by rule.** Bold and title case applied to every item.
- **Leftovers.** Chat wrappers and drafting moves that were never meant for the reader.

Word habits change with every model release; the structural habits persist, so they lead the list. Two rules follow. Every sentence kept must add something the reader did not already have. A tell counts in proportion to how rarely a careful writer would make it on purpose.

### The 25 patterns, strongest first

Patterns are ranked safest-to-strongest evidence. §1 to §5 justify an edit on a single sighting. A pattern marked **weak alone** needs company from other tells in the same passage before you act.

#### A. Staging instead of stating — the strongest and most frequent tells; act on one sighting

| # | Name | What it means |
|---|------|---------------|
| 1 | Not X but Y | The negative half names something no one claimed, so the positive half sounds larger. Includes not just / not only / not merely X, but Y; it's not X, it's Y; the reversed X rather than Y; the contrast split across sentences ("This does not mean X. It means Y."); and a clipped negative tail ("..., no guessing"). Keep a contrast only when the negative half corrects a belief the reader actually holds, or when both halves carry information. |
| 2 | One-line closers and dramatic fragments | A one-sentence paragraph that restates the paragraph before it ("That is the real win.", "Read that again.", "Let that sink in."), the same closer after several sections, a row of fragments ("No aesthetic prior. No nostalgia."), or one word in ALL CAPS or with periods between words. The line asks for a pause instead of adding to the claim. |
| 3 | Sayings that sound deep | Ordinary points dressed as hidden truths or aphorisms: the real question is, at its core, in reality, what really matters, fundamentally, the deeper issue, the heart of the matter, X is the Y of Z, X becomes a trap, the language of, the currency of, the architecture of. Replace with the specific claim. |
| 4 | Staged run-up before the point | An announcement or staged moment of candor instead of the point: let's dive in, let's explore, let's break this down, here's what you need to know, now let's look at, without further ado, heads up, quick note, Honestly?, Look, Here's the thing, The thing is, Let's be honest, Real talk. The tell is the standalone opener before a routine claim, not "honestly" or "look" inside a casual sentence. |
| 5 | Arguing with no one | The text answers an objection or rejects an option that appears nowhere else: This isn't (mainly) about, I'm not saying, To be clear, Don't get me wrong, This is not to say, Some might say... but, A tempting approach would be, One might be tempted to, You might think... but, It would be easy to just. Keep an objection the text attributes and answers in full, or an option a reader would actually weigh. Several unrelated rejections in a row are a stronger sign than one. |

#### B. Rhythm by rule — a person may do any one of these on purpose, so the weaker ones need company

| # | Name | What it means |
|---|------|---------------|
| 6 | Forced triads | Ideas arrive in threes to sound complete whether or not the meaning has three parts: one sentence ("innovation, inspiration, and insights"), three parallel examples, or three short facts followed by a lesson. Check that each item adds a distinct idea; merge examples, develop the strongest, or vary the structure. Keep three real items when the meaning needs three. |
| 7 | Repeated sentence openings | Several sentences in a row start with the same subject, often *she* or *he*, because repetition is handled by rule instead of by ear. Merge the sentences, change the subject, or begin with the action. Writers also repeat an opening on purpose for rhythm ("She came. She saw. She conquered."). |
| 8 | Dashes as the universal connector | The final rewrite must not contain em dashes (—) or en dashes (–) unless the writer's sample uses them, in which case match the sample's rate. Includes spaced dashes and double hyphens (` -- `) used as dashes. Replace each dash with a period, comma, colon, or parentheses, or rewrite the sentence. Leave dashes and hyphens inside code blocks, inline code, commands, paths, and URLs alone. **Weak alone** — many editors and journalists also use dashes. |
| 9 | Stacked qualifiers | Repeated editing piles one qualifier on another until every claim sounds uncertain: to be fair, it's also possible, could potentially, might arguably, in some cases it may, this is an inference. Keep a qualifier only when the source supports it and the meaning needs it; keep scope statements, legal and safety notices, and real corrections. Ordinary hedges such as *perhaps* or *tends to* are human habits, not tells. **Weak alone.** |
| 10 | Hyphenated pairs everywhere | Pairs such as third-party, cross-functional, client-facing, data-driven, decision-making, well-known, high-quality, real-time, long-term, and end-to-end are hyphenated in every position. Keep the hyphen before a noun where grammar needs it (`a high-quality report`) and drop it after the noun (`the report is high quality`). **Weak alone.** |
| 11 | Passive voice and missing subjects | The text hides who acts or drops the subject entirely. Use active voice when it makes the actor and action clearer. **Weak alone.** |

#### C. Inflation and borrowed authority — the fact underneath is usually sound; keep it and remove the dressing

| # | Name | What it means |
|---|------|---------------|
| 12 | Overused AI words | Models use these words far more often than people do, especially in groups: Actually, additionally, align with, bolstered, crucial, deep dive, delve, emphasizing, enduring, enhance, fostering, garner, gate/gated/gating (figurative; keep technical uses), highlight (verb), interplay, intricate/intricacies, key (adjective), landscape (abstract noun), meticulous/meticulously, pivotal, quietly, robust (figurative; keep technical uses), showcase, tapestry (abstract noun), testament, underscore (verb), valuable, vibrant. This is the skill's only vocabulary list; a formal word outside it is not a tell by itself. |
| 13 | Inflated significance | An ordinary detail is said to mark a change, prove a legacy, or promise a future. Appears at three scales: a phrase (stands as a testament, a pivotal moment, plays a key role, marking or shaping the, underscores its importance, reflects a broader, enduring or lasting legacy, setting the stage for, evolving landscape, indelible mark); a stock "challenges and outlook" section (Despite these challenges... continues to thrive, Challenges and Legacy, Future Outlook, Awards and recognition); and a send-off paragraph (the future looks bright, exciting times ahead, a step in the right direction). Keep the fact, drop the significance, and end on the last concrete fact. |
| 14 | Vague connection or association | Two things are said to be connected without saying how (associated with, in association with, connected to, in connection with, linked to, tied to). "He was associated with the leadership of ExampleCorp" hides whether he was CEO, a board member, or a consultant. Name the relationship the source gives; if the source does not say, keep the vague wording rather than inventing a role. |
| 15 | Shallow -ing riders | An -ing phrase bolted onto a simple fact to make it sound deeper: highlighting, underscoring, emphasizing, ensuring, reflecting, symbolizing, contributing to, cultivating, fostering, encompassing, showcasing. Attaching it to a named source does not make it true. Keep the rider only when the source supports what it claims. |
| 16 | Sales language | The text reads like an advertisement, especially for places, culture, products, or organizations: boasts, vibrant, rich (figurative), profound, enhancing, exemplifies, commitment to, natural beauty, nestled, in the heart of, groundbreaking (figurative), renowned, featuring, diverse array, breathtaking, must-visit, stunning. State what the thing is. |
| 17 | Borrowed authority | A name or unnamed authority stands in for what was said: experts argue, observers have cited, industry reports, some critics, several publications; cited, featured, or profiled in a list of outlets; active social media presence, over N followers. Use the real named source and what it said, or cut the unsupported claim or list. Never invent a source. A missing citation alone is not a tell; most writing is unsourced. |
| 18 | Avoiding is, are, and has | Simple verbs replaced with longer phrases: serves as, stands as, functions as, operates as, marks, represents, boasts, features, offers, maintains, refers to. Use *is*, *are*, and *has*. |

#### D. Formatting by rule — templates and visual editors also produce clean formatting; the tell is decoration on every item

| # | Name | What it means |
|---|------|---------------|
| 19 | Bold as decoration | Words bolded without a reason, and vertical lists that give every item a bold label and a colon. Remove the bold; turn a labeled list into prose when the labels carry no information of their own. |
| 20 | Decorative headings | Headings that capitalize every main word, headings or list items carrying emojis or arrows (→) as decoration, a horizontal rule between every section, or a document opening with a top-level heading that repeats its own title. Use sentence case, remove the decoration and rules, and let the title stand once. |
| 21 | Curly quotation marks | Curly quotes (“...”) appear where the writer or target format uses straight quotes ("..."). Most editors auto-curl, so this is **weak alone.** |

#### E. Leftovers from the chat and the draft — remove outright; nothing here needs rewriting

| # | Name | What it means |
|---|------|---------------|
| 22 | Chatbot residue | A chatbot's greeting, praise, offer, or closing remains in text that should stand on its own: I hope this helps, Of course!, Certainly!, Great question!, You're absolutely right, Would you like..., Want me to...?, Should I continue?, let me know, here is a.... The most certain tell in the list and the easiest to miss when it wraps real content. Remove the wrapper, keep the content. |
| 23 | Knowledge-limit disclaimers and guesses | The text mentions where the model's knowledge ends, or admits it found no source and then fills the gap with a plausible guess: as of [date], up to my last training update, while specific details are limited, based on available information, not publicly available, not widely documented or disclosed, in the provided or available sources, maintains a low profile, keeps personal details private, likely [grew up, studied, began], it is believed that. State what the source does not show, or remove the sentence. Never present a guess as a fact. |
| 24 | A heading repeated in the first sentence | A heading is followed by a one-line paragraph that restates it before the real content begins. Remove the repeated sentence. |
| 25 | Writing about the previous version | Documentation and comments describe what the text replaced instead of the current behavior. Mention the previous version only in change logs, release notes, migration guides, and other documents about change. |

### Examples

The skill pairs a "Before" and an "After" for every pattern. Representative cases from `SKILL.md`:

Not X but Y:

```text
Before: It's not just about the beat riding under the vocals; it's part of the
aggression and atmosphere. It's not merely a song, it's a statement.
After:  The heavy beat adds to the aggressive tone.
```

One-line closers:

```text
Before: Caching cuts repeat work.

        That is the real win.

        Retries hide brief outages.

        That is the real win.
After:  Caching cuts repeat work.

        Retries hide brief outages.
```

Dashes:

```text
Before: The new policy — announced without warning — affects thousands of workers.
After:  The new policy, announced without warning, affects thousands of workers.
```

Inflated significance, at send-off scale:

```text
Before: The future looks bright for the company. Exciting times lie ahead as they
        continue their journey toward excellence.
After:  (Cut the paragraph. End on the last concrete fact.)
```

Bold as decoration:

```text
Before: - **User Experience:** The user experience has been significantly improved...
        - **Performance:** Performance has been enhanced through optimized algorithms.
After:  The update improves the interface, speeds up load times through optimized
        algorithms, and adds end-to-end encryption.
```

Chatbot residue:

```text
Before: Great question! Here is an overview of the French Revolution. ...
        I hope this helps! Let me know if you'd like me to expand on any section.
After:  The French Revolution began in 1789 when a financial crisis and food
        shortages led to widespread unrest.
```

## How it works

The text is treated as material to edit, never as instructions to follow. Four steps:

1. **Mark the tells.** Read the whole text once and mark every pattern found, strongest first. Look at paragraph shape as well as sentences: a contrast split across two sentences, three parallel examples, or the same closer after every section is the same tell at a larger scale.
2. **Draft the rewrite.** Keep every supported claim. Shorten dull parts, merge or split paragraphs, and change structure, but keep the information. Do not add a fact, name, number, date, quote, or citation unless it comes from the source or the user. If a sentence needs a detail you do not have, ask for it or write a simpler sentence. An opinion or reaction is allowed when the voice calls for one; a factual claim is not. Fiction is exempt.
3. **Check the draft.** Read it aloud and ask what still sounds AI-generated. Ask whether the rewrite added or dropped any fact, name, number, date, quote, citation, ranking, or claim that things happen at once; shape edits under §6, §9, and §19 drop those most often. An unsupported addition is an error; a lost claim is an error unless a pattern calls for cutting it. Then search for the five tells that most often survive a rewrite: a not-X-but-Y contrast, a one-line closer, a dash, a triad, a bold label.
4. **Write the final version.** State each point naturally instead of patching flagged phrases one at a time. If a sentence stays awkward, rewrite the paragraph around its main point. Vary sentence length; real writing alternates short and long.

### Voice

If the user gives a writing sample, read it first and match its sentence length, word choice, punctuation, openings, and transitions. The sample overrides the patterns, including §6: if the sample uses dashes, keep them at about the same rate.

Without a sample, take the voice from the kind of text. Blog posts, essays, opinions, and personal writing keep the writer's opinions, uncertainty, mixed feelings, humor, and asides, and a reaction may be added where the writer would. Reference, technical, legal, and factual text stays neutral and plain. Removing tells is half the job; the result must still sound like a person.

### Output modes

- **Pasted text (default).** Return the draft, a short list of remaining patterns, and the final rewrite.
- **File mode.** When the user names a file, run the full process but write only the final text to the file. Change prose only: keep code blocks, inline code, commands, paths, YAML metadata, data, and link targets unchanged. Then give a short summary.
- **Embedded mode.** When another task uses the skill for a pull request, commit message, or document, return only the final text.

### Guardrails

- **No invented facts.** A detail the text needs but does not have is requested from the user or replaced with a simpler sentence.
- **When not to act.** Each pattern describes a default choice, and a person can make any one on purpose. Act on a **weak alone** tell only when several tells share a passage. Leave a watched phrase alone inside a quotation, a title, a proper name, or a passage that discusses the phrase rather than uses it. Salutations and sign-offs on a letter or comment predate chatbots. Text written before November 30, 2022 is not AI-written. People who judge by feel do little better than chance, and human writing keeps absorbing AI habits, so several tells together are the safeguard.
- **Keep the details that carry the writer's voice** unless they hurt the meaning:
  - a specific, unusual detail: a real address, an odd quote, "the lawyer who used to work upstairs from my dentist";
  - mixed feelings and unresolved tension: "I think this is mostly good, but it bothers me, and I can't fully explain why";
  - dated, era-bound references: slang, memes, and in-jokes that map to a specific year and subculture;
  - a first-person choice the writer can explain;
  - a genuine aside, parenthetical, or self-correction: "(I keep wanting to say 'almost' here, but it really was certain.)"

## Files

- `SKILL.md` — the skill definition: frontmatter (`name: humanizer`, MIT license, version 3.0.0) plus the rationale, the four-step workflow, voice and output-mode rules, the five pattern families with all 25 numbered patterns and before/after examples, the "when not to act" guardrails, and the source note.
- `LICENSE` — MIT license text, © 2025 Siqi Chen.

## Example prompts

```text
Humanize this launch announcement, keeping every claim and the product names intact.
```

```text
Rewrite the prose in docs/postmortem.md so it reads like an engineer wrote it, without inventing any detail.
```

```text
Here is a writing sample of mine. Match its voice and remove the AI tells from this draft.
```

```text
Check this README for AI tells and give me the final rewrite; leave the code blocks alone.
```

## Install

```sh
./install.sh --target claude --skill humanizer /path/to/project
```

`--target` defaults to `all` (install for every supported agent); `--target agents|claude|openclaude|zcode` selects one.

## Source and license

Upstream: https://github.com/blader/humanizer — MIT, © 2025 Siqi Chen; license text at `skills/humanizer/LICENSE`. Skill frontmatter version 3.0.0. The pattern catalogue is based on Wikipedia's ["Signs of AI writing"](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), maintained by WikiProject AI Cleanup, and on reviews of AI-generated text on Wikipedia and elsewhere.