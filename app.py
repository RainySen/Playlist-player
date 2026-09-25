import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from core import bootstrap, config
from core.config import AppPaths
from core.logging_setup import setup_logging


def _icon_path(paths: AppPaths) -> str:
    bundled = os.path.join(getattr(sys, "_MEIPASS", paths.base_dir), "icon.ico")
    return bundled if os.path.exists(bundled) else os.path.join(paths.base_dir, "icon.ico")


def main() -> int:
    paths = AppPaths.detect()
    paths.ensure_dirs()
    setup_logging(paths)

    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    icon = QIcon(_icon_path(paths))
    ui = bootstrap.build(paths, icon)
    app.aboutToQuit.connect(ui.shutdown)
    ui.window.closed.connect(app.quit)
    ui.window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
