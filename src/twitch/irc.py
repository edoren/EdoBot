import logging
import socket
import ssl
from typing import List, Optional

__all__ = ["IRC"]


class IRC:
    def __init__(self, nickname: str, password: str):
        self.socket: Optional[ssl.SSLSocket] = None

        self.channels: List[str] = []
        self.nickname: str = nickname
        self.password: str = 'oauth:' + password.lstrip('oauth:')
        self.is_running: bool = True
        self.subscribers = []

        self.connect()
        self.authenticate()

    def run(self):
        while self.is_running:
            try:
                data = self._read_line()
                text = data.decode("UTF-8").strip('\n\r')

                if text.find('PING') >= 0:
                    self.send_raw('PONG ' + text.split()[1])

                if text.find('Login authentication failed') > 0:
                    logging.fatal('IRC authentication error: ' + text or '')
                    return

                if data is not None and len(data) != 0:
                    for sub in self.subscribers:
                        sub(data)
            except IOError:
                break

    def stop(self):
        self.is_running = False

    def subscribe(self, subscriber):
        self.subscribers.append(subscriber)

    def send_raw(self, message: str) -> None:
        data = (message.lstrip('\n') + '\n').encode('utf-8')
        self.socket.send(data)

    def send_message(self, message: str, channel: str) -> None:
        channel = channel.lstrip('#')
        self.send_raw(f'PRIVMSG #{channel} :{message}')

    def connect(self) -> None:
        hostname = "irc.chat.twitch.tv"
        port = 6697
        sock = socket.create_connection((hostname, port))
        context = ssl.create_default_context()
        self.socket = context.wrap_socket(sock, server_hostname=hostname)
        self.socket.settimeout(0.5)

    def authenticate(self) -> None:
        self.send_raw(f'PASS {self.password}')
        self.send_raw(f'NICK {self.nickname}')

    def join_channel(self, channel: str) -> None:
        channel = channel.lstrip('#')
        self.channels.append(channel)
        self.send_raw(f'JOIN #{channel}')

    def leave_channel(self, channel: str) -> None:
        channel = channel.lstrip('#')
        self.channels.remove(channel)
        self.send_raw(f'PART #{channel}')

    def leave_channels(self, channels: List[str]) -> None:
        channels = [channel.lstrip('#') for channel in channels]
        [self.channels.remove(channel) for channel in channels]
        self.send_raw('PART #' + '#'.join(channels))

    def _read_line(self) -> bytes:
        data: bytes = b''
        while self.is_running:
            try:
                next_byte: bytes = self.socket.recv(1)
                if next_byte == b'\n':
                    break
                data += next_byte
            except Exception:
                continue
        return data
