from .util import startEnd, _request
from .config import Config, getGlobalConfig


@startEnd
def getUnreadMsgNumRaw(config: Config = None) -> dict:
    """获取未读消息数。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/im/unread-count?token={config.token}"
    return _request('get', 'json', 'getUnreadMsgNumRaw', url, config=config)


@startEnd
def getUnreadModerationNumRaw(config: Config = None) -> dict:
    """获取未读审核日志数。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/moderation/logs/unread-count?token={config.token}"
    return _request('get', 'json', 'getUnreadModerationNumRaw', url, config=config)


@startEnd
def getCommentRepliesNumRaw(config: Config = None) -> dict:
    """获取｢评论我的｣消息数。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/im/comment-replies/unread-count?token={config.token}"
    return _request('get', 'json', 'getCommentRepliesNumRaw', url, config=config)


@startEnd
def getMentionsNumRaw(config: Config = None) -> dict:
    """获取｢@我的｣消息数。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/im/mentions/unread-count?token={config.token}"
    return _request('get', 'json', 'getMentionsNumRaw', url, config=config)


@startEnd
def getUnreadCounts(config: Config = None) -> dict:
    """获取未读消息数。需要token。"""
    if config is None:
        config = getGlobalConfig()
    im = getUnreadMsgNumRaw(config)['data']['new_message_num']
    mod = getUnreadModerationNumRaw(config)['data']
    mod['unread_moderation'] = mod['unread_count']
    del mod['unread_count']
    mod['unread_im'] = int(im)
    mention = getMentionsNumRaw(config)['data']['unread_count']
    mod['unread_mentions'] = mention
    repl = getCommentRepliesNumRaw(config)['data']['unread_count']
    mod['unread_replies'] = repl
    return mod


@startEnd
def getIMRaw(receiver: int, offset: int = 0, config: Config = None) -> dict:
    """获取与指定uid的私信记录。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/im/conversations/{receiver}/messages?offset={offset}"\
          f"&num={config.msgPerReq}&if_time_desc={int(not config.ascending)}&token={config.token}"
    return _request('get', 'json', 'getIMRaw', url, config=config)


@startEnd
def getModerationRaw(offset: int = 0, config: Config = None) -> dict:
    """获取审核日志。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/moderation/logs?offset={offset}&num={config.modLogPerReq}&token={config.token}"
    return _request('get', 'json', 'getModerationRaw', url, config=config)


@startEnd
def sendIM(receiver: int, msg: str, config: Config = None):
    """发送私信至指定uid。需要token。"""
    if config is None:
        config = getGlobalConfig()
    data = {'token': config.token, 'receiver': receiver, 'message': msg}
    return _request('post', 'json', "sendIM", f"https://{config.APIBase}api/im/messages", config=config, data=data)


@startEnd
def getCommentRepliesRaw(offset: int = 0, num: int = 20, config: Config = None) -> dict:
    """获取｢评论我的｣消息。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f'https://{config.APIBase}api/im/comment-replies?offset={offset}&num={num}&token={config.token}'
    return _request('get', 'json', 'getCommentRepliesRaw', url, config=config)


@startEnd
def getMentionsRaw(offset: int = 0, num: int = 20, config: Config = None) -> dict:
    """获取｢@我的｣消息。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f'https://{config.APIBase}api/im/mentions?offset={offset}&num={num}&token={config.token}'
    return _request('get', 'json', 'getMentionsRaw', url, config=config)