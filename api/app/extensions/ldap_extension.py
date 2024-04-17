"""Open LDAP authentication extension."""

import logging
from ldap3 import (
    Server,
    Connection,
    Tls,
    ALL,
    SYNC,
    AUTO_BIND_TLS_BEFORE_BIND,
    AUTO_BIND_NO_TLS,
    ANONYMOUS,
    SIMPLE,
    SUBTREE,
)
from ldap3.utils.dn import parse_dn
from ldap3.core.exceptions import LDAPInvalidDnError, LDAPInvalidFilterError, LDAPBindError

from ..config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    LDAP_HOST,
    LDAP_PORT,
    LDAP_USE_SSL,
    LDAP_USE_TLS,
    LDAP_USER_LOGIN_ATTR,
    LDAP_BASE_DN,
    LDAP_SECRET,
)

LOG = logging.getLogger(__name__)


class ExtensionNotInitialized(Exception):
    pass


def is_valid_dn(username: str) -> bool:
    """Check if username is a valid LDAP DN

    :param username: Username for loging
    :type username: str
    :return: True if valid
    :rtype: bool
    """
    try:
        parse_dn(username)
        is_valid = True
    except LDAPInvalidDnError:
        is_valid = False
    return is_valid


class LDAPConnection:
    """Manage connection and authentication to a LDAP server."""

    def __init__(self) -> None:
        self.ldap_connection = None
        self.ldap_server = None

    def init_app(self):
        # setup TLS
        self.tls = Tls()
        # connect to server
        self.server = Server(
            host=LDAP_HOST, port=LDAP_PORT, use_ssl=LDAP_USE_SSL, get_info=ALL
        )

    def connect(self, user: str | None, password: str | None, anonymous: bool = False):
        # set autobind strategy
        authentication_policy = SIMPLE
        if LDAP_USE_TLS:
            auto_bind_strategy = AUTO_BIND_TLS_BEFORE_BIND
        else:
            auto_bind_strategy = AUTO_BIND_NO_TLS

        if anonymous:
            authentication_policy = ANONYMOUS
            user = None
            password = None

        if self.ldap_server is None:
            raise ExtensionNotInitialized("LDAP extension has not been initialized.")

        ldap_conn = Connection(
            self.ldap_server,
            auto_bind=auto_bind_strategy,
            authentication=authentication_policy,
            user=user,
            password=password,
            check_names=True,
        )
        return ldap_conn

    @property
    def connection(self):
        if self.ldap_connection is None:
            self.ldap_connection = self.connect(
                user=LDAP_BASE_DN,
                password=LDAP_SECRET,
                anonymous=LDAP_BASE_DN is None or LDAP_SECRET is None,
            )
        return self.ldap_connection

    def authenticate(
        self,
        user: str,
        password: str,
        base_dn: str | None = None,
        search_filter: str | None = None,
        search_scope=SUBTREE,
    ):
        is_authenticated: bool = False
        if not is_valid_dn(user):
            # try to lookup user DN
            user_filter = "{LDAP_USER_LOGIN_ATTR}={user}"
            if search_filter is not None:
                user_filter = "(&{user_filter}{search_filter})"

            # if lookup fail return false
            try:
                self.connection.search(base_dn, user_filter, search_scope)
            except (LDAPInvalidDnError, LDAPInvalidFilterError, IndexError) as error:
                LOG.warning("Failed to lookup DN for user %s; error: %s", user, error)
                is_authenticated = False
        
        try:
            conn_obj = self.connect(user, password)
            conn_obj.unbind()
            is_authenticated = True
        except LDAPBindError as error:
            LOG.warning("Failed to authenticate user: %s; error: %s", user, error)
            is_authenticated = False
        return is_authenticated
    
    def teardown(self):
        """Teardown admin connection to LDAP server."""
        if self.ldap_connection is None:
            raise ExtensionNotInitialized("No active connection to BASE_DN.")
        self.ldap_connection.unbind()