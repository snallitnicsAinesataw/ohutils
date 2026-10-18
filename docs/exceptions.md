# 1.5 异常类
此文档对应`ohutils.errs.*` 即`core\exception.py`。

不确定这些异常是否都能出现。大部分对着｢`otohub api 1.9.2.txt`｣写的。

[目录](nav.md)

---

## 1.5.1 基类

`class OttoBaseException(Exception)`

库异常基类。直接子异常：

| 类名                       | doc                | 注                                                           |
|--------------------------|--------------------|-------------------------------------------------------------|
| `APIError`               | API响应状态不是`success` | 托底异常，若API返回不在映射内的`message`则抛出                               |
| `MissingArgumentError`   | 缺少参数               | *可能* 由于缺少`token`引起。                                         |
| `InvalidFileFormatError` | 非法文件格式             | 视频格式不是mp4、mov、m4v以及封面格式不是jpg、jpeg、png、gif。由`postDraft()`抛出。 |
| `FileTooBigError`        | 文件太大               | 大于400MB。由`postDraft()`抛出。                                   |
| `FileNotProvidedError`   | 缺少文件               | 缺少视频文件。由`postDraft()`下的`checkDur()`抛出。                      |
| `TooManyRequests`        | 请求频率过高             | 429                                                         |
| `MethodNotAllowed`       | 请求方法不允许            | 405                                                         |
| `ExhaustedRetriesError`  | 耗尽重试次数             | `config.retries`规定的重试次数耗尽                                   |
| `DurationDetectionError` | 在自动检测视频时长时失败       | 由`postDraft()`下的`checkDur()`抛出。                             |


## 1.5.2 API异常❓

`class APIError(OttoBaseException)`

API异常。均来自`_request()`。子异常：

| 类名                               | doc                      | 注                                               |
|----------------------------------|--------------------------|-------------------------------------------------|
| `ServerError`                    | 系统错误 (服务器返回system_error) | 若合集不存在，会在`getBlogCollItems()`内抛出。               |
| `WrongPasswordError`             | 密码错误                     |                                                 |
| `PasswordMismatchError`          | 两次密码不一致                  |                                                 |
| `EmailExistError`                | 邮箱已注册                    |                                                 |
| `VerificationCodeError`          | 验证码错误                    |                                                 |
| `EmailNotFoundError`             | 邮箱不存在                    |                                                 |
| `EmailError`                     | 邮箱错误                     |                                                 |
| `InvalidQQEmailError`            | 不是纯数字QQ邮箱                |                                                 |
| `NumericTypeError`               | 错误的类型数值                  |                                                 |
| `NumberTooBigError`              | 数量太大                     | *可能* 来自配置中的*perReq太大                            |
| `VIDError`                       | 错误的VID                   |                                                 |
| `BIDError`                       | 错误的BID                   | 若动态设置了｢仅频道内可见｣且不在频道内也会抛出                        |
| `UIDError`                       | 错误的UID                   | 不存在或被封                                          |
| `DanmakuIDError`                 | 错误的弹幕ID                  |                                                 |
| `CIDError`                       | 错误的频道ID                  |                                                 |
| `NotReviewerError`               | 不是审核                     |                                                 |
| `InvalidFollowingUIDError`       | 非法的关注对象                  |                                                 |
| `TooManyFollowingsError`         | 关注数大于888人                |                                                 |
| `InvalidTokenError`              | 非法token                  |                                                 |
| `InvalidReceiverError`           | 错误的接受者                   | 指站内信                                            |
| `ContentTooShortError`           | 内容太短                     |                                                 |
| `ContentTooLongError`            | 内容太长                     |                                                 |
| `SensitiveWordError`             | 触发敏感词                    |                                                 |
| `MessageIDError`                 | 错误的消息ID                  |                                                 |
| `NoPermissionError`              | 没有权限                     |                                                 |
| `InvalidParentIDError`           | 非法父评论ID                  |                                                 |
| `InvalidParentError`             | 非法父评论                    | 将子评论作为父评论，即｢楼中楼中楼｣                              |
| `InvalidUsernameError`           | 非法用户名                    |                                                 |
| `UsernameExistError`             | 用户名已存在                   |                                                 |
| `InvalidPhoneError`              | 非法手机号                    |                                                 |
| `InvalidQQError`                 | 非法QQ号                    |                                                 |
| `InvalidSexError`                | 非法性别                     |                                                 |
| `InvalidIntroError`              | 非法简介                     |                                                 |
| `TitleTooShortError`             | 标题太短                     |                                                 |
| `TitleTooLongError`              | 标题太长                     |                                                 |
| `TagTooFewError`                 | 标签太少                     |                                                 |
| `TagTooManyError`                | 标签太多                     |                                                 |
| `InvalidTagError`                | 非法标签                     |                                                 |
| `InvalidCategoryError`           | 非法分区                     |                                                 |
| `InvalidDanmakuError`            | 非法的弹幕参数                  |                                                 |
| `ResourceNotFoundError`          | 资源不存在                    |                                                 |
| `VideoNotFoundError`             | 视频不存在或不属于当前用户            |                                                 |
| `InvalidCoverURLError`           | 封面URL无效                  |                                                 |
| `InvalidVideoURLError`           | 视频URL无效                  |                                                 |
| `InvalidDurationError`           | 视频时长无效                   |                                                 |
| `DraftNotFoundError`             | 草稿不存在                    |                                                 |
| `DraftExistsError`               | 草稿已存在                    |                                                 |
| `IndexConflictError`             | 索引冲突                     | ❓                                               |
| `NotChannelMemberError`          | 不是频道成员                   |                                                 |
| `MissingExtensionParameterError` | 缺少扩展参数                   | ❓                                               |
| `NotInCollectionError`           | 请求的对象不在合集中               |                                                 |
| `APINotFoundError`               | API不存在                   |                                                 |
| `GoreNotAllowedError`            | 不允许请求is_gore=1内容         |                                                 |
| `InvalidModuleError`             | 错误的`?module=...`参数。      | 此错误不应该发生。（旧格式(指`?module=...&action=...`)API遗留物） |
