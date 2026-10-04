import sqlite3
import os
from typing import Union, Tuple, Generator
from time import time
from ..core.config import Config, getGlobalConfig
from ..core.util import parseTime, _request, startEnd, BlogEntry, flattenComments, Comment, VideoEntry, Danmaku, logger, _c
from ..core._const import _RED
from dataclasses import asdict, dataclass
from enum import IntEnum
from contextlib import contextmanager


def _tag_factory(tags: list[str]) -> str:
    try:
        tags.remove('吉吉国民')
    except ValueError:
        pass
    return ''.join('#' + t for t in tags)


class _MT(IntEnum):
    # 因为记不住。
    UNKNOWN = 0
    USER = 1
    BLOG = 2
    M_OBC_API = 3
    M_BLOG_ENTRY = 4
    OBC = 5
    OVC = 6
    OSC = 7
    M_OSC_API = 8
    FOLLOW = 9
    BLOG_COLL = 10
    VIDEO_COLL = 11
    SEIGA_COLL = 12
    SEIGA = 13
    SEIGA_TAG = 14
    SEIGA_TAGMAP = 15
    SEIGA_PAGE = 16
    VIDEO = 17
    MEDIA = 18
    CHANNEL = 19
    CHANNEL_SECTION = 20
    CHANNEL_NOTICE = 21
    VIDEO_STAFF = 22
    DANMAKU = 23
    CHANNEL_PIN = 24


@dataclass(frozen=True)
class _SQLBatch:
    sql_type: _MT
    data: list[dict]


#########################################################################################
# {sql_type: int -> tuple[table_name: str, table_def: str, prim_key: str]}
_MAP = {
    _MT.USER: ('oh_user_v1', '''uid INTEGER PRIMARY KEY NOT NULL, name TEXT, intro TEXT, create_ts INTEGER,
        sex TEXT, honour TEXT, exp INTEGER, avatar BLOB, cover_h BLOB, cover_v BLOB, video INTEGER, blog INTEGER,
        seiga INTEGER, media INTEGER, follow INTEGER, fan INTEGER, arc_ts INTEGER''', 'uid'),
    _MT.BLOG: ('oh_blog_v1', '''bid INTEGER PRIMARY KEY NOT NULL, uid INTEGER, pub_ts INTEGER, arc_ts INTEGER,
        channel INTEGER, like_count INTEGER, fav_count INTEGER, view_count INTEGER, attached_vid INTEGER, copyright_type INTEGER,
        blog_type INTEGER, comment_count INTEGER, title TEXT, content TEXT, tags TEXT, gore INTEGER, forward_bid INTEGER,
        forward_died INTEGER''', 'bid'),
    _MT.OBC: ('oh_obc_v1', '''bcid INTEGER PRIMARY KEY NOT NULL, bid INTEGER, uid INTEGER, parent_bcid INTEGER DEFAULT 0,
        pub_ts INTEGER, arc_ts INTEGER, content TEXT, reply_count INTEGER DEFAULT 0, pin_order INTEGER DEFAULT 0''',
              'bcid'),
    _MT.OVC: ('oh_ovc_v1', '''vcid INTEGER PRIMARY KEY NOT NULL, vid INTEGER, uid INTEGER, parent_vcid INTEGER DEFAULT 0,
        pub_ts INTEGER, arc_ts INTEGER, content TEXT, reply_count INTEGER DEFAULT 0, pin_order INTEGER DEFAULT 0''',
              'vcid'),
    _MT.OSC: ('oh_osc_v1', '''scid INTEGER PRIMARY KEY NOT NULL, sid INTEGER, uid INTEGER, parent_scid INTEGER DEFAULT 0, 
        pub_ts INTEGER, arc_ts INTEGER, content TEXT, reply_count INTEGER DEFAULT 0, pin_order INTEGER DEFAULT 0''',
              'scid'),
    _MT.FOLLOW: ('oh_follow_v1', 'uid INTEGER, target_uid INTEGER, PRIMARY KEY (uid, target_uid)', 'uid, target_uid'),
    _MT.BLOG_COLL: ('oh_blog_collection_v1', '''bid INTEGER NOT NULL, uid INTEGER, name TEXT NOT NULL, 
        sort_order INTEGER, arc_ts INTEGER, PRIMARY KEY (name, bid)''', 'name, bid'),
    _MT.VIDEO_COLL: ('oh_video_collection_v1', '''vid INTEGER NOT NULL, uid INTEGER, name TEXT NOT NULL, 
        sort_order INTEGER, arc_ts INTEGER, PRIMARY KEY (name, vid)''', 'name, vid'),
    _MT.SEIGA_COLL: ('oh_seiga_collection_v1', '''sid INTEGER NOT NULL, uid INTEGER, name TEXT NOT NULL, 
        sort_order INTEGER, arc_ts INTEGER, PRIMARY KEY (name, sid)''', 'name, sid'),
    _MT.SEIGA: ('oh_seiga_v1', '''sid INTEGER PRIMARY KEY NOT NULL, uid INTEGER, title TEXT, description TEXT, pages INTEGER, 
        is_doujin INTEGER DEFAULT 0, is_ai INTEGER DEFAULT 0, is_gore INTEGER DEFAULT 0, hall TEXT, 
        pub_ts INTEGER, arc_ts INTEGER, fav_count INTEGER, view_count INTEGER, comment_count INTEGER''', 'sid'),
    _MT.SEIGA_TAG: ('oh_seiga_tag_v1', 'tid INTEGER PRIMARY KEY NOT NULL, name TEXT NOT NULL', 'tid'),
    _MT.SEIGA_TAGMAP: ('oh_seiga_tagmap_v1', '''sid INTEGER NOT NULL, tid INTEGER NOT NULL, is_locked INTEGER DEFAULT 0, 
        lock_sort INTEGER DEFAULT 0, added_by INTEGER, arc_ts INTEGER, PRIMARY KEY (sid, tid)''', 'sid, tid'),
    _MT.SEIGA_PAGE: ('oh_seiga_page_v1', '''sid INTEGER PRIMARY KEY NOT NULL, page_no INTEGER, asset_id INTEGER, original BLOB, 
        original_url TEXT, width INTEGER, height INTEGER, is_animated INTEGER DEFAULT 0, arc_ts INTEGER, CHECK 
        ((original IS NULL AND original_url IS NOT NULL) OR (original IS NOT NULL AND original_url IS NULL))''', 'sid'),
    _MT.VIDEO: ('oh_video_v1', '''vid INTEGER PRIMARY KEY NOT NULL, uid INTEGER, title TEXT, intro TEXT, vid_type INTEGER, 
        category INTEGER, channel_id INTEGER, tags TEXT, pub_ts INTEGER, like_count INTEGER, fav_count INTEGER, view_count INTEGER,
        comment INTEGER, cover BLOB, video_url TEXT, video_local TEXT, video_m3u8_url TEXT, audio_url TEXT, dur INTEGER,
        arc_ts INTEGER, gore INTEGER, CHECK ((video_url IS NULL AND video_local IS NOT NULL) OR 
        (video_url IS NOT NULL AND video_local IS NULL))''', 'vid'),
    _MT.MEDIA: ('oh_media_v1', '''m_id INTEGER PRIMARY KEY NOT NULL, uid INTEGER, ext TEXT, title TEXT, description TEXT, 
        tags TEXT, orig_source TEXT, media_type TEXT, copyright_type INTEGER, file_size INTEGER, pub_ts INTEGER, 
        file_url TEXT, file_local TEXT, fav_count INTEGER, arc_ts INTEGER, CHECK((file_url IS NULL AND file_local IS NOT NULL) 
        OR (file_url IS NOT NULL AND file_local IS NULL))''', 'm_id'),
    _MT.CHANNEL: ('oh_channel_v1', '''cid INTEGER PRIMARY KEY NOT NULL, name TEXT, title TEXT, description TEXT, cover BLOB, 
        cover_url TEXT, creator_uid INTEGER, owner_uid INTEGER, admin_uid_list TEXT, join_permission INTEGER, 
        open_post INTEGER, member INTEGER, follower INTEGER, create_ts INTEGER, update_ts INTEGER, arc_ts INTEGER,
        CHECK ((cover_url IS NULL AND cover IS NOT NULL) OR (cover_url IS NOT NULL AND cover IS NULL))''', 'cid'),
    _MT.CHANNEL_SECTION: ('oh_channel_section_v1', '''cid INTEGER, section_id INTEGER, name TEXT, description TEXT,
        icon BLOB, sort_order INTEGER, creator_uid INTEGER, create_ts INTEGER, update_ts INTEGER, arc_ts INTEGER,
        is_deleted INTEGER, video INTEGER, blog INTEGER, total INTEGER, PRIMARY KEY (cid, section_id)''',
                          'cid, section_id'),
    _MT.CHANNEL_NOTICE: ('oh_channel_notice_v1', '''cid INTEGER, notice_id INTEGER, title TEXT, content TEXT, sort_order INTEGER,
        creator_uid INTEGER, create_ts INTEGER, update_ts INTEGER, arc_ts INTEGER, is_deleted INTEGER, 
        PRIMARY KEY (cid, notice_id)''', 'cid, notice_id'),
    _MT.VIDEO_STAFF: ('oh_video_staff_v1', '''vid INTEGER NOT NULL, uid INTEGER NOT NULL, role TEXT, sort_order INTEGER, 
    PRIMARY KEY (vid, uid)''', 'vid, uid'),
    _MT.DANMAKU: ('oh_danmaku_v1', '''danmaku_id INTEGER PRIMARY KEY NOT NULL, vid INTEGER, text TEXT, time_ms INTEGER, 
    mode TEXT, color_rgb INTEGER, font_size INTEGER, render INTEGER''', 'danmaku_id'),
    _MT.CHANNEL_PIN: ('oh_channel_pin_v1', '''pin_id INTEGER PRIMARY KEY NOT NULL, cid INTEGER, type TEXT,
    content_id INTEGER, sort_order INTEGER, arc_ts INTEGER''', 'pin_id'),
}
##########################################################################################
# {api_k: str -> tuple[db_k: str, factory: callable]}
_MAP_USER = {'uid': ('uid', int), 'username': ('name', None), 'intro': ('intro', None),
             'time': ('create_ts', parseTime), 'sex': ('sex', None),
             'honour': ('honour', None), 'experience': ('exp', int), 'video_num': ('video', int),
             'blog_num': ('blog', int), 'seiga_num': ('seiga', int), 'media_num': ('media', int),
             'followings_count': ('follow', int), 'fans_count': ('fan', int)}
# _MAP_BLOG_API特殊处理forward_died。
_MAP_BLOG_API = {'bid': ('bid', int), 'uid': ('uid', int), 'time': ('pub_ts', parseTime),
                 'like_count': ('like_count', int),
                 'favorite_count': ('fav_count', int), 'view_count': ('view_count', int),
                 'attached_vid': ('attached_vid', int),
                 'copyright_type': ('copyright_type', int), 'blog_type': ('blog_type', int),
                 'comment_count': ('comment_count', int), 'title': ('title', None), 'content': ('content', None),
                 'is_gore': ('gore', int), 'tag': ('tags', _tag_factory), 'channel_id': ('channel', int),
                 'forward_bid': ('forward_bid', None)}
# _MAP_OBC_API特殊处理bid, API不返回。
_MAP_OBC_API = {'bcid': ('bcid', int), 'uid': ('uid', int), 'parent_bcid': ('parent_bcid', int),
                'time': ('pub_ts', parseTime), 'content': ('content', None), 'child_comment_num': ('reply_count', int),
                'pin_order': ('pin_order', int)}
_MAP_BLOG_ENTRY = {'bid': ('bid', int), 'uid': ('uid', int), 'timestamp': ('pub_ts', None),
                   'like_count': ('like_count', int),
                   'favorite_count': ('fav_count', int), 'view_count': ('view_count', int),
                   'attached_vid': ('attached_vid', int),
                   'copyright_type': ('copyright_type', int), 'blog_type': ('blog_type', int),
                   'title': ('title', None), 'content': ('content', None), 'tags': ('tags', _tag_factory),
                   'arc_time': ('arc_ts', None), 'channel_id': ('channel', None), 'is_gore': ('gore', int),
                   'forward_bid': ('forward_bid', None), 'is_unavailable': ('forward_died', int)}
# Comment类没有bid/vid/sid字段。
_MAP_OBC = {'cid': ('bcid', None), 'uid': ('uid', None), 'timestamp': ('pub_ts', None), 'content': ('content', None),
            'reply_count': ('reply_count', None), 'pin_order': ('pin_order', None), 'parent_cid': ('parent_bcid', None)}
_MAP_OVC = {'cid': ('vcid', None), 'uid': ('uid', None), 'timestamp': ('pub_ts', None), 'content': ('content', None),
            'reply_count': ('reply_count', None), 'pin_order': ('pin_order', None), 'parent_cid': ('parent_vcid', None)}
_MAP_OSC = {'cid': ('scid', None), 'uid': ('uid', None), 'timestamp': ('pub_ts', None), 'content': ('content', None),
            'reply_count': ('reply_count', None), 'pin_order': ('pin_order', None), 'parent_cid': ('parent_scid', None)}
# _MAP_OSC_API特殊处理sid, API不返回。
_MAP_OSC_API = {'bcid': ('scid', int), 'uid': ('uid', int), 'parent_scid': ('parent_scid', int),
                'time': ('pub_ts', parseTime), 'content': ('content', None), 'child_comment_num': ('reply_count', int)}
_MAP_SEIGA_API = {'sid': ('sid', int), 'uid': ('uid', int), 'title': ('title', None), 'view_count': ('view_count', int),
                  'description': ('description', None), 'page_count': ('pages', int), 'is_fanwork': ('is_doujin', int),
                  'hall_at': ('hall', None), 'is_ai': ('is_ai', int), 'is_gore': ('is_gore', int),
                  'time': ('pub_ts', parseTime), 'favorite_count': ('fav_count', int),
                  'comment_count': ('comment_count', int)}
# _MT.FOLLOW不需要map。
# _MAP_*_COLL_API特殊处理name, arc_ts。
_MAP_BLOG_COLL_API = {'bid': ('bid', int), 'uid': ('uid', int), 'collection_sort_order': ('sort_order', int)}
_MAP_VIDEO_COLL_API = {'vid': ('vid', int), 'uid': ('uid', int), 'collection_sort_order': ('sort_order', int)}
_MAP_SEIGA_COLL_API = {'sid': ('sid', int), 'uid': ('uid', int), 'collection_sort_order': ('sort_order', int)}
# _MT.SEIGA_PAGE, _MT.SEIGA_TAG, _MT.SEIGA_TAGMAP不需要map。
# _MAP_VIDEO_API特殊处理video_local, staff, video_url, arc_ts。
_MAP_VIDEO_API = {'vid': ('vid', int), 'uid': ('uid', int), 'title': ('title', None), 'intro': ('intro', None),
                  'type': ('vid_type', int), 'category': ('category', int), 'channel_id': ('channel_id', int),
                  'tag': ('tags', None), 'time': ('pub_ts', parseTime), 'like_count': ('like_count', int),
                  'favorite_count': ('fav_count', int), 'view_count': ('view_count', int),
                  'comment_count': ('comment', int),
                  'duration': ('dur', int), 'audio_url': ('audio_url', None), 'is_gore': ('gore', int),
                  'video_m3u8_url': ('video_m3u8_url', None)}
# _MAP_MEDIA_API特殊处理file_local, file_url, arc_ts
_MAP_MEDIA_API = {'media_id': ('m_id', int), 'uid': ('uid', int), 'extension': ('ext', None),
                  'title': ('title', None), 'intro': ('description', None), 'tag': ('tags', None),
                  'original_source': ('orig_source', None), 'media_type': ('media_type', None),
                  'copyright_type': ('copyright_type', int), 'file_size': ('file_size', int),
                  'created_at': ('pub_ts', parseTime), 'favorite_count': ('fav_count', int)}
# _MAP_CHANNEL_API特殊处理cover, cover_url, arc_ts
_MAP_CHANNEL_API = {'channel_id': ('cid', int), 'channel_name': ('name', None), 'channel_title': ('title', None),
                    'description': ('description', None), 'creator_uid': ('creator_uid', int),
                    'owner_uid': ('owner_uid', int), 'admin_uids': ('admin_uid_list', lambda x: ','.join(str(i) for i in x)),
                    'join_permission': ('join_permission', int), 'open_post': ('open_post', int),
                    'member_count': ('member', None), 'follower_count': ('follower', int),
                    'created_at': ('create_ts', parseTime), 'updated_at': ('update_ts', parseTime)}
# _MAP_COLLECTION(C)_API特殊处理icon, arc_ts, video, blog, total
_MAP_C_SECTION = {'channel_id': ('cid', int), 'channel_section_id': ('section_id', int), 'section_name': ('name', None),
                  'description': ('description', None), 'sort_order': ('sort_order', int),
                  'creator_uid': ('creator_uid', int), 'created_at': ('create_ts', parseTime),
                  'updated_at': ('update_ts', parseTime), 'is_deleted': ('is_deleted', int)}
_MAP_C_NOTICE = {'channel_id': ('cid', int), 'notice_id': ('notice_id', int), 'title': ('title', None),
                 'content': ('content', None), 'sort_order': ('sort_order', int),
                 'creator_uid': ('creator_uid', int), 'created_at': ('create_ts', parseTime),
                 'updated_at': ('update_ts', parseTime), 'is_deleted': ('is_deleted', int)}
_MAP_DANMAKU = {'danmaku_id': ('danmaku_id', None), 'text': ('text', None), 'time_ms': ('time_ms', None),
                'mode': ('mode', None), 'color_rgb': ('color_rgb', None), 'font_size': ('font_size', None),
                'render': ('render', lambda x: x if x else None)}
_MAP_CHANNEL_PIN_API = {'pin_id': ('pin_id', int), 'type': ('type', None), 'content_id': ('content_id', int),
                    'sort_order': ('sort_order', int)}
#########################################################################################
# map_type: int -> map: dict
# sql_type集合是map_type集合的真子集。
# 未做map：
# (19, 'oh_channel_v1'), (20, 'oh_channel_section_v1'), (21, 'oh_channel_notice_v1')]
# 各种2DB返回的是sql_type不是map_type。
# 我服了我自己了，写出来一个奇丑的tuple[tuple[int, dict], tuple[int, list[dict]], tuple[int, list[dict]], tuple[int, list[dict]]]。
# 最后还是改了。
# 我在干什么。现在(*2026/9/12)凌晨2点半了。果然熬夜写这个不好。
_META_MAP = {
    _MT.USER: _MAP_USER, _MT.BLOG: _MAP_BLOG_API, _MT.M_OBC_API: _MAP_OBC_API, _MT.M_BLOG_ENTRY: _MAP_BLOG_ENTRY,
    _MT.OBC: _MAP_OBC, _MT.OVC: _MAP_OVC, _MT.OSC: _MAP_OSC, _MT.M_OSC_API: _MAP_OSC_API,
    _MT.BLOG_COLL: _MAP_BLOG_COLL_API, _MT.VIDEO_COLL: _MAP_VIDEO_COLL_API, _MT.SEIGA_COLL: _MAP_SEIGA_COLL_API,
    _MT.SEIGA: _MAP_SEIGA_API,
    _MT.VIDEO: _MAP_VIDEO_API,
    _MT.MEDIA: _MAP_MEDIA_API,
    _MT.CHANNEL: _MAP_CHANNEL_API, _MT.CHANNEL_NOTICE: _MAP_C_NOTICE, _MT.CHANNEL_SECTION: _MAP_C_SECTION,
    _MT.CHANNEL_PIN: _MAP_CHANNEL_PIN_API,
    _MT.DANMAKU: _MAP_DANMAKU,
}
#########################################################################################


def _process(data: dict, sql_type: _MT) -> dict:
    mapped = {}
    for api_key, (db_key, factory) in _META_MAP[sql_type].items():
        if api_key in data:
            if factory is None:
                mapped[db_key] = data[api_key]
            else:
                mapped[db_key] = factory(data[api_key])
    return mapped


@startEnd
def user2DB(data: dict, config: Config = None, **_) -> tuple[_SQLBatch]:
    """映射getUserDetail(...)的字段至oh_user，附处理。"""
    if config is None:
        config = getGlobalConfig()
    mapped = _process(data, _MT.USER)  # 1
    mapped['arc_ts'] = int(time())  # 使用当前时间代替
    mapped['avatar'] = _request('get', 'content', 'user2DB', data['avatar_url'], config=config)
    mapped['cover_h'] = _request('get', 'content', 'user2DB', data['cover_h_url'], config=config)
    mapped['cover_v'] = _request('get', 'content', 'user2DB', data['cover_v_url'], config=config)
    return _SQLBatch(_MT.USER, [mapped]),


def blog2DB(data: Union[dict, BlogEntry], **_) -> tuple[_SQLBatch]:
    """映射getBlogDetail(...)和BlogEntry的字段至oh_blog。"""
    if isinstance(data, BlogEntry):
        data = data.toDictShallow()
        mapped = _process(data, _MT.M_BLOG_ENTRY)  # 4
        mapped['comment_count'] = len(flattenComments(data['comments']))
    else:
        mapped = _process(data, _MT.BLOG)  # 2
        mapped['arc_ts'] = int(time())  # 使用当前时间代替
        forward = data['forward']
        if forward is not None:
            mapped['forward_died'] = forward.get('is_unavailable')
    return _SQLBatch(_MT.BLOG, [mapped]),


def commentRaw2DB(data: list[dict], from_id: int = 0, **_) -> tuple[_SQLBatch]:
    """不建议使用。
    映射_get*CommentList(...)的字段至对应的数据表。会自动判断评论类型。
    提供from_id: int以向表中存储评论所在的bid/sid字段。"""
    res = []
    id_ = _MT.UNKNOWN
    if len(data) == 0:
        return _SQLBatch(id_, []),
    if data[0].get("bcid"):
        # blog
        for b in data:
            mapped = _process(b, _MT.M_OBC_API)  # 3
            if from_id:
                mapped['bid'] = from_id
            res.append(mapped)
        id_ = _MT.M_OBC_API
    elif data[0].get("scid"):
        # seiga
        for b in data:
            mapped = _process(b, _MT.M_OSC_API)  # 8
            if from_id:
                mapped['sid'] = from_id
            res.append(mapped)
        id_ = _MT.M_OSC_API
    return _SQLBatch(id_, res),


def comments2DB(data: Union[list[Comment], Comment], from_id: int = 0, **_) -> tuple[_SQLBatch]:
    """映射getAll*Comments(...)和Comment的字段至对应的数据表。
    提供from_id: int以向表中存储评论所在的bid/vid/sid字段。"""
    if isinstance(data, Comment):
        data = [data]
    if isinstance(data, list) and len(data) == 0:
        return _SQLBatch(_MT.UNKNOWN, []),
    data = flattenComments(data)
    res, id_ = [], _MT.UNKNOWN
    for c in data:
        if c.c_type == 'blog':
            d = asdict(c)
            mapped = _process(d, _MT.OBC)  # 5
            if from_id:
                mapped['bid'] = from_id
            id_ = _MT.OBC
        elif c.c_type == 'video':
            d = asdict(c)
            mapped = _process(d, _MT.OVC)  # 6
            if from_id:
                mapped['vid'] = from_id
            id_ = _MT.OVC
        elif c.c_type == 'seiga':
            d = asdict(c)
            mapped = _process(d, _MT.OSC)  # 7
            if from_id:
                mapped['sid'] = from_id
            id_ = _MT.OSC
        else:
            raise ValueError(f'不支持的Comment.c_type类型: {data.c_type}')
        mapped['arc_ts'] = int(time())
        res.append(mapped)
    return _SQLBatch(id_, res),


def following2DB(data: list[dict], main_uid: int, **_) -> tuple[_SQLBatch]:
    """映射关注的用户信息至数据表。需要提供main_uid (关注者uid)。
    data可以从ohutils.user_api.getAllFollowings(main_uid)获取。"""
    result = []
    for relation in data:
        result.append({'uid': main_uid, 'target_uid': relation['uid']})
    return _SQLBatch(_MT.FOLLOW, result),


@startEnd
def seiga2DB(data: dict, config: Config = None, **_) -> tuple[_SQLBatch, _SQLBatch, _SQLBatch, _SQLBatch]:
    """映射getSeigaDetail(...)的字段至数据表。"""
    sid = int(data['sid'])
    mapped = _process(data, _MT.SEIGA)  # 13
    mapped['arc_ts'] = int(time())
    tag_dicts, tagmap_dicts, page_dicts = [], [], []
    for t in data['tags']:
        tid = int(t['tag_id'])
        tag_dicts.append({'tid': tid, 'name': t['tag_name']})
        tagmap_dicts.append({'sid': sid, 'tid': tid, 'is_locked': t['is_locked'],
                             'lock_sort': t['lock_sort'], 'added_by': int(t['added_by_uid']), 'arc_ts': int(time())})
    for p in data['pages']:
        p_dict = {'sid': sid, 'page_no': int(p['page_no']), 'asset_id': int(p['image_asset_id']),
                  'width': int(p['width']), 'height': int(p['height']), 'is_animated': p['is_animated'],
                  'original': _request('get', 'content', 'seiga2DB', p['original_url'], config=config),
                  'arc_ts': int(time())}
        page_dicts.append(p_dict)
    return (_SQLBatch(_MT.SEIGA, [mapped]), _SQLBatch(_MT.SEIGA_TAG, tag_dicts),
            _SQLBatch(_MT.SEIGA_TAGMAP, tagmap_dicts), _SQLBatch(_MT.SEIGA_PAGE, page_dicts))


def collection2DB(data: list[dict], coll_name: str, **_) -> tuple[_SQLBatch]:
    res, id_ = [], _MT.UNKNOWN
    if len(data) == 0:
        return _SQLBatch(_MT.UNKNOWN, []),
    for b in data:
        if 'bid' in data[0]:
            mapped = _process(b, _MT.BLOG_COLL)
            id_ = _MT.BLOG_COLL
        elif 'vid' in data[0]:
            mapped = _process(b, _MT.VIDEO_COLL)
            id_ = _MT.VIDEO_COLL
        elif 'sid' in data[0]:
            mapped = _process(b, _MT.SEIGA_COLL)
            id_ = _MT.SEIGA_COLL
        else:
            raise ValueError(f'存在不支持的collection类型')
        mapped['arc_ts'] = int(time())  # 使用当前时间代替
        mapped['name'] = coll_name
        res.append(mapped)
    return _SQLBatch(id_, res),


def video2DB(data, video_local: str = None, config: Config = None, **_) -> tuple[_SQLBatch, _SQLBatch]:
    mapped = _process(data, _MT.VIDEO)
    mapped['arc_ts'] = int(time())
    if video_local is None:
        mapped['video_url'] = data['video_url']
    else:
        mapped['video_local'] = video_local
    mapped['cover'] = _request('get', 'content', 'video2DB', data['cover_url'], config=config)

    staffs = []
    for s in data['staff']:
        staffs.append({'vid': data['vid'], 'uid': s['uid'], 'role': s['role'], 'sort_order': int(s['sort_order'])})
    return _SQLBatch(_MT.VIDEO, [mapped]), _SQLBatch(_MT.VIDEO_STAFF, staffs)


def media2DB(data, file_local: str = None, **_) -> tuple[_SQLBatch]:
    mapped = _process(data, _MT.MEDIA)
    mapped['arc_ts'] = int(time())
    if file_local is None:
        mapped['file_url'] = data['file_url']
    else:
        mapped['file_local'] = file_local
    return _SQLBatch(_MT.MEDIA, [mapped]),


def channel2DB(data: dict, send_request: bool = True, config: Config = None, **_) -> tuple[_SQLBatch]:
    mapped = _process(data, _MT.CHANNEL)
    mapped['arc_ts'] = int(time())
    if send_request:
        mapped['cover'] = _request('get', 'content', 'channel2DB', data['cover_url'], config=config)
    else:
        mapped['cover_url'] = data['cover_url']
    return _SQLBatch(_MT.CHANNEL, [mapped]),


def channelSection2DB(data, config: Config = None, **_) -> tuple[_SQLBatch]:
    res = []
    for d in data['sections']:
        mapped = _process(d, _MT.CHANNEL_SECTION)
        mapped['arc_ts'] = int(time())
        t_ = d['content_count']
        mapped['video'], mapped['blog'], mapped['total'] = t_['video_count'], t_['blog_count'], t_['total_count']
        if d['icon_url']:
            mapped['icon'] = _request('get', 'content', 'channelSection2DB', d['icon_url'], config=config)
        res.append(mapped)
    return _SQLBatch(_MT.CHANNEL_SECTION, res),


def channelNotice2DB(data, **_) -> tuple[_SQLBatch]:
    res = []
    for d in data['notices']:
        mapped = _process(d, _MT.CHANNEL_NOTICE)
        mapped['arc_ts'] = int(time())
        res.append(mapped)
    return _SQLBatch(_MT.CHANNEL_NOTICE, res),


def channelPin2DB(data: list[dict], from_cid: int = 0, **_) -> tuple[_SQLBatch]:
    """提供from_id: int以向表中存储评论所在的cid。"""
    result = []
    for pin in data:
        mapped = _process(pin, _MT.CHANNEL_PIN)
        mapped['cid'] = from_cid
        mapped['arc_ts'] = int(time())
        result.append(mapped)
    return _SQLBatch(_MT.CHANNEL_PIN, result),


def danmaku2DB(data: Union[Danmaku, list[Danmaku]], from_vid: int = 0, **_) -> tuple[_SQLBatch]:
    """映射Danmaku类至oh_danmaku。
    提供from_id: int以向表中存储评论所在的vid。"""
    if isinstance(data, Danmaku):
        data = [data]
    res = []
    for d in data:
        mapped = _process(asdict(d), _MT.DANMAKU)
        if from_vid:
            mapped['vid'] = from_vid
        res.append(mapped)  # 23
    return _SQLBatch(_MT.DANMAKU, res),


def auto2DB(data, **kwargs):
    """自动判断类型并映射字段。
    main_uid: (仅following)关注者uid。
    coll_name: (仅collection list)合集名称。
    from_id: (可选，仅Comment)评论所在的bid/vid/sid字段。
    from_cid: (可选，仅channel pin dict)所在频道id。
    from_vid: (可选，仅Danmaku)弹幕所在vid。
    file_local: (可选，仅media dict)本地存储路径。
    video_local: (可选，仅video dict)本地存储路径。
    send_request: (可选，仅channel dict)发送请求以保存二进制。
    config: (可选，仅user dict和seiga dict和video dict和channel dict和channel section dict)配置。"""
    if isinstance(data, BlogEntry):
        return blog2DB(data)  # blog2DB的BlogEntry式
    if isinstance(data, Comment):
        return comments2DB(data, **kwargs)  # comments2DB的Comment式
    if isinstance(data, Danmaku):
        return danmaku2DB(data, **kwargs)  # danmaku2DB的Danmaku式
    if isinstance(data, list):
        if not data:
            return _SQLBatch(_MT.UNKNOWN, []),
        if isinstance(data[0], Danmaku):
            return danmaku2DB(data, **kwargs)  # danmaku2DB的list[Danmaku]式
        if isinstance(data[0], Comment):
            return comments2DB(data, **kwargs)  # comments2DB的list[Comment]式
        if 'bcid' in data[0] or 'scid' in data[0]:
            return commentRaw2DB(data, **kwargs)
        if 'follow_status' in data[0]:
            return following2DB(data, **kwargs)
        if 'pin_id' in data[0]:
            return channelPin2DB(data, **kwargs)
        if 'collection_sort_order' in data[0]:
            return collection2DB(data, **kwargs)
    if isinstance(data, dict):
        if 'bid' in data and 'title' in data:
            return blog2DB(data)  # blog2DB的dict式
        if 'uid' in data and 'experience' in data and 'sex' in data:
            return user2DB(data, **kwargs)
        if 'sid' in data and 'description' in data:
            return seiga2DB(data, **kwargs)
        if 'vid' in data and 'staff' in data:
            return video2DB(data, **kwargs)
        if 'channel_name' in data and 'join_permission' in data:
            return channel2DB(data, **kwargs)
        if 'sections' in data:
            return channelSection2DB(data, **kwargs)
        if 'notices' in data:
            return channelNotice2DB(data)
        if 'media_id' in data:
            return media2DB(data, **kwargs)
    raise ValueError("无法识别数据类型")


@contextmanager
def loadTable(config: Config = None) -> Generator[sqlite3.Connection, None, None]:
    """上下文管理器，自动关闭连接。
    用法: with loadTable() as conn: ..."""
    if config is None:
        config = getGlobalConfig()
    conn = sqlite3.connect(os.path.join(config.indexPath, config.SQLName))
    try:
        yield conn
    finally:
        conn.close()


def _writeData(sql_type: _MT, data: dict, conn: sqlite3.Connection, no_update: bool = False):
    cur = conn.cursor()
    keys = data.keys()
    table_name, _, prim_key = _MAP[sql_type]
    if no_update:
        cur.execute(
            f"INSERT OR IGNORE INTO {table_name} ({', '.join(keys)}) VALUES ({', '.join('?' * len(keys))})",
            tuple(data.values())
        )
    else:
        conflict = f"ON CONFLICT({prim_key}) DO UPDATE SET " + \
                   ", ".join([f"{k} = excluded.{k}" for k in keys if k != prim_key])
        cur.execute(
            f"INSERT INTO {table_name} ({', '.join(keys)}) VALUES ({', '.join('?' * len(keys))}) {conflict}",
            tuple(data.values())
        )
    conn.commit()


def writeSQL(batches: tuple[_SQLBatch, ...], no_update: bool = False, config: Config = None):
    """批量写入数据库。接收来自*2DB的值。"""
    if config is None:
        config = getGlobalConfig()
    conn = sqlite3.connect(os.path.join(config.indexPath, config.SQLName))
    cur = conn.cursor()
    for sql_ in batches:
        sql_type, sql_dicts = sql_.sql_type, sql_.data
        if sql_type == 0:
            continue
        table_name, table_def, _ = _MAP[sql_type]
        cur.execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({table_def})')
        for row in sql_dicts:
            _writeData(sql_type, row, conn, no_update)
    conn.close()


def readData(sql_type: int, conn: sqlite3.Connection, fields: list = None, **kwargs) -> list:
    """从指定数据库读取选择的字段(fields)，带条件。
    条件的比较运算符: 若无后缀，为等于(=)。
    若有__gt / __lt / __ge / __le / __ne / __like后缀，
    则分别为大于(>)，小于(<)，大于等于(>=)，小于等于(<=)，不等于(!=)，LIKE。

    e.g.:
    view__le=132 -> view <= 132
    exp__gt=100 -> exp > 100
    fav=15 -> fav = 15
    """
    cur = conn.cursor()
    fields_str = ", ".join(fields) if fields else "*"
    kv = []
    map_ = {'lt': '<', 'gt': '>', 'le': '<=', 'ge': '>=', 'ne': '!=', 'like': ' LIKE '}
    for k in kwargs.keys():
        # 哦还有rsplit这种东西的啊。
        k_list = k.rsplit('__', maxsplit=1)
        if len(k_list) == 1:
            kv.append(k + '=?')  # 无后缀
        else:
            if k_list[1] not in map_.keys():
                map_[k_list[1]] = '__' + k_list[1]  # 若误分割，拼回来
            kv.append(k_list[0] + map_[k_list[1]] + '?')
    cond = ('WHERE ' if kwargs.keys() else '') + " AND ".join(kv)
    query = f"SELECT {fields_str} FROM {_MAP[sql_type][0]} {cond}"
    cur.execute(query, tuple(kwargs.values()))
    return cur.fetchall()


def init(config: Config = None):
    """初始化数据库，创建所有表。"""
    if config is None:
        config = getGlobalConfig()
    conn = sqlite3.connect(os.path.join(config.indexPath, config.SQLName))
    cur = conn.cursor()
    tables = _MAP.values()
    for t in tables:
        table_name, table_def, _ = t
        cur.execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({table_def})')
    conn.close()


def writeSQLA(*items, no_update: bool = False, config: Config = None, **kwargs):
    """批量写入数据库，自动判断类型。接收来自*2DB的值。其实是for i in items: writeSQL(auto2DB(i))的缩略形式。
    !!来自不同动态、视频、静画的评论分开调用!!

    kwargs:
    main_uid: (仅following)关注者uid。
    coll_name: (仅collection list)合集名称。
    from_id: (可选，仅Comment)评论所在的bid/vid/sid字段。
    from_cid: (可选，仅channel pin dict)所在频道id。
    from_vid: (可选，仅Danmaku)弹幕所在vid。
    file_local: (可选，仅media dict)本地存储路径。
    video_local: (可选，仅video dict)本地存储路径。
    send_request: (可选，仅channel dict)发送请求以保存二进制。
    config: (可选，仅user dict和seiga dict和video dict和channel dict和channel section dict)配置。"""
    if config is None:
        config = getGlobalConfig()
    kwargs.setdefault('config', config)

    for i, data in enumerate(items):
        try:
            writeSQL(auto2DB(data, **kwargs), no_update=no_update, config=config)
        except ValueError:
            t_ = f"item #{i} unrecognized: {type(data)}"
            if isinstance(data, list):
                t_ += f"; first: {type(data[0])} {data[0] if data else ''}"
            else:
                t_ += f"; keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}"
            logger.error(f"[writeSQLA]{_c(_RED, t_, config)}")
