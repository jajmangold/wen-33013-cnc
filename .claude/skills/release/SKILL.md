---
name: release
description: Cut a tagged release - move the Unreleased changelog section under a version, bump pyproject, verify everything is green and not stale, then tag. Use when the user asks to release, tag, or cut a version.
when_to_use: Only when the user explicitly asks for a release. Never as part of ordinary work.
argument-hint: [major|minor|patch]
disable-model-invocation: true
allowed-tools: Bash(git *) Bash(make *) Read Edit
---

## Cut a $1 release

```!
git status --short
git log --oneline -8
```

### Gate - all of these before anything else

```bash
make all      # verify + lint + test
```

STOP if any of these is true:

- tests failing
- `make verify` reports a stale generated file
- the working tree is dirty
- `## [Unreleased]` in `CHANGELOG.md` is empty - there is nothing to release

### Version

Semantic versioning, interpreted for a machine rather than a library:

- **major** - the machine description changes meaning, or a generated file's
  format breaks compatibility with firmware already flashed
- **minor** - new capability: an axis, a node, a generator, a screen
- **patch** - fixes and corrections, including corrected measurements

A changed measurement that makes the machine cut correctly is a **patch**. A
changed measurement that requires reflashing firmware is **minor** at least.

### Steps

1. Pick the version from the changes under `## [Unreleased]`.
2. In `CHANGELOG.md`, replace `## [Unreleased]` with
   `## [X.Y.Z] - YYYY-MM-DD` and add a fresh empty `## [Unreleased]` above it.
   Update the link definitions at the bottom.
3. Bump `version` in `pyproject.toml` to match.
4. `make all` once more.
5. Commit: `chore: release vX.Y.Z`
6. Tag: `git tag -a vX.Y.Z -m "vX.Y.Z"`
7. Push with tags: `git push --follow-tags`

### Rules

- MUST NOT add AI attribution or co-author trailers to the commit or tag.
- MUST NOT tag with a dirty tree or stale generated files - the tag would
  describe a state that was never tested.
- If the release includes a change to steps/mm, homing direction, or soft
  limits, say so prominently in the changelog entry. Those are the ones that
  break a physical machine rather than a build.
