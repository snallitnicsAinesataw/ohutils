from . import arc
from .arc import sql_io
from .core import *
from .core.util import (
    Comment, BlogEntry, Danmaku, VideoEntry,
    parseTime, formatTime,
    startEnd,
    genKey, encrypt, decrypt,
    dict2BlogComment, getVersion,
    flattenComments,
    mergeBlogEntry,
    appSim, useConfig,
)
from .core.config import Config, setGlobalConfig, getGlobalConfig

__version__ = "0.7.0"
F_ENCRYPT_CONTENT = 1
F_GORE = 2
F_HAS_FORWARD = 4
CT_ALL = 'all'
CT_BLOG = 'blog'
CT_VIDEO = 'video'
SORT_CREATED = "created_at"
SORT_VIEWS = "view_count"
SORT_LIKES = "like_count"
LIMIT_DAY = 1
LIMIT_WEEK = 7
LIMIT_MONTH = 30
LIMIT_QUARTER = 90
VCT_REPOST = 1
VCT_ORIGINAL = 2
VT_OTHER = 0
VT_KICHIKU = 1
VT_HUMAN_VOCALOID = 3
VT_SHOWCASE = 4  # "剧场"
VT_GAMES = 5
VT_NOSTALGIA = 6
VT_MUSIC = 7
DEFAULT_TS = 946656000
SG_DAILY = 'daily'
SG_WEEKLY = 'weekly'
SG_MONTHLY = 'monthly'
SG_ALL = 'total'
STAT_UNKNOWN = -1
STAT_SELF = 0
STAT_UNFOLLOWED = 1  # 未关注
STAT_FOLLOWING = 2  # 关注了对方
STAT_FOLLOWED = 3  # 被对方关注
STAT_MUTUAL = 4  # 互关
