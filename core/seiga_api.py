import random
import time
from .util import _request, startEnd, Comment, logger, _format, _fn_formatTime, parseTime
from .config import Config, getGlobalConfig
from .exception import NotInCollectionError
from ._const import _RED, DEFAULT_TS
import os
from typing import Literal, Union


@startEnd
def getPopularTags(offset: int = 0, config: Config = None) -> list:
    """获取静画｢热门标签｣列表。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/seiga/tags/popular?offset={offset}&num={config.tagsPerReq}&is_gore={int(config.gore)}"
    return _request('get', 'json', 'getPopularTags', url, config=config)['data']['tag_list']


@startEnd
def getRankedSeiga(offset: int = 0, is_doujin: bool = False, is_hall: bool = False,
                   time_limit: Literal['daily', 'weekly', 'monthly', 'all'] = 'daily', config: Config = None) -> list:
    """获取静画｢按时段统计的排行榜｣。
    time_limit支持的常量：ohutils.SG_*"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/seiga/ranking?offset={offset}&num={config.seigaPerReq}&is_gore={int(config.gore)}" \
          f"&is_fanwork={int(is_doujin)}&is_hall={int(is_hall)}&span={time_limit}"
    return _request('get', 'json', 'getRankedSeiga', url, config=config)['data']['seiga_list']


@startEnd
def getSeigaByTags(tag: str, offset: int = 0, config: Config = None) -> list:
    """获取指定标签下的静画。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/seiga/search?tag={tag}&offset={offset}&num={config.seigaPerReq}&is_gore={int(config.gore)}"
    return _request('get', 'json', 'getSeigaByTags', url, config=config)['data']['seiga_list']


@startEnd
def getSeigaDetail(sid: int, config: Config = None) -> dict:
    """获取指定sid的静画数据。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/seiga/{sid}"
    return _request('get', 'json', 'getSeigaDetail', url, config=config)['data']


@startEnd
def downloadSeiga(sid: int, config: Config = None) -> bool:
    """下载指定sid的静画。"""
    if config is None:
        config = getGlobalConfig()
    seiga: dict = getSeigaDetail(sid, config)
    all_seiga: list = seiga['pages']

    pub_ts = parseTime(seiga['time']) if seiga['time'] else DEFAULT_TS
    for s in all_seiga:
        pg, url = s['page_no'], s['original_url']
        content = _request('get', 'content', 'downloadSeiga', url, config=config)

        fn = _format(config.seigaPath, sid=sid, page=pg, pubts=pub_ts, pubftime=_fn_formatTime(pub_ts),
                     uid=int(seiga['uid']))
        with open(os.path.join(config.seigaPath, fn), "wb") as f:
            f.write(content)
        time.sleep(random.uniform(*config.pagingDelay))
    return True


@startEnd
def getSeigaTags(sid: int, config: Config = None) -> dict:
    """获取指定sid的静画标签。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/seiga/{sid}/tags"
    res = _request('get', 'json', 'getSeigaTags', url, config=config)
    del res['sid']
    return res


@startEnd
def getRelatedSeiga(sid: int, offset: int = 0, config: Config = None) -> list[dict]:
    """获取指定sid的一组｢相关推荐｣(不递归)。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/seiga/related/{sid}?offset={offset}&num={config.seigaPerReq}&is_gore={int(config.gore)}"
    return _request('get', 'json', 'getRelatedSeiga', url, config=config)['data']['seiga_list']


@startEnd
def _getSeigaCommentList(sid: int, parent_scid=0, offset: int = 0, config: Config = None) -> list[dict]:
    """获取指定sid的一组评论(不递归)。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/comment/seigas/{sid}?parent_scid={parent_scid}&offset={offset}" \
          f"&num={config.commentPerReq}&cid_asc={config.ascending}"
    return _request('get', 'json', '_getSeigaCommentList', url, config=config)['data']['comment_list']


@startEnd
def getSeigaCollection(sid: int, config: Config = None) -> Union[dict, None]:
    """获取指定sid所属的合集。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/collection/seigas/{sid}/collection/"
    try:
        return _request('get', 'json', 'getSeigaCollection', url, config=config)
    except NotInCollectionError:
        return None


@startEnd
def getAllSeigaComments(sid: int, parent_scid: int = 0, config: Config = None) -> list[Comment]:
    """递归拉取指定sid的所有评论。"""
    if config is None:
        config = getGlobalConfig()
    all_comments, offset = [], 0
    while True:
        if offset != 0 and config.verbose:
            logger.info(f"[getAllSeigaComments]curr offset: {offset}")
        try:
            comment_list = _getSeigaCommentList(sid, parent_scid, offset, config)
        except ExhaustedRetriesError as e:
            t_ = f"fail to get all comments: {e}"
            logger.error(f"[getAllSeigaComments]{_c(_RED, t_, config)}")
            return []  # 过于激进?
        if not comment_list:
            return []  # 过于激进?
        for c in comment_list:
            child_num = int(c.get("child_comment_num", 0))
            comment = Comment(
                cid=int(c["scid"]),
                uid=int(c["uid"]),
                timestamp=parseTime(c['time']),
                content=c["content"],
                reply_count=c["child_comment_num"],
                replies=[],
                is_pinned=False,
                pin_order=c["pin_order"],
                c_type='seiga',
                parent_cid=int(c['parent_scid'])
            )
            if child_num > 0:
                if config.verbose:
                    logger.info(f"[getAllSeigaComments]Get replies of scid{comment.cid}...")
                comment.replies = getAllSeigaComments(sid, comment.cid, config)
            all_comments.append(comment)
        if len(comment_list) < config.commentPerReq:
            break
        offset += config.commentPerReq
        time.sleep(random.uniform(*config.pagingDelay))
    return all_comments
