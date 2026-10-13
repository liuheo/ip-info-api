import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publish_results", ROOT / "scripts/publish_results.py")
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.env = patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(base / "empty-config"), "GIT_CONFIG_NOSYSTEM": "1"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.remote = base / "remote.git"
        self.repo = base / "repo"
        self.output = base / "output"
        self.output.mkdir()
        subprocess.run(["git", "init", "--bare", str(self.remote)], check=True, capture_output=True)
        subprocess.run(["git", "init", "-b", "master", str(self.repo)], check=True, capture_output=True)
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.com")
        (self.repo / "README.md").write_text("source", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-m", "initial")
        self.git("remote", "add", "origin", str(self.remote))
        self.git("push", "origin", "master")
        self.head = self.git("rev-parse", "HEAD")
        (self.output / "README.md").write_text("report one", encoding="utf-8")
        (self.output / "latest.json").write_text('{"results": []}', encoding="utf-8")

    def git(self, *args):
        return publisher.git(self.repo, *args).stdout.decode().strip()

    def test_create_update_and_repeat_preserve_source_and_index(self):
        (self.repo / "README.md").write_text("staged edit", encoding="utf-8")
        self.git("add", "README.md")
        (self.repo / "README.md").write_text("unstaged edit", encoding="utf-8")
        status = self.git("status", "--porcelain")
        index = self.git("write-tree")
        first = publisher.publish(self.repo, self.output)
        self.assertEqual(self.git("ls-tree", "--name-only", first).splitlines(), ["README.md", "latest.json"])
        self.assertEqual(publisher.publish(self.repo, self.output), first)
        (self.output / "README.md").write_text("report two", encoding="utf-8")
        second = publisher.publish(self.repo, self.output)
        self.assertNotEqual(first, second)
        self.assertEqual(self.git("rev-parse", f"{second}^"), first)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.head)
        self.assertEqual(self.git("write-tree"), index)
        self.assertEqual(self.git("status", "--porcelain"), status)
        self.assertEqual(self.git("ls-remote", "origin", "refs/heads/master").split()[0], self.head)
        self.assertEqual(self.git("ls-remote", "origin", publisher.RESULTS_REF).split()[0], second)

    def test_push_rejects_racing_results_without_overwriting(self):
        first = publisher.publish(self.repo, self.output)
        (self.output / "README.md").write_text("report two", encoding="utf-8")
        original_git = publisher.git
        racing_commit = None

        def race(root, *args, **kwargs):
            nonlocal racing_commit
            if args[0] == "push":
                tree = self.git("rev-parse", f"{first}^{{tree}}")
                racing_commit = original_git(root, "commit-tree", tree, "-p", first, data=b"concurrent result\n").stdout.decode().strip()
                original_git(root, "push", "origin", f"{racing_commit}:{publisher.RESULTS_REF}")
            return original_git(root, *args, **kwargs)

        with patch.object(publisher, "git", side_effect=race):
            with self.assertRaises(subprocess.CalledProcessError):
                publisher.publish(self.repo, self.output)
        self.assertEqual(self.git("ls-remote", "origin", publisher.RESULTS_REF).split()[0], racing_commit)
        self.assertEqual(self.git("ls-remote", "origin", "refs/heads/master").split()[0], self.head)


if __name__ == "__main__":
    unittest.main()
