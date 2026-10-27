"""Test del mixing e dei nomi colore (funzioni pure, nessuna finestra)."""
import itertools
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.color_mixing import Mode, kinds, mix  # noqa: E402
from game.color_names import EMPTY_NAME, color_name  # noqa: E402


def name(mode: Mode, counts) -> str:
    return color_name(mode, mix(mode, counts))


# --- Pittura: dosi (rosso, giallo, blu) ---------------------------------
@pytest.mark.parametrize(
    "counts, expected",
    [
        ((1, 0, 0), "Rosso"),
        ((0, 1, 0), "Giallo"),
        ((0, 0, 1), "Blu"),
        ((1, 1, 0), "Arancione"),
        ((0, 1, 1), "Verde"),
        ((1, 0, 1), "Viola"),
        ((1, 1, 1), "Marrone"),
        ((3, 3, 0), "Arancione"),
        ((2, 2, 2), "Marrone"),
    ],
)
def test_paint_names(counts, expected):
    assert name(Mode.PAINT, counts) == expected


# --- Luce: dosi (rosso, verde, blu) --------------------------------------
@pytest.mark.parametrize(
    "counts, expected",
    [
        ((1, 0, 0), "Rosso"),
        ((0, 1, 0), "Verde"),
        ((0, 0, 1), "Blu"),
        ((1, 1, 0), "Giallo"),
        ((0, 1, 1), "Ciano"),
        ((1, 0, 1), "Magenta"),
        ((1, 1, 1), "Bianco"),
        ((3, 3, 3), "Bianco"),
    ],
)
def test_light_names(counts, expected):
    assert name(Mode.LIGHT, counts) == expected


def test_empty_cauldron_has_no_colour():
    for mode in Mode:
        assert mix(mode, (0, 0, 0)) is None
        assert color_name(mode, None) == EMPTY_NAME


def test_mix_depends_only_on_proportions():
    for mode in Mode:
        assert mix(mode, (1, 2, 0)) == mix(mode, (3, 6, 0))


def test_light_white_is_pure_white():
    assert mix(Mode.LIGHT, (2, 2, 2)) == (255, 255, 255)


def test_more_red_gives_redder_orange():
    """Più rosso che giallo -> arancione più rosso (canale verde più basso)."""
    reddish = mix(Mode.PAINT, (3, 1, 0))
    yellowish = mix(Mode.PAINT, (1, 3, 0))
    assert reddish[1] < yellowish[1]


def test_every_combination_up_to_10_doses_is_valid():
    """Nessuna combinazione (<= 10 dosi) deve dare errori o canali fuori range."""
    for mode in Mode:
        for counts in itertools.product(range(11), repeat=3):
            if sum(counts) > 10:
                continue
            rgb = mix(mode, counts)
            if sum(counts) == 0:
                assert rgb is None
                continue
            assert all(0 <= c <= 255 for c in rgb)
            assert color_name(mode, rgb) != EMPTY_NAME


def test_kinds():
    assert kinds((0, 0, 0)) == 0
    assert kinds((4, 0, 0)) == 1
    assert kinds((1, 0, 3)) == 2


def test_wrong_length_raises():
    with pytest.raises(ValueError):
        mix(Mode.PAINT, (1, 2))
