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
DEFAULT_TTL_MINUTES = 240

DENY_REASON = (
    "quiz-me gate is closed. The user has not passed the comprehension quiz for "
    "this change yet. Do not edit. Investigate, then quiz with AskUserQuestion "
    "(root cause / mechanism / fix). After a 100% pass, run "
    "`mkdir -p .claude && echo pass > .claude/quiz-me.pass`, then edit. "
    "If the user explicitly said to override, write `override: <their reason>` "
    "to that file instead and say plainly that the change is shipping unverified."
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
    try:
        with open(os.path.join(root, CONFIG)) as f:
            return json.load(f)
    except Exception:
        return {}


def is_armed(config):
    if os.environ.get("QUIZ_ME_ENFORCE") in ("1", "true", "yes"):
        return True
    return bool(config.get("enforce"))


def marker_valid(root, config):
    path = os.path.join(root, MARKER)
    try:
        age_minutes = (time.time() - os.path.getmtime(path)) / 60
    except OSError:
        return False
    ttl = config.get("ttlMinutes", DEFAULT_TTL_MINUTES)
    return ttl <= 0 or age_minutes <= ttl


def is_state_file(root, tool_input):
    target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not target:
        return False
    name = os.path.basename(target)
    return name in ("quiz-me.pass", "quiz-me.json", "quiz-me-misses.md")


def main():
    payload = json.load(sys.stdin)

    if "--clear" in sys.argv:
        root = payload.get("cwd") or os.getcwd()
        try:
            os.remove(os.path.join(root, MARKER))
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

    deny(DENY_REASON)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        allow()
