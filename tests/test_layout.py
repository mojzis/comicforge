import pytest

from comicforge import bubble_layout
from comicforge.bubbles import Tail, bubble, tail_from, tail_geometry, tail_look
from comicforge.cli import main
from comicforge.layout import layout_bubbles, speaker_points
from comicforge.render import build_svg
from comicforge.validate import check_spec, validate_spec


def _page(panel, **top):
    return {
        "page": [200, 150],
        "px_per_mm": 2,
        "margin_mm": 0,
        "rows": [{"panels": [panel]}],
        **top,
    }


def _two_hander(**extra):
    return {
        "speakers": {"ema": [0.8, 0.55], "jan": [0.2, 0.6]},
        "bubbles": [
            {"text": "Ahoj, jak se máš?", "speaker": "ema", **extra},
            {"text": "Dobře, díky.", "speaker": "jan", **extra},
        ],
    }


def test_speaker_point_aims_the_tail():
    panel = {
        "speakers": {"ema": [0.7, 0.6]},
        "bubbles": [{"text": "a", "speaker": "ema"}],
    }
    [b] = bubble_layout(_page(panel))["bubbles"]
    assert b["tail"]["target"] == [0.7, 0.6]


def test_to_overrides_the_speaker_point():
    panel = {
        "speakers": {"ema": [0.7, 0.6]},
        "bubbles": [{"text": "a", "speaker": "ema", "to": [0.1, 0.9]}],
    }
    [b] = bubble_layout(_page(panel))["bubbles"]
    assert b["tail"]["target"] == [0.1, 0.9]


def test_actor_wins_over_a_speaker_point_of_the_same_name():
    panel = {
        "speakers": {"tom": [0.9, 0.9]},
        "actors": [{"char": "tom", "x": 0.3, "y": 0.6, "scale": 0.5}],
    }
    assert speaker_points(panel)["tom"] == pytest.approx((0.3, 0.6 - 0.5 * 0.42))


def test_right_hand_first_speaker_goes_top_right_and_reply_lower_left():
    first, reply = bubble_layout(_page(_two_hander()))["bubbles"]
    assert first["center"][0] > 0.5 > reply["center"][0]
    half = 0.5 * (first["box"][3] - first["box"][1])
    assert reply["box"][1] >= first["box"][1] + half - 1e-3


def test_reading_order_holds_for_a_same_side_exchange():
    panel = {
        "speakers": {"ema": [0.3, 0.8], "jan": [0.35, 0.85]},
        "bubbles": [
            {"text": "Jedna", "speaker": "ema"},
            {"text": "Dvě", "speaker": "jan"},
            {"text": "Tři", "speaker": "ema"},
        ],
    }
    tops = [b["box"][1] for b in bubble_layout(_page(panel))["bubbles"]]
    assert tops == sorted(tops) and len(set(tops)) == 3


def test_reading_placed_bubbles_avoid_speakers_and_crossing_tails():
    assert bubble_layout(_page(_two_hander()))["warnings"] == []


def test_placement_marks_only_reading_order_bubbles_auto():
    panel = _two_hander()
    panel["bubbles"][1]["at"] = "bl"
    auto = [b["auto"] for b in bubble_layout(_page(panel))["bubbles"]]
    assert auto == [True, False]


def test_panels_without_speakers_keep_the_old_layout(library):
    panel = {
        "actors": [{"char": "tom", "x": 0.7}],
        "bubbles": [{"text": "a", "speaker": "tom"}, {"text": "b"}],
    }
    placed = layout_bubbles(panel, 0, 0, 400, 300)
    assert [p.auto for p in placed] == [False, False]
    assert placed[0].centre[0] == pytest.approx(0.7 * 400)
    assert placed[1].centre[0] == pytest.approx(200)


def test_bubble_layout_excludes_the_caption_band():
    panel = {"caption": "Pod čarou.", "speakers": {"ema": [0.5, 1.0]}, "bubbles": []}
    out = bubble_layout(_page(panel))
    assert out["height"] < 300
    assert out["width"] == 400


def test_bubble_layout_rejects_a_missing_panel():
    with pytest.raises(ValueError, match="no panel"):
        bubble_layout(_page({}), row=3)


def test_tail_from_normalises_every_form():
    assert tail_from("r") == ("r", None)
    assert tail_from(0.25) == (None, 0.25)
    assert tail_from({"edge": "t", "pos": 1}) == ("t", 1)
    assert tail_from(None) == (None, None)


@pytest.mark.parametrize("bad", ["x", 1.5, True, {"side": "l"}, [1, 2]])
def test_tail_from_rejects_nonsense(bad):
    with pytest.raises(ValueError):
        tail_from(bad)


def test_tail_from_pins_edge_and_position():
    geom = tail_geometry(
        100, 100, 80, 40, (100, 300), {"tail_from": {"edge": "l", "pos": 0.25}}
    )
    assert geom.edge == "l"
    assert geom.start == pytest.approx((60, 90))


def test_tail_from_edge_alone_slides_toward_the_target():
    geom = tail_geometry(100, 100, 80, 40, (400, 100), {"tail_from": "t"})
    assert geom.start == pytest.approx((124, 80))  # nudged right, capped at 0.3 w


def test_default_tail_geometry_is_unchanged():
    geom = tail_geometry(100, 100, 80, 40, (100, 300))
    assert (geom.edge, geom.start) == ("b", (100, 120))
    assert geom.tip == pytest.approx((100, 120 + 46))


def test_line_tail_runs_to_the_gap_before_the_target():
    geom = tail_geometry(100, 100, 80, 40, (100, 300), {"tail": "line", "tail_gap": 10})
    assert geom.tip == pytest.approx((100, 290))


def test_line_tail_draws_a_halo_under_the_body():
    svg = bubble("hi", 100, 100, tail=(100, 300), style={"tail": "line"})
    halo, rest = svg.split("<rect", 1)
    assert 'stroke="#ffffff"' in halo
    assert 'stroke="#21304a"' in rest and "stroke-linecap" in rest


def test_thought_line_tail_is_a_trail_of_dots():
    svg = bubble(
        "hmm", 100, 100, tail=(100, 300), kind="thought", style={"tail": "line"}
    )
    assert svg.count("<circle") > 10


def test_curve_tail_reaches_further_than_a_wedge():
    wedge = tail_geometry(100, 100, 80, 40, (100, 300))
    curve = tail_geometry(100, 100, 80, 40, (100, 300), {"tail": "curve"})
    assert curve.tip[1] > wedge.tip[1]


def test_positive_bend_bows_right_of_the_direction_of_travel():
    geom = Tail("b", (0, 0), (0, 100), (0, 120), "curve", 1.0)
    assert geom.control == pytest.approx((-50, 50))  # heading down: right is -x
    assert geom.point(0) == (0, 0)
    assert geom.point(1) == pytest.approx((0, 100))


def test_wedge_ignores_bend():
    geom = tail_geometry(100, 100, 80, 40, (100, 300), {"tail_bend": 1})
    assert geom.bend == 0


def test_curve_tail_is_outlined_under_the_body_and_filled_over_it():
    svg = bubble(
        "hi", 100, 100, tail=(100, 300), style={"tail": "curve", "tail_bend": 0.5}
    )
    under, rest = svg.split("<rect", 1)
    assert " Q" in under and 'stroke-width="6.00"' in under
    assert 'stroke="none"' in rest


def test_thought_keeps_its_circles_on_a_curve():
    svg = bubble(
        "hmm", 100, 100, tail=(100, 300), kind="thought", style={"tail": "curve"}
    )
    assert svg.count("<circle") == 3


def test_tail_none_draws_and_lays_out_no_tail():
    panel = {
        "speakers": {"ema": [0.7, 0.6]},
        "bubbles": [{"text": "a", "speaker": "ema", "tail": "none"}],
    }
    [b] = bubble_layout(_page(panel))["bubbles"]
    assert b["tail"] is None
    assert "<path" not in bubble("a", 10, 10, tail=(50, 50), style={"tail": "none"})


def _side(tail, point):
    (sx, sy), (tx, ty) = tail["start"], tail["tip"]
    return (tx - sx) * (point[1] - sy) - (ty - sy) * (point[0] - sx)


def test_auto_bend_bows_tails_away_from_the_neighbouring_bubble():
    panel = {
        "speakers": {"ema": [0.45, 0.9], "jan": [0.55, 0.9]},
        "bubbles": [
            {"text": "a", "speaker": "ema", "at": "tl", "tail": "curve"},
            {"text": "b", "speaker": "jan", "at": "tr", "tail": "line"},
        ],
    }
    left, right = bubble_layout(_page(panel))["bubbles"]
    for me, other in ((left, right), (right, left)):
        assert (
            _side(me["tail"], me["tail"]["control"])
            * _side(me["tail"], other["center"])
            < 0
        )


def test_explicit_bend_wins_over_auto():
    panel = {
        "speakers": {"ema": [0.5, 0.9]},
        "bubbles": [{"text": "a", "speaker": "ema", "tail": "line", "tail_bend": -1}],
    }
    [b] = bubble_layout(_page(panel))["bubbles"]
    assert b["tail"]["bend"] == -1


@pytest.mark.parametrize(
    "bad", [{"tail": "zigzag"}, {"tail_bend": 2}, {"tail_bend": "x"}]
)
def test_tail_look_rejects_nonsense(bad):
    with pytest.raises(ValueError):
        tail_look(bad)


def test_per_bubble_tail_overrides_page_style(library):
    panel = {
        "speakers": {"ema": [0.5, 0.9]},
        "bubbles": [{"text": "a", "speaker": "ema", "tail": "wedge"}],
    }
    svg = build_svg(_page(panel, bubble_style={"tail": "line"}), library=library)
    assert "stroke-linecap" not in svg


def test_validate_accepts_speaker_point_names(library):
    assert validate_spec(_page(_two_hander()), library=library) == []


def test_validate_flags_bad_speakers_and_tail_keys(library):
    panel = {
        "speakers": {"ema": [0.5]},
        "bubbles": [
            {"text": "a", "speaker": "nobody", "tail": "zigzag", "tail_from": "x"},
            {"text": "b", "tail_bend": 1.5},
        ],
    }
    problems = validate_spec(_page(panel), library=library)
    assert len(problems) == 5


def test_warns_on_reading_order(library):
    panel = {"bubbles": [{"text": "druhá", "at": "bl"}, {"text": "první", "at": "tl"}]}
    [warning] = check_spec(_page(panel), library=library).warnings
    assert "out of reading order" in warning


def test_warns_on_level_bubbles_read_right_to_left(library):
    panel = {"bubbles": [{"text": "b", "at": "tr"}, {"text": "a", "at": "tl"}]}
    [warning] = check_spec(_page(panel), library=library).warnings
    assert "left of it" in warning


def test_warns_on_crossing_tails(library):
    panel = {
        "speakers": {"ema": [0.9, 0.9], "jan": [0.9, 0.1]},
        "bubbles": [
            {"text": "a", "at": "tl", "speaker": "ema"},
            {"text": "b", "at": "bl", "speaker": "jan"},
        ],
    }
    warnings = check_spec(_page(panel), library=library).warnings
    assert any("cross" in w for w in warnings)


def test_warns_on_a_bubble_covering_a_speaker(library):
    panel = {
        "speakers": {"ema": [0.5, 0.5]},
        "bubbles": [{"text": "a", "x": 0.5, "y": 0.5}],
    }
    [warning] = check_spec(_page(panel), library=library).warnings
    assert "covers speaker 'ema'" in warning


def test_cli_passes_warnings_unless_strict(tmp_path, library):
    spec = tmp_path / "warn.yaml"
    spec.write_text(
        f"library: {library.root}\n"
        "rows:\n  - panels:\n      - bubbles:\n"
        "          - {text: b, at: bl}\n          - {text: a, at: tl}\n"
    )
    assert main(["validate", str(spec)]) == 0
    assert main(["validate", str(spec), "--strict"]) == 1
