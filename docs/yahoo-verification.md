# Manual Yahoo verification (FGM-003)

Automated checks use synthetic data only. The developer reported successful live
OAuth authorization, token exchange, HTTP 200 from both the basic NHL API and
league-discovery probes, and discovery/display of their actual NHL leagues. This
used the second Yahoo application after Yahoo confirmed API activation, resolving
the earlier HTTP 403 issue. The final engineering review and follow-up validation
were offline only and did not independently repeat the reported live checks.
This guide is for the developer's confirmed personal, read-only Yahoo application;
authorize only your own approved account. Keep Yahoo-backed AI/MCP access disabled.

## Confirm before authorizing

- Yahoo application: **Fantasy GM**, **Public Client**.
- Registered redirect, exactly: `https://huzym.github.io/fantasy-gm/oauth/callback/`.
- Permission: **Fantasy Sports - Read**; no profile, OIDC, email, or write access.
- GitHub Pages callback is deployed and reachable at that exact HTTPS URL.
- Discovery uses the **current Yahoo hockey game/season**, not all historical
  leagues. Confirm that this matches the league you want to identify.

Yahoo's current [OAuth documentation](https://developer.yahoo.com/sign-in-with-yahoo/)
requires S256 PKCE for Public Clients and omits `client_secret`. Authorization uses
`https://api.login.yahoo.com/oauth2/request_auth`; token exchange/refresh uses
`https://api.login.yahoo.com/oauth2/get_token`.
The verifier follows [RFC 7636](https://www.rfc-editor.org/rfc/rfc7636).

The [Fantasy API User APIs / Games collection documentation](https://sports.yahoo.com/developer/docs/)
describes the logged-in user's games/leagues hierarchy, with game-code aliases
for the current season. FGM-003 uses one GET:

```text
https://fantasysports.yahooapis.com/fantasy/v2/users;use_login=1/games;game_keys=nhl/leagues
```

This is an implementation based on the documented URI combination. The reported
live run established access and response compatibility for the developer's
account at that time. Empty live collections, other accounts, future season
rollovers, and live refresh behavior remain unverified. Extra metadata in Yahoo's
default response is discarded in memory. No additional subresources are requested.

Token responses are streamed with a 64 KiB maximum, counting received bytes
regardless of Content-Length. Identity encoding is requested; compressed responses
are rejected before reading. Access tokens are validated for Bearer syntax before
discovery. These follow-up protections are covered by synthetic tests; they have
not been reverified in a live flow.

Discovery accepts at most 1 MiB of unencoded XML. It counts streamed bytes even
when `Content-Length` is absent or wrong, requests `identity` encoding, and rejects
compressed responses before reading. Required collection children/namespaces and
any supplied counts must be consistent; optional counts are not required. If live
Yahoo responses exceed this limit or differ in structure/encoding, stop and review
the compatibility issue without saving the response or relaxing protections.

## Run in a private interactive PowerShell terminal

Run from the repository root, with Python 3.12+ and uv installed. Do not use terminal
transcripts, debug HTTP logging, screen recording, or output redirection. Do not
share terminal or callback contents with an AI client. Never paste codes/tokens
into shell commands, documentation, issues, or source files.

For state-input diagnosis, use `uv run --locked python -m fantasy_gm.auth
--diagnose-state` in that private terminal (one command on one line). It adds only
`State received: yes/no` and `State length matches: yes/no` before the unchanged
exact comparison. Matching lengths do not prove matching values. Do not share
the authorization URL or any other terminal/callback contents; report only these
two booleans and the sanitized error.

Python's Windows hidden input reads individual characters. A CRLF paste can leave
an LF for the next prompt; empty input now reprompts without submitting state.
Whitespace and other unexpected characters are not trimmed or accepted. Use the
terminal's Paste action (for example Ctrl+Shift+V in Windows Terminal), since
PowerShell's shell-line editing is not active inside Python's hidden prompt.
Paste just the single value, then press Enter only if the prompt is still waiting.
Ctrl+C cancels. Every restarted invocation requires its own newly printed URL and
callback; a failed comparison or token exchange cannot reuse a consumed session.

```powershell
Set-Location 'D:\Codex\Fantasy GM\fantasy-gm'
uv sync --locked
$env:YAHOO_CLIENT_ID = Read-Host 'Yahoo Public Client ID'
$env:YAHOO_AI_TOOLS_ENABLED = 'false'
uv run --locked python -m fantasy_gm.auth
Remove-Item Env:YAHOO_CLIENT_ID
```

If using this checkout's existing local uv instead of a PATH installation, replace
`uv` with `& '.\.tools\bin\uv.exe'` and set its local runtime locations first:

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD '.tools\cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PWD '.tools\python'
```

1. Open the printed Yahoo authorization URL manually. No browser is opened by code.
2. Authorize with your own account. If permissions differ from those above, stop.
3. At the static callback page, copy the authorization code. Return to the still
   running local process and paste it at the hidden **Authorization code** prompt.
4. Copy the callback's returned state, paste it at the hidden **Returned state**
   prompt, and close the callback tab. Clear the clipboard after the handoff.
5. The process validates state before sending the code/verifier. A missing or
   mismatched state, rejected code, or network failure requires restarting the
   flow; each session permits only one attempt.
6. Successful verification prints Yahoo attribution and minimal league identifiers,
   names, sport, and season (or an empty result), then exits. It never prints access
   tokens, refresh tokens, or PKCE verifiers. Do not copy this output into files or
   an LLM conversation.

Codes/state are not accepted as command-line arguments. The CLI requires an
interactive input/output terminal, suppresses library logging, disables environment
proxy/auth inheritance in its HTTP client, and fails if hidden input is unavailable.
Temporary token values and league data exist only in memory during the process.
There is no token file or automatic refresh; a later invocation starts fresh.
The refresh method is covered synthetically, including rotated/omitted refresh
tokens; its live behavior is not verified by this one-shot CLI.

The callback keeps responses in page memory and removes OAuth parameters from
the visible URL. GitHub Pages still receives the initial redirect request; this
does not erase hosting infrastructure logs. Clipboard/terminal/browser history
are outside the application's control. Use a private session without clipboard
history/sync, close the tab, and avoid recording the manual flow.

## Local MCP verification

The official [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk)
implements the stdio server:

```powershell
uv run --locked python -m fantasy_gm.mcp
```

Launch this command through a local MCP client. Health and capabilities expose
only package/configuration information. `yahoo_list_my_leagues` always refuses in
FGM-003: the absent/false flag gives a policy denial; even exact `true` stays
unwired. Never enable or test live Yahoo data through an LLM for this ticket.

Automated smoke tests start the real stdio entry point in a child process with
network guards installed before server imports, discover/call the safe tools,
verify denial, and require a clean exit on stdin EOF. Normal test fixtures guard
test execution, with one exact private wakeup socket pair for Windows asyncio.
They do not provide a general collection-time or arbitrary-subprocess network
sandbox.

## Technical agreement constraints

Personal use, read-only, developer-owned leagues/teams only. No commercial or
multi-user Yahoo feature. Yahoo Fantasy information must not be persisted, cached,
indexed, dumped, recorded as test fixtures, or included in telemetry, even in
ignored directories. Future interfaces displaying Yahoo information must meet
Yahoo attribution requirements; the CLI identifies Yahoo as the source.
Yahoo-backed AI/MCP data exposure is disabled pending written clarification of
the agreement's AI-grounding language. These are project requirements, not a legal
interpretation. No workaround or browser-based write operation is included.
