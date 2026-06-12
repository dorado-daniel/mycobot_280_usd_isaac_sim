import omni.ui as ui

from . import logger
from .logger import get_logger
from .robot import MyCobotRobot

_log = get_logger("ui")

_LEVEL_COLORS = {
    "info": 0xFFCCCCCC,
    "warn": 0xFF55CCFF,  # ABGR -> light orange/yellow
    "error": 0xFF5555FF,  # red-ish
}
_MAX_PANEL_LINES = 500


class LogPanel:
    """A scrollable read-only text area that mirrors the extension log."""

    def __init__(self) -> None:
        self._lines: list[tuple[str, str]] = []
        self._labels_stack: ui.VStack | None = None
        self._scroll: ui.ScrollingFrame | None = None
        self._unsubscribe = None

    def build(self) -> None:
        with ui.CollapsableFrame("Log", height=220, collapsed=False):
            with ui.VStack(spacing=4):
                with ui.HStack(height=0):
                    ui.Spacer()
                    ui.Button("Clear", width=60, clicked_fn=self._on_clear)
                self._scroll = ui.ScrollingFrame(
                    horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                    vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_ON,
                )
                with self._scroll:
                    self._labels_stack = ui.VStack(spacing=0)

        for level, line in logger.get_history():
            self._append(level, line, scroll=False)
        self._scroll_to_bottom()

        if self._unsubscribe is None:
            self._unsubscribe = logger.subscribe(self._on_log_event)

    def _on_log_event(self, level: str, line: str) -> None:
        self._append(level, line, scroll=True)

    def _append(self, level: str, line: str, scroll: bool) -> None:
        self._lines.append((level, line))
        if len(self._lines) > _MAX_PANEL_LINES:
            self._rebuild_all()
        elif self._labels_stack is not None:
            with self._labels_stack:
                ui.Label(
                    line,
                    word_wrap=True,
                    style={"color": _LEVEL_COLORS.get(level, 0xFFCCCCCC)},
                )
        if scroll:
            self._scroll_to_bottom()

    def _rebuild_all(self) -> None:
        self._lines = self._lines[-_MAX_PANEL_LINES:]
        if self._labels_stack is None:
            return
        self._labels_stack.clear()
        with self._labels_stack:
            for level, line in self._lines:
                ui.Label(
                    line,
                    word_wrap=True,
                    style={"color": _LEVEL_COLORS.get(level, 0xFFCCCCCC)},
                )

    def _scroll_to_bottom(self) -> None:
        if self._scroll is not None:
            try:
                self._scroll.scroll_y = self._scroll.scroll_y_max
            except Exception:
                pass

    def _on_clear(self) -> None:
        self._lines.clear()
        if self._labels_stack is not None:
            self._labels_stack.clear()

    def destroy(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        self._labels_stack = None
        self._scroll = None


class MyCobotControlWindow(ui.Window):
    def __init__(self, robot: MyCobotRobot):
        super().__init__("MyCobot Control", width=480, height=420)
        self._robot = robot
        self._log_panel = LogPanel()
        self.frame.set_build_fn(self._build_ui)

    def _build_ui(self):
        with ui.VStack(spacing=8):
            ui.Label(f"Robot root: {self._robot.robot_root_path}", height=0)
            with ui.HStack(spacing=8, height=0):
                ui.Button("Validate Robot", clicked_fn=self._on_validate)
                ui.Button("Print Joints", clicked_fn=self._on_print_joints)

            ui.Spacer(height=4)
            ui.Label("Gripper", height=0)
            with ui.HStack(spacing=8, height=0):
                ui.Button("Open", clicked_fn=self._on_open)
                ui.Button("Close", clicked_fn=self._on_close)
                ui.Button("Neutral", clicked_fn=self._on_neutral)
            with ui.HStack(spacing=8, height=0):
                ui.Label("Closed", width=50)
                self._grip_slider = ui.FloatSlider(min=0.0, max=1.0)
                self._grip_slider.model.add_value_changed_fn(self._on_slider)
                ui.Label("Open", width=40)

            self._log_panel.build()

    def _on_validate(self):
        _log.info("--- Validate Robot (button clicked) ---")
        try:
            self._robot.validate()
        except Exception as exc:
            _log.error(f"validate() raised: {exc!r}")
            raise

    def _on_print_joints(self):
        _log.info("--- Print Joints (button clicked) ---")
        try:
            self._robot.list_joints()
        except Exception as exc:
            _log.error(f"list_joints() raised: {exc!r}")
            raise

    def _on_open(self):
        try:
            self._robot.open_gripper()
        except Exception as exc:
            _log.error(f"open_gripper() raised: {exc!r}")
            raise

    def _on_close(self):
        try:
            self._robot.close_gripper()
        except Exception as exc:
            _log.error(f"close_gripper() raised: {exc!r}")
            raise

    def _on_neutral(self):
        try:
            self._robot.set_gripper_target(0.0)
        except Exception as exc:
            _log.error(f"set_gripper_target() raised: {exc!r}")
            raise

    def _on_slider(self, model):
        try:
            self._robot.set_gripper_fraction(model.get_value_as_float())
        except Exception as exc:
            _log.error(f"set_gripper_fraction() raised: {exc!r}")
            raise

    def destroy(self):
        if self._log_panel is not None:
            self._log_panel.destroy()
            self._log_panel = None
        super().destroy()
