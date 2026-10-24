This file owns repository-wide working standards. All agents MUST follow them and explicit user instructions; higher-priority platform instructions prevail. CAPITALIZED requirement words have the meanings defined by BCP 14 (RFC 2119 and RFC 8174).

# Document Boundaries

- **AGENTS.md:** working principles and required standards.
- **[Adversarial review skill](.agents/skills/adversarial-review/SKILL.md):** how to run the pre-commit review: reviewer dispatch, integrity snapshots, triage and reporting. Its [scratch-testing recipe](.agents/skills/adversarial-review/references/scratch-testing.md) owns scratch copies, import provenance and mutation evidence.
- **[README.md](README.md):** project overview. **[pyproject.toml](pyproject.toml):** package metadata, supported Python versions, development dependencies, pytest options and mypy settings. **[.github/workflows/python-tests.yml](.github/workflows/python-tests.yml):** CI commands and the tested Python-version matrix.

Link to the owning document instead of duplicating it. Skills implement these standards; they do not override them. If documents disagree, follow the owning document and confirm any material conflict with the user.

# Scope and Decisions

- If not running in a Docker container, stop and confirm with the user before continuing. This repository assumes its devcontainer with harness permissions set to Full Access or bypass; if the harness enforces restrictions, follow them and report the mismatch.
- Read relevant code and documentation and inspect repository status before editing.
- Give each change a boundary: intent, non-goals, validation and done criteria. Revalidate written tasks against the current code; do not broaden their scope unilaterally, and keep unrelated work untouched.
- State assumptions. Confirm unresolved choices that materially affect scope, public API, architecture, correctness or data safety before dependent work. Non-material assumptions MAY be made when repository evidence supports them; name them in the handoff.
- Accepted decisions and user authorization persist; do not ask again about settled choices.
- Subagents MAY be used for independent work; the main agent remains accountable for integration and verification.

# Library Contracts

This is a small, dependency-free library. Its public API is what each module exports in `__all__`, re-exported from [`pathlib_extensions`](src/pathlib_extensions/__init__.py).

- Changes to exported names, signatures, return values, raised exceptions, path semantics, filesystem side effects or logged messages are user-visible; confirm breaking changes with the user before implementing them.
- Library code MUST run on every Python version in `requires-python` and the CI matrix; do not use newer syntax or standard-library features without confirming a support change.
- Do not add runtime dependencies without user confirmation.
- Filesystem behavior is not portable by assumption: verify assumptions about Python versions, platforms or filesystems empirically or against version-appropriate documentation.

# Design and Documentation

- Prefer the simplest cohesive implementation within scope, with clear responsibilities and pure logic where practical. Avoid `Any` and `type: ignore` in new code.
- Before removing a layer, identify the behavior it carries (errors, ordering, messages, API-visible behavior) and keep what is still needed, with its tests.
- New or changed non-test functions, methods and classes MUST have Google-style docstrings covering purpose and any non-obvious contracts, side effects or constraints. Comments explain non-obvious reasons or trade-offs.
- Update documentation the change makes stale, distinguishing verified behavior from proposals and hypotheses. Markdown documentation MUST use one source line per prose paragraph, preserving structural line breaks (headings, lists, tables, code blocks).

# Tests

- Tests MUST protect behavior or an invariant and fail when it breaks. Cover boundaries, failure paths and compatibility contracts; avoid timing-dependent assertions. Test names describe the protected behavior and each test has a one-line docstring.
- Bug fixes SHOULD include a regression test that fails for the original defect and passes with the fix, where reproducible; report any inability to demonstrate the original failure. Assert public results, exceptions and side effects rather than only internal calls.
- Prefer real operations on test-owned temporary files for filesystem contracts, including link targets, permissions, collisions and failure cleanup where relevant. Use mocks for controlled fault injection or unavailable capabilities, not as the sole evidence that filesystem behavior works.
- New or changed tests MUST import the module under test as `import pathlib_extensions.my_module as testee`, call it as `testee.function_name`, and patch with `patch.object(testee, 'attribute', ...)`. Order test functions to match the source file.
- Tests MUST NOT reach external services or touch real user files. All reads and writes by tests or the code under test stay within test-owned temporary paths, including symlink and hard-link targets and failure paths. Reading source, installed dependencies and static test fixtures is permitted; this does not permit access to host data or real configuration. Use fixtures that own their teardown, such as `tmp_path` and `monkeypatch`; leave no files, environment variables or working-directory changes behind.
- Tests run in random order under `pytest-randomly`; order-dependent state is a defect, not a flake.
- Changes to data-loss-sensitive behavior (overwrite decisions, staged publication, permission handling, directory creation) MUST have targeted mutation evidence produced in a scratch copy under the [scratch-testing recipe](.agents/skills/adversarial-review/references/scratch-testing.md). The reviewer MAY request mutations wherever other protection is doubtful.
- Before removing or weakening coverage, show that a retained test still fails for a mutant breaking the protected property. Consolidating tests that keep the same cases and assertions needs no evidence per removed test body.
- `pyproject.toml` owns pytest discovery and coverage policy: collect from `tests`, measure the library package with branch coverage, show missing lines/branches, and require at least 90% combined statement-and-branch coverage for the project total. This is not a per-file threshold or separate statement/branch minimum. Inspect affected-module coverage; tests themselves are excluded from the coverage target. A passing total does not excuse untested changed behavior; inspect and explain uncovered branches in affected code. Coverage exclusions and test skips need a narrow rationale and retained verification where feasible; do not lower the gate or exclude library code just to make checks pass.

# Validation and Review

- Before implementation, record a passing baseline of the relevant checks on the starting revision. Fix a failing baseline in a separate, authorized change first.
- The final code, test or configuration candidate MUST pass `pytest`, `mypy .` and `ruff check .` (matching CI). The suite is fast: rerun gates after substantive edits instead of reusing earlier results. Resolve new warnings or explain them.
- Every non-trivial code, test or configuration change MUST pass the [review procedure](.agents/skills/adversarial-review/SKILL.md#procedure) before commit. A change is non-trivial if it could affect runtime behavior, the public API, test guarantees, build/configuration output or filesystem safety; when uncertain, review. Tightly coupled tasks committed together MAY share one review.
- Documentation-only changes (including governance and skill prose) and read-only assessments are exempt from gates and formal review; verify their claims, links and diff instead, preserving safeguards and authorization boundaries. Documentation consumed by build or runtime tools as executable input follows the non-trivial rules.
- Fix validated Blocking findings, then rerun gates and review. Non-blocking findings and Nits MAY be deferred with a recorded reason and revisit trigger, and MUST be reported to the user; deferrals that change scope, behavior or accepted risk need user agreement. Never silently discard or reclassify a finding.
- Never point a development or test run at real user files or mounted host data, including the Git and SSH configuration mounted by the devcontainer. Destructive operations on user data require explicit user authorization. Treat credentials and `.env` values as secrets: do not echo, log, commit or transmit them.
- Clean up owned processes and disposable artifacts. Identify owned PIDs before using `kill`; NEVER use `pkill -f`. Before finishing, check the diff, status and any changed guidance against the requested scope.

# Version Control

- Keep functionally independent changes in separate, self-contained commits. Honor requests to leave drafts uncommitted.
- Stage explicit paths and inspect the staged diff and status immediately before committing. NEVER use `git add -A` or `git commit -a`.
- Commit messages MUST start with `<Claude/Codex/...>: <one-line summary>`, followed by a blank line and explanatory paragraphs. Do not add a `Co-Authored-By` line.
