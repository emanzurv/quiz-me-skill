# Changelog

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
