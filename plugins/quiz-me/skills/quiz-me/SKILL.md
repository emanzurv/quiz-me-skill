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

Do not edit anything yet. Not one line, not "just to try it".

### 2. Quiz with `AskUserQuestion`

Ask **2-3 questions per round**, delivered through the `AskUserQuestion` tool as
multiple choice. Not prose questions — the user should be clicking options.

Cover, in order:

1. **Root cause** — what is actually wrong (the cause, not the symptom).
2. **Mechanism** — which line/function produces the behavior, and why.
3. **Fix and blast radius** — what the change should be, and what else it affects.

Each question: one correct option plus plausible distractors. Draw distractors from
misconceptions that are genuinely tempting in *this* code — the neighboring function
that looks responsible, the plausible-but-wrong ordering, the fix that treats the
symptom. Vary which position holds the correct answer.

### 3. Grade every answer out loud

- **Correct** → confirm briefly, move on.
- **Wrong** → state the correct answer and explain *why* the chosen option fails.
  Then re-quiz that same point: reword the original question, and add a follow-up
  that probes the same concept from a different angle. Repeat until correct.

### 4. Implement only on a 100% pass

A partial pass does not unlock implementation. Every question in every round must be
answered correctly before the first edit.

If the user says "hold", "wait", or "you can't change it yet" and an edit has already
landed, revert that edit to its exact original text and go back to quizzing.

### 5. Post-implementation comprehension check

After the change, verify the user can explain what shipped:

- List **every distinct change** as `file:line — what it does`. Hide nothing. Do not
  gloss anything as "minor" or bundle edits together.
- For each change, ask the user to explain what it does and why it was needed. Use
  `AskUserQuestion` again.
- Give an explicit per-item verdict: **understood** / **partial** / **gap**. Name the
  ones the user got wrong or could not explain, and fill those in.
- Close with a tally: `4/5 understood — gap on the serializer change`.

Never credit understanding the user did not demonstrate.

## When to skip the quiz

- Pure lookups, reads, and questions
- Formatting, renames, one-line typos
- Mechanical edits with no design content
- The user already stated the root cause *and* the fix in their own prompt

When skipping, just do the work. Do not announce the skip.

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

**Editing while the quiz is open.** The gate is the whole feature.

## Optional: make it always-on

Skills load when invoked or when Claude judges them relevant. To make the gate apply
to every non-trivial change in a project, add a line to `CLAUDE.md`:

```markdown
Before implementing any non-trivial change, use the quiz-me skill.
```
