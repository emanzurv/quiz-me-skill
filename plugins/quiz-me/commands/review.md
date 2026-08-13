---
description: Cold re-quiz on code that already shipped — your own session commits, not the change in front of you.
argument-hint: "[number of your session commits, default 5]"
allowed-tools: Bash(git log:*), Bash(git show:*), Bash(git diff:*), Bash(git config:*), Bash(git rev-parse:*), Bash(jq:*), Bash(printf:*), Bash(xargs:*), Bash(mkdir:*), Bash(echo:*), Read, Grep, Glob, AskUserQuestion
---

Re-quiz the user on code that already landed. Passing a quiz right after implementing
proves recall at peak context; this proves retention.

Scope is the user's own session work, never the whole branch. Code someone else pushed
to the branch is not something the user can be expected to have retained.

1. Collect every file this repo's sessions have edited, across *all* sessions. Session
   transcripts live under `~/.claude/projects/`, one directory per project, named after
   the repo path with every non-alphanumeric character replaced by a dash:

   ```bash
   ROOT=$(git rev-parse --show-toplevel)
   PROJ=~/.claude/projects/$(printf '%s' "$ROOT" | sed 's/[^a-zA-Z0-9]/-/g')
   FILES=$(jq -r 'select(.message.content) | .message.content[]?
       | select(.type == "tool_use" and (.name == "Edit" or .name == "Write"
                or .name == "MultiEdit" or .name == "NotebookEdit"))
       | .input.file_path // empty' "$PROJ"/*.jsonl 2>/dev/null \
     | grep "^$ROOT/" | sed "s|^$ROOT/||" | sort -u)
   ```

   Subagent edits sit in the same transcripts under `isSidechain: true`; they count.
2. Stop here if `FILES` is empty. Do not fall through to the next step — an empty
   variable leaves a bare trailing `--`, which git reads as *no path restriction* and
   answers with the user's entire history, silently undoing the session scoping:

   ```bash
   [ -z "$FILES" ] && echo "no session-edited files in this repo — nothing to review"
   ```

   Empty means either no session work or no local transcripts; a fresh clone is
   indistinguishable from an idle repo here, and neither justifies quizzing on code the
   user did not write.
3. List the last `${1:-5}` commits that are the user's *and* touch those files. Walk
   back as far as history needs — `5` means five surviving commits, not five candidates.
   Feed the paths through `xargs -0`; do not interpolate `$FILES` into the command, as
   zsh does not word-split unquoted expansions and would hand git one newline-stuffed
   pathspec that matches nothing:

   ```bash
   printf '%s\n' "$FILES" | tr '\n' '\0' \
     | xargs -0 git log --author="$(git config user.email)" --oneline -n ${1:-5} --
   ```

   Both filters carry weight. Authorship alone still admits branch work that never went
   through a session; paths alone still admit other people's commits to files the user
   happens to have edited. Show the list.
4. Read `difficulty` from `.claude/quiz-me.json` merged over `~/.claude/quiz-me.json`
   (`QUIZ_ME_DIFFICULTY` overrides both; unset reads as `normal`). It sets how many hunks
   to pick, how many options each question carries, how tight the distractors are, and
   how wide the previews run — the table in the skill's *Difficulty* section governs here
   too. Then pick that many of the most substantive hunks — control flow, API shape,
   ordering, error handling. Skip formatting, renames, and generated files. Prefer hunks
   in files not quizzed before; the review log sits beside the misses log:

   ```bash
   cat ~/.claude/quiz-me/"${PWD//\//_}".reviewed.md 2>/dev/null
   ```

   Never-reviewed files first, then least recently reviewed. Repeating a file is fine
   once the unreviewed ones run out — say which bucket each question came from.
5. Read the *current* state of the code around each hunk, not just the diff. The
   question is about how the code works today.
6. Quiz with `AskUserQuestion`, one question per hunk, cold — do not restate what the
   commit message said, and do not show the diff before asking. Open with a rule line:

   ```
   ━━━ 🧠 COLD REVIEW · 5 session commits · 4 questions ━━━━
   ```

   Fill every field: `header` as `Q2/4 cache`-style progress chips, `description` as one
   grounded line per option, and `preview` showing the code each option points at — same
   line count for every option, real lines only, all-or-none. Place the correct answer by
   the slot rule, not first: smallest line number it cites, `mod` the option count, `+ 1`.
7. Grade each answer out loud: **retained** / **fuzzy** / **lost**. For anything not
   retained, explain the mechanism and append a line to the project's misses log under
   `~/.claude/quiz-me/` — never inside the repo:

   ```bash
   mkdir -p ~/.claude/quiz-me && echo "YYYY-MM-DD — <concept> — <what was missed>" \
     >> ~/.claude/quiz-me/"${PWD//\//_}".misses.md
   ```
8. Record every file quizzed, pass or fail, so the next run can rotate past it:

   ```bash
   echo "YYYY-MM-DD — <file> — <retained|fuzzy|lost>" \
     >> ~/.claude/quiz-me/"${PWD//\//_}".reviewed.md
   ```
9. Close with the scorecard:

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
