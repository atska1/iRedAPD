# Author: Zhang Huangbin <zhb _at_ iredmail.org>

from libs.logger import logger
from libs import utils
import ldap
import settings


def get_account_ldif(conn, account, query_filter=None, attrs=None):
    logger.debug("[+] Getting LDIF data of account: {0}".format(account))

    if not query_filter:
        query_filter = '(&' + \
                       '(!(domainStatus=disabled))' + \
                       '(|(mail=%(account)s)(shadowAddress=%(account)s))' % {'account': account} + \
                       '(|' + \
                       '(objectClass=mailUser)' + \
                       '(objectClass=mailList)' + \
                       '(objectClass=mailAlias)' + \
                       '))'

    logger.debug("search base dn: {0}\n"
                 "search scope: SUBTREE \n"
                 "search filter: {1}\n"
                 "search attributes: {2}".format(
                     settings.ldap_basedn,
                     query_filter,
                     attrs))

    if not isinstance(attrs, list):
        # Attribute list must be None (search all attributes) or non-empty list
        attrs = None

    try:
        result = conn.search_s(settings.ldap_basedn,
                               ldap.SCOPE_SUBTREE,
                               query_filter,
                               attrs)

        if result:
            logger.debug("result: {0}".format(repr(result)))
            # (dn, entry = result[0])
            return result[0]
        else:
            logger.debug('No such account.')
            return (None, None)
    except Exception as e:
        logger.debug("<!> ERROR: {0}".format(repr(e)))
        return (None, None)


def get_primary_and_alias_domains(conn, domain):
    """Query LDAP to get all available alias domain names of given domain.

    Return list of alias domain names.

    @conn -- ldap connection cursor
    @domain -- domain name
    """
    if not utils.is_domain(domain):
        return []

    try:
        _f = "(&(objectClass=mailDomain)(|(domainName=%s)(domainAliasName=%s)))" % (domain, domain)
        qr = conn.search_s(settings.ldap_basedn,
                           1,  # 1 == ldap.SCOPE_ONELEVEL
                           _f,
                           ['domainName', 'domainAliasName'])
        if qr:
            (_dn, _ldif) = qr[0]
            _all_domains = _ldif.get('domainName', []) + _ldif.get('domainAliasName', [])

            return list(set(_all_domains))
    except Exception as e:
        # Log and return if LDAP error occurs
        logger.error("Error while querying alias domains of domain ({0}): {1}".format(domain, repr(e)))
        return []


def is_local_domain(conn,
                    domain,
                    include_alias_domain=True,
                    include_backupmx=True):
    if not utils.is_domain(domain):
        return False

    if utils.is_server_hostname(domain):
        return True

    try:
        _filter = '(&(objectClass=mailDomain)(accountStatus=active)'

        if include_alias_domain:
            _filter += '(|(domainName=%s)(domainAliasName=%s))' % (domain, domain)
        else:
            _filter += '(domainName=%s)' % domain

        if not include_backupmx:
            _filter += '(!(domainBackupMX=yes))'

        _filter += ')'

        qr = conn.search_s(settings.ldap_basedn,
                           1,   # 1 == ldap.SCOPE_ONELEVEL
                           _filter,
                           ['dn'])
        if qr:
            return True
    except ldap.NO_SUCH_OBJECT:
        return False
    except Exception as e:
        logger.error("<!> Error while querying local domain: {0}".format(repr(e)))
        return False


def get_alias_target_domain(alias_domain, conn, include_backupmx=True):
    """Query target domain of given alias domain name."""
    alias_domain = str(alias_domain).lower()

    if not utils.is_domain(alias_domain):
        logger.debug("Given alias_domain {0} is not an valid domain name.".format(alias_domain))
        return None

    try:
        _filter = '(&(objectClass=mailDomain)(accountStatus=active)'
        _filter += '(domainAliasName=%s)' % alias_domain

        if not include_backupmx:
            _filter += '(!(domainBackupMX=yes))'

        _filter += ')'

        logger.debug("[LDAP] query target domain of given alias domain: {0}\n"
                     "[LDAP] query filter: {1}".format(alias_domain, _filter))
        qr = conn.search_s(settings.ldap_basedn,
                           1,   # 1 == ldap.SCOPE_ONELEVEL
                           _filter,
                           ['domainName'])

        logger.debug("result: {0}".format(repr(qr)))
        if qr:
            (_dn, _ldif) = qr[0]
            _domain = _ldif['domainName'][0]
            return _domain
    except ldap.NO_SUCH_OBJECT:
        pass
    except Exception as e:
        logger.error("<!> Error while querying alias domain: {0}".format(repr(e)))

    return None
