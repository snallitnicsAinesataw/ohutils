from .util import startEnd, _request
from .config import Config, getGlobalConfig
from typing import Callable
from getpass import getpass


@startEnd(is_auth=True)
def login(uid_email: str, password: str, config: Config = None) -> dict:
    """登录。
    useStartEnd此时无效(固定为False)，以防止日志泄露账号密码。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/auth/login/"
    res = _request('post', 'json', 'login', url, config=config, data={'uid_email': uid_email, "pw": password})
    del res['status']
    return res


def loginAndSetToken(uid_email: str, password: str, config: Config = None):
    """登录并更新全局配置的token。"""
    if config is None:
        config = getGlobalConfig()
    config.token = login(uid_email, password, config)['token']


@startEnd
def checkin(config: Config = None) -> bool:
    """签到。需要token。返回if_today_first_login。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/auth/sign-in/"
    res = _request('post', 'json', 'checkin', url, config=config, data={"token": config.token})['if_today_first_login']
    return {'yes': True, 'no': False}[res]


@startEnd(is_auth=True)
def resetPassword(e_mail: str, new_pswd: str, config: Config = None, *, verify_code_: Callable[[None], int] = None):
    """更改密码。
    因为无法获取验证码，所以需要一个函数(verify_code_)来返回验证码。
    默认为getpass('[resetPassword]input verification code: ')。
    此函数会等待verify_code_返回结果再继续。
    useStartEnd此时无效(固定为False)，以防止日志泄露账号密码。"""
    if verify_code_ is None:
        verify_code_ = lambda: getpass('[resetPassword]input verification code: ')
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/auth/password-reset/"

    url2 = f"https://{config.APIBase}api/auth/password-reset/verification-code/"
    _request('post', 'json', 'resetPassword', url2, config=config, data={'email': e_mail})  # 发送验证码

    code = verify_code_()
    data = {"email": e_mail, "passwordreset_verification_code": str(code), "pw": new_pswd, "confirm_pw": new_pswd}
    _request('post', 'json', 'resetPassword', url, config=config, data=data)


@startEnd(is_auth=True)
def register(e_mail: str, pswd: str, config: Config = None, *, verify_code_: Callable[[None], int] = None):
    """注册新OTTOHub账号。
    因为无法获取验证码，所以需要一个函数(verify_code_)来返回验证码。
    默认为getpass('[register]input verification code: ')。
    此函数会等待verify_code_返回结果再继续。
    useStartEnd此时无效(固定为False)，以防止日志泄露账号密码。"""
    if verify_code_ is None:
        verify_code_ = lambda: getpass('[register]input verification code: ')
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/auth/register/"

    url2 = f"https://{config.APIBase}api/auth/register/verification-code/"
    _request('post', 'json', 'register', url2, config=config, data={'email': e_mail})  # 发送验证码

    code = verify_code_()
    data = {"email": e_mail, "register_verification_code": str(code), "pw": pswd, "confirm_pw": pswd}
    return _request('post', 'json', 'register', url, config=config, data=data)

