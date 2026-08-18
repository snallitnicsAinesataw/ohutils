import random

from .util import _request, startEnd
from .exceptions import OttoBaseException
from .config import Config, getGlobalConfig
from .exceptions import UIDError
import time


@startEnd
def getUserDetailRaw(uid: int, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"{config.APIBase}api/user/{uid}"
    return _request('get', 'json', 'getUserDetailRaw', url, config)


@startEnd
def getUserVideoCollectionsRaw(uid: int, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"{config.APIBase}api/collection/videos/collections?uid={uid}"
    return _request('get', 'json', 'getUserVideoCollectionsRaw', url, config)


@startEnd
def getUserBlogCollectionsRaw(uid: int, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"{config.APIBase}api/collection/blogs/collections?uid={uid}"
    return _request('get', 'json', 'getUserVideoCollectionsRaw', url, config)


@startEnd
def getUserBlogsRaw(uid: int, offset: int = 0, config: Config = None) -> list:
    if config is None:
        config = getGlobalConfig()
    url = f"{config.APIBase}api/blog/users/{uid}/blogs?offset={offset}&num={config.userBlogPerReq}"
    return _request('get', 'json', 'getUserBlogsRaw', url, config).get("blog_list", [])


@startEnd
def getAllUserBlog(uid: int, config: Config = None) -> list:
    if config is None:
        config = getGlobalConfig()
    all_blogs = []
    offset = 0
    while True:
        if offset != 0 and config.verbose:
            print(f"[getAllUserBlog]curr offset: {offset}")
        blog_list = getUserBlogsRaw(uid, offset, config)
        if not blog_list:
            break
        all_blogs.extend(blog_list)
        if len(blog_list) < config.userBlogPerReq:
            break  # 最后一页没满，结束
        offset += config.userBlogPerReq
        time.sleep(random.uniform(*config.blogBatchDelay))  # 限速
    if config.verbose:
        print(f"[getAllUserBlog]get {len(all_blogs)} blog(s) of ou{uid}")
    return all_blogs


def isUserAlive(uid: int, config: Config = None) -> bool:
    try:
        getUserDetailRaw(uid, config)
        return True
    except UIDError:
        return False


def findLatestUser(max_n=10 ** 6, config: Config = None) -> int:
    if config is None:
        config = getGlobalConfig()
    lo, hi = 0, max_n
    while lo < hi:
        mid = (lo + hi) // 2
        if config.verbose:
            print(f"[findLatestUser]try mid={mid}...")
        if isUserAlive(mid, config):
            lo = mid + 1
        else:
            hi = mid
    return lo - 1