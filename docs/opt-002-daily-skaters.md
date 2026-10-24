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
