import time
from .util import _request, startEnd
from .config import Config, getGlobalConfig
import os


@startEnd
def getPopularTagsRaw(offset: int = 0, config: Config = None) -> dict:
    """请求｢热门标签｣。
    返回格式：{status:str, data:[{tag_id:int, tag_name:str, use_count:int}, ...]}"""
    if config is None:
        config = getGlobalConfig()
    url = f"{config.APIBase}api/seiga/tags/popular?offset={offset}&num={config.tagsPerReq}&is_gore={int(config.gore)}"
    return _request('get', 'json', 'getPopularTagsRaw', url, config)


@startEnd
def getRankedSeigaRaw(offset: int = 0, is_doujin: bool = False, is_hall: bool = False,
                      time_limit: str = 'daily', config: Config = None) -> dict:
    """请求｢按时段统计的排行榜｣。
    time_limit支持的常量：ottosave.SG_*"""
    if config is None:
        config = getGlobalConfig()
    url = f"{config.APIBase}api/seiga/ranking?offset={offset}&num={config.seigaPerReq}&is_gore={int(config.gore)}"\
          f"&is_fanwork={int(is_doujin)}&is_hall={int(is_hall)}&span={time_limit}"
    return _request('get', 'json', 'getRankedSeigaRaw', url, config)


@startEnd
def getSeigaByTagsRaw(tag: str, offset: int = 0, config: Config = None) -> dict:
    """请求给定标签下的静画作品"""
    if config is None:
        config = getGlobalConfig()
    url = f"{config.APIBase}api/seiga/search?tag={tag}&offset={offset}&num={config.seigaPerReq}&is_gore={int(config.gore)}"
    return _request('get', 'json', 'getSeigaByTagsRaw', url, config)


@startEnd
def getSeigaDataRaw(sid: int, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"{config.APIBase}api/seiga/{sid}"
    return _request('get', 'json', 'getSeigaDetailRaw', url, config)


@startEnd
def downloadSeiga(sid: int, config: Config = None) -> bool:
    if config is None:
        config = getGlobalConfig()
    all_seiga: list = getSeigaDataRaw(sid, config)['data']['pages']
    for s in all_seiga:
        pg, url = s['page_no'], s['original_url']
        content = _request('get', 'content', 'downloadSeiga', url, config)
        with open(os.path.join(config.seigaPath, config.seigaName%(sid, pg)), "wb") as f:
            f.write(content)
        time.sleep(1)
    return True
