---
name: quiz-me
description: Quiz the user on root cause and intended fix BEFORE writing any non-trivial code, then verify comprehension of every change after. Use when the user asks for a bug fix, refactor, or feature and wants to stay technically sharp instead of vibe-coding. Also use when the user says "quiz me", "don't let me vibe code", or "explain it back to me first".
---

# Quiz Me

A gate that keeps the user in the loop. Claude investigates, then tests the user's
understanding with interactive multiple-choice questions. Code lands only after the
user answers every question correctly. After the change, Claude checks that the user
can explain each edit.

The quiz is **for the user**, not for Claude. Claude already knows the answers from
its investigation — the point is for the user to demonstrate them.

## Workflow

### 1. Investigate first — no edits

Read the real code. Find the actual root cause, the specific line or function that
produces the behavior, and what the fix touches. The quiz must be grounded in
findings from this codebase, never a generic pop quiz.

If a misses log exists for this project, read it. Concepts the user has missed before
get priority in this round's questions:

```bash
cat ~/.claude/quiz-me/"${PWD//\//_}".misses.md 2>/dev/null
```

The log lives under `~/.claude/quiz-me/`, never in the user's repo. Nothing this skill
writes lands in the working tree.

Do not edit anything yet. Not one line, not "just to try it".

### 2. Quiz with `AskUserQuestion`

Ask **the number of questions the difficulty sets** — 3 by default — delivered through
the `AskUserQuestion` tool as multiple choice. Not prose questions — the user should be
clicking options. See *Difficulty* below for the full shape of a round.

Pick the ladder that matches the work:

| Work | Ask about |
| :--- | :--- |
| **Bug fix** | 1. Root cause — what is actually wrong, not the symptom. 2. Mechanism — which line/function produces the behavior, and why. 3. Fix and blast radius. |
| **Feature** | 1. Constraint — what in the existing code forces this design. 2. Tradeoff — what the chosen approach gives up against the obvious alternative. 3. Break surface — what existing behavior this can break. |
| **Refactor** | 1. Invariant — which behavior must come out identical. 2. Proof — which test or call path demonstrates that. 3. Reach — every call site that moves, and what happens to the one that gets missed. |

Feature and refactor work has no root cause. Do not invent one to force the bug ladder,
and do not skip the quiz because the bug ladder does not fit.

Each question: one correct option plus plausible distractors. Draw distractors from
misconceptions that are genuinely tempting in *this* code — the neighboring function
that looks responsible, the plausible-but-wrong ordering, the fix that treats the
symptom.

#### Place the correct answer by rule, not by feel

The answer is the option you write first, because it is the one you already know. Left
alone, that lands it in slot 1 on every question and the quiz becomes a reflex. "Vary the
position" is not enough — variation is a property of a batch, and each question is
authored alone.

So compute the slot. Take the smallest line number the correct option cites, `mod` the
number of options, `+ 1`. That is the slot the correct answer goes in; the distractors
fill the rest in the order you drafted them. Four options and an answer citing
`gate.py:30` → `30 mod 4 + 1` → slot 3.

Draft the answer first. Place it last. The rule is deterministic for you and unguessable
for the user, which is the only combination that works.

#### Fill in every field the picker gives you

A bare question with four bare options wastes most of the UI. Every question sends:

- **`header`** — a progress chip, 12 characters max. Use `Q1/3 cause`, `Q2/3 mech`,
  `Q3/3 blast` for bugs; `Q1/3 limit`, `Q2/3 trade`, `Q3/3 break` for features;
  `Q1/3 invar`, `Q2/3 proof`, `Q3/3 reach` for refactors. The user should always know
  how many are left.
- **`label`** — the claim itself, 1-5 words. No leading numbers; the picker numbers them.
- **`description`** — one line of grounded detail that makes the option tempting. Keep
  every description within a few words of the same length.
- **`preview`** — the code that option blames, as it actually appears in the repo.

#### Previews are the whole trick — before the change only

`preview` renders a monospace panel beside the option list, so arrowing through answers
walks the user through the suspect code. Give every option a preview of the lines its
claim depends on: `file.js:7` plus real code, copied exactly — three or four lines at
`normal`, wider or narrower as the difficulty table sets.

These preview rules govern the pre-implementation rounds, where the suspect code is what
the user is reasoning about. The post-implementation check in step 5 runs with no previews
at all, which satisfies all-or-none rather than breaking it.

Rules that keep it a quiz instead of a giveaway:

- **All or none.** If one option has a preview, every option has one. A lone panel is a
  flashing arrow at the answer.
- **Equal weight.** Same line count across options, within one line. Same style of
  excerpt. The longest panel must not be the correct one more often than chance.
- **Real lines only.** Never synthesize code for a distractor. If an option blames code
  that does not exist, that option is not tempting, it is filler — cut it.
- Previews only work on single-select questions. Quiz questions are always single-select.

#### Chrome

Open each round with a rule line, so the quiz reads as a thing that started and will end:

```
━━━ 🧠 QUIZ ME · round 1 · root cause ━━━━━━━━━━━━━━━━━━━━
```

Use a plain rule, not a full box — a box whose width does not match the terminal looks
broken, and the user's terminal width is unknown.

### 3. Grade every answer out loud

- **Correct** → confirm briefly, move on.
- **Wrong** → state the correct answer and explain *why* the chosen option fails.
  Then re-quiz that same point: reword the original question, and add a follow-up
  that probes the same concept from a different angle. Repeat as the difficulty sets —
  once at `easy`, until correct at `normal`, until correct with the rung restarting at
  `hard`. Append one line to the project's misses log (create it if absent):

  ```bash
  mkdir -p ~/.claude/quiz-me && echo "YYYY-MM-DD — <concept> — <what was missed>" \
    >> ~/.claude/quiz-me/"${PWD//\//_}".misses.md
  ```

Close each round with a scorecard — a 12-cell bar, one line per question, then the state
of play:

```
━━━ 🧠 SCORE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ▓▓▓▓▓▓▓▓░░░░  2/3

  ✅ cause      forEach drops the promise the callback returns
  ✅ mech       the count is computed before any insert has run
  ❌ blast      missed that callers now need the failed rows back

  one to go — re-asking the blast radius from a different angle
```

Fill cells in proportion to correct answers, `▓` filled and `░` empty. On a clean sweep,
say so and open the gate:

```
  ▓▓▓▓▓▓▓▓▓▓▓▓  3/3 — 🔓 gate open, writing the fix
```

**The answer key can be wrong.** The key comes from Claude's investigation, and that
investigation can be wrong. If the user picks a different option *and* supplies a
mechanism for it, stop grading and re-read the code before ruling. When the user turns
out to be right, say so plainly and correct the key. A gate that can only fail the user
is a gate that launders Claude's mistakes into the user's head.

### 4. Implement only on a 100% pass

A partial pass does not unlock implementation. Every question in every round must be
answered correctly before the first edit.

On a full pass, unlock the enforcement gate before editing:

```bash
mkdir -p ~/.claude/quiz-me && echo pass > ~/.claude/quiz-me/"${PWD//\//_}".pass
```

The marker lives outside the repo, so nothing lands in the user's working tree. A
project-local `.claude/quiz-me.pass` also unlocks, for repos that prefer it.

If the user says "hold", "wait", or "you can't change it yet" and an edit has already
landed, revert that edit to its exact original text and go back to quizzing.

**Escape hatch.** The loop in step 3 has no natural exit, and 2am incidents do not wait
for multiple choice. If the user explicitly says to override — "quiz override", "ship
it, I'll learn it later" — honor it. Do not argue, and do not require a reason.

```bash
mkdir -p ~/.claude/quiz-me && echo "override: <reason or 'none given'>" > ~/.claude/quiz-me/"${PWD//\//_}".pass
```

Then say plainly, once, that the change is shipping unverified, and log it to the misses
log (`~/.claude/quiz-me/"${PWD//\//_}".misses.md`). Overriding beats the user uninstalling
the gate.

### 5. Post-implementation comprehension check

After the change, verify the user can explain what shipped:

- List **every distinct change** as `file:line — what it does`. Hide nothing. Do not
  gloss anything as "minor" or bundle edits together.
- **Quiz the substantive ones**, capped at the round size the difficulty sets — 2 at
  `easy`, 3 at `normal`, 5 at `hard`. Control flow, API shape, ordering,
  error handling, anything with design content. Mechanical edits — renames, import
  moves, formatting, mirrored boilerplate — get listed but not quizzed. State which
  ones were listed-only, so the gap is visible rather than silent.
- For each quizzed change, ask **one single-select `AskUserQuestion` multiple choice**
  covering what the edit does and why it was needed. Never a prose question — no "explain
  this edit in your own words", no free-text recall. Every answer is a click, same as
  before the change.
- **No `preview` on these questions.** The panel would show the lines that just landed,
  which is the answer. Ground the options in `file:line` references in the `description`
  instead, and draw distractors from the other edits in this batch and from what the code
  did before the change. The slot rule still applies — place the correct answer at
  `line mod options + 1`, off the `file:line` its description cites.
- Give an explicit per-item verdict: **understood** / **partial** / **gap**. Name the
  ones the user got wrong or could not explain, and fill those in. Log gaps to
  `~/.claude/quiz-me/"${PWD//\//_}".misses.md`.
- Close with the receipt — verdict column, `file:line`, then what the edit does:

```
━━━ 🧠 RECEIPT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ✅  importUsers.js:4   for...of so each insert is awaited
  ✅  importUsers.js:12  returns the failed rows, not just a count
  ⚠️   db.js:22          insertUser takes a client for one transaction
  ✅  db.js:31           rollback on partial batch failure

  ▓▓▓▓▓▓▓▓▓░░░  3/4 understood — partial on the shared transaction
  🔒 gate re-locked
```

Verdict marks: `✅` understood, `⚠️` partial, `❌` gap. Mechanical edits that were listed
but not quizzed get `·` and a `not quizzed` note, so the receipt never overstates what was
checked.

- Re-lock the gate for the next change:

```bash
rm -f ~/.claude/quiz-me/"${PWD//\//_}".pass .claude/quiz-me.pass
```

Never credit understanding the user did not demonstrate.

## Plan mode

Plan mode and this gate are independent. Plan mode blocks edits until the user
approves a plan; the quiz blocks edits until the user demonstrates understanding.
Approving a plan is a click, not a demonstration — it never substitutes for the quiz.

Order: investigate → write the plan → `ExitPlanMode` → **quiz** → first edit. Once the
plan is approved, run the quiz before touching a file, grounded in the approved plan's
root cause and fix. A plan Claude wrote is not the user stating root cause and fix, so
the skip rule below does not apply to it.

Do not quiz inside plan mode. Present the plan first, so the questions are about the
change that is actually happening.

## Enforcement

Prose alone does not stop an edit. The plugin ships a `PreToolUse` hook that denies
`Edit`, `Write`, and `NotebookEdit` until a pass marker exists for the current directory.
A `SessionStart` hook deletes that marker, so every session starts locked.

Enforcement is **off by default** — it would otherwise block one-line typo fixes. Arm it
for one project with `.claude/quiz-me.json`, or for every project with
`~/.claude/quiz-me.json`:

```json
{ "enforce": true, "ttlMinutes": 240, "difficulty": "hard" }
```

Keys merge, global first, project on top — so a project file setting only `enforce` still
inherits the global `difficulty`. `QUIZ_ME_ENFORCE=1` in the environment also arms it, and
`QUIZ_ME_DIFFICULTY` overrides the level for one session.

`ttlMinutes` expires the marker so a forgotten pass does not unlock a whole day; `0`
disables expiry.

Known limit: the hook covers file-editing tools, not shell commands. A `sed -i` still
goes through. That is deliberate — the marker itself has to be writable, and the gate
is a commitment device, not a sandbox.

## Difficulty

`difficulty` is `easy`, `normal`, or `hard`; unset or unrecognized reads as `normal`. It
is one dial that moves four levers together, so a level is a whole shape of round rather
than a single number:

| | `easy` | `normal` | `hard` |
|---|---|---|---|
| **Questions per round** | 2 | 3 | 5 |
| **Options per question** | 3 | 4 | 4 |
| **Distractors** | one clearly wrong, the rest plausible | every one plausible | every one a near-miss, differing from the answer by a single mechanism detail |
| **Previews** | 5-6 lines, enough context to reason from the panel alone | 3-4 lines | 2 lines, too narrow to settle it without reading the file |
| **Wrong answer** | explain, re-ask once, move on either way | re-ask until correct | re-ask until correct, and the rung restarts — a wrong answer on Q4 sends the round back to Q1 |

Read the level from config before writing the first question. When enforcement is armed,
the gate's deny message names the level and its shape, so the round is already specified
by the time an edit is attempted.

Two rules do not scale. The slot rule holds at every level — `easy` does not mean the
answer sits in slot 1. All-or-none holds too: `easy` gives wider panels, never a panel on
some options and not others.

`hard` mode makes the gate genuinely expensive. Five questions with near-miss distractors
and a restarting rung can cost several rounds before an edit lands. That is the point of
the level, but it is worth choosing deliberately rather than globally.

## When to skip the quiz

The test is mechanical, so the gate fires consistently: **if understanding the change
required reading more than one file, quiz.** Otherwise skip.

Always skip:

- Pure lookups, reads, and questions
- Formatting, renames, one-line typos
- Mechanical edits with no design content
- The user already stated the root cause *and* the fix in their own prompt

When skipping, just do the work. Do not announce the skip.

## Cold review

Passing right after implementing proves recall at peak context, which is the easiest
moment there is. `/quiz-me:review [n]` re-quizzes the user on their last `n` commits cold
— no diff shown, no commit message restated — and grades **retained** / **fuzzy** /
**lost**. Scope is the user's own commits touching files their sessions edited, so a
teammate's work on the branch never shows up.
Suggest it when the user has shipped several gated changes and wants to know what stuck.

## Anti-patterns

**Asking for preferences instead of knowledge.** "Should we fix this at the filter
layer or the view layer?" is a design question, not a quiz question. A quiz question
has one answer that is correct about the code as it exists.

**Leaking the answer.** Do not let question phrasing, option length, or option order
identify the correct choice. Order is the one that slips silently — apply the slot rule
every time. Avoid "all of the above" and throwaway joke distractors.

**Quizzing before investigating.** A question you cannot grade with certainty is not
a quiz question.

**Softening a wrong answer.** If the user picks wrong, say so plainly and explain the
mechanism. The value of the gate is that it can fail.

**Defending a wrong answer key.** The gate must be able to fail Claude too.

**Editing while the quiz is open.** The gate is the whole feature.

## Optional: make it always-on

Skills load when invoked or when Claude judges them relevant. To make the gate apply
to every non-trivial change in a project, add a line to `CLAUDE.md`:

```markdown
Before implementing any non-trivial change, use the quiz-me skill.
```
