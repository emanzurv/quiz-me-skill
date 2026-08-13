# Changelog

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
