from __future__ import annotations
from ..core.util import Danmaku, Comment, VideoEntry, _request, _temp_name, _iter_chunks, _format, Staff, getVersion, \
    getGlobalConfig, logger, parseTime, _fn_formatTime, _c, _crc, foldComments, flattenComments
from ..core.config import Config
from ..core._const import DANMAKU_TOP, DANMAKU_SCROLL, DANMAKU_BOTTOM, _LATEST_OBARC_VER, _OVARC_END_MARKER, \
    _LATEST_OVARC_VER, _YELLOW, _RED, _GRAY, F_MANUAL, F_GORE, DEFAULT_TS
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
from dataclasses import dataclass, asdict, field

_DANMAKU_MAP: dict[int, Literal['scroll', 'top', 'bottom']] = {DANMAKU_SCROLL: 'scroll', DANMAKU_TOP: 'top',
                                                               DANMAKU_BOTTOM: 'bottom'}
_DANMAKU_MAP_INV: dict[Literal['scroll', 'top', 'bottom'], int] = {'scroll': DANMAKU_SCROLL, 'top': DANMAKU_TOP,
                                                                   'bottom': DANMAKU_BOTTOM}


@dataclass
class _ISnapshotVesicle:
    vid: int
    like: int
    fav: int
    view: int
    dur: int
    cnl_id: int
    vt: int
    cat: int
    tags: list[str]
    title: str
    intro: str
    staffs: list[Staff]
    dan: list[Danmaku]
    cmt: list[Comment['VideoEntry']]
    is_gore: bool
    c_sha1: bytes
    v_sha1: bytes
    v_offset: int  # video在文件里的偏移
    v_size: int  # video字节数
    next_addr: int
    snapshot_ts: int
    c_b: bytes = field(repr=False, default=None)


class VideoSnapshots:
    def __init__(self, pub_ts: int, s_num: int, uid: int, vid: int, h_flag: int, ss: list[_ISnapshotVesicle], fp: str):
        self._s_num = s_num
        self.uid = uid
        self.vid = vid
        self.pub_ts = pub_ts
        self.file_flags = h_flag
        self._ss = sorted(ss, key=lambda s: s.snapshot_ts, reverse=True)  # 新 -> 老
        self._fp = fp

    def _spec(self, layer, internal: bool = False):
        base = self._ss[layer]

        def trace(attr):
            for i in range(layer, self._s_num):
                v = getattr(self._ss[i], attr)
                if v is not None:
                    return v
            return None

        def trace_video():
            for i in range(layer, self._s_num):
                s = self._ss[i]
                if s.v_offset is not None:
                    return s.v_offset, s.v_size, s.v_sha1
            return None, None, None

        def replay_cmt():
            comments = {}
            for i in range(self._s_num - 1, layer - 1, -1):
                for c in (self._ss[i].cmt or []):
                    if c.cid > 0:
                        comments[c.cid] = c
                    else:
                        comments.pop(-c.cid, None)
            return list(comments.values())

        def replay_dan():
            dan = {}
            for i in range(self._s_num - 1, layer - 1, -1):
                for d in (self._ss[i].dan or []):
                    if d.danmaku_id > 0:
                        dan[d.danmaku_id] = d
                    else:
                        dan.pop(-d.danmaku_id, None)
            return list(dan.values())

        def replay_tags():
            tags = []
            for i in range(self._s_num - 1, layer - 1, -1):
                for t in (self._ss[i].tags or []):
                    if t.startswith('+'):
                        tags.append(t[1:])
                    elif t.startswith('-'):
                        tags = [x for x in tags if x != t[1:]]
            return tags

        def replay_staffs():
            staffs = {}
            for i in range(self._s_num - 1, layer - 1, -1):
                for s in (self._ss[i].staffs or []):
                    if s.uid > 0:
                        staffs[s.uid] = s
                    else:
                        staffs.pop(-s.uid, None)
            return list(staffs.values())

        v_off, v_sz, v_sha1 = trace_video()

        if internal:
            ve = _ISnapshotVesicle(
                vid=self.vid, like=base.like, fav=base.fav, view=base.view, dur=base.dur, cnl_id=base.cnl_id,
                c_sha1=trace('c_sha1'), cat=base.cat, dan=replay_dan(), cmt=replay_cmt(), is_gore=base.is_gore,
                snapshot_ts=base.snapshot_ts, title=trace('title'), intro=trace('intro'), vt=base.vt,
                tags=replay_tags(),
                next_addr=base.next_addr, staffs=replay_staffs(), v_offset=v_off, v_size=v_sz, v_sha1=v_sha1)
        else:
            ve = VideoEntry(
                vid=self.vid, uid=self.uid, pub_time=self.pub_ts,
                like_count=base.like, favorite_count=base.fav, view_count=base.view,
                duration=base.dur, vid_type=base.vt, category=base.cat, channel_id=base.cnl_id,
                arc_time=base.snapshot_ts, is_gore=base.is_gore,
                tags=replay_tags(), title=trace('title'), intro=trace('intro'),
                staffs=replay_staffs(), danmaku=replay_dan(), comments=replay_cmt(),
                _cover=trace('c_b'), _video_fp=self._fp, _video_offset=v_off, _video_size=v_sz)
        if None in asdict(ve).values() and not internal:
            t_ = '[_writeOvarc2p_append/_spec' if internal else '[VideoSnapshots'
            logger.error(t_ + f']underflow when tracing layer {layer}, values in VideoEntry can be None')
        return ve

    def head(self, layer: int = 0) -> VideoEntry:
        return self._spec(min(layer, self._s_num - 1))

    def all(self) -> list[VideoEntry]:
        res = []
        for i in range(self._s_num):
            res.append(self._spec(i))
        return res

    def __len__(self):
        return self._s_num

    def __repr__(self):
        return f"<VideoSnapshots ({self._s_num} snapshots)>"

    def __str__(self):
        return self.__repr__()


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
    if ver <= 1:
        f.write(struct.pack('<I', danmaku.danmaku_id))
    else:
        f.write(struct.pack('<i', danmaku.danmaku_id))
    f.write(struct.pack('<Q', danmaku.time_ms))
    f.write(struct.pack('<B', _DANMAKU_MAP_INV[danmaku.mode]))
    f.write(struct.pack('<I', danmaku.color_rgb))
    f.write(struct.pack('<B', danmaku.font_size))
    f.write(struct.pack('<B', len(render_bytes)))
    f.write(render_bytes)
    f.write(struct.pack('<H', len(content_bytes)))
    f.write(content_bytes)


def _readSnapshot(ver: int, vid: int, f, snapshot_addr, verify: bool = True, parse: bool = True) -> _ISnapshotVesicle:
    f.seek(snapshot_addr)
    next_addr, snapshot_ts = struct.unpack('<QI', f.read(12))
    h_meta_s = -1  # PyCharm你是哈批吗我用同一个条件判断还能告诉我｢局部变量 'h_meta_s' 可能在赋值前引用｣?
    title = intro = staffs = danmaku = comments = cover_binary = video_size = video_addr = tags = video_sha1 = None
    cover_sha1 = None
    sha1 = f.read(20)
    flag_cg = struct.unpack('<B', f.read(1))[0]
    flag2, cd_len = struct.unpack('<BI', f.read(5))
    if verify:
        h_meta_s = f.tell()
    like, fav, view, dur, v_c, cid = struct.unpack('<IIIIBI', f.read(21))
    vid_type, category, gore = (v_c >> 4), v_c & 0xf, bool(flag2 & F_GORE)
    # print(f"******RS/start: flag_cg={flag_cg}, cd_len={cd_len}, ss_addr={snapshot_addr}")
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
            tl = struct.unpack('<h', f.read(2))[0]
            tg = f.read(abs(tl)).decode('utf-8')
            tg = ('+' if tl > 0 else '-') + tg
            tags.append(tg)
    if flag_cg & 8:
        # staffs更改
        staff_count = struct.unpack('<B', f.read(1))[0]
        staffs = []
        for _ in range(staff_count):
            s_uid = struct.unpack('<i', f.read(4))[0]
            rl = f.read(1)[0]
            role = f.read(rl).decode('utf-8')
            sort_order = struct.unpack('<I', f.read(4))[0]
            staffs.append(Staff(abs(s_uid), role, sort_order))
    cd_data = f.read(cd_len)
    # print(f"******RS/cmt_before: cd_data.len={len(cd_data)}, cd_len={cd_len}, f.tell={f.tell()}")
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
        h_meta = hashlib.sha1(struct.pack('<B', flag2))
        h_meta.update(f.read(h_meta_e - h_meta_s))  # 计算h_meta
        f.seek(h_meta_e)
        # print(f"******RS/verify: h_meta_s={h_meta_s}, h_meta_e={h_meta_e}, flag2={flag2}, ss_addr={snapshot_addr},\\")
        # print(f"******RS/verify: flag_cg={flag_cg}, cd_len={cd_len}")
        if h_meta.digest() != sha1:
            raise VerificationError(f'快照sha1不匹配: 应为{sha1.hex()}, 实为{h_meta.hexdigest()}')
    if flag_cg & 64:
        # cover更改
        cover_sha1 = f.read(20)
        cover_size = struct.unpack('<I', f.read(4))[0]
        cover_binary = f.read(cover_size)
        if parse:
            h_c = hashlib.sha1(cover_binary)
            if verify and cover_sha1 != h_c.digest():
                raise VerificationError(f'快照中封面sha1不匹配: 应为{cover_sha1.hex()}, 实为{h_c.hexdigest()}')
        else:
            cover_binary = -1
    if flag_cg & 128:
        # video更改
        video_sha1 = f.read(20)
        video_size = struct.unpack('<Q', f.read(8))[0]
        video_addr = f.tell()

    return _ISnapshotVesicle(
        vid=vid, view=view, like=like, dur=dur, fav=fav, cnl_id=cid,
        tags=tags, title=title, intro=intro, staffs=staffs, dan=danmaku, cmt=comments, vt=vid_type, cat=category,
        is_gore=gore, c_sha1=cover_sha1, v_sha1=video_sha1, v_offset=video_addr, v_size=video_size,
        next_addr=next_addr, snapshot_ts=snapshot_ts, c_b=cover_binary if parse else None)


def _writeSnapshot_stp1(ver: int, f, *, title, intro, vid_type, category, channel_id, tags, staff, comments, flag_cg,
                        flag2, like, fav, view, dur, danmaku, cover_bytes, video_stream, config):
    """f模式：wb或r+b。
    tags示：['-YTPMV', '+音MAD']。staff中Staff的uid：正加负删，Comment.cid、Danmaku id同。
    comments传入要展平。返回info_, h_meta, video_size, h_video。"""
    # print(f"******W1/start: (before h_meta=hashlib.sha1()) ss_addr={f.tell()}")
    h_meta = hashlib.sha1()
    info_ = {}
    f.write(struct.pack('<Q', 0))  # 8B next_snapshot_addr = 0
    f.write(struct.pack('<I', int(time.time())))  # 4B snapshot_ts
    info_['sha1_put'] = f.tell()
    f.write(b'\x00' * 20)  # sha1 (占位)
    f.write(struct.pack('<B', flag_cg))  # 1B flags
    f.write(struct.pack('<B', flag2))  # 1B flags2

    info_['cd_put'] = f.tell()
    f.write(struct.pack('<I', 0))  # 8B cd_len = 0
    info_['meta_s'] = f.tell()
    f.write(struct.pack('<I', int(like)))  # 4B like
    f.write(struct.pack('<I', int(fav)))  # 4B fav
    f.write(struct.pack('<I', int(view)))  # 4B view
    f.write(struct.pack('<I', int(dur)))  # 4B duration (s)
    f.write(struct.pack('<B', (vid_type << 4) | category))  # 1B v_type + category
    f.write(struct.pack('<I', channel_id))  # 4B channel_id

    if flag_cg & 1:
        title_bytes = title.encode('utf-8')
        f.write(struct.pack('<H', len(title_bytes)))  # title_len
        f.write(title_bytes)  # title
    if flag_cg & 2:
        intro_bytes = intro.encode('utf-8')
        f.write(struct.pack('<I', len(intro_bytes)))  # intro_len
        f.write(intro_bytes)  # intro
    if flag_cg & 4:
        f.write(struct.pack('<B', len(tags)))
        for t in tags:  # tags
            sign = {'-': -1, '+': 1}[t[0]]
            t_bytes = t[1:].encode('utf-8')
            f.write(struct.pack('<h', len(t_bytes * sign)))
            f.write(t_bytes)
    if flag_cg & 8:
        f.write(struct.pack('<B', len(staff)))
        for s in staff:
            f.write(struct.pack('<i', s.get('uid', 0)))  # uid signed
            role_bytes = s.get('role', '').encode('utf-8')
            f.write(struct.pack('<B', len(role_bytes)))  # role_len
            f.write(role_bytes)  # role
            f.write(struct.pack('<I', s.get('sort_order', 0)))  # sort_order

    info_['cd_s'] = f.tell()
    if flag_cg & 16:
        roots = foldComments(comments)  # 先建树
        # print(f'******W1/cmt_in: roots={roots}')
        f.write(struct.pack('<I', len(roots)))  # 顶层数
        for c in roots:
            _writeComment(_LATEST_OBARC_VER, f, c, pm=True)
    if flag_cg & 32:
        f.write(struct.pack('<I', len(danmaku)))
        for d in danmaku:
            _writeDanmaku(ver, f, d)
    info_['meta_e'] = f.tell()

    # ===================视频封面===================
    if flag_cg & 64:
        h_cover = hashlib.sha1(cover_bytes)
        dig = h_cover.digest()
        logger.debug(f'[_writeSnapshot_stp1/v{ver}]sha1 of cover is {dig.hex()}')
        f.write(dig)
        f.write(struct.pack('<I', len(cover_bytes)))
        f.write(cover_bytes)
        del cover_bytes  # 清理

    # ===================视频===================
    video_size = h_video = None
    if flag_cg & 128:
        video_size = 0
        h_video = hashlib.sha1()
        info_['video_sha1_put'] = f.tell()
        f.write(b'\x00' * 20)  # sha1 (占位)
        info_['video_size_put'] = f.tell()
        f.write(struct.pack('<Q', video_size))  # video_size（占位）
        for chunk in _iter_chunks(video_stream, config.chunkSize):
            f.write(chunk)
            h_video.update(chunk)
            video_size += len(chunk)
        logger.debug(f'[_writeSnapshot_stp1/v{ver}]sha1 of video is {h_video.hexdigest()}')

    return info_, h_meta, video_size, h_video, flag2


def _writeSnapshot_stp2(ver: int, f, info_, h_meta, video_size, h_video, flag2):
    """f模式：r+b。直接接stp1。"""
    f.seek(info_['cd_put'])
    f.write(struct.pack('<I', info_['meta_e'] - info_['cd_s']))
    if video_size is not None:
        f.seek(info_['video_size_put'])
        f.write(struct.pack('<Q', video_size))
    f.seek(info_['meta_s'])
    h_meta.update(struct.pack('<B', flag2))
    h_meta.update(f.read(info_['meta_e'] - info_['meta_s']))
    logger.debug(f'[_writeSnapshot_stp2/v{ver}]sha1 of metadata is {h_meta.hexdigest()}')
    if h_video is not None:
        f.seek(info_['video_sha1_put'])
        f.write(h_video.digest())
    f.seek(info_['sha1_put'])
    f.write(h_meta.digest())
    # print(f"******W2/end: meta_s={info_['meta_s']}, meta_e={info_['meta_e']}, flag2={flag2}, cd_s={info_['cd_s']}")


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


def _writeOvarc2p_create(version: int, vid: int, video_data: dict, comments: list[Comment], danmaku: list[Danmaku],
                         video_stream: Union[bytes, Response], cover_bytes: bytes, fp, config: Config = None):
    """comments要展平。"""
    if config is None:
        config = getGlobalConfig()

    with open(fp, 'wb') as f:
        # ===================文件头 (32字节)===================
        info_ = {}
        pub_ts = parseTime(video_data["time"]) if video_data.get("time") else DEFAULT_TS
        channel_id = video_data.get("channel_id", 0)
        is_gore = int(video_data.get('is_gore', 0))
        tags = video_data.get('tags', [])
        flag = is_gore * F_GORE
        vid_type = int(video_data.get('type', 0))
        category = int(video_data.get('category', 0))
        vid = int(video_data.get("vid", vid))
        uid = int(video_data.get('uid', 0))
        staff = video_data.get('staff', [])
        tags_new = []
        for t in tags:
            tags_new.append('+' + t)
        del tags

        f.write(b'OVARC')  # 5B magic
        f.write(struct.pack('<B', version))  # 1B版本
        f.write(struct.pack('<I', pub_ts))  # 4B 原始发布时间
        f.write(struct.pack('<H', 1))  # 2B snapshot_num = 1
        f.write(struct.pack('<I', uid))  # 4B uid

        f.write(struct.pack('<Q', 0))  # 8B 总大小（占位）
        f.write(struct.pack('<H', 0))  # 2B 保留
        f.write(struct.pack('<I', vid))  # 4B vid
        f.write(struct.pack('<B', 0))  # 1B 总标志位,不知道写啥
        f.write(b'\xA3')  # 1B 头结尾

        info_['last_ss_put'] = f.tell()
        f.write(struct.pack('<Q', 0))  # 8B last_snapshot_addr 占位
        info_['last_ss'] = f.tell()
        # ===================快照部分===================
        pck = _writeSnapshot_stp1(version, f, title=video_data.get('title', ''), intro=video_data.get('intro', ''),
                                  category=category, channel_id=channel_id, dur=video_data.get('duration', 0),
                                  fav=video_data.get('favorite_count', 0), like=video_data.get('like_count', 0),
                                  view=video_data.get('view_count', 0), staff=staff, tags=tags_new, vid_type=vid_type,
                                  comments=comments, flag_cg=0xff, flag2=flag, cover_bytes=cover_bytes, danmaku=danmaku,
                                  video_stream=video_stream, config=config)
        f.write(_OVARC_END_MARKER)
        # 回填
        file_size = f.tell()

    with open(fp, 'r+b') as f:
        # 回填各种
        f.seek(0x10)
        f.write(struct.pack('<Q', file_size))
        f.seek(info_['last_ss_put'])
        f.write(struct.pack('<Q', info_['last_ss']))
        _writeSnapshot_stp2(version, f, *pck)

    if config.verbose:
        logger.info(f"[_writeOvarc2p_create/v{version}]Write complete: {fp}")
    return fp


# 改的时候记得把_create和_append全改了
def _writeOvarc2p_append(version: int, vid: int, video_data: dict, comments: list[Comment], danmaku: list[Danmaku],
                         video_stream: Union[bytes, Response], cover_bytes: bytes, fp, config: Config = None):
    """comments要展平。"""
    if config is None:
        config = getGlobalConfig()

    fn = f'w2p+_ov{vid}.buf'
    tfp = os.path.join(config.savePath, _temp_name(fn))
    h_video = hashlib.sha1()
    logger.info(f'[_writeOvarc2p_append/v{version}]Write temp video file to {tfp}...')
    with open(tfp, 'wb') as f:
        for chunk in _iter_chunks(video_stream, config.chunkSize):
            f.write(chunk)
            h_video.update(chunk)
    logger.info(f'[_writeOvarc2p_append/v{version}]Write temp video file finished')

    with open(fp, 'r+b') as f:
        info_ = {}
        # ==============================读之前的==============================
        f.seek(0xa)
        snapshot_num = struct.unpack('<H', f.read(2))[0]
        f.seek(0x20)
        last_ss_addr = struct.unpack('<Q', f.read(8))[0]  # 读last_ss
        info_['new_addr_put'] = last_ss_addr
        ss = _uni(version, vid, f)
        vss = VideoSnapshots(DEFAULT_TS, snapshot_num, 0, vid, 0, ss, fp)
        last_ss: _ISnapshotVesicle = vss._spec(0, internal=True)
        last_ss.cmt = flattenComments(last_ss.cmt)
        # print(f'******W+/read_prev: last_ss.next_addr={last_ss.next_addr}, snapshot_ts={last_ss.snapshot_ts}')
        f.seek(-len(_OVARC_END_MARKER), 2)
        info_['new_addr'] = f.tell()

        # ==============================新的==============================
        channel_id = video_data.get("channel_id", 0)
        is_gore = int(video_data.get('is_gore', 0))
        tags = set(video_data.get('tags', []))
        flag = is_gore * F_GORE
        vid_type = int(video_data.get('type', 0))
        category = int(video_data.get('category', 0))
        staff = video_data.get('staff', [])
        title = video_data.get('title', '')
        intro = video_data.get('intro', '')

        # ==============================比对，写==============================
        # last_ss是None还得倒推。先写两快照版本。服了。
        if title == last_ss.title:
            title_, flag_cg = None, 0
        else:
            title_, flag_cg = title, 1
        if intro == last_ss.intro:
            intro_ = None
        else:
            intro_ = intro
            flag_cg |= 2
        tags_old = set(last_ss.tags or [])
        tags_delta = ['-' + t for t in (tags_old - tags)] + ['+' + t for t in (tags - tags_old)]
        del tags_old
        if tags_delta:
            flag_cg |= 4

        staffs_old = {s.uid: s for s in (last_ss.staffs or [])}
        staffs_new = {int(s['uid']): Staff(int(s['uid']), s.get('role', ''), int(s.get('sort_order', 0))) for s in
                      staff}
        staffs_delta = []
        for uid, s in staffs_new.items():
            if uid not in staffs_old or staffs_old[uid] != s:
                staffs_delta.append(asdict(s))  # 加或改
        for uid in staffs_old:
            if uid not in staffs_new:
                staffs_delta.append({'uid': -uid, 'role': '', 'sort_order': 0})  # 删(uid 取负)
        del staffs_new, staffs_old
        if staffs_delta:
            flag_cg |= 8

        cid_old = {c.cid for c in (last_ss.cmt or [])}
        cid_new = {c.cid for c in comments}
        cmt_delta = [c for c in comments if c.cid not in cid_old] + \
                    [Comment(-c.cid, 0, DEFAULT_TS, '', 0, [], False, 0, 'video', 0) for c in (last_ss.cmt or []) if
                     c.cid not in cid_new]
        del cid_old, cid_new
        if cmt_delta:
            flag_cg |= 16

        dan_old = {d.danmaku_id for d in (last_ss.dan or [])}
        dan_new = {d.danmaku_id for d in danmaku}
        dan_delta = [d for d in danmaku if d.danmaku_id not in dan_old] + \
                    [Danmaku(-d.danmaku_id, '', 0, 'scroll', 0, 0, '') for d in (last_ss.dan or []) if
                     d.danmaku_id not in dan_new]
        del dan_old, dan_new
        if dan_delta:
            flag_cg |= 32

        h_cover = hashlib.sha1(cover_bytes)
        if h_cover.digest() == last_ss.c_sha1:
            cover_bytes = None
        else:
            flag_cg |= 64

        # print(f'******W+/video_before: last_addr={info_["new_addr_put"]}, h_video={h_video.hexdigest()}, \\')
        # print(f'******W+/video_before: last_ss.v_sha1={last_ss.v_sha1.hex()}')

        if h_video.digest() == last_ss.v_sha1:
            video_stream = None
        else:
            video_stream = open(tfp, 'rb')
            flag_cg |= 128

        pck = _writeSnapshot_stp1(version, f, dur=video_data.get('duration', 0),
                                  fav=video_data.get('favorite_count', 0),
                                  like=video_data.get('like_count', 0), view=video_data.get('view_count', 0),
                                  channel_id=channel_id,
                                  vid_type=vid_type, category=category,
                                  title=title_, intro=intro_,
                                  staff=staffs_delta, tags=tags_delta, comments=cmt_delta, flag2=flag, flag_cg=flag_cg,
                                  cover_bytes=cover_bytes, danmaku=dan_delta, video_stream=video_stream, config=config)
        video_stream.close() if hasattr(video_stream, 'close') else 0
        # ==============================回填+清理==============================
        _writeSnapshot_stp2(version, f, *pck)
        f.seek(0xa)
        f.write(struct.pack('<H', snapshot_num + 1))
        f.seek(0, 2)
        total = f.tell()
        f.seek(0x10)
        f.write(struct.pack('<Q', total))
        f.seek(0x20)
        f.write(struct.pack('<Q', info_['new_addr']))
        f.seek(info_['new_addr_put'])
        f.write(struct.pack('<Q', info_['new_addr']))
        f.seek(0, 2)
        f.write(_OVARC_END_MARKER)
    os.remove(tfp)
    logger.info(f'[_writeOvarc2p_append/v{version}]temp video file cleared')

    if config.verbose:
        logger.info(f"[_writeOvarc2p_append/v{version}]Append complete: {fp}")
    return fp


def _writeOvarc_disp(version: int, vid: int, video_data: dict, comments: list[Comment], danmaku: list[Danmaku],
                     video_stream: Union[bytes, Response], cover_bytes: bytes, fp, action: bool, config: Config = None):
    """action: True -> 新建。False -> 添加。
    comments要树。"""
    if version <= 1:
        return _writeOvarc1(vid, video_data, comments, danmaku, video_stream, cover_bytes, fp, config)
    else:
        comments = flattenComments(comments)  # 树->扁平，设parent_cid，清空replies
        if action:
            # raise NotImplementedError("追加快照还没写")
            return _writeOvarc2p_create(version, vid, video_data, comments, danmaku, video_stream, cover_bytes, fp,
                                        config)
        else:
            return _writeOvarc2p_append(version, vid, video_data, comments, danmaku, video_stream, cover_bytes, fp,
                                        config)


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


def _uni(version: int, vid: int, f) -> list[_ISnapshotVesicle]:
    res = []
    addr = 0x28  # 第一个快照
    while addr != 0:
        vesicle = _readSnapshot(version, vid, f, addr)
        res.append(vesicle)
        addr = vesicle.next_addr
    return res


def _loadOvarc2p(version: int, fp: str) -> VideoSnapshots:
    with open(fp, "rb") as f:
        header = f.read(6)
        # 提取头
        if header[:5] != b'OVARC':
            raise VerificationError(f"{fp}不是有效的.ovarc文件")
        pub_ts, s_num, uid, size, _, vid, flag, _, last_ss = struct.unpack('<IHIQHIBBQ', f.read(34))
        ss = _uni(version, vid, f)
    return VideoSnapshots(pub_ts, s_num, uid, vid, flag, ss, fp)


def _loadOvarc_disp(ver, fp):
    if ver == 1:
        return _loadOvarc1(fp)
    else:
        return _loadOvarc2p(ver, fp)


def loadVideo(vid: int, fn: str = None, config: Config = None) -> Union[VideoEntry, VideoSnapshots]:
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
                             temp_file_path, action=True, config=config)
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
        # raise NotImplementedError  # 我好像是不知道了。
        _writeOvarc_disp(version, vid, video_data, comments, danmaku_list, video_stream, cover_binary,
                         file_path, action=False, config=config)
    return file_path, True


def saveVideo(vid: int, config: Config = None) -> tuple[str, bool]:
    """存储视频至.ovarc文件。"""
    return _saveVideo(_LATEST_OVARC_VER, vid, config)
