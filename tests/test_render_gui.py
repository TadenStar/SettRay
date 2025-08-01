import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sett_render_gui_v02_FULL_NO_DOTS import BlenderRenderGUI, SegmentedProgressBar

class DummyVar:
    def __init__(self, value):
        self._value = value
    def get(self):
        return self._value

def test_parse_frame_range_success():
    gui = BlenderRenderGUI.__new__(BlenderRenderGUI)
    gui.blender_path = DummyVar('blender')
    gui.project_path = DummyVar('project.blend')

    result = SimpleNamespace(stdout='START:5,END:15')
    with patch('subprocess.run', return_value=result) as run:
        start, end = BlenderRenderGUI.parse_frame_range(gui)
        assert (start, end) == (5, 15)
        run.assert_called_once()

def test_parse_frame_range_failure():
    gui = BlenderRenderGUI.__new__(BlenderRenderGUI)
    gui.blender_path = DummyVar('blender')
    gui.project_path = DummyVar('project.blend')

    with patch('subprocess.run', side_effect=Exception):
        start, end = BlenderRenderGUI.parse_frame_range(gui)
        assert (start, end) == (1, 100)

def test_segmented_progress_bar_bounds():
    bar = object.__new__(SegmentedProgressBar)
    bar.segments = 20
    bar.progress = 0
    bar._draw = lambda: None

    SegmentedProgressBar.set(bar, 150)
    assert bar.progress == 100

    SegmentedProgressBar.set(bar, -10)
    assert bar.progress == 0

def test_gradient_color_format():
    bar = object.__new__(SegmentedProgressBar)
    color = SegmentedProgressBar._gradient_color(bar, 0.5)
    assert color.startswith('#') and len(color) == 7
