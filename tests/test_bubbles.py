from comicforge.bubbles import _wrap, bubble


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
