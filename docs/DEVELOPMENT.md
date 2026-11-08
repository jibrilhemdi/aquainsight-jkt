# Development workflow

Remote: https://github.com/jibrilhemdi/aquainsight-jkt . Branch: `main`.

The user's preference is to commit and push regularly at tested implementation milestones. Run `ruff check .` and `python -m pytest -q`, inspect `git diff --stat` and staged paths, then create a descriptive commit and push to `origin/main`. Do not force-push or overwrite unrelated remote history. A failed push is a blocker to report, not a reason to claim publication succeeded.

Raw official CSVs, virtual environments, private uploads, caches and environment secrets are excluded. `data/raw/.gitkeep` is the only versioned raw-directory entry. On machines without the separately obtained official files, the labeled synthetic demo and schema tests remain available; local-file integration tests skip.
