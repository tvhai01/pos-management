"""
Custom user manager for the Accounts app.

Provides manager methods for creating regular users and superusers
using email as the primary identifier instead of username.
"""

import logging

from django.contrib.auth.models import BaseUserManager

logger = logging.getLogger(__name__)


class UserManager(BaseUserManager):
    """Custom manager for User model.

    Uses email as the unique identifier for authentication
    instead of the default username field.
    """

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: object,
    ) -> "User":  # noqa: F821
        """Create and return a regular user.

        Args:
            email: The user's email address (required, used as login).
            password: The user's password (will be hashed).
            **extra_fields: Additional fields to set on the user model.

        Returns:
            The created User instance.

        Raises:
            ValueError: If email is not provided.
        """
        if not email:
            raise ValueError("The email field is required.")

        email = self.normalize_email(email)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        logger.info("Created user: %s", email)
        return user

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: object,
    ) -> "User":  # noqa: F821
        """Create and return a superuser.

        Args:
            email: The superuser's email address (required).
            password: The superuser's password (will be hashed).
            **extra_fields: Additional fields to set on the user model.

        Returns:
            The created superuser User instance.

        Raises:
            ValueError: If is_staff or is_superuser is not True.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        logger.info("Creating superuser: %s", email)
        return self.create_user(email, password, **extra_fields)
