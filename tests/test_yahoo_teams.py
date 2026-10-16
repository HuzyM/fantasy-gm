"""Invented team contracts only; no recorded provider data or live I/O."""

import httpx
import pytest
from pydantic import SecretStr

from fantasy_gm.providers.yahoo.fantasy import YahooFantasyClient, YahooFantasyError
from tests.test_yahoo_contract_verifier import OWNED, TEAM, TEAMS

KEY = "999.l.1001"
SECOND = (
    TEAM.replace(".t.1", ".t.2")
    .replace("<team_id>1", "<team_id>2")
    .replace("Invented Ice Team", "Invented Second Team")
)
OTHER = TEAM.replace("999.l.1001", "999.l.1002")


def test_league_teams_normalize_only_provider_independent_identities() -> None:
    from fantasy_gm.domain.team import Team

    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, stream=httpx.ByteStream(TEAMS))
        ),
        trust_env=False,
    ) as client:
        result = YahooFantasyClient(http_client=client).list_league_teams(
            SecretStr("fake-team-token"), KEY
        )
    assert result == [
        Team(
            provider="yahoo",
            provider_league_id=KEY,
            provider_team_id=KEY + ".t.1",
            name="Invented Ice Team",
        )
    ]
    assert set(result[0].model_dump()) == {
        "provider",
        "provider_league_id",
        "provider_team_id",
        "name",
    }


def test_multiple_owned_teams_are_cross_checked_without_scoring_or_retries() -> None:
    owned = OWNED.replace(b'teams count="1"', b'teams count="3"').replace(
        TEAM.encode(), (TEAM + SECOND + OTHER).encode()
    )
    league = TEAMS.replace(b'teams count="1"', b'teams count="2"').replace(
        TEAM.encode(), (TEAM + SECOND).encode()
    )
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            200, stream=httpx.ByteStream([owned, league][len(calls) - 1])
        )

    with httpx.Client(transport=httpx.MockTransport(handle), trust_env=False) as client:
        provider = YahooFantasyClient(http_client=client)
        result = provider.list_my_league_teams(SecretStr("fake-team-token"), KEY)
        assert set(vars(provider)) == {"_http_client"}
    assert [team.provider_team_id for team in result] == [KEY + ".t.1", KEY + ".t.2"]
    assert [request.url.path for request in calls] == [
        "/fantasy/v2/users;use_login=1/games;game_keys=999/teams",
        "/fantasy/v2/league/999.l.1001/teams",
    ]
    assert all(request.method == "GET" and not request.content for request in calls)


@pytest.mark.parametrize(
    "kind",
    [
        "missing",
        "duplicate",
        "inconsistent",
        "other_league",
        "other_game",
        "name_changed",
    ],
)
def test_malformed_or_inconsistent_team_identities_fail_safely(kind: str) -> None:
    from fantasy_gm.providers.yahoo.fantasy import parse_league_teams

    body = {
        "missing": TEAMS.replace(b"<team_id>1</team_id>", b""),
        "duplicate": TEAMS.replace(b'teams count="1"', b'teams count="2"').replace(
            TEAM.encode(), (TEAM + TEAM).encode()
        ),
        "inconsistent": TEAMS.replace(b"<team_id>1</team_id>", b"<team_id>2</team_id>"),
        "other_league": TEAMS.replace(b"999.l.1001.t.1", b"999.l.1002.t.1"),
        "other_game": TEAMS.replace(b"999.l.1001.t.1", b"998.l.1001.t.1"),
        "name_changed": TEAMS.replace(b"Invented Ice Team", b""),
    }[kind]
    with pytest.raises(YahooFantasyError) as error:
        parse_league_teams(body, league_key=KEY)
    assert "Invented" not in str(error.value) and KEY not in str(error.value)


@pytest.mark.parametrize(
    "key", ["../private", "nhl.l.1001", "999.l.1001?secret=fake", " 999.l.1001"]
)
def test_invalid_league_keys_never_reach_transport(key: str) -> None:
    def forbidden(request: httpx.Request) -> httpx.Response:
        pytest.fail("Invalid resource key reached transport")

    with httpx.Client(
        transport=httpx.MockTransport(forbidden), trust_env=False
    ) as client:
        provider = YahooFantasyClient(http_client=client)
        with pytest.raises(YahooFantasyError):
            provider.list_league_teams(SecretStr("fake-team-token"), key)
        with pytest.raises(YahooFantasyError):
            provider.list_my_league_teams(SecretStr("fake-team-token"), key)


def test_owned_team_absent_from_league_list_is_not_returned_as_valid() -> None:
    responses = [OWNED, TEAMS.replace(TEAM.encode(), SECOND.encode())]
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, stream=httpx.ByteStream(responses[len(calls) - 1]))

    with httpx.Client(transport=httpx.MockTransport(handle), trust_env=False) as client:
        with pytest.raises(YahooFantasyError):
            YahooFantasyClient(http_client=client).list_my_league_teams(
                SecretStr("fake-team-token"), KEY
            )
    assert len(calls) == 2


@pytest.mark.parametrize(
    "body",
    [
        OWNED.replace(b'teams count="1"', b'teams count="0"').replace(
            TEAM.encode(), b""
        ),
        OWNED.replace(TEAM.encode(), OTHER.encode()),
    ],
)
def test_no_owned_team_in_selected_league_returns_empty_without_extra_get(
    body: bytes,
) -> None:
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, stream=httpx.ByteStream(body))

    with httpx.Client(transport=httpx.MockTransport(handle), trust_env=False) as client:
        assert (
            YahooFantasyClient(http_client=client).list_my_league_teams(
                SecretStr("fake-team-token"), KEY
            )
            == []
        )
    assert len(calls) == 1


@pytest.mark.parametrize(
    "kind",
    [
        "user",
        "game",
        "game_key",
        "team_game",
        "count",
        "namespace",
        "id_namespace",
        "duplicate_field",
        "name_missing",
        "key_attribute",
    ],
)
def test_owned_response_rejects_ambiguous_or_malformed_identity(kind: str) -> None:
    from fantasy_gm.providers.yahoo.fantasy import parse_my_teams

    body = {
        "user": OWNED.replace(b"</user>", b"</user><user/>"),
        "game": OWNED.replace(b"</game>", b"</game><game/>"),
        "game_key": OWNED.replace(
            b"<game_key>999</game_key>", b"<game_key>998</game_key>"
        ),
        "team_game": OWNED.replace(b"999.l.1001.t.1", b"998.l.1001.t.1"),
        "count": OWNED.replace(b'teams count="1"', b'teams count="2"'),
        "namespace": OWNED.replace(b"<teams", b'<teams xmlns="urn:synthetic"'),
        "id_namespace": OWNED.replace(b"<team_id>", b'<team_id xmlns="urn:synthetic">'),
        "duplicate_field": OWNED.replace(
            b"</team_id>", b"</team_id><team_id>1</team_id>"
        ),
        "name_missing": OWNED.replace(b"<name>Invented Ice Team</name>", b""),
        "key_attribute": OWNED.replace(b"<team_key>", b'<team_key fake="private">'),
    }[kind]
    with pytest.raises(YahooFantasyError):
        parse_my_teams(body, game_key="999")


@pytest.mark.parametrize(
    "field,value",
    [
        ("league_key", "999.l.1002"),
        ("league_id", "1002"),
        ("game_key", "998"),
        ("game_code", "nba"),
        ("num_teams", "2"),
    ],
)
def test_supplied_league_metadata_must_agree(field: str, value: str) -> None:
    from fantasy_gm.providers.yahoo.fantasy import parse_league_teams

    if field == "league_key":
        body = TEAMS.replace(
            b"<league_key>999.l.1001</league_key>",
            f"<{field}>{value}</{field}>".encode(),
        )
    else:
        body = TEAMS.replace(
            b"</league>", f"<{field}>{value}</{field}></league>".encode()
        )
    with pytest.raises(YahooFantasyError):
        parse_league_teams(body, league_key=KEY)


def test_changed_name_between_user_and_league_responses_is_not_silently_merged() -> (
    None
):
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        body = (
            OWNED
            if len(calls) == 1
            else TEAMS.replace(b"Invented Ice Team", b"Invented Renamed Team")
        )
        return httpx.Response(200, stream=httpx.ByteStream(body))

    with httpx.Client(transport=httpx.MockTransport(handle), trust_env=False) as client:
        with pytest.raises(YahooFantasyError):
            YahooFantasyClient(http_client=client).list_my_league_teams(
                SecretStr("fake-team-token"), KEY
            )
    assert len(calls) == 2


def test_empty_league_collection_and_unconsumed_manager_data() -> None:
    from fantasy_gm.providers.yahoo.fantasy import parse_league_teams

    assert (
        parse_league_teams(
            TEAMS.replace(b'teams count="1"', b'teams count="0"').replace(
                TEAM.encode(), b""
            ),
            league_key=KEY,
        )
        == []
    )
    body = TEAMS.replace(
        b"</team>",
        b"<managers><manager><guid>fake-private-guid</guid></manager></managers><is_owned_by_current_login>0</is_owned_by_current_login></team>",
    )
    result = parse_league_teams(body, league_key=KEY)
    assert "fake-private-guid" not in repr(result)


def test_team_reads_do_not_persist_log_or_retain_provider_values(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import builtins
    import logging

    def handle(request: httpx.Request) -> httpx.Response:
        logging.critical("fake-private-guid and Invented Ice Team")
        return httpx.Response(200, stream=httpx.ByteStream(TEAMS))

    def deny(*args: object, **kwargs: object) -> None:
        raise AssertionError("Provider attempted filesystem access")

    with httpx.Client(transport=httpx.MockTransport(handle), trust_env=False) as client:
        provider = YahooFantasyClient(http_client=client)
        with monkeypatch.context() as patch:
            patch.setattr(builtins, "open", deny)
            first = provider.list_league_teams(SecretStr("fake-team-token"), KEY)
            second = provider.list_league_teams(SecretStr("fake-team-token"), KEY)
        assert first == second and set(vars(provider)) == {"_http_client"}
    assert not caplog.records


@pytest.mark.parametrize(
    "kind", ["unauthorized", "redirect", "gzip", "oversized", "transport"]
)
def test_team_transport_uses_existing_sanitized_limits_and_never_retries(
    kind: str,
) -> None:
    import traceback

    from fantasy_gm.providers.yahoo.fantasy import MAX_LEAGUE_RESPONSE_BYTES

    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.headers["authorization"] == "Bearer fake-team-token"
        assert request.headers["accept-encoding"] == "identity"
        assert request.headers["cache-control"] == "no-store"
        assert request.extensions["timeout"] == dict.fromkeys(
            ("connect", "read", "write", "pool"), 10.0
        )
        if kind == "transport":
            raise httpx.ReadTimeout("fake-private-value", request=request)
        return httpx.Response(
            {"unauthorized": 401, "redirect": 302}.get(kind, 200),
            headers={
                "Location": "https://example.test/fake-private",
                "Content-Encoding": "gzip" if kind == "gzip" else "identity",
            },
            stream=httpx.ByteStream(
                b"x" * (MAX_LEAGUE_RESPONSE_BYTES + 1)
                if kind == "oversized"
                else b"fake-private-value"
            ),
        )

    with httpx.Client(
        transport=httpx.MockTransport(handle), trust_env=False, follow_redirects=True
    ) as client:
        with pytest.raises(YahooFantasyError) as error:
            YahooFantasyClient(http_client=client).list_my_league_teams(
                SecretStr("fake-team-token"), KEY
            )
    assert len(calls) == 1
    assert "fake-private" not in "".join(traceback.format_exception(error.value))


def test_verifier_can_select_second_owned_team_using_shared_parsers() -> None:
    from fantasy_gm.providers.yahoo.contract_verifier import (
        Check,
        Report,
        Status,
        verify_contracts,
    )
    from tests.test_yahoo_contract_verifier import DISCOVERY, ROSTER, SETTINGS

    pair = (TEAM + SECOND).encode()
    payloads = [
        DISCOVERY,
        SETTINGS.replace(b"<num_teams>1</num_teams>", b"<num_teams>2</num_teams>"),
        OWNED.replace(b'teams count="1"', b'teams count="2"').replace(
            TEAM.encode(), pair
        ),
        TEAMS.replace(b'teams count="1"', b'teams count="2"').replace(
            TEAM.encode(), pair
        ),
        ROSTER.replace(b"999.l.1001.t.1", b"999.l.1001.t.2"),
    ]
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, stream=httpx.ByteStream(payloads[len(calls) - 1]))

    def choose(title: str, options: tuple[str, ...]) -> int:
        if title == "Select your owned team":
            assert len(options) == 2
            return 1
        return 0

    report = Report()
    with httpx.Client(transport=httpx.MockTransport(handle), trust_env=False) as client:
        verify_contracts(
            SecretStr("fake-team-token"),
            http_client=client,
            report=report,
            choose=choose,
            confirm=lambda check, details: Status.PASS,
        )
    assert len(calls) == 5 and calls[-1].url.path.endswith(".t.2/roster")
    assert report.passed(Check.OWNED_TEAM_MEMBERSHIP)
    assert report.passed(Check.HUMAN_ROSTER_COMPLETE)
