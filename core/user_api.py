import random
from .util import _request, startEnd, _recur_request, BlogEntry, logger
from .exception import OttoBaseException
from .config import Config, getGlobalConfig
from .exception import UIDError
import time


###################################################
# 单页
@startEnd
def _getUserBlogList(uid: int, offset: int, config: Config) -> list:
    """获取指定uid的一组动态列表(不递归)。"""
    url = f"https://{config.APIBase}api/blog/users/{uid}/blogs?offset={offset}&num={config.blogPerReq}"
    return _request('get', 'json', '_getUserBlogList', url, config=config).get("blog_list", [])


@startEnd
def _getFollowersList(uid: int, offset: int, config: Config) -> list[dict]:
    url = f"https://{config.APIBase}api/following/fans/{uid}?offset={offset}&num={config.userPerReq}"
    return _request('get', 'json', '_getFollowersList', url, config=config)['data']['user_list']


@startEnd
def _getFollowingsList(uid: int, offset: int, config: Config) -> list[dict]:
    url = f"https://{config.APIBase}api/following/list/{uid}?offset={offset}&num={config.userPerReq}"
    return _request('get', 'json', '_getFollowersList', url, config=config)['data']['user_list']


@startEnd
def _getFavBlogs(offset: int, config: Config) -> dict:
    """获取一组收藏的动态(不递归)。需要token。"""
    url = f"https://{config.APIBase}api/blog/favorite-list?num={config.managePerReq}&offset={offset}" \
          f"&_t={int(time.time())}&token={config.token}"
    return _request('get', 'json', "_getFavBlogs", url, config=config)


###################################################


@startEnd
def getUserDetail(uid: int, config: Config = None) -> dict:
    """获取指定uid的数据。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/user/{uid}"
    return _request('get', 'json', 'getUserDetail', url, config=config)['data']


@startEnd
def getUserVideoCollections(uid: int, config: Config = None) -> list[str]:
    """获取指定uid的视频合集。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/collection/videos/collections?uid={uid}"
    return _request('get', 'json', 'getUserVideoCollections', url, config=config)['collection_list']


@startEnd
def getUserBlogCollections(uid: int, config: Config = None) -> list[str]:
    """获取指定uid的动态合集。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/collection/blogs/collections?uid={uid}"
    return _request('get', 'json', 'getUserBlogCollections', url, config=config)['collection_list']


@startEnd
def getAllUserBlogs(uid: int, config: Config = None) -> list[dict]:
    """递归获取指定uid的所有动态。"""
    if config is None:
        config = getGlobalConfig()
    all_blogs = _recur_request('getAllUserBlogs',
                               lambda off: (_getUserBlogList(uid, off, config), None),
                               config.blogPerReq, config.pagingDelay, config=config)
    if config.verbose:
        logger.info(f"[getAllUserBlogs]get {len(all_blogs)} blog(s) of ou{uid}")
    return all_blogs


def isUserAlive(uid: int, config: Config = None) -> bool:
    """测试用户状态是否正常。"""
    try:
        getUserDetail(uid, config)
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
            logger.info(f"[findLatestUser]test ou{mid}...")
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
def getAllFollowers(uid: int, config: Config = None) -> list[dict]:
    """递归获取指定uid的所有粉丝。
    使用alwaysUseToken可以获取token对应用户与粉丝之间的关系(follow_status)，否则均为ohutils.STAT_UNKNOWN (-1)."""
    if config is None:
        config = getGlobalConfig()
    all_ = _recur_request('getAllFollowers',
                          lambda off: (_getFollowersList(uid, off, config), None),
                          config.userPerReq, config.pagingDelay, config=config)
    if config.verbose:
        logger.info(f"[getAllFollowers]get {len(all_)} follower(s) of ou{uid}")
    return all_


@startEnd
def getAllFollowings(uid: int, config: Config = None) -> list[dict]:
    """递归获取指定uid的所有关注用户。
    使用alwaysUseToken可以获取token对应用户与关注用户之间的关系(follow_status)，否则均为ohutils.STAT_UNKNOWN (-1)."""
    if config is None:
        config = getGlobalConfig()
    all_ = _recur_request('getAllFollowings',
                          lambda off: (_getFollowingsList(uid, off, config), None),
                          config.userPerReq, config.pagingDelay, config=config)
    if config.verbose:
        logger.info(f"[getAllFollowings]get {len(all_)} following(s) of ou{uid}")
    return all_


@startEnd
def getAllFavBlogs(config: Config = None) -> list[int]:
    """获取所有收藏的动态bid。需要token。"""
    if config is None:
        config = getGlobalConfig()

    def _fetch(offset):
        resp = _getFavBlogs(offset, config)
        inner = resp['data']
        return inner.get('blog_list', []), inner.get('favorite_blog_count')

    all_blogs = _recur_request('getAllFavBlogs', _fetch,
                               config.managePerReq, config.pagingDelay, config=config)
    return [b['bid'] for b in all_blogs]
