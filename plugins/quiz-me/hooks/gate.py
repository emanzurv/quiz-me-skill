#!/usr/bin/env python3
"""quiz-me enforcement gate.

PreToolUse hook: denies Edit/Write/NotebookEdit until the quiz has been passed
in this session. SessionStart hook (--clear): removes a stale pass marker so
every new session starts locked.

Fails open on any error — a broken hook must never brick a session.
"""

import json
import os
import sys
import time

MARKER = os.path.join(".claude", "quiz-me.pass")
CONFIG = os.path.join(".claude", "quiz-me.json")
GLOBAL_DIR = os.path.expanduser(os.path.join("~", ".claude", "quiz-me"))
GLOBAL_CONFIG = os.path.expanduser(os.path.join("~", ".claude", "quiz-me.json"))
DEFAULT_TTL_MINUTES = 240

UNLOCK_CMD = (
    'mkdir -p ~/.claude/quiz-me && echo pass > ~/.claude/quiz-me/"${PWD//\\//_}".pass'
)

DIFFICULTY = {
    "easy": "2 questions, 3 options each, one clearly wrong distractor per question",
    "normal": "3 questions, 4 options each, every distractor plausible",
    "hard": (
        "5 questions, 4 options each, every distractor a near-miss that differs "
        "from the answer by one mechanism detail; previews narrowed to 2 lines"
    ),
}

DENY_BODY = (
    "The user has not passed the comprehension quiz for this change yet. Do not "
    "edit. Investigate, then quiz with AskUserQuestion (root cause / mechanism / "
    "blast radius), filling in header, description, and preview on every option, "
    "and placing the correct answer at slot `line mod options + 1` rather than first. "
    "After a 100% pass, run:\n"
    "  " + UNLOCK_CMD + "\n"
    "then edit. If the user explicitly said to override, write "
    "`override: <their reason>` to that path instead of `pass`, and say plainly "
    "that the change is shipping unverified."
)


def deny_reason(level):
    return (
        "🔒 quiz-me · gate closed — "
        + level
        + " difficulty: "
        + DIFFICULTY[level]
        + ".\n"
        + DENY_BODY
    )


def allow():
    sys.exit(0)


def deny(reason):
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )
    sys.exit(0)


def load_config(root):
    merged = {}
    for path in (GLOBAL_CONFIG, os.path.join(root, CONFIG)):
        try:
            with open(path) as f:
                loaded = json.load(f)
        except Exception:
            continue
        if isinstance(loaded, dict):
            merged.update(loaded)
    return merged


def difficulty(config):
    level = os.environ.get("QUIZ_ME_DIFFICULTY") or config.get("difficulty")
    level = str(level or "normal").strip().lower()
    return level if level in DIFFICULTY else "normal"


def marker_paths(root):
    return [
        os.path.join(root, MARKER),
        os.path.join(GLOBAL_DIR, root.replace(os.sep, "_") + ".pass"),
    ]


def is_armed(config):
    if os.environ.get("QUIZ_ME_ENFORCE") in ("1", "true", "yes"):
        return True
    return bool(config.get("enforce"))


def marker_valid(root, config):
    ttl = config.get("ttlMinutes", DEFAULT_TTL_MINUTES)
    for path in marker_paths(root):
        try:
            age_minutes = (time.time() - os.path.getmtime(path)) / 60
        except OSError:
            continue
        if ttl <= 0 or age_minutes <= ttl:
            return True
    return False


def is_state_file(root, tool_input):
    target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not target:
        return False
    if os.path.abspath(target).startswith(GLOBAL_DIR + os.sep):
        return True
    name = os.path.basename(target)
    return name in ("quiz-me.pass", "quiz-me.json", "quiz-me-misses.md")


def main():
    payload = json.load(sys.stdin)

    if "--clear" in sys.argv:
        root = payload.get("cwd") or os.getcwd()
        for path in marker_paths(root):
            try:
                os.remove(path)
            except OSError:
                pass
        allow()

    root = payload.get("cwd") or os.getcwd()
    config = load_config(root)

    if not is_armed(config):
        allow()
    if is_state_file(root, payload.get("tool_input") or {}):
        allow()
    if marker_valid(root, config):
        allow()

    deny(deny_reason(difficulty(config)))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        allow()
