from ..core.util import Danmaku, Comment, VideoEntry, _request, _temp_name, _iter_chunks, _format, Staff, getVersion, \
    getGlobalConfig, logger, parseTime, _fn_formatTime, _c
from ..core.config import Config
from ..core._const import DANMAKU_TOP, DANMAKU_SCROLL, DANMAKU_BOTTOM, _LATEST_OBARC_VER, _OVARC_END_MARKER, \
    _LATEST_OVARC_VER, _YELLOW, _RED, _GRAY
from ..core.vid_api import getAllDanmaku, getAllVideoComments, getVideoDetail, _downloadVideo
from ..core.exception import VIDError
from typing import Literal, Union, Optional
from .obarc import _writeComment, _parseComment
import time
import struct
from requests import Response, RequestException
import os
import zlib

_DANMAKU_MAP: dict[int, Literal['scroll', 'top', 'bottom']] = \
    {DANMAKU_SCROLL: 'scroll', DANMAKU_TOP: 'top', DANMAKU_BOTTOM: 'bottom'}
_DANMAKU_MAP_INV: dict[Literal['scroll', 'top', 'bottom'], int] = \
    {'scroll': DANMAKU_SCROLL, 'top': DANMAKU_TOP, 'bottom': DANMAKU_BOTTOM}


def _parseDanmaku(data: bytes, offset: int) -> tuple[Danmaku, int]:
    d_id, time_ms, mode, color, f_size, render_len = struct.unpack_from('<IQBIBB', data, offset)
    offset += 19
    render = data[offset:offset + render_len].decode('utf-8')
    offset += render_len

    text_len = struct.unpack_from('<H', data, offset)[0]
    offset += 2
    text = data[offset:offset + text_len].decode('utf-8')
    offset += text_len

    return Danmaku(d_id, text, time_ms, _DANMAKU_MAP[mode], color, f_size, render), offset


def _writeDanmaku(f, danmaku: Danmaku):
    # 写弹幕
    content_bytes = danmaku.text.encode('utf-8')
    render_bytes = danmaku.render.encode('utf-8')
    f.write(struct.pack('<I', danmaku.danmaku_id))
    f.write(struct.pack('<Q', danmaku.time_ms))
    f.write(struct.pack('<B', _DANMAKU_MAP_INV[danmaku.mode]))
    f.write(struct.pack('<I', danmaku.color_rgb))
    f.write(struct.pack('<B', danmaku.font_size))

    f.write(struct.pack('<B', len(render_bytes)))
    f.write(render_bytes)

    f.write(struct.pack('<H', len(content_bytes)))
    f.write(content_bytes)


def _writeOvarc(version: int, vid: int, video_data: dict, comments: list[Comment], danmaku: list[Danmaku],
                video_stream: Union[bytes, Response], cover_bytes: bytes, fp, config: Config = None):
    if config is None:
        config = getGlobalConfig()
    with open(fp, 'wb') as f:
        # ===================文件头 (32字节)===================
        info_ = {}
        pub_ts = parseTime(video_data["time"]) if video_data.get("time") else DEFAULT_TS
        archive_ts = int(time.time())
        channel_id = video_data.get("channel_id", 0)
        is_gore = bool(int(video_data.get('is_gore', 0)))
        tags = video_data.get('tags', [])
        flag = is_gore << 1
        vid_type = int(video_data.get('type', 0))
        category = int(video_data.get('category', 0))

        f.write(b'OVARC')  # 5B magic
        f.write(struct.pack('<B', version))  # 1B版本
        f.write(struct.pack('<B', flag))  # 1B 标志位
        f.write(struct.pack('<B', (vid_type << 4) | category))  # 1B v_type + category
        f.write(struct.pack('<I', pub_ts))  # 4B 原始发布时间
        f.write(struct.pack('<I', archive_ts))  # 4B 存档时间

        f.write(struct.pack('<Q', 0))  # 8B 总大小（占位）
        f.write(struct.pack('<I', 0))  # 4B CRC32（占位）
        f.write(struct.pack('<H', channel_id))  # 2B 频道ID
        f.write(struct.pack('<B', len(tags)))  # 1B tag数量
        f.write(b'\xA3')  # 1B 头结尾

        # ===================视频条目===================
        title_bytes = video_data.get("title", "").encode('utf-8')
        intro_bytes = video_data.get("intro", "").encode('utf-8')
        f.write(struct.pack('<I', int(video_data.get("vid", vid))))  # 4B vid
        f.write(struct.pack('<I', int(video_data.get("uid", 0))))  # 4B uid
        f.write(struct.pack('<I', int(video_data.get("like_count", 0))))  # 4B like
        f.write(struct.pack('<I', int(video_data.get("favorite_count", 0))))  # 4B fav

        f.write(struct.pack('<I', int(video_data.get("view_count", 0))))  # 4B view
        f.write(struct.pack('<I', int(video_data.get('duration', 0))))  # 4B duration (s)
        info_['cover_addr'] = f.tell()
        f.write(struct.pack('<Q', 0))  # 8B 封面地址（占位）

        f.write(struct.pack('<H', len(title_bytes)))  # title_len
        f.write(title_bytes)  # title

        f.write(struct.pack('<I', len(intro_bytes)))  # intro_len
        f.write(intro_bytes)  # intro

        for t in tags:  # tags
            t_bytes = t.encode('utf-8')
            f.write(struct.pack('<H', len(t_bytes)))
            f.write(t_bytes)

        staff = video_data.get('staff', [])  # staff
        f.write(struct.pack('<B', len(staff)))
        for s in staff:
            f.write(struct.pack('<I', s.get('uid', 0)))  # uid
            role_bytes = s.get('role', '').encode('utf-8')
            f.write(struct.pack('<B', len(role_bytes)))  # role_len
            f.write(role_bytes)  # role
            f.write(struct.pack('<I', s.get('sort_order', 0)))  # sort_order

        f.write(struct.pack('<I', len(comments)))
        for c in comments:
            _writeComment(_LATEST_OBARC_VER, f, c)

        f.write(struct.pack('<I', len(danmaku)))
        for d in danmaku:
            _writeDanmaku(f, d)

        info_['cover'] = f.tell()
        # ===================视频封面===================
        f.write(struct.pack('<I', len(cover_bytes)))
        f.write(cover_bytes)

        # ===================视频===================
        video_size = 0
        info_['video'] = f.tell()
        f.write(struct.pack('<Q', video_size))  # video_size（占位）
        for chunk in _iter_chunks(video_stream, config.chunkSize):
            f.write(chunk)
            video_size += len(chunk)

        f.write(_OVARC_END_MARKER)
        file_size = f.tell()

    with open(fp, 'r+b') as f:
        # 回填
        f.seek(0x20)
        all_data = f.read()
        crc32 = zlib.crc32(all_data) & 0xFFFFFFFF  # 计算CRC32

        # 回填总大小(偏移0x10)
        f.seek(0x10)
        f.write(struct.pack('<Q', file_size))

        # 回填CRC32(偏移0x18)
        f.seek(0x18)
        f.write(struct.pack('<I', crc32))

        # 回填地址
        f.seek(info_['cover_addr'])
        f.write(struct.pack('<Q', info_['cover']))

        # 回填地址
        f.seek(info_['video'])
        f.write(struct.pack('<Q', video_size))
    if config.verbose:
        logger.info(f"[_writeOvarc/v{version}]Write complete: {fp}, CRC32: {crc32:08X}")
    return fp


def _loadOvarc(version: int, fp: str) -> VideoEntry:
    with open(fp, "rb") as f:
        header = f.read(32)
        # 提取头
        flags = header[6]
        v_c = header[7]
        vid_type, category = (v_c >> 4), v_c & 0xf
        pub_ts = struct.unpack('<I', header[0x8:0xC])[0]
        arc_ts = struct.unpack('<I', header[0xC:0x10])[0]
        channel_id = struct.unpack('<H', header[0x1C:0x1E])[0]
        tag_count = header[0x1E]

        # 元数据
        vid, uid, like, fav, view, dur, video_cover_addr = struct.unpack('<IIII IIQ', f.read(32))
        title_len = struct.unpack('<H', f.read(2))[0]
        title = f.read(title_len).decode('utf-8')
        intro_len = struct.unpack('<I', f.read(4))[0]
        intro = f.read(intro_len).decode('utf-8')
        tags = []
        for _ in range(tag_count):
            tag_len = struct.unpack('<H', f.read(2))[0]
            tag = f.read(tag_len).decode('utf-8')
            tags.append(tag)

        staffs = []
        staff_count = struct.unpack('<B', f.read(1))[0]
        for _ in range(staff_count):
            staff_uid = struct.unpack('<I', f.read(4))[0]
            role_len = struct.unpack('<B', f.read(1))[0]
            role = f.read(role_len).decode('utf-8')
            staff_sort = struct.unpack('<I', f.read(4))[0]
            staffs.append(Staff(
                uid=staff_uid,
                role=role,
                sort_order=staff_sort
            ))

        # comments+danmaku的bytes
        cd_start = f.tell()
        cd_data = f.read(video_cover_addr - cd_start)

        offset = 0
        comment_count = struct.unpack_from('<I', cd_data, offset)[0]
        offset += 4
        comments = []
        for _ in range(comment_count):
            c, offset = _parseComment('video', _LATEST_OBARC_VER, cd_data, offset)
            comments.append(c)

        danmaku_count = struct.unpack_from('<I', cd_data, offset)[0]
        offset += 4
        danmaku = []
        for _ in range(danmaku_count):
            d, offset = _parseDanmaku(cd_data, offset)
            danmaku.append(d)

        # cover
        f.seek(video_cover_addr)
        cover_size = struct.unpack('<I', f.read(4))[0]
        cover_bytes = f.read(cover_size)

        # video
        video_size = struct.unpack('<Q', f.read(8))[0]
        video_offset = f.tell()

    # 构造 VideoEntry
    return VideoEntry(
        vid=vid, uid=uid,
        like_count=like, favorite_count=fav, view_count=view,
        duration=dur, channel_id=channel_id,
        pub_time=pub_ts, arc_time=arc_ts,
        tags=tags, vid_type=vid_type, category=category,
        title=title, intro=intro, staffs=staffs,
        danmaku=danmaku, comments=comments,
        _cover=cover_bytes,
        _video_fp=fp,
        _video_offset=video_offset,
        _video_size=video_size,
    )


def loadVideo(vid: int, fn: str = None, config: Config = None) -> VideoEntry:
    """从config.savePath中加载.ovarc文件。
    若savePath中包含了除了{vid}之外的占位符，应提供完整文件名。此时vid参数被忽略。"""
    if config is None:
        config = getGlobalConfig()
    if fn is None:
        try:
            fn = _format(config.ovarcName, vid="ov%i" % vid) + '.ovarc'
        except KeyError as e:
            raise ValueError(
                f"fileName包含vid以外的占位符{e}") from e
    filepath = os.path.join(config.savePath, fn)
    ver = getVersion(filepath)
    return _loadOvarc(ver, filepath)


def _saveVideo(version: int, vid: int, config: Config = None) -> tuple[Optional[str], bool]:
    if config is None:
        config = getGlobalConfig()

    verbose = config.verbose
    policy = config.policy

    if policy not in ['keep', 'merge', 'override', 'keep_after']:
        raise ValueError
    if policy == 'keep':
        if '{pubts}' in config.ovarcName or '{pubftime}' in config.ovarcName:
            raise ValueError(
                "keep策略仅支持{bid}、{ver}、{toolver}占位符，请用keep_after")
        keep_fn = _format(config.ovarcName, vid='ov%i' % vid, ver=version) + '.ovarc'
        file_path = os.path.join(config.savePath, keep_fn)
        if os.path.exists(file_path):
            if verbose:
                t_ = f"File {keep_fn} already exist, skip due to 'keep' policy"
                logger.info(f"[_saveVideo/v{version}]{_c(_YELLOW, t_, config)}")
            return file_path, False

    # ===================获取视频元数据===================
    if verbose:
        logger.info(f"[_saveVideo/v{version}]Get metadata of ov{vid}...")
    try:
        video_data = getVideoDetail(vid, config=config)
        pub_ts = parseTime(video_data["time"]) if video_data.get("time") else DEFAULT_TS
        fn = _format(
            config.ovarcName,
            vid='ov%i' % vid, uid=video_data.get('uid', 0),
            ver=version,
            pubts=pub_ts,
            pubftime=_fn_formatTime(pub_ts),
        ) + '.ovarc'
        file_path = os.path.join(config.savePath, fn)
    except VIDError as e:
        t_ = f"Video ov{vid} metadata get failed: {e}"
        logger.error(f"[_saveVideo/v{version}]{_c(_RED, t_, config)}")
        return None, True

    # ===================获取评论===================
    # time.sleep(random.uniform(*config.blogToCommentDelay))
    if verbose:
        logger.info(f"[_saveVideo/v{version}]Get comments of ov{vid}...")
    try:
        comments = getAllVideoComments(vid, config=config)
    except RequestException as e:
        t_ = f"Network error: {e}"
        logger.error(f'[_saveVideo/v{version}]{_c(_RED, t_, config)}')
        return file_path, True
    if verbose:
        logger.info(f"[_saveVideo/v{version}]Finish, get {len(comments)} top comment(s) in total")

    # ===================获取弹幕===================
    # time.sleep(random.uniform(*config.blogToCommentDelay))
    if verbose:
        logger.info(f"[_saveVideo/v{version}]Get danmaku of ov{vid}...")
    try:
        danmaku_list = getAllDanmaku(vid, config=config)
    except RequestException as e:
        t_ = f"Network error: {e}"
        logger.error(f'[_saveVideo/v{version}]{_c(_RED, t_, config)}')
        return file_path, True
    if verbose:
        logger.info(f"[_saveVideo/v{version}]Finish, get {len(danmaku_list)} danmaku in total")

    # ===================获取封面===================
    # time.sleep(random.uniform(*config.blogToCommentDelay))
    if verbose:
        logger.info(f"[_saveVideo/v{version}]Get cover of ov{vid}...")
    try:
        cover_binary = _request('get', 'content', f'_saveVideo/v{version}',
                                video_data['cover_url'], config=config, is_chat=True)
    except RequestException as e:
        t_ = f"Network error: {e}"
        logger.error(f'[_saveVideo/v{version}]{_c(_RED, t_, config)}')
        return file_path, True
    if verbose:
        logger.info(f"[_saveVideo/v{version}]finished getting cover")

    # ===================获取视频流===================
    # time.sleep(random.uniform(*config.blogToCommentDelay))
    if verbose:
        logger.info(f"[_saveVideo/v{version}]Get video stream of ov{vid}...")
    video_stream = _downloadVideo(video_data['video_url'], config, stream=True)

    # ===================写文件===================
    temp_file_path = os.path.join(config.savePath, _temp_name(fn))

    exist = os.path.exists(file_path)
    if not exist or policy == 'override':
        try:
            _writeOvarc(version, vid, video_data, comments, danmaku_list, video_stream, cover_binary, temp_file_path,
                        config)
        finally:
            video_stream.close()
        os.replace(temp_file_path, file_path)
        return file_path, True

    if policy == 'keep_after':
        if verbose:
            t_ = f"File {fn} already exist, discard data due to 'keep_after' policy"
            logger.info(
                f"[_saveVideo/v{version}]{_c(_YELLOW, t_, config)}")
        return file_path, True

    if policy == 'merge':
        raise NotImplementedError
    return file_path, True


def saveVideo(vid: int, config: Config = None) -> tuple[str, bool]:
    """存储视频至.ovarc文件。"""
    return _saveVideo(_LATEST_OVARC_VER, vid, config)
