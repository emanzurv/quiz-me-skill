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
get priority in this round's questions. Pull the streak in the same call — one read
covers both files that exist, and a missing one just produces no output for its half:

```bash
r=$(git rev-parse --show-toplevel 2>/dev/null || pwd); f=~/.claude/quiz-me/"${r//\//_}"
cat "$f".misses.md "$f".streak 2>/dev/null
```

The log lives under `~/.claude/quiz-me/`, never in the user's repo. Nothing this skill
writes lands in the working tree.

Derive the key from the repo root, not from `$PWD`. The hook starts from the payload's
`cwd`, which is where the session started, and then walks up to the repo root that
contains it, so both sides land on the same filename even when the session began in a
subdirectory. `gate.py` also resolves symlinks and falls back to a case-insensitive
match, so the two agree when the paths disagree on case. The repo root is what keeps them
agreeing in the first place — key off anything else and the marker is written under a
name the hook never checks, leaving the gate closed with nothing to unlock it but TTL
expiry. Every snippet below opens with the same `r=`/`f=` pair.

#### Open concepts carry forward

Every line is `YYYY-MM-DD — <concept> — <what was missed>`, except a resolution line,
which is `YYYY-MM-DD — <concept> — RESOLVED`. `override` is reserved: the escape hatch
logs under it, and those lines are bookkeeping, not misses. Nothing counts them as an
open concept — two overrides in a row would otherwise promote a concept the user never
got wrong to 🐉 boss — so never file a real miss under that name. A concept is **open** if its most recent
line (by position in the file) is a miss, not a `RESOLVED`. Group lines by the exact
`<concept>` text to find the latest one.

Any open concept that the current change touches gets a guaranteed question this round —
on top of the ladder, not instead of it if the round size allows, and swapped in for the
least load-bearing ladder question if it doesn't. Reword it: same concept, a different
angle than the line that was missed, never the identical question repeated. Tighten its
distractors one notch past whatever the configured difficulty would otherwise give it —
`easy` gets `normal`-grade plausibility, `normal` and `hard` get near-misses.

A concept with **two or more** open misses in a row — missed, re-asked, missed again,
never resolved — is a **boss concept**. When one applies this round, open with one boss
question before the ladder, marked with 🐉 in its header (e.g. `🐉 boss`). A boss question
always gets `hard`-width previews (2 lines) and near-miss distractors, and a wrong answer
restarts the whole round from Q1 — regardless of the project's configured difficulty.
This is the one place a level's shape does not hold; say so plainly when it fires, so it
reads as a deliberate escalation and not a bug in the difficulty table.

When a question in this round is answered correctly on a concept that had an open miss,
queue a resolution line for it — same rule as every other write in this skill: note it
down, do not shell out mid-round. It ships in step 4's unlock call, alongside whatever
misses step 3 queued:

```
YYYY-MM-DD — <concept> — RESOLVED
```

The post-implementation check (step 5) resolves the same way, queued into its own
batch-end call. Lines from before this convention existed have no `RESOLVED` counterpart
and read as open — that is correct, not a bug; an old miss nobody ever confirmed fixed
should still surface.

Do not edit anything yet. Not one line, not "just to try it".

### 2. Quiz with `AskUserQuestion`

**Brief the user before the first question.** Investigation happened silently in step 1
— the user has not seen it. Two to four plain sentences, before the round banner: what
was asked for, which file(s) and function(s) are in play, and what kind of change this
is (bug fix / feature / refactor). Not the answers — the questions still have to be
answered — but enough orientation that a preview panel is something the user can reason
about, not a cold-open trivia question about code they don't know is even involved. A
quiz with no preceding context is not gradable fairly; the user can only guess at a
question whose subject they were never told.

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
  `Q1/3 invar`, `Q2/3 proof`, `Q3/3 reach` for refactors; `🐉 boss` for a boss question
  (no `Qn/N` — a boss question sits outside the round's count). The user should always
  know how many are left. Keep iconography rare and load-bearing: 🐉 marks a state that
  doesn't fire every round; do not add a per-category emoji that would repeat on every
  single question — that's decoration competing with signal, not adding it, and stacks
  of unfamiliar glyphs are a big part of why this looked cluttered before. Verdicts use
  three plain colors and nothing else: 🟢 correct/understood, 🔴 wrong/gap, 🟡 partial —
  never `✅`/`❌`/`⚠️`, whose variation-selector codepoints render double-width in some
  terminals and break column alignment in a scorecard or receipt.
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

Open each round with a rule line, so the quiz reads as a thing that started and will end.
Read the streak (see *Streak* below) and append it when it is nonzero — it is the one
piece of state that survives across batches, so it belongs on the banner, not buried in
the scorecard. Nonzero:

```
── QUIZ ME · round 1 · root cause · streak 5 ──
```

Zero or unset, drop the segment entirely rather than printing `streak 0`:

```
── QUIZ ME · round 1 · root cause ──
```

Use a short bookend rule, not a full-width box — a rule sized to the terminal is
guesswork the terminal's actual width breaks, and two dashes on each side reads as
deliberate framing without pretending to know that width. If a boss question opens the
round, say so on its own line right after the banner, once, before asking it:

```
🐉 boss — this concept has come back twice unresolved. Wrong here restarts the round.
```

### 3. Grade every answer out loud

- **Correct** → confirm briefly, move on.
- **Wrong** → state the correct answer and explain *why* the chosen option fails.
  Then re-quiz that same point: reword the original question, and add a follow-up
  that probes the same concept from a different angle. Repeat as the difficulty sets —
  once at `easy`, until correct at `normal`, until correct with the rung restarting at
  `hard`. This batch is no longer a clean sweep — see *Streak* — even once the retry
  lands correctly; the streak only rewards getting it right the first time. Queue a
  misses-log line (concept and what was missed); do not shell out per wrong answer —
  every queued line ships in the single unlock call in step 4, once the round actually
  passes.

Close each round with a scorecard — a 12-cell bar, one line per question, then the state
of play:

```
── SCORE ──

  🟩🟩🟩🟩🟩🟩🟩🟩🟥🟥🟥🟥  2/3

  🟢 cause      forEach drops the promise the callback returns
  🟢 mech       the count is computed before any insert has run
  🔴 blast      missed that callers now need the failed rows back

  one to go — re-asking the blast radius from a different angle
```

Fill cells in proportion to correct answers, 🟩 filled and 🟥 empty. On a clean sweep,
say so and open the gate:

```
  🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩  3/3 — 🔓 gate open, writing the fix
```

**The answer key can be wrong.** The key comes from Claude's investigation, and that
investigation can be wrong. If the user picks a different option *and* supplies a
mechanism for it, stop grading and re-read the code before ruling. When the user turns
out to be right, say so plainly and correct the key. A gate that can only fail the user
is a gate that launders Claude's mistakes into the user's head.

### 4. Implement only on a 100% pass

A partial pass does not unlock implementation. Every question in every round must be
answered correctly before the first edit.

On a full pass — and out of plan mode, never inside it — unlock the enforcement gate
before editing, in the same call that flushes whatever misses and resolutions were
queued in steps 1 and 3 (skip the `>>` clause if nothing was queued — a clean-on-first-try
round has nothing to flush):

```bash
r=$(git rev-parse --show-toplevel 2>/dev/null || pwd) \
  && mkdir -p ~/.claude/quiz-me && f=~/.claude/quiz-me/"${r//\//_}" \
  && { echo "2024-01-01 — concept a — what was missed"; \
       echo "2024-01-01 — concept b — RESOLVED"; } >> "$f".misses.md \
  && echo pass > "$f".pass
```

The marker lives outside the repo, so nothing lands in the user's working tree. A
project-local `.claude/quiz-me.pass` also unlocks, for repos that prefer it.

**Write it once per batch, not once per edit.** One passing quiz covers the whole unit of
work it was about — every file, every edit, however many tool calls that takes. The hook
reads the marker, it does not consume it, so re-running the unlock between edits is noise.
If an edit is denied after a pass, the marker is missing or expired; check `ttlMinutes`
rather than re-arming reflexively.

If the user says "hold", "wait", or "you can't change it yet" and an edit has already
landed, revert that edit to its exact original text and go back to quizzing.

**Escape hatch.** The loop in step 3 has no natural exit, and 2am incidents do not wait
for multiple choice. If the user explicitly says to override — "quiz override", "ship
it, I'll learn it later" — honor it. Do not argue, and do not require a reason.

```bash
r=$(git rev-parse --show-toplevel 2>/dev/null || pwd) \
  && mkdir -p ~/.claude/quiz-me && f=~/.claude/quiz-me/"${r//\//_}" \
  && echo "2024-01-01 — override — <reason or 'none given'>" >> "$f".misses.md \
  && echo "override: $CLAUDE_CODE_SESSION_ID — <reason or 'none given'>" > "$f".pass \
  && echo 0 > "$f".streak
```

The session id is not decoration. A pass marker unlocks any session in the project until
it expires — passing the quiz is knowledge, and knowledge is not scoped to one transcript
— but an override is a bypass the user granted to *this* session, so it carries the id and
unlocks nothing else. "Don't quiz me" said here does not disarm the gate in the other
window, and it does not outlive this conversation. Write the id in, always: an override
line with a reason where the id belongs matches no session and unlocks nothing, which is
the safe direction to fail but reads as the gate ignoring an override the user granted.

Then say plainly, once, that the change is shipping unverified. Overriding beats the
user uninstalling the gate.

### 5. Post-implementation comprehension check

Run this **once, at the end of the batch** — after every edit the quiz covered has landed,
not after each one. Mid-batch checks fragment one unit of work into several quizzes, which
is the thing that makes the gate feel like it fires per change.

Verify the user can explain what shipped:

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
  ones the user got wrong or could not explain, and fill those in. Queue a misses-log
  line for each gap and a `RESOLVED` line (see *Open concepts carry forward* in step 1)
  for any open concept this batch's edits addressed and the user answered correctly here
  — queue means note it down, do not shell out yet. They land in the single batch-end
  write below, along with everything else this step needs to persist. A `partial` or
  `gap` on any item is also a broken streak, same as a wrong answer in step 3.
- Close with the receipt — verdict column, `file:line`, then what the edit does:

```
── RECEIPT ──

  🟢  importUsers.js:4   for...of so each insert is awaited
  🟢  importUsers.js:12  returns the failed rows, not just a count
  🟡  db.js:22           insertUser takes a client for one transaction
  🟢  db.js:31           rollback on partial batch failure

  🟩🟩🟩🟩🟩🟩🟩🟩🟩🟥🟥🟥  3/4 understood — partial on the shared transaction
  🔒 gate re-locked
```

Verdict marks: `🟢` understood, `🟡` partial, `🔴` gap. Mechanical edits that were listed
but not quizzed get `·` and a `not quizzed` note, so the receipt never overstates what was
checked.

- Close the batch with **one** shell call — every queued misses/RESOLVED line, the
  streak update, and the re-lock together, `&&`-chained. Not one command per line item;
  one command for the whole close-out, every time, so approving it once covers the
  batch instead of prompting per line:

  ```bash
  r=$(git rev-parse --show-toplevel 2>/dev/null || pwd) \
    && mkdir -p ~/.claude/quiz-me && f=~/.claude/quiz-me/"${r//\//_}" \
    && { echo "2024-01-01 — concept a — what was missed"; \
         echo "2024-01-01 — concept b — RESOLVED"; } >> "$f".misses.md \
    && cur=$(cat "$f".streak 2>/dev/null || echo 0) \
    && echo $(( clean_sweep ? cur + 1 : 0 )) > "$f".streak \
    && rm -f "$f".pass "$r"/.claude/quiz-me.pass
  ```

  Omit the misses-append clause entirely on a batch with nothing queued — an empty
  `{ }` block still runs and still counts as a call. `clean_sweep` is `1` only if every
  question in every pre-implementation round and this check was answered correctly on
  the first try; an override batch (*Escape hatch*) is never clean, and always writes
  `0` regardless of what the post-check found, since the pre-quiz that would have earned
  the streak never ran.

  Every state write this skill makes shares the one prefix, `mkdir -p ~/.claude/quiz-me
  && ...` under that directory, or `rm -f` on the two pass-marker paths — nothing else.
  Approving that prefix once (a project or user permission rule) clears every future
  quiz-me write silently; re-approving the same shape on every call is the friction to
  avoid, so keep new state inside this one directory and this one command family rather
  than inventing a new shape per feature.

Re-locking is the last part of that call, never a step between edits. The next quiz
belongs to the next unit of work.

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

Do not write the pass marker inside plan mode either. Plan mode denies every write and
every side-effecting shell command, so the unlock command is denied there — and it is not
due yet: the marker is only read when an edit is attempted, which cannot happen until the
plan is approved. An edit attempted in plan mode gets the gate's plan-mode denial, which
says the same. That is not a deadlock, there is nothing for the user to allow, and the
plan does not belong in a chat message as a workaround — go back to planning. The misses
log waits the same way: hold the entries until after `ExitPlanMode`.

## Enforcement

Prose alone does not stop an edit. The plugin ships a `PreToolUse` hook that denies
`Edit`, `Write`, `MultiEdit`, and `NotebookEdit` until a pass marker exists for the
current directory.

Its denial is three lines and routes to this skill — `Skill`, `quiz-me:quiz-me` — rather
than restating the protocol. Both halves of that are deliberate. `permissionDecisionReason`
is one string with two audiences: the user reads it in the terminal, styled as a blocked
tool call, and Claude reads it as an instruction. So it opens with the state of the gate
and how to skip it, in plain language, and spends one line pointing Claude at the skill.
Shell commands, marker paths and protocol detail belong here, not in a red block the user
has to scroll past. A deny message compact enough to sit in a hook can only
carry a sketch of a round, and a session that quizzes from the sketch produces something
that grades like a quiz and looks nothing like one: no briefing, no banner, no difficulty
ladder, no previews, no scorecard, no receipt. Load the skill; the message names the gate,
it is not a substitute for what the gate is holding the line for.

The hook only reads the marker — one write covers every edit until it
expires or the batch ends. A `SessionStart` hook deletes it on `startup`, `resume`, and
`clear`, so every session starts locked. It also matches `compact` and then deliberately
does nothing, because a context compaction is the middle of a batch, not the start of one
— matching the event is what makes that skip a decision the hook actually gets to make
rather than a branch nothing ever reaches.

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

A marker holding `pass` unlocks any session until it expires. A marker holding
`override: <session-id> — <reason>` unlocks only the session whose id it names: the hook
reads the file's first bytes, and matches that id against the payload's `session_id` or
`$CLAUDE_CODE_SESSION_ID`, accepting either because the marker is written from the shell
and read from the payload. Everything else — a different session, an override with no id,
a bare `override:` — falls through to a denial. `ttlMinutes` still applies on top, so an
override is bounded by the session *and* the clock. Markers written before this scoping
existed carry no id and are inert, which re-locks any stale bypass still sitting in
`~/.claude/quiz-me/` rather than honoring it for the rest of its TTL.

Known limits, both deliberate — the marker itself has to be writable, and the gate is a
commitment device, not a sandbox:

- **Shell commands are not covered.** The hook matches file-editing tools, so a `sed -i`
  or a heredoc redirect still goes through.
- **Paths outside the session root are not covered.** `is_outside_root` exempts any
  target that is not the session's `cwd` or under it, so edits to a sibling checkout or
  to `~/.claude` are never gated. The check compares against `root + os.sep`, so a
  sibling whose name merely starts with the root's name (`/repo-old` against `/repo`) is
  correctly treated as outside rather than swept in by the string prefix. `~/.claude/quiz-me.json`
  falls under this: the global config stays writable from a locked session. The project
  config does not — `.claude/quiz-me.json` is inside the root and gated like any other
  file, so a locked session cannot disarm the gate by flipping `enforce` in the repo.

The test suite in `hooks/test_gate.py` pins both, so neither can quietly widen:

```bash
python3 -m unittest discover -s plugins/quiz-me/hooks
```

Run it after any change to `gate.py`. The hook fails open on every error — a broken hook
allows the edit rather than blocking it, which is the right call for a session but means
a bug in it is indistinguishable from a passed quiz. Nothing surfaces it except a test.

## Streak

`~/.claude/quiz-me/<project-path>.streak` holds one integer: consecutive batches where
every question, everywhere in the batch — every pre-implementation round and the
post-implementation check — was answered correctly on the first try. Any re-ask, any
`partial` or `gap`, or an override resets it to `0`. It only ever moves at the single
batch-end write in step 5 (or the unlock write in step 4, for an override) — never
mid-round, so a round in progress never shows a number that is about to be wrong.

It exists to be seen, not just stored: read it alongside the misses log in step 1, and
carry it on the round banner (`streak 5`) whenever it is nonzero. `gate.py` also reads
it and folds it into the hook's deny message, so a denied edit already shows the number
before a single question is asked.

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
some options and not others. A boss question (*Open concepts carry forward*, step 1) is
the one deliberate exception — it always runs at `hard`'s tightness regardless of the
configured level, and says so out loud when it fires.

`hard` mode makes the gate genuinely expensive. Five questions with near-miss distractors
and a restarting rung can cost several rounds before an edit lands. That is the point of
the level, but it is worth choosing deliberately rather than globally.

## When to skip the quiz

Skip only when the change clears one of the cases below. Touching a single file is
never by itself one of those cases — it is the fewest files a quizzable change could
touch, not a reason to skip one.

Always skip:

- Pure lookups, reads, and questions
- Formatting, renames, one-line typos
- Mechanical edits with no design content
- The user already stated the root cause *and* the fix in their own prompt

Everything else gets quizzed — including a change confined to one file, if it required
a real decision (a boundary condition, an ordering choice, a tradeoff) that a reader
would have to reconstruct to explain the change back. Needing more than one file to
understand a change is a strong signal it needs a quiz; it is not reversible into "one
file means skip."

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
