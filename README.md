<div align="center">

# 🧠 quiz-me

### The bouncer for your diff.

![version](https://img.shields.io/badge/version-0.3.0-black)
![claude code](https://img.shields.io/badge/Claude%20Code-plugin-orange)
![license](https://img.shields.io/badge/license-MIT-blue)
![vibe coding](https://img.shields.io/badge/vibe%20coding-denied-red)

</div>

```
you     ›  just fix the import bug
claude  ›  sure. quick question first: why does it report
           500 imported when only 30 rows actually land?
you     ›  ...because it's broken?
claude  ›  (waiting)
```

That's it. That's the plugin.

Claude keeps the boring half — reading, searching, typing. You keep the half that can't be
outsourced: **knowing why.** Nothing gets written until you convince it you do.

---

## 🎯 Pop quiz. And it's for you, not Claude.

Real bug. The support ticket says: *"the import claims 500 users imported, 0 failed — but
only about 30 are actually in the database."*

Claude goes digging and surfaces this beauty:

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

And then, instead of a diff, it hands you this:

```
━━━ 🧠 QUIZ ME · round 1 · root cause ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Why does it report 500 imported when only ~30 rows land?

  ┌─ Q1/3 cause ────────────────────┬─ importUsers.js:7 ──────────────┐
  │                                 │                                 │
  │  ○ catch swallows the error     │      } catch (err) {            │
  │  ● forEach drops the promise    │        failed.push(row);        │
  │  ○ pool dies on process exit    │      }                          │
  │  ○ push races between callbacks │    });                          │
  │                                 │                                 │
  └─────────────────────────────────┴─────────────────────────────────┘
     ↑↓ to move — the panel shows the code that answer blames
```

**Answer before you scroll.** No peeking. You're inside the demo — this is exactly how it
feels, minus the mild panic.

<br><br>

### 👉 It's 3.

Picked 1? Excellent taste in wrong answers. Here's how Claude peels you off it:

> If inserts were throwing, `failed` would be **filling up**. But the count came back as
> *exactly* `rows.length` — so `failed` was still empty when the function returned. The
> callbacks hadn't even run yet. `forEach` takes the promise, drops it on the floor, and
> strolls on. `importUsers` returns a number it invented, and 470 pending inserts die alone
> in the dark when the process exits.

Get it wrong and nobody just hands you the answer. You get the same idea again — reworded,
from a new angle — until it sticks. Get all three right and *then* the code lands.

Then the receipt arrives:

```
━━━ 🧠 RECEIPT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ✅  importUsers.js:4   for...of instead of forEach, so each insert is awaited
  ✅  importUsers.js:12  return the failed rows, not just a count, so callers retry
  ⚠️   db.js:22          insertUser takes a client, so the batch shares a transaction

  ▓▓▓▓▓▓▓▓░░░░  2/3 understood — partial on the shared transaction
  🔒 gate re-locked
```

Every edit named. Nothing bundled, nothing quietly filed under "minor," and **no credit for
the one you couldn't explain** — that one just gets explained *to* you until you can.

---

## ⚡ Install

```
/plugin marketplace add schwann2402/quiz-me-skill
/plugin install quiz-me@quiz-me
```

Told to `Run /reload-plugins to activate.`? That's not a suggestion.

**Did it land?** Type `/quiz-me:` — you should see `quiz-me` and `review`. Nothing? Go check
`/plugin`, someone's fibbing.

It's now on your machine for every project, sitting perfectly still, judging nothing, until
you pick a level. 👇

## 🎚️ Pick your level

| | What happens | Cost |
| :-- | :-- | :-- |
| **1 · On request** | Quizzes you when you ask nicely | nothing |
| **2 · One repo** | Quizzes you on every real change in that repo | one line |
| **3 · Everywhere** | Same, in every project you open | one line |
| **🔒 Hard mode** | Claude *physically cannot* edit until you pass | one small file |

**Level 1** — say `/quiz-me:quiz-me`, or just *"quiz me on this first"*. That's the setup.
That was it.

**Level 2** — drop this into that project's `CLAUDE.md`:

```markdown
Before implementing any non-trivial change, use the quiz-me skill.
```

Ideal for the one codebase that keeps ambushing you at 2am. Your other repos carry on,
blissfully ungoverned.

**Level 3** — same line, but in `~/.claude/CLAUDE.md`. No repo escapes. No takebacks.
(Fine: one `rm` of takebacks.)

Fair warning: levels 2 and 3 are *instructions*, and instructions have a habit of
evaporating around hour three of a long session. Which brings us to…

## 🔒 Hard mode

Levels 1–3 are a New Year's resolution. Hard mode is a lock on the fridge.

A hook denies Claude's editing tools outright until you've passed, then re-arms itself at
the start of every session like a very small, very smug security guard. Off by default,
because nobody wants a pop quiz to rename a variable. Arm it for one repo via
`.claude/quiz-me.json`, or for all of them via `~/.claude/quiz-me.json`:

```json
{ "enforce": true, "ttlMinutes": 240 }
```

- A project file beats the global one — `{ "enforce": false }` pardons any repo.
- `ttlMinutes` = how long one pass holds the door open. `0` = forever, you optimist.
- Your repos stay spotless; the pass marker lives over in `~/.claude/quiz-me/`.

## 🧊 The surprise exam

Passing a quiz thirty seconds after Claude explained everything isn't memory. It's a rental.

```
/quiz-me:review 5
```

Grabs your last 5 commits and quizzes you **cold**. No diff. No commit message. Just the
code, staring back.

```
3/5 retained — lost the retry backoff, fuzzy on the cache key
```

Humbling. Extremely the point.

## 😴 It's not a jerk about it

Zero quizzes for lookups, formatting, renames, typos, or anything where you already called
the bug *and* the fix yourself. The rule is mechanical: **if Claude had to read more than one
file, you get quizzed.** Otherwise it shuts up and works.

And when it's 2am and prod is a smoking crater, say **"quiz override."** It ships. No
argument, no justification, no disappointed sigh — just one quiet note that this one went
out unverified.

A gate you can't bypass is a gate you uninstall at 2:04am. 🚪

## 🧯 Kill switch

- **Just this once** → "quiz override"
- **This repo** → delete the line from its `CLAUDE.md`; set `{ "enforce": false }` if hard
  mode is on
- **Salt the earth** → `/plugin uninstall quiz-me@quiz-me`, then delete
  `~/.claude/quiz-me.json` and `~/.claude/quiz-me/`

No hard feelings. Mostly.

## 🩺 Something's off

| Symptom | What's actually going on |
| :-- | :-- |
| It didn't quiz me | Your change hit the skip list. Say *"quiz me on this first"* if you want it anyway. |
| It quizzed me on something dumb | *"quiz override."* Onward. |
| Hard mode isn't blocking anything | Run `python3 --version`. The hook is Python and fails **open** on purpose — no python3, no lock, just vibes. Then check `enforce` is actually `true`. |
| It edited before quizzing me | Say *"hold — revert that."* File goes back, quiz resumes. Hard mode makes this a non-event. |

**Requirements:** Claude Code. Plus `python3` on your PATH for hard mode. That's the entire
list.

## 🤔 Why bother

Autocomplete-driven development is *gloriously* fast — right up until 2am, when something
detonates inside code you have genuinely never read. Congratulations: you're now debugging a
stranger's work.

The stranger is you. Last Tuesday. 👻

| Claude does | You do |
| :--- | :--- |
| The reading | The **understanding** |
| The searching | The **deciding** |
| The typing | The **knowing why** |

Every "✔️ I reviewed this" checkbox is a lie you tell yourself at speed.

**This one can actually fail you.** Which is the only reason it's worth anything.

<div align="center">

⭐ **Star it** if you'd rather understand your codebase than inherit it.

</div>

## 📄 License

MIT — go wild.
