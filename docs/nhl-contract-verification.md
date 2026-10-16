# Private NHL contract verification

The supported private CLI has passed human-reported live acceptance for displayed
league/team, scoring, roster and position information. This separate strict
contract-investigation utility remains available for approved future work; it
is not a release gate requiring another live session. See the
[application acceptance boundary](fgm-004-private-cli.md#acceptance-and-remaining-limitations).

This is an offline-tested verifier for FGM-004, not the league/roster feature.
No live verification was performed during implementation. Public Yahoo GET
examples establish candidate XML structures; they do not establish the personal
NHL league's scoring semantics. Source: [Yahoo Fantasy API documentation](https://sports.yahoo.com/developer/docs/).

## Approval and privacy boundary

Do not run the interactive command until the developer separately approves a
live session. A human must use a standalone, private terminal, outside Codex,
ChatGPT, MCP clients, IDE agents, remote terminal sessions, recordings, screen
sharing, PowerShell transcripts, and HTTP/debug logging. Never ask an AI to run,
observe, troubleshoot, or capture that terminal or the authenticated browser.

The command requires terminal input, output, and error streams. On Windows it
requires console virtual-terminal support and uses an alternate screen buffer;
the buffer is cleared on normal exit, cancellation, and handled exceptions.
Library logging is disabled for the process's verification attempt. Hidden input
fails closed if echo protection is unavailable. Yahoo fields are escaped before
private display; the OAuth authorization URL is shown only in the private buffer.

These measures cannot detect or prevent an external recorder, debugger, terminal
integration, crash dump, operating-system paging, or a forced process kill.
Python does not guarantee cryptographic erasure of immutable strings. The utility
does not intentionally save, cache, index, log, or export tokens or Fantasy
Information. Do not start if the terminal cannot provide the required privacy.

After the private buffer closes, the only output is a fixed list of
`CHECK_IDENTIFIER PASS`, `CHECK_IDENTIFIER FAIL`, or
`CHECK_IDENTIFIER UNVERIFIED` lines. Incomplete/stopped attempts additionally
include the allowlisted diagnostic lines documented below. No
diagnostic/export files are created.
Only this final block may be shared. Never share screenshots, private panels,
the authorization URL, code/state, XML, names, identifiers, or scoring values.

## Future human-operated steps — approval required first

1. Obtain separate approval for live authentication and the five read-only
   Fantasy API requests below. This guide is not authorization to execute them.
2. Open standalone Windows Terminal/PowerShell. Disable transcription, recording,
   screen sharing, and agent integrations. Use a private browser for Yahoo.
3. Change to the repository and confirm the branch is
   `feature/fgm-004-league-roster-foundation`. Do not redirect or pipe the verifier.
4. Keep `YAHOO_AI_TOOLS_ENABLED=false`. Supply the existing Public Client ID only
   in this human process's environment, as in the original authorization guide.
   Do not create a `.env`, put credentials on a command line, or share environment
   output. The utility does not read a `.env` or accept resource keys as arguments.
5. Run the already-installed locked environment directly:

   ```powershell
   Set-Location -LiteralPath 'D:\Codex\Fantasy GM\fantasy-gm'
   $env:YAHOO_AI_TOOLS_ENABLED = 'false'
   .\.venv\Scripts\python.exe -B -m fantasy_gm.verify_nhl --interactive
   ```

6. The privacy/approval screen must appear in an alternate buffer. If escape
   sequences appear literally or the terminal is being observed, press Ctrl+C
   before approval. Otherwise type `APPROVE PRIVATE READ-ONLY` only after checking
   the session is private. This authorizes one attempt; the utility opens no
   browser automatically.
7. Open the authorization URL yourself, complete the existing Public Client
   PKCE flow, and paste code and returned state into the separate hidden prompts.
   Close the callback tab and clear sensitive clipboard contents afterward.
8. Select the personal NHL league and owned team by local menu number. Inspect
   each private panel, typing `NEXT` for additional pages. Compare every requested
   item with Yahoo's website for the same league and roster date. Type `CONFIRM`
   only when the comparison is established; `REJECT` records failure and
   `UNKNOWN` records uncertainty. Other answers never count as confirmation.
9. On completion or cancellation, confirm the private buffer has disappeared.
   Share only the final identifier/status block, including any appended stop
   diagnostics. Exit code 0 requires every
   structural and human check to pass; exit code 1 means failure, cancellation,
   unsupported structure, or remaining uncertainty. An `UNVERIFIED` check does
   not mean a malformed response or permission to infer a missing value.
10. Stop. Do not retry, broaden requests, export data, or start implementation to
    work around a failure. Review the fixed statuses before approving next work.

`--help` is offline and reads no Yahoo configuration. No command-line approval
switch bypasses the interactive approval prompt. A true AI-tools flag prevents
authentication. The utility has no automatic refresh or retry.

## Requests and transport

After a single OAuth code exchange, the verifier uses these GET paths on the
fixed `https://fantasysports.yahooapis.com/fantasy/v2/` origin:

1. `users;use_login=1/games;game_keys=nhl/leagues`
2. `league/{selected_league_key}/settings`
3. `users;use_login=1/games;game_keys={selected_season_game_key}/teams`
4. `league/{selected_league_key}/teams`
5. `team/{selected_owned_team_key}/roster`

Selections come from validated responses, not free-form URLs. Only these path
shapes are accepted. The season-specific game key comes from the selected league
key; no current-season alias is used for later team requests. Essential identity,
authentication and transport failures, and explicit human REJECT, stop dependent
requests. Unsupported/malformed scoring stops its branch, preserving its actual
UNVERIFIED/FAIL status. UNKNOWN scoring never certifies skipped checks.
After ownership/membership and explicit selection, the single roster GET provides
independent envelope and normalization evidence before slot validation. Slot
checks gate only the stricter position/capacity/human workflow. The same settings
and roster responses are reused in memory. No automatic refetch or retry is added.
No statistic catalogue, player statistics, transaction, or write endpoint is used.

Transport reuses the discovery safeguards: 1 MiB maximum identity XML, raw bounded
streaming, compressed responses rejected before reading, no redirects, 10-second
timeouts, no inherited auth, no environment proxies/trust configuration, and no
automatic retries. OAuth retains its 64 KiB bound and state/PKCE/Bearer validation.
DTD/entities, invalid namespaces, duplicate consumed fields, malformed collection
counts, invalid resource identifiers, and mismatched resource membership fail.

## Meaning of the checks

Automated `PASS` establishes only the stated structural/numeric assertion. It
never establishes scoring semantics or complete reserve inclusion by itself.
All `HUMAN_*` checks require actual private comparison; tests simulate these
answers only against invented fixtures.

| Automated check | Assertion |
|---|---|
| `PRIVATE_TERMINAL` | All three streams are terminals; alternate-buffer setup succeeded. |
| `LIVE_APPROVAL` | Exact human attestation received; AI flag is false or absent/default false. |
| `AUTHORIZATION` | Existing single-use OAuth flow returned a validated Bearer token. |
| `LEAGUE_DISCOVERY` | NHL discovery parsed; selection candidates have unique validated keys. |
| `SETTINGS_STRUCTURE` | Selected league, settings container, and supplied team count are structurally valid. |
| `SCORING_STRUCTURE` | Categories/modifiers have supported candidate structures and unique, joining identifiers. Raw scoring codes are preserved, not translated. |
| `MODIFIER_VALUES` | Supplied weights are finite, bounded decimal strings parsed exactly, without rounding or float conversion. Missing is never zero. Exponent notation remains unsupported. |
| `STAT_APPLICABILITY` | Consumed metadata, optional flags, and repeated position applicability have supported syntax. Missing flags/scopes retain uncertainty for human review. |
| `ROSTER_SLOTS` | Unique opaque slot codes, nonnegative integer capacities, optional position types. |
| `OWNED_TEAM_MEMBERSHIP` | User-scoped team belongs to the selected season/league. No manager-name or ownership-flag inference. |
| `LEAGUE_TEAMS_STRUCTURE` | Team collection parsed; selected ownership keys are present. |
| `LEAGUE_TEAMS_COMPLETENESS` | Returned team cardinality matches supplied league `num_teams`; absent metadata stays unverified. |
| `ROSTER_STRUCTURE` | Selected team's roster/player collection parsed and supplied count matches its children. |
| `ROSTER_NORMALIZATION` | Required player IDs/names and supported supplied position/coverage fields normalize. Optional absence stays absent; legality and completeness are not established. |
| `PLAYER_POSITIONS` | Unique matching player identities, names, eligibility and assignment structures; assigned codes occur in configured slots. Empty rosters do not establish player-field contracts. |
| `ROSTER_SLOT_CAPACITY` | Returned assignments do not exceed configured capacities; empty slots are allowed. |
| `ROSTER_COVERAGE` | Explicit ISO dates and `date` coverage agree across roster and every selected position, with no supplied week. Missing or mixed coverage is never inferred. |
| `ROSTER_RETURNED_COUNT` | A returned count exists and matches parsed children. This does not prove total completeness. |
| `SESSION` | Every required automated and human check passed, with no handled failure. |

Required human comparisons are `HUMAN_POINTS_FORMAT`,
`HUMAN_SCORING_COMPLETE`, `HUMAN_POSITION_SCOPES`, `HUMAN_ROSTER_SLOTS`,
`HUMAN_LEAGUE_TEAMS_COMPLETE`, `HUMAN_PLAYER_POSITIONS`,
`HUMAN_ROSTER_COVERAGE`, and `HUMAN_ROSTER_COMPLETE`. The private prompts define
their comparison criteria. Missing date/coverage can be inspected, but cannot
receive a human coverage pass. The separate roster-membership comparison can
still be completed in that case. A rejection always stops verification.

Unknown scoring structures/bonus components are not silently normalized. The
scoring branch stops instead of guessing an unsupported representation. It displays
known metadata and exact weights for human inspection; it does not calculate
fantasy points or map Yahoo codes to provider-independent scoring semantics.
Unrecognized attributes/children on critical scoring structures leave scoring
unverified. Slot, roster, and assignment problems stop dependent roster checks. A pagination marker outside the supported
roster shape remains unverified; the utility does not invent another page request.
Collection-wide assertions pass only after the entire collection is validated.

## Sanitized stop diagnostics

Statuses preserve the actual result of each attempted check. After an
incomplete/stopped attempt, three additional lines identify the earliest branch
or session stop; this need not have ended the entire session. All field names and values come from fixed allowlists:

```text
STOP_CHECK SCORING_STRUCTURE
STOP_REASON UNSUPPORTED_STAT_STRUCTURE
DOWNSTREAM_CHECKS_SKIPPED YES
```

If a distinct later stop is recorded, three further fixed fields expose the most
recent stop. The report holds only the first and latest enum/bool tuples, not a
history or any provider payload. For example, entirely synthetic:

```text
STOP_CHECK SCORING_STRUCTURE
STOP_REASON UNSUPPORTED_SCORING_SETTING
DOWNSTREAM_CHECKS_SKIPPED YES
LAST_STOP_CHECK OWNED_TEAM_MEMBERSHIP
LAST_STOP_REASON SELECTION_NOT_COMPLETED
LAST_DOWNSTREAM_CHECKS_SKIPPED YES
```

All `LAST_*` values use the same existing check/reason enums and YES/NO allowlist.
They appear only when the later tuple differs. They may describe a later cleanup
error; this is not a complete stop history. The original first cause is preserved,
and individual statuses plus SESSION continue to show actual failures.

This is a synthetic example, not a diagnosis of a live response. `STOP_CHECK` is
an existing check identifier. `DOWNSTREAM_CHECKS_SKIPPED` is `YES` when the stop
skips later checks in that branch, or `NO` when the last scoring confirmation
is UNKNOWN and independent checks continue, for the final roster confirmation,
or for session completion/cleanup. It excludes the final `SESSION` status itself. A selection
stop is attributed to `LEAGUE_DISCOVERY` or `OWNED_TEAM_MEMBERSHIP`; that completed
check can still be `PASS` because its private selection was not completed.

| Stop reason | Fixed condition |
|---|---|
| `UNSUPPORTED_SCORING_SETTING` | An unrecognized direct settings element, unsupported metadata shape/namespace, or attribute on a known scoring scalar was found. Only predefined administrative scalar/division exclusions are applied. |
| `UNSUPPORTED_SCORING_CONTAINER` | The settings container has attributes, or category/modifier containers are outside the accepted child/attribute shape. |
| `EMPTY_SCORING_COLLECTION` | Either validated category/modifier collection is empty. |
| `UNSUPPORTED_STAT_STRUCTURE` | A category statistic has an unsupported child or attribute. |
| `UNSUPPORTED_MODIFIER_STRUCTURE` | A modifier statistic has an unsupported child or attribute. |
| `UNSUPPORTED_STRUCTURE` | Another existing unsupported-structure branch was reached; the check identifies its stage. |
| `VALIDATION_FAILED` | An existing structural/value/transport validation failed, or the AI flag failed its existing gate. No exception text is included. |
| `HUMAN_CONFIRMATION_REJECTED` | A private human verification explicitly returned failure. |
| `HUMAN_CONFIRMATION_NOT_COMPLETED` | A human comparison or initial live approval was not confirmed. |
| `USER_CANCELLED` | The human typed the exact `CANCEL` option in a league/team selection menu. |
| `SELECTION_NOT_COMPLETED` | Selection returned no valid choice without an explicit cancellation classification. |
| `INTERACTION_INTERRUPTED` | The existing KeyboardInterrupt path, including Ctrl+C or stopping pagination with a non-NEXT answer. |
| `SESSION_ERROR` | An unexpected exception reached the CLI boundary. Only the stage and this code are retained. |
| `VALIDATION_INCOMPLETE` | The attempt reached finalization without an earlier stop, but some checks remain unverified, such as absent/mixed coverage. |

An early stop leaves unexecuted checks `UNVERIFIED`; the diagnostic does not
promote or demote them. A fully successful attempt emits no stop diagnostics.
The first stop reason survives any later cleanup failure; the check statuses
still indicate that failure. No XML element names, exception messages, private
values, identifiers, URLs, hashes, or numeric response details are emitted.

`DOWNSTREAM_CHECKS_SKIPPED YES` describes checks skipped by the first recorded
branch stop. It does not mean every subsequent branch was skipped, or that no
roster request occurred. `LAST_DOWNSTREAM_CHECKS_SKIPPED` describes the most recent
stop's skips. Neither boolean identifies a particular HTTP response or field.

## Settings classification evidence and private inspection

The previous heuristic looked for `scor`, `stat`, `point`, or `bonus` anywhere in
an unfamiliar direct settings name. A name containing `status` could therefore
be treated as scoring-critical without semantic evidence. Conversely, a new rule
without those substrings could be ignored. Neither inference is reliable.
The latest shared reason identifies that guard, not the triggering field.
No actual live field name or NHL scoring rule has been inferred here.

[Yahoo's public API reference](https://sports.yahoo.com/developer/docs/) documents
league settings as containing draft type, scoring type, roster positions,
stat categories/modifiers, and divisions. It separately documents authenticated
user-owned teams, league teams, and team resources. It supplies no exhaustive
current NHL settings schema that establishes the unknown field as irrelevant.
The public reference's resource separation supports testing team identity and
rosters without calculating scoring weights.

The [public YFPY Settings source](https://yfpy.uberfastman.com/models/#yfpy.models.Settings)
provides names and descriptions for administrative keys. It is evidence of that
client's published model, not an authoritative NHL contract. The verifier now
excludes only these exact, correctly namespaced scalar keys from scoring checks:
`cant_cut_list`, `draft_pick_time`, `draft_time`, `draft_together`, `draft_type`,
`invite_permission`, `is_auction_draft`, `max_teams`, `persistent_url`,
`pickem_enabled`, `player_pool`, `post_draft_players`, `sendbird_channel_url`,
`trade_end_date`, `trade_ratify_type`, `trade_reject_time`, `uses_faab`,
`waiver_rule`, `waiver_time`, and `waiver_type`. Additional documented administrative scalars and the strictly
validated division ID/name metadata container are listed in the
[team slice contract notes](fgm-004-team-contracts.md#scoring-classification-evidence).
These exclusions apply only to administrative metadata, not point calculation.
For scalar exemptions, attributes, child elements, wrong namespaces, and
duplicate fields are not exempted.
These keys concern drafting, membership, transactions, or a separate pick'em
feature; this does not certify their complete semantics for other workflows.

The accepted scoring keys remain `scoring_type`, `stat_categories`,
`stat_modifiers`, `uses_fractional_points`, and `uses_negative_points`.
`roster_positions` is validated separately. Scoring type and flags describe
format/point handling; categories identify statistics and applicability;
modifiers supply exact weights joined by stat ID. Missing weights remain missing.
No calculations, float conversion, modifier defaults, bonus interpretation,
position mapping, or new NHL scoring-code mapping has been added.

The documented `uses_median_score` and `has_multiweek_championship` flags are
now preserved as competition configuration and included in the private human
comparison, without changing stat weights or calculating matchup results.
Other unrecognized direct fields conservatively leave scoring UNVERIFIED with
`UNSUPPORTED_SCORING_SETTING`, even when their names lack the old substrings.
This closed classification may still reject legitimate, currently unhandled
metadata. It deliberately does not claim those fields are
invalid or scoring-critical. Unknown custom/premium rules are not silently
certified. Category/modifier/stat validation
and Decimal checks remain strict; unknown attributes on settings and known
scoring scalar fields also cannot certify scoring.

When a direct settings field cannot be classified, the settings wrapper carries
unsupported attributes, or the roster wrapper fails its existing shape guard,
the same private alternate-screen panel now displays bounded structural details.
It identifies the check, local element name, fixed parent path, attribute names,
text/children/mixed/empty presence, immediate child names where relevant, and the
unmatched rule. A known name with an unsupported shape is distinguished from an
unrecognized name with unknown semantics. This is verifier recognition, not an
automatic claim about Yahoo documentation or scoring meaning.

Only rejected nodes are shown, up to four per panel. For each node, at most four
attribute and four immediate child names are displayed; names are ASCII-escaped
and bounded to 80 displayed characters plus a truncation marker. Wrapper
attribute failures do not display unrelated child names. Namespaces are labelled
expected Yahoo, other (URI hidden), or absent. Namespace URLs, attribute values,
element text, XML fragments, identifiers, names and weights are never shown by
this structural view. No recursive response explorer is added.

Unsupported means the verifier cannot establish the contract; it does not mean
Yahoo returned invalid data. Read the private information and use `NEXT` to
acknowledge it, or `UNKNOWN` when its meaning cannot be established. Neither
answer approves semantics or changes any check to PASS. Scoring inspection may
continue independent team/roster checks; unsupported roster inspection still
stops dependent normalization. Pagination uses `NEXT`; `CANCEL`, other answers,
or Ctrl+C interrupt and still trigger private-buffer cleanup. Keep every panel
local: do not copy it to AI, capture it, or write private structural notes.

This view reuses the already-fetched XML; no request, dependency, file, log or
Report payload is added. Only existing fixed statuses/reason codes reach the
shareable summary, after private-screen cleanup. Unsupported terminals fail
before authorization or inspection. Private display/input errors stop further
requests and produce only the existing fixed failure diagnostics. External recording cannot be detected or
undone, so the existing private/unrecorded-terminal attestation still applies.
The view is intentionally limited to these two contract boundaries; deeper
scoring, player normalization, count and required-value failures retain their
existing behavior without a new general inspection framework.

Unsupported scoring does not certify any skipped scoring or human check.
Independent checks may PASS, while SESSION remains UNVERIFIED; any FAIL makes
SESSION FAIL. Exact rejection, cancellation, essential transport/identity
failures still stop dependent work. Malformed consumed scoring values retain FAIL
while independent roster checks may proceed; SESSION remains FAIL.
The earliest diagnostic cause remains visible if a later failure occurs; the
individual statuses and SESSION still reflect that later failure.

## Unresolved until a private session

The developer now reports successful private user/team structure, membership,
league-team completeness and human team-list checks. Newly implemented provider
methods have been tested offline only. NHL scoring-code semantics, actual
category/modifier applicability, display-only interpretation, roster slot/player
contracts, roster date behavior, and full reserve inclusion remain unverified. A successful observed session is
evidence for that account, league, season, and response shape; it is not a global
Yahoo contract guarantee. Offseason behavior and undocumented pagination cannot
be established from a single current-roster sample. No live data belongs in tests.

The utility has no MCP registration, AI service client, telemetry, output-file
option, database, cache, or background task. Yahoo-backed MCP tools stay disabled.

## Roster envelope scope

The [integrated application revision](fgm-004-private-cli.md) now shares pure
settings/stat/Decimal/scope/slot parsing with this verifier. Documented median
and multiweek competition flags are included in its private scoring comparison,
separately from weights. Unknown premium/custom structures still stop scoring.
Published optional slot labels do not alter opaque codes or capacities.

The known scalar 0/1 `is_prescoring` flag no longer blocks basic roster facts;
any supplied value leaves context explicitly unverified. Coverage remains
UNVERIFIED and human position/coverage/completeness certification is not promoted.
This does not establish its NHL semantics or identify the actual live blocker.

The [roster contract](fgm-004-team-contracts.md#independent-roster-envelope-implemented-offline)
defines the normalized fields and remaining uncertainty. ROSTER_STRUCTURE and the
new fixed ROSTER_NORMALIZATION check can PASS before slots are established.
POSITION/COVERAGE/CAPACITY and human checks remain separate and are not promoted
by normalization. Missing player IDs or invalid date syntax now fail normalization
before those later checks. No explicit date parameter or effective-date inference
was added. This code has offline synthetic validation only, not a live NHL roster
contract guarantee.
