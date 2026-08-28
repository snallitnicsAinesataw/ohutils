import sqlite3
import os
from typing import Union
from time import time
from ..core.config import Config, getGlobalConfig
from ..core.util import parseTime, _request, startEnd, BlogEntry, flattenComments, Comment, VideoEntry
from dataclasses import asdict


def _tag_factory(tags: list[str]) -> str:
    tags.remove('吉吉国民')
    return ','.join(tags)


# {sql_type: int -> tuple[table_name: str, table_def: str, prim_key: str]}
_MAP = {1: ('oh_user_v1', '''uid INTEGER PRIMARY KEY NOT NULL, name TEXT, intro TEXT, create_ts INTEGER,
        sex TEXT, honour TEXT, exp INTEGER, avatar BLOB, cover_h BLOB, cover_v BLOB, video INTEGER, blog INTEGER,
        seiga INTEGER, media INTEGER, follow INTEGER, fan INTEGER, avatar_url TEXT, cover_h_url TEXT, cover_v_url TEXT,
        CHECK (((avatar IS NULL AND avatar_url IS NOT NULL) OR (avatar IS NOT NULL AND avatar_url IS NULL)) AND 
        ((cover_h IS NULL AND cover_h_url IS NOT NULL) OR (cover_h IS NOT NULL AND cover_h_url IS NULL)) AND 
        ((cover_v IS NULL AND cover_v_url IS NOT NULL) OR (cover_v IS NOT NULL AND cover_v_url IS NULL)))''', 'uid'),
        2: ('oh_blog_v1', '''bid INTEGER PRIMARY KEY NOT NULL, uid INTEGER, pub_ts INTEGER, arc_ts INTEGER,
        channel INTEGER, like INTEGER, fav INTEGER, view INTEGER, attached_vid INTEGER, copyright_type INTEGER,
        blog_type INTEGER, comment_count INTEGER, title TEXT, content TEXT, tags TEXT, gore INTEGER''', 'bid'),
        5: ('oh_obc_v1', '''bcid INTEGER PRIMARY KEY NOT NULL, bid INTEGER, uid INTEGER, parent_bcid INTEGER DEFAULT 0,
        pub_ts INTEGER, content TEXT, reply_count INTEGER DEFAULT 0, pin_order INTEGER DEFAULT 0''', 'bcid'),
        6: ('oh_ovc_v1', '''vcid INTEGER PRIMARY KEY NOT NULL, vid INTEGER, uid INTEGER, parent_vcid INTEGER DEFAULT 0,
        pub_ts INTEGER, content TEXT, reply_count INTEGER DEFAULT 0, pin_order INTEGER DEFAULT 0''', 'vcid'),
        7: ('oh_osc_v1', '''scid INTEGER PRIMARY KEY NOT NULL, sid INTEGER, uid INTEGER, parent_scid INTEGER DEFAULT 0, 
        pub_ts INTEGER, content TEXT, reply_count INTEGER DEFAULT 0, pin_order INTEGER DEFAULT 0''', 'scid'),
        9: ('oh_follow_v1', 'uid INTEGER, target_uid INTEGER, PRIMARY KEY (uid, target_uid)', '(uid, target_uid)'),
        10: ('oh_blog_collection_v1', '''bid INTEGER NOT NULL, uid INTEGER, name TEXT NOT NULL, order INTEGER, 
        PRIMARY KEY (name, bid)''', '(name, bid)'),
        11: ('oh_video_collection_v1', '''vid INTEGER NOT NULL, uid INTEGER, name TEXT NOT NULL, order INTEGER, 
        PRIMARY KEY (name, vid)''', '(name, vid)'),
        12: ('oh_seiga_collection_v1', '''sid INTEGER NOT NULL, uid INTEGER, name TEXT NOT NULL, order INTEGER, 
        PRIMARY KEY (name, sid)''', '(name, sid)'),
        13: ('oh_seiga_v1', '''sid INTEGER PRIMARY KEY NOT NULL, uid INTEGER, title TEXT, desc TEXT, pages INTEGER, 
        is_doujin INTEGER DEFAULT 0, is_ai INTEGER DEFAULT 0, is_gore INTEGER DEFAULT 0, hall TEXT, 
        pub_ts INTEGER DEFAULT 946656000, fav INTEGER, view INTEGER, comment_count INTEGER''', 'sid'),
        14: ('oh_seiga_tag_v1', 'tid INTEGER PRIMARY KEY NOT NULL, name TEXT NOT NULL', 'tid'),
        15: ('oh_seiga_tagmap_v1', '''sid INTEGER NOT NULL, tid INTEGER NOT NULL, is_locked INTEGER DEFAULT 0, 
        lock_sort INTEGER DEFAULT 0, added_by INTEGER, PRIMARY KEY (sid, tid)''', '(sid, tid)'),
        16: ('oh_seiga_page_v1', '''sid INTEGER PRIMARY KEY NOT NULL, page_no INTEGER, asset_id INTEGER, original BLOB, 
        original_url TEXT, width INTEGER, height INTEGER, is_animated INTEGER DEFAULT 0, CHECK 
        ((original IS NULL AND original_url IS NOT NULL) OR (original IS NOT NULL AND original_url IS NULL))''', 'sid')
        }
##########################################################################################
# {api_k: str -> tuple[db_k: str, factory: callable]}
_MAP_USER = {'uid': ('uid', int), 'username': ('name', None), 'intro': ('intro', None),
             'time': ('create_ts', parseTime), 'sex': ('sex', None),
             'honour': ('honour', None), 'experience': ('exp', int), 'video_num': ('video', int),
             'blog_num': ('blog', int), 'seiga_num': ('seiga', int), 'media_num': ('media', int),
             'followings_count': ('follow', int), 'fans_count': ('fan', int)}
_MAP_BLOG = {'bid': ('bid', int), 'uid': ('uid', int), 'time': ('pub_ts', parseTime), 'like_count': ('like', int),
             'favorite_count': ('fav', int), 'view_count': ('view', int), 'attached_vid': ('attached_vid', int),
             'copyright_type': ('copyright_type', int), 'blog_type': ('blog_type', int),
             'comment_count': ('comment_count', int), 'title': ('title', None), 'content': ('content', None),
             'is_gore': ('gore', int), 'tag': ('tags', _tag_factory), 'channel_id': ('channel', int)}
# _MAP_OBC_API特殊处理bid, API不返回。
_MAP_OBC_API = {'bcid': ('bcid', int), 'uid': ('uid', int), 'parent_bcid': ('parent_bcid', int),
                'time': ('pub_ts', parseTime), 'content': ('content', None), 'child_comment_num': ('reply_count', int),
                'pin_order': ('pin_order', int)}
_MAP_BLOG_ENTRY = {'bid': ('bid', int), 'uid': ('uid', int), 'timestamp': ('pub_ts', None), 'like_count': ('like', int),
                   'favorite_count': ('fav', int), 'view_count': ('view', int), 'attached_vid': ('attached_vid', int),
                   'copyright_type': ('copyright_type', int), 'blog_type': ('blog_type', int),
                   'title': ('title', None), 'content': ('content', None), 'tags': ('tags', lambda x: ','.join(x)),
                   'arc_time': ('arc_ts', None), 'channel_id': ('channel', None), 'is_gore': ('gore', int)}
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
_MAP_SEIGA_API = {'sid': ('sid', int), 'uid': ('uid', int), 'title': ('title', None), 'description': ('desc', None),
                  'page_count': ('pages', int), 'is_fanwork': ('is_doujin', int), 'hall_at': ('hall', None),
                  'is_ai': ('is_ai', int), 'is_gore': ('is_gore', int), 'time': ('pub_ts', parseTime),
                  'favorite_count': ('fav', int), 'view_count': ('view', int), 'comment_count': ('comment_count', int)}
#########################################################################################
# map_type: int -> map: dict
# sql_type集合是map_type集合的真子集。
_META_MAP = {1: _MAP_USER, 2: _MAP_BLOG, 3: _MAP_OBC_API, 4: _MAP_BLOG_ENTRY, 5: _MAP_OBC, 6: _MAP_OVC, 7: _MAP_OSC,
             8: _MAP_OSC_API, 13: _MAP_SEIGA_API}


#########################################################################################


def _process(data: dict, sql_type: int):
    mapped = {}
    for api_key, (db_key, factory) in _META_MAP[sql_type].items():
        if api_key in data:
            if factory is None:
                mapped[db_key] = data[api_key]
            else:
                mapped[db_key] = factory(data[api_key])
    return mapped


@startEnd
def user2DB(data: dict, send_request: bool = True, config: Config = None) -> dict:
    """映射getUserDetailRaw(...)的字段至oh_user，附处理。
    send_request: 是否发送请求以获取用户头像和封面，默认为True。"""
    if config is None:
        config = getGlobalConfig()
    mapped = _process(data, 1)  # 1: USER
    mapped['arc_ts'] = int(time())  # 使用当前时间代替
    if send_request:
        mapped['avatar'] = _request('get', 'content', 'user2DB', data['avatar_url'], config=config)
        mapped['cover_h'] = _request('get', 'content', 'user2DB', data['cover_h_url'], config=config)
        mapped['cover_v'] = _request('get', 'content', 'user2DB', data['cover_v_url'], config=config)
    else:
        mapped['avatar_url'] = mapped['avatar_url']
        mapped['cover_h_url'], mapped['cover_v_url'] = data['cover_h_url'], data['cover_v_url']
    return mapped


def blog2DB(data: Union[dict, BlogEntry]) -> dict:
    """映射getBlogRaw(...)和BlogEntry的字段至oh_blog。"""
    if isinstance(data, BlogEntry):
        data = data.toDictShallow()
        mapped = _process(data, 4)  # 4: BLOG_ENTRY
        mapped['comment_count'] = len(flattenComments(data['comments']))
    else:
        mapped = _process(data, 2)  # 2: BLOG
        mapped['arc_ts'] = int(time())  # 使用当前时间代替
    return mapped


def commentRaw2DB(data: list[dict], from_id: int = 0) -> list[dict]:
    """映射get*CommentListRaw(...)的字段至对应的数据表。会自动判断评论类型。
    提供from_id: int以向表中存储评论所在的bid/sid字段。"""
    res = []
    if data.get("bcid"):
        # blog
        for b in data:
            mapped = _process(b, 3)  # 3: OBC_API
            if from_id:
                mapped['bid'] = from_id
            res.append(mapped)
    elif data.get("scid"):
        # seiga
        for b in data:
            mapped = _process(b, 8)  # 8: OSC_API
            if from_id:
                mapped['sid'] = from_id
            res.append(mapped)
    return res


def comment2DB(data: Comment[Union[BlogEntry, VideoEntry]], from_id: int = 0):
    """映射getAll*Comments(...)和Comment的字段至对应的数据表。
    提供from_id: int以向表中存储评论所在的bid/vid/sid字段。"""
    if data.c_type == 'blog':
        d = asdict(data)
        mapped = _process(d, 5)  # 5: OBC
        if from_id:
            mapped['bid'] = from_id
    elif data.c_type == 'video':
        d = asdict(data)
        mapped = _process(d, 6)  # 6: OVC
        if from_id:
            mapped['vid'] = from_id
    elif data.c_type == 'seiga':
        d = asdict(data)
        mapped = _process(d, 7)  # 7: OSC
        if from_id:
            mapped['sid'] = from_id
    else:
        raise ValueError(f'不支持的Comment.c_type类型: {data.c_type}')
    return mapped


def following2DB(main_uid: int, data: list[dict]) -> list[tuple[int, int]]:
    """映射关注的用户信息至数据表。需要提供main_uid (关注者uid)。返回[(uid, target_uid), ...]。
    data可以从ohutils.user_api.getAllFollowings(main_uid)获取。"""
    result = []
    for relation in data:
        result.append((main_uid, relation['uid']))
    return result


def seiga2DB(data: dict, send_request: bool = False, config: Config = None) -> tuple[dict, list[dict], list[dict], list[dict]]:
    """映射getSeigaDetailRaw(...)的字段至数据表。
    send_request: 是否发送请求以获取原始静画，默认为False(仅存储URL)。
    返回[oh_seiga_v1, oh_seiga_tag_v1, oh_seiga_tagmap_v1, oh_seiga_page_v1]。"""
    sid = int(data['sid'])
    mapped = _process(data, 13)  # 13: SEIGA_API
    tag_dicts, tagmap_dicts, page_dicts = [], [], []
    for t in data['tags']:
        tid = int(t['tag_id'])
        tag_dicts.append({'tid': tid, 'name': t['tag_name']})
        tagmap_dicts.append({'sid': sid, 'tid': tid, 'is_locked': t['is_locked'],
                             'lock_sort': t['lock_sort'], 'added_by': int(t['added_by_uid'])})
    for p in data['pages']:
        p_dict = {'sid': sid, 'page_no': int(p['page_no']), 'asset_id': int(p['image_asset_id']),
                  'width': int(p['width']), 'height': int(p['height']), 'is_animated': p['is_animated']}
        if send_request:
            p_dict['original'] = _request('get', 'content', 'seiga2DB', data['original_url'], config=config)
        else:
            p_dict['original_url'] = p['original_url']
        page_dicts.append(p_dict)
    return mapped, tag_dicts, tagmap_dicts, page_dicts


def loadTable(sql_type: int, config: Config = None) -> sqlite3.Connection:
    """记得conn.close()"""
    if config is None:
        config = getGlobalConfig()
    conn = sqlite3.connect(os.path.join(config.indexPath, config.SQLName))
    cur = conn.cursor()
    table_name, table_def, _ = _MAP[sql_type]
    cur.execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({table_def})')
    return conn


def writeData(sql_type: int, conn: sqlite3.Connection, no_update: bool = False, **kw):
    cur = conn.cursor()
    keys = kw.keys()
    table_name, _, prim_key = _MAP[sql_type]
    if no_update:
        cur.execute(
            f"INSERT OR IGNORE INTO {table_name} ({', '.join(keys)}) VALUES ({', '.join('?' * len(keys))})",
            tuple(kw.values())
        )
    else:
        conflict = f"ON CONFLICT({prim_key}) DO UPDATE SET " + \
                   ", ".join([f"{k} = excluded.{k}" for k in keys if k != prim_key])
        cur.execute(
            f"INSERT INTO {table_name} ({', '.join(keys)}) VALUES ({', '.join('?' * len(keys))}) {conflict}",
            tuple(kw.values())
        )
    conn.commit()


def readData(sql_type: int, conn: sqlite3.Connection, fields: list = None, **kwargs) -> list:
    """从指定数据库读取选择的字段(fields)，带条件。
    条件的比较运算符: 若无后缀，为等于(=)。
    若有__gt / __lt / __ge / __le / __ne 后缀，
    则分别为大于(>)，小于(<)，大于等于(>=)，小于等于(<=)，不等于(!=)。

    e.g.:
    view__le=132 -> view <= 132
    exp__gt=100 -> exp > 100
    fav=15 -> fav = 15
    """
    cur = conn.cursor()
    fields_str = ", ".join(fields) if fields else "*"
    kv = []
    for k in kwargs.keys():
        k_list = k.split('__', maxsplit=1)
        if len(k_list) == 1:
            kv.append(k + '=?')  # 无后缀
        else:
            kv.append(k_list[0] + {'lt': '<', 'gt': '>', 'le': '<=', 'ge': '>=', 'ne': '!='}[k_list[1]] + '?')
    cond = 'WHERE ' if kwargs.keys() else '' + " AND ".join(...)
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
