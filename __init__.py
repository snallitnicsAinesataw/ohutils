from . import arc
from .arc import sql_io as sql
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
from .peripheral import *
from .core._const import *
from .core._const import _version as __version__

# 日志初始化
import logging
if not logging.root.handlers:
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s.%(msecs)03d %(levelname).1s]%(message)s',
        datefmt='%H:%M:%S'
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
