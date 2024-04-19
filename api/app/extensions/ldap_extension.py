"""Open LDAP authentication extension."""

import logging
from ldap3 import (
    Server,
    Connection,
    Tls,
    ALL,
    AUTO_BIND_TLS_BEFORE_BIND,
    AUTO_BIND_NO_TLS,
    ANONYMOUS,
    SIMPLE,
    SUBTREE,
)
from ldap3.utils.dn import parse_dn
from ldap3.core.exceptions import (
    LDAPInvalidDnError,
    LDAPInvalidFilterError,
    LDAPBindError,
)

from ..config import settings

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
        self.tls = Tls(
            local_private_key_file=settings.ldap_client_private_key,
            local_certificate_file=settings.ldap_client_cert,
            validate=settings.ldap_require_cert,
            version=settings.ldap_tls_version,
            ca_certs_file=settings.ldap_ca_certs_file,
            valid_names=settings.ldap_valid_names,
            ca_certs_path=settings.ldap_ca_certs_path,
            ca_certs_data=settings.ldap_ca_certs_data,
            local_private_key_password=settings.ldap_private_key_password,
        )
        # connect to server
        self.ldap_server = Server(
            host=settings.ldap_host,
            port=settings.ldap_port,
            use_ssl=settings.ldap_use_ssl,
            connect_timeout=settings.ldap_connection_timeout,
            tls=self.tls,
            get_info=ALL,
        )

    def connect(self, user: str | None, password: str | None, anonymous: bool = False):
        # set autobind strategy
        authentication_policy = SIMPLE
        if settings.ldap_use_tls:
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
                user=settings.ldap_bind_dn,
                password=settings.ldap_secret,
                anonymous=settings.ldap_bind_dn is None or settings.ldap_secret is None,
            )
        return self.ldap_connection

    def authenticate(
        self,
        username: str,
        password: str,
        attribute: str = settings.ldap_search_attr,
        base_dn: str = settings.ldap_base_dn,
        search_filter: str | None = settings.ldap_search_filter,
        search_scope=SUBTREE,
    ):
        is_authenticated: bool = False
        if not is_valid_dn(username):
            # try to lookup user DN
            user_filter = f"({attribute}={username})"
            LOG.info("Invalid DN provided, %s, try lookup DN", username)
            if search_filter is not None:
                user_filter = f"(&{user_filter}{search_filter})"

            # if lookup fail return false
            try:
                self.connection.search(
                    search_base=base_dn,
                    search_filter=user_filter,
                    search_scope=search_scope,
                    attributes=[attribute],
                )
                response = self.connection.response
                username = response[0]["dn"]  # update DN
            except (LDAPInvalidDnError, LDAPInvalidFilterError, IndexError) as error:
                LOG.warning("Failed to lookup DN for user %s; error: %s", username, error)
                return False

        try:
            conn_obj = self.connect(username, password)
            conn_obj.unbind()
            is_authenticated = True
        except LDAPBindError as error:
            LOG.warning("Failed to authenticate user: %s; error: %s", username, error)
            is_authenticated = False
        return is_authenticated

    def teardown(self):
        """Teardown admin connection to LDAP server."""
        if self.ldap_connection is not None:
            self.ldap_connection.unbind()
        else:
            LOG.info("No active connection to BASE_DN. Skipping teardown")

    def whoami(self):
        """Return BIND_DN."""
        return self.connection.extend.standard.who_am_i()


ldap_connection = LDAPConnection()
