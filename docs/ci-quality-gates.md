# Application CI and release gates

The workflow is `.github/workflows/frontend.yml`. It runs once per PR update,
including stacked PRs, and on main pushes, merge-queue groups and manual dispatch.
Feature-branch push runs are removed; superseded runs for the same PR/ref cancel.
There are no path exclusions that could leave required checks permanently pending.
All jobs use read-only repository permissions and checkout without persisted Git
credentials. No environment secrets or provider configuration is supplied.

## Blocking verification

| Exact check name | What it executes |
| --- | --- |
| `Python Linux` | Python 3.12, locked uv environment, complete offline pytest suite, Ruff lint and `ruff format --check` |
| `Python Windows and browser` | Native Windows Python 3.12 pytest suite including Windows input tests, native strict mypy, production build/TypeScript and the existing complete synthetic-API browser suite |
| `Frontend and local API` | Node 22.15.0, locked npm install, frontend formatting/unit tests, production build/TypeScript through Playwright's existing server command, all synthetic-API browser cases and the retained Overview interaction regression |

Python is not merely type-checked for Windows on Linux: Windows executes the
actual tests. Linux's existing Windows-only skips remain visible in pytest/JUnit
results. Lint/format run once, strict mypy runs natively on Windows, and frontend
unit tests run once on Linux. Each browser job builds once through the existing
Playwright configuration; the retained Linux Overview check reuses that build.
The Windows browser run provides OS-specific rendering and functional coverage,
not an extra browser/version matrix. uv 0.12.23, Node 22.15.0, npm's lockfile and
the Playwright dependency/browser revision are fixed; package and uv caches avoid
repeated downloads. Browser installation uses the lockfile's Chromium rather than
an independently updated system Chrome. Retries are not used to hide failures.

The suite covers all eight screens at four viewports, local assets, keyboard
interactions, Settings navigation in normal/compact layouts, overflow and axe
WCAG A/AA rules. Unit/API/protocol tests retain malformed-input, unauthorized
access, capability expiry, private restart/disconnect, public recovery, successful
server rotations, in-flight clearing, stale responses/request ordering and absence
of private browser storage. `test.only` is forbidden in CI. Test bodies remain
synthetic; test fixtures remove provider configuration and block live transports.
The production browser server is started with no private/public provider flags.

JUnit and browser JSON results, screenshots, accessibility attachments, visual
differences and environment metadata are uploaded for seven days even if checks
fail (except cancellation). Browser screenshots live in `output/playwright/screens`
so the legacy Overview captures do not overwrite the full-suite evidence. No
private profiles, storage files, tokens, traces of real sessions or environment
dumps are uploaded. The metadata allowlist contains OS/image, Node, browser,
Playwright and bundled font versions only.

## Visual comparisons: investigate before blocking

The approved `docs/frontend/win32` images were generated locally with a system
Chrome whose exact baseline environment was not recorded. A shared `win32` label
alone does not establish equivalent browser, OS renderer or fonts. Playwright
[documents these environment dependencies](https://playwright.dev/docs/test-snapshots).

The Windows job uses `windows-2025`, bundled versioned fonts, pinned Playwright
Chromium and `VISUAL_COMPARE=advisory` to compare all 32 existing images in the
same run as the blocking functional checks. Only the screenshot assertion is
advisory: failed asset, interaction, layout, page-error, API or accessibility
assertions still fail the job. Each visual comparison records matched/mismatch
JSON and preserves available actual/expected/diff evidence. Summary counts expect
32 comparisons. CI never updates or creates baselines. Existing local
`VISUAL_COMPARE=1` remains blocking.

Promotion requires inspection of actual CI artifacts against the approved designs,
an explicitly recorded equivalent baseline environment and repeated identical-head
Windows runs demonstrating stable captures. Do not silently replace local approved
images or relax the difference tolerance just to get green CI. If CI output differs
from the historical environment, retain the advisory results until reviewed CI
baselines and a maintenance policy are approved. Hosted OS images still update
within the named release; environment metadata makes that drift visible.

## Advisory dependency audits

Linux Python exports all locked dependency groups excluding the local project,
then runs isolated pinned `pip-audit==2.10.1` with dependency resolution/install
disabled. npm audits the existing locked runtime and development dependency tree.
Neither audit modifies dependencies. JSON reports and step outcomes are preserved;
findings and vulnerability-service/tool failures remain advisory pending triage.
No broad ignore list or automatic fix is applied. Marker/platform coverage and
any unavailable advisories must be reported with the actual results; a successful
scan is not a guarantee against unknown vulnerabilities or malicious packages.
These scanners send public dependency names/versions to public advisory services,
not provider/account data. No extra application dependency is introduced.

## Owner action: protect main

The audit found main unprotected and no active repository/parent rulesets. This
workflow does **not** silently change repository settings. After these checks have
run, the owner should create an active rule for `refs/heads/main` in GitHub
Settings → Rules/Rulesets (or branch protection), require a pull request and the
three exact check names above, selecting GitHub Actions as their source. Require
the branch to be up to date or use a merge queue; `merge_group` is supported.
Configure any administrator/bypass policy explicitly, and block force pushes and
branch deletion. Advisory dependency/visual outcomes should not be selected as
separate required gates before triage/stability approval.

The former single `frontend` context should not remain the required context after
migration: the meaningful gates are the three named jobs. Main protection cannot
be claimed until the owner applies and verifies the rule. No PR is merged or
retargeted by this CI work.

## Measurement

The old PR #14 workflow executed twice for the same commit: push 2m22s and PR
2m15s, each doing the same Linux work. Its log records 776 passed/26 skipped Python
tests, 64 frontend tests and 38 browser cases; Windows execution, Python formatting,
visual comparisons and dependency audits were absent. Production build/TypeScript
also ran both explicitly and again in the browser server command.

Actual new run durations, Windows/Linux results, dependency findings and screenshot
stability evidence are reported on the CI-hardening PR. Use measured runner/job
times for ongoing overhead estimates, separating one-off warm-up and repeated
Windows stability experiments from normal per-update work. Hosted-runner queue,
cache and advisory-service timing can vary; no paid service is required.
