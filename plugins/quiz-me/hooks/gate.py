#!/usr/bin/env python3
"""quiz-me enforcement gate.

PreToolUse hook: denies Edit/Write/NotebookEdit until the quiz has been passed
in this session. Inside plan mode it denies with a different reason: the marker
cannot be written there and is not due until the plan is approved.
SessionStart hook (--clear): removes a stale pass marker so every new session
starts locked.

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

BOOKKEEPING_CONCEPTS = {"override"}

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

PLAN_DENY = (
    "\U0001F512 quiz-me \u00b7 gate closed \u2014 plan mode. The quiz comes after you "
    "approve the plan, not before.\n"
    "\u2192 Claude: nothing to unlock here \u2014 plan mode denies the marker write too, and "
    "that is not a deadlock. Finish the plan, call ExitPlanMode, then load the quiz-me "
    "skill and quiz before the first edit."
)

DENY_BODY = (
    "You'll be quizzed on this change before it lands. Say \"quiz override\" to skip it.\n"
    "→ Claude: do not edit. Load the quiz-me skill (Skill, `quiz-me:quiz-me`) and run the "
    "round it specifies — it carries the protocol, the unlock marker and the override "
    "format. Do not improvise a quiz from this message."
)


def deny_reason(level, root):
    counts = concept_counts(root)
    open_n = sum(1 for c in counts.values() if c >= 1)
    boss_n = sum(1 for c in counts.values() if c >= 2)
    streak = read_streak(root)

    extras = []
    if streak:
        extras.append("streak " + str(streak))
    if open_n:
        note = str(open_n) + " open concept" + ("s" if open_n != 1 else "") + " from past misses"
        if boss_n:
            note += " (" + str(boss_n) + " boss)"
        extras.append(note)
    suffix = " — " + ", ".join(extras) if extras else ""

    return (
        "🔒 quiz-me · gate closed — "
        + level
        + " difficulty: "
        + DIFFICULTY[level]
        + suffix
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


def git_root(path):
    """Nearest ancestor holding a .git entry, or None."""
    current = os.path.abspath(path)
    while True:
        if os.path.exists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def path_keys(root):
    """Filename-safe keys for this project, most likely first.

    The session cwd comes first, then the repo root it sits under. The skill
    writes its state under the repo root, so a session started in a
    subdirectory would otherwise look for a marker nobody ever writes and stay
    locked with nothing able to unlock it.
    """
    candidates = [os.path.abspath(root), os.path.realpath(root)]
    repo = git_root(root)
    if repo:
        candidates += [repo, os.path.realpath(repo)]
    keys = []
    for candidate in candidates:
        key = candidate.replace(os.sep, "_")
        if key not in keys:
            keys.append(key)
    return keys


def state_paths(root, suffix):
    """Every file that could hold this project's state, best guess first.

    The shell writes these names from $PWD; the hook derives them from the
    payload cwd. The two disagree on symlinked prefixes and on case, so an
    exact miss falls back to a case-insensitive scan of the state directory.
    """
    paths = [os.path.join(GLOBAL_DIR, key + suffix) for key in path_keys(root)]
    wanted = {os.path.basename(p).lower() for p in paths}
    seen = {p.lower() for p in paths}
    try:
        entries = os.listdir(GLOBAL_DIR)
    except OSError:
        entries = []
    for name in sorted(entries):
        path = os.path.join(GLOBAL_DIR, name)
        if name.lower() in wanted and path.lower() not in seen:
            paths.append(path)
    return paths


def marker_paths(root):
    return [os.path.join(root, MARKER)] + state_paths(root, ".pass")


def misses_paths(root):
    return state_paths(root, ".misses.md")


def streak_paths(root):
    return state_paths(root, ".streak")


def concept_counts(root):
    """concept -> consecutive open misses since its last RESOLVED line, or 0.

    Escape-hatch lines share the log's shape but are bookkeeping, not misses:
    `— override — <reason>` records that a batch shipped unquizzed. Counting
    them manufactures an `override` concept that goes boss after the second
    one, so the deny message reports a concept the user never got wrong.
    """
    lines = None
    for path in misses_paths(root):
        try:
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
            break
        except OSError:
            continue
    if lines is None:
        return {}
    counts = {}
    for line in lines:
        parts = line.rstrip("\n").split(" — ")
        if len(parts) < 3:
            continue
        concept, text = parts[1].strip(), parts[2].strip()
        if concept.lower() in BOOKKEEPING_CONCEPTS:
            continue
        counts[concept] = 0 if text == "RESOLVED" else counts.get(concept, 0) + 1
    return counts


def read_streak(root):
    for path in streak_paths(root):
        try:
            with open(path) as f:
                return int(f.read().strip())
        except (OSError, ValueError):
            continue
    return 0


def is_plan_mode(payload):
    mode = (
        payload.get("permission_mode")
        or payload.get("permissionMode")
        or os.environ.get("CLAUDE_PERMISSION_MODE")
        or os.environ.get("CLAUDE_CODE_PERMISSION_MODE")
        or ""
    )
    return str(mode).strip().lower() == "plan"


def is_armed(config):
    env = str(os.environ.get("QUIZ_ME_ENFORCE") or "").strip().lower()
    if env in ("1", "true", "yes", "on"):
        return True
    return bool(config.get("enforce"))


def ttl_minutes(config):
    """Configured TTL as a number.

    A non-numeric value falls back to the default rather than raising: the
    raise would land in main's fail-open handler, which turns a typo in the
    config into an expiry that silently never fires.
    """
    try:
        return float(config.get("ttlMinutes", DEFAULT_TTL_MINUTES))
    except (TypeError, ValueError):
        return float(DEFAULT_TTL_MINUTES)


def override_session(path):
    """Session id an override marker is scoped to, or None if it is not one.

    A pass marker unlocks any session in the project until it expires: passing
    the quiz is knowledge, and knowledge does not belong to one transcript. An
    override is the opposite — a bypass the user granted to the session that
    asked for it — so it carries that session's id and unlocks nothing else.
    An override with no id (the pre-scoping format, or a reason where the id
    should be) matches no session and unlocks nothing at all.
    """
    try:
        with open(path, encoding="utf-8") as f:
            body = f.read(4096).strip()
    except OSError:
        return None
    if not body.lower().startswith("override:"):
        return None
    rest = body[len("override:"):].split()
    return rest[0].strip(":") if rest else ""


def session_ids(payload):
    """Every id that identifies the session making this call.

    The payload id is authoritative, but the override marker is written by a
    shell command, which has only $CLAUDE_CODE_SESSION_ID to name itself with.
    Accept either, so a scoped override written from the shell still unlocks
    the session that asked for it.
    """
    candidates = (
        payload.get("session_id"),
        payload.get("sessionId"),
        os.environ.get("CLAUDE_CODE_SESSION_ID"),
    )
    ids = []
    for candidate in candidates:
        value = str(candidate or "")
        if value and value not in ids:
            ids.append(value)
    return ids


def marker_valid(root, config, sessions):
    ttl = ttl_minutes(config)
    for path in marker_paths(root):
        try:
            age_minutes = (time.time() - os.path.getmtime(path)) / 60
        except OSError:
            continue
        if ttl > 0 and age_minutes > ttl:
            continue
        scope = override_session(path)
        if scope is not None and scope not in sessions:
            continue
        return True
    return False


def is_state_file(root, tool_input):
    """True for the quiz's own state, which a locked session must still write.

    The config file is deliberately not on this list. It holds `enforce`, so
    exempting it would let a locked session disarm the gate and edit freely.
    """
    target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not target:
        return False
    if os.path.abspath(target).startswith(GLOBAL_DIR + os.sep):
        return True
    return os.path.basename(target) == "quiz-me.pass"


def is_outside_root(root, tool_input):
    target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not target:
        return False
    abs_root = os.path.abspath(root)
    abs_target = os.path.abspath(target)
    return not (abs_target == abs_root or abs_target.startswith(abs_root + os.sep))


def main():
    payload = json.load(sys.stdin)

    if "--clear" in sys.argv:
        if (payload.get("source") or "") == "compact":
            allow()
        root = payload.get("cwd") or os.getcwd()
        for path in marker_paths(root):
            try:
                os.remove(path)
            except OSError:
                pass
        allow()

    root = payload.get("cwd") or os.getcwd()
    config = load_config(root)
    sessions = session_ids(payload)

    if not is_armed(config):
        allow()
    if is_state_file(root, payload.get("tool_input") or {}):
        allow()
    if is_outside_root(root, payload.get("tool_input") or {}):
        allow()
    if marker_valid(root, config, sessions):
        allow()
    if is_plan_mode(payload):
        deny(PLAN_DENY)

    deny(deny_reason(difficulty(config), root))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        allow()
