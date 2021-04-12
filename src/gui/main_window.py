
import logging
import os
import os.path
import pathlib
import sys
import traceback
import webbrowser
import zipfile
from datetime import datetime
from typing import Callable, List, Optional

import arrow
from PySide2.QtCore import QSettings, Qt, Signal
from PySide2.QtGui import QCloseEvent, QFont, QIcon, QKeySequence, QResizeEvent
from PySide2.QtWidgets import (QAction, QApplication, QDockWidget, QHBoxLayout,
                               QMainWindow, QMessageBox, QScrollArea,
                               QSizePolicy, QStyle, QTextBrowser, QWidget)

import model
from core import App, Constants
from twitch.component import ChatComponent

from .widgets import (ActiveComponentsWidget, AllComponentsWidget,
                      ComponentWidget, SettingsWidget)

gLogger = logging.getLogger(f"edobot.main")


class CallbackHandler(logging.Handler):
    def __init__(self, msg_callback: Optional[Callable[[logging.LogRecord], None]] = None):
        super().__init__()
        self.msg_callback = msg_callback

    def flush(self):
        self.acquire()
        self.release()

    def emit(self, record: logging.LogRecord):
        try:
            if self.msg_callback is not None:
                self.msg_callback(record)
            self.flush()
        except Exception:
            self.handleError(record)

    def setMessageCallback(self, msg_callback: Callable[[logging.LogRecord], None]):
        self.acquire()
        self.msg_callback = msg_callback
        self.release()


class LogWidget(QTextBrowser):
    logRecordReceived = Signal(logging.LogRecord)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.logRecordReceived.connect(self.append_record)  # type: ignore
        self.setLineWrapMode(QTextBrowser.LineWrapMode.NoWrap)
        self.horizontalScrollBar().sliderReleased.connect(self.hscroll_bar_released)  # type: ignore
        self.verticalScrollBar().sliderReleased.connect(self.vscroll_bar_released)  # type: ignore
        self.textChanged.connect(self.scroll_to_hstart)  # type: ignore
        self.setFont(QFont("Segoe UI", 9))
        self.user_set_hpos = 0
        self.attach_to_bottom = True

    def scroll_to_hstart(self):
        if self.user_set_hpos == 0:
            self.horizontalScrollBar().setValue(0)

    def hscroll_bar_released(self):
        self.user_set_hpos = self.horizontalScrollBar().value()

    def vscroll_bar_released(self):
        self.attach_to_bottom = self.verticalScrollBar().value() == self.verticalScrollBar().maximum()

    def resizeEvent(self, e: QResizeEvent) -> None:
        if self.attach_to_bottom:
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        return super().resizeEvent(e)

    def append_record(self, record: logging.LogRecord):
        msg = ""
        msg += f"<b>[{arrow.now().format('HH:mm:ss')}]</b>"
        if __debug__:
            msg += f" <b><i>{record.threadName}</i></b>"
        if record.levelno == logging.INFO:
            level_color = "orange"
        elif record.levelno == logging.ERROR:
            level_color = "red"
        else:
            level_color = "black"
        msg += f" <b><font color='{level_color}'>{record.levelname}</font></b>"
        msg += f" <i>{record.name}</i>"
        msg += f" - {record.msg}"
        self.append(msg)


class MainWindow(QMainWindow):
    edobotStarted = Signal()
    edobotStopped = Signal()
    hostConnected = Signal(model.User)
    botConnected = Signal(model.User)
    hostDisconnected = Signal()
    botDisconnected = Signal()
    componentAdded = Signal(ChatComponent)

    def __init__(self):
        super().__init__()

        self.settings = QSettings(QSettings.Format.NativeFormat, QSettings.Scope.UserScope,
                                  "Edoren", Constants.APP_NAME)

        self.setWindowTitle(f"{Constants.APP_NAME} {Constants.APP_VERSION}")
        self.setWindowIcon(QIcon(os.path.join(Constants.DATA_DIRECTORY, "icon.ico")))

        self.component_list = ActiveComponentsWidget()
        self.component_list.setMinimumSize(400, 200)
        self.setCentralWidget(self.component_list)

        self.create_actions()
        self.create_menus()
        self.create_status_bar()
        self.create_windows()

        handlers: List[logging.Handler] = []

        log_dir = os.path.join(Constants.SAVE_DIRECTORY, "logs")
        log_filename = "edobot-latest.log"

        # Create the log folder if it dooes not exists
        if not os.path.isdir(log_dir):
            os.makedirs(log_dir)

        # Compress the old log file
        log_file = os.path.join(log_dir, log_filename)
        if os.path.isfile(log_file):
            fname = pathlib.Path(log_file)
            modified_time = datetime.fromtimestamp(fname.stat().st_mtime)
            zip_file = os.path.join(log_dir, modified_time.strftime("edobot-%d-%m-%Y.zip"))
            zipfile.ZipFile(zip_file, mode="a", compression=zipfile.ZIP_BZIP2,
                            compresslevel=9).write(log_file, arcname=modified_time.strftime("%H-%M-%S-%f.log"))

        if __debug__:
            default_level = logging.DEBUG
        else:
            default_level = logging.INFO

        file_handler = logging.FileHandler(log_file, "w", "utf-8")
        file_handler.setLevel(default_level)
        file_handler.setFormatter(TimeFormatter(
            "[%(asctime)s] %(process)s %(threadName)s %(levelname)s %(name)s - %(message)s"))
        handlers.append(file_handler)

        stream_handler = CallbackHandler(self.log_widget.logRecordReceived.emit)  # type: ignore
        stream_handler.setLevel(logging.INFO)
        handlers.append(stream_handler)

        logging.basicConfig(level=default_level, handlers=handlers)

        self.app: App = App()
        self.app.started = self.edobotStarted.emit  # type: ignore
        self.edobotStarted.connect(self.edobot_started)  # type: ignore
        self.app.stopped = self.edobotStopped.emit  # type: ignore
        self.edobotStopped.connect(self.edobot_stopped)  # type: ignore
        self.app.component_added = self.componentAdded.emit  # type: ignore
        self.componentAdded.connect(self.add_component_widget)  # type: ignore
        self.app.host_connected = self.hostConnected.emit  # type: ignore
        self.hostConnected.connect(self.host_connected)  # type: ignore
        self.app.bot_connected = self.botConnected.emit  # type: ignore
        self.botConnected.connect(self.bot_connected)  # type: ignore
        self.app.host_disconnected = self.hostDisconnected.emit  # type: ignore
        self.hostDisconnected.connect(self.host_disconnected)  # type: ignore
        self.app.bot_disconnected = self.botDisconnected.emit  # type: ignore
        self.botDisconnected.connect(self.bot_disconnected)  # type: ignore
        self.app.start()

        self.last_clicked_component = None

        self.component_list.componentDropped.connect(self.add_component)  # type: ignore
        self.component_list.componentRemoved.connect(self.remove_component)  # type: ignore
        self.component_list.componentClicked.connect(self.component_clicked)  # type: ignore

        for comp_instance in self.app.get_active_components().values():
            self.add_component_widget(comp_instance)

        for comp_type in self.app.get_available_components().values():
            self.avaiable_comps_widget.add_component(comp_type.get_id(), comp_type.get_name(),
                                                     comp_type.get_description())

        self.read_settings()

    def about(self):
        text = ("EdoBot is an open source tool to create Twitch components that interacts with the chat."
                "<br><br>"
                "Please go to <a href='https://github.com/edoren/EdoBot'>github.com/edoren/EdoBot</a> for more info."
                "<br><br>"
                "Download latest release <a href='https://github.com/edoren/edobot/releases/latest'>here</a>.")
        QMessageBox.about(self, f"About {Constants.APP_NAME}", text)

    def create_actions(self):
        self.settings_action = QAction("&Settings", self)
        self.settings_action.setStatusTip("Application settings")
        self.settings_action.triggered.connect(self.open_settings)  # type: ignore

        self.quit_action = QAction("&Quit", self)
        self.quit_action.setShortcut(QKeySequence.Quit)
        self.quit_action.setStatusTip("Quit the application")
        self.quit_action.triggered.connect(self.close)  # type: ignore

        self.about_action = QAction("&About", self)
        self.about_action.setStatusTip("Show the application's About box")
        self.about_action.triggered.connect(self.about)  # type: ignore

        self.about_qt_action = QAction("About &Qt", self)
        self.about_qt_action.setStatusTip("Show the Qt library's About box")
        self.about_qt_action.triggered.connect(QApplication.aboutQt)  # type: ignore

    def create_menus(self):
        self.file_menu = self.menuBar().addMenu("&File")
        self.file_menu.addAction(self.settings_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.quit_action)

        self.view_menu = self.menuBar().addMenu("&View")

        self.menuBar().addSeparator()

        self.help_menu = self.menuBar().addMenu("&Help")
        self.help_menu.addAction(self.about_action)
        self.help_menu.addAction(self.about_qt_action)

    def create_status_bar(self):
        self.statusBar().showMessage("Ready")

    def create_windows(self):
        dock = QDockWidget("Log", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea |  # type: ignore
                             Qt.DockWidgetArea.BottomDockWidgetArea)
        dock.setObjectName("Log Window")
        dock.setMinimumHeight(150)
        self.log_widget = LogWidget(dock)
        dock.setWidget(self.log_widget)
        dock.hide()
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, dock)
        self.view_menu.addAction(dock.toggleViewAction())

        dock = QDockWidget("Available Components", self)
        dock.setObjectName("Available Components Window")
        dock.setMinimumWidth(200)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)  # type: ignore
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea |  # type: ignore
                             Qt.DockWidgetArea.RightDockWidgetArea)
        self.avaiable_comps_widget = AllComponentsWidget(dock)
        dock.setWidget(self.avaiable_comps_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

        dock = QDockWidget("Component Configuration", self)
        dock.setObjectName("Component Configuration Window")
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)  # type: ignore
        dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)  # type: ignore
        dock.setMinimumHeight(150)

        self.component_config_scroll_area = QScrollArea(dock)
        self.component_config_scroll_area.setWidgetResizable(True)

        self.component_config_main_widget = QWidget(dock)
        self.component_config_main_widget.setObjectName("CompConfObj")
        self.component_config_main_widget.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding,
                                                                    QSizePolicy.Policy.Expanding))

        self.component_config_main_widget_layout = QHBoxLayout()
        self.component_config_main_widget_layout.setContentsMargins(0, 0, 0, 0)
        self.component_config_main_widget.setLayout(self.component_config_main_widget_layout)

        self.component_config_scroll_area.setContentsMargins(0, 0, 0, 0)
        self.component_config_scroll_area.setWidget(self.component_config_main_widget)
        dock.setWidget(self.component_config_scroll_area)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)

        self.active_component_config_widget: Optional[QWidget] = None

        self.settings_widget = SettingsWidget(self)
        self.settings_widget.obsWebsocketSettingsChanged.connect(self.obs_websocket_settings_changed)  # type: ignore
        self.settings_widget.accountHostConnectPressed.connect(self.account_host_connect_pressed)  # type: ignore
        self.settings_widget.accountBotConnectPressed.connect(self.account_bot_connect_pressed)  # type: ignore
        self.settings_widget.accountHostDisconnectPressed.connect(self.account_host_disconnect_pressed)  # type: ignore
        self.settings_widget.accountBotDisconnectPressed.connect(self.account_bot_disconnect_pressed)  # type: ignore

        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)

    def read_settings(self):
        self.restoreGeometry(self.settings.value("geometry"))  # type: ignore
        self.restoreState(self.settings.value("windowState"))  # type: ignore
        self.move(self.settings.value("pos", self.pos()))  # type: ignore
        self.resize(self.settings.value("size", self.size()))  # type: ignore
        if self.settings.value("maximized", self.isMaximized(), bool):
            self.showMaximized()

    #################################################################
    # Slots
    #################################################################

    def obs_websocket_settings_changed(self, settings):
        self.app.set_obs_config(settings["host"], settings["port"], settings["password"])

    def account_host_connect_pressed(self):
        if self.app is not None and self.app.host_twitch_service is None:
            self.__open_url(self.app.get_host_connect_url())
            self.settings_widget.host_account_button.setDisabled(True)

    def account_bot_connect_pressed(self):
        if self.app is not None and self.app.bot_twitch_service is None:
            self.__open_url(self.app.get_bot_connect_url())
            self.settings_widget.bot_account_button.setDisabled(True)

    def account_host_disconnect_pressed(self):
        if self.app is not None and self.app.host_twitch_service is not None:
            self.settings_widget.host_account_button.setDisabled(True)
            self.app.reset_host_account()

    def account_bot_disconnect_pressed(self):
        if self.app is not None and self.app.bot_twitch_service is not None:
            self.settings_widget.bot_account_button.setDisabled(True)
            self.app.reset_bot_account()

    def open_settings(self):
        obs_config = self.app.get_obs_config()
        self.settings_widget.host_line_edit.setText(obs_config["host"])
        self.settings_widget.port_line_edit.setText(str(obs_config["port"]))
        self.settings_widget.password_line_edit.setText(obs_config["password"])
        self.settings_widget.show()
        self.settings_widget.activateWindow()

    def add_component(self, component_id: str) -> None:
        if self.app is None:
            return
        self.app.add_component(component_id)

    def remove_component(self, component_id: str) -> None:
        if self.app is None:
            return
        self.app.remove_component(component_id)

    def component_clicked(self, component_id: str) -> None:
        self.last_clicked_component = component_id

        active_components = self.app.get_active_components()
        if component_id in active_components:
            component_instance = active_components[component_id]
            if not component_instance.has_started:
                return
            config_something = component_instance.get_config_something()
            if isinstance(config_something, QWidget):
                if self.active_component_config_widget:
                    self.component_config_main_widget_layout.removeWidget(self.active_component_config_widget)
                    if self.active_component_config_widget != config_something:
                        self.active_component_config_widget.setParent(None)  # type: ignore
                        self.active_component_config_widget = None
                config_something.resize(config_something.minimumWidth(), config_something.minimumHeight())
                scroll_bar_width = self.style().pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent)
                border_width = 1
                self.component_config_main_widget_layout.addWidget(config_something)
                self.component_config_scroll_area.setMinimumWidth(config_something.width() +
                                                                  scroll_bar_width + border_width * 2)
                self.active_component_config_widget = config_something
            if config_something is None:
                if self.active_component_config_widget:
                    self.component_config_main_widget_layout.removeWidget(self.active_component_config_widget)
                    self.active_component_config_widget.setParent(None)  # type: ignore
                    self.component_config_scroll_area.setMinimumWidth(0)
                    self.active_component_config_widget = None

    #################################################################
    # EdoBot Listeners
    #################################################################

    def edobot_started(self):
        if self.last_clicked_component:
            self.component_clicked(self.last_clicked_component)

    def edobot_stopped(self):
        if self.active_component_config_widget:
            self.component_config_main_widget_layout.removeWidget(self.active_component_config_widget)
            self.active_component_config_widget.setParent(None)  # type: ignore
            self.active_component_config_widget = None

    def add_component_widget(self, component: ChatComponent):
        widget = ComponentWidget(component.get_id(), component.get_name(), component.get_description())
        self.component_list.add_component(widget)

    def host_connected(self, user: model.User):
        self.settings_widget.set_host_account(user.display_name)

    def bot_connected(self, user: model.User):
        self.settings_widget.set_bot_account(user.display_name)

    def host_disconnected(self):
        self.settings_widget.set_host_account(None)

    def bot_disconnected(self):
        self.settings_widget.set_bot_account(None)

    #################################################################
    # Overrides
    #################################################################

    def closeEvent(self, event: QCloseEvent) -> None:
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("maximized", self.isMaximized())
        if not self.isMaximized():
            self.settings.setValue("pos", self.pos())
            self.settings.setValue("size", self.size())
        event.accept()

    def __del__(self) -> None:
        if self.app is not None:
            self.app.shutdown()
            self.app.config["components"] = self.component_list.get_component_order()

    #################################################################
    # Private
    #################################################################

    def __open_url(self, url):
        gLogger.info(f"You will be redirected to the browser to login to {url}")
        try:
            webbrowser.open_new(url)
        except Exception:
            gLogger.info(f"Could not find a suitable browser, please open the URL directly:\n{url}")


class TimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        locale = arrow.now()
        if datefmt:
            return locale.format(datefmt)
        else:
            return locale.isoformat(timespec="seconds")


def main():
    if not os.path.isdir(Constants.SAVE_DIRECTORY):
        os.makedirs(Constants.SAVE_DIRECTORY)

    if __debug__:
        print(f"Debug info: [PID: {os.getpid()}]")

    try:
        app = QApplication(sys.argv)
        main_win = MainWindow()
        main_win.show()
        main_win.activateWindow()
        ret = app.exec_()
        main_win = None
        app = None
        sys.exit(ret)
    except Exception as e:
        traceback_str = ''.join(traceback.format_tb(e.__traceback__))
        gLogger.critical(f"Critical error: {e}\n{traceback_str}")
        raise e
