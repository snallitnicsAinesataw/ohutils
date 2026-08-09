from .util import startEnd, _postJson
from .config import Config, getGlobalConfig


@startEnd
def loginRaw(uid_email: str, password: str, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = "https://www.ottohub.cn/api/auth/login/"
    return _postJson("loginRaw", url, {'uid_email': uid_email, "pw": password}, config)


def loginAndSetToken(uid_email: str, password: str, config: Config = None):
    if config is None:
        config = getGlobalConfig()
    config.token = loginRaw(uid_email, password,config)['token']


@startEnd
def signinRaw(config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = "https://www.ottohub.cn/api/auth/sign-in/"
    return _postJson("signinRaw", url, {"token": config.token}, config)
