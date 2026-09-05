from .util import startEnd, _request
from .config import Config, getGlobalConfig


@startEnd
def getUnreadMsgNum(config: Config = None) -> int:
    """获取未读消息数。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/im/unread-count?token={config.token}"
    return int(_request('get', 'json', 'getUnreadMsgNum', url, config=config)['data']['new_message_num'])


@startEnd
def getUnreadModerationNum(config: Config = None) -> dict:
    """获取未读审核日志数。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/moderation/logs/unread-count?token={config.token}"
    return _request('get', 'json', 'getUnreadModerationNum', url, config=config)['data']


@startEnd
def getCommentRepliesNum(config: Config = None) -> int:
    """获取｢评论我的｣消息数。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/im/comment-replies/unread-count?token={config.token}"
    return int(_request('get', 'json', 'getCommentRepliesNum', url, config=config)['data']['unread_count'])


@startEnd
def getMentionsNum(config: Config = None) -> int:
    """获取｢@我的｣消息数。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/im/mentions/unread-count?token={config.token}"
    return int(_request('get', 'json', 'getMentionsNum', url, config=config)['data']['unread_count'])


@startEnd
def getUnreadCounts(config: Config = None) -> dict:
    """获取未读消息数。需要token。"""
    if config is None:
        config = getGlobalConfig()
    im = getUnreadMsgNum(config)
    mod = getUnreadModerationNum(config)
    mod['unread_moderation'] = mod['unread_count']
    del mod['unread_count']
    mod['unread_im'] = im
    mention = getMentionsNum(config)
    mod['unread_mentions'] = mention
    repl = getCommentRepliesNum(config)
    mod['unread_replies'] = repl
    return mod


@startEnd
def getIM(receiver: int, offset: int = 0, config: Config = None) -> list:
    """获取与指定uid的私信记录。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/im/conversations/{receiver}/messages?offset={offset}"\
          f"&num={config.msgPerReq}&if_time_desc={int(not config.ascending)}&token={config.token}"
    return _request('get', 'json', 'getIM', url, config=config)['data']['message_list']


@startEnd
def getModeration(offset: int = 0, config: Config = None) -> list[dict]:
    """获取审核日志。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/moderation/logs?offset={offset}&num={config.modLogPerReq}&token={config.token}"
    return _request('get', 'json', 'getModeration', url, config=config)['data']['logs']


@startEnd
def sendIM(receiver: int, msg: str, config: Config = None):
    """发送私信至指定uid。需要token。"""
    if config is None:
        config = getGlobalConfig()
    data = {'token': config.token, 'receiver': receiver, 'message': msg}
    return _request('post', 'json', "sendIM", f"https://{config.APIBase}api/im/messages", config=config, data=data)


@startEnd
def getCommentReplies(offset: int = 0, num: int = 20, config: Config = None) -> list[dict]:
    """获取｢评论我的｣消息。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f'https://{config.APIBase}api/im/comment-replies?offset={offset}&num={num}&token={config.token}'
    return _request('get', 'json', 'getCommentReplies', url, config=config)['data']['list']


@startEnd
def getMentions(offset: int = 0, num: int = 20, config: Config = None) -> list[dict]:
    """获取｢@我的｣消息。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f'https://{config.APIBase}api/im/mentions?offset={offset}&num={num}&token={config.token}'
    return _request('get', 'json', 'getMentions', url, config=config)['data']['list']