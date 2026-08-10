# Changelog

## 0.2.0

- Enforcement hook: `PreToolUse` denies `Edit`/`Write`/`NotebookEdit` until
  `.claude/quiz-me.pass` exists; `SessionStart` clears the marker so each session starts
  locked. Off by default, armed per project via `.claude/quiz-me.json` or
  `QUIZ_ME_ENFORCE=1`. Fails open on error.
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
