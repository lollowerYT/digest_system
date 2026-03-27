from fastapi import HTTPException, status


class DigestSystemException(HTTPException):
    status_code = 500
    detail = ""
    
    def __init__(self):
        super().__init__(status_code=self.status_code, detail=self.detail)


class InvalidTelegramAuthorizationException(DigestSystemException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Invalid Telegram authorization"

class AuthorizationExpiredException(DigestSystemException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Authorization expired"

class InvalidTokenException(DigestSystemException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Invalid token"

class UserNotFoundException(DigestSystemException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "User not found"

class UserNotAuthenticatedException(DigestSystemException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "User not authenticated"

class NotAdminException(DigestSystemException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "You don't have enough rights to visit this resource"

class SubscriptionNotExistsException(DigestSystemException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "You don't have any subsription. Contact the administrator or the developer"

class NegativeTokensAmountException(DigestSystemException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Tokens can't be negative"

class DigestNotExistsException(DigestSystemException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Digest doesn't exist"

class DigestAlreadyExistsException(DigestSystemException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Digest already exists"

class AudioNotExistsException(DigestSystemException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Audio doesn't exist"


