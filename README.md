# Fantasy GM

Fantasy GM is a fantasy sports analytics and management platform designed to connect real fantasy league data with schedule, player, matchup, and roster intelligence. The initial integration targets Yahoo Fantasy Hockey.

**Status: early development.** This repository contains the project foundation
only. Package namespaces, development tools, and documentation are ready; the
capabilities below are planned and are not implemented.

## Planned capabilities

- Yahoo Fantasy Hockey integration
- League and scoring settings
- Roster retrieval
- Matchup analysis
- Available-player analysis
- Weekly roster optimization
- Add/drop and trade analysis
- MCP interface for AI assistants

Future integrations may support **ESPN** and **Sleeper**, with sport intelligence
for **NBA, NFL, and MLB** alongside NHL.

Transaction/write functionality depends on provider-supported access. Analysis
does not imply that a provider allows transaction execution.

## Architecture

Provider integrations will normalize external data into Fantasy GM's own domain
types. Strategy and optimization will consume those types, keeping Yahoo details
out of the core. Sport intelligence will provide sport-specific context. Policy
will hold transaction safety rules when transaction functionality is introduced.
MCP will expose core capabilities to AI clients as an interface.

All namespaces are lightweight placeholders. Pydantic is reserved for future
domain/configuration models; httpx is reserved for future HTTP integrations.
See [the architecture document](docs/architecture.md) for the intended boundaries.

## Development setup

Install Python **3.12+** and [uv](https://docs.astral.sh/uv/getting-started/installation/).
The default development interpreter is Python 3.12.

From the repository root:

```sh
uv sync --locked
uv run python -c "import fantasy_gm; print('Fantasy GM imports successfully')"
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

`uv sync` installs the package and development dependencies into `.venv`.
Commit `uv.lock` to keep dependency versions reproducible. Build distributions
with `uv build` when needed.

`.env.example` contains blank placeholders for future Yahoo configuration.
Nothing currently reads these variables, and credentials are not needed to run
the scaffold or its checks.

## Security

Never commit `.env`, credentials, OAuth secrets, tokens, cookies, or personal
Yahoo data. Keep local data under ignored `data/` or `local/` directories and
review staged files before committing. Ignore rules are a safeguard, not a
substitute for that review.

## License

All rights reserved pending the project owner's choice of license. See `LICENSE`.
