# OPT-002: supplied-value daily skater assignment

This implements the pure solver slice proposed by the external OPT-001 feasibility
specification. It chooses the best legal assignment **only for the complete supplied
assumptions and projections**. It does not establish predictive advantage, actual
Yahoo legality, improved Head-to-Head win probability or a production recommendation.
The existing application and private human acceptance gates are unchanged.

## Interface

`fantasy_gm.optimizer.daily_skaters.optimize_daily_skaters(players, slots,
current=(), locked=()) -> DailyLineupResult`

All inputs are immutable domain models in `fantasy_gm.domain.lineup`:

- `SkaterProjection(player_id, projected_points, eligible_positions)`: fictional
  identifier, finite **Decimal** value and a nonempty tuple of explicitly allowed
  positions. Missing projections, floats and unsupported extra fields are rejected.
- `SlotCapacity(position, capacity)`: a nonnegative integer maximum for one slot
  type. Zero capacities are valid. Every slot is optional unless occupied by a lock.
- `LineupAssignment(player_id, position)`: used for both the current baseline and
  the fixed active assignments. Aggregate capacities distinguish slot types; equal
  slots within a type have no separate identity.

Supported codes are `C`, `LW`, `RW`, `D`, `F`, `W`, `UTIL`. These are literal edges:
`C` does not imply `F` or `UTIL`, and `LW` does not imply `W`. Supply every allowed
code explicitly. No provider eligibility or position expansion is inferred.
Goalie, bench and reserve codes are unsupported. Frozen goalie/reserve selections
stay outside this skater input; no real roster is read or adapted here.

The baseline may be partial, but every supplied assignment must name a known,
eligible player within capacity, with no duplicates. It is not silently repaired.
Locks independently constrain the solution, even if they differ from the baseline.
A lock can force a negative total or negative estimated improvement. Unknown lock
semantics must be resolved by a future caller before supplying this contract.

The result contains canonical starting `assignments`, `benched_player_ids`,
`projected_points`, `baseline_points`, `estimated_improvement`, and per-player
`changes` with old/new positions, supplied value and a factual joint-total reason.
The delta is optimized total minus supplied baseline total using the same values.
Coupled changes are explained as a joint assignment, not independent scoring gains.
No change is sent anywhere or retained by the solver.

## Algorithm and determinism

Capacity-vector dynamic programming processes players in sorted identifier order.
For each occupancy vector it retains the best partial assignment. Each next player
can be benched or placed in exactly one eligible slot with remaining capacity;
a locked player has only its fixed placement. Flexible players therefore compete
across all positions simultaneously, rather than taking slots greedily.

For the same processed players and occupancy, remaining feasible choices are
identical. A worse partial score cannot improve a completion, so retaining the best
candidate per vector preserves global optimality. The output constraints and locks
are checked again before returning.

Ties prefer fewer changed players, then lexicographically smaller sorted
`(player_id, position)` assignments. A start, bench or position move each counts as
one changed player. Thus an already optimal valid baseline is preserved exactly
as assignments, regardless of input tuple order. With no baseline, optional zero
and negative starters are left out. A zero-value current starter may remain on a tie.

Arithmetic uses a private Decimal context with enough precision for exact sums and
the delta. It does not inherit or modify the caller's precision, rounding or traps.
Inexact/unrepresentable arithmetic is rejected rather than rounded into a result.
The candidate-state bound is `product(min(capacity, player_count) + 1)`; each player
considers each slot type for each state. Tuple copying/comparison also costs time
proportional to the partial lineup length. To bound work, inputs exceeding 100,000
capacity states or requiring over 10,000 digits of working precision are rejected.
In addition, a conservative total-work estimate must not exceed 50,000,000:

`player_count * state_bound * (slot_type_count + 1) * (lineup_bound + 1)`

Here `lineup_bound = min(sum(effective_capacities), player_count)`. The estimate
accounts for all player/state/slot visits and the lineup tuple copying/comparison
factor. It is a preflight size safeguard, not a precise instruction count or a
wall-clock guarantee. It may reject sparse inputs whose actual reachable work
would be smaller. It raises `UnsupportedLineupError` before the DP begins; it
never returns a partial or approximate optimum. Existing numeric limits still
bound Decimal arithmetic separately. The 14-skater C2/LW2/RW2/D4 case estimates
103,950 work units; even a fully flexible 30-skater, 16-slot C2/LW2/RW2/D4/F2/W2/UTIL2
case estimates 14,871,600, leaving headroom under the limit. The old state limit
alone would accept 100 fully flexible skaters with four slots of each of seven
types (78,125 states); its 1,812,500,000 estimated units are now rejected.
No approximation, truncated search or external solver is used.

## Rejections and verification

Model construction raises Pydantic `ValidationError` for invalid field types or
values. The solver raises `UnsupportedLineupError` for ambiguous duplicate inputs,
unknown player references and unsupported size/numeric ranges. It raises
`InfeasibleLineupError` for illegal baseline/fixed assignments, including duplicate
placement, invalid assignment eligibility and oversubscribed locks. Both are
`ValueError` subclasses. An empty feasible lineup is a valid result, not a failure.

`tests/test_daily_skater_optimizer.py` exercises the public function and models
with fictional data. It includes the OPT-001 hand-scored examples, eight competing
skaters with seven multi-position players, capacity congestion, locks, Decimal
precision, zero/negative values, deterministic ties and explicit refusal cases.

The independent oracle enumerates every occupant combination of up to four physical
slots for six/seven-player seeded cases. It rejects duplicate/ineligible occupants
and uses exact Fraction arithmetic to compare totals. It shares no production
DP, scoring, validation or eligibility helpers. One hundred seeded cases compare
the complete optimum and declared tie policy, then repeat with reversed inputs.

This is a single daily skater problem. Required-fill rules, goalie/reserve handling,
weekly or cross-day constraints, participation, scoring/projection generation,
matchup adjustments, live data and UI integration are not implemented. The next
milestone should qualify the scoring/projection and effective-rule input contract
and define an out-of-sample evaluation before claiming useful predictions or
connecting the solver to real data.

## Executed verification

October 24, 2026, Windows, Python 3.12.15, isolated worktree based on `f31d8a5`.
Commands below ran from that worktree. The separate checkout's diagnostic changes
were not copied into this implementation or included in these test counts.

| Exact command | Observed result |
| --- | --- |
| `.\.venv\Scripts\python.exe -m pytest tests/test_daily_skater_optimizer.py -q` | 45 passed; includes 100 seeded exhaustive-oracle comparisons and three hand cases |
| `.\.venv\Scripts\python.exe -m pytest` | 892 passed |
| `.\.venv\Scripts\ruff.exe check src tests scripts/pr_status.py` | All checks passed |
| `.\.venv\Scripts\ruff.exe format --check src tests scripts/pr_status.py` | 84 files already formatted |
| `.\.venv\Scripts\mypy.exe` | No issues in 83 source files |

The full offline suite ran with normal host permissions for its existing local
async sockets and temporary folders; the repository's live-network guards stayed
enabled. No private launcher, authentication or live provider request ran.


## OPT-002A: daily Head-to-Head Points league regressions

The representative synthetic league has **C=2, LW=2, RW=2, D=4**, with no
UTIL/F/W slots or eligibility. Fourteen fictional available skaters supply ten
starters and four bench alternatives, including C/LW, C/LW/RW and LW/RW forwards.
All points are fabricated caller inputs; no Yahoo scoring or projection logic is
implemented. Goalies, IR and IR+ remain outside this skater problem. Fourteen
skaters is a synthetic test choice, not an inferred count of available real skaters.

Regressions compare the complete assignment and tie policy against an independent
exhaustive oracle using Fraction arithmetic. It enumerates occupant subsets for
each position, omitting permutations of indistinguishable physical slots, then
rejects players assigned twice. It uses no production helpers, DP or score pruning.
The original physical-slot oracle and its 100 seeded cases remain in place.

The supplied baseline totals 41.25. The unlocked optimum is 44.50; fixing a forward
to LW (different from its current RW assignment) and a lower-value defender to D
yields 43.25. Both cases require moving a flexible C/LW skater to LW to admit a
stronger benched C. Reversed-input results match completely. A separate all-tied
10-starter scenario preserves the supplied optimal baseline, including flexible
positions and a lexically later starter over an equally valued bench alternative.
The total-work safeguard has exact accepted/rejected boundary tests and rejects
the dense 78,125-state problem described above without starting the DP.

This covers one daily assignment at a time. Repeating it for seven dates is only
a performance exercise; it does not impose weekly lineup locks or cross-day rules.
**OPT-003 remains the next contract-qualification step:** establish scoring
semantics, projection inputs and effective daily lock rules before any real-data
integration or decision-quality claim. Goalie/reserve rules are unresolved.
No Yahoo reads, OAuth, private session, provider request, UI, database or dependency
changes are part of OPT-002A.

OPT-002A local verification on October 24, 2026, Windows Python 3.12.15:

| Check | Result |
| --- | --- |
| Optimizer pytest, bytecode/cache disabled | 51 passed in 1.56s |
| Complete offline pytest, bytecode/cache disabled | 898 passed in 15.93s |
| Ruff lint | All checks passed |
| Ruff formatting | 84 files already formatted |
| Strict mypy, cache disabled | No issues in 83 source files |

The repository's live HTTP/DNS/socket guards remained enabled throughout tests.
Hosted review/CI evidence is recorded on the PR at its exact head, separately
from these local results. No merge or auto-merge is authorized by this slice.


Performance used five samples of seven sequential calls, with the same fabricated
inputs and interpreter for `ee61ded` and OPT-002A. Medians (seconds):

| Synthetic problem | Prior implementation | With preflight limit |
| --- | --- | --- |
| 14 skaters, C2/LW2/RW2/D4, baseline supplied | 0.00696 | 0.00711 |
| Same problem with two fixed starters | 0.00388 | 0.00399 |
| 30 skaters, 16 slots, all seven positions explicitly eligible | 3.90115 | 3.89236 |

The large stress case uses C2/LW2/RW2/D4/F2/W2/UTIL2. It is retained only to
check supported generic-solver performance; it does not describe this league.
These local measurements support negligible preflight overhead, not a portable
latency guarantee. The actual league fixture stays far below one second for
seven independent solves. No timing threshold is imposed on hosted CI.
