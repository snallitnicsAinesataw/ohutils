from .util import _request, startEnd
from .config import Config, getGlobalConfig
from typing import Literal


@startEnd
def getRecChannels(page: int = 1, config: Config = None) -> dict:
    """获取推荐的频道。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/channel?page={page}&limit={config.channelsPerReq}"\
          f"&sort={config.sorting}&order={'asc' if config.ascending else 'desc'}"
    return _request('get', 'json', 'getRecChannels', url, config=config)['data']


@startEnd
def getChannelDetail(cid: int, config: Config = None) -> dict:
    """获取特定频道的数据。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/channel/{cid}"
    return _request('get', 'json', 'getChannelDetail', url, config=config)['data']


@startEnd
def getChannelSections(cid: int, config: Config = None) -> dict:
    """获取特定频道的分区。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/channel/{cid}/sections"
    return _request('get', 'json', 'getChannelSections', url, config=config)['data']


@startEnd
def getChannelNotices(cid: int, config: Config = None) -> dict:
    """获取特定频道的公告。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/channel/{cid}/notices"
    return _request('get', 'json', 'getChannelNotices', url, config=config)['data']


@startEnd
def getChannelContents(cid: int, type_: Literal['all', 'blog', 'video'] = 'all',
                       page: int = 1, config: Config = None) -> dict:
    """获取特定频道的内容(不递归)。
    type_支持的常量: ohutils.CT_*"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/channel/{cid}/content?type={type_}&page={page}"\
          f"&limit={config.channelsPerReq}&sort={config.sorting}&order={'asc' if config.ascending else 'desc'}"
    return _request('get', 'json', 'getChannelContents', url, config=config)['data']
