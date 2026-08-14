from .util import _request, startEnd
from .config import Config, getGlobalConfig


@startEnd
def getRecChannelsRaw(page: int = 1, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"{config.APIBase}api/channel?page={page}&limit={config.channelsPerReq}"\
          f"&sort={config.sorting}&order={'asc' if config.ascending else 'desc'}"
    return _request('get', 'json', 'getRecChannelsRaw', url, config)


@startEnd
def getChannelDetailRaw(cid: int, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"{config.APIBase}api/channel/{cid}"
    return _request('get', 'json', 'getChannelDetailRaw', url, config)


@startEnd
def getChannelSectionsRaw(cid: int, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"{config.APIBase}api/channel/{cid}/sections"
    return _request('get', 'json', 'getChannelSectionsRaw', url, config)


@startEnd
def getChannelNoticeRaw(cid: int, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"{config.APIBase}api/channel/{cid}/notices"
    return _request('get', 'json', 'getChannelNoticeRaw', url, config)


@startEnd
def getChannelContentRaw(cid: int, type_: str = 'all', page: int = 1, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"{config.APIBase}api/channel/{cid}/content?type={type_}&page={page}"\
          f"&limit={config.channelsPerReq}&sort={config.sorting}&order={'asc' if config.ascending else 'desc'}"
    return _request('get', 'json', 'getRecChannelsRaw', url, config)
