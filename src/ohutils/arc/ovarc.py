from ..core.util import Danmaku, Comment, VideoEntry, _request, _temp_name, _iter_chunks, _format, Staff, getVersion, \
    getGlobalConfig, logger, parseTime, _fn_formatTime, _c, _crc
from ..core.config import Config
from ..core._const import DANMAKU_TOP, DANMAKU_SCROLL, DANMAKU_BOTTOM, _LATEST_OBARC_VER, _OVARC_END_MARKER, \
    _LATEST_OVARC_VER, _YELLOW, _RED, _GRAY, F_MANUAL, F_GORE
from ..core.vid_api import getAllDanmaku, getAllVideoComments, getVideoDetail, _downloadVideo
from ..core.exception import VIDError, VerificationError
from typing import Literal, Union, Optional
from .obarc import _writeComment, _parseComment
import time
import struct
from requests import Response, RequestException
import os
import zlib
import random
import hashlib

_DANMAKU_MAP: dict[int, Literal['scroll', 'top', 'bottom']] = {DANMAKU_SCROLL: 'scroll', DANMAKU_TOP: 'top',
                                                               DANMAKU_BOTTOM: 'bottom'}
_DANMAKU_MAP_INV: dict[Literal['scroll', 'top', 'bottom'], int] = {'scroll': DANMAKU_SCROLL, 'top': DANMAKU_TOP,
                                                                   'bottom': DANMAKU_BOTTOM}

class VideoSnapshots:
    def __init__(self):
        ...

    def latest(self):
        ...

    def all(self):
        ...


def _parseDanmaku(ver: int, data: bytes, offset: int) -> tuple[Danmaku, int]:
    if ver <= 1:
        d_id = struct.unpack_from('<I', data, offset)[0]
    else:
        d_id = struct.unpack_from('<i', data, offset)[0]
    offset += 4
    time_ms, mode, color, f_size, render_len = struct.unpack_from('<QBIBB', data, offset)
    offset += 15
    render = data[offset:offset + render_len].decode('utf-8')
    offset += render_len

    text_len = struct.unpack_from('<H', data, offset)[0]
    offset += 2
    text = data[offset:offset + text_len].decode('utf-8')
    offset += text_len

    return Danmaku(d_id, text, time_ms, _DANMAKU_MAP[mode], color, f_size, render), offset


def _writeDanmaku(ver: int, f, danmaku: Danmaku):
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


def _readSnapshot(ver: int, vid: int, uid: int, pub_ts: int, f, snapshot_addr, verify: bool = True):
    f.seek(snapshot_addr)
    next_addr, snapshot_ts = struct.unpack('<QI', f.read(12))
    h_meta_s = -1  # PyCharm你是哈批吗我用同一个条件判断还能告诉我｢局部变量 'h_meta_s' 可能在赋值前引用｣?
    title = intro = staffs = danmaku = comments = cover_binary = video_size = video_addr = tags = video_sha1 = None
    sha1 = f.read(20)
    flag_cg = struct.unpack('<B', f.read(1))[0]
    if verify:
        h_meta_s = f.tell()
    flag2, cd_len, like, fav, view, dur, v_c, cid = struct.unpack('<BIIIIIBI', f.read(26))
    vid_type, category, gore = (v_c >> 4), v_c & 0xf, flag2 & F_GORE
    if flag_cg & 1:
        # title更改
        title_len = struct.unpack('<H', f.read(2))[0]
        title = f.read(title_len).decode('utf-8')
    if flag_cg & 2:
        # intro更改
        intro_len = struct.unpack('<I', f.read(4))[0]
        intro = f.read(intro_len).decode('utf-8')
    if flag_cg & 4:
        # tags更改
        tag_count = f.read(1)[0]
        tags = []
        for _ in range(tag_count):
            tl = struct.unpack('<H', f.read(2))[0]
            tags.append(f.read(tl).decode('utf-8'))
    if flag_cg & 8:
        # staffs更改
        staff_count = struct.unpack('<B', f.read(1))[0]
        staffs = []
        for _ in range(staff_count):
            s_uid = struct.unpack('<I', f.read(4))[0]
            rl = f.read(1)[0]
            role = f.read(rl).decode('utf-8')
            sort_order = struct.unpack('<I', f.read(4))[0]
            staffs.append(Staff(s_uid, role, sort_order))
    cd_data = f.read(cd_len)
    offset = 0
    if flag_cg & 16:
        # comments更改
        comment_count = struct.unpack_from('<I', cd_data, offset)[0]
        offset += 4
        comments = []
        for _ in range(comment_count):
            c, offset = _parseComment('video', _LATEST_OBARC_VER, cd_data, offset)
            comments.append(c)
    if flag_cg & 32:
        # dan更改
        danmaku_count = struct.unpack_from('<I', cd_data, offset)[0]
        offset += 4
        danmaku = []
        for _ in range(danmaku_count):
            d, offset = _parseDanmaku(ver, cd_data, offset)
            danmaku.append(d)
    if verify:
        h_meta_e = f.tell()
        f.seek(h_meta_s)
        h_meta = hashlib.sha1(f.read(h_meta_e - h_meta_s))  # 计算h_meta
        f.seek(h_meta_e)
        if h_meta.digest() != sha1:
            raise VerificationError(f'快照sha1不匹配: 应为{sha1.hex()}, 实为{h_meta.hexdigest()}')
    if flag_cg & 64:
        # cover更改
        cover_sha1 = f.read(20)
        cover_size = struct.unpack('<I', f.read(4))[0]
        cover_binary = f.read(cover_size)
        h_c = hashlib.sha1(cover_binary)
        if verify and cover_sha1 != h_c.digest():
            raise VerificationError(f'快照中封面sha1不匹配: 应为{cover_sha1.hex()}, 实为{h_c.hexdigest()}')
    if flag_cg & 128:
        # video更改
        video_sha1 = f.read(20)
        video_size = struct.unpack('<Q', f.read(8))[0]
        video_addr = f.tell()

    return VideoEntry(vid=vid, uid=uid, like_count=like, favorite_count=fav, view_count=view, duration=dur,
                      channel_id=cid, pub_time=pub_ts, arc_time=snapshot_ts, tags=tags,
                      vid_type=vid_type, category=category, title=title, intro=intro, staffs=staffs,
                      is_gore=gore, danmaku=danmaku, comments=comments, _cover=cover_binary, _video_fp=f.name,
                      _video_size=video_size, _video_offset=video_addr), video_sha1, next_addr


def _writeOvarc1(vid: int, video_data: dict, comments: list[Comment], danmaku: list[Danmaku],
                 video_stream: Union[bytes, Response], cover_bytes: bytes, fp, config: Config = None):
    if config is None:
        config = getGlobalConfig()
    with open(fp, 'wb') as f:
        # ===================文件头 (32字节)===================
        info_, flag = {}, 0
        pub_ts = parseTime(video_data["time"]) if video_data.get("time") else DEFAULT_TS
        archive_ts = int(time.time())
        channel_id = video_data.get("channel_id", 0)
        is_gore = bool(int(video_data.get('is_gore', 0)))
        tags = video_data.get('tags', [])
        flag = is_gore * F_GORE
        vid_type = int(video_data.get('type', 0))
        category = int(video_data.get('category', 0))

        f.write(b'OVARC')  # 5B magic
        f.write(struct.pack('<B', 1))  # 1B版本
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
            _writeDanmaku(1, f, d)

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
        crc32 = _crc(f, 0x20, file_size)

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
        logger.info(f"[_writeOvarc/v1]Write complete: {fp}, CRC32: {crc32:08X}")
    return fp


def _writeOvarc2p(version: int, vid: int, video_data: dict, comments: list[Comment], danmaku: list[Danmaku],
                  video_stream: Union[bytes, Response], cover_bytes: bytes, fp, config: Config = None):
    if config is None:
        config = getGlobalConfig()
    if os.path.exists(fp):
        raise NotImplementedError("追加快照还没写")
    h_meta = hashlib.sha1()
    h_cover = hashlib.sha1()
    h_video = hashlib.sha1()
    with open(fp, 'wb') as f:
        # ===================文件头 (32字节)===================
        info_ = {}
        pub_ts = parseTime(video_data["time"]) if video_data.get("time") else DEFAULT_TS
        channel_id = video_data.get("channel_id", 0)
        is_gore = bool(int(video_data.get('is_gore', 0)))
        tags = video_data.get('tags', [])
        flag = is_gore * F_GORE
        vid_type = int(video_data.get('type', 0))
        category = int(video_data.get('category', 0))
        vid = int(video_data.get("vid", vid))
        uid = int(video_data.get('uid', 0))

        f.write(b'OVARC')  # 5B magic
        f.write(struct.pack('<B', version))  # 1B版本
        f.write(struct.pack('<I', pub_ts))  # 4B 原始发布时间
        f.write(struct.pack('<H', 1))   # 2B snapshot_num = 1
        f.write(struct.pack('<I', uid))  # 4B uid

        f.write(struct.pack('<Q', 0))  # 8B 总大小（占位）
        f.write(struct.pack('<H', 0))  # 2B 保留
        f.write(struct.pack('<I', vid))  # 4B vid
        f.write(struct.pack('<B', 0))  # 1B 总标志位,不知道写啥
        f.write(b'\xA3')  # 1B 头结尾

        # ===================快照部分===================
        title_bytes = video_data.get("title", "").encode('utf-8')
        intro_bytes = video_data.get("intro", "").encode('utf-8')
        info_['last_ss_put'] = f.tell()
        f.write(struct.pack('<Q', 0))  # 8B last_snapshot_addr 占位
        # 快照
        info_['last_ss'] = f.tell()
        f.write(struct.pack('<Q', 0))  # 8B next_snapshot_addr = 0
        f.write(struct.pack('<I', int(time.time())))  # 4B snapshot_ts
        info_['sha1_put'] = f.tell()
        f.write(b'\x00' * 20)  # sha1 (占位)
        f.write(struct.pack('<B', 0xFF))  # 1B flags = $FF
        info_['meta_s'] = f.tell()
        f.write(struct.pack('<B', flag))  # 1B flags2

        info_['cd_put'] = f.tell()
        f.write(struct.pack('<I', 0))  # 8B cd_len = 0
        f.write(struct.pack('<I', int(video_data.get("like_count", 0))))  # 4B like
        f.write(struct.pack('<I', int(video_data.get("favorite_count", 0))))  # 4B fav
        f.write(struct.pack('<I', int(video_data.get("view_count", 0))))  # 4B view
        f.write(struct.pack('<I', int(video_data.get('duration', 0))))  # 4B duration (s)
        f.write(struct.pack('<B', (vid_type << 4) | category))  # 1B v_type + category
        f.write(struct.pack('<I', channel_id))  # 4B channel_id

        f.write(struct.pack('<H', len(title_bytes)))  # title_len
        f.write(title_bytes)  # title
        f.write(struct.pack('<I', len(intro_bytes)))  # intro_len
        f.write(intro_bytes)  # intro

        f.write(struct.pack('<B', len(tags)))
        for t in tags:  # tags
            t_bytes = t.encode('utf-8')
            f.write(struct.pack('<H', len(t_bytes)))
            f.write(t_bytes)

        staff = video_data.get('staff', [])  # staff
        f.write(struct.pack('<B', len(staff)))
        for s in staff:
            f.write(struct.pack('<i', s.get('uid', 0)))  # uid signed
            role_bytes = s.get('role', '').encode('utf-8')
            f.write(struct.pack('<B', len(role_bytes)))  # role_len
            f.write(role_bytes)  # role
            f.write(struct.pack('<I', s.get('sort_order', 0)))  # sort_order

        info_['cd_s'] = f.tell()
        f.write(struct.pack('<I', len(comments)))
        for c in comments:
            _writeComment(_LATEST_OBARC_VER, f, c, pm=True)

        f.write(struct.pack('<I', len(danmaku)))
        for d in danmaku:
            _writeDanmaku(version, f, d)
        info_['meta_e'] = f.tell()

        # ===================视频封面===================
        h_cover.update(cover_bytes)
        dig = h_cover.digest()
        logger.debug(f'[_writeOvarc2p/v{version}]sha1 of cover is {dig.hex()}')
        f.write(dig)
        f.write(struct.pack('<I', len(cover_bytes)))
        f.write(cover_bytes)
        del cover_bytes  # 清理

        # ===================视频===================
        video_size = 0
        info_['video_sha1_put'] = f.tell()
        f.write(b'\x00' * 20)  # sha1 (占位)
        info_['video_size_put'] = f.tell()
        f.write(struct.pack('<Q', video_size))  # video_size（占位）
        for chunk in _iter_chunks(video_stream, config.chunkSize):
            f.write(chunk)
            h_video.update(chunk)
            video_size += len(chunk)
        logger.debug(f'[_writeOvarc2p/v{version}]sha1 of video is {h_video.hexdigest()}')

        f.write(_OVARC_END_MARKER)
        # 回填
        file_size = f.tell()

    with open(fp, 'r+b') as f:
        # 回填各种
        f.seek(0x10)
        f.write(struct.pack('<Q', file_size))
        f.seek(info_['last_ss_put'])
        f.write(struct.pack('<I', info_['last_ss']))
        f.seek(info_['cd_put'])
        f.write(struct.pack('<I', info_['meta_e'] - info_['cd_s']))
        f.seek(info_['video_size_put'])
        f.write(struct.pack('<Q', video_size))
        f.seek(info_['meta_s'])
        h_meta.update(f.read(info_['meta_e'] - info_['meta_s']))
        logger.debug(f'[_writeOvarc2p/v{version}]sha1 of metadata is {h_meta.hexdigest()}')
        f.seek(info_['video_sha1_put'])
        f.write(h_video.digest())
        f.seek(info_['sha1_put'])
        f.write(h_meta.digest())

    if config.verbose:
        logger.info(f"[_writeOvarc2p/v{version}]Write complete: {fp}")
    return fp


def _writeOvarc_disp(version: int, vid: int, video_data: dict, comments: list[Comment], danmaku: list[Danmaku],
                     video_stream: Union[bytes, Response], cover_bytes: bytes, fp, config: Config = None):
    if version == 1:
        return _writeOvarc1(vid, video_data, comments, danmaku, video_stream, cover_bytes, fp, config)
    else:
        return _writeOvarc2p(version, vid, video_data, comments, danmaku, video_stream, cover_bytes, fp, config)


def _loadOvarc1(fp: str) -> VideoEntry:
    with open(fp, "rb") as f:
        header = f.read(32)
        # 提取头
        if header[:5] != b'OVARC':
            raise VerificationError(f"{fp}不是有效的.ovarc文件")
        flags = header[6]
        is_gore = flags & 1
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
            d, offset = _parseDanmaku(1, cd_data, offset)
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
        is_gore=bool(is_gore),
        _cover=cover_bytes,
        _video_fp=fp,
        _video_offset=video_offset,
        _video_size=video_size,
    )


def _loadOvarc2p(version: int, fp: str):
    with open(fp, "rb") as f:
        header = f.read(6)
        # 提取头
        if header[:5] != b'OVARC':
            raise VerificationError(f"{fp}不是有效的.ovarc文件")
        pub_ts, s_num, uid, size, _, vid, flag, _, last_ss = struct.unpack('<IHIQHIBBQ', f.read(34))
        ss, _, _ = _readSnapshot(version, vid, uid, pub_ts, f, last_ss)
    return ss


def _loadOvarc_disp(ver, fp):
    if ver == 1:
        return _loadOvarc1(fp)
    else:
        return _loadOvarc2p(ver, fp)


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
    return _loadOvarc_disp(ver, filepath)


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
    time.sleep(random.uniform(*config.stageDelay))
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
    time.sleep(random.uniform(*config.stageDelay))
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
    time.sleep(random.uniform(*config.stageDelay))
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
    time.sleep(random.uniform(*config.stageDelay))
    if verbose:
        logger.info(f"[_saveVideo/v{version}]Get video stream of ov{vid}...")
    video_stream = _downloadVideo(video_data['video_url'], config, stream=True)

    # ===================写文件===================
    temp_file_path = os.path.join(config.savePath, _temp_name(fn))

    exist = os.path.exists(file_path)
    if not exist or policy == 'override':
        try:
            _writeOvarc_disp(version, vid, video_data, comments, danmaku_list, video_stream, cover_binary,
                             temp_file_path, config)
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
        raise NotImplementedError  # 我好像是不知道了。
    return file_path, True


def saveVideo(vid: int, config: Config = None) -> tuple[str, bool]:
    """存储视频至.ovarc文件。"""
    return _saveVideo(_LATEST_OVARC_VER, vid, config)
