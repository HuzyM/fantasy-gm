# v0.2A: upcoming observed team games and identity feasibility

Audited 2026-10-20 against main `d6ce7f30be400c4f1d24bfb089001341ff5b5056`
(completed v0.1 integration and CI gates). No account/private data was inspected;
no Yahoo or PuckAPI data requests were made. Research used public documentation.

## Existing architecture and the missing feature

| Layer | Existing reusable behavior |
| --- | --- |
| `domain/roster.py`, Yahoo `fantasy.py` | Full Yahoo player key, name, reported positions/slot and optional normalized professional-team abbreviation. Missing, malformed, orphaned or conflicting affiliations remain explicit. No NHL player-ID mapping. |
| `providers/puckapi.py`, `domain/schedule.py` | Bounded manually requested public schedule observations; UTC instants, normalized type/state, team catalogue, observation timestamp and coverage uncertainty. Missing or timezone-free starts remain unplaced. |
| `ScheduleService` | Memory-only bounded cache of public snapshots, no roster input, no background refresh or new provider needed. |
| `sports/nhl/schedule.py` | Pure date/timezone filtering, duplicate collapse, game-state counts, uncertain/unplaced observations and qualified coverage semantics. Empty observations do not imply zero games. |
| `sports/nhl/roster_schedule.py` | One pure affiliation join per roster/window. Distinct missing/unverified/unsupported affiliation, cohort and season statuses. A successful join means a supported team association only. |
| `web/data.py` | Whitelisted local display contract, the existing pure analyses and join statuses; no browser endpoint invokes a provider. |
| React | Roster and inspector already contain next-game slots; Profile and Planner already display team fixtures. The provider roster adapter previously hardcoded next game to Unknown; Profile's upcoming list also included past/completed observations. |

These five facts remain separate:

1. **Yahoo player identity:** a game-scoped Yahoo key; never an NHL player ID.
2. **Reported team affiliation:** Yahoo metadata associated with that identity;
   even a syntactically supported join may be stale after a trade.
3. **Verified NHL player identity:** unavailable for Yahoo roster entries until an
   explicit trustworthy crosswalk is established. No photographs or statistics
   are attached using names, positions or team affiliations.
4. **Observed team game:** a normalized fixture associated with a supported club.
   Coverage, current state and freshness remain limited to the loaded snapshot.
5. **Confirmed player appearance:** unsupported. A team fixture proves no player
   appearance, injury status, lineup availability or goalie start.

## Data flow and first-slice scope

The existing human-operated launcher optionally loads Yahoo roster data and one
explicitly approved public schedule snapshot. This slice adds no provider call,
endpoint, dependency, cache, persistence or integration.

`ScheduleSnapshot -> analyze_schedule -> schedule_view -> parseView ->
upcomingObservedGames -> joinedTeamGames -> roster/inspector/profile`

`roster_schedule_rows` continues to establish the affiliation join status. The
local display contract adds `upcomingEligible` to each dated fixture: only a
normal, regular-season, SCHEDULED observation with a known UTC instant qualifies.
Unknown type/state, postponements, reschedules, cancellations and missing times
cannot qualify. Older contracts without the flag default to ineligible.

React retains the original UTC instant alongside the Toronto display time. The
pure selector filters the loaded local-date window and starts at or after the
supplied current instant, collapses duplicate IDs and orders by UTC then ID.
The roster adapter calculates the ordered observations once per render; each
player uses only their supported affiliation join. Equal local times around DST
are ordered by their UTC instants. No date is inferred from an unplaced start.

**Next observed** means the earliest eligible observation in the loaded window.
It is useful even under partial coverage, but does not prove that an earlier
unobserved game does not exist. With no qualifying observation, the result is
Unknown; with no loaded schedule, it is Unavailable. Neither means an off-day.

My Roster and its inspector show opponent, home/away, local date/time and explicit
observation limits. Profile reuses the same selection for its upcoming list.
Planner keeps its daily observation history, including completed/uncertain games,
and now displays their states. Window, timezone and source observation timestamp
are visible. Existing synthetic demo presentation/baselines are preserved.

The existing local-memory reread every 15 seconds/on focus recomputes selection
against the browser clock; no provider is refreshed. A suspended browser or
incorrect local clock can delay that change. Loaded observations are not live
state guarantees. Existing private session expiry/disconnect behavior is unchanged.

### Acceptance criteria

- Select the earliest eligible future observation, independent of input order;
  support home/away, exact cutoff, duplicate IDs and multiple roster players on a club.
- Preserve Unknown/Unavailable for absent observations and every unsupported join.
- Keep partial coverage, stale affiliation and unconfirmed appearance visible.
- Sort repeated DST hours by UTC; use the normalized Toronto day at UTC midnight.
- Exclude completed/in-progress/unknown/cancelled/postponed/rescheduled, abnormal,
  unknown-type and unplaced observations from upcoming selections.
- Keep identity, photos, injuries and performance unsupported where they were
  unsupported; never use a name/team/position match as identity evidence.
- Preserve private-memory-only display, default-deny AI/MCP and human-only
  provider authorization. Browsing, navigation and rereads spend no provider credits.
- Pass repository CI, responsive/accessibility regressions and existing screenshot
  comparisons. Examine new synthetic observation captures; do not update baselines
  unless an intentional visual difference has been reviewed.

## Yahoo-to-NHL identity feasibility

**Finding: no documented verified bridge found in the inspected sources.** This
does not prove that no bridge exists; it establishes why this slice leaves the
identity unverified and implements no resolver.

- [Yahoo's official reference](https://sports.yahoo.com/developer/docs/) defines
  `{game_key}.p.{player_id}` as a fantasy-game player identity. The current parser
  checks that the returned numeric Yahoo ID agrees with the key suffix; this is
  consistency inside Yahoo's namespace, not an NHL mapping.
- The author-maintained [YFPY Player model](https://yfpy.uberfastman.com/models/#yfpy.models.Player)
  documents Yahoo editorial player/team keys. An editorial team key identifies a
  club in Yahoo's namespace, not an NHL player. It cannot establish a crosswalk.
- PuckAPI's published [search fields](https://puckapi.com/docs/search-players) and
  [player profile fields](https://puckapi.com/docs/get-player-stats) include player
  ID, names, team/position and bio attributes, but expose no Yahoo identifier in
  the documented response. Searching these fields supplies candidates only.
- [SportsDataIO's NHL dictionary](https://sportsdata.io/developers/data-dictionary/nhl)
  describes `YahooPlayerID` for Yahoo **Daily Fantasy Sports**. Equivalence to
  seasonal Yahoo Fantasy IDs is unverified, and SportsDataIO's own PlayerID must
  not be confused with the official NHL ID.
- [Sportradar's ID-handling documentation](https://developer.sportradar.com/ice-hockey/docs/nhl-ig-id-handling)
  describes explicit NHL reference IDs for its own identities. The inspected
  documentation does not supply the missing seasonal Yahoo connection.

Names, positions and teams are insufficient: duplicate names, spelling variants,
transfers, historical clubs, stale or missing affiliations and conflicting
metadata can all yield an attractive but unsupported match. The current Yahoo
roster domain has no birth date or explicit NHL player ID; obtaining biographical
candidates alone still would not establish a provider-backed crosswalk. Missing,
duplicate or contradictory mappings must retain an unresolved state.

## Validation and next investigation

Local validation: 808 offline Python tests; Ruff lint/format; strict mypy over
78 source files; 91 frontend tests; TypeScript and production build. Synthetic
regressions cover selection, uncertain/missing schedules, join statuses, DST,
UTC/local date boundaries, game states, unavailable data and UI semantics.
Browser and hosted CI evidence are reported on the implementation PR.

The smallest v0.2B identity investigation is one public provider-owned schema or
example explicitly connecting a **seasonal Yahoo Fantasy player key/ID** and an
**official NHL.com player ID**, with namespace definitions, coverage and
duplicate/missing/conflict behavior. The published PuckAPI schema currently does
not provide that evidence. A documentation clarification can be prepared for
human follow-up; no provider contact is sent automatically. Do not add a resolver,
player-statistics work or another provider until the identity contract is supported.

Real-provider acceptance remains a separate human-operated activity. This work
uses synthetic tests only and cannot certify real schedule completeness,
current player affiliation or player participation. Do not merge without owner approval.
