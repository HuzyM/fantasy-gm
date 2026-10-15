"""Hand-written synthetic XML only; never captured Yahoo data."""

import logging
import traceback
from collections.abc import Iterator

import httpx
import pytest
from pydantic import SecretStr

from fantasy_gm.domain.league import League
from fantasy_gm.providers.yahoo.fantasy import (
    LEAGUE_DISCOVERY_URL,
    MAX_LEAGUE_RESPONSE_BYTES,
    YahooFantasyClient,
    YahooFantasyError,
    parse_leagues,
)

SYNTHETIC_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<fantasy_content xmlns="http://fantasysports.yahooapis.com/fantasy/v2/base.rng">
  <users count="1"><user><guid>fake-unused-guid</guid><games count="1"><game>
    <game_key>999</game_key><code>nhl</code><season>2099</season>
    <leagues count="2">
      <league><league_key>999.l.1001</league_key><name>Synthetic Hockey One</name>
        <game_code>nhl</game_code><season>2099</season><num_teams>12</num_teams></league>
      <league><league_key>999.l.1002</league_key>
        <name>Synthetic Hockey Two</name></league>
    </leagues>
  </game></games></user></users>
</fantasy_content>"""


def test_xml_normalizes_to_provider_independent_league() -> None:
    result = parse_leagues(SYNTHETIC_XML)
    assert len(result) == 2
    assert result[0] == League(
        provider="yahoo",
        provider_league_id="999.l.1001",
        name="Synthetic Hockey One",
        sport="nhl",
        season=2099,
    )
    assert result[1].season == 2099 and result[1].sport == "nhl"
    assert set(result[0].model_dump()) == {
        "provider",
        "provider_league_id",
        "name",
        "sport",
        "season",
    }
    assert not hasattr(result[0], "guid") and not hasattr(result[0], "num_teams")


def test_discovery_get_bearer_and_no_cache_or_logging(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert str(request.url) == LEAGUE_DISCOVERY_URL
        assert request.method == "GET" and not request.content
        assert request.headers["authorization"] == "Bearer fake-access-token-for-tests"
        assert request.headers["accept"] == "application/xml"
        assert request.headers["cache-control"] == "no-store"
        assert request.headers["accept-encoding"] == "identity"
        return httpx.Response(200, stream=httpx.ByteStream(SYNTHETIC_XML))

    with httpx.Client(
        transport=httpx.MockTransport(handle), auth=("fake-id", "fake-secret")
    ) as client:
        provider = YahooFantasyClient(http_client=client)
        first = provider.list_my_hockey_leagues(
            SecretStr("fake-access-token-for-tests")
        )
        second = provider.list_my_hockey_leagues(
            SecretStr("fake-access-token-for-tests")
        )
        assert set(vars(provider)) == {"_http_client"}
    assert len(calls) == 2 and first == second
    assert "fake-access-token-for-tests" not in caplog.text
    assert "Synthetic Hockey" not in caplog.text


@pytest.mark.parametrize("status", [302, 401, 403, 429, 500])
def test_http_error_and_redirect_are_sanitized(status: int) -> None:
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            status,
            content=SYNTHETIC_XML,
            headers={"Location": "https://example.test/never-called"},
        )

    with httpx.Client(
        transport=httpx.MockTransport(handle), follow_redirects=True
    ) as client:
        with pytest.raises(YahooFantasyError) as error:
            YahooFantasyClient(http_client=client).list_my_hockey_leagues(
                SecretStr("fake-token")
            )
    assert str(status) in str(error.value) and "Synthetic Hockey" not in str(
        error.value
    )
    assert len(calls) == 1


def test_transport_error_is_sanitized() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("fake-sensitive-league-and-token", request=request)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(YahooFantasyError) as error:
            YahooFantasyClient(http_client=client).list_my_hockey_leagues(
                SecretStr("fake-token")
            )
    assert "fake-sensitive" not in "".join(traceback.format_exception(error.value))


@pytest.mark.parametrize(
    "xml",
    [
        b"fake-invalid-xml",
        b"{}",
        b"\xff",
        SYNTHETIC_XML.replace(b"<name>Synthetic Hockey One</name>", b""),
        SYNTHETIC_XML.replace(b"<league_key>999.l.1001</league_key>", b""),
        SYNTHETIC_XML.replace(
            b"<season>2099</season>", b"<season>fake-bad-season</season>"
        ),
        SYNTHETIC_XML.replace(b"<season>2099</season>", b"<season>-1</season>"),
        SYNTHETIC_XML.replace(b"nhl", b"nba"),
        b'<fantasy_content xmlns="http://fantasysports.yahooapis.com/fantasy/v2/base.rng"><error>fake-provider-error</error></fantasy_content>',
        b'<!DOCTYPE fantasy_content [<!ENTITY x "fake-entity">]>'
        b"<fantasy_content>&x;</fantasy_content>",
    ],
)
def test_malformed_xml_never_echoes_data(xml: bytes) -> None:
    with pytest.raises(YahooFantasyError, match="Malformed") as error:
        parse_leagues(xml)
    assert "Synthetic Hockey" not in str(error.value)
    assert "fake-provider-error" not in str(error.value)


def test_no_leagues_is_valid() -> None:
    xml = SYNTHETIC_XML.replace(
        SYNTHETIC_XML[
            SYNTHETIC_XML.index(b'<leagues count="2">') : SYNTHETIC_XML.index(
                b"</leagues>"
            )
            + len(b"</leagues>")
        ],
        b'<leagues count="0"/>',
    )
    assert parse_leagues(xml) == []


def test_missing_game_is_valid_for_no_participation() -> None:
    xml = (
        b'<fantasy_content xmlns="http://fantasysports.yahooapis.com/fantasy/v2/base.rng">'
        b'<users count="1"><user><games count="0"/></user></users></fantasy_content>'
    )
    assert parse_leagues(xml) == []


def test_empty_token_is_rejected_without_http() -> None:
    with httpx.Client() as client:
        with pytest.raises(YahooFantasyError, match="required"):
            YahooFantasyClient(http_client=client).list_my_hockey_leagues(
                SecretStr(" ")
            )


@pytest.mark.parametrize(
    ("before", "after"),
    [
        (b'users count="1"', b'users count="0"'),
        (b'users count="1"', b'users count="2"'),
        (b'games count="1"', b'games count="2"'),
        (b'games count="1"', b'games count="0"'),
        (b'leagues count="2"', b'leagues count="3"'),
        (b'leagues count="2"', b'leagues count="1"'),
        (b'leagues count="2"', b'leagues count="0"'),
        (b'leagues count="2"', b'leagues count="-1"'),
        (b'leagues count="2"', b'leagues count="fake-invalid"'),
        (b'leagues count="2"', b'leagues count=""'),
        (b"<game>", b'<game xmlns="urn:fake-wrong-namespace">'),
        (b'<games count="1">', b'<games xmlns="urn:fake-wrong" count="1">'),
        (b"<league>", b'<league xmlns="urn:fake-wrong-namespace">'),
        (b"<name>", b'<name xmlns="urn:fake-wrong-namespace">'),
        (b"<name>Synthetic Hockey Two</name>", b"<name><fake-child/></name>"),
        (b"</users>", b'</users><users count="0"/>'),
        (b"</users>", b'</users><users xmlns="urn:fake-wrong" count="0"/>'),
    ],
)
def test_collection_counts_structure_and_namespaces_fail_closed(
    before: bytes, after: bytes
) -> None:
    with pytest.raises(YahooFantasyError, match="Malformed") as error:
        parse_leagues(SYNTHETIC_XML.replace(before, after))
    assert "Synthetic Hockey" not in str(error.value)
    assert "urn:fake" not in str(error.value)


@pytest.mark.parametrize(
    "body",
    [
        b'<users count="0"/>',
        b'<users count="1"><user><games count="0"/></user></users>',
        b'<users count="1"><user><games count="1"><game>'
        b'<leagues count="0"/></game></games></user></users>',
    ],
)
def test_valid_empty_collections(body: bytes) -> None:
    xml = (
        b'<fantasy_content xmlns="http://fantasysports.yahooapis.com/fantasy/v2/base.rng">'
        + body
        + b"</fantasy_content>"
    )
    assert parse_leagues(xml) == []


@pytest.mark.parametrize(
    "body",
    [
        b'<users count="1"><user><games count="1"/></user></users>',
        b'<users count="1"><user><games count="1"><game>'
        b'<leagues count="1"/></game></games></user></users>',
    ],
)
def test_declared_nonempty_but_missing_children_is_malformed(body: bytes) -> None:
    xml = (
        b'<fantasy_content xmlns="http://fantasysports.yahooapis.com/fantasy/v2/base.rng">'
        + body
        + b"</fantasy_content>"
    )
    with pytest.raises(YahooFantasyError, match="Malformed"):
        parse_leagues(xml)


def test_one_bad_league_rejects_entire_collection() -> None:
    # First league is valid; a malformed second league must not be omitted.
    xml = SYNTHETIC_XML.replace(b"<name>Synthetic Hockey Two</name>", b"")
    with pytest.raises(YahooFantasyError, match="Malformed"):
        parse_leagues(xml)


def test_both_documented_namespaces_and_optional_fields() -> None:
    https_xml = SYNTHETIC_XML.replace(
        b'xmlns="http://fantasysports', b'xmlns="https://fantasysports'
    )
    assert parse_leagues(https_xml) == parse_leagues(SYNTHETIC_XML)
    no_counts = SYNTHETIC_XML.replace(b' count="1"', b"").replace(b' count="2"', b"")
    assert len(parse_leagues(no_counts)) == 2
    optional = (
        SYNTHETIC_XML.replace(b"<season>2099</season>", b"")
        .replace(b"<code>nhl</code>", b"")
        .replace(b"<game_code>nhl</game_code>", b"")
    )
    leagues = parse_leagues(optional)
    assert all(league.season is None and league.sport is None for league in leagues)


class SyntheticStream(httpx.SyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.read_count = 0
        self.closed = False

    def __iter__(self) -> Iterator[bytes]:
        for chunk in self.chunks:
            self.read_count += 1
            yield chunk

    def close(self) -> None:
        self.closed = True


@pytest.mark.parametrize("headers", [{}, {"Content-Length": "1"}])
def test_stream_size_limit_ignores_missing_or_misleading_length(
    headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    stream = SyntheticStream(
        [
            b"fake-sensitive-" + b"x" * (MAX_LEAGUE_RESPONSE_BYTES // 2),
            b"x" * (MAX_LEAGUE_RESPONSE_BYTES // 2),
            b"fake-never-read",
        ]
    )

    def never_parse(content: bytes) -> list[League]:
        pytest.fail("Oversized XML must never reach the parser")

    monkeypatch.setattr("fantasy_gm.providers.yahoo.fantasy.parse_leagues", never_parse)
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, headers=headers, stream=stream)
        )
    ) as client:
        with pytest.raises(YahooFantasyError, match="size limit") as error:
            YahooFantasyClient(http_client=client).list_my_hockey_leagues(
                SecretStr("fake-token")
            )
    assert stream.read_count == 2 and stream.closed
    assert "fake-sensitive" not in str(error.value)


def test_exact_limit_is_accepted() -> None:
    padded = SYNTHETIC_XML + b" " * (MAX_LEAGUE_RESPONSE_BYTES - len(SYNTHETIC_XML))
    stream = SyntheticStream([padded[:1024], padded[1024:]])
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, stream=stream)
        )
    ) as client:
        assert (
            len(
                YahooFantasyClient(http_client=client).list_my_hockey_leagues(
                    SecretStr("fake-token")
                )
            )
            == 2
        )
    assert stream.closed


def test_compressed_response_is_rejected_before_read() -> None:
    stream = SyntheticStream([b"fake-never-read"])
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, headers={"Content-Encoding": "gzip"}, stream=stream
            )
        )
    ) as client:
        with pytest.raises(YahooFantasyError, match="content encoding"):
            YahooFantasyClient(http_client=client).list_my_hockey_leagues(
                SecretStr("fake-token")
            )
    assert stream.read_count == 0 and stream.closed


def test_direct_parser_enforces_the_same_size_bound() -> None:
    with pytest.raises(YahooFantasyError, match="size limit"):
        parse_leagues(b"fake-" + b"x" * MAX_LEAGUE_RESPONSE_BYTES)


def test_stream_read_failure_is_sanitized_and_closed() -> None:
    class FailingStream(SyntheticStream):
        def __iter__(self) -> Iterator[bytes]:
            yield b"fake-sensitive-partial-response"
            raise httpx.ReadError("fake-sensitive-transport-message")

    stream = FailingStream([])
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, stream=stream)
        )
    ) as client:
        with pytest.raises(YahooFantasyError, match="request failed") as error:
            YahooFantasyClient(http_client=client).list_my_hockey_leagues(
                SecretStr("fake-token")
            )
    assert stream.closed
    assert "fake-sensitive" not in "".join(traceback.format_exception(error.value))


def test_rejected_stream_body_is_never_read() -> None:
    stream = SyntheticStream([b"fake-sensitive-provider-error"])
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(403, stream=stream)
        )
    ) as client:
        with pytest.raises(YahooFantasyError, match="HTTP 403"):
            YahooFantasyClient(http_client=client).list_my_hockey_leagues(
                SecretStr("fake-token")
            )
    assert stream.read_count == 0 and stream.closed
