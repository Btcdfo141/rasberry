"""Auth models."""
from datetime import datetime, timedelta
import uuid

import attr

from homeassistant.util import dt as dt_util

from .const import ACCESS_TOKEN_EXPIRATION
from .util import generate_secret


@attr.s(slots=True)
class User:
    """A user."""

    name = attr.ib(type=str)
    id = attr.ib(type=str, default=attr.Factory(lambda: uuid.uuid4().hex))
    is_owner = attr.ib(type=bool, default=False)
    is_active = attr.ib(type=bool, default=False)
    system_generated = attr.ib(type=bool, default=False)

    # List of credentials of a user.
    credentials = attr.ib(type=list, default=attr.Factory(list), cmp=False)

    # Tokens associated with a user.
    refresh_tokens = attr.ib(type=dict, default=attr.Factory(dict), cmp=False)

    # Enabled multi-factor auth modules of a user.
    mfa_modules = attr.ib(type=list, default=attr.Factory(list), cmp=False)


@attr.s(slots=True)
class RefreshToken:
    """RefreshToken for a user to grant new access tokens."""

    user = attr.ib(type=User)
    client_id = attr.ib(type=str)
    id = attr.ib(type=str, default=attr.Factory(lambda: uuid.uuid4().hex))
    created_at = attr.ib(type=datetime, default=attr.Factory(dt_util.utcnow))
    access_token_expiration = attr.ib(type=timedelta,
                                      default=ACCESS_TOKEN_EXPIRATION)
    token = attr.ib(type=str,
                    default=attr.Factory(lambda: generate_secret(64)))
    access_tokens = attr.ib(type=list, default=attr.Factory(list), cmp=False)


@attr.s(slots=True)
class AccessToken:
    """Access token to access the API.

    These will only ever be stored in memory and not be persisted.
    """

    refresh_token = attr.ib(type=RefreshToken)
    created_at = attr.ib(type=datetime, default=attr.Factory(dt_util.utcnow))
    token = attr.ib(type=str,
                    default=attr.Factory(generate_secret))

    @property
    def expired(self):
        """Return if this token has expired."""
        expires = self.created_at + self.refresh_token.access_token_expiration
        return dt_util.utcnow() > expires


@attr.s(slots=True)
class Credentials:
    """Credentials for a user on an auth provider."""

    auth_provider_type = attr.ib(type=str)
    auth_provider_id = attr.ib(type=str)

    # Allow the auth provider to store data to represent their auth.
    data = attr.ib(type=dict)

    id = attr.ib(type=str, default=attr.Factory(lambda: uuid.uuid4().hex))
    is_new = attr.ib(type=bool, default=True)
