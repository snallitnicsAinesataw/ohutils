from .util import startEnd, Comment, Danmaku, VideoEntry, _request, parseTime, logger, _c, _format, _fn_2hms, \
    _fn_formatTime, _temp_name, _tag_factory, Staff
from .config import Config, getGlobalConfig
from typing import Literal, Union
from .exception import ExhaustedRetriesError, NotInCollectionError, FileTooBigError, InvalidFileFormatError
from ._const import _RED, DEFAULT_TS, _MAX_VIDEO, _MAX_COVER
from requests import Response
import os
from pathlib import Path
import time
import random
from ._dur import checkDurI
import mimetypes
from urllib.parse import quote
from dataclasses import asdict


@startEnd
def getVideoDetail(vid: int, config: Config = None) -> dict:
    """获取给定vid的数据。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/video/{vid}"
    return _request('get', 'json', 'getVideoDetail', url, config=config)['data']


@startEnd
def getAllDanmaku(vid: int, config: Config = None) -> list[Danmaku]:
    """获取给定vid的所有弹幕。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/danmaku/{vid}"
    ds = _request('get', 'json', 'getAllDanmaku', url, config=config).get('data', [])
    resp = []
    for d in ds:
        resp.append(Danmaku(
            danmaku_id=int(d['danmaku_id']),
            text=d['text'],
            time_ms=int(float(d['time']) * 1000),
            mode=d['mode'],
            color_rgb=int(d['color'].lstrip('#'), 16),
            font_size=int(d['font_size'].replace('px', '')),
            render=d.get('render', ''),
        ))
    return resp


@startEnd
def getPopularVideos(time_limit_day: int = 7, offset: int = 0, config: Config = None) -> list[dict]:
    """获取视频｢热门榜｣。
    time_limit_day以｢天｣为单位，也可以使用常量ohutils.LIMIT_*以对应网页的｢本周热门｣、｢本月热门｣、｢本季热门｣。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/video/popular?time_limit={time_limit_day}&offset={offset}&num={config.videoPerReq}"
    return _request('get', 'json', "getPopularVideos", url, config=config)['data']['video_list']


@startEnd
def getRandomVideos(config: Config = None) -> list[dict]:
    """获取随机视频列表。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/video/random?num={config.videoPerReq}"
    return _request('get', 'json', "getRandomVideos", url, config=config)['data']['video_list']


@startEnd
def getLatestVideos(type_: Literal[0, 1, 3, 4, 5, 6, 7], offset: int = 0, config: Config = None) -> list[dict]:
    """获取最新的视频列表。
    type_支持的常量：ohutils.VT_*"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/video/new?offset={offset}&type={type_}&num={config.videoPerReq}"
    return _request('get', 'json', "getLatestVideos", url, config=config)['data']['video_list']


@startEnd
def getVideoCollection(vid: int, config: Config = None) -> Union[dict, None]:
    """获取给定vid的所在合集。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/collection/videos/{vid}/collection"
    try:
        return _request('get', 'json', "getVideoCollection", url, config=config)
    except NotInCollectionError:
        return None


@startEnd
def _getVideoCommentList(vid: int, offset: int = 0, parent_vcid: int = 0,
                         cid_asc: bool = True, include_pinned: bool = False, config: Config = None):
    url = f"https://{config.APIBase}api/comment/videos/{vid}?parent_vcid={parent_vcid}&offset={offset}" \
          f"&num={config.commentPerReq}&cid_asc={int(cid_asc)}&include_pinned={int(include_pinned)}"
    return _request('get', 'json', '_getVideoCommentList', url, config=config)['data']["comment_list"]


@startEnd
def getAllVideoComments(vid: int, parent_vcid: int = 0,
                        include_pinned: bool = True, config: Config = None) -> list[Comment]:
    """递归拉取指定vid的所有评论。"""
    if config is None:
        config = getGlobalConfig()
    all_comments, offset = [], 0
    while True:
        if offset != 0 and config.verbose:
            logger.info(f"[getAllVideoComments]curr offset: {offset}")
        try:
            comment_list = _getVideoCommentList(vid, offset, parent_vcid, config.ascending, include_pinned, config)
        except ExhaustedRetriesError as e:
            t_ = f"fail to get all comments: {e}"
            logger.error(f"[getAllVideoComments]{_c(_RED, t_, config)}")
            return []  # 过于激进?
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
                    logger.info(f"[getAllVideoComments]Get replies of vcid{comment.cid}...")
                comment.replies = getAllVideoComments(vid, comment.cid, include_pinned, config)
            all_comments.append(comment)
        if len(comment_list) < config.commentPerReq:
            break
        offset += config.commentPerReq
        time.sleep(random.uniform(*config.pagingDelay))
    return all_comments


@startEnd
def _downloadVideo(url: str, config: Config, stream: bool = True) -> Response:
    resp = _request('get', 'stream', '_downloadVideo', url,
                    config=config, stream=stream, is_long=True, is_chat=True, is_video=True)
    return resp


def downloadVideo(vid: int, config: Config = None):
    """下载指定vid的视频。"""
    if config is None:
        config = getGlobalConfig()
    video = getVideoDetail(vid, config)

    pub_ts = parseTime(video["time"]) if video.get("time") else DEFAULT_TS
    fn = _format(config.videoName,
                 vid='ov%i' % video['vid'], uid=video['uid'], dur=video['duration'], durf=_fn_2hms(video['duration']),
                 pubts=pub_ts, pubftime=_fn_formatTime(pub_ts))
    temp_fn = _temp_name(fn)
    fp = os.path.join(config.videoPath, temp_fn)
    fp_new = os.path.join(config.videoPath, fn)

    resp = _downloadVideo(video['video_url'], config, stream=True)
    with open(fp, "wb") as f:
        for chunk in resp.iter_content(chunk_size=config.chunkSize):
            f.write(chunk)
    os.replace(fp, fp_new)
    logger.info(f'[downloadVideo]video downloaded: {fp_new}')


@startEnd
def sendVideoComment(vid: int, content: str, parent_vcid: int = 0, config: Config = None) -> dict:
    """发送视频评论。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/comment/videos/{vid}"
    data = {'token': config.token, 'parent_vcid': parent_vcid, 'content': content}
    return _request('post', 'json', 'sendVideoComment', url, config=config, data=data)['data']


@startEnd
def deleteVideoComment(vcid: int, config: Config = None) -> None:
    """删除视频评论。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/comment/video-comments/{vcid}"
    _request('delete', 'json', 'deleteVideoComment', url, config=config, data={'token': config.token})


@startEnd
def toggleVideoLike(vid, config: Config = None):
    """切换指定vid的点赞状态。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/video/like/{vid}"
    return _request('post', 'json', 'toggleVideoLike', url, config=config, data={'token': config.token})['data']


@startEnd
def toggleVideoFav(vid, config: Config = None):
    """切换指定vid的收藏状态。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/video/favorite/{vid}"
    return _request('post', 'json', 'toggleVideoFav', url, config=config, data={'token': config.token})['data']


@startEnd
def sendDanmaku(vid: int, text: str, time_: float = 0.0, mode: Literal['scroll', 'top', 'bottom'] = 'scroll',
                color: str = 'FFFFFF', font_size: str = '25px', render: str = '', config: Config = None):
    """发送弹幕。
    示例：color: '1B3DF6'; font_size: '25px'"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/danmaku/"
    data = {
        'token': config.token, 'vid': vid, 'text': text,
        'time': time_, 'mode': mode, 'color': color,
        'font_size': font_size, 'render': render,
    }
    _request('post', 'json', 'sendDanmaku', url, config=config, data=data)


def sendDanmakuD(vid, dan: Danmaku, config: Config = None):
    """发送弹幕。参数来自Danmaku实例。danmaku_id不使用。"""
    sendDanmaku(vid, dan.text, danmaku.time_ms/1000, dan.mode,
                f"{danmaku.color_rgb:06X}", f"{danmaku.font_size}px", dan.render, config)


@startEnd
def getDraft(config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f'https://{config.APIBase}api/video/draft?token={quote(config.token, safe="")}'
    return _request('get', 'json', 'deleteDraft', url, config=config)['data']


@startEnd
def deleteDraft(config: Config = None):
    if config is None:
        config = getGlobalConfig()
    url = f'https://{config.APIBase}api/video/draft/'
    _request('delete', 'json', 'deleteDraft', url, config=config, data={'token': quote(config.token, safe='')})


@startEnd
def postDraft(video_path: str, cover_path: str, title: str, intro: str = '', vid_type: int = 3, category: int = 0, *,
              tags: list[str] = None, duration: int = None, channel_id: int = None, channel_section_id: int = None,
              staffs: list[Staff] = None, config: Config = None) -> int:
    """上传视频与封面，创建草稿。需要token。duration不传则自动探测(秒)。"""
    if config is None:
        config = getGlobalConfig()

    if tags is None:
        tag = ""
    else:
        tag = _tag_factory(tags)

    # 2. 本地校验 + duration 探测（上传前做完，早失败）
    vp, cp = Path(video_path), Path(cover_path)
    if vp.stat().st_size > _MAX_VIDEO:
        raise FileTooBigError(f"视频超过 400MB: {vp.stat().st_size}")
    if cp.stat().st_size > _MAX_COVER:
        raise FileTooBigError(f"封面超过 3MB: {cp.stat().st_size}")

    video_ext = vp.suffix.lstrip(".").lower()
    cover_ext = cp.suffix.lstrip(".").lower()
    if video_ext not in ['mp4', 'mov', 'm4v']:
        raise InvalidFileFormatError(f"{video_ext}")
    if cover_ext not in ['jpg', 'jpeg', 'png', 'gif']:
        raise InvalidFileFormatError(f"{cover_ext}")
    logger.info(f'[postDraft]video extension {video_ext}, cover extension {cover_ext}')

    if duration is None:
        duration = checkDurI(vp)
    logger.info(f'[postDraft]got duration: {duration} second(s)')

    # 3. presign
    v = _request('get', 'json', 'postDraft',
                 f"https://{config.APIBase}api/video/video-presigned?extension={video_ext}&token={quote(config.token, safe='')}",
                 config=config)['data']
    c = _request('get', 'json', 'postDraft',
                 f"https://{config.APIBase}api/video/cover-presigned?extension={cover_ext}&token={quote(config.token, safe='')}",
                 config=config)['data']
    video_mime = mimetypes.guess_type(video_path)[0] or 'application/octet-stream'
    cover_mime = mimetypes.guess_type(cover_path)[0] or 'application/octet-stream'

    with open(vp, "rb") as f:
        _request('put', 'content', 'postDraft', v['url'], config=config, data=f, content_type=video_mime, is_long=True, is_form=True)
    with open(cp, "rb") as f:
        _request('put', 'content', 'postDraft', c['url'], config=config, data=f, content_type=cover_mime, is_long=True, is_form=True)
    logger.info(f'[postDraft]video & cover uploaded, prepared to post draft')

    body = {
        "token": quote(config.token, safe=""),
        "title": title,
        "intro": intro,
        "type": int(vid_type),
        "category": int(category),
        "tag": tag,
        "cover_url": c["path"],
        "video_url": v["path"],
        "duration": int(duration),
        'channel_id': int(channel_id or 0),
        'staff': list(asdict(s) for s in staffs)
    }
    if channel_section_id is not None:
        body["channel_section_id"] = int(channel_section_id)
    return _request('post', 'json', 'postDraft', f"https://{config.APIBase}api/video/draft/", config=config, data=body)['data']['draft_id']


@startEnd
def publishDraft(config: Config = None) -> dict:
    """发布当前草稿。需要token。"""
    if config is None:
        config = getGlobalConfig()
    return _request('post', 'json', 'publishDraft', f"https://{config.APIBase}api/video/draft/publish/",
                    config=config, data={"token": config.token}, is_long=True)['data']
