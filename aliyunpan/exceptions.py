class AliyunpanException(BaseException):
    def __init__(self, message='', *args):
        super(AliyunpanException, self).__init__(*args)
        self.message = message

    def __str__(self):
        return self.message


class InvalidToken(AliyunpanException):
    """无效的Token"""


class InvalidRefreshToken(InvalidToken):
    """无效的refresh_token"""

    def __str__(self):
        return self.message or 'Is not a valid refresh_token.'


class InvalidAccessToken(InvalidToken):
    """无效的access_token"""

    def __str__(self):
        return self.message or 'Is not a valid access_token.'


class InvalidParentFileId(AliyunpanException):
    """无效的parent_file_id"""

    def __str__(self):
        return self.message or 'parent_file_id is not a valid value.'


class InvalidPassword(AliyunpanException):
    """无效的密码"""


class LoginFailed(AliyunpanException):
    """登录失败"""


class ConfigurationFileError(AliyunpanException, FileNotFoundError):
    """配置文件错误"""


class ConfigurationFileNotFoundError(ConfigurationFileError):
    """找不到配置文件"""


class CreateDirError(AliyunpanException):
    """创建目录错误"""


class InvalidConfiguration(ConfigurationFileError):
    """无效的配置文件"""


class InvalidParameter(AliyunpanException):
    """参数错误"""


class InvalidContentHash(InvalidParameter):
    """Hash不匹配"""


class InvalidExpiration(InvalidParameter):
    """错误的Expiration"""


class RequestExpired(AliyunpanException):
    """请求过期"""


class UploadUrlExpired(RequestExpired):
    """上传链接过期"""


class UploadUrlFailedRefresh(UploadUrlExpired):
    """上传链接刷新失败"""


class BadResponseCode(AliyunpanException):
    """错误的响应代码"""


class InvalidPartNumber(InvalidParameter):
    """分块数量错误"""


class PartNumberOverLimit(InvalidPartNumber):
    """分块上限"""

    def __str__(self):
        return self.message or '\nPart Number must be an integer between 1 and 10000, inclusive.\n' \
                               'Please increase the size of chunk_size.'


class PartNotSequential(AliyunpanException):
    """上传序列错误"""

    def __str__(self):
        return self.message or 'For sequential multipart upload,' \
                               'you must upload or complete parts with sequential part number.'


class FileShareNotAllowed(AliyunpanException):
    """文件无法分享"""


class AliyunpanCode(object):
    existed = 'AlreadyExist.File'
    token_invalid = 'AccessTokenInvalid'
    invalid_content_hash = 'InvalidParameter.ContentHash'
    not_found_file = 'NotFound.File'
    request_expired = 403
    part_already_exist = 409
    part_not_sequential = 400
    Forbidden = 'Forbidden'
    InvalidExpiration = 'InvalidParameter.Expiration'
    FileShareNotAllowed = 'FileShareNotAllowed'
