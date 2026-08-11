---
description: Cold re-quiz on code that already shipped — recent commits, not the change in front of you.
argument-hint: "[number of commits, default 5]"
allowed-tools: Bash(git log:*), Bash(git show:*), Bash(git diff:*), Read, Grep, Glob, AskUserQuestion
---

Re-quiz the user on code that already landed. Passing a quiz right after implementing
proves recall at peak context; this proves retention.

1. `git log --oneline -n ${1:-5}` to list the commits in scope. Show the list.
2. Pick the 3-5 most substantive hunks across those commits — control flow, API shape,
   ordering, error handling. Skip formatting, renames, and generated files.
3. Read the *current* state of the code around each hunk, not just the diff. The
   question is about how the code works today.
4. Quiz with `AskUserQuestion`, one question per hunk, cold — do not restate what the
   commit message said, and do not show the diff before asking. Open with a rule line:

   ```
   ━━━ 🧠 COLD REVIEW · 5 commits · 4 questions ━━━━━━━━━━━━
   ```

   Fill every field: `header` as `Q2/4 cache`-style progress chips, `description` as one
   grounded line per option, and `preview` showing the code each option points at — same
   line count for every option, real lines only, all-or-none.
5. Grade each answer out loud: **retained** / **fuzzy** / **lost**. For anything not
   retained, explain the mechanism and append a line to the project's misses log under
   `~/.claude/quiz-me/` — never inside the repo:

   ```bash
   mkdir -p ~/.claude/quiz-me && echo "YYYY-MM-DD — <concept> — <what was missed>" \
     >> ~/.claude/quiz-me/"${PWD//\//_}".misses.md
   ```
6. Close with the scorecard:

   ```
   ━━━ 🧠 COLD REVIEW ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

     ▓▓▓▓▓▓▓░░░░░  3/5 retained

     ✅ retry queue    dead letters after 3 attempts
     ✅ auth guard     refresh token rotates on every use
     ⚠️  cache key      knew it was scoped, fuzzy on by what
     ❌ retry backoff  thought it was linear; it is exponential
     ✅ pagination     cursor, not offset, so deletes cannot skip rows
   ```

Never credit retention the user did not demonstrate. This command grades only; it does
not edit code.
