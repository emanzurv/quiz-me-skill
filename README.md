# quiz-me

**Your AI won't touch the code until you can explain the bug.**

Claude reads your codebase, finds the actual root cause — and then makes *you* prove you
understand it before a single line changes. Multiple choice. Graded. It can fail you.

Think of it as a bouncer for your diff.

---

## Try it yourself

Here's a real one. A user reports: *"the import says 500 users imported, 0 failed — but only
about 30 are actually in the database."*

Claude goes looking and finds this:

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

Instead of handing you a diff, it hands you this:

```
Why does it report 500 imported when only ~30 rows land?

  1. insertUser is throwing and the catch swallows the error
  2. The connection pool is exhausted, so later inserts queue up
     and die when the process exits
  3. forEach ignores the promise the async callback returns, so the
     function returns before any insert has finished
  4. failed.push races between concurrent callbacks and loses entries
```

Pick one before you scroll. Seriously — this is the whole product.

<br>

**It's 3.**

If you went with 1, that's the good trap, and here's how Claude talks you out of it: if
inserts were throwing, `failed` would be filling up. But the count came back as *exactly*
`rows.length` — so `failed` was still empty when the function returned. The callbacks hadn't
even run. `forEach` doesn't wait for the promise, `importUsers` resolves immediately, and
the pending inserts die with the process.

Miss it and Claude explains that, then asks again from a new angle until it lands. Get all
three questions right and *now* it writes the fix.

Then it hands you the receipt:

```
importUsers.js:4  — for...of instead of forEach so each insert is actually awaited
importUsers.js:12 — return the failed rows, not just a count, so callers can retry
db.js:22          — insertUser now takes a client so the batch shares one transaction

2/3 understood — gap on the shared transaction
```

Every edit named. Nothing waved off as "minor." And no, you don't get credit for the one you
couldn't explain.

---

## Install

```
/plugin marketplace add schwann2402/quiz-me-skill
/plugin install quiz-me@quiz-me
```

If the install summary says `Run /reload-plugins to activate.` — run that.

**Did it work?** Type `/quiz-me:` and you should see `quiz-me` and `review`. If not, check
`/plugin`.

It's now on your machine for every project — and it stays completely quiet until you pick a
level below.

## Pick your level

### Level 1 — When you ask for it

```
/quiz-me:quiz-me
```

Or just say *"quiz me on this first"*. Nothing to configure. Good place to start.

### Level 2 — Always, in one repo

One line in that project's `CLAUDE.md`:

```markdown
Before implementing any non-trivial change, use the quiz-me skill.
```

That repo is now gated. Every other repo carries on as normal. Ideal for the codebase that
keeps biting you at 2am.

### Level 3 — Always, everywhere

Same line, but in `~/.claude/CLAUDE.md`. Every project, every session, no exceptions.

*Caveat:* levels 2 and 3 are instructions, and instructions can be forgotten mid-session.
If you want a rule that can't be talked out of, keep reading.

## Hard mode

Levels 1–3 are a promise. This is a lock. 🔒

A hook denies Claude's file-editing tools outright until you've passed — and re-locks itself
at the start of every session. Off by default (nobody wants a pop quiz to rename a
variable). Switch it on for one repo with `.claude/quiz-me.json`, or for all of them with
`~/.claude/quiz-me.json`:

```json
{ "enforce": true, "ttlMinutes": 240 }
```

- A project file beats the global one — set `"enforce": false` in any repo you want exempt.
- `ttlMinutes` is how long one pass keeps the door open. `0` means forever.
- Your repos stay clean. The pass marker lives in `~/.claude/quiz-me/`.

## The surprise exam

Passing a quiz thirty seconds after Claude explained everything? Easy. Next week is the real
test.

```
/quiz-me:review 5
```

Grabs your last 5 commits and quizzes you cold — no diff, no commit message, just the code
as it stands today.

```
3/5 retained — lost the retry backoff, fuzzy on the cache key
```

Humbling. That's the point.

## It knows when to shut up

No quiz for lookups, formatting, renames, typos, or anything where you already called the
bug and the fix yourself. Rule of thumb: **if Claude had to read more than one file, you get
quizzed.**

And when it's 2am and prod is down, say **"quiz override"**. It ships, no argument, no
reason required. It just notes once that the change went out unverified. A gate you can't
bypass is a gate you'd uninstall.

## Kill switch

- **This one change:** "quiz override"
- **This repo:** delete the line from its `CLAUDE.md`; set `{ "enforce": false }` if you
  turned on hard mode
- **All of it:** `/plugin uninstall quiz-me@quiz-me`, then remove `~/.claude/quiz-me.json`
  and `~/.claude/quiz-me/`

## When something's off

**It didn't quiz me.** Probably landed in the skip list above. Say "quiz me on this first"
to force it.

**It quizzed me on something trivial.** "quiz override" and move on.

**Hard mode isn't blocking anything.** Run `python3 --version` — the hook is a Python script
and it fails *open* by design, so no python3 means no lock. Then confirm `enforce` is `true`
in `.claude/quiz-me.json` or `~/.claude/quiz-me.json`.

**It edited before quizzing me.** Say "hold — revert that" and it puts the file back and
returns to the quiz. Hard mode exists so this can't happen.

**Requirements:** Claude Code, plus `python3` on your PATH for hard mode. That's it.

## Why bother

Autocomplete-driven development is gloriously fast right up until something explodes in code
you've never actually read. Then you're debugging a stranger's work — and the stranger was
you, last Tuesday.

This splits the job properly:

| Claude does | You do |
| :--- | :--- |
| The reading | The **understanding** |
| The searching | The **deciding** |
| The typing | The **knowing why** |

Every other "I reviewed this" checkbox is a lie you tell yourself. This one can actually
fail.

## License

MIT.
