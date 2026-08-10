# Records the README demo GIF with VHS: https://github.com/charmbracelet/vhs
#
#   brew install vhs
#   cd demo && vhs demo.tape
#
# This records a real Claude Code session against fixture/importUsers.js.
# Expect to re-record a few times until the timing lines up — the Sleep values
# below are the only thing you need to tune.

Output demo.gif

Set Shell zsh
Set FontSize 15
Set Width 1280
Set Height 760
Set Padding 24
Set Theme "Catppuccin Mocha"
Set TypingSpeed 45ms
Set PlaybackSpeed 1.0

Hide
Type "cd fixture && clear"
Enter
Sleep 1s
Show

Type "claude"
Enter
Sleep 6s

Type "the import says 500 users imported but only ~30 are in the database"
Sleep 800ms
Enter

# Claude investigates, then opens the quiz. Bump this if it needs longer.
Sleep 45s

# Question 1 — move down to the forEach answer and pick it.
Down
Sleep 900ms
Down
Sleep 900ms
Enter
Sleep 8s

# Question 2 — mechanism.
Down
Sleep 900ms
Enter
Sleep 8s

# Question 3 — blast radius.
Down
Sleep 900ms
Down
Sleep 900ms
Enter

# Scorecard, gate opens, fix lands, receipt prints.
Sleep 40s
