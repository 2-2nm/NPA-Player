import sys

from PySide6.QtWidgets import QApplication

from app import config
from ui import theme
from ui.logo import app_icon
from ui.shell.main_window import MainWindow


def main():
    if sys.platform == "win32":
        # without its own AppUserModelID Windows groups the taskbar button under python.exe and shows its icon
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(config.APP_USER_MODEL_ID)
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setWindowIcon(app_icon())  # window, taskbar and Alt+Tab
    theme.load_fonts()
    app.setFont(theme.font(13))
    theme.set_accent(config.new_settings().value("appearance/accent", theme.DEFAULT_ACCENT))  # chosen in Settings
    app.setStyleSheet(theme.style())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
