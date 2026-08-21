import json
import threading
import time
from threading import Thread
from .util import startEnd, _request
from .config import Config, getGlobalConfig
import websocket
from typing import Optional, Callable, Any, Union, Tuple


class ChatClient(websocket.WebSocketApp):
    def __init__(self,
                 token: str,
                 room: str = 'main',
                 config: Config = None,
                 on_open: Callable[[websocket.WebSocketApp], None] = None,
                 on_message: Callable[[websocket.WebSocketApp, dict], None] = None,
                 on_error: Callable[[websocket.WebSocketApp, Any], None] = None,
                 on_close: Callable[[websocket.WebSocketApp, Any, Any], None] = None,
                 on_ping: Callable = None,
                 on_pong: Callable = None,
                 on_reconnect: Callable[[websocket.WebSocketApp], None] = None,
                 on_chat: Callable[[websocket.WebSocketApp, dict], None] = None
                 ):
        """聊天室客户端。
        websocket.WebSocketApp的包装。
        on_chat: 收到聊天信息时的回调函数。
        on_message: 收到所有信息时的回调函数。"""
        self._url = f'wss://{config.chatAPIBase}ws?room={room}&token={token}'
        self.ws = None
        self._token = token
        self.room = room
        self._config = config
        self._user_on_open = on_open
        self._user_on_message = on_message
        self._user_on_error = on_error
        self._user_on_close = on_close
        self._user_on_ping = on_ping
        self._user_on_pong = on_pong
        self._user_on_reconnect = on_reconnect
        self._user_on_chat = on_chat
        self._pinged = False
        self._running = False
        super().__init__(self._url,
                         header=self._config.headers,
                         on_open=self._on_open,
                         on_reconnect=self._on_reconnect,
                         on_message=self._on_message,
                         on_error=self._on_error,
                         on_close=self._on_close,
                         on_ping=self._on_ping,
                         on_pong=self._on_pong,
                         )

    def sendPing(self) -> None:
        """发送心跳包。一般无需外部触发此函数。"""
        self.send(json.dumps({'type': 'ping'}))

    def _on_open(self, ws):
        # 默认函数。
        if self._user_on_open:
            self._user_on_open(ws)
        self._running = True

        def heartbeat():
            while self._running:
                time.sleep(30)
                if self._pinged:
                    print(f'[ChatClient/heartbeat]{self._config.colorYellow}did not receive pong after ping\033[0m')
                if self.sock and self.sock.connected:
                    self._pinged = True
                    self.sendPing()

        threading.Thread(target=heartbeat, daemon=True).start()  # 启动新线程
        print(f"[ChatClient]connected to room '{self.room}'")

    def _on_message(self, ws, msg: str):
        # 默认函数。
        data: dict = json.loads(msg)
        type_ = data.get('type')
        if type_ == 'pong':
            if not self._pinged:
                print('[ChatClient/heartbeat]'
                      f"{self._config.colorYellow}receive pong without ping. This shouldn't happen.\033[0m")
            self._pinged = False
        elif type_ == 'welcome':
            self.uid = data.get('uid')
            self.name = data.get('username')
            self.mute = data.get('mute')
            self.is_admin = bool(data.get('is_admin'))
            self.announcement: dict = data.get('pinned_announcement')
            self.role = data.get('role')
            print(f'[ChatClient/msg:welcome]Welcome {self.name}(ou{self.uid})! ({self.role})')
        elif type_ == 'online_count':
            print(f'[ChatClient/msg:online]Online count:{data["count"]} @{time.time()}')
        elif type_ == 'message':
            if self._user_on_chat:
                self._user_on_chat(ws, data)
            else:
                print(f'[ChatClient/msg:chat]id={data["id"]}@{data["created_at"]}: <ou{data["uid"]}> {data["content"]}')
        elif type_ == 'message_deleted':
            print(f'[ChatClient/msg:delMsg]id={data["id"]} deleted in room \'{self.room}\'')
        if self._user_on_message:
            self._user_on_message(ws, data)

    def _on_error(self, ws, e):
        if self._user_on_error:
            self._user_on_error(ws, e)
        else:
            print(f'[ChatClient/error]{self._config.colorRed}{e}\033[0m')

    def _on_close(self, ws, code, msg):
        if self._user_on_close:
            self._user_on_close(ws, code, msg)
        else:
            print('[ChatClient]connection closed' + f' with code {code}' if code is not None else '')

    def _on_ping(self, *args, **kwargs):
        if self._user_on_ping:
            self._user_on_ping(*args, **kwargs)

    def _on_pong(self, *args, **kwargs):
        if self._user_on_pong:
            self._user_on_pong(*args, **kwargs)

    def _on_reconnect(self, ws):
        if self._user_on_reconnect:
            self._user_on_reconnect(ws)
        else:
            print(f'[ChatClient/reconnect]{self._config.colorYellow}reconnect triggered\033[0m')

    def stop(self):
        """停止心跳并关闭连接。"""
        self._running = False
        self._pinged = False
        if self.sock and self.sock.connected:
            self.close()

    def sendMessage(self, content: str, reply_id: int = None):
        """发送聊天消息。"""
        load = {'type': 'message', 'content': content}
        if reply_id is not None:
            load['reply'] = reply_id
        self.send(json.dumps(load))

    def deleteMessage(self, msg_id: int):
        """删除聊天消息。"""
        deleteMessage(msg_id, self._token, self._config)

    def blockUser(self, uid: int):
        """拉黑指定uid。"""
        blockUser(uid, self._token, self._config)

    def unblockUser(self, uid: int):
        """取消拉黑指定uid。"""
        unblockUser(uid, self._token, self._config)


@startEnd
def getChatToken(config: Config = None) -> str:
    """获取聊天室chat_token。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.chatAPIBase}api/auth/exchange/"
    d = _request('post', 'json', 'loginChatRaw', url, config, {'main_token': config.token}, is_chat=True)
    return d['data']['chat_token']


@startEnd
def meRaw(chat_token: str, config: Config = None):
    """获取chat_token对应用户的信息。需要chat_token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.chatAPIBase}api/auth/me/"
    return _request('get', 'json', 'meRaw', url, config, is_chat=True, chat_token=chat_token)


@startEnd
def getBlockUsersRaw(chat_token: str, config: Config = None):
    """获取chat_token对应用户的已屏蔽用户。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.chatAPIBase}api/blocks/"
    return _request('get', 'json', 'getBlockUsersRaw', url, config, is_chat=True, chat_token=chat_token)


@startEnd
def getChatsRaw(config: Config = None) -> dict:
    """获取聊天室消息。
    在config.alwaysUseToken=True时，会发送请求以获得chat_token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.chatAPIBase}api/rooms/main/messages?limit={config.msgPerReq}"
    chat_token = None
    if config.alwaysUseToken:
        chat_token = getChatToken(config)
    return _request('get', 'json', 'getChatsRaw', url, config, is_chat=True,
                    chat_token=chat_token if config.alwaysUseToken else None)


def connectChat(room: str = 'main', config: Config = None, threaded: bool = True,
                on_open: Callable[[websocket.WebSocketApp], None] = None,
                on_message: Callable[[websocket.WebSocketApp, dict], None] = None,
                on_error: Callable[[websocket.WebSocketApp, Any], None] = None,
                on_close: Callable[[websocket.WebSocketApp, Any, Any], None] = None,
                on_ping: Callable = None,
                on_pong: Callable = None,
                on_reconnect: Callable[[websocket.WebSocketApp], None] = None,
                on_chat: Callable[[websocket.WebSocketApp, dict], None] = None
                ) -> Union[tuple[ChatClient, Thread], ChatClient]:
    """自动获取chat_token并连接聊天室。需要token。
    threaded: 是否开启新线程运行客户端。若为True，则返回(ChatClient, Thread)。否则返回ChatClient。
    on_chat: 收到聊天信息时的回调函数。
    on_message: 收到所有信息时的回调函数。"""
    if config is None:
        config = getGlobalConfig()
    token = getChatToken(config)
    client = ChatClient(token, room, config, on_open=on_open, on_reconnect=on_reconnect, on_message=on_message,
                        on_error=on_error, on_ping=on_ping, on_chat=on_chat, on_close=on_close, on_pong=on_pong)
    if threaded:
        thread = threading.Thread(target=client.run_forever, daemon=True)
        thread.start()
        return client, thread
    else:
        return client


@startEnd
def deleteMessage(msg_id: int, chat_token: str, config: Config = None):
    """删除消息。需要chat_token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.chatAPIBase}/api/messages/{msg_id}"
    return _request('delete', 'json', 'deleteMessage', url, config, is_chat=True, chat_token=chat_token)


@startEnd
def blockUser(uid: int, chat_token: str, config: Config = None):
    """拉黑指定uid。需要chat_token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.chatAPIBase}api/blocks/"
    return _request('post', 'json', 'blockUser', url, config, is_chat=True, chat_token=chat_token, data={'uid': uid})


@startEnd
def unblockUser(uid: int, chat_token: str, config: Config = None):
    """取消拉黑指定uid。需要chat_token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.chatAPIBase}api/blocks/{uid}"
    return _request('delete', 'json', 'unblockUser', url, config, is_chat=True, chat_token=chat_token)
