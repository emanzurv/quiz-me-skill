#!/usr/bin/env python3
"""Tests for the quiz-me enforcement gate.

The gate fails open by design, so a bug in it looks exactly like a passed quiz:
no error, no deny, the edit just runs. Nothing else in the plugin can notice
that. These tests are the only thing that can.

Run: python3 -m unittest discover -s plugins/quiz-me/hooks
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "gate.py")
HOOKS_JSON = os.path.join(HERE, "hooks.json")


class GateCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.home = os.path.join(self.tmp, "home")
        self.root = os.path.join(self.tmp, "repo")
        self.state = os.path.join(self.home, ".claude", "quiz-me")
        os.makedirs(self.state)
        os.makedirs(os.path.join(self.root, ".claude"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def key(self, root=None):
        return os.path.abspath(root or self.root).replace(os.sep, "_")

    def write_config(self, config, scope="project"):
        if scope == "project":
            path = os.path.join(self.root, ".claude", "quiz-me.json")
        else:
            path = os.path.join(self.home, ".claude", "quiz-me.json")
        with open(path, "w") as f:
            json.dump(config, f)

    def write_state(self, suffix, content, root=None, age_minutes=0):
        path = os.path.join(self.state, self.key(root) + suffix)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        if age_minutes:
            old = time.time() - age_minutes * 60
            os.utime(path, (old, old))
        return path

    def run_gate(self, *args, root=None, tool_input=None, mode=None, env=None,
                 payload=None, raw_stdin=None, session=None):
        root = root or self.root
        body = payload if payload is not None else {
            "cwd": root,
            "tool_name": "Edit",
            "tool_input": tool_input or {"file_path": os.path.join(root, "app.py")},
            "permission_mode": mode or "default",
            "session_id": session or "",
        }
        environ = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith("QUIZ_ME_") and k != "CLAUDE_CODE_SESSION_ID"
        }
        environ["HOME"] = self.home
        environ.update(env or {})
        return subprocess.run(
            [sys.executable, GATE, *args],
            input=raw_stdin if raw_stdin is not None else json.dumps(body),
            capture_output=True,
            text=True,
            env=environ,
            cwd=root,
        )

    def assertAllowed(self, proc):
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "", "expected no decision on stdout")

    def assertDenied(self, proc):
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "deny")
        return out["permissionDecisionReason"]


class TestArming(GateCase):
    def test_unarmed_allows(self):
        self.assertAllowed(self.run_gate())

    def test_project_config_arms(self):
        self.write_config({"enforce": True})
        self.assertIn("gate closed", self.assertDenied(self.run_gate()))

    def test_global_config_arms(self):
        self.write_config({"enforce": True}, scope="global")
        self.assertIn("gate closed", self.assertDenied(self.run_gate()))

    def test_project_config_inherits_global_keys(self):
        self.write_config({"enforce": True, "difficulty": "hard"}, scope="global")
        self.write_config({"ttlMinutes": 60})
        self.assertIn("5 questions", self.assertDenied(self.run_gate()))

    def test_env_arms_case_insensitively(self):
        proc = self.run_gate(env={"QUIZ_ME_ENFORCE": "TRUE"})
        self.assertIn("gate closed", self.assertDenied(proc))

    def test_env_arms_with_on(self):
        proc = self.run_gate(env={"QUIZ_ME_ENFORCE": " On "})
        self.assertIn("gate closed", self.assertDenied(proc))

    def test_env_ignores_unrelated_value(self):
        self.assertAllowed(self.run_gate(env={"QUIZ_ME_ENFORCE": "no"}))


class TestMarkers(GateCase):
    def setUp(self):
        super().setUp()
        self.write_config({"enforce": True})

    def test_global_marker_allows(self):
        self.write_state(".pass", "pass")
        self.assertAllowed(self.run_gate())

    def test_project_marker_allows(self):
        with open(os.path.join(self.root, ".claude", "quiz-me.pass"), "w") as f:
            f.write("pass")
        self.assertAllowed(self.run_gate())

    def test_expired_marker_denies(self):
        self.write_config({"enforce": True, "ttlMinutes": 30})
        self.write_state(".pass", "pass", age_minutes=90)
        self.assertIn("gate closed", self.assertDenied(self.run_gate()))

    def test_zero_ttl_never_expires(self):
        self.write_config({"enforce": True, "ttlMinutes": 0})
        self.write_state(".pass", "pass", age_minutes=60 * 24 * 30)
        self.assertAllowed(self.run_gate())

    def test_marker_found_through_symlinked_root(self):
        link = os.path.join(self.tmp, "link")
        os.symlink(self.root, link)
        self.write_state(".pass", "pass", root=os.path.realpath(self.root))
        self.assertAllowed(self.run_gate(root=link))

    def test_marker_found_from_subdirectory_of_repo(self):
        os.makedirs(os.path.join(self.root, ".git"))
        sub = os.path.join(self.root, "pkg", "sub")
        os.makedirs(sub)
        self.write_state(".pass", "pass")
        self.assertAllowed(self.run_gate(root=sub))

    def test_numeric_string_ttl_still_expires(self):
        self.write_config({"enforce": True, "ttlMinutes": "30"})
        self.write_state(".pass", "pass", age_minutes=90)
        self.assertIn("gate closed", self.assertDenied(self.run_gate()))

    def test_unparsable_ttl_falls_back_to_the_default(self):
        self.write_config({"enforce": True, "ttlMinutes": "soon"})
        self.write_state(".pass", "pass", age_minutes=60 * 24)
        self.assertIn("gate closed", self.assertDenied(self.run_gate()))

    def test_marker_found_despite_case_mismatch(self):
        path = os.path.join(self.state, self.key().lower() + ".pass")
        if os.path.basename(path) == self.key() + ".pass":
            self.skipTest("state key has no case to mismatch")
        with open(path, "w") as f:
            f.write("pass")
        self.assertAllowed(self.run_gate())


class TestOverrideScope(GateCase):
    def setUp(self):
        super().setUp()
        self.write_config({"enforce": True})

    def test_override_unlocks_the_session_that_asked_for_it(self):
        self.write_state(".pass", "override: sess-1 — user said no quiz")
        self.assertAllowed(self.run_gate(session="sess-1"))

    def test_override_does_not_unlock_another_session(self):
        self.write_state(".pass", "override: sess-1 — user said no quiz")
        proc = self.run_gate(session="sess-2")
        self.assertIn("gate closed", self.assertDenied(proc))

    def test_override_without_a_session_id_unlocks_nothing(self):
        self.write_state(".pass", "override: user said no quiz")
        proc = self.run_gate(session="sess-1")
        self.assertIn("gate closed", self.assertDenied(proc))

    def test_bare_override_unlocks_nothing(self):
        self.write_state(".pass", "override:")
        self.assertIn("gate closed", self.assertDenied(self.run_gate(session="sess-1")))

    def test_pass_marker_is_not_session_scoped(self):
        self.write_state(".pass", "pass")
        self.assertAllowed(self.run_gate(session="sess-2"))

    def test_override_still_expires_with_the_ttl(self):
        self.write_config({"enforce": True, "ttlMinutes": 30})
        self.write_state(".pass", "override: sess-1 — ship it", age_minutes=90)
        proc = self.run_gate(session="sess-1")
        self.assertIn("gate closed", self.assertDenied(proc))

    def test_project_override_is_scoped_too(self):
        with open(os.path.join(self.root, ".claude", "quiz-me.pass"), "w") as f:
            f.write("override: sess-1 — ship it")
        self.assertAllowed(self.run_gate(session="sess-1"))
        proc = self.run_gate(session="sess-2")
        self.assertIn("gate closed", self.assertDenied(proc))

    def test_env_session_id_matches_an_override_written_from_the_shell(self):
        self.write_state(".pass", "override: sess-env — ship it")
        proc = self.run_gate(env={"CLAUDE_CODE_SESSION_ID": "sess-env"})
        self.assertAllowed(proc)

    def test_env_session_id_does_not_match_another_session(self):
        self.write_state(".pass", "override: sess-1 — ship it")
        proc = self.run_gate(env={"CLAUDE_CODE_SESSION_ID": "sess-env"})
        self.assertIn("gate closed", self.assertDenied(proc))

    def test_case_insensitive_override_prefix(self):
        self.write_state(".pass", "Override: sess-1 — ship it")
        self.assertAllowed(self.run_gate(session="sess-1"))
        self.assertIn("gate closed", self.assertDenied(self.run_gate(session="x")))


class TestDenyBody(GateCase):
    def setUp(self):
        super().setUp()
        self.write_config({"enforce": True})

    def test_deny_routes_to_the_skill(self):
        reason = self.assertDenied(self.run_gate())
        self.assertIn("quiz-me:quiz-me", reason)

    def test_deny_carries_the_session_id_for_the_override_line(self):
        reason = self.assertDenied(self.run_gate(session="sess-1"))
        self.assertIn("override: sess-1 —", reason)

    def test_deny_without_a_session_id_says_so(self):
        reason = self.assertDenied(self.run_gate())
        self.assertIn("no session id", reason)


class TestExemptions(GateCase):
    def setUp(self):
        super().setUp()
        self.write_config({"enforce": True})

    def test_state_file_write_allowed(self):
        target = os.path.join(self.state, self.key() + ".pass")
        self.assertAllowed(self.run_gate(tool_input={"file_path": target}))

    def test_project_marker_write_allowed(self):
        target = os.path.join(self.root, ".claude", "quiz-me.pass")
        self.assertAllowed(self.run_gate(tool_input={"file_path": target}))

    def test_outside_root_allowed(self):
        target = os.path.join(self.tmp, "elsewhere", "notes.md")
        self.assertAllowed(self.run_gate(tool_input={"file_path": target}))

    def test_sibling_prefix_is_not_inside_root(self):
        target = self.root + "-old/app.py"
        self.assertAllowed(self.run_gate(tool_input={"file_path": target}))

    def test_project_config_write_is_gated(self):
        target = os.path.join(self.root, ".claude", "quiz-me.json")
        proc = self.run_gate(tool_input={"file_path": target})
        self.assertIn("gate closed", self.assertDenied(proc))

    def test_config_anywhere_in_the_repo_is_gated(self):
        target = os.path.join(self.root, "quiz-me.json")
        proc = self.run_gate(tool_input={"file_path": target})
        self.assertIn("gate closed", self.assertDenied(proc))

    def test_notebook_path_is_gated(self):
        target = os.path.join(self.root, "nb.ipynb")
        proc = self.run_gate(tool_input={"notebook_path": target})
        self.assertIn("gate closed", self.assertDenied(proc))


class TestPlanMode(GateCase):
    def setUp(self):
        super().setUp()
        self.write_config({"enforce": True})

    def test_plan_mode_uses_plan_reason(self):
        reason = self.assertDenied(self.run_gate(mode="plan"))
        self.assertIn("plan mode", reason)
        self.assertNotIn("difficulty", reason)

    def test_plan_mode_with_marker_allows(self):
        self.write_state(".pass", "pass")
        self.assertAllowed(self.run_gate(mode="plan"))

    def test_camel_case_permission_mode(self):
        payload = {
            "cwd": self.root,
            "tool_name": "Write",
            "tool_input": {"file_path": os.path.join(self.root, "a.py")},
            "permissionMode": "plan",
        }
        self.assertIn("plan mode", self.assertDenied(self.run_gate(payload=payload)))


class TestClear(GateCase):
    def test_clear_removes_both_markers(self):
        glob_marker = self.write_state(".pass", "pass")
        proj_marker = os.path.join(self.root, ".claude", "quiz-me.pass")
        with open(proj_marker, "w") as f:
            f.write("pass")
        proc = self.run_gate("--clear", payload={"cwd": self.root, "source": "startup"})
        self.assertAllowed(proc)
        self.assertFalse(os.path.exists(glob_marker))
        self.assertFalse(os.path.exists(proj_marker))

    def test_clear_skips_compact(self):
        marker = self.write_state(".pass", "pass")
        proc = self.run_gate("--clear", payload={"cwd": self.root, "source": "compact"})
        self.assertAllowed(proc)
        self.assertTrue(os.path.exists(marker))

    def test_clear_leaves_misses_and_streak(self):
        misses = self.write_state(".misses.md", "2026-01-01 — c — x\n")
        streak = self.write_state(".streak", "4")
        self.run_gate("--clear", payload={"cwd": self.root, "source": "clear"})
        self.assertTrue(os.path.exists(misses))
        self.assertTrue(os.path.exists(streak))


class TestDenyReason(GateCase):
    def setUp(self):
        super().setUp()
        self.write_config({"enforce": True})

    def test_default_difficulty_is_normal(self):
        self.assertIn("3 questions", self.assertDenied(self.run_gate()))

    def test_unknown_difficulty_falls_back_to_normal(self):
        self.write_config({"enforce": True, "difficulty": "brutal"})
        self.assertIn("3 questions", self.assertDenied(self.run_gate()))

    def test_env_overrides_configured_difficulty(self):
        self.write_config({"enforce": True, "difficulty": "easy"})
        proc = self.run_gate(env={"QUIZ_ME_DIFFICULTY": "hard"})
        self.assertIn("5 questions", self.assertDenied(proc))

    def test_streak_and_open_concepts_reported(self):
        self.write_state(
            ".misses.md",
            "2026-01-01 — cache key — scoped by what\n"
            "2026-01-02 — retry backoff — thought linear\n"
            "2026-01-03 — retry backoff — thought linear again\n",
        )
        self.write_state(".streak", "3")
        reason = self.assertDenied(self.run_gate())
        self.assertIn("streak 3", reason)
        self.assertIn("2 open concepts", reason)
        self.assertIn("(1 boss)", reason)

    def test_resolved_closes_a_concept(self):
        self.write_state(
            ".misses.md",
            "2026-01-01 — cache key — scoped by what\n"
            "2026-01-02 — cache key — RESOLVED\n",
        )
        self.assertNotIn("open concept", self.assertDenied(self.run_gate()))

    def test_zero_streak_omitted(self):
        self.write_state(".streak", "0")
        self.assertNotIn("streak", self.assertDenied(self.run_gate()))


class TestFailOpen(GateCase):
    def test_malformed_stdin_allows(self):
        self.write_config({"enforce": True})
        self.assertAllowed(self.run_gate(raw_stdin="not json at all"))

    def test_unreadable_config_allows(self):
        with open(os.path.join(self.root, ".claude", "quiz-me.json"), "w") as f:
            f.write("{ broken")
        self.assertAllowed(self.run_gate())

    def test_corrupt_streak_does_not_break_deny(self):
        self.write_config({"enforce": True})
        self.write_state(".streak", "not-a-number")
        self.assertIn("gate closed", self.assertDenied(self.run_gate()))


class TestHooksManifest(unittest.TestCase):
    def setUp(self):
        with open(HOOKS_JSON) as f:
            self.manifest = json.load(f)["hooks"]

    def test_every_file_editing_tool_is_matched(self):
        matcher = self.manifest["PreToolUse"][0]["matcher"]
        for tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            self.assertIn(tool, matcher.split("|"))

    def test_session_start_matches_compact_so_the_guard_is_live(self):
        matcher = self.manifest["SessionStart"][0]["matcher"]
        for source in ("startup", "resume", "clear", "compact"):
            self.assertIn(source, matcher.split("|"))


if __name__ == "__main__":
    unittest.main()
