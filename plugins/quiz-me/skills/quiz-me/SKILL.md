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

If `.claude/quiz-me-misses.md` exists, read it. Concepts the user has missed before
get priority in this round's questions.

Do not edit anything yet. Not one line, not "just to try it".

### 2. Quiz with `AskUserQuestion`

Ask **2-3 questions per round**, delivered through the `AskUserQuestion` tool as
multiple choice. Not prose questions — the user should be clicking options.

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
symptom. Vary which position holds the correct answer.

### 3. Grade every answer out loud

- **Correct** → confirm briefly, move on.
- **Wrong** → state the correct answer and explain *why* the chosen option fails.
  Then re-quiz that same point: reword the original question, and add a follow-up
  that probes the same concept from a different angle. Repeat until correct.
  Append one line to `.claude/quiz-me-misses.md` (create it if absent):
  `YYYY-MM-DD — <concept> — <what was missed>`

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

Then say plainly, once, that the change is shipping unverified, and log it to
`.claude/quiz-me-misses.md`. Overriding beats the user uninstalling the gate.

### 5. Post-implementation comprehension check

After the change, verify the user can explain what shipped:

- List **every distinct change** as `file:line — what it does`. Hide nothing. Do not
  gloss anything as "minor" or bundle edits together.
- **Quiz the substantive ones, cap at 5 questions.** Control flow, API shape, ordering,
  error handling, anything with design content. Mechanical edits — renames, import
  moves, formatting, mirrored boilerplate — get listed but not quizzed. State which
  ones were listed-only, so the gap is visible rather than silent.
- For each quizzed change, ask the user to explain what it does and why it was needed.
  Use `AskUserQuestion` again.
- Give an explicit per-item verdict: **understood** / **partial** / **gap**. Name the
  ones the user got wrong or could not explain, and fill those in. Log gaps to
  `.claude/quiz-me-misses.md`.
- Close with a tally: `4/5 understood — gap on the serializer change`.
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
{ "enforce": true, "ttlMinutes": 240 }
```

Project config wins over global. `QUIZ_ME_ENFORCE=1` in the environment also arms it.

`ttlMinutes` expires the marker so a forgotten pass does not unlock a whole day; `0`
disables expiry.

Known limit: the hook covers file-editing tools, not shell commands. A `sed -i` still
goes through. That is deliberate — the marker itself has to be writable, and the gate
is a commitment device, not a sandbox.

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
moment there is. `/quiz-me:review [n]` re-quizzes the user on the last `n` commits cold —
no diff shown, no commit message restated — and grades **retained** / **fuzzy** / **lost**.
Suggest it when the user has shipped several gated changes and wants to know what stuck.

## Anti-patterns

**Asking for preferences instead of knowledge.** "Should we fix this at the filter
layer or the view layer?" is a design question, not a quiz question. A quiz question
has one answer that is correct about the code as it exists.

**Leaking the answer.** Do not let question phrasing, option length, or option order
identify the correct choice. Avoid "all of the above" and throwaway joke distractors.

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
