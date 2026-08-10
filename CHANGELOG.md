# Changelog

## 0.1.0

Initial release.

- `quiz-me` skill: gates non-trivial code changes behind a multiple-choice quiz on root
  cause, mechanism, and fix. Implementation unlocks only on a 100% pass.
- Post-implementation comprehension check: every edit listed as `file:line`, per-item
  verdict (understood / partial / gap), closing tally.
- Skip rules for lookups, formatting, renames, one-line typos, and cases where the user
  already stated root cause and fix.
