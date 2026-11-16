"""The dwinui command line.

These exist because the commands are referenced from documentation, a skill
and an SVG description. A command that silently stops working takes the whole
screen workflow with it, and nothing else would notice.
"""

from __future__ import annotations

import pytest
from dwinui.__main__ import main

SCREEN = "ui/screens/dro.svg"


@pytest.fixture
def screen(tmp_path):
    """A valid minimal screen on disk."""
    path = tmp_path / "test.svg"
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="272" '
        'data-background="#000">'
        '<rect x="0" y="0" width="40" height="20" fill="#fff"/>'
        '<text x="0" y="40" font-size="16" fill="#fff">HI</text>'
        "</svg>",
        encoding="utf-8",
    )
    return path


class TestCheck:
    def test_check_passes_on_the_committed_screens(self, capsys):
        assert main(["check"]) == 0
        assert "draw calls" in capsys.readouterr().out


class TestPreview:
    def test_writes_an_svg_beside_the_source(self, screen):
        assert main(["preview", str(screen)]) == 0
        assert screen.with_suffix(".preview.svg").exists()

    def test_honours_an_explicit_output(self, screen, tmp_path):
        out = tmp_path / "elsewhere.svg"
        assert main(["preview", str(screen), "-o", str(out)]) == 0
        assert out.read_text(encoding="utf-8").startswith("<svg")


class TestOps:
    def test_lists_the_draw_calls(self, screen, capsys):
        assert main(["ops", str(screen)]) == 0
        out = capsys.readouterr().out
        assert "clear" in out
        assert "draw calls" in out


class TestExport:
    def test_emits_an_importable_module(self, screen, tmp_path):
        out = tmp_path / "scr.py"
        assert main(["export", str(screen), "-o", str(out)]) == 0
        source = out.read_text(encoding="utf-8")
        assert "DO NOT EDIT" in source
        assert "def draw(panel):" in source

    def test_exported_module_replays_onto_a_panel(self, screen, tmp_path):
        """The exported module must actually drive a display-shaped object.

        Catches the real risk: an op whose name does not match a method on
        T5UIC1Display would fail only on the device, with the panel simply
        staying blank.
        """
        out = tmp_path / "scr.py"
        main(["export", str(screen), "-o", str(out)])

        namespace: dict = {}
        exec(compile(out.read_text(encoding="utf-8"), str(out), "exec"), namespace)  # noqa: S102

        calls = []

        class FakePanel:
            def __getattr__(self, name):
                def record(*args):
                    calls.append((name, args))
                return record

        namespace["draw"](FakePanel())
        assert [c[0] for c in calls] == [op[0] for op in namespace["OPS"]]
        assert calls, "exported screen drew nothing"

    def test_exported_methods_exist_on_the_real_driver_surface(self, screen, tmp_path):
        """Every emitted method must be one the T5UIC1 driver actually has."""
        known = {
            "clear", "draw_point", "draw_points", "draw_line", "draw_polyline",
            "draw_rectangle", "draw_circle", "fill_circle", "draw_text",
            "draw_text_bytes", "draw_bitmap", "move_area",
        }
        out = tmp_path / "scr.py"
        main(["export", str(screen), "-o", str(out)])
        namespace: dict = {}
        exec(compile(out.read_text(encoding="utf-8"), str(out), "exec"), namespace)  # noqa: S102
        for method, _args in namespace["OPS"]:
            assert method in known, f"{method} is not a T5UIC1Display method"


class TestFailureModes:
    def test_a_broken_screen_exits_nonzero(self, tmp_path):
        bad = tmp_path / "bad.svg"
        bad.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="272">'
            '<path d="M0 0"/></svg>',
            encoding="utf-8",
        )
        assert main(["ops", str(bad)]) == 2

    def test_a_missing_file_exits_nonzero(self, tmp_path):
        assert main(["ops", str(tmp_path / "nope.svg")]) == 2
