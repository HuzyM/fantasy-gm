## Agent skills

### Issue tracker

Issues and specs are tracked in GitHub Issues for HuzyM/fantasy-gm.
See `docs/agents/issue-tracker.md`.

### Triage labels

Use the five default triage roles, reusing matching existing labels.
See `docs/agents/triage-labels.md`.

### Domain docs

Use a single-context layout: root `GLOSSARY.md` and `docs/adr/`.
See `docs/agents/domain.md`.

These workflow conventions supplement existing project documentation;
they do not override repository privacy, provider, authorization,
testing or release requirements.

## PR and commit writing

- Write PR titles, descriptions and commit messages in a natural,
  professional software developer voice.
- Focus on what changed, why it changed and how it was verified.
  Use concise, technically accurate language.
- Avoid generic, repetitive, overly polished or promotional wording.
- Do not unnecessarily mention AI, Codex, Claude, agents, skills or
  orchestration processes. Describe the actual engineering changes.
- Use conventional commit formatting when appropriate:
  `<type>(<optional scope>): <summary>`.
- Keep PR descriptions proportional to the complexity of the change.
  Include relevant testing information and risks when applicable.
- Never claim tests were run or functionality was verified without
  evidence. Distinguish completed checks from checks not performed.
- Follow repository and organizational disclosure requirements.
  Required disclosures take precedence over wording preferences.
