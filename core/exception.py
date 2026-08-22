class OttoBaseException(Exception):
    """异常基类"""
    pass


class APIError(OttoBaseException):
    """API响应状态不是success"""
    pass


class ServerError(OttoBaseException):
    """系统错误 (服务器返回system_error)"""
    pass


class MissingArgumentError(OttoBaseException):
    """缺少参数"""
    pass


class WrongPasswordError(OttoBaseException):
    """密码错误"""
    pass


class PasswordMismatchError(OttoBaseException):
    """两次密码不一致"""
    pass


class EmailExistError(OttoBaseException):
    """邮箱已存在"""
    pass


class VerificationCodeError(OttoBaseException):
    """验证码错误"""
    pass


class EmailNotFoundError(OttoBaseException):
    """邮箱不存在"""
    pass


class EmailError(OttoBaseException):
    """邮箱错误"""
    pass


class InvalidQQEmailError(OttoBaseException):
    """不是纯数字QQ邮箱"""
    pass


class NumericTypeError(OttoBaseException):
    """错误的类型数值"""
    pass


class NumberTooBigError(OttoBaseException):
    """数量太大"""
    pass


class VIDError(OttoBaseException):
    """错误的VID"""
    pass


class BIDError(OttoBaseException):
    """错误的BID"""
    pass


class UIDError(OttoBaseException):
    """错误的UID"""
    pass


class DanmakuIDError(OttoBaseException):
    """错误的弹幕ID"""
    pass


class CIDError(OttoBaseException):
    """错误的频道ID"""
    pass


class NotReviewerError(OttoBaseException):
    """不是审核"""
    pass


class InvalidFollowingUIDError(OttoBaseException):
    """非法的关注对象"""
    pass


class TooManyFollowingsError(OttoBaseException):
    """关注数大于888人"""
    pass


class InvalidTokenError(OttoBaseException):
    """非法token"""
    pass


class InvalidReceiverError(OttoBaseException):
    """错误的接受者"""
    pass


class ContentTooShortError(OttoBaseException):
    """内容太短"""
    pass


class ContentTooLongError(OttoBaseException):
    """内容太长"""
    pass


class SensitiveWordError(OttoBaseException):
    """触发敏感词 (=warn)"""
    pass


class MessageIDError(OttoBaseException):
    """错误的消息ID"""
    pass


class NoPermissionError(OttoBaseException):
    """没有权限"""
    pass


class InvalidParentIDError(OttoBaseException):
    """非法父评论ID"""
    pass


class InvalidParentError(OttoBaseException):
    """非法父评论（将子评论作为父评论）"""
    pass


class InvalidUsernameError(OttoBaseException):
    """非法用户名"""
    pass


class UsernameExistError(OttoBaseException):
    """用户名已存在"""
    pass


class InvalidPhoneError(OttoBaseException):
    """非法手机号"""
    pass


class InvalidQQError(OttoBaseException):
    """非法QQ号"""
    pass


class InvalidSexError(OttoBaseException):
    """非法性别"""
    pass


class InvalidIntroError(OttoBaseException):
    """非法简介"""
    pass


class TitleTooShortError(OttoBaseException):
    """标题太短"""
    pass


class TitleTooLongError(OttoBaseException):
    """标题太长"""
    pass


class TagTooFewError(OttoBaseException):
    """标签太少"""
    pass


class TagTooManyError(OttoBaseException):
    """标签太多"""
    pass


class InvalidTagError(OttoBaseException):
    """非法标签"""
    pass


class InvalidCategoryError(OttoBaseException):
    """非法分区"""
    pass


class InvalidFileFormatError(OttoBaseException):
    """非法文件格式"""
    pass


class FileTooBigError(OttoBaseException):
    """文件太大"""
    pass


class FileNotProvidedError(OttoBaseException):
    """缺少文件"""
    pass


class InvalidDanmakuError(OttoBaseException):
    """非法的弹幕参数"""
    pass


class ResourceNotFoundError(OttoBaseException):
    """资源不存在"""
    pass


class TooManyRequests(OttoBaseException):
    """请求频率过高(429)"""
    pass


class MethodNotAllowed(OttoBaseException):
    """请求方法不允许(405)"""
    pass


class VideoNotFoundError(OttoBaseException):
    """视频不存在或不属于当前用户"""
    pass


class InvalidCoverURLError(OttoBaseException):
    """封面URL无效"""
    pass


class InvalidVideoURLError(OttoBaseException):
    """视频URL无效"""
    pass


class InvalidDurationError(OttoBaseException):
    """视频时长无效"""
    pass


class DraftNotFoundError(OttoBaseException):
    """草稿不存在"""
    pass


class DraftExistsError(OttoBaseException):
    """草稿已存在"""
    pass


class IndexConflictError(OttoBaseException):
    """索引冲突"""
    pass


class NotChannelMemberError(OttoBaseException):
    """不是频道成员"""
    pass


class MissingExtensionParameterError(OttoBaseException):
    """缺少扩展参数"""
    pass


class ExhaustedRetriesError(OttoBaseException):
    """耗尽重试次数"""
    pass


class NotInCollectionError(OttoBaseException):
    """请求的对象不在合集中"""
    pass


mappings = {
    'missing_argument': MissingArgumentError,
    'system_error': ServerError,
    'error_password': WrongPasswordError, 'error_pw': WrongPasswordError,
    'mismatch_pw': PasswordMismatchError,
    'email_exist': EmailExistError,
    'error_verification_code': VerificationCodeError,
    'email_unexist': EmailNotFoundError,
    'error_email': EmailError,
    'error_qq_email': InvalidQQEmailError,
    'error_type': NumericTypeError,
    'too_big_num': NumberTooBigError,
    'error_vid': VIDError,
    'error_token': InvalidTokenError, 'Token required': InvalidTokenError,
    'not_reviewer': NotReviewerError,
    'error_bid': BIDError,
    'error_following_uid': InvalidFollowingUIDError,
    'too_many_followings': TooManyFollowingsError,
    'error_receiver': InvalidReceiverError,
    'too_short_message': ContentTooShortError, 'content_too_short': ContentTooShortError,
    'intro_too_short': ContentTooShortError, 'text_too_short': ContentTooShortError,
    'too_long_message': ContentTooLongError, 'content_too_long': ContentTooLongError,
    'intro_too_long': ContentTooLongError, 'text_too_long': ContentTooLongError,
    'warn': SensitiveWordError,
    'error_msg_id': MessageIDError,
    'no_permission': NoPermissionError,
    'error_parent_bcid': InvalidParentIDError, 'error_parent_vcid': InvalidParentIDError,
    'error_parent': InvalidParentError,
    'error_username': InvalidUsernameError,
    'username_exist': UsernameExistError,
    'error_phone': InvalidPhoneError,
    'error_qq': InvalidQQError,
    'error_sex': InvalidSexError,
    'error_intro': InvalidIntroError,
    'error_uid': UIDError,
    'title_too_long': TitleTooLongError,
    'title_too_short': TitleTooShortError,
    'tag_too_few': TagTooFewError,
    'tag_too_many': TagTooManyError,
    'error_category': InvalidCategoryError,
    'error_tag': InvalidTagError,
    'error_file': InvalidFileFormatError, 'invalid_file_extension': InvalidFileFormatError,
    'too_big_file': FileTooBigError,
    'file_not_found': FileNotProvidedError,
    'missing_argument_token': MissingArgumentError, 'missing_argument_title': MissingArgumentError,
    'missing_argument_intro': MissingArgumentError, 'missing_argument_type': MissingArgumentError,
    'missing_argument_category': MissingArgumentError, 'missing_argument_tag': MissingArgumentError,
    'missing_argument_file_mp4': MissingArgumentError, 'missing_argument_file_jpg': MissingArgumentError,
    'error_time': InvalidDanmakuError, 'render_too_long': InvalidDanmakuError,
    'error_font_size': InvalidDanmakuError, 'error_color': InvalidDanmakuError, 'error_mode': InvalidDanmakuError,
    'error_danmaku_id': DanmakuIDError,
    'too_many_requests': TooManyRequests,
    'resource_not_found': ResourceNotFoundError,
    'method not allowed': MethodNotAllowed,
    'channel_not_found': CIDError,
    'video_not_found_or_not_owned': VideoNotFoundError,
    'error_cover_url': InvalidCoverURLError,
    'error_video_url': InvalidVideoURLError,
    'error_duration': InvalidDurationError,
    'draft_not_found': DraftNotFoundError,
    'draft_exists': DraftExistsError,
    'index_conflict': IndexConflictError,
    'not_channel_member': NotChannelMemberError,
    'Missing_extension_parameter': MissingExtensionParameterError,
    'seiga_not_in_collection': NotInCollectionError, 'blog_not_in_collection': NotInCollectionError,
    'video_not_in_collection': NotInCollectionError,
}