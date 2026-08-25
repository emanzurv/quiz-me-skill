---
description: Show the gate's current state — armed or not, difficulty, marker, streak, open concepts.
allowed-tools: Bash(cat:*), Bash(ls:*), Bash(stat:*), Bash(date:*), Bash(tail:*), Bash(echo:*), Bash(git rev-parse:*), Bash(for:*), Bash(test:*)
---

Report the gate's state. Read-only: this command never writes a marker, never appends to
the misses log, and never quizzes. Everything it needs comes from one shell call.

1. Collect the state in a single command — the same `~/.claude/quiz-me/` prefix every
   other quiz-me write uses, so one approval covers it:

   ```bash
   r=$(git rev-parse --show-toplevel 2>/dev/null || pwd); f=~/.claude/quiz-me/"${r//\//_}"
   echo "root: $r"
   echo "--- config global"; cat ~/.claude/quiz-me.json 2>/dev/null
   echo "--- config project"; cat "$r"/.claude/quiz-me.json 2>/dev/null
   echo "--- env: enforce=${QUIZ_ME_ENFORCE:-unset} difficulty=${QUIZ_ME_DIFFICULTY:-unset}"
   echo "--- markers"
   for m in "$f".pass "$r"/.claude/quiz-me.pass; do
     [ -f "$m" ] || continue
     s=$(stat -f %m "$m" 2>/dev/null || stat -c %Y "$m")
     echo "$m age=$(( ( $(date +%s) - s ) / 60 ))m content=$(cat "$m")"
   done
   echo "--- streak"; cat "$f".streak 2>/dev/null
   echo "--- misses"; cat "$f".misses.md 2>/dev/null
   echo "--- reviewed"; tail -20 "$f".reviewed.md 2>/dev/null
   ```

2. Resolve the effective config yourself: project keys merge over global keys, and
   `QUIZ_ME_ENFORCE` / `QUIZ_ME_DIFFICULTY` override both. Unset or unrecognized
   `difficulty` is `normal`; unset `ttlMinutes` is `240`; `0` means no expiry.
3. Decide the gate state from the markers and the TTL — **open** if a marker exists and
   its age is within `ttlMinutes`, **closed** otherwise. A marker whose content starts
   with `override:` is open but unearned; say so and quote the reason.
4. Compute open concepts from the misses log by the rule in the skill: group lines by
   their exact `<concept>` text, and a concept is open if its most recent line is a miss
   rather than `RESOLVED`. Two or more open misses in a row makes it a 🐉 boss concept.
5. Render one block. Omit rows that have nothing to say — no streak line at `0`, no
   concepts section when everything is resolved:

   ```
   ━━━ 🧠 QUIZ ME · STATUS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

     gate        🔒 closed — no marker
     enforce     armed (~/.claude/quiz-me.json)
     difficulty  normal — 3 questions, 4 options, plausible distractors
     ttl         240m
     streak      🔥 3

     open concepts
       🐉 retry backoff   missed twice, unresolved — restarts the round
       ·  cache key       missed 2026-01-01

     last reviewed  db.js (retained), importUsers.js (fuzzy)
   ```

   Name the source file for `enforce` and `difficulty` — global config, project config, or
   environment — so a surprising level is traceable to the file that set it.
6. Close with the one thing the state implies, in a sentence: what the next edit will do.
   "Next edit will be denied — 3 questions at normal, one of them on the open boss
   concept." Or "Marker expires in 40m; after that the next edit re-quizzes."

If enforcement is off, say so plainly and note that the skill still runs when invoked —
`enforce` governs the hook, not the quiz.
