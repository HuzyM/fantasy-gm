"""The private wakeup pair never relaxes denial for another thread/socket."""

import socket
import threading

import pytest

from tests import conftest as guards


def test_unrelated_connections_denied_during_wakeup_connect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    in_connect = threading.Event()
    release = threading.Event()
    original_connect = guards._WAKEUP_CONNECT
    denied_connect = socket.socket.connect
    pairs: list[tuple[socket.socket, socket.socket]] = []
    failures: list[BaseException] = []

    def paused_connect(client: socket.socket, address: tuple[str, int]) -> None:
        in_connect.set()
        assert release.wait(5.0), "Regression test did not release wakeup connection"
        original_connect(client, address)

    def create_pair() -> None:
        try:
            pairs.append(socket.socketpair())
        except BaseException as error:
            failures.append(error)

    monkeypatch.setattr(guards, "_WAKEUP_CONNECT", paused_connect)
    worker = threading.Thread(target=create_pair, daemon=True)
    worker.start()
    try:
        assert in_connect.wait(5.0), "Wakeup connection did not start"
        assert socket.socket.connect is denied_connect
        # Port zero prevents an external request even if this guard regresses.
        with socket.socket() as unrelated:
            with pytest.raises(AssertionError, match="Live network"):
                unrelated.connect(("127.0.0.1", 0))
            with pytest.raises(AssertionError, match="Live network"):
                unrelated.connect_ex(("127.0.0.1", 0))
        with pytest.raises(AssertionError, match="Live network"):
            socket.getaddrinfo("example.test", 443)
    finally:
        release.set()
        worker.join(5.0)
        for server, client in pairs:
            server.close()
            client.close()
    assert not worker.is_alive() and not failures
    assert len(pairs) == 1
    assert socket.socket.connect is denied_connect


def test_wakeup_pair_is_connected_and_ordinary_localhost_remains_denied() -> None:
    left, right = socket.socketpair()
    try:
        left.sendall(b"fake-wakeup")
        assert right.recv(11) == b"fake-wakeup"
        assert left.getpeername() == right.getsockname()
    finally:
        left.close()
        right.close()
    with socket.socket() as unrelated:
        with pytest.raises(AssertionError, match="Live network"):
            unrelated.connect(("127.0.0.1", 0))
