from .util import _request, startEnd, _recur_request
from .config import Config, getGlobalConfig
from typing import Literal
from ._const import MAX_LIMIT


@startEnd
def getRecChannels(page: int = 1, config: Config = None) -> dict:
    """获取config.channelsPerReq条推荐的频道。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/channel?page={page}&limit={config.channelsPerReq}" \
          f"&sort={config.sorting}&order={'asc' if config.ascending else 'desc'}"
    return _request('get', 'json', 'getRecChannels', url, config=config)['data']


def getAllRecChannels(config: Config = None) -> list[dict]:
    """获取所有推荐的频道。"""
    if config is None:
        config = getGlobalConfig()
    def _fetch(page):
        resp = getRecChannels(page, config)
        pg = resp.get('pagination', {})
        return resp.get('channels', []), pg.get('total')   # 总条数
    return _recur_request('getAllRecChannels', _fetch, config.channelsPerReq,
                          config.pagingDelay, is_page=True, config=config)


@startEnd
def getChannelDetail(cid: int, config: Config = None) -> dict:
    """获取特定频道的数据。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/channel/{cid}"
    return _request('get', 'json', 'getChannelDetail', url, config=config)['data']


@startEnd
def getChannelSections(cid: int, config: Config = None) -> dict:
    """获取特定频道的所有分区。"""
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
def _getChannelContents(cid: int, type_, page: int, section_id: int, config: Config) -> dict:
    url = f"https://{config.APIBase}api/channel/{cid}/content?type={type_}&page={page}" \
          f"&limit={config.channelsPerReq}&order={'asc' if config.ascending else 'desc'}" + \
          (f'&sort={config.sorting}' if config.sorting != 'random' else '') + \
          ('&random=true' if config.sorting == 'random' else '') + \
          (f'&channel_section_id={section_id}' if section_id is not None else '')
    return _request('get', 'json', '_getChannelContents', url, config=config)['data']


@startEnd
def getAllChannelContents(cid: int, type_: Literal['all', 'blog', 'video'] = 'all',
                          section_id: int = None, config: Config = None) -> list[dict]:
    """获取特定频道的所有内容。提供section_is以获取特定分区的内容。
    type_支持的常量: ohutils.CT_*；使用config.blogPerReq。"""
    def _fetch(page):
        resp = _getChannelContents(cid, type_, page, section_id, config)
        pg = resp.get('pagination', {})
        return resp.get('content', []), pg.get('total')  # 总条数
    return _recur_request('getChannelContents', _fetch, config.blogPerReq,
                          config.pagingDelay, is_page=True, config=config)


@startEnd
def getChannelPins(cid: int, config: Config = None) -> dict:
    """获取特定频道的置顶。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/channel/{cid}/pins?order={'asc' if config.ascending else 'desc'}" \
          f"&limit={MAX_LIMIT}"
    return _request('get', 'json', 'getChannelPins', url, config=config)['data']
