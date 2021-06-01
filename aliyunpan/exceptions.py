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


class InvalidPassword(AliyunpanException):
    """无效的密码"""


class LoginFailed(AliyunpanException):
    """登录失败"""


class ConfigurationFileError(AliyunpanException, FileNotFoundError):
    """配置文件错误"""


class ConfigurationFileNotFoundError(ConfigurationFileError):
    """找不到配置文件"""


class InvalidConfiguration(ConfigurationFileError):
    """无效的配置文件"""


class AliyunpanCode(object):
    existed = 'AlreadyExist.File'
    token_invalid = 'AccessTokenInvalid'
