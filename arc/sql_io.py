import sqlite3
import os
from ..core.config import Config, getGlobalConfig
from ..core.util import parseTime, _request, startEnd


# {sql_type: int -> tuple[table_name: str, table_def: str, prim_key: str]}
_MAP = {1: ('oh_user', '''uid INTEGER PRIMARY KEY NOT NULL, name TEXT, intro TEXT, create_ts INTEGER,
        sex TEXT, honour TEXT, exp INTEGER, avatar BLOB, cover BLOB, video INTEGER, blog INTEGER,
        seiga INTEGER, media INTEGER, follow INTEGER, fan INTEGER''', 'uid'),
        2: ('oh_blog', '''bid INTEGER PRIMARY KEY NOT NULL, uid INTEGER, pub_ts INTEGER, arc_ts INTEGER,
        channel INTEGER, like INTEGER, fav INTEGER, view INTEGER, attached_vid INTEGER, copyright_type INTEGER,
        blog_type INTEGER, comment_count INTEGER, title TEXT, content TEXT''', 'bid'),
        3: ('oh_comment', '''bcid INTEGER PRIMARY KEY NOT NULL, bid INTEGER, uid INTEGER, parent_bcid INTEGER DEFAULT 0,
        timestamp INTEGER, content TEXT, reply_count INTEGER DEFAULT 0''', 'bcid')}


# {api_k: str -> tuple[db_k: str, factory: callable]}
_MAP_USER_TO_DB = {'uid': ('uid', int), 'username': ('name', None), 'intro': ('intro', None),
                   'time': ('create_ts', parseTime), 'sex': ('sex', None),
                   'honour': ('honour', None), 'experience': ('exp', int), 'video_num': ('video', int),
                   'blog_num': ('blog', int), 'seiga_num': ('seiga', int), 'media_num': ('media', int),
                   'followings_count': ('follow', int), 'fans_count': ('fan', int)}


@startEnd
def User2DB(data: dict, send_request: bool = True, config: Config = None) -> dict:
    """映射getUserDetailRaw(...)的字段至oh_user，附处理"""
    if config is None:
        config = getGlobalConfig()
    mapped = {}
    for api_key, db_k_m in _MAP_USER_TO_DB.items():
        if api_key in data:
            if db_k_m[1] is None:
                mapped[db_k_m[0]] = data[api_key]
            else:
                mapped[db_k_m[0]] = db_k_m[1](data[api_key])
    if send_request:
        mapped['avatar'] = _request('get', 'content', 'User2DB', data['avatar_url'], config=config)
        mapped['cover'] = _request('get', 'content', 'User2DB', data['cover_url'], config=config)
    return mapped


def loadTable(sql_type: int, config: Config = None) -> sqlite3.Connection:
    """记得conn.close()"""
    if config is None:
        config = getGlobalConfig()
    conn = sqlite3.connect(os.path.join(config.indexPath, config.SQLName))
    cur = conn.cursor()
    cur.execute(f'CREATE TABLE IF NOT EXISTS {_MAP[sql_type][0]} ({_MAP[sql_type][1]})')
    return conn


def writeData(sql_type: int, conn: sqlite3.Connection, no_update: bool = False, **kw):
    cur = conn.cursor()
    keys = kw.keys()
    if no_update:
        cur.execute(
            f"INSERT OR IGNORE INTO {_MAP[sql_type][0]} ({', '.join(keys)}) VALUES ({', '.join('?'*len(keys))})",
            tuple(kw.values())
        )
    else:
        conflict = f"ON CONFLICT({_MAP[sql_type][2]}) DO UPDATE SET " + \
                   ", ".join([f"{k} = excluded.{k}" for k in keys if k != "uid"])
        cur.execute(
            f"INSERT INTO {_MAP[sql_type][0]} ({', ' .join(keys)}) VALUES ({', '.join('?'*len(keys))}) {conflict}",
            tuple(kw.values())
        )
    conn.commit()


def readData(sql_type: int, conn: sqlite3.Connection, fields: list = None, **kw):
    cur = conn.cursor()
    fields_str = ", ".join(fields) if fields else "*"
    cond = 'WHERE ' if kw.keys() else '' + " AND ".join([f"{k} = ?" for k in kw.keys()])
    query = f"SELECT {fields_str} FROM {_MAP[sql_type][0]} {cond}"
    cur.execute(query, tuple(kw.values()))
    return cur.fetchall()
