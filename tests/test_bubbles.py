from comicforge.bubbles import _wrap, bubble, bubble_size, text_width


def test_wrap_breaks_on_max_chars():
    lines = _wrap("one two three four", 8)
    assert all(len(line) <= 8 for line in lines)
    assert " ".join(lines).split() == ["one", "two", "three", "four"]


def test_wrap_empty_string():
    assert _wrap("", 10) == [""]


def test_bubble_escapes_text():
    svg = bubble("a < b & c", 100, 100)
    assert "&lt;" in svg and "&amp;" in svg
    assert "a < b" not in svg


def test_bubble_kinds_render():
    speech = bubble("hi", 50, 50, kind="speech")
    thought = bubble("hmm", 50, 50, kind="thought")
    shout = bubble("HEY", 50, 50, kind="shout")
    assert speech.startswith("<g>") and speech.endswith("</g>")
    assert "<rect" in speech
    assert "<ellipse" in thought
    assert "<polygon" in shout


def test_bubble_tail_only_when_target_given():
    assert "<path" not in bubble("hi", 50, 50)
    assert "<path" in bubble("hi", 50, 50, tail=[10, 10])


def test_caps_measure_wider_than_lowercase():
    assert text_width("HELLO", 16) > text_width("hello", 16)
    assert bubble_size("HELLO THERE")[0] > bubble_size("hello there")[0]


def test_tail_exits_edge_facing_target():
    below = bubble("hi", 100, 100, tail=[100, 300])
    above = bubble("hi", 100, 100, tail=[100, -100])
    ty = lambda svg: float(svg.split('<path d="M')[1].split()[1])  # noqa: E731
    assert ty(below) > 100 > ty(above)


def test_em_scales_measured_width():
    wide, _ = bubble_size("hello there wide", style={"em": 1.0})
    narrow, _ = bubble_size("hello there wide", style={"em": 0.8})
    assert narrow < wide


def test_tail_exits_side_edge_for_lateral_target():
    # target far to the right, level with the bubble: the tail must leave the
    # right edge, not the top or bottom
    svg = bubble("hi", 100, 100, tail=[400, 100])
    path = svg.split('<path d="M')[1].split('"')[0]
    # base points share the exit x; the tip is further right than either
    pts = [tuple(map(float, seg.split())) for seg in path.replace("Z", "").split("L")]
    (ax, ay), (tipx, _tipy), (bx2, by2) = pts
    assert tipx > ax and tipx > bx2
    assert abs(ay - by2) > 5  # base spans vertically, i.e. lies on a side edge
