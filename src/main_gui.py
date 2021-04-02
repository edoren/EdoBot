
import logging
import os
import os.path
import sys
import traceback
import webbrowser
from typing import Callable, List, Optional

import arrow
from PySide2.QtCore import QSettings, Qt, Signal
from PySide2.QtGui import QCloseEvent, QFont, QKeySequence, QResizeEvent
from PySide2.QtWidgets import (QAction, QApplication, QDockWidget, QMainWindow,
                               QMessageBox, QSizePolicy, QTextBrowser, QWidget)

import model
from core import Constants, EdoBot
from gui import widgets
from gui.widgets import ActiveComponentsWidget, AllComponentsWidget
from gui.widgets.component import ComponentWidget
from twitch.component import ChatComponent

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
    hostConnected = Signal(model.User)
    botConnected = Signal(model.User)
    componentAdded = Signal(ChatComponent)

    def __init__(self):
        super().__init__()

        self.settings = QSettings(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, "Edoren", "EdoBot")

        self.component_list = ActiveComponentsWidget()
        self.component_list.setMinimumSize(400, 300)
        self.setCentralWidget(self.component_list)

        self.create_actions()
        self.create_menus()
        self.create_status_bar()
        self.create_windows()

        handlers: List[logging.Handler] = []

        file_handler = logging.FileHandler(os.path.join(Constants.SAVE_DIRECTORY, "out.log"), "a")
        file_handler.setLevel(logging.NOTSET)
        file_handler.setFormatter(TimeFormatter(
            "[%(asctime)s] %(process)s %(threadName)s %(levelname)s %(name)s - %(message)s"))
        handlers.append(file_handler)

        stream_handler = CallbackHandler(self.log_widget.logRecordReceived.emit)  # type: ignore
        stream_handler.setLevel(logging.INFO)
        handlers.append(stream_handler)

        logging.getLogger(f"obswebsocket").setLevel(logging.CRITICAL)
        logging.basicConfig(level=logging.NOTSET, handlers=handlers)

        self.bot: EdoBot = EdoBot()
        self.bot.component_added = self.componentAdded.emit  # type: ignore
        self.bot.host_connected = self.hostConnected.emit  # type: ignore
        self.bot.bot_connected = self.botConnected.emit  # type: ignore
        self.reconnect_bot()

        self.componentAdded.connect(self.add_component_widget)  # type: ignore
        self.hostConnected.connect(self.host_connected)  # type: ignore
        self.botConnected.connect(self.bot_connected)  # type: ignore

        self.component_list.componentDropped.connect(self.add_component)  # type: ignore
        self.component_list.componentRemoved.connect(self.remove_component)  # type: ignore
        self.component_list.componentClicked.connect(self.component_clicked)  # type: ignore

        for comp_instance in self.bot.get_active_components().values():
            self.add_component_widget(comp_instance)

        for comp_type in self.bot.get_available_components().values():
            self.avaiable_comps_widget.add_component(comp_type.get_id(), comp_type.get_name(),
                                                     comp_type.get_description())

        self.setWindowTitle("EdoBot")
        self.read_settings()

    def reconnect_bot(self):
        self.bot.start()

    def about(self):
        QMessageBox.about(self, "EdoBot",
                          "The <b>Dock Widgets</b> example demonstrates how to use "
                          "Qt's dock widgets. You can enter your own text, click a "
                          "customer to add a customer name and address, and click "
                          "standard paragraphs to add them.")

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
        self.component_config = QWidget(dock)
        self.component_config.setObjectName("CompConfObj")
        self.component_config.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding))
        self.component_config.setStyleSheet("QWidget#CompConfObj\n"
                                            "{ background-color: #f5f5f5; border: 1px solid #828790; }")
        dock.setWidget(self.component_config)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)

        self.settings_widget = widgets.SettingsWidget()
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
        self.bot.set_obs_config(settings["host"], settings["port"], settings["password"])

    def account_host_connect_pressed(self):
        if self.bot is not None and self.bot.host_twitch_service is None:
            gLogger.info(f"You will be redirected to the browser to login [Press Enter]")
            self.__open_url(self.bot.get_host_connect_url())
            self.settings_widget.host_account_button.setDisabled(True)

    def account_bot_connect_pressed(self):
        if self.bot is not None and self.bot.bot_twitch_service is None:
            gLogger.info(f"You will be redirected to the browser to login [Press Enter]")
            self.__open_url(self.bot.get_bot_connect_url())
            self.settings_widget.bot_account_button.setDisabled(True)

    def account_host_disconnect_pressed(self):
        if self.bot is not None and self.bot.host_twitch_service is not None:
            self.settings_widget.host_account_button.setDisabled(True)
            self.bot.reset_host_account()  # TODO: Stop BOT

    def account_bot_disconnect_pressed(self):
        if self.bot is not None and self.bot.bot_twitch_service is not None:
            self.settings_widget.bot_account_button.setDisabled(True)
            self.bot.reset_bot_account()  # TODO: Stop BOT

    def open_settings(self):
        obs_config = self.bot.get_obs_config()
        self.settings_widget.host_line_edit.setText(obs_config["host"])
        self.settings_widget.port_line_edit.setText(str(obs_config["port"]))
        self.settings_widget.password_line_edit.setText(obs_config["password"])
        self.settings_widget.show()
        self.settings_widget.activateWindow()

    def add_component(self, component_id: str) -> None:
        if self.bot is None:
            return
        self.bot.add_component(component_id)

    def remove_component(self, component_id: str) -> None:
        if self.bot is None:
            return
        self.bot.remove_component(component_id)

    def component_clicked(self, component_id: str) -> None:
        print(component_id)

    #################################################################
    # EdoBot Listeners
    #################################################################

    def add_component_widget(self, component: ChatComponent):
        widget = ComponentWidget(component.get_id(), component.get_name(), component.get_description())
        self.component_list.add_component(widget)

    def host_connected(self, user: model.User):
        self.settings_widget.set_host_account(user.display_name)

    def bot_connected(self, user: model.User):
        self.settings_widget.set_bot_account(user.display_name)

    def host_disconnected(self, user: model.User):
        self.settings_widget.set_host_account(None)

    def bot_disconnected(self, user: model.User):
        self.settings_widget.set_bot_account(None)

    #################################################################
    # Overrides
    #################################################################

    def closeEvent(self, event: QCloseEvent) -> None:
        self.settings_widget.close()
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("maximized", self.isMaximized())
        if not self.isMaximized():
            self.settings.setValue("pos", self.pos())
            self.settings.setValue("size", self.size())
        event.accept()

    def __del__(self) -> None:
        if self.bot is not None:
            self.bot.stop()

    #################################################################
    # Private
    #################################################################

    def __open_url(self, url):
        gLogger.info(f"You will be redirected to the browser to login' [Press Enter]")
        try:
            webbrowser.open_new(url)
        except Exception:
            print("Could not find a suitable browser, please open the URL directly:\n{}".format(url))
        self.bot


class TimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        locale = arrow.now()
        if datefmt:
            return locale.format(datefmt)
        else:
            return locale.isoformat(timespec="seconds")


if __name__ == '__main__':
    print("------------------------------------------------------------")
    print("------------------------ EdoBot 1.0 ------------------------")
    print("------------------------------------------------------------", flush=True)

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
        sys.exit(0)
    except Exception as e:
        traceback_str = ''.join(traceback.format_tb(e.__traceback__))
        gLogger.critical(f"Critical error: {e}\n{traceback_str}")
        raise e
