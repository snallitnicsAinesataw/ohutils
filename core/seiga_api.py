import random
import time
from .util import _request, startEnd
from .config import Config, getGlobalConfig
import os
from typing import Literal


@startEnd
def getPopularTagsRaw(offset: int = 0, config: Config = None) -> dict:
    """获取静画｢热门标签｣列表。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/seiga/tags/popular?offset={offset}&num={config.tagsPerReq}&is_gore={int(config.gore)}"
    return _request('get', 'json', 'getPopularTagsRaw', url, config=config)


@startEnd
def getRankedSeigaRaw(offset: int = 0, is_doujin: bool = False, is_hall: bool = False,
                      time_limit: Literal['daily', 'weekly', 'monthly', 'all'] = 'daily', config: Config = None) -> dict:
    """获取静画｢按时段统计的排行榜｣。
    time_limit支持的常量：ohutils.SG_*"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/seiga/ranking?offset={offset}&num={config.seigaPerReq}&is_gore={int(config.gore)}"\
          f"&is_fanwork={int(is_doujin)}&is_hall={int(is_hall)}&span={time_limit}"
    return _request('get', 'json', 'getRankedSeigaRaw', url, config=config)


@startEnd
def getSeigaByTagsRaw(tag: str, offset: int = 0, config: Config = None) -> dict:
    """获取指定标签下的静画。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/seiga/search?tag={tag}&offset={offset}&num={config.seigaPerReq}&is_gore={int(config.gore)}"
    return _request('get', 'json', 'getSeigaByTagsRaw', url, config=config)


@startEnd
def getSeigaDetailRaw(sid: int, config: Config = None) -> dict:
    """获取指定sid的静画数据。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/seiga/{sid}"
    return _request('get', 'json', 'getSeigaDetailRaw', url, config=config)


@startEnd
def downloadSeiga(sid: int, config: Config = None) -> bool:
    """下载指定sid的静画。"""
    if config is None:
        config = getGlobalConfig()
    all_seiga: list = getSeigaDetailRaw(sid, config)['data']['pages']
    for s in all_seiga:
        pg, url = s['page_no'], s['original_url']
        content = _request('get', 'content', 'downloadSeiga', url, config=config)
        with open(os.path.join(config.seigaPath, config.seigaName.format(sid=sid, page=pg)), "wb") as f:
            f.write(content)
        time.sleep(random.uniform(*config.seigaDelay))
    return True


@startEnd
def getSeigaTagsRaw(sid: int, config: Config = None) -> dict:
    """获取指定sid的静画标签。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/seiga/{sid}/tags"
    return _request('get', 'json', 'getSeigaTagsRaw', url, config=config)


@startEnd
def getRelatedSeigaRaw(sid: int, offset: int = 0, config: Config = None) -> dict:
    """获取指定sid的一组｢相关推荐｣(不递归)。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/seiga/related/{sid}?offset={offset}&num={config.seigaPerReq}&is_gore={config.gore}"
    return _request('get', 'json', 'getRelatedSeigaRaw', url, config=config)


@startEnd
def getSeigaCommentListRaw(sid: int, parent_scid = 0, offset: int = 0, config: Config = None) -> dict:
    """获取指定sid的一组评论(不递归)。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/comment/seigas/{sid}?parent_scid={parent_scid}&offset={offset}"\
          f"&num={config.commentPerReq}&cid_asc={config.ascending}"
    return _request('get', 'json', 'getBlogCommentListRaw', url, config=config)


@startEnd
def getSeigaCollectionsRaw(sid: int, config: Config = None) -> dict:
    """获取指定sid所属的合集。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/collection/seigas/{sid}/collection/"
    return _request('get', 'json', 'getSeigaCollectionsRaw', url, config=config)

