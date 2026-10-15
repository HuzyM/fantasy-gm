# Yahoo HTTP 403 isolation (historical investigation, local only)

The developer reported resolving the earlier HTTP 403 issue using the second
Yahoo application after Yahoo confirmed API activation. OAuth and token exchange
succeeded, both diagnostic endpoints returned HTTP 200, and normal discovery
retrieved/displayed the developer's actual NHL leagues. The final engineering
review and follow-up validation were offline only and did not repeat those live
checks. The investigation below records the earlier diagnosis and retains the
local procedure for future failures.

Ask for explicit approval before any new authorization or API request. Use the
developer's own account and approved Public Client with Fantasy Sports - Read. Keep
`YAHOO_AI_TOOLS_ENABLED=false`. Do not change scopes or application settings based
on a 403 alone.

## Read-only audit

The existing discovery client sends a bodyless GET to:

```text
https://fantasysports.yahooapis.com/fantasy/v2/users;use_login=1/games;game_keys=nhl/leagues
```

It supplies `Authorization: Bearer <in-memory access token>`,
`Accept: application/xml`, `Cache-Control: no-store`, and
`Accept-Encoding: identity`. It disables inherited client auth and redirects,
uses a 10-second timeout, and checks the actual HTTP status before XML parsing.
A parser failure therefore cannot produce the reported HTTP 403 message.
The manual CLI creates a clean `httpx.Client(trust_env=False)`.

The frozen configuration reads the current process's `YAHOO_CLIENT_ID` once;
authorization and token exchange use that same ID and fixed redirect URI. No
`.env`, legacy secret, old token file, or alternate app lookup is used. A stale
shell environment can nevertheless select the wrong app. Confirm the intended
ID privately, without printing it or sending it to an AI client.

PKCE uses 256 bits of randomness, an RFC 7636 verifier, and S256. The same session
supplies the authorization state/challenge and consumes the returned state using
constant-time comparison before token exchange. Token exchange submits the code,
verifier, client ID, redirect URI, and authorization-code grant without a secret.
The CLI requires a Bearer token and immediately uses its access token. Lifetime
is validated as a positive `expires_in`; no acquisition timestamp or automatic
refresh is maintained. A fresh immediate probe avoids reusing an expired token,
but mocked tests cannot establish live token validity or granted permissions.

The earlier investigation did not establish an implementation defect explaining
the 403 and considered application provisioning and token permissions possible
causes. The later reported success followed Yahoo's API activation confirmation
for the second application. Successful OAuth alone still does not independently
prove Fantasy API access.

## Official documentation checked

- [Fantasy API reference](https://sports.yahoo.com/developer/docs/): Game resource
  accepts a game code as its key; User APIs document the games/leagues hierarchy.
  The game-code alias normally follows Yahoo's current available season, which
  need not be the particular season the developer intended.
- [Yahoo OAuth API requests](https://developer.yahoo.com/oauth2/guide/apirequests/):
  HTTPS requests use the Bearer access token in the Authorization header.
- [Current Public Client OAuth guidance](https://developer.yahoo.com/sign-in-with-yahoo/):
  Public Clients require PKCE and omit a client secret. It also mentions relevant
  API scope identifiers for private data, without resolving Fantasy-specific
  scope/default behavior in the documentation retrieved for this investigation.
- [Fantasy Developer portal](https://sports.yahoo.com/developer/): application
  review/access is a separate process from user OAuth authorization.

Direct retrieval of the Fantasy reference and modern OAuth page failed in the
research tool; their official search-indexed text was available. These sources
support the URI patterns and request structure, not live endpoint availability
or provisioning of either client ID. No Fantasy-specific scope string was
established; ask Yahoo whether selected app permissions suffice or an explicit
read scope is required for this Public Client. Do not invent a scope or add OIDC.
No documented extra GET Content-Type or custom Fantasy header was established.

## Diagnostic behavior

`providers.yahoo.diagnostics.diagnose_fantasy_access` probes exactly:

- A: `https://fantasysports.yahooapis.com/fantasy/v2/game/nhl`
- B: the existing discovery URL above.

Both GETs use the same supplied in-memory access token and production request
headers. No redirects, retries, token refresh, persistence, or body reads occur.
Responses are closed without parsing or retaining any Fantasy payload. Logging
is suppressed during the probes and its previous setting restored afterward.
Only predefined labels, status codes, accepted/rejected, and status-derived
categories are returned. Categories are not Yahoo's underlying error reason.
HTTP 2xx means accepted at the HTTP level; it does not validate response content.
The helper has no MCP registration, domain integration, or arbitrary URL input.
The human CLI's `--diagnose-api` mode calls it after normal state validation and
token exchange, prints a UTC attempt time, and exits without ordinary discovery.
It never restarts automatically. No dependencies or OAuth request parameters changed.

## Token exchange failures

A supervised attempt returned HTTP 400 before any diagnostic GET. Its underlying
cause remains unknown: the old error handler discarded Yahoo's error code. The
client now reports only exact allowlisted OAuth/Yahoo protocol categories, such
as `invalid_grant`, `invalid_client`, or `invalid_authorization_code`. Unknown,
malformed, oversized, or deeply nested error responses give `category=unknown`.
Free-form `error_description`, response bodies, headers, and credentials are never
shown or persisted. See [Yahoo troubleshooting](https://developer.yahoo.com/oauth2/guide/openid_connect/troubleshooting.html).
An invalid grant is not proof of expiration: code reuse, client/redirect mismatch,
or PKCE rejection can also require investigation. Do not infer blame or change
configuration from that category alone. A failed exchange produces no Fantasy GET
and prints a UTC failure time; it requires a separately approved fresh attempt.

## Supervised procedure, only after explicit approval

Use the direct CLI mode below, not the previous Pdb procedure. Pdb restarts after
program exit and its old line-61 breakpoint is no longer valid. Quit any remaining
debugger with `q`; do not continue it. Use a private human-controlled terminal with
no transcript, screen sharing, HTTP logging, or recording. The existing manual
authorization prelude displays its private authorization URL for the human; it
must never be shared with an AI client. Diagnostic output is only a UTC time and
the two sanitized status lines (or a sanitized failure).

1. Privately confirm that the intended application's settings and confirmation
   submission refer to the same client ID. Start a fresh PowerShell process;
   provide that ID via a secure prompt instead of reusing a stale environment.
   Do not read or modify `.env`.

   ```powershell
   Set-Location 'D:\Codex\Fantasy GM\fantasy-gm'
   $env:UV_CACHE_DIR = Join-Path $PWD '.tools\cache'
   $env:UV_PYTHON_INSTALL_DIR = Join-Path $PWD '.tools\python'
   $env:YAHOO_AI_TOOLS_ENABLED = 'false'
   $yahooIdSecure = Read-Host 'Confirmed Yahoo Public Client ID' -AsSecureString
   $yahooIdPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($yahooIdSecure)
   try {
       $env:YAHOO_CLIENT_ID = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($yahooIdPointer)
   }
   finally {
       [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($yahooIdPointer)
       $yahooIdSecure.Dispose()
       Remove-Variable yahooIdSecure, yahooIdPointer
   }
   & '.\.tools\bin\uv.exe' run --locked --offline python -m fantasy_gm.auth --diagnose-api
   ```

   This input method supports Windows PowerShell 5.1. Client ID remains only in
   the local process environment; do not print it or read `.env`.

2. Manually open the authorization URL displayed by the existing CLI, authorize
   only the approved personal account/read permission, and return the fresh code
   and state to its hidden prompts. Do not reuse a previous callback or session.
   Close the callback and clear the clipboard. No browser automation is used.
   On failure, stop. Do not retry under the previous one-session approval.

3. Successful exchange automatically produces one UTC diagnostic attempt time and
   exactly the two predefined GET summaries, using the same fresh token. Then the
   process exits. No ordinary league parsing or display occurs. On token failure
   it exits with a sanitized category/time and no GET requests. Tokens expire
   naturally; this procedure does not revoke them.

4. Remove `YAHOO_CLIENT_ID` from this process's environment and close the private
   terminal/browser session. Share only the sanitized diagnostic output and UTC
   time. Never share the authorization prelude, debugger
   variables, headers, token response, callback, or Fantasy response.

   ```powershell
   Remove-Item Env:YAHOO_CLIENT_ID
   ```

## Interpretation and escalation

| A | B | What to investigate next |
| --- | --- | --- |
| 403 | 403 | Broad API/application authorization, provisioning, token permission, or gateway rejection; not proof of any one cause. |
| 200 | 403 | Game access works; investigate user/resource permission and the discovery combination. |
| 200 | 200 | Both requests were HTTP-accepted; next inspect integration/response compatibility separately without saving or sharing data. |
| 401 | any | Fresh token validity, Bearer header, revocation, client/account mismatch. |
| other | any | Redirect, missing resource, throttling, server error, or transport failure according to its own status/category. |

If both are 403, send Yahoo support (through its approved private channel) the
application names/client IDs, approval/confirmation submission dates, Public
Client type, Read permission, registered redirect URI, affected account identifier
if requested, UTC attempt time, the two fixed GET paths/statuses, and confirmation
that a fresh PKCE exchange preceded them. Client IDs are needed for Yahoo's
provisioning lookup but must not be posted publicly or shared with an AI client.
Ask Yahoo to confirm effective Fantasy read access for each exact client ID,
Public Client support, user-consent requirements, explicit scope/default behavior,
and whether an account/region or gateway restriction explains the denial.
Do not send secrets, tokens, codes, state, verifiers, full headers/bodies, HARs,
or league data. This helper intentionally does not capture a request ID; ask
Yahoo whether it needs additional non-sensitive correlation information before
adding any further diagnostic capture.
