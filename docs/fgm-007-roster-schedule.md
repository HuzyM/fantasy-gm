# FGM-007 private roster schedule session

This human-only workflow joins Yahoo-reported NHL affiliations to observed
PuckAPI team schedules. A team game is **not a guaranteed player appearance**.
No player statistics, projections, optimization, transactions or AI tools are
added. FGM-004 league/configuration views and FGM-006 standalone schedule/demo
commands remain available unchanged. The operator reports successful private
live acceptance of this workflow. Implementation and automated tests use
synthetic data only; Codex did not make live provider requests.

## Human-reported live acceptance

The operator confirmed Yahoo authentication, player affiliation matching,
observed NHL game counts, player selection, cache reuse, manual refresh, visible
input retries, BACK navigation and clean exit work in the private session.
No credentials, account identifiers, player names or provider responses are
included in this acceptance record.

The operator understands and accepts the displayed total-unknown and B2B-unknown
states as intentional consequences of `COVERAGE_UNVERIFIED`. This acceptance
does not establish complete schedule coverage, every affiliation format, roster
completeness, player appearances or complete back-to-back coverage. The separate
offline suite tests expiry, malformed/partial responses and policy boundaries
using synthetic fixtures; those checks are not additional live acceptance claims.

## Run privately

Use a fresh, unrecorded PowerShell terminal outside Codex, screen sharing,
transcripts or AI-observed terminals. Never paste credentials or joined roster
output into chat. This sets keys only in the shell session and removes them on
exit; no files or profiles are written.

```powershell
Set-Location 'D:\Codex\Fantasy GM\fantasy-gm'
$fgmYahooId = Read-Host 'Yahoo Public Client ID (hidden)' -AsSecureString
$fgmPuckKey = Read-Host 'PuckAPI key (hidden)' -AsSecureString
try {
    $env:YAHOO_CLIENT_ID = [System.Net.NetworkCredential]::new('', $fgmYahooId).Password
    $env:PUCKAPI_API_KEY = [System.Net.NetworkCredential]::new('', $fgmPuckKey).Password
    $env:YAHOO_AI_TOOLS_ENABLED = 'false'
    & .\.tools\bin\uv.exe run --locked --offline --cache-dir .tools/cache python -B -m fantasy_gm.roster_schedule --interactive --cache-ttl-seconds 3600
} finally {
    Remove-Item Env:\PUCKAPI_API_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:\YAHOO_CLIENT_ID -ErrorAction SilentlyContinue
    $fgmYahooId.Dispose()
    $fgmPuckKey.Dispose()
    Remove-Variable fgmYahooId,fgmPuckKey
}
```

`--offline` applies to dependency resolution, not the explicitly requested live
provider requests. `--help` performs no authentication. All three streams must
be terminals, and alternate-screen setup must succeed before authorization.
Recording cannot be detected or undone; the private-session attestation is
required. Yahoo-backed AI/MCP remains disabled and unwired.

Authorize once, select a discovered NHL league and an owned Yahoo team, then
enter an inclusive 1–31-day NHL window within that league's season years.
The default display zone is America/Toronto. There are at most four Yahoo
Fantasy GETs: discovery, owned teams, league teams and the selected roster.
No settings, extra player endpoint, Yahoo refresh or repeated roster call is
needed. The access-token reference is released after roster retrieval.

The first schedule load displays the roster overview. Menu commands show that
overview, select a roster player for opponents/home-away/B2B details, select an
NHL team independently, change the window, manually refresh, or exit. Selecting
an NHL team does not select another fantasy roster or make another Yahoo call.
Missing/unsupported player affiliations do not prevent independent NHL-team
queries. Ordinary navigation, date entry and selections are visible while typing
inside the private screen. Invalid selections, dates and confirmation typos show
an error and retry locally without repeating authentication or provider calls.
OAuth authorization codes and returned state remain hidden; keys use the hidden
PowerShell prompts above. Do not enter credentials at an ordinary input prompt.

BACK returns from a player/team selection, details view, refresh confirmation or
change-window start prompt to the session menu. At an end-date prompt it returns
to start-date entry; during pagination it returns to the previous page (or the
menu from the first page when available). An unfinished date change leaves the
previous window intact. Initial league/owned-team selection and initial date
entry have no earlier safe step: BACK explains this and lets you continue or
CANCEL without restarting OAuth. Confirmations still require their exact phrase.
CANCEL/Ctrl+C exits the session safely; menu option 6 finishes normally.

## Affiliation contracts

The existing roster XML can supply `editorial_team_abbr`; the
[author-maintained YFPY model](https://yfpy.uberfastman.com/models/#yfpy.models.Player)
documents professional-team metadata, and its
[NHL roster examples](https://yfpy.uberfastman.com/query/#get_team_roster_player_info_by_date)
show the abbreviation and optional `nhl.t.*` editorial key. No additional Yahoo
endpoint is introduced. Only unique scalar fields with the expected namespace
are consumed. Optional malformed fields leave the player visible and the
affiliation unverified. Conflicting code/key relationships within the response
invalidate the affected affiliations; numeric editorial IDs are not decoded.

Case is normalized. Direct supported codes join the validated current PuckAPI
catalogue. The only additional alias is Yahoo's documented `Was` to PuckAPI's
`WSH`, corroborated by their published Washington names and
[PuckAPI's team directory](https://puckapi.com/teams). No name matching, fuzzy
lookup, historical franchise mapping or guessed aliases are used. For example,
an unsupported two-letter abbreviation stays unsupported; it is not expanded.

Each player retains their Yahoo identity. Missing, unsupported, conflicting,
unqualified-cohort and season-mismatched joins receive distinct fixed statuses.
The selected league season must match the schedule season. A reported roster
date outside its season years also prevents the join. Missing dates are not
filled from the clock. Reported affiliations can become stale or change after
trades, and unknown coverage does not establish a current/effective affiliation.
Roster completeness, lineup legality and future player appearances remain
unverified. Do not silently translate ambiguous metadata into a current team.

## Cache lifetime and spending

`ScheduleService` keeps at most **four** immutable, normalized PuckAPI snapshots
in process memory, with least-recently-used eviction. Keys include season,
inclusive dates, display timezone, game type and result limit. No Yahoo roster,
player name/identity, joined result, token, API key or raw response is cached.
The service never receives a roster. Joins are computed separately in memory.

The default TTL is one hour from successful load completion, measured with a
monotonic clock. `--cache-ttl-seconds` accepts a positive finite value. Hits do
not extend expiry. Expired entries are removed on the next access; there is no
background work. Context exit or cancellation clears the cache.

`CACHE_MISS` loads teams and games once, normally six credits. Repeated player
or NHL-team views of the same window show `CACHE_HIT` with the original
observation timestamp and make zero requests. A different key needs a new load.
Manual refresh requires typing REFRESH, displays `CACHE_REFRESH` and replaces
only that key. Expiration also needs a fresh load on the next requested view.
Each load owns a new bounded two-request client; six-second pacing is retained
between loads as well as between its requests. There are no automatic retries,
provider fallbacks, purchases or credit top-ups.

Errors and malformed responses are not cached. Refresh invalidates the old
entry before requesting; failure never silently falls back to stale data.
Validated partial/truncated observations can be reused, preserving their
`COVERAGE_UNVERIFIED`, `COHORT_UNVERIFIED` and `POSSIBLY_TRUNCATED` warnings.
An invalid snapshot cannot be promoted by caching it.

Coverage remains exactly as in FGM-006: below-limit results and empty responses
do not prove complete schedules or zeros. Times without a valid explicit UTC
offset remain unplaced. Unknown states remain uncertain. Observed B2B pairs
can be shown, but an empty pair list does not prove no B2Bs exist. No reschedule
history, source freshness guarantee or complete rankings are inferred.

## Private acceptance checklist

1. Compare each displayed professional affiliation with the Yahoo roster in the
   private browser. Missing/unsupported rows must remain explicit; never infer
   a team to obtain a match. If extra aliases are needed, establish them from
   published evidence before changing the mapping.
2. Compare observed team counts, opponents, home/away and B2B dates for a chosen
   week to the published NHL schedule. Check that these are team games, with no
   claim about whether the player will appear.
3. Observe CACHE_MISS initially, then CACHE_HIT while changing players and NHL
   teams. Players sharing an NHL team should agree and require no new requests.
4. Manually refresh once intentionally and confirm CACHE_REFRESH. For an
   intentional short-expiry test, start a separate session with a short TTL,
   wait past it and request another view; it should show CACHE_MISS. Both tests
   spend credits. No automatic repeated verification is required.
5. Check a Toronto DST-boundary window, missing-affiliation handling and exit.
   Only the fixed PRIVATE_SESSION outcome remains after the private screen is
   cleared. FINISHED means the interaction ended normally, not full coverage.

Share only sanitized pass/fail and fixed cache/policy statuses, never player
names, team ownership, keys, identifiers, XML, joined output or screenshots.
No actual Yahoo or PuckAPI requests were made during implementation.
