import sqlite3
import os
from ..core.config import Config, getGlobalConfig


# {sql_type: int -> tuple[table_name: str, table_def: str]}
_MAP = {1: ('oh_user', '''uid INTEGER PRIMARY KEY NOT NULL, name TEXT, intro TEXT, create_ts INTEGER,
        sex TEXT, honour TEXT, exp INTEGER, avatar BLOB, cover BLOB, video INTEGER, blog INTEGER,
        seiga INTEGER, media INTEGER, follow INTEGER, fan INTEGER'''),
        2: ('oh_blog', '''bid INTEGER PRIMARY KEY NOT NULL, uid INTEGER, pub_ts INTEGER, arc_ts INTEGER,
        channel INTEGER, like INTEGER, fav INTEGER, view INTEGER, attached_vid INTEGER, copyright_type INTEGER,
        blog_type INTEGER, comment_count INTEGER, title TEXT, content TEXT'''),
        3: ('oh_comment', '''bcid INTEGER PRIMARY KEY NOT NULL, bid INTEGER, uid INTEGER, parent_bcid INTEGER DEFAULT 0,
        timestamp INTEGER, content TEXT, reply_count INTEGER DEFAULT 0''')}


def _loadTable(sql_type: int, config: Config = None) -> tuple[sqlite3.Connection, sqlite3.Cursor]:
    """记得conn.close()"""
    if config is None:
        config = getGlobalConfig()
    conn = sqlite3.connect(os.path.join(config.indexPath, config.SQLName))
    cur = conn.cursor()
    cur.execute(f'CREATE TABLE IF NOT EXISTS {_MAP[sql_type][0]} (_MAP[sql_type][1])')
    return conn, cur


def _writeData(sql_type: int, cur: sqlite3.Cursor, **kw):
    keys = kw.keys()
    cur.execute(
        f"INSERT INTO {_MAP[sql_type][0]} ({', ' .join(keys)}) VALUES ({', '.join('?'*len(keys))})", kw.values()
    )

