# 🧠 quiz-me

### Your AI won't write the code until you can explain the bug. 🚪🔒

Claude reads your codebase, hunts down the real root cause — and then **refuses to touch a
single line** until *you* prove you understand it. Multiple choice. Grounded in the actual
code it just read. Get one wrong? It explains why, then asks again. 🔁

No more merging diffs you'd fail to defend in code review. 🛡️

```
/plugin marketplace add schwann2402/quiz-me-skill
/plugin install quiz-me@quiz-me
```

> 💡 If the install summary says `Run /reload-plugins to activate.` — run that.

---

## 🎬 What it actually feels like

**You:** *"my timer component counts to 1 and then just… stops"*

Claude goes and reads the code. Then, instead of a diff, you get… **this**: 👇

```
┌─ 🧠 Question 1 of 3 ───────────────────────────────────────────┐
│ Why does the counter freeze at 1?                              │
│                                                                │
│   1. setState is async, so the rapid updates get batched away  │
│   2. The interval callback closed over count from the first    │
│      render and keeps computing 0 + 1 forever                  │
│   3. The effect re-runs every render, restarting the interval  │
│   4. StrictMode double-mounts and cancels the second update    │
└────────────────────────────────────────────────────────────────┘
```

Tempted by #1? 🪤 Gotcha. Batching would lose *some* increments, not pin the value at
exactly 1 forever. The real culprit: the `[]` dep array means the effect runs **once**, so
the callback captured `count = 0` and every tick recomputes `0 + 1`. Same answer, every
second, for eternity. ♾️

Claude tells you exactly that, then loops the same idea back — reworded, from a new angle —
until it clicks. 💡

Nail all three? ✅ **Now** the code lands.

## 🧾 Then it grades your homework

No vague *"let me know if you have questions!"* You get a receipt: 🧮

```
✅ useTimer.ts:14 — setCount(c => c + 1) so the tick never reads a captured count
✅ useTimer.ts:19 — return clearInterval cleanup so unmount doesn't leak the timer
⚠️  Timer.tsx:8 — memoized onTick so the parent re-render stops resetting the hook

2/3 understood — gap on the memoized onTick
```

Every edit named. 🔍 Nothing bundled, nothing waved off as "minor." You explain each one and
each gets a verdict — **understood** ✅ / **partial** ⚠️ / **gap** ❌. Gaps get filled in on
the spot. 🩹

## 🕹️ How to use it

```
/quiz-me:quiz-me
```

Or just talk like a human — *"quiz me on this first"*, *"don't let me vibe-code this"* — and
it jumps in on its own. 🎯

### 🔧 Want it on for *everything*?

One line in your project's `CLAUDE.md`:

```markdown
Before implementing any non-trivial change, use the quiz-me skill.
```

Boom. 💥 Every real change in that repo goes through the gate. No reminding yourself, no
willpower required. 🧘

## 😴 It knows when to get out of the way

Zero quiz for lookups, formatting, renames, one-line typos, or anything where you already
called the root cause **and** the fix yourself. The gate is for changes that matter — not
friction cosplay. 🚫🎪

## 🤔 Why you'd want this

Autocomplete-driven development is *gloriously* fast… right up until something explodes at
2am 🔥 in code you have never actually read. Now you're debugging a stranger's work — except
the stranger was **you**, last Tuesday. 👻

This flips the deal:

| 🤖 Claude does | 🧑‍💻 You do |
| :--- | :--- |
| The reading | The **understanding** |
| The searching | The **deciding** |
| The typing | The **knowing why** |

And unlike a checkbox that says *"I reviewed this"* ☑️ — **this gate can actually fail.** 😬

Your codebase stays yours. 🏠

## 📄 License

MIT — go wild. 🎉

---

⭐ **Find it useful?** Star the repo so other people stop vibe-coding too.
