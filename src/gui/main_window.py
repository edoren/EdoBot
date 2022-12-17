import argparse
import logging
import os
import os.path
import sys
import traceback
import webbrowser
import zipfile
from datetime import datetime
from typing import Callable, List, Optional

import arrow
from PySide6.QtCore import QEvent, QLocale, QSettings, QSize, Qt, QTranslator, QUrl, Signal
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QFont, QIcon, QKeySequence, QResizeEvent
from PySide6.QtWidgets import (QApplication, QDockWidget, QFrame, QHBoxLayout, QLayout, QMainWindow, QMenu, QMessageBox,
                               QSizePolicy, QSystemTrayIcon, QTextBrowser, QWidget)

import model
from core import App, ChatComponent, Constants

from .unique_application import UniqueApplication
from .widgets import ActiveComponentsWidget, AllComponentsWidget, ComponentWidget, SettingsWidget

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
        messages = record.msg.split("\n")
        msg += f" - {messages[0]}"
        self.append(msg)
        for msg in messages[1:]:
            self.append(msg)


class MainWindow(QMainWindow):
    edobotStarted = Signal()
    edobotStopped = Signal()
    hostConnected = Signal(model.User)
    botConnected = Signal(model.User)
    hostDisconnected = Signal()
    botDisconnected = Signal()
    componentAdded = Signal(ChatComponent)

    def __init__(self, args: argparse.Namespace):
        super().__init__()

        self.translator_units = []

        translator = QTranslator()
        translator.load(QLocale(), "", "", os.path.join(Constants.EXECUTABLE_DIRECTORY, "i18n"), ".qm")
        QApplication.installTranslator(translator)
        self.translator_units.append(translator)

        self.settings = QSettings(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, "Edoren",
                                  Constants.APP_NAME)

        self.setWindowTitle(f"{Constants.APP_NAME} {Constants.APP_VERSION}")

        self.active_component_config_widget: Optional[QWidget] = None

        self.component_list = ActiveComponentsWidget()
        self.component_list.setMinimumSize(400, 200)
        self.setCentralWidget(self.component_list)

        self.create_actions()
        self.create_menus()
        self.create_system_tray()
        self.create_status_bar()
        self.create_dock_windows()
        self.create_settings_window()

        handlers: List[logging.Handler] = []

        self.open_time = datetime.now()

        log_dir = os.path.join(Constants.SAVE_DIRECTORY, "logs")
        log_filename = "edobot-latest.log"

        # Create the log folder if it dooes not exists
        if not os.path.isdir(log_dir):
            os.makedirs(log_dir)

        self.log_file_path = os.path.join(log_dir, log_filename)

        if __debug__:
            default_level = logging.DEBUG
        else:
            default_level = logging.INFO

        file_handler = logging.FileHandler(self.log_file_path, "a", "utf-8")
        file_handler.setLevel(default_level)
        file_handler.setFormatter(
            TimeFormatter("[%(asctime)s] %(process)s %(threadName)s %(levelname)s %(name)s - %(message)s"))
        handlers.append(file_handler)

        stream_handler = CallbackHandler(self.log_widget.logRecordReceived.emit)  # type: ignore
        stream_handler.setLevel(logging.INFO)
        handlers.append(stream_handler)

        logging.basicConfig(level=default_level, handlers=handlers)

        if __debug__:
            gLogger.info(f"Debug info: [PID: {os.getpid()}]")

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

        self.last_clicked_component = None

        self.component_list.componentDropped.connect(self.add_component)  # type: ignore
        self.component_list.componentRemoved.connect(self.remove_component)  # type: ignore
        self.component_list.componentClicked.connect(self.component_clicked)  # type: ignore

        for comp_type in self.app.get_available_components().values():
            # Load translation files
            component_folder = self.app.get_component_folder(comp_type.get_id())
            if component_folder is not None:
                translator = QTranslator()
                translator.load(QLocale(), "", "", os.path.join(component_folder, "i18n"), ".qm")
                QApplication.installTranslator(translator)
                self.translator_units.append(translator)
            comp_metadata = comp_type.get_metadata()
            if __debug__ or not comp_metadata.debug:
                self.available_comps_widget.add_component(comp_type.get_id(), comp_metadata)

        self.app.start()

        self.restore_window_settings()

        if self.settings_widget.is_system_tray_enabled() and args.background:
            self.close()
        else:
            self.show()
            self.activateWindow()

    def about(self):
        text = ("EdoBot is an open source tool to create Twitch components that interacts with the chat."
                "<br><br>"
                "Please go to <a href='https://github.com/edoren/EdoBot'>github.com/edoren/EdoBot</a> for more info."
                "<br><br>"
                "Download latest release <a href='https://github.com/edoren/edobot/releases/latest'>here</a>.")
        QMessageBox.about(self, self.tr("About {0}").format(Constants.APP_NAME), text)

    def create_actions(self):
        self.settings_action = QAction("&Settings", self)
        self.settings_action.setText(self.tr("Settings"))
        self.settings_action.setShortcut(QKeySequence.StandardKey.Preferences)
        self.settings_action.setStatusTip(self.tr("Application settings"))
        self.settings_action.triggered.connect(self.open_settings)  # type: ignore

        self.open_user_folder_action = QAction(self.tr("Open User Folder"), self)
        self.open_user_folder_action.setStatusTip(self.tr("Open the user's folder"))
        self.open_user_folder_action.triggered.connect(self.open_user_folder)  # type: ignore

        self.close_action = QAction("&Close", self)
        self.close_action.setText(self.tr("Close"))
        self.close_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.close_action.setStatusTip(self.tr("Close the application"))
        self.close_action.triggered.connect(self.close)  # type: ignore

        self.about_action = QAction("&About", self)
        self.about_action.setText(self.tr("About"))
        self.about_action.setStatusTip(self.tr("Show the application's About box"))
        self.about_action.triggered.connect(self.about)  # type: ignore

        self.about_qt_action = QAction(self.tr("About {0}").format("&Qt"), self)
        self.about_qt_action.setStatusTip(self.tr("Show the Qt library's About box"))
        self.about_qt_action.triggered.connect(QApplication.aboutQt)  # type: ignore

    def create_menus(self):
        self.file_menu = self.menuBar().addMenu("&File")
        self.file_menu.setTitle(self.tr("File"))
        self.file_menu.addAction(self.settings_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.open_user_folder_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.close_action)

        self.view_menu = self.menuBar().addMenu("&View")
        self.view_menu.setTitle(self.tr("View"))

        self.menuBar().addSeparator()

        self.help_menu = self.menuBar().addMenu("&Help")
        self.help_menu.setTitle(self.tr("Help"))
        self.help_menu.addAction(self.about_action)
        self.help_menu.addAction(self.about_qt_action)

    def create_system_tray(self):
        # Creating the options
        menu = QMenu()
        quit_action = QAction(self.tr("Quit"), self)
        quit_action.setToolTip(self.tr("Quit the application"))
        quit_action.triggered.connect(self.system_tray_quit)  # type: ignore
        open_action = QAction(self.tr("Open"), self)
        open_action.setToolTip(self.tr("Open the application"))
        open_action.triggered.connect(self.system_tray_open)  # type: ignore
        menu.addAction(open_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self.system_tray = QSystemTrayIcon(self)
        self.system_tray.setIcon(self.windowIcon())
        self.system_tray.setToolTip(Constants.APP_NAME)
        self.system_tray.setContextMenu(menu)
        self.system_tray.show()

        self.system_tray.activated.connect(self.system_tray_activated)  # type: ignore

    def create_status_bar(self):
        self.statusBar().showMessage(self.tr("Ready"))

    def create_dock_windows(self):
        self.log_dock = QDockWidget(self.tr("Logs"), self)
        self.log_dock.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea |  # type: ignore
                                      Qt.DockWidgetArea.BottomDockWidgetArea)
        self.log_dock.setObjectName("Logs Window")
        self.log_dock.setMinimumHeight(150)
        self.log_widget = LogWidget(self.log_dock)
        self.log_dock.setWidget(self.log_widget)
        self.log_dock.hide()
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.log_dock)
        toggle_action = self.log_dock.toggleViewAction()
        toggle_action.setStatusTip(self.tr("Toggle the log window"))
        self.view_menu.addAction(toggle_action)

        dock = QDockWidget(self.tr("Available Components"), self)
        dock.setObjectName("Available Components Window")
        dock.setMinimumWidth(200)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)  # type: ignore
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea |  # type: ignore
                             Qt.DockWidgetArea.RightDockWidgetArea)
        self.available_comps_widget = AllComponentsWidget(dock)
        dock.setWidget(self.available_comps_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

        dock = QDockWidget(self.tr("Component Configuration"), self)
        dock.setObjectName("Component Configuration Window")
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)  # type: ignore
        dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)  # type: ignore
        dock.setMinimumHeight(150)
        dock.setMaximumHeight(150)

        self.component_config_main_widget = QFrame(dock)
        self.component_config_main_widget.setFrameShape(QFrame.Shape.StyledPanel)
        self.component_config_main_widget.setFrameShadow(QFrame.Shadow.Sunken)
        self.component_config_main_widget.setObjectName("CompConfObj")

        component_config_main_widget_layout = QHBoxLayout()
        component_config_main_widget_layout.setContentsMargins(0, 0, 0, 0)
        component_config_main_widget_layout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        self.component_config_main_widget.setLayout(component_config_main_widget_layout)
        self.component_dock_widget = dock

        dock.setWidget(self.component_config_main_widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)

        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)

    def create_settings_window(self):
        self.settings_widget = SettingsWidget(self, self.settings)
        self.settings_widget.obsConfigChanged.connect(self.obs_settings_changed)  # type: ignore
        self.settings_widget.accountHostConnectPressed.connect(self.account_host_connect_pressed)  # type: ignore
        self.settings_widget.accountBotConnectPressed.connect(self.account_bot_connect_pressed)  # type: ignore
        self.settings_widget.accountHostDisconnectPressed.connect(self.account_host_disconnect_pressed)  # type: ignore
        self.settings_widget.accountBotDisconnectPressed.connect(self.account_bot_disconnect_pressed)  # type: ignore
        self.settings_widget.systemTrayEnabled.connect(self.system_tray_enabled)  # type: ignore
        self.system_tray_enabled(self.settings_widget.system_tray_check_box.isChecked())

    def restore_window_settings(self):
        self.restoreGeometry(self.settings.value("geometry"))  # type: ignore
        self.restoreState(self.settings.value("window_state"))  # type: ignore
        self.move(self.settings.value("pos", self.pos()))  # type: ignore
        self.resize(QSize(800, 600))  # type: ignore
        if self.settings.value("maximized", self.isMaximized(), bool):
            self.showMaximized()

    def shutdown(self) -> None:
        if getattr(self, "app", None) is not None:
            self.app.shutdown()
            self.app.config["components"] = self.component_list.get_component_order()
        logging.shutdown()
        log_dir = os.path.dirname(self.log_file_path)
        zip_file_path = os.path.join(log_dir, self.open_time.strftime("edobot-%d-%m-%Y.zip"))
        zip_file = zipfile.ZipFile(zip_file_path, mode="a", compression=zipfile.ZIP_BZIP2, compresslevel=9)
        zip_file.write(self.log_file_path, arcname=self.open_time.strftime("%d-%m-%Y-%H-%M-%S.log"))
        with open(self.log_file_path, "w"):
            pass

    #################################################################
    # Slots
    #################################################################

    def obs_settings_changed(self, settings):
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

    def open_user_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(Constants.SAVE_DIRECTORY))

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
            try:
                config_something = component_instance.get_config_ui()
            except Exception as e:
                gLogger.error(''.join(traceback.format_tb(e.__traceback__)))
                return
            layout = self.component_config_main_widget.layout()
            self.component_dock_widget.setMinimumSize(0, 150)  # Reset dock minimum size
            if isinstance(config_something, QWidget):
                if self.active_component_config_widget is not None:
                    if self.active_component_config_widget != config_something:
                        layout.removeWidget(self.active_component_config_widget)
                        self.active_component_config_widget.setParent(None)  # type: ignore
                        self.active_component_config_widget.deleteLater()
                        self.active_component_config_widget = None
                        self.component_config_main_widget.adjustSize()
                        self.component_dock_widget.adjustSize()
                    else:
                        return
                self.component_dock_widget.setMaximumHeight(16777215)
                self.active_component_config_widget = config_something
                config_something.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                config_something.adjustSize()
                layout.addWidget(self.active_component_config_widget)
            if config_something is None:
                if self.active_component_config_widget:
                    layout.removeWidget(self.active_component_config_widget)
                    self.active_component_config_widget.setParent(None)  # type: ignore
                    self.active_component_config_widget.deleteLater()
                    self.active_component_config_widget = None
                    self.component_dock_widget.setMinimumHeight(150)
                    self.component_dock_widget.setMaximumHeight(150)

    def system_tray_enabled(self, enabled: bool):
        QApplication.instance().setQuitOnLastWindowClosed(not enabled)  # type: ignore

    def system_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.system_tray_open()

    def system_tray_open(self):
        self.show()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def system_tray_quit(self):
        if self.log_dock.isFloating():
            self.log_dock.hide()
        self.hide()
        self.system_tray.hide()
        QApplication.quit()

    #################################################################
    # EdoBot Listeners
    #################################################################

    def edobot_started(self):
        if self.last_clicked_component:
            self.component_clicked(self.last_clicked_component)

    def edobot_stopped(self):
        if self.active_component_config_widget:
            self.component_config_main_widget.layout().removeWidget(self.active_component_config_widget)
            self.active_component_config_widget.setParent(None)  # type: ignore
            self.active_component_config_widget.deleteLater()
            self.active_component_config_widget = None

    def add_component_widget(self, component: ChatComponent):
        widget = ComponentWidget(component.get_id(), component.get_metadata())
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
        if self.settings_widget.is_system_tray_enabled() and self.log_dock.isFloating():  # type: ignore
            self.log_dock.hide()
        event.accept()

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.WindowDeactivate:
            self.settings.setValue("geometry", self.saveGeometry())
            self.settings.setValue("window_state", self.saveState())
            self.settings.setValue("maximized", self.isMaximized())
            if not self.isMaximized():
                self.settings.setValue("pos", self.pos())
                self.settings.setValue("size", self.size())
        return super().event(event)

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--background", help="Open app in background", action="store_true")
    args = parser.parse_args()

    if not os.path.isdir(Constants.SAVE_DIRECTORY):
        os.makedirs(Constants.SAVE_DIRECTORY)

    try:
        qt_app = UniqueApplication(sys.argv)
        qt_app.setWindowIcon(QIcon(os.path.join(Constants.DATA_DIRECTORY, "icon.ico")))

        # QLocale.setDefault(QLocale(QLocale.Language.Spanish, QLocale.Country.Colombia))
        # QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))

        if qt_app.is_unique():
            qt_app.start_listener()
            main_win = MainWindow(args)
            qt_app.anotherInstance.connect(main_win.system_tray_open)  # type: ignore
            ret = qt_app.exec_()
            main_win.shutdown()
            main_win = None
            qt_app = None
            sys.exit(ret)
    except Exception as e:
        traceback_str = ''.join(traceback.format_tb(e.__traceback__))
        gLogger.critical(f"Critical error: {e}\n{traceback_str}")
        raise e
