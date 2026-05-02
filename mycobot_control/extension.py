import omni.ext

from .logger import configure_logging, get_logger
from .robot import MyCobotRobot
from .ui import MyCobotControlWindow

_log = get_logger("ext")


class MyCobotControlExtension(omni.ext.IExt):
    def on_startup(self, ext_id: str):
        configure_logging("info")
        _log.info(f"Starting extension: {ext_id}")
        self._robot = MyCobotRobot()
        self._window = MyCobotControlWindow(self._robot)
        _log.info("UI window 'MyCobot Control' created.")

    def on_shutdown(self):
        _log.info("Shutting down extension.")
        if getattr(self, "_window", None) is not None:
            self._window.destroy()
            self._window = None
        self._robot = None
