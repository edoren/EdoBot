from PySide2.QtCore import Signal
from PySide2.QtNetwork import QLocalServer, QLocalSocket
from PySide2.QtWidgets import QApplication

from core import Constants


class UniqueApplication(QApplication):
    anotherInstance = Signal()

    def is_unique(self):
        socket = QLocalSocket()
        socket.connectToServer(f"{Constants.APP_NAME}-InstanceSock")
        return socket.state() != QLocalSocket.LocalSocketState.ConnectedState

    def start_listener(self):
        self.listener = QLocalServer(self)
        self.listener.setSocketOptions(QLocalServer.SocketOption.WorldAccessOption)  # type: ignore
        self.listener.newConnection.connect(self.anotherInstance)  # type: ignore
        self.listener.listen(f"{Constants.APP_NAME}-InstanceSock")
