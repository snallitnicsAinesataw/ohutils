import random
from .util import _request, startEnd, _recur_request, BlogEntry
from .exception import OttoBaseException
from .config import Config, getGlobalConfig
from .exception import UIDError
import time


@startEnd
def getUserDetailRaw(uid: int, config: Config = None) -> dict:
    """获取指定uid的数据。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/user/{uid}"
    return _request('get', 'json', 'getUserDetailRaw', url, config)


@startEnd
def getUserVideoCollectionsRaw(uid: int, config: Config = None) -> dict:
    """获取指定uid的视频合集。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/collection/videos/collections?uid={uid}"
    return _request('get', 'json', 'getUserVideoCollectionsRaw', url, config)


@startEnd
def getUserBlogCollectionsRaw(uid: int, config: Config = None) -> dict:
    """获取指定uid的动态合集。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/collection/blogs/collections?uid={uid}"
    return _request('get', 'json', 'getUserBlogCollectionsRaw', url, config)


@startEnd
def getUserBlogsRaw(uid: int, offset: int = 0, config: Config = None) -> list:
    """获取指定uid的一组动态列表(不递归)。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/blog/users/{uid}/blogs?offset={offset}&num={config.userBlogPerReq}"
    return _request('get', 'json', 'getUserBlogsRaw', url, config).get("blog_list", [])


@startEnd
def getAllUserBlog(uid: int, config: Config = None) -> list[dict]:
    """递归获取指定uid的所有动态。"""
    if config is None:
        config = getGlobalConfig()
    all_blogs = _recur_request('getAllUserBlog',
                               lambda off: getUserBlogsRaw(uid, off, config),
                               config.userBlogPerReq, config.blogBatchDelay, config)
    if config.verbose:
        print(f"[getAllUserBlog]get {len(all_blogs)} blog(s) of ou{uid}")
    return all_blogs


def isUserAlive(uid: int, config: Config = None) -> bool:
    """测试用户状态是否正常。"""
    try:
        getUserDetailRaw(uid, config)
        return True
    except UIDError:
        return False


def findLatestUser(max_n: int = 10 ** 6, config: Config = None) -> int:
    """通过二分法寻找最后注册的uid。max_n为二分上界。"""
    died = [122, 343, 891, 1947, 5365, 5862, 6361, 6496, 6760, 7856, 8664, 8958, 9733, 10414, 10417, 12801, 13488,
            15689, 17152, 19215, 19325, 20081, 20260, 22522, 23188, 23596]  # 数据来自28Ciry(ob53116)
    if config is None:
        config = getGlobalConfig()
    lo, hi = 0, max_n
    while lo < hi:
        mid = (lo + hi) // 2
        if config.verbose:
            print(f"[findLatestUser]test ou{mid}...")
        if isUserAlive(mid, config) or mid in died:
            lo = mid + 1
        else:
            hi = mid
    return lo - 1


@startEnd
def isAudit(config: Config = None) -> bool:
    """测试config.token对应用户是否为审核。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/profile/is-audit?token={config.token}"
    return bool(_request('get', 'json', 'isAudit', url, config=config)['data']['is_audit'])


@startEnd
def getFollowersRaw(uid: int, offset: int = 0, config: Config = None) -> dict:
    """获取指定uid的一组粉丝(不递归)。
    使用alwaysUseToken可以获取token对应用户与粉丝之间的关系(follow_status)，否则均为ohutils.STAT_UNKNOWN (-1)."""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/following/fans/{uid}?offset={offset}&num={config.userPerReq}"
    return _request('get', 'json', 'getFollowersRaw', url, config=config)


@startEnd
def getAllFollowers(uid: int, config: Config = None) -> list[dict]:
    """递归获取指定uid的所有粉丝。
    使用alwaysUseToken可以获取token对应用户与粉丝之间的关系(follow_status)，否则均为ohutils.STAT_UNKNOWN (-1)."""
    if config is None:
        config = getGlobalConfig()
    all_ = _recur_request('getAllFollowers',
                          lambda off: getFollowersRaw(uid, off, config)['data']['user_list'],
                          config.userPerReq, config.userBatchDelay, config)
    if config.verbose:
        print(f"[getAllFollowers]get {len(all_)} follower(s) of ou{uid}")
    return all_


@startEnd
def getFollowingsRaw(uid: int, offset: int = 0, config: Config = None) -> dict:
    """获取指定uid的一组关注用户(不递归)。
    使用alwaysUseToken可以获取token对应用户与关注用户之间的关系(follow_status)，否则均为ohutils.STAT_UNKNOWN (-1)."""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/following/list/{uid}?offset={offset}&num={config.userPerReq}"
    return _request('get', 'json', 'getFollowersRaw', url, config=config)


@startEnd
def getAllFollowings(uid: int, config: Config = None) -> list[dict]:
    """递归获取指定uid的所有关注用户。
    使用alwaysUseToken可以获取token对应用户与关注用户之间的关系(follow_status)，否则均为ohutils.STAT_UNKNOWN (-1)."""
    if config is None:
        config = getGlobalConfig()
    all_ = _recur_request('getAllFollowings',
                          lambda off: getFollowersRaw(uid, off, config)['data']['user_list'],
                          config.userPerReq, config.userBatchDelay, config)
    if config.verbose:
        print(f"[getAllFollowings]get {len(all_)} following(s) of ou{uid}")
    return all_
