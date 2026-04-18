# Contributing

Thanks for your interest in contributing. This is a community-maintained fork and we actively accept improvements.

## Before you start

For anything non-trivial — new tools, protocol changes, significant refactors — please open an issue first to discuss the change. This avoids wasted work if the direction isn't right for the project.

Small fixes (typos, clear bugs, docs) can go straight to a PR.

## Development setup

See the [Quick Start](README.md#quick-start) section of the README. In short:

```bash
uv sync
uv run pytest tests/ -v
```

Tests use temporary directories and never touch a real vault.

## Pull request expectations

- **Tests**: add or update tests for any behaviour change. New tools need tests; bug fixes should have a regression test.
- **Scope**: one logical change per PR. Unrelated cleanups in a separate PR.
- **Commits**: focused and descriptive. Conventional-style prefixes (`feat:`, `fix:`, `docs:`, `chore:`, `test:`) are preferred but not required.
- **Security**: this project handles authenticated access to personal notes. Flag any change that touches auth, path resolution, or write behaviour so it gets closer review.

## Branch naming

Use a short prefix that matches the change type:

- `feat/<short-name>` — new functionality
- `fix/<short-name>` — bug fixes
- `docs/<short-name>` — documentation only
- `chore/<short-name>` — tooling, deps, housekeeping

## Merge strategy

Maintainers choose per PR:

- **Squash and merge** — default for PRs with many work-in-progress commits, or single-author changes where per-commit granularity doesn't matter. Author attribution on the squashed commit is preserved.
- **Merge commit** — used when the PR's commit history is clean and worth keeping on `main` verbatim (e.g. cherry-picks from other forks where preserving each upstream author's commits matters).

Rebase-and-merge is avoided because it rewrites committer metadata.

## Attribution

If your PR incorporates work from another fork or commit series, preserve the original author's commits (use `git cherry-pick` rather than copy-paste) and note the source in the PR description.

## AI tooling

Maintainers use AI assistants (Claude, Copilot, etc.) to help write and review code. This is disclosed openly rather than hidden:

- AI-assisted commits carry a `Co-Authored-By:` trailer naming the tool.
- Every change — AI-assisted or not — is reviewed and tested by a human before merge. The human committer takes full responsibility for the code.

External contributors are welcome to use AI assistance on their PRs. Please:

- Add a `Co-Authored-By:` trailer to AI-assisted commits, or mention it in the PR description.
- Review and test the output yourself before submitting. PRs that appear to be unreviewed AI output will be sent back for polish.
- Keep the PR focused and explain non-obvious decisions in the description.

We'd rather have disclosed AI-assisted work than hidden AI-assisted work.

## Code of conduct

Be constructive. Assume good faith. Disagree on technical merits, not people.
