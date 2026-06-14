from comicforge.render import render_spec
from comicforge.scaffold import init_project, skill_src


def test_init_creates_renderable_project(tmp_path):
    dest = tmp_path / "proj"
    created = init_project(dest)

    # the four asset dirs, starter page, seed sprite, readme, gitignore all exist
    for d in ("characters", "scenes", "pixel", "pages"):
        assert (dest / d).is_dir()
    page = dest / "pages" / "hello.yaml"
    assert page.is_file()
    assert (dest / "pixel" / "heart.yaml").is_file()
    assert (dest / "README.md").is_file()
    assert (dest / ".gitignore").is_file()
    assert page in created

    # the starter page renders with no hand-authored art
    out = tmp_path / "hello.png"
    render_spec(page, out)
    assert out.stat().st_size > 0


def test_init_bundles_the_skill(tmp_path):
    # skill_src resolves (source tree in dev, wheel data when installed)
    assert skill_src() is not None
    dest = tmp_path / "proj"
    init_project(dest)
    skill = dest / ".claude" / "skills" / "comicforge"
    assert (skill / "SKILL.md").is_file()
    assert (skill / "reference.md").is_file()


def test_init_is_idempotent_and_force_overwrites(tmp_path):
    dest = tmp_path / "proj"
    init_project(dest)

    # hand-edit a scaffolded file; a plain re-run must not clobber it
    page = dest / "pages" / "hello.yaml"
    page.write_text("title: mine\n", encoding="utf-8")
    second = init_project(dest)
    assert second == []  # nothing rewritten
    assert page.read_text(encoding="utf-8") == "title: mine\n"

    # --force restores the scaffolded content
    forced = init_project(dest, force=True)
    assert page in forced
    assert "ComicForge" in page.read_text(encoding="utf-8")
