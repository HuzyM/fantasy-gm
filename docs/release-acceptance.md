# Weekly Roster Review and Plan release candidate

Release gate: [#30](https://github.com/HuzyM/fantasy-gm/issues/30), under
[#26 A14–A18](https://github.com/HuzyM/fantasy-gm/issues/26). This record concerns
the personal, local, owned Yahoo hockey-team journey. **v1.0 is not accepted.**
Engineering readiness, human source correctness and practical usefulness have
separate gates; synthetic checks cannot establish the latter two.

## Candidate and evidence boundaries

The runtime candidate is Git revision
`42d93d9fc9691d4b1d41ecea088c7c03d15e08d8`, the main merge of PR #34. It includes
the deliberate weekly window, session-only manual plan and roster/comparison
context work from #27–#29. The #30 change updates operating instructions and this
evidence record only; it does not change runtime code, assets, dependencies or
the acceptance contract. Its final documentation/PR revision and exact-head
review/check evidence must accompany the PR before engineering readiness is
claimed. A later runtime change requires a new candidate and renewed evidence.

| Gate | Current verdict | Evidence still required |
| --- | --- | --- |
| Engineering readiness: A1–A14 | Local checks below passed; browser/final-head evidence pending at authoring | All three required checks on the final PR head; completed Standards/implementation and Spec reviews with actionable findings resolved |
| Human source correctness: A15 | Pending; no private acceptance run performed for #30 | Separately authorized human source reconciliation and relevant session-clearing checks |
| Practical usefulness: A16–A17 | Pending; zero of three required sessions recorded | Three private human reviews, each within ten minutes after loads, reduced effort in at least two, zero unsupported claims; coarse evidence only |
| Documentation and distribution: A18 | Operating/acceptance instructions supplied; distribution conditional | Review instructions with engineering evidence; resolve applicable provider/asset rights before any public distribution |

### Historical baseline, not a rerun of this candidate

[PR #34](https://github.com/HuzyM/fantasy-gm/pull/34) records refreshed
[Application CI run 39903665295](https://github.com/HuzyM/fantasy-gm/actions/runs/39903665295)
on `84fc673ea6d4853a4f186d0f553c9c4309fb6f4b`: all three required checks passed,
independent review had no remaining findings, and the hosted Python/npm audits
reported no known vulnerabilities in their scanned dependencies. This is
historical evidence on that PR head, not an exact-head result for the main merge
or the #30 documentation revision. Earlier acceptance documents' test counts are
superseded historical snapshots, not current counts.

The lock retains `certifi==2026.10.19` and `opentelemetry-api==1.45.1`. Advisory
audits and their coverage limitations remain as described in
[CI quality gates](ci-quality-gates.md#advisory-dependency-audits): Linux Python
markers exclude Windows-only and unsupported Emscripten packages. A clean scan
does not certify those exclusions or unknown vulnerabilities. Use actual reports
from the final-head run for current results; do not silently treat a failed or
unavailable advisory service as a clean audit.

### Current verification record

Authoring snapshot: October 23, 2026, at runtime revision
`42d93d9fc9691d4b1d41ecea088c7c03d15e08d8`. The local checks below were actually
rerun. Final-head hosted checks and completed independent reviews belong in the
associated #30 PR evidence, with their full SHA and run/review pointers; they
supersede this authoring snapshot only when observed. A pending row is not a
failure and does not imply the later PR evidence was already collected.

| Required evidence | Current #30 result |
| --- | --- |
| Complete offline Python tests, Ruff lint/format and native strict mypy | PASS: 847 Python tests; Ruff lint, format (81 files), native strict mypy (80 files). Python evidence: `test-results/python-windows-local-rerun.xml` |
| Frontend formatting, unit tests, TypeScript and production build | PASS: formatting; 159 tests in 19 files; TypeScript/production build during browser startup |
| Complete synthetic production-browser journey and retained Overview regression | Pending rerun |
| Blocking Windows visual comparisons and WCAG A/AA assertions | Pending rerun; retain 32 comparisons and existing tolerances |
| `Python Linux`, `Python Windows and browser`, `Frontend and local API` | Pending final PR head; a green earlier head is insufficient |
| Advisory Python/npm audits, findings and platform limits | Current local npm audit: zero reported vulnerabilities. Python and final-head hosted audit reports pending; historical hosted results above only |
| Independent Standards/implementation and Spec review | Pending completed reviews of final revision; requested reviews are insufficient |
| Scope/privacy diff and protected-file integrity | Pending final check; no runtime boundary change is intended |

The local environment used Python 3.12.15, Node 22.15.0 and uv 0.13.1; the
hosted workflow pins uv 0.12.23. Locked offline dependency installs succeeded.
The initial restricted-runner Python attempt was inconclusive (814 passed,
14 failed, 19 errors), with Windows wakeup-socket permission and temporary-folder
denials. The complete rerun under normal host permissions passed all 847 tests;
the test fixtures retained their provider-network and environment guards. This
permission adjustment authorized no live provider call or private launcher run.
The complete 80-case browser run and its blocking visual/accessibility checks
were still pending at this snapshot; `frontend/output/browser-results.json` is
the expected local result path, not proof of a completed pass.

Use the existing [blocking verification workflow](ci-quality-gates.md), including
its exact-head status summary. Browser verification uses fabricated protocol data
and the default synthetic server only. Do not run private mode or live providers
to fill engineering evidence. Retain blocking accessibility and visual assertions,
no retries or arbitrary synchronization sleeps, and the unchanged screenshot
tolerances. This documentation change requires no baseline update. Any future
intentional affected-screen change needs inspection before a targeted baseline
update; unrelated images must remain unchanged.

The final scope check must confirm no private persistence/export/telemetry,
Yahoo-backed AI/MCP exposure, Yahoo writes, provider expansion, background refresh,
automatic retries or purchases were introduced. Keep these existing untracked
files unchanged and unpublished:

- `docs/yahoo-nhl-crosswalk-static-audit.md`
- `docs/yahoo-nhl-player-id-crosswalk-research.md`
- `to-questionnaire-tjstats-crosswalk.md`

## Separately authorized human acceptance

Follow the [private acceptance runbook](local-application.md#human-release-acceptance-runbook)
only after the owner explicitly authorizes a human-operated session and its
bounded request budget. Engineering authorization does not authorize these runs.
No agent may launch private mode, authenticate Yahoo, inspect credentials/accounts
or observe private sessions. Close AI/MCP observation, browser automation,
recording/transcription, remote views and screen sharing first.

Each approved private launch allows one authorization exchange and at most four
Fantasy GETs, for discovery, owned teams, membership and one selected owned
roster. Each separately approved public window allows at most two existing
PuckAPI requests, normally six credits at reviewed rates. Use existing free-tier
access only, with no paid/trial access, account lookup, purchase, top-up, retry,
fan-out or background refresh. No balance is claimed. New windows, launches and
failure recovery must fit the explicit authorization; there is no implied budget
for extra runs or the three usefulness sessions.

### Human source correctness — pending

Privately verify the selected owned team and returned roster fields against the
owner's Yahoo source, including the distinction between reported eligibility and
assigned slots. Check representative displayed games against their source for
the exact seven-date Toronto window, including opponent, home/away, local time
and status where supplied. Check exact player/pair references, original dates
and window after creating/reopening manual plan items. Exercise the relevant
clearing behaviors using the runbook without extra unauthorized loads.

A mismatch affecting a claimed fact blocks acceptance until corrected or
accurately shown as disputed/unavailable. Sampled agreement never proves complete
coverage, full roster/reserve membership, rules, lineup legality or player
appearances. Missing/unsupported affiliations, excluded or disputed observations,
unknown coverage, unavailable performance and injury data stay qualified after
review. No-action-needed is a valid outcome; acknowledgement cannot verify a
source or prove a Yahoo change.

### Practical usefulness — pending

Complete three separately authorized human planning sessions. Start each review
timer after its authorized data loads finish; finish when the manager has reviewed
the window and prepared the intended review items or acknowledged no action
needed. Each review must take no more than ten minutes. The owner must report
reduced effort in at least two of three sessions. There must be zero unsupported
claims of completeness, participation, lineup legality or scoring advantage.
There is no minimum item count and no need to invent changes.

| Required session | Review duration after loads | Reduced effort | Coarse result |
| --- | --- | --- | --- |
| 1 | Not performed | Not assessed | Pending |
| 2 | Not performed | Not assessed | Pending |
| 3 | Not performed | Not assessed | Pending |

Share only coarse pass/fail, elapsed durations and reduced-effort verdicts, using
the safe report in the runbook. Do not share account fields, roster/plan content,
private structural details, capabilities, tokens, private links, screenshots or
provider bodies with an AI tool or issue. Add no telemetry, recording, export or
persistent private acceptance dataset. If a gate fails, report only the coarse
failure; pause acceptance. A failed usefulness gate requires reconsidering the
product, not decorative UI expansion.

## Release decision and rights

Keep #30 and parent #26 open while required human gates remain pending or failed;
use a non-closing PR reference to #30. Do not mark v1.0 accepted from engineering
checks alone. A completed engineering verdict may state that this exact candidate
is ready for separately authorized human acceptance, while correctness and
usefulness remain pending. No merge, public deployment or distribution follows
from this record.

Personal local acceptance does not establish public, commercial or multi-user
permission. Before public distribution, resolve applicable provider and asset
rights, or remove unlicensed bundled logos and use text fallbacks; preserve photo
attribution and applicable licenses. Official NHL logo redistribution rights remain
unresolved in [asset provenance](../frontend/ASSETS.md). This gate authorizes no
provider contact, rights-related code/asset changes or distribution.
