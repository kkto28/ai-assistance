---
name: commit-message-writer
description: Write clear, accurate commit messages from the current Git diff, including a concise summary and the reason for the change.
---

# Commit Message Writer

Use this skill when the user asks for a commit message, commit summary, change rationale, or help preparing a commit.

## Objective

Turn the actual repository changes into a concise, truthful commit message that explains:

1. **What changed** — the observable implementation or documentation update.
2. **Why it changed** — the problem, requirement, or user outcome motivating it.
3. **Important detail** — the main behavior, boundary, risk, or validation result a reviewer should know.

Never invent intent, files, tests, or behavior that are not supported by the diff and repository context.

## Required workflow

1. Inspect the repository state:
   - `git status --short`
   - `git diff --stat`
   - `git diff`
   - For staged changes, also inspect `git diff --cached`.
2. Read relevant nearby documentation, tests, and configuration when the diff alone does not establish the reason or behavior.
3. Separate:
   - implementation changes,
   - tests,
   - documentation/configuration,
   - unrelated or pre-existing work.
4. Identify the smallest accurate scope and choose a conventional type:
   - `feat` for a new capability,
   - `fix` for a defect correction,
   - `refactor` for behavior-preserving restructuring,
   - `test` for tests only,
   - `docs` for documentation only,
   - `build` or `ci` for tooling/build pipeline changes,
   - `chore` for maintenance that does not fit the above.
5. Produce the requested output format. If the user asks only for a message, do not add unnecessary commentary.

## Default output

```text
<type>(<scope>): <imperative summary>

Summary:
- <main change>
- <important supporting change>

Reason:
<The problem or user outcome this change addresses.>

Validation:
- <tests/checks run, or "Not run (documentation/configuration-only change).">
```

Keep the subject:

- Imperative and specific.
- At most 72 characters when practical.
- Free of a trailing period.
- Focused on the user-visible or architectural result, not the file list.

Use a body only when it adds context. Do not restate every changed line.

## Accuracy rules

- Base the message on the diff, not on assumptions from a ticket title.
- Mention migrations, compatibility behavior, security boundaries, data-loss risk, or breaking changes when present.
- If the reason is unclear, state the evidence-based reason briefly and mark uncertainty instead of fabricating motivation.
- Do not claim tests passed unless they were actually run and passed.
- Do not include secrets, tokens, document contents, or sensitive paths.
- If unrelated changes are present, call them out separately rather than combining them into the commit message.
- If changes are staged and unstaged, distinguish them before generating the message.
- Prefer one commit message for one coherent change; suggest splitting only when the diff contains clearly independent concerns.

## Examples

### Feature

```text
feat(workflows): add scheduled document briefing

Summary:
- Add a scheduler trigger that runs the document-brief workflow.
- Record workflow status and failures for each scheduled run.

Reason:
Users can generate recurring document briefs without starting the workflow manually.

Validation:
- Added scheduler and workflow integration tests.
```

### Fix

```text
fix(sync): preserve remote-only files during incremental indexing

Summary:
- Distinguish unavailable remote files from deleted files.
- Retry provider availability before updating the local catalog.

Reason:
Cloud-backed files were incorrectly treated as deleted when they were not
downloaded locally yet.

Validation:
- Added connector regression tests for unavailable and deleted states.
```

### Documentation or planning

```text
docs(plan): define modular agent and provider architecture

Summary:
- Document module boundaries for agents, tools, schedulers, interfaces, and LLM providers.
- Add incremental TDD delivery phases and Google Drive/Claude integration goals.

Reason:
The project needs an implementation path that supports replaceable providers and
small, testable vertical slices.

Validation:
- Not run (documentation-only change).
```

## Optional response modes

When requested, also provide:

- A one-line subject only.
- A Conventional Commits message without the `Summary`, `Reason`, and `Validation` labels.
- A release-note summary.
- A reviewer-oriented change summary.
