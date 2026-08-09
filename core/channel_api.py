from .util import _requestJson, startEnd
from .config import Config, getGlobalConfig


@startEnd
def getRecChannelsRaw(page: int = 1, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/channel?page={page}&limit={config.channelsPerReq}"\
          f"&sort={config.sorting}&order={'asc' if config.ascending else 'desc'}"\
          f"&token={config.token}" if config.alwaysUseToken else ""
    return _requestJson('getRecChannelsRaw', url, config)


@startEnd
def getChannelDetailRaw(cid: int, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/channel/{cid}"+f"?token={config.token}" if config.alwaysUseToken else ""
    return _requestJson('getChannelDetailRaw', url, config)


@startEnd
def getChannelSectionsRaw(cid: int, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/channel/{cid}/sections"+f"?token={config.token}" if config.alwaysUseToken else ""
    return _requestJson('getChannelSectionsRaw', url, config)


@startEnd
def getChannelNoticeRaw(cid: int, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/channel/{cid}/notices"+f"?token={config.token}" if config.alwaysUseToken else ""
    return _requestJson('getChannelNoticeRaw', url, config)


@startEnd
def getChannelContentRaw(cid: int, type_: str = 'all', page: int = 1, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/channel/{cid}/content?type={type_}&page={page}"\
          f"&limit={config.channelsPerReq}&sort={config.sorting}&order={'asc' if config.ascending else 'desc'}"\
          f"&token={config.token}" if config.alwaysUseToken else ""
    return _requestJson('getRecChannelsRaw', url, config)
