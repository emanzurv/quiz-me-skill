# Changelog

## 0.8.1

- The denial is three lines instead of fourteen. `permissionDecisionReason` is one string
  with two audiences — the terminal renders it to the user as a blocked tool call, and
  Claude reads it as an instruction — so it now opens with the gate's state and how to
  skip it, then spends one line pointing Claude at the skill. The unlock command, the
  override format and the protocol detail are gone from it; the skill carries all three
  at the point they are used. The plan-mode denial got the same treatment.
- `concept_counts` no longer counts escape-hatch log lines. `— override — <reason>` shares
  the log's shape but records a batch that shipped unquizzed, so two of them promoted an
  `override` concept the user had never got wrong to 🐉 boss and put it in every deny
  message. `override` is now reserved bookkeeping.
- README version badge said 0.3.0.
- 5 more hook tests, 58 total, including one that fails if the denial grows past three
  lines or starts carrying shell commands again.

## 0.8.0

- The hook's denial now routes to the skill (`Skill`, `quiz-me:quiz-me`) instead of
  restating a compressed version of the protocol. The old text was self-contained enough
  to satisfy: a denied session quizzed from those few lines and `SKILL.md` never loaded,
  so the round arrived with no briefing, no banner, no difficulty ladder, no option
  previews, no scorecard and no receipt. Nothing was broken in the skill — nothing was
  reading it.
- Overrides are scoped to one session. `override: <session-id> — <reason>` unlocks only
  the session that asked for the bypass; `marker_valid` reads the marker's content and
  matches the id against the payload's `session_id` or `$CLAUDE_CODE_SESSION_ID`. Before
  this, the hook only stat'd the file, so "don't quiz me" written once opened the gate for
  every session in that repo for the full `ttlMinutes` with nothing on screen to say so.
  A plain `pass` marker is unchanged and still covers any session — passing the quiz is
  knowledge, a bypass is not.
- Override markers written before this release carry no session id, match nothing, and
  are inert. Any stale bypass sitting in `~/.claude/quiz-me/` re-locks on upgrade.
- `/quiz-me:status` distinguishes an override that belongs to this session from one that
  belongs to another, and prints the session id it compared against.
- 13 more hook tests, 53 total.

## 0.7.1

- `homepage` and `repository` in `plugin.json` pointed at `schwann2402/quiz-me-skill`,
  which now only redirects. Both read `emanzurv/quiz-me-skill`, as does the
  `/plugin marketplace add` line in the README.

## 0.7.0

- `hooks/test_gate.py`: 40 tests over the enforcement hook, run with
  `python3 -m unittest discover -s plugins/quiz-me/hooks`. The gate fails open by design,
  so a bug in it is indistinguishable from a passed quiz — no error, no deny, the edit
  just runs. Nothing else in the plugin can notice that, which is why this exists.
- Fixed a marker-path divergence that could wedge the gate shut. The docs derived the
  state filename from the shell's `$PWD` while `gate.py` derived it from the hook
  payload's `cwd`; the two disagree whenever the shell sits in a subdirectory, and on
  macOS they can also disagree on case. The hook now resolves symlinks and falls back to
  a case-insensitive scan of `~/.claude/quiz-me/`, and every snippet in the skill and in
  `/quiz-me:review` keys off the repo root instead of `$PWD`.
- The hook now walks up from the payload `cwd` to the repo root when building the state
  filename. The previous release fixed the docs half of this divergence; the hook half was
  still keyed on `cwd` alone, so a session started in a subdirectory looked for a marker
  the skill never wrote there — a gate that stayed shut for the full `ttlMinutes` with
  nothing able to open it.
- A non-numeric `ttlMinutes` no longer disables expiry. `"240"` or `"soon"` made the
  comparison in `marker_valid` raise `TypeError`, which the bottom-of-file handler turned
  into an allow — so any existing marker unlocked forever. Numeric strings are now
  honored, anything unparsable falls back to the 240-minute default.
- `quiz-me.json` is off the state-file exemption. It holds `enforce`, so exempting it let
  a locked session legally write `{"enforce": false}` and edit freely. `quiz-me.pass` and
  everything under `~/.claude/quiz-me/` stay exempt; the global config remains writable
  through the documented outside-root limit, the project one does not.
- `MultiEdit` is now in the `PreToolUse` matcher. It was absent, so a `MultiEdit` call was
  never routed to the hook at all — no deny was possible, and `/quiz-me:review` had been
  counting it as an edit tool the whole time.
- The `SessionStart` matcher now includes `compact`, making the existing compact guard
  reachable. It was previously dead code: the matcher never delivered the event it skips.
- `QUIZ_ME_ENFORCE` is matched case-insensitively and accepts `on`. `QUIZ_ME_ENFORCE=TRUE`
  silently failed to arm the gate.
- Dropped a stale `quiz-me-misses.md` basename from the hook's state-file exemption; the
  file has been `<project-path>.misses.md` under `~/.claude/quiz-me/` for two releases.
- New `/quiz-me:status` — read-only: armed or not and which config file did it, level,
  gate open/closed with time remaining, streak, and open concepts with bosses marked.
- The outside-root exemption is now documented as a known limit next to the `sed -i` one,
  and pinned by a test. Edits outside the session root were always ungated; that was never
  written down.
- Marketplace metadata was two releases behind the plugin (`0.4.0` against `0.6.0`), so
  update detection had nothing to detect. Both now read `0.7.0`.
- README documents the misses log, open concepts, boss questions, and streaks — all
  shipped in 0.6.0 with no way to discover them. Also corrected the skip rule: "more than
  one file" is a signal that a change needs a quiz, never a rule that one file means skip.

## 0.6.0

- The misses log gains a `RESOLVED` sentinel. A concept is open if its latest line is a
  miss rather than a resolution; open concepts touching the current change get a
  guaranteed, reworded question this round with tightened distractors, and a concept
  missed twice in a row with no resolution becomes a **boss question** — hard-tightness
  distractors, 2-line previews, and a wrong answer restarts the whole round, regardless
  of the configured `difficulty`.
- New streak counter at `~/.claude/quiz-me/<project-path>.streak`: consecutive batches
  where every question, everywhere in the batch, was answered correctly on the first
  try. Any re-ask, `partial`/`gap`, or override resets it to `0`. It rides on the round
  banner (`🔥 streak 5`) and in the hook's deny message, so it's visible before a
  question is ever asked.
- The gate's deny message now names open-concept and boss counts and the current streak,
  read straight from the misses/streak files — `gate.py` gained `concept_counts` and
  `read_streak` for this, both scoped under `GLOBAL_DIR` so they inherit the existing
  hook exemption without a new special case.
- Every state write this skill makes collapses onto one shell-command family per step
  (one call for the round-end misses/RESOLVED/streak/re-lock, one for the unlock/misses
  flush, one for override) instead of one call per line item — approving the shared
  `~/.claude/quiz-me/` prefix once now covers a whole batch instead of prompting on every
  slightly different command.
- Step 2 now requires a short plain-language brief — what's being changed, which files
  and functions are in play — before the first question. A quiz with no preceding
  context asked the user to reason about code they were never told was involved.
- Per-question category emoji (one considered per ladder item) were tried and dropped:
  repeating a new glyph on every single question read as clutter rather than signal.
  Iconography stays reserved for states that don't fire every round — 🐉 boss, 🔥 streak.
- The `PreToolUse` hook now allows any `Edit`/`Write`/`NotebookEdit` target outside the
  project root. It used to gate on the session's `cwd` alone, so an armed project denied
  edits to files that were never part of it — a scratch file, an artifact draft anywhere
  else on disk.
- "When to skip the quiz" no longer reads as "single file means skip." The always-skip
  list was always the actual test; the multi-file line only ever said multi-file forces
  a quiz, not that one file excuses one.

## 0.5.0

- The pass marker is now scoped to a batch of work instead of a single edit. Step 4 says
  to write it once and states that the hook reads the marker rather than consuming it, so
  re-running the unlock between edits was always redundant. The gate's deny message says
  the same, since that message is what a model reads after a denial and it previously
  implied one unlock per edit.
- The post-implementation check and the re-lock moved to the end of the batch. Step 5 used
  to read as "after the change", and re-locking was described as preparing for "the next
  change" — together that turned one unit of work spanning several files into several
  quizzes, which is what made the gate feel like it fired per change.
- Plan mode no longer deadlocks the gate. A quiz passed inside plan mode had nowhere to
  land: plan mode denies every write, the pass marker included, so the unlock command was
  denied and the model reported itself stuck with the plan stranded in a chat message. The
  gate now recognizes plan mode and denies with a different reason — the marker is not due
  until the first real edit, which plan mode already blocks — and the skill says to hold
  both the unlock and the misses log until after `ExitPlanMode`.
- `SessionStart` no longer clears the marker on `compact`. The hook had no matcher, so it
  ran on every source, and a context compaction mid-task re-locked the gate in the middle
  of a batch the user had already passed. Now scoped to `startup|resume|clear`, with a
  matching `source == "compact"` guard in `gate.py` for hosts that ignore the matcher.

## 0.4.0

- New `difficulty` setting — `easy`, `normal` (default), or `hard`, in
  `.claude/quiz-me.json`, `~/.claude/quiz-me.json`, or `QUIZ_ME_DIFFICULTY`. One dial
  moves four levers together: questions per round (2/3/5), options per question (3/4/4),
  distractor tightness (one clearly wrong → all plausible → all near-misses), preview
  width (5-6 lines → 3-4 → 2), and what a wrong answer costs (re-ask once → re-ask until
  correct → restart the rung). The slot rule and all-or-none do not scale with it.
- Config now merges instead of shadowing. `load_config` returned the first file that
  parsed, so a project `.claude/quiz-me.json` holding only `{"enforce": true}` hid every
  global key. Global loads first, project keys land on top.
- The gate's deny message names the active level and its shape, so the model reading it
  knows the round size before writing question one. It no longer hardcodes "3 questions".

- The correct answer no longer lands in slot 1 every time. "Vary which position holds
  the correct answer" was advisory, and variation is a property of a batch — each
  question is authored alone, and the answer is always the option written first because
  it is the one already known. Placement is now a rule: smallest line number the correct
  option cites, `mod` the option count, `+ 1`. Deterministic to compute, unguessable to
  answer. Applied to the pre-change rounds, the post-change check, `/quiz-me:review`,
  and the gate's deny message.
- `/quiz-me:review` now quizzes only on your own session work. It reads the session
  transcripts under `~/.claude/projects/` to find which files this repo's sessions
  edited, then keeps commits that are yours *and* touch those files. A teammate's
  commits on the branch no longer show up; neither does hand-typed work that never
  passed through a session.
- Empty file set is a hard stop. An empty pathspec leaves git a bare `--`, which it
  reads as "no path restriction" and answers with your entire history — silently
  undoing the scoping. No transcripts (a fresh clone) looks the same as no session
  work, and neither is a reason to widen the scope.
- Paths reach git through `xargs -0`. zsh does not word-split unquoted expansions, so
  interpolating the list directly hands git one newline-stuffed pathspec that matches
  nothing.
- New review log at `~/.claude/quiz-me/<project-path>.reviewed.md` records every file
  quizzed, pass or fail. Files never quizzed get picked first, then least recently
  quizzed. The misses log is unchanged and still tracks only what was not retained.

## 0.3.2

- The post-implementation comprehension check is multiple choice, same as the pre-change
  rounds. No prose questions, no free-text recall — every answer is a click.
- Those questions carry no `preview`: the panel would show the lines that just landed,
  which is the answer. Options ground themselves in `file:line` in the description, and
  distractors come from the other edits in the batch and from what the code did before.
- Preview rules are now scoped to the pre-change rounds, so a preview-less post-change
  round satisfies all-or-none instead of reading as a violation of it.

## 0.3.1

- The misses log no longer lands in the user's repo. It moves from
  `.claude/quiz-me-misses.md` to `~/.claude/quiz-me/<project-path>.misses.md`, matching
  where the pass marker already lived. Nothing quiz-me writes touches the working tree.
- Existing `.claude/quiz-me-misses.md` files are left alone; delete them by hand.

## 0.3.0

- Quiz questions now fill every field the picker offers: `header` as a progress chip
  (`Q2/3 mech`), `description` as one grounded line per option, and `preview` showing the
  real code each option blames — side by side with the option list.
- Preview rules to stop the panel leaking the answer: all-or-none, equal line counts, real
  lines only.
- Round banner, 12-cell progress bar, and a scorecard after every round; receipt after
  implementation carries the same bar plus the gate state.
- Hook denial now reads as part of the product: `🔒 quiz-me · gate closed — 3 questions to
  unlock`.
- `/quiz-me:review` uses the same chrome and previews.

## 0.2.0

- Enforcement hook: `PreToolUse` denies `Edit`/`Write`/`NotebookEdit` until a pass marker
  exists for the current directory; `SessionStart` clears it so each session starts locked.
  Off by default, armed via `.claude/quiz-me.json` (one project), `~/.claude/quiz-me.json`
  (all projects), or `QUIZ_ME_ENFORCE=1`. Project config wins. Marker defaults to
  `~/.claude/quiz-me/`, so nothing lands in the working tree. Fails open on error.
- Answer key is fallible: a user answer backed by a mechanism sends Claude back to the
  code before grading.
- Feature and refactor question ladders, so work without a root cause still gets gated.
- Post-implementation check caps at 5 questions on substantive edits; mechanical edits
  are listed but named as not-quizzed.
- Explicit override path (`quiz override`) that ships unverified, says so once, and logs
  it — instead of the user disabling the skill.
- Mechanical skip test: if understanding the change required reading more than one file,
  quiz.
- `/quiz-me:review [n]` re-quizzes the last `n` commits cold, graded retained / fuzzy /
  lost.
- Miss log at `.claude/quiz-me-misses.md` biases later quizzes toward weak spots.
- Plan mode: quiz runs after plan approval and before the first edit. Approving a plan
  never substitutes for the quiz.

## 0.1.0

Initial release.

- `quiz-me` skill: gates non-trivial code changes behind a multiple-choice quiz on root
  cause, mechanism, and fix. Implementation unlocks only on a 100% pass.
- Post-implementation comprehension check: every edit listed as `file:line`, per-item
  verdict (understood / partial / gap), closing tally.
- Skip rules for lookups, formatting, renames, one-line typos, and cases where the user
  already stated root cause and fix.
