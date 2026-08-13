from .util import (
    startEnd,
    Comment, Danmaku, VideoEntry,
    APIError,
    _request
)
import requests
from typing import List
from .config import Config, getGlobalConfig


@startEnd
def getVideoDetailRaw(vid: int, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/video/{vid}"
    return _request('get', 'json', 'getVideoDetailRaw', url, config).get('data', {})


@startEnd
def getAllDanmakuRaw(vid: int, config: Config = None) -> list:
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/danmaku/{vid}"
    return _request('get', 'json', 'getVideoDetailRaw', url, config).get('data', [])


def getAllDanmaku(vid: int) -> List[Danmaku]:
    """idk how to deal with it"""
    resp = []
    ds = getAllDanmakuRaw(vid)
    for d in ds:
        resp.append(Danmaku.fromDict(d))
    return resp


@startEnd
def getPopularVideosRaw(time_limit_day: int = 7, offset: int = 0, config: Config = None):
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/video/popular?time_limit={time_limit_day}&offset={offset}&num={config.videoPerReq}"
    return _request('get', 'json', "getPopularVideosRaw", url, config)


@startEnd
def getRandomVideosRaw(config: Config = None):
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/video/random?num={config.videoPerReq}"
    return _request('get', 'json', "getRandomVideosRaw", url, config)


@startEnd
def getLatestVideosRaw(type_: int, offset: int = 0, config: Config = None):
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/video/new?offset={offset}&type={type_}&num={config.videoPerReq}"
    return _request('get', 'json', "getLatestVideosRaw", url, config)
