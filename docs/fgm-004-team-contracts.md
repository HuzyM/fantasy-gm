# FGM-004: verified team identities and remaining contracts

**Historical investigation:** The earlier blockers and proposed next steps below
are superseded for the supported application workflow. The human operator has
confirmed league/team selection, scoring, roster and position displays work and
match Yahoo. See the [current acceptance boundary](fgm-004-private-cli.md#acceptance-and-remaining-limitations).
This does not certify every scoring rule, completeness or lineup legality.

The subsequently implemented [private application](fgm-004-private-cli.md)
integrates these identities with reported settings/roster views. That guide
describes current behavior; earlier conservative exclusions below are historical
where superseded by documented competition flags, slot labels and explicit
unverified roster-context handling. The detailed earlier findings remain historical.

## Implemented slice

The developer reports a private human-operated session confirming authentication,
NHL league discovery, basic settings identity, user-owned team membership, league
team structure/completeness, and the human team-list comparison. Scoring and
roster checks remain UNVERIFIED. These are reported live observations of the
existing verifier; the new provider methods were validated offline only.

`domain.team.Team` is an immutable, strict, provider-independent identity with
`provider`, `provider_league_id`, `provider_team_id`, and `name`. Provider IDs are
opaque to the domain. No manager profiles, ownership flags, XML, roster, scoring,
credentials, or token lifecycle fields enter this model.

The caller uses a private human process, a caller-owned clean `httpx.Client`, and
the existing in-memory access token. Select the league from authenticated NHL
discovery. The new methods on `YahooFantasyClient` are:

| Operation | Requests | Result |
|---|---|---|
| `list_league_teams(token, league_key)` | One `league/{league_key}/teams` GET | All returned normalized league team identities. |
| `list_my_league_teams(token, league_key)` | User-scoped season teams GET, then one league teams GET when matching ownership exists | Every owned team in the selected league, cross-checked by identity and name. |

The owned-team operation derives the season game key from the selected league
key. It parses exactly one logged-in user and the requested game, validates every
returned team identity before filtering other leagues, and verifies that each
selected owned team agrees with the league response. It returns a list, never
arbitrarily selecting the first team. An empty owned collection, or no owned team
in the selected league, returns `[]` after one GET. The other leagues are not
fetched. No settings or roster requests are made by these operations.

Missing/blank identity fields, duplicate keys/consumed fields, mismatched team
IDs, wrong games/leagues/namespaces, inconsistent counts, and conflicting identity
snapshots reject the entire response. A rename between the two reads causes a
sanitized inconsistency error; it is not silently reconciled or retried. Different
teams may legitimately have the same name or the same numeric ID in different
leagues; full opaque keys determine identity. Collection counts and optional
`num_teams` metadata are checked when present. Their absence does not prove total
completeness. A human completeness confirmation is still separate.

The verifier uses these same parsers and membership validation. Existing XML
helpers were moved into the provider for reuse, without changing scoring,
roster, OAuth, or session semantics. There is no provider framework or separate
team HTTP stack. The two methods are standalone alternatives; calling both makes
two separate league-list requests because the provider deliberately has no cache.

All GETs reuse the fixed-path/fixed-origin guard, Bearer validation, bounded
identity XML streaming, compression rejection, DTD/entity rejection, strict XML
namespaces, ten-second timeout, no redirects, and no retries. Library logging is
disabled during each GET and restored in `finally`, matching the private CLI's
existing pattern; this prevents HTTP URL logs from exposing league/team keys.
Responses, tokens, and normalized results are not retained on the provider.
This synchronous human-only integration is not a concurrent service. Callers must
also disable HTTP hooks, recording, caching, and terminal observation; the
provider cannot undo external recording.

## Scoring classification evidence

[Yahoo's API reference](https://sports.yahoo.com/developer/docs/) documents the
separate league/team/user resources and identifies divisions as league settings.
[YFPY's published Settings model](https://yfpy.uberfastman.com/models/#yfpy.models.Settings)
and the [yfantasy XML types](https://pkg.go.dev/github.com/famendola1/yfantasy/schema#Settings)
provide explicit administrative field names. These reference implementations are
evidence for their published shapes, not proof of all current NHL responses.

The scalar administrative exclusions now additionally recognize:

- `can_trade_draft_picks`, `max_weekly_adds`, `uses_roster_import`, and
  `roster_import_deadline` for transactions and roster-import administration.
- `has_playoff_consolation_games`, `num_playoff_consolation_teams`,
  `num_playoff_teams`, `playoff_start_week`, `uses_lock_eliminated_teams`,
  `uses_playoff`, and `uses_playoff_reseeding` for bracket/team administration.

Only exact names in the expected namespace, with scalar contents and no
attributes, receive this exclusion. It does not certify their values or implement
bracket, schedule, transaction, or season aggregation rules. Duplicate scalar
fields still fail validation. The known `divisions/division` metadata container
is accepted only with validated collection counts, unique numeric `division_id`
fields and nonblank `name` fields; unfamiliar children/attributes are not ignored.
No division domain model or standings logic is added.

`uses_median_score`, `has_multiweek_championship`, unknown premium feature
containers, unfamiliar scoring-critical fields, modifiers and bonuses remain
unsupported. No weights, stat joins, Decimal parsing, position mappings, human
confirmations, or SESSION aggregation rules have been relaxed. The sanitized
live reason does not identify the rejected field, so this patch cannot establish
that the live blocker is resolved. Existing private name-only inspection remains
the way for the human to investigate it without sharing XML or private names.

## Independent roster envelope: implemented offline

The separately approved slice now makes the existing single roster GET after
validated ownership, league membership, the human team-list check and explicit
owned-team selection. It validates the envelope and normalizes reported player
fields before slot validation. Later checks reuse the same in-memory response.

`YahooFantasyClient.get_owned_team_roster(token, league_key=..., team_key=...)`
validates key syntax, cross-checks authenticated ownership, requires the explicit
key in the owned list, then makes one roster GET. It makes no settings request.
The standalone operation uses two ownership/membership GETs and one roster GET;
the verifier still uses at most the original five Fantasy GETs. No retry or
response retention is added. A pure `parse_roster` accepts a supplied Team for
offline parsing; pure parsing alone cannot establish ownership.

[Yahoo's Roster Resource documentation](https://sports.yahoo.com/developer/docs/)
establishes the GET subresource and date-based hockey organization. This slice
keeps only the existing unparameterized roster path. Explicit date/week parameters
remain unsupported by the transport allowlist. Yahoo's server selects its default
roster; the code does not manufacture an effective date. Public shapes are
candidate contracts, not proof of successful live NHL roster verification.

The earlier proposal deferred domain normalization. The subsequent explicit
approval authorizes these minimal frozen, strict provider-independent models:

| Model | Reported facts |
|---|---|
| `RosterCoverage` | Opaque kind, optional explicit ISO date and optional opaque week. |
| `RosterEntry` | Opaque player ID/name, optional eligible-position tuple, selected code/coverage, and supplied flex flag. |
| `Roster` | Validated team, entries, coverage, optional returned count, and `requested_date=None` for the unparameterized request. |

Yahoo XML remains inside the provider. Player keys match the selected season
game and their player IDs, with no duplicates. Names require `name/full`.
Supported optional fields follow the published
[SelectedPosition/Player models](https://yfpy.uberfastman.com/models/) and existing
candidate XML structures. Missing optional containers remain `None`; explicit
empty eligibility remains `()`. Position codes stay opaque, without trimming,
aliases, bench/reserve inference or mapping. A supplied 0/1 flex flag becomes an
optional boolean; absence never becomes false. Preserving these values does not
establish eligibility or lineup legality.

Supplied dates must be canonical ISO dates. Missing dates stay `None` even with
coverage kind date. Unknown coverage kinds/weeks stay opaque. Neither today's
date nor a missing selected-position date is inferred. A supplied collection
count is validated against returned children; it proves no reserve inclusion,
pagination or total completeness. Missing counts remain `None`.

Known roster, eligibility and assignment containers retain strict child,
attribute and namespace validation. Unknown critical structures raise a fixed,
sanitized unsupported error. Invalid required identities/counts/date syntax fail.
Unconsumed ordinary player metadata is discarded, never returned as raw XML.

| Check | Evidence established |
|---|---|
| `ROSTER_STRUCTURE` | GET/envelope succeeded, team matches, player collection/count has supported structure. |
| `ROSTER_NORMALIZATION` | Required player IDs/names and supported supplied position/coverage fields normalize. Optional absence is not existence proof. |
| `PLAYER_POSITIONS` | Existing stricter fields/assignments, including membership in established slot codes, pass. Missing positions remain UNVERIFIED. |
| `ROSTER_SLOT_CAPACITY` | Established slots and assignments show capacities are not exceeded. |
| `ROSTER_COVERAGE` | Existing explicit matching-date requirements pass. Missing/unknown coverage cannot pass. |
| `HUMAN_ROSTER_COMPLETE` | Explicit private comparison establishes returned membership, including bench/reserves. |

Successful retrieval/normalization never certifies legality, date agreement,
capacity or completeness. Unsupported slots may leave independent checks PASS and
dependent checks/SESSION UNVERIFIED. A local scoring validation FAIL still fails
that check and SESSION but permits independent roster evidence. Explicit human
REJECT/interruption and identity/authentication/transport failures still stop
dependent work. Invalid player fields/date syntax now fail ROSTER_NORMALIZATION
before any position/capacity assertion. Scoring validation rules are unchanged.

Synthetic tests cover valid/wrong-team/unowned requests, missing/duplicate player
IDs, missing/empty collections, namespace/count errors, optional positions,
unknown coverage, unsupported shapes, transport bounds, and no file/log/MCP
disclosure. No live verification occurred. Future private human verification
requires separate approval and may share only the final fixed summary.

## Incomplete roster report: established paths and correction

The current verifier catches the scoring branch stop before user/team checks.
After successful ownership/membership and the human team-list comparison, it
requires an explicit owned-team menu selection. Only a valid selection reaches
the roster GET, envelope check and normalization. Slot validation runs afterward.
There is no scoring/modifier/slot-capacity gate on basic roster retrieval.
The standalone owned-roster provider method already has the same independence.

The reported combination (team/human checks PASS, roster envelope/normalization
UNVERIFIED, SESSION UNVERIFIED and first scoring stop reason) was reproduced with
three wholly invented cases:

| Synthetic case | Fantasy GETs | Explanation |
|---|---|---|
| Team menu returns no valid choice | 4 | Selection stops before any roster request. |
| Team menu explicitly CANCELs | 4 | Selection stops before any roster request. |
| Valid owned selection, unsupported roster envelope | 5 | One roster response is received but cannot establish a supported envelope; normalization is unattempted. |

These cases produce the same check statuses and the same old first-only stop
block. Thus the user's block cannot establish whether their roster GET occurred,
which team-selection outcome happened, or what Yahoo returned. Do not infer
cancellation, malformed Yahoo data or a particular unsupported field. Identity,
transport, or required-field failures would instead produce FAIL in the current
flow. Unsupported normalization after a supported envelope would leave
ROSTER_STRUCTURE PASS, unlike the reported pattern.

The concrete defect was diagnostic masking: the first scoring stop hid later
independent stops. Report now retains the first and most recent enum-only stop
and appends LAST_STOP_CHECK/LAST_STOP_REASON/LAST_DOWNSTREAM_CHECKS_SKIPPED when
there is a distinct later cause. No parser acceptance, request dependencies,
selection requirements, status aggregation or scoring metadata exceptions changed.
The original skip flag describes only the first branch; it never proved all
later work was skipped. The additional fields disambiguate these synthetic paths.

A supported selected roster still establishes envelope/normalization PASS when
scoring and slots are UNVERIFIED; slot capacity, human completeness and SESSION
stay UNVERIFIED. Tests also confirm invalid selections/unowned teams cannot
request a roster, identity mismatches and missing player IDs FAIL, and unknown
roster structures remain UNVERIFIED. No information is promoted to PASS merely
to obtain a complete session.

## Evidence still needed for the scoring blocker

No speculative metadata exceptions were added. To justify any future scoring
classification change, the human must privately establish:

1. The exact expanded element name and namespace shown in the existing private
   unsupported-name panel, and that it is a direct child of settings.
2. Whether it is one scalar or a container/repeated structure, and whether it
   carries attributes or child elements. If it matches an existing administrative
   name, establish which namespace/attribute/nesting condition prevented exemption.
3. An independent public contract/reference describing that same name and shape
   as unrelated administrative metadata. A similar spelling is insufficient.
4. If it can affect points, bonuses, thresholds or aggregation, the documented
   semantics needed to interpret it correctly; it must remain unsupported until
   that evidence exists. Known modifier checks and exact stat-ID joins remain strict.

Keep all live-derived names, shapes and values inside the private human session;
do not send them to AI, write notes/dumps, capture XML or enable response logging.
The subsequently approved minimal structural view now supplies bounded
rejected-node shapes as described in the [current inspection guide](nhl-contract-verification.md#settings-classification-evidence-and-private-inspection).
Parser acceptance and semantic requirements remain unchanged. Public documentation URLs and the fixed final
status/diagnostic block are the shareable evidence. A future private roster run is
justified to distinguish selection from unsupported envelope behavior using the
new LAST_* fields, but it requires separate live approval. It cannot by itself
resolve unknown scoring semantics.

## Remaining milestone criteria

The subsequent [scoring and roster compatibility audit](fgm-004-contract-audit.md)
records the exact latest rejection boundaries, public evidence limits, missing
private structural evidence and shortest private CLI completion path. It makes
no new parser exceptions or diagnostic changes.

- Establish the unsupported live scoring field privately; accept only structures
  supported by evidence. Confirm NHL points semantics, complete weights, stat
  applicability and display-only behavior before scoring normalization.
- Establish slot metadata, player identity/eligibility/assignment structure,
  current roster coverage/date behavior, capacity, and human completeness.
- Implement remaining settings/scoring contracts and additional roster semantics
  only after that evidence, preserving exact values and explicit uncertainty.
- Complete the private read-only workflow and its offline regressions/review;
  do not treat this team slice as complete FGM-004.

No live data is used in automated fixtures. No token or Fantasy Information is
persisted, cached, indexed, sent to third parties, or exposed through MCP.
`YAHOO_AI_TOOLS_ENABLED=false` remains the operating requirement.
