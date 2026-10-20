# Domain Docs

Use a single-context layout:

- `GLOSSARY.md` at the repository root.
- Architecture decision records under `docs/adr/`.

## Before exploring

Read the root glossary when present and any ADRs relevant to the area
being investigated.

If these documents do not exist, proceed silently. Do not create empty
placeholders or propose creating them merely because they are absent.
The domain-modeling workflow creates them when terminology or decisions
are actually resolved.

Continue consulting existing project documentation, including
`docs/architecture.md`, relevant feature guides and
`docs/ci-quality-gates.md`. This layout does not relocate or replace them.

## Vocabulary

Use glossary terms consistently in issue titles, proposals, hypotheses,
tests and implementation.

When a concept is missing, first check existing code and documentation.
Record a genuine terminology gap for the domain-modeling workflow;
do not invent a definition.

## Decision conflicts

If a proposal contradicts an existing ADR, identify the conflict
explicitly and explain why the decision should be reconsidered.
Do not silently override it.
