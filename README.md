# quiz-me

**Claude won't write the code until you can explain the bug.**

Claude reads your code and finds the root cause. Then, before editing anything, it quizzes
you on it — multiple choice, based on your actual code. Answer everything right and the fix
lands. Get one wrong and it explains why, then asks again.

## What it looks like

You say: *"my import says 500 users imported, 0 failed — but only about 30 are in the
database"*

Claude finds this:

```js
async function importUsers(rows) {
  const failed = [];

  rows.forEach(async (row) => {
    try {
      await db.insertUser(row);
    } catch (err) {
      failed.push(row);
    }
  });

  return { imported: rows.length - failed.length, failed };
}
```

Instead of a diff, you get this:

```
Why does it report 500 imported when only ~30 rows land?

  1. insertUser is throwing and the catch swallows the error
  2. The connection pool is exhausted, so later inserts queue up
     and die when the process exits
  3. forEach ignores the promise the async callback returns, so the
     function returns before any insert has finished
  4. failed.push races between concurrent callbacks and loses entries
```

The answer is **3**. Option 1 is the tempting one — but if inserts were throwing, `failed`
would be filling up. The count came back as *exactly* `rows.length`, which means `failed`
was still empty when the function returned. The callbacks hadn't run yet. `forEach` doesn't
wait for them, so `importUsers` resolves immediately and the pending inserts die with the
process.

Get it wrong and Claude explains that, then asks again from a different angle until it
clicks. Get all three questions right and it writes the fix.

Afterwards it lists every edit and checks you can explain each one:

```
importUsers.js:4  — for...of instead of forEach so each insert is actually awaited
importUsers.js:12 — return the failed rows, not just a count, so callers can retry
db.js:22          — insertUser now takes a client so the batch shares one transaction

2/3 understood — gap on the shared transaction
```

## Install

```
/plugin marketplace add schwann2402/quiz-me-skill
/plugin install quiz-me@quiz-me
```

If the install summary says `Run /reload-plugins to activate.` — run that.

**Check it worked:** type `/quiz-me:` and you should see `quiz-me` and `review` in the
command list. If you don't, run `/plugin` and confirm quiz-me is listed as installed.

Installing puts it on your machine for every project, but it stays quiet until you ask for
it. Next section is how you decide when it kicks in.

## Choose how it applies

Three levels. Start at 1 — you can move up any time.

### 1. Only when you ask (default)

```
/quiz-me:quiz-me
```

Or just say *"quiz me on this first"*. Nothing to set up.

### 2. Automatic in one repo

Add one line to that project's `CLAUDE.md`:

```markdown
Before implementing any non-trivial change, use the quiz-me skill.
```

Every real change in that repo now gets quizzed. Other repos are untouched.

### 3. Automatic everywhere

Same line, but in `~/.claude/CLAUDE.md` instead. Every project, every session.

Levels 2 and 3 are instructions to Claude, and Claude can drift. For an actual lock, see
below.

## Hard mode: make it a lock

A line in `CLAUDE.md` is a promise. This is a hook that denies Claude's file-editing tools
outright until you've passed. It re-locks at the start of every session.

Off by default. Turn it on for one repo with `.claude/quiz-me.json`, or for every repo with
`~/.claude/quiz-me.json`:

```json
{ "enforce": true, "ttlMinutes": 240 }
```

- A project file beats the global one, so you can set `"enforce": false` in a repo where you
  don't want it.
- `ttlMinutes` is how long one pass keeps the lock open — after that you get quizzed again.
  Use `0` for no expiry.
- Nothing is written into your repos. The pass marker lives in `~/.claude/quiz-me/`.

## Cold review

Passing a quiz right after Claude explained everything is easy. A week later is the real
test.

```
/quiz-me:review 5
```

Pulls your last 5 commits and quizzes you on them cold — no diff, no commit message, just
the code as it stands now. Grades each one **retained** / **fuzzy** / **lost**.

## When it stays quiet

No quiz for lookups, formatting, renames, typos, or when you already said what the bug and
the fix are. Rule of thumb: if Claude had to read more than one file, you get quizzed.

Stuck and don't want a quiz right now? Say **"quiz override"** and it ships — no arguing, no
reason required. It just tells you once that the change went out unverified.

## Turning it off

- **For one change:** say "quiz override".
- **For one repo:** delete the line from that repo's `CLAUDE.md`, and set
  `{ "enforce": false }` in `.claude/quiz-me.json` if you turned on hard mode.
- **Everywhere:** `/plugin uninstall quiz-me@quiz-me`, then delete `~/.claude/quiz-me.json`
  and `~/.claude/quiz-me/`.

## Troubleshooting

**It didn't quiz me.** The change was probably in the skip list above. Say "quiz me on this
first" to force it.

**It quizzed me on something trivial.** Say "quiz override" and it ships.

**Hard mode isn't blocking anything.** Confirm `python3 --version` works — the hook is a
Python script and it fails *open* on purpose, so a missing `python3` means no lock. Then
check that `enforce` is `true` in `.claude/quiz-me.json` or `~/.claude/quiz-me.json`.

**Claude edited before quizzing me.** Say "hold — revert that" and it puts the file back and
returns to the quiz. Hard mode exists to prevent this.

## Requirements

Claude Code, plus `python3` on your PATH if you use hard mode. Nothing else.

## Why

Code you didn't understand when it landed is code you can't debug at 2am. This keeps Claude
doing the reading and typing, and keeps you doing the understanding.

Unlike a checkbox that says "I reviewed this," this one can actually fail.

## License

MIT.
