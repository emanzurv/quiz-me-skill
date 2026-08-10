# Recording the demo GIF

The GIF at the top of the main README is a real Claude Code session, recorded with
[VHS](https://github.com/charmbracelet/vhs).

```bash
brew install vhs
cd demo
vhs demo.tape
```

`fixture/` holds a seeded bug — `importUsers` calls `forEach` with an async callback, so it
returns a success count before any insert has finished. It spans two files on purpose, so
the change clears the skill's "more than one file" threshold and actually triggers a quiz.

Before recording:

1. Make sure the plugin is installed and hard mode is armed for the fixture directory, so
   the gate is visibly doing something.
2. Do a dry run without VHS and note how long the investigation takes. Tune the `Sleep`
   values in `demo.tape` to match — that's the only part that needs fiddling.
3. Record. Expect two or three takes.

Keep the final GIF under ~10MB or GitHub will be slow to load it inline. If it runs long,
raise `Set PlaybackSpeed` to `1.5` rather than cutting the quiz itself — the quiz is the
product.
