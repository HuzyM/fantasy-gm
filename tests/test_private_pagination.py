"""Final-page navigation with fabricated rows; no provider access."""

import pytest

from fantasy_gm import verify_nhl
from fantasy_gm.providers.yahoo.contract_verifier import SelectionCancelled


@pytest.mark.parametrize(
    "row_count,actions,visits",
    [
        (1, ("NEXT",), (1,)),
        (13, ("NEXT", "BACK", "NEXT", "NEXT"), (2, 2)),
        (25, ("NEXT", "NEXT", "BACK", "BACK", "NEXT", "NEXT", "NEXT"), (2, 3, 2)),
    ],
)
def test_visible_navigation_remains_available_on_every_page(
    capsys: pytest.CaptureFixture[str],
    row_count: int,
    actions: tuple[str, ...],
    visits: tuple[int, ...],
) -> None:
    answers = iter(actions)
    verify_nhl._show(
        tuple(f"Synthetic row {i}" for i in range(row_count)),
        read_input=lambda _: next(answers),
    )
    assert next(answers, None) is None, "Final page must consume NEXT"
    output = capsys.readouterr().out
    for page, count in enumerate(visits):
        assert output.count(f"Synthetic row {page * 12}\n") == count


def test_final_page_invalid_input_retries_without_losing_position(
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(["NEXT", "mistyped", "", "BACK", "NEXT", "NEXT"])
    verify_nhl._show(
        tuple(f"Synthetic row {i}" for i in range(13)),
        read_input=lambda _: next(answers),
    )
    assert next(answers, None) is None
    output = capsys.readouterr().out
    assert output.count("Synthetic row 0\n") == 2
    assert output.count("Synthetic row 12\n") == 2
    assert output.count("Invalid action") == 2


@pytest.mark.parametrize("row_count", [1, 13, 25])
def test_cancel_on_final_page_exits_safely(row_count: int) -> None:
    answers = iter(["NEXT"] * ((row_count - 1) // 12) + ["CANCEL"])
    with pytest.raises(SelectionCancelled):
        verify_nhl._show(
            tuple(f"Synthetic row {i}" for i in range(row_count)),
            read_input=lambda _: next(answers),
        )


@pytest.mark.parametrize("allow_back", [False, True])
def test_first_page_back_preserves_navigation_boundary(allow_back: bool) -> None:
    answers = iter(["BACK", "NEXT"])
    if allow_back:
        with pytest.raises(verify_nhl._BackRequested):
            verify_nhl._show(
                ("Synthetic row",),
                read_input=lambda _: next(answers),
                allow_back=True,
            )
        assert next(answers) == "NEXT"
    else:
        verify_nhl._show(("Synthetic row",), read_input=lambda _: next(answers))
        assert next(answers, None) is None


def test_wrapped_32_team_selector_finishes_pagination_before_numeric_selection(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Each 80-character option wraps into two rows; title + 64 rows = six pages.
    options = tuple(f"Synthetic team {i:02d} " + "x" * 62 for i in range(1, 33))
    actions = iter(["NEXT"] * 5 + ["BACK", "NEXT", "NEXT"])
    prompts: list[str] = []

    def read(prompt: str) -> str:
        if "Selection number" in prompt:
            assert next(actions, None) is None, "Selection started before final NEXT"
            prompts.append("selection")
            return "32"
        prompts.append("navigation")
        return next(actions)

    assert verify_nhl._choose("Synthetic catalogue", options, read_input=read) == 31
    assert prompts == ["navigation"] * 8 + ["selection"]
    output = capsys.readouterr().out
    assert output.count("32: Synthetic team 32") == 2


@pytest.mark.parametrize("row_count", [1, 13, 25])
def test_legacy_hidden_pagination_does_not_prompt_on_final_page(
    monkeypatch: pytest.MonkeyPatch, row_count: int
) -> None:
    prompts: list[str] = []

    def read(prompt: str) -> str:
        prompts.append(prompt)
        return "NEXT"

    monkeypatch.setattr(verify_nhl, "_read_hidden_input", read)
    verify_nhl._show(tuple(f"Synthetic row {i}" for i in range(row_count)))
    assert len(prompts) == (row_count - 1) // 12
