# OPT-003A: offline scoring and daily-input qualification

Status: proposed design only. No runtime code or new tests implemented.
Base: merged main `a00333a2bd60fde9a41c71edfbc307ada02c2bf0`.
OPT-002 PR #37 was merged first; this design is a separate change.

## Intent and scope

Qualify the inputs to the existing supplied-value daily skater solver before
connecting real data or claiming useful predictions. The proposed implementation
is one small pure qualification module, immutable input/result types only where
existing types are insufficient, and synthetic tests. It adds no transport,
provider path, UI, persistence, dependency, forecast model or autonomous action.
Implementation requires approval of this design and explicit code scope.

User-reported league: daily H2H Points; C2/LW2/RW2/D4, G2, BN4, IR2,
IR+2, with no UTIL/F/W. Normal capacity is 16, reserve capacity is 4.
The stated snapshot has 18 players, including 2 reserve occupants, leaving 16
normal players. Slot capacity is not actual occupancy or proof of completeness.
G2 does not prove exactly two rostered goalies; do not infer 14 available skaters.
The 14-skater OPT-002A fixture is synthetic.

## Approaches

Recommended: qualify explicit inputs offline, preserving unknowns and refusing
solver preparation when required evidence is missing. This fits the existing
reported-facts models and exposes the smallest useful contract.

A direct roster-to-solver adapter would silently need unresolved scoring, date,
participation and lock assumptions. A forecast or matchup model would add sources
and evaluation obligations before those assumptions are qualified. Defer both.
These are design recommendations, not claims of user approval of implementation.

## Verified now versus unknown

| Area | Verified repository behavior | Still unknown |
| --- | --- | --- |
| Scoring | Settings join categories/modifiers by stat ID; retain finite Decimal values, validated literals, enabled/display flags, optional scopes, opaque format code and incomplete markers. | Complete league scoring semantics, stat units/identity mapping, conflicting scopes, flag interpretation and any rounding/aggregation policy. An `incomplete=False` structural observation is not semantic certification. |
| Roster | Unique reported identities, literal eligible/selected positions, explicit coverage and optional count normalize independently of scoring. Required identity/count errors reject; some optional failures preserve facts with uncertainty. | Complete effective roster, reserve inclusion, actual player type and eligibility, injury/participation status, scoring-effective date and legal moves. A returned count is not completeness proof. |
| Daily date | Missing dates stay missing; current unparameterized GET leaves `requested_date=None`. Verifier requires explicit matching roster/selected dates for its coverage check. | League-specific effective day/timezone, deadlines, as-of freshness, post-start edits and reschedule/postponement behavior. |
| Locks | OPT-002 honors supplied fixed active assignments. Roster `is_editable` is syntax-checked but has no normalized lock field; `is_prescoring` presence marks context unverified. | Per-player active/bench locks and when they take effect. Neither a team flag nor an NHL start time proves a legal move. |
| Stats | No player-stat observation model, stat parser, or stats path exists in the current Yahoo read allowlist. Existing scoring rules describe configuration, not observations or projections. | Suitable source, units, period, completeness, corrections, identity mapping, permitted use and projection calibration. |
| Access | Fixed human-only read paths, bounded in-memory responses, and unwired Yahoo MCP remain. OAuth configuration sends no scopes; Fantasy Sports Read is documented as app configuration. | Current account permissions and live behavior were not checked. Read access does not authorize AI exposure or new data requests. |

Inspection anchors: `domain/settings.py`, `domain/roster.py`,
`domain/lineup.py`, `providers/yahoo/settings.py`,
`providers/yahoo/fantasy.py`, `providers/yahoo/contract_verifier.py`,
`policy/yahoo.py`, `config/yahoo.py`, and `mcp/server.py`, all under
`src/fantasy_gm/`. Existing tests cover partial information, roster coverage,
settings metadata, contract compatibility and solver oracles. They do not
establish live semantics.

Yahoo's [public API reference](https://sports.yahoo.com/developer/docs/) describes
NHL rosters by date, and separate settings and player-stat resources. Its roster
write examples do not establish the current NHL GET XML contract or this league's
locks. This public documentation was consulted without calling Fantasy API
endpoints. No stats or date-parameterized request is authorized here.

## Proposed bounded contract

The qualifier returns either a complete supplied daily problem or an unavailable
result with fixed reason codes. Separate configuration, date, roster, locks and
values evidence; preserve useful observations when another section is unknown.
Evidence labels describe explicit inputs, not provider certification.

1. **Context:** explicit effective date, as-of instant and timezone provenance.
   A Toronto weekly window is not a Yahoo matchup week. Missing or conflicting
   roster/assignment dates or unverified provider context prevent preparation.
   Future code must not fill dates from the computer clock.
2. **Scoring:** an explicitly qualified points format and supported additive
   skater rules, with stat identity, units, finite Decimal weights, scope and
   complete flag interpretation. Missing weights are unknown, never zero.
   Unknown/nonadditive rules, scope conflicts and unsupported rounding refuse
   scoring. Do not equate skater/goalie scope with a selected C/LW/RW slot.
3. **Values:** distinguish realized stats, projected stat quantities and supplied
   projected points. Any stat vector needs explicit identity mapping, time period,
   unit, status/completeness and as-of cutoff. Synthetic additive examples may use
   an exact weighted sum. This is arithmetic qualification, not a forecast.
   Reject mismatched periods/identities, duplicate stats, nonfinite values,
   floats and missing required quantities. Zero requires an explicit known value.
4. **Roster partition:** classify normal skaters, goalies and reserve occupants
   from explicit supported evidence. Only qualified normal skaters enter the
   solver. Preserve goalie/reserve selections outside it. Check normal and reserve
   counts independently; do not demand every optional starter slot be filled.
   Shared BN4 capacity must account for all retained normal players, including
   benched goalies. No IR activation, goalie selection or position expansion.
5. **Moves:** every relevant skater needs explicit movable, fixed-active, or
   fixed-bench evidence for the target date. Unknown is not movable.
   Fixed-active assignments become solver locks. Fixed-bench players remain
   outside the candidate pool and cannot be promoted. Refuse incompatible,
   stale, missing or conflicting evidence. An empty lock tuple alone is
   insufficient proof that everyone can move.
6. **Solver boundary:** literal C/LW/RW/D eligibility, capacities 2/2/2/4,
   qualified baseline, fixed active locks and finite supplied daily values.
   Preserve OPT-002 tie and optional-slot semantics and validate the complete
   retained roster after solving. Optional empty slots can overflow the shared
   bench even when the supplied problem qualified; reject that result rather
   than repair it or change OPT-002 semantics. Qualification or post-solve
   rejection yields no recommendation or delta.

Suggested reason families: unsupported scoring, unknown stat semantics,
unqualified date, incomplete roster evidence, unknown locks, invalid partition,
missing values. Do not add a diagnostic framework or leak provider values in errors.

## Offline qualification and acceptance

Implement only after approval, with fabricated identities and fixtures:

| Cases | Expected check |
| --- | --- |
| Decimal weighted sums, negative/zero values, supported skater scopes | Match an independent Fraction/hand calculation; retain exact supplied totals. |
| Absent modifier, display-only/disabled/unknown flags, conflicting or goalie scopes, unsupported rounding | Refuse or explicitly exclude only with established semantics; never invent zero or mix goalie rules. |
| Absent/mismatched dates, stale as-of, unsupported week/state; before/at/after a supplied deadline and DST boundary | Preserve unknowns; enforce the explicitly supplied rule without inventing Yahoo deadline semantics. |
| 18-player fabricated roster with 2 reserves and 16 normal; varying goalie counts | Exact partition, shared bench accounting, no reserve/goalie leakage, no assumed 14-skater count. |
| Fixed starter, fixed bench, unknown lock, changed selected date | Respect both fixed states or refuse before calling the solver. |
| OPT-002 full-size baseline tie and flexible-forward cases | Retain independent optimum/tie comparisons with the new supplied-input boundary. |
| Missing stats versus observed zero; wrong identity/unit/period; post-cutoff information | No manufactured value and no future information in inputs. |
| Optional negative-value starter is benched, causing BN4 overflow | Post-solve rejection with no recommendation or delta; do not silently force starters. |
| Refusal stages | Preflight failures make zero solver calls. Post-solve rejection may follow one solve. Both make zero provider calls; access allowlist stays unchanged. |

Run the focused qualification/parser/optimizer tests, then the full existing
offline suite, Ruff lint/format, strict mypy and the three hosted CI gates at the
resulting exact head. These are planned checks, not executed OPT-003A results.

## Deferred decisions and exit

No live OAuth, sessions, credentials, real roster/provider data, new provider GETs,
PuckAPI usage, charges or captured private fixtures. No historical data retrieval,
baseline forecast, matchup adjustment, calibrated upside strategy or win-probability
claim. Future data use needs separate authorization and applicable policy clearance.

Before a later forecast, approve source/units/period and a frozen baseline plus
chronological held-out evaluation, with explicit missingness, participation and
leakage controls. Calibration and strategy follow baseline validation.

This design can finish with the unknowns above still unresolved. Synthetic tests
may qualify mechanics only. Real-data recommendations remain blocked until their
own scoring, effective-date, roster, lock, stats and access evidence is established.
