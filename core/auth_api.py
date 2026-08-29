from .util import startEnd, _request
from .config import Config, getGlobalConfig
from typing import Callable
from getpass import getpass


@startEnd(is_auth=True)
def loginRaw(uid_email: str, password: str, config: Config = None) -> dict:
    """登录。
    noStartEnd此时无效(固定为True)，以防止日志泄露账号密码。"""
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


@startEnd(is_auth=True)
def resetPassword(e_mail: str, new_pswd: str, verify_code_: Callable[[None], int] = None, config: Config = None) -> None:
    """更改密码。
    因为无法获取验证码，所以需要一个函数(verify_code_)来返回验证码。
    默认为getpass('[resetPassword]input verification code: ')。
    此函数会等待verify_code_返回结果再继续。
    noStartEnd此时无效(固定为True)，以防止日志泄露账号密码。"""
    if verify_code_ is None:
        verify_code_ = lambda: getpass('[resetPassword]input verification code: ')
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/auth/password-reset/"

    url = f"https://{config.APIBase}api/auth/password-reset/verification-code/"
    _request('post', 'json', 'sendVerificationCode', url, config, {'email': e_mail})  # 发送验证码

    code = verify_code_()
    data = {"email": e_mail, "passwordreset_verification_code": code, "pw": new_pswd, "confirm_pw": new_pswd}
    _request('post', 'json', 'resetPassword', url, config, data)

