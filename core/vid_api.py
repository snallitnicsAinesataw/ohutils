from .util import startEnd, Comment, Danmaku, VideoEntry, _request, parseTime
from .config import Config, getGlobalConfig
from typing import Literal
from .exception import ExhaustedRetriesError, APIError


@startEnd
def getVideoDetailRaw(vid: int, config: Config = None) -> dict:
    """获取给定vid的数据。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/video/{vid}"
    return _request('get', 'json', 'getVideoDetailRaw', url, config=config).get('data', {})


@startEnd
def getAllDanmakuRaw(vid: int, config: Config = None) -> list:
    """获取给定vid的所有弹幕。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/danmaku/{vid}"
    return _request('get', 'json', 'getVideoDetailRaw', url, config=config).get('data', [])


def getAllDanmaku(vid: int) -> list[Danmaku]:
    """获取给定vid的所有弹幕。返回格式是list[Danmaku]而不是dict。"""
    resp = []
    ds = getAllDanmakuRaw(vid)
    for d in ds:
        resp.append(Danmaku.fromDict(d))
    return resp


@startEnd
def getPopularVideosRaw(time_limit_day: int = 7, offset: int = 0, config: Config = None):
    """获取视频｢热门榜｣。
    time_limit_day以｢天｣为单位，也可以使用常量ohutils.LIMIT_*以对应网页的｢本周热门｣、｢本月热门｣、｢本季热门｣。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/video/popular?time_limit={time_limit_day}&offset={offset}&num={config.videoPerReq}"
    return _request('get', 'json', "getPopularVideosRaw", url, config=config)


@startEnd
def getRandomVideosRaw(config: Config = None):
    """获取随机视频列表。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/video/random?num={config.videoPerReq}"
    return _request('get', 'json', "getRandomVideosRaw", url, config=config)


@startEnd
def getLatestVideosRaw(type_: Literal[0, 1, 3, 4, 5, 6, 7], offset: int = 0, config: Config = None):
    """获取最新的视频列表。
    type_支持的常量：ohutils.VT_*"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/video/new?offset={offset}&type={type_}&num={config.videoPerReq}"
    return _request('get', 'json', "getLatestVideosRaw", url, config=config)


@startEnd
def getVideoCollectionRaw(vid: int, config: Config = None) -> dict:
    """获取给定vid的所在合集。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/collection/videos/{vid}/collection"
    return _request('get', 'json', "getVideoCollectionsRaw", url, config=config)


@startEnd
def getVideoCommentListRaw(vid: int, offset: int = 0, parent_vcid: int = 0,
                           cid_asc: bool = True, include_pinned: bool = False, config: Config = None):
    """"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/comment/videos/{vid}?parent_vcid={parent_vcid}&offset={offset}"\
          f"&num={config.commentPerReq}&cid_asc={int(cid_asc)}&include_pinned={int(include_pinned)}"
    return _request('get', 'json', 'getVideoCommentListRaw', url, config=config)


@startEnd
def getAllVideoComments(vid: int, parent_vcid: int = 0,
                        include_pinned: bool = True, config: Config = None) -> list[Comment]:
    """递归拉取指定vid的所有评论。"""
    if config is None:
        config = getGlobalConfig()
    all_comments, offset = [], 0
    while True:
        if offset != 0 and config.verbose:
            print(f"[getAllVideoComments]curr offset: {offset}")
        try:
            data = getVideoCommentListRaw(vid, parent_vcid, offset, config.ascending, include_pinned, config)
        except ExhaustedRetriesError as e:
            if config.verbose:
                print(f"[getAllVideoComments]{config.colorRed}fail to get all comments: {e}")
            return []  # 过于激进?
        comment_list = data['data'].get("comment_list", [])
        if not comment_list:
            return []  # 过于激进?
        for c in comment_list:
            child_num = int(c.get("child_comment_num", 0))
            comment = Comment(
                cid=int(c["vcid"]),
                uid=int(c["uid"]),
                timestamp=parseTime(c['time']),
                content=c["content"],
                reply_count=c["child_comment_num"],
                replies=[],
                is_pinned=bool(c["is_pinned"]),
                pin_order=c["pin_order"],
                c_type='video'
            )
            if child_num > 0:
                if config.verbose:
                    print(f"[getAllVideoComments]Get replies of vcid{comment.cid}...")
                comment.replies = getAllVideoComments(vid, comment.cid, include_pinned, config)
            all_comments.append(comment)
        if len(comment_list) < config.commentPerReq:
            break
        offset += config.commentPerReq
        time.sleep(random.uniform(*config.commentBatchDelay))
    return all_comments
