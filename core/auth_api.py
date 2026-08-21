from .util import startEnd, _request
from .config import Config, getGlobalConfig


@startEnd
def loginRaw(uid_email: str, password: str, config: Config = None) -> dict:
    """登录。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/auth/login/"
    return _request('post', 'json', 'loginRaw', url, config, {'uid_email': uid_email, "pw": password})


def loginAndSetToken(uid_email: str, password: str, config: Config = None):
    """登录并更新全局配置的token。"""
    if config is None:
        config = getGlobalConfig()
    config.token = loginRaw(uid_email, password, config)['token']


@startEnd
def checkinRaw(config: Config = None) -> dict:
    """签到。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/auth/sign-in/"
    return _request('post', 'json', 'signinRaw', url, config, {"token": config.token})
