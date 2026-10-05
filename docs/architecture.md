# Intended architecture

Fantasy GM is a provider-independent core with thin interfaces and replaceable
integrations. The diagram describes future responsibilities, not implemented
services or frameworks.

```text
AI Client
    |
    | MCP
    v
Fantasy GM MCP
    |
    v
Fantasy GM Core
    |
    +-- Provider Layer
    |      +-- Yahoo
    |      +-- future ESPN
    |      +-- future Sleeper
    |
    +-- Sport Intelligence
    |      +-- NHL
    |
    +-- Strategy Engine
    |
    +-- Weekly Optimizer
    |
    +-- Policy / Transaction Safety Layer
```

## Package responsibilities

| Namespace | Intended responsibility |
| --- | --- |
| `config` | Pydantic configuration models as configuration is introduced. |
| `domain` | Fantasy GM's own Pydantic domain types. |
| `providers` | Provider access and normalization into domain types. |
| `providers.yahoo` | Yahoo-specific transport and models. |
| `sports` / `sports.nhl` | Sport-specific schedule, player, and matchup context. |
| `strategy` | Analysis consuming domain types. |
| `optimizer` | Weekly roster optimization consuming domain types. |
| `policy` | Access constraints and transaction safety rules. |
| `mcp` | A thin interface exposing core capabilities to AI clients. |

## Boundaries and sources of truth

1. Yahoo-specific models must never become core domain models. Each provider
   will translate its data into Fantasy GM's domain types at the provider boundary.
2. Strategy and optimization must depend on the domain layer, without importing
   Yahoo-specific transport or models. Providers must remain replaceable.
3. The domain layer will be the shared source of truth for normalized types.
   Keep provider payloads confined to their integrations.
4. MCP is an interface into Fantasy GM, not the core architecture. The official
   Python MCP SDK can be added as an optional dependency when that interface is
   implemented; no SDK, server, or tools are included now.
5. Transaction/write functionality depends on provider-supported access. Future
   implementation must respect that access and the policy layer.
6. Never put credentials, tokens, OAuth secrets, cookies, or personal Yahoo data
   into source control.

## Incremental implementation

Implement only what each approved task needs. The current modules contain only
package docstrings; there are no speculative models, provider protocols, plugin
registries, or dependency injection frameworks. Define concrete models and
interfaces when actual integrations establish their requirements.

The current foundation uses Python 3.12+, a `src/` package layout, uv dependency
management and its build backend, Pydantic, and httpx. Pytest, Ruff, and strict
mypy provide development checks. `pyproject.toml` holds project/tool settings;
`uv.lock` holds resolved dependency versions.

No OAuth, API requests, NHL integration, strategy, optimization, transaction
execution, browser automation, database, frontend, Docker, or autonomous agents
are implemented in this scaffold.
