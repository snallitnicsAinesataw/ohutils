# 2.2 登录相关API
此文档对应`core\auth_api.py`。

---
## 2.2.1 login()
`login(uid_email: str, password: str, config: Config = None) -> dict`

登录。

 - **参数**: 
   - `uid_email` -> uid或邮箱。
   - `password` -> 密码。
   - *可选* `config` -> Config对象。不提供则使用全局配置或`useConfig(...)`设定的配置。
 - **返回**: `{uid: str, token, avatar_url, cover_url, cover_h_url, cover_v_url, if_today_first_login, email, is_audit, is_admin}`。
 - **注意**: `useStartEnd`**此时无效**(固定为`False`)，以防止日志泄露账号密码。

## 2.2.2 loginAndSetToken()
`loginAndSetToken(uid_email: str, password: str, config: Config = None) -> None`

登录并更新全局配置的`token`。 参数同`login()`。

## 2.2.3 checkin()
`checkin(config: Config = None) -> bool`

签到。
 - **参数**: 
   - *可选* `config` -> Config对象。需要在对象中包含有效`token`。不提供则使用全局配置或`useConfig(...)`设定的配置。
 - **返回**: 布尔值`if_today_first_login`（今日是否已登录）。


## 2.2.4 resetPassword()
`resetPassword(e_mail: str, new_pswd: str, config: Config = None, *, verify_code_ = None) -> None`

更改密码。

 - **参数**: 
   - `e_mail` -> 账号使用的邮箱。
   - `new_pswd` -> 密码。
   - *可选* `config` -> Config对象。不提供则使用全局配置或`useConfig(...)`设定的配置。
   - *可选* `verify_code_: (None) -> int` -> 因为无法获取验证码，所以需要它来返回验证码。默认为`getpass('[resetPassword]input verification code: ')`。
 - **注意**: `useStartEnd`**此时无效**(固定为`False`)，以防止日志泄露账号密码。

## 2.2.5 register()
`register(e_mail: str, pswd: str, config: Config = None, *, verify_code_ = None) -> dict`

注册新账号。

 - **参数**: 
   - `e_mail` -> 邮箱。
   - `pswd` -> 密码。
   - *可选* `config` -> Config对象。不提供则使用全局配置或`useConfig(...)`设定的配置。
   - *可选* `verify_code_: (None) -> int` -> 因为无法获取验证码，所以需要它来返回验证码。默认为`getpass('[register]input verification code: ')`。**若需覆盖**，确保函数返回`int`类型，且不需要传参。
 - **返回格式未确认**。
 - **注意**: `useStartEnd`**此时无效**(固定为`False`)，以防止日志泄露账号密码。
