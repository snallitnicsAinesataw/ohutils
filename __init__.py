from . import arc
from .core import *
from .core.util import (
    Comment, BlogEntry, Danmaku, VideoEntry,
    parseTime, formatTime,
    startEnd,
    genKey, encrypt, decrypt,
    dict2Comment, getVersion,
    flattenComments,
    mergeBlogEntry,
    appSim,
)
from .core.config import Config, setGlobalConfig, getGlobalConfig

ver = "0.5"
F_ENCRYPT = 1
F_GORE = 2
CT_ALL = 'all'
CT_BLOG = 'blog'
CT_VIDEO = 'video'
SORT_CREATED = "created_at"
SORT_VIEWS = "view_count"
SORT_LIKES = "like_count"
LIMIT_WEEK = 7
LIMIT_MONTH = 30
LIMIT_QUARTER = 90
VT_REPOST = 1
VT_ORIGINAL = 2
VT_OTHER = 0
VT_GICHIKU = 1
VT_VOCALOID = 3
VT_SHOWCASE = 4 # "剧场"
VT_GAME = 5
VT_NOSTALGIA = 6
VT_MUSIC = 7
DEFAULT_TS = 946656000
SG_DAILY = 'daily'
SG_WEEKLY = 'weekly'
SG_MONTHLY = 'monthly'
SG_ALL = 'total'
