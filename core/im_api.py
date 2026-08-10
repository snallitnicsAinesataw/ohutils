from .util import startEnd, _request
from .config import Config, getGlobalConfig


@startEnd
def getUnreadMsgNumRaw(config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/im/unread-count?token={config.token}"
    return _request('get', 'json', 'getUnreadMsgNumRaw', url, config)


@startEnd
def getUnreadModerationNumRaw(config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/moderation/logs/unread-count?token={config.token}"
    return _request('get', 'json', 'getUnreadModerationNumRaw', url, config)


@startEnd
def getUnreadCounts(config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    im = getUnreadMsgNumRaw(config)['data']['new_message_num']
    mod = getUnreadModerationNumRaw(config)['data']
    mod['unread_moderation'] = mod['unread_count']
    del mod['unread_count']
    mod['unread_im'] = im
    return mod


@startEnd
def getIMRaw(receiver: int, offset: int = 0, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/im/conversations/{receiver}/messages?offset={offset}"\
          f"&num={config.msgPerReq}&if_time_desc={int(not config.ascending)}&token={config.token}"
    return _request('get', 'json', 'getIMRaw', url, config)


@startEnd
def getModerationRaw(offset: int = 0, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"https://www.ottohub.cn/api/moderation/logs?offset={offset}&num={config.modLogPerReq}&token={config.token}"
    return _request('get', 'json', 'getModerationRaw', url, config)


@startEnd
def sendIM(receiver: int, msg: str, config: Config = None):
    if config is None:
        config = getGlobalConfig()
    data = {'token': config.token, 'receiver': receiver, 'message': msg}
    return _postJson('post', 'json', "sendIM", "https://www.ottohub.cn/api/im/messages", config, data)
