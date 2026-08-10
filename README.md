# quiz-me

**Claude won't write the code until you can explain the bug.**

Claude reads your code and finds the root cause. Then, before editing anything, it quizzes
you on it — multiple choice, based on your actual code. Answer everything right and the fix
lands. Get one wrong and it explains why, then asks again.

## Install

```
/plugin marketplace add schwann2402/quiz-me-skill
/plugin install quiz-me@quiz-me
```

If the install summary says `Run /reload-plugins to activate.` — run that.

## Use it

```
/quiz-me:quiz-me
```

Or just say *"quiz me on this first"* and it starts on its own.

To make it automatic for a project, add one line to your `CLAUDE.md`:

```markdown
Before implementing any non-trivial change, use the quiz-me skill.
```

## Example

You say: *"my timer counts to 1 and then stops"*

Claude reads the code, then asks:

```
Why does the counter freeze at 1?

  1. setState is async, so the rapid updates get batched away
  2. The interval callback closed over count from the first render
     and keeps computing 0 + 1 forever
  3. The effect re-runs every render, restarting the interval
  4. StrictMode double-mounts and cancels the second update
```

Pick wrong and it tells you why that answer fails, then asks again from a different angle.
Pick right on all three and it writes the fix.

Afterwards it lists every edit and checks you can explain each one:

```
useTimer.ts:14 — setCount(c => c + 1) so the tick never reads a stale count
useTimer.ts:19 — clearInterval cleanup so unmount doesn't leak the timer
Timer.tsx:8   — memoized onTick so the parent re-render stops resetting the hook

2/3 understood — gap on the memoized onTick
```

## When it stays quiet

No quiz for lookups, formatting, renames, typos, or when you already said what the bug and
the fix are. Rule of thumb: if Claude had to read more than one file, you get quizzed.

Say **"quiz override"** any time and it ships without the quiz — no arguing. It just notes
that the change went out unverified.

## Options

| What | How |
| :--- | :--- |
| Re-quiz on code that already shipped | `/quiz-me:review 5` — quizzes your last 5 commits, cold |
| Hard-block editing until you pass | add `.claude/quiz-me.json` with `{ "enforce": true }` |
| See what you keep getting wrong | missed answers are logged to `.claude/quiz-me-misses.md` |

Works for features and refactors too, not just bugs — the questions change to match
(what constrains the design, what must stay identical, what breaks).

If you use plan mode, approving a plan doesn't skip the quiz. The quiz runs after you
approve, before the first edit.

## Why

Code you didn't understand when it landed is code you can't debug at 2am. This keeps Claude
doing the reading and typing, and keeps you doing the understanding.

Unlike a checkbox that says "I reviewed this," this one can actually fail.

## License

MIT.
