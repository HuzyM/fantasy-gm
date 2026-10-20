# Issue tracker: GitHub

Issues and specs live in GitHub Issues for `HuzyM/fantasy-gm`.
Use the `gh` CLI from this repository, or specify
`--repo HuzyM/fantasy-gm` explicitly.

## Conventions

Preserve established naming, milestone and project conventions.
Existing documentation uses FGM identifiers; retain those identifiers
when referring to existing work.

- Create an issue:
  `gh issue create --repo HuzyM/fantasy-gm --title "..." --body-file <file>`
- Read an issue:
  `gh issue view <number> --repo HuzyM/fantasy-gm --json number,title,body,labels,comments`
- List issues:
  `gh issue list --repo HuzyM/fantasy-gm --state open --limit 1000 --json number,title,body,labels,comments`
- Comment:
  `gh issue comment <number> --repo HuzyM/fantasy-gm --body-file <file>`
- Apply or remove labels:
  `gh issue edit <number> --repo HuzyM/fantasy-gm --add-label "..."`
  or `--remove-label "..."`
- Close:
  `gh issue close <number> --repo HuzyM/fantasy-gm`

For multiline bodies and comments, write the exact text to a temporary
file and use `--body-file`.

Issue listings are capped at 1,000 results. If that cap is reached,
continue with paginated GitHub API queries before treating discovery
as complete.

Read triage-role mappings from `docs/agents/triage-labels.md`.
Reuse matching labels without changing their descriptions or colors.
Create only missing configured labels.

## Pull requests as a triage surface

**PRs as a request surface: no.**

GitHub shares a number space across issues and pull requests.
Resolve an ambiguous number with `gh pr view <number>`, falling back
to `gh issue view <number>`.

## Skill terminology

When a skill says "publish to the issue tracker", create a GitHub issue.

When a skill says "fetch the relevant ticket", read the GitHub issue,
including its body, labels and comments.

## Wayfinding operations

A wayfinding map is one issue labelled `wayfinder:map`.
Child tickets use `wayfinder:<type>` labels: research, prototype,
grilling or task.

Use native sub-issues and issue dependencies when supported.
Otherwise, put `Part of #<parent>` in the child and maintain a task
list in the map. Record fallback dependencies with
`Blocked by: #<number>`.

The frontier consists of open child tickets without open blockers
or an assignee, in map order. Claim a selected ticket by assigning
the driving developer. Resolve it by recording the result, closing
the ticket and updating the map's decisions.

Wayfinding labels and issues are created only when that workflow
is invoked; they are not part of this setup.
