# Issue Tracker

This repository uses **GitHub Issues** as its issue tracker.

## Configuration

- **Tracker**: GitHub Issues
- **CLI**: `gh` (GitHub CLI)
- **Repository**: Determined from `git remote -v` (the GitHub remote URL)

## Conventions

- Issues are created, read, and updated via the `gh` CLI
- The `gh` CLI must be authenticated (`gh auth login`)
- All issue operations assume the current working directory is the repository root

## PRs as a Request Surface

**Disabled by default.** This means external pull requests are NOT automatically added to the triage queue. If you want external PRs to appear in triage, edit this file and set the flag below to `true`.

```yaml
prs_as_request_surface: false
```

## Usage by Skills

- `to-tickets`: Creates GitHub issues from specifications
- `triage`: Labels and routes GitHub issues using the triage label vocabulary
- `to-spec`: Reads GitHub issues to generate specifications