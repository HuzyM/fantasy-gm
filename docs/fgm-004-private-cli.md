# FGM-004 private league and roster application

## Run outside AI-observed terminals

Use a human-operated, unrecorded terminal after separate live approval. Do not
run this from Codex, an AI tool, a transcript, a remote screen viewer or a shared
terminal. Set the already registered Public Client ID locally and keep
`YAHOO_AI_TOOLS_ENABLED=false`; never put values on the command line or in files.

```text
uv run --locked --offline python -B -m fantasy_gm.league --interactive
```

With this checkout's established Windows runtime:

```powershell
.\.tools\bin\uv.exe --cache-dir .tools/verifier-uv-cache run --locked --offline --python .venv/Scripts/python.exe python -B -m fantasy_gm.league --interactive
```

`--help` performs no authorization. Existing `fantasy_gm.auth` discovery,
`--diagnose-state`, `--diagnose-api`, and `fantasy_gm.verify_nhl` modes remain.
This implementation task made no live requests or authentication attempts.

## Workflow and limitations

The CLI requires all three streams to be terminals and alternate-screen setup
to succeed before authorization. The operator attests to an unrecorded private
session, authorizes once using the existing Public Client PKCE/state flow, and
selects a discovered NHL league. The provider reads user-owned teams and league
teams once, validates membership, then presents an explicit owned-team menu.

Only after selection does it fetch settings, show supported configuration or
fixed unavailable labels, and fetch the selected roster once. The selection
callback reuses the two ownership/membership reads; it does not call them again.
At most five Fantasy GETs occur: discovery, owned teams, league teams, settings,
and one roster. No owned team means no settings or roster request. There is no
refresh, retry, arbitrary URL input, transaction or lineup write.

Supported configuration preserves the provider's untranslated scoring format,
exact Decimal modifiers, enable/display-only/visibility flags, stat identifiers,
position scopes and roster slot codes/capacities. Missing flags stay unknown.
An explicit zero modifier stays zero; a missing weight never becomes zero.
Unweighted statistics not explicitly disabled or display-only make the scoring
observations incomplete. Other known values still appear. Visibility exclusion
is not treated as display-only.
No scoring, standings, matchup aggregation or lineup calculations are performed.

The application reads consumed fields rather than certifying every optional XML
field. Unknown settings/custom/premium structures keep `ScoringRules.incomplete`
true: supported categories, literal modifiers and flags still appear under an
explicit partial, not-calculation-ready warning. A malformed optional weight,
flag or scope remains unknown without erasing independent stat facts. Broken
stat identities, duplicate IDs, invalid joins or collection hierarchy/counts
make that scoring table unavailable. No unknown scoring rule is deemed harmless.
`roster_slots_incomplete` similarly distinguishes observed slot codes/capacities
from a complete supported configuration. Invalid presentation labels do not
erase those facts.

Roster parsing validates selected team identity, player identities/names and
collection hierarchy/counts before producing a view. Unknown outer metadata,
unsupported coverage or invalid optional positions mark `context_unverified`;
only the affected optional values are unavailable. Independently validated
players and supported position fields remain visible. Required identity,
authentication, transport and XML security failures still stop dependent work.
No response/error text is printed on failure. The existing strict contract
verifier continues rejecting unsupported structures; it does not certify these
partial application observations.

The roster view displays reported player identities/names, eligible and selected
position codes separately, selected coverage/flex, roster coverage and returned
count. Absent metadata stays unknown; an explicit empty eligibility tuple stays
empty. Dates are never filled from the clock, and no reserve/bench mapping is
invented. Returned count is not completeness proof. Every roster view explicitly
leaves completeness, lineup legality and slot capacity UNVERIFIED.

Use NEXT to read additional pages and acknowledge views, or CANCEL/Ctrl+C to
exit. Private data is cleared on exit and never written to disk or ordinary logs.
Recording cannot be detected or undone, so the human attestation remains
necessary. Display/input/cleanup failures produce a fixed failure outcome.
The only ordinary final output is `PRIVATE_SESSION FINISHED`, `PARTIAL`,
`CANCELLED` or `FAILED`. FINISHED means the requested supported views were shown,
not that Yahoo semantics or roster completeness have been live-verified.

## Evidence-supported corrections

[Yahoo's reference](https://sports.yahoo.com/developer/docs/) separates league
settings, user-owned teams and roster resources and documents date-organized NHL
rosters. No new endpoint is required.

The [published YFPY Settings/Roster models](https://yfpy.uberfastman.com/models/)
describe median-matchup and multiweek-championship flags as competition options.
These are now preserved explicitly rather than blocking stat/modifier parsing;
neither becomes a stat multiplier. Unknown premium features remain uninterpreted
and prevent complete scoring support; they do not erase independent fields.
The same source recognizes the numeric `is_prescoring` flag but leaves its exact
meaning unresolved. Basic normalization now accepts its strict scalar 0/1 syntax
and records `Roster.context_unverified=True` whenever supplied, including zero.
It does not infer a scoring-effective period from that value. The verifier keeps
coverage and human position/completeness certification UNVERIFIED in this case.
The ordinary editability flag is validated but never enables writes.

The [published yfantasy roster-position XML type](https://pkg.go.dev/github.com/famendola1/yfantasy/schema#RosterPosition)
includes presentation labels `abbreviation` and `display_name`. These unique
scalar labels no longer block slot code/capacity normalization. They are not
aliases, scoring fields or position mappings. Unknown slot rules remain
uninterpreted; known slot facts appear as partial observations.

Shared pure parsing now lives in `providers.yahoo.settings`, reused by the
verifier and application rather than implementing a second scoring parser.
`domain.settings` holds immutable provider-independent reported contracts. Yahoo
XML, keys, transport and normalization remain at the provider boundary.

## Acceptance and remaining limitations

The human operator reports successful live use of the private CLI against their
Yahoo Fantasy Hockey league: league selection, owned-team selection, scoring
settings, player roster and roster positions worked, and the displayed information
matched Yahoo. This completes acceptance of the supported FGM-004 display workflow.
No account identifiers, private values, responses or credentials were supplied
or recorded. Agents did not perform live requests or authentication.

Offline tests use wholly synthetic fixtures and validate parsing, ownership
boundaries, partial views, transport/XML protections and privacy behavior. They
are separate from the human-reported acceptance. The strict contract verifier
may still leave additional semantic checks unverified; its complete PASS is not
a prerequisite for showing supported observations.

Acceptance does not establish all Yahoo scoring variants, complete points
calculation semantics, effective NHL roster coverage, reserve inclusion, roster
completeness, slot capacity/lineup legality or transaction behavior. Unknown rules
and optional fields keep their existing partial/unknown markers. No points,
matchup, optimization or transaction engine is implemented. Yahoo-backed MCP
remains disabled and unwired pending written provider clarification.

No further live session is required to finalize this milestone. Any later live
investigation still requires separate approval and an unrecorded human-only
terminal. Do not share screenshots, XML, values, identifiers or live-derived
structural names with AI. The operating limit remains one authorization and at
most five Fantasy GETs per approved private CLI session, without retry/refresh.
