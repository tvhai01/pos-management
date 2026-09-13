"""
Custom exceptions for the Accounts app.

App-specific exceptions that inherit from shared.exceptions.ApplicationError.
Each exception maps to a specific HTTP status code and error message.
"""

from rest_framework import status

from apps.accounts.constants import MSG_EMAIL_ALREADY_EXISTS, MSG_USER_NOT_FOUND
from shared.exceptions import ApplicationError


class InvalidCredentialsError(ApplicationError):
    """Raised when login credentials are invalid."""

    status_code: int = status.HTTP_401_UNAUTHORIZED
    default_detail: str = "Invalid email or password."
    default_code: str = "invalid_credentials"


class InactiveAccountError(ApplicationError):
    """Raised when a deactivated user attempts to authenticate."""

    status_code: int = status.HTTP_401_UNAUTHORIZED
    default_detail: str = "This account has been deactivated."
    default_code: str = "inactive_account"


class TokenError(ApplicationError):
    """Raised when a JWT token is invalid or expired."""

    status_code: int = status.HTTP_401_UNAUTHORIZED
    default_detail: str = "Token is invalid or expired."
    default_code: str = "token_error"


class OldPasswordIncorrectError(ApplicationError):
    """Raised when the old password doesn't match during password change."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    default_detail: str = "Old password is incorrect."
    default_code: str = "old_password_incorrect"


class PasswordMismatchError(ApplicationError):
    """Raised when new password and confirm password don't match."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    default_detail: str = "New password and confirm password do not match."
    default_code: str = "password_mismatch"


class RoleNotFoundError(ApplicationError):
    """Raised when a role cannot be found."""

    status_code: int = status.HTTP_404_NOT_FOUND
    default_detail: str = "Role not found."
    default_code: str = "role_not_found"


class RoleHasUsersError(ApplicationError):
    """Raised when trying to delete a role that has assigned users."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    default_detail: str = "Cannot delete role that has assigned users."
    default_code: str = "role_has_users"


class UserNotFoundError(ApplicationError):
    """Raised when a user cannot be found."""

    status_code: int = status.HTTP_404_NOT_FOUND
    default_detail: str = MSG_USER_NOT_FOUND
    default_code: str = "user_not_found"


class UserAlreadyExistsError(ApplicationError):
    """Raised when creating a user with an email that is already in use."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    default_detail: str = MSG_EMAIL_ALREADY_EXISTS
    default_code: str = "user_already_exists"
