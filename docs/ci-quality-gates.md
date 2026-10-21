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
| `Python Windows and browser` | Native Windows Python 3.12 pytest suite including Windows input tests, native strict mypy, production build/TypeScript, the existing complete synthetic-API browser suite and 32 blocking Windows screenshot comparisons |
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

## Qualified Windows visual comparisons

The approved `docs/frontend/win32` images were generated locally with a system
Chrome whose exact baseline environment was not recorded. A shared `win32` label
alone does not establish equivalent browser, OS renderer or fonts. Playwright
[documents these environment dependencies](https://playwright.dev/docs/test-snapshots).

Two independent hosted Windows executions of `aeb21d2` in
[run 39298580835](https://github.com/HuzyM/fantasy-gm/actions/runs/39298580835)
each passed all 38 browser cases and matched all 32 existing baselines at the
unchanged `maxDiffPixelRatio: 0.005`. Their metadata was identical:
`windows-2025` image `20261007.264.1`, OS `10.0.26100`, Node `22.15.0`,
Playwright `1.64.1`, Chromium `156.0.8078.4`, bundled Barlow/Barlow Condensed
`5.3.0`. Thirty captures were byte-identical. The comparison laptop/tablet
portraits differed by at most 8/255 per colour channel; all 32 pairs had **zero
perceptually different pixels** under the locked Playwright comparator with
`maxDiffPixels: 0` and its unchanged default colour threshold. This qualifies
repeatable CI output compatible with the approved baselines; it does not recover
the unknown historical Chrome environment. No baseline image changed.

The Windows job therefore uses `VISUAL_COMPARE=1`: screenshot failures now block
alongside asset, interaction, layout, page-error, API and accessibility failures.
Each attempted visual comparison records matched/mismatch JSON before a blocking
error propagates and preserves available actual/expected/diff evidence. Summary
counts expect 32 comparisons. CI never updates or creates baselines. The optional
`VISUAL_COMPARE=advisory` investigation mode catches screenshot errors only.

Hosted OS images still update within the named release. When the image, browser,
fonts or capture output changes, inspect artifact differences and repeat captures
in the new recorded environment. Do not automatically replace approved images or
relax the tolerance to make CI pass. Rendering drift requires review of the
environment or any proposed baseline update; retain the failing evidence.

The weekly roster matrix adds Daily matchups / Roster week navigation. Its four
Planner baselines were inspected at desktop, laptop, tablet and mobile sizes,
including the comparison diffs, before replacement. The intentional navigation
row shifts existing content down 62 pixels. The other 28 images and the 0.005
comparison tolerance remain unchanged. Review environment: Windows 10.0.26200,
Chrome 155.0.8059.80, Node 22.15.0, Playwright 1.64.1 and bundled fonts 5.3.0.
Separate fabricated-observation captures exercise the matrix; browser assertions
also bound its sticky player column and verify mobile fixture exposure after
scrolling, since page-overflow and accessibility checks alone missed that defect.

## Two-player weekly game comparison visual review

The four Comparison baselines were reviewed at 1672, 1440, 768 and 390 pixels
after the original four images first matched in the same local environment.
The intentional changes replace the duplicate Upcoming Schedule panel with the
full-width Comparison Context panel and use games/synthetic-roster wording.
The new Schedule tab was separately captured and inspected at all four sizes;
its synthetic browser cases check aligned date rows, mobile stacking, readable
content, keyboard access, accessibility and cleared navigation context.
Review environment: Windows 10.0.26200, Chrome 155.0.8059.80, Node 22.15.0,
Playwright 1.64.1 and bundled fonts 5.3.0. Only the four Comparison images were
replaced after inspecting actual/expected differences. The other 28 images,
the 0.005 tolerance and all blocking checks remain unchanged.

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

The first hosted scans reported zero known vulnerabilities: 42 Linux Python
packages and npm's locked tree. The Python export preserves environment markers,
so Linux does not scan Windows-only `colorama`/`pywin32` or the unsupported
Emscripten-only `httpx2-jsfetch`. This is a remaining audit coverage limitation,
not evidence that those packages have been checked. Dependency metadata may
change independently of this commit; use the latest run's reports.

## Owner action: protect main

The audit found main unprotected and no active repository/parent rulesets. This
workflow does **not** silently change repository settings. After these checks have
run, the owner should create an active rule for `refs/heads/main` in GitHub
Settings → Rules/Rulesets (or branch protection), require a pull request and the
three exact check names above, selecting GitHub Actions as their source. Require
the branch to be up to date or use a merge queue; `merge_group` is supported.
Configure any administrator/bypass policy explicitly, and block force pushes and
branch deletion. Advisory dependency outcomes should not be selected as separate
required gates before triage. Windows visual comparisons are part of the required
`Python Windows and browser` job.

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
