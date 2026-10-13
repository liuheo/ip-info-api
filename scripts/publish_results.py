"""Publish report files to monitor-results without changing the source branch/index."""

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

RESULTS_REF = "refs/heads/monitor-results"
FILES = ("README.md", "latest.json")


def git(root, *args, data=None, env=None, check=True):
    return subprocess.run(["git", "-C", str(root), *args], input=data,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env=env, check=check)


def publish(root, output_dir):
    contents = {name: (output_dir / name).read_bytes() for name in FILES}
    remote = git(root, "ls-remote", "--exit-code", "origin", RESULTS_REF, check=False)
    parent = None
    if remote.returncode == 0:
        git(root, "fetch", "--no-tags", "origin", RESULTS_REF)
        parent = git(root, "rev-parse", "FETCH_HEAD").stdout.decode().strip()
    elif remote.returncode != 2:
        raise RuntimeError(remote.stderr.decode(errors="replace"))

    # A separate temporary index keeps both tracked source and staged user edits intact.
    with tempfile.TemporaryDirectory(prefix="ip-monitor-index-") as directory:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / "index"),
                   GIT_AUTHOR_NAME="github-actions[bot]",
                   GIT_AUTHOR_EMAIL="41898282+github-actions[bot]@users.noreply.github.com",
                   GIT_COMMITTER_NAME="github-actions[bot]",
                   GIT_COMMITTER_EMAIL="41898282+github-actions[bot]@users.noreply.github.com")
        git(root, "read-tree", "--empty", env=env)
        for name, data in contents.items():
            blob = git(root, "hash-object", "-w", "--stdin", data=data, env=env).stdout.decode().strip()
            git(root, "update-index", "--add", "--cacheinfo", f"100644,{blob},{name}", env=env)
        tree = git(root, "write-tree", env=env).stdout.decode().strip()
        if parent and git(root, "rev-parse", f"{parent}^{{tree}}").stdout.decode().strip() == tree:
            return parent
        parents = ["-p", parent] if parent else []
        commit = git(root, "commit-tree", tree, *parents,
                     data="更新 IP 接口检测结果\n".encode("utf-8"), env=env).stdout.decode().strip()
        # An explicit, non-forced refspec can never update the default branch.
        git(root, "push", "origin", f"{commit}:{RESULTS_REF}")
        return commit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    try:
        print(publish(args.root, args.output_dir or args.root / "monitor/output"))
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.stderr.decode(errors="replace")) from exc


if __name__ == "__main__":
    main()
