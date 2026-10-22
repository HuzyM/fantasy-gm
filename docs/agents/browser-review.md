# Browser lifecycle review

For route/focus, disclosure and session-boundary browser tests, reuse
`frontend/browser-tests/helpers/navigation.mjs` and `helpers/session.mjs`.
Navigation waits for the application's focus transfer. Replacement-session tests
hold the fabricated response for that session until the loading state is visible,
then release it; the helper removes only its own route handler.

When reviewing cleared state, verify the feature is visibly open before asserting
empty contents. A missing item or private string while its panel is closed or
unmounted does not establish clearing. After browser back/forward, reopen the
disclosure if needed and assert visible empty/pending state inside its region.
Keep old-data absence assertions alongside those positive visibility assertions.

Use observable loading, focus and rendered-state transitions for synchronization.
Do not make a race pass with sleeps, retries or wider screenshot tolerances.

For parallel local worktrees, set a distinct `BROWSER_TEST_PORT` (1024–65535) in
that shell for Playwright and the retained Overview check. The default is 4173;
the host stays loopback and existing-server reuse stays disabled. Each worktree
keeps its own build and output directories.
