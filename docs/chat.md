# 2.1 聊天室API
此文档对应`core\chat_api.py`。

所有的`time_str`结构为`YYYY-MM-DD HH:MM:SS`，可以使用`parseTime`处理为时间戳。

---
## 2.1.1 getChatToken()
`getChatToken(config: Config = None) -> str`

获取聊天室所需要的`chat_token`。

 - **参数**: *可选* `config` -> Config对象。需要在对象中包含有效`token`。不提供则使用全局配置或`useConfig(...)`设定的配置。
 - **返回**: `chat_token` (e.g. `'f339af2b...50a5'`)。

## 2.1.2 meRaw()
`meRaw(chat_token: str, config: Config = None) -> dict`

获取提供的`chat_token`对应用户的信息原始数据。

 - **参数**:
   - `chat_token: str` -> 聊天室token。
   - *可选* `config` -> Config对象。不提供则使用全局配置或`useConfig(...)`设定的配置。
 - **返回**: 字典`data{uid: int, username: str, is_admin: int, mute}`。
 - **注**: `mute`字段当前未知具体含义。

## 2.1.3 getChats()
`getChats(config: Config = None) -> dict`

获取聊天室消息和公告。在`config.alwaysUseToken=True`时，会发送请求以获得`chat_token`。

 - **参数**: *可选* `config` -> Config对象。不提供则使用全局配置或`useConfig(...)`设定的配置。
 - **返回**: 字典。
   - `{room: str, pinned_announcement: dict, message_list: list[dict]}`
   - **pinned_announcement**: `{room: str, content: str, pinned: bool, updated_by: int, updated_at: time_str}`。
   - **message_list**: `[{id: int, room: str, uid: int, username: str, content: str, created_at: time_str, reply: dict?},...]`
   - **reply**: `{id: int, uid: int, username: str, content: str, deleted: bool}`。若为`None`则表示不回复消息。
 
## 2.1.4 connectChat()
`connectChat(room, config, threaded, beat_interval, 
on_open, on_message, on_error, on_close, on_ping, on_pong, on_reconnect, on_chat, on_online_change, on_welcome)
  -> tuple[ChatClient, Thread] | ChatClient`

自动获取`chat_token`并连接聊天室。

 - **参数**: 
   - *可选* `room` -> 房间名。默认为`main`，对应[主聊天室](https://www.ottohub.cn/chat/) 。
   - *可选* `config` -> Config对象。不提供则使用全局配置或`useConfig(...)`设定的配置。
   - *可选* `threaded` -> 是否开启新线程运行客户端。默认为`True`。
    否则返回`ChatClient`实例，此时需要手动调用`client.run_forever()`以运行客户端。
   - *可选* `beat_interval` -> 发送ping包的时间间隔。默认为30，单位：**秒**。
   - *可选* `on_open` -> 在WebSocket打开时调用的回调函数。接收一个参数，为WebSocket实例。 
   - *可选* `on_reconnect` -> 在WebSocket重新连接时调用的回调函数。接收一个参数，为WebSocket实例。
   - *可选* `on_message` -> 在接收到数据时调用的回调函数。接收两个参数，第一个参数为WebSocket实例，第二个参数是从服务器接收到的字典。
     - 第二个参数格式:
     `{type: welcome/pong/online_count/message/message_deleted, ...}`
     - **其他键值随`type`改变。见下方 ｢2.1.4.2 on_message格式｣。**
   - *可选* `on_error` -> 在发生错误时调用的回调函数。接收两个参数，第一个参数为WebSocket实例，第二个参数是异常对象。  
   - *可选* `on_close` -> 在连接关闭时调用的回调函数。接收三个参数，第一个参数为WebSocket实例，第二个参数是关闭状态码，第三个参数是关闭消息。
   - *可选* `on_ping` -> *透传至内部WebSocketApp，不做处理。*
   - *可选* `on_pong` -> *透传至内部WebSocketApp，不做处理。*
   - *可选* `on_chat` -> 在收到**聊天信息**时调用的回调函数。接收两个参数，第一个参数为WebSocket实例，第二个参数是从服务器接收到的字典。
   - *可选* `on_online_change` -> 收到 **｢在线人数更改｣** 时调用的回调函数。接收两个参数，第一个参数为WebSocket实例，第二个参数是从服务器接收到的字典。
   - *可选* `on_welcome` -> 收到**欢迎信息**时调用的回调函数。接收两个参数，第一个参数为WebSocket实例，第二个参数是从服务器接收到的字典。
 - **返回**：
   - 当`threaded`为`True`时：返回`(ChatClient实例, threading.Thread)`。
   - 当`threaded`为`False`时：返回`ChatClient`实例。**此时需要手动调用`client.run_forever()`以运行客户端**。
 - **注意**：
   - 即使传递了`on_chat`/`on_message`/`on_online_change`参数, `on_message`**仍会被调用**。
 
### 2.1.4.2 on_message格式
| `type`            | 其它键值                                                                                                                           |
|-------------------|:-------------------------------------------------------------------------------------------------------------------------------|
| `pong`            | 无其它键值。                                                                                                                         |
| `welcome`         | `is_admin` -> 是否为管理员。在默认行为下，此值会存储为`is_admin: bool`。                                                                            |
|                   | `mute` -> 禁言状态。在默认行为下，此值会存储为`mute`。                                                                                            |
|                   | `pinned_announcement{room, content, pinned, updated_by: int, updated_at: time_str}` -> 置顶公告。在默认行为下，此值会存储为`announcement: dict`。 |
|                   | `role` -> 角色。在默认行为下，此值会存储为`role`。                                                                                              |
|                   | `room` -> 房间名称。                                                                                                                |
|                   | `uid` -> `chat_token`所对应`uid`。在默认行为下，此值会存储为`uid`。                                                                              |
|                   | `name` -> `chat_token`所对应`uid`的用户名。在默认行为下，此值会存储为`name`。                                                                        |
| `online_count`    | `room` -> 房间名称。                                                                                                                |
|                   | `count` -> 房间人数。                                                                                                               |
| `message`         | `id` -> 消息id。                                                                                                                  |
|                   | `room` -> 房间名称。                                                                                                                |
|                   | `uid` -> 发送者uid。                                                                                                               |
|                   | `username` -> 发送者名称。                                                                                                           |
|                   | `content` -> 消息内容。                                                                                                             |
|                   | `created_at: time_str` -> 消息发送时间。                                                                                              |
|                   | `reply{id, uid, username, content, deleted}或None` -> 回复的消息。                                                                    |
| `message_deleted` | `id` -> 消息id。                                                                                                                  |
|                   | `room` -> 房间名称。                                                                                                                |

## 2.1.5 ChatClient类
> **通常不需要直接实例化**，而是使用`connectChat()`创建。

聊天室客户端。`websocket.WebSocketApp`的包装。
**参数**见 2.1.4。

### 2.1.5.2 client.sendMessage()
`client.sendMessage(self, content: str, reply_id: int = None) -> None`

发送消息。

 - **参数**：
   - `content` -> 消息内容。
   - *可选* `reply_id` -> 回复的消息id。

### 2.1.5.3 client.deleteMessage()
`client.deleteMessage(self, msg_id: int) -> None`

删除聊天消息。**参数**: `msg_id` -> 消息id。

### 2.1.5.4 client.blockUser() & client.unblockUser()
`client.blockUser(self, uid: int) -> None` `client.unblockUser(self, uid: int) -> None`

拉黑/取消拉黑指定uid。

### 2.1.5.5 getBlockUsers()
`client.getBlockUsers(self) -> list`

返回拉黑用户列表`[{uid, username, created_at: time_str},...]`。

## 2.1.6 deleteMessage(), blockUser(), unblockUser(), getBlockUsers()
> **不建议直接使用。** 应使用connectChat()返回的ChatClient进行操作。

`blockUser(uid: int, chat_token: str, config: Config = None) -> None`

`unblockUser(uid: int, chat_token: str, config: Config = None) -> None`

`deleteMessage(msg_id: int, chat_token: str, config: Config = None) -> None`

`getBlockUsers(chat_token: str, config: Config = None) -> list`

- **通用参数**:
   - `chat_token: str` -> 聊天室token。
   - *可选* `config` -> Config对象。不提供则使用全局配置或`useConfig(...)`设定的配置。
   - 其它参数定义见2.1.5.3，2.1.5.4，2.1.5.5。
   