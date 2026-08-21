from .util import (
    startEnd,
    Comment, Danmaku, VideoEntry,
    APIError,
    _request
)
from .config import Config, getGlobalConfig


@startEnd
def getVideoDetailRaw(vid: int, config: Config = None) -> dict:
    """获取给定视频的数据。"""
    if config is None:
        config = getGlobalConfig()
    url = f"{config.APIBase}api/video/{vid}"
    return _request('get', 'json', 'getVideoDetailRaw', url, config).get('data', {})


@startEnd
def getAllDanmakuRaw(vid: int, config: Config = None) -> list:
    """获取给定视频的所有弹幕。"""
    if config is None:
        config = getGlobalConfig()
    url = f"{config.APIBase}api/danmaku/{vid}"
    return _request('get', 'json', 'getVideoDetailRaw', url, config).get('data', [])


def getAllDanmaku(vid: int) -> list[Danmaku]:
    """获取给定视频的所有弹幕。返回格式是list[Danmaku]而不是dict。"""
    resp = []
    ds = getAllDanmakuRaw(vid)
    for d in ds:
        resp.append(Danmaku.fromDict(d))
    return resp


@startEnd
def getPopularVideosRaw(time_limit_day: int = 7, offset: int = 0, config: Config = None):
    """获取视频｢热门榜｣。"""
    if config is None:
        config = getGlobalConfig()
    url = f"{config.APIBase}api/video/popular?time_limit={time_limit_day}&offset={offset}&num={config.videoPerReq}"
    return _request('get', 'json', "getPopularVideosRaw", url, config)


@startEnd
def getRandomVideosRaw(config: Config = None):
    """获取随机视频列表。"""
    if config is None:
        config = getGlobalConfig()
    url = f"{config.APIBase}api/video/random?num={config.videoPerReq}"
    return _request('get', 'json', "getRandomVideosRaw", url, config)


@startEnd
def getLatestVideosRaw(type_: int, offset: int = 0, config: Config = None):
    """获取最新的视频列表。"""
    if config is None:
        config = getGlobalConfig()
    url = f"{config.APIBase}api/video/new?offset={offset}&type={type_}&num={config.videoPerReq}"
    return _request('get', 'json', "getLatestVideosRaw", url, config)
