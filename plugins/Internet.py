###
# Copyright (c) 2002-2004, Jeremiah Fincher
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

"""
Various internet-related commands.
"""

__revision__ = "$Id$"

import supybot.plugins as plugins

import sets
import socket
import telnetlib

import supybot.utils as utils
from supybot.commands import wrap
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

class Internet(callbacks.Privmsg):
    threaded = True
    def dns(self, irc, msg, args, host):
        """<host|ip>

        Returns the ip of <host> or the reverse DNS hostname of <ip>.
        """
        if utils.isIP(host):
            hostname = socket.getfqdn(host)
            if hostname == host:
                irc.reply('Host not found.')
            else:
                irc.reply(hostname)
        else:
            try:
                ip = socket.gethostbyname(host)
                if ip == '64.94.110.11': # Verisign sucks!
                    irc.reply('Host not found.')
                else:
                    irc.reply(ip)
            except socket.error:
                irc.reply('Host not found.')
    dns = wrap(dns, ['something'])

    _tlds = sets.Set(['com', 'net', 'edu'])
    _domain = ['Domain Name', 'Server Name']
    _registrar = ['Sponsoring Registrar', 'Registrar', 'source']
    _updated = ['Last Updated On', 'Domain Last Updated Date', 'Updated Date',
                'Last Modified', 'changed']
    _created = ['Created On', 'Domain Registration Date', 'Creation Date']
    _expires = ['Expiration Date', 'Domain Expiration Date']
    _status = ['Status', 'Domain Status', 'status']
    def whois(self, irc, msg, args, domain):
        """<domain>

        Returns WHOIS information on the registration of <domain>.
        """
        usertld = domain.split('.')[-1]
        if '.' not in domain:
            irc.error('<domain> must be in .com, .net, .edu, or .org.')
            return
        elif len(domain.split('.')) != 2:
            irc.error('<domain> must be a domain, not a hostname.')
            return
        if usertld in self._tlds:
            server = 'rs.internic.net'
            search = '=%s' % domain
        else:
            server = '%s.whois-servers.net' % usertld
            search = domain
        try:
            t = telnetlib.Telnet(server, 43)
        except socket.error, e:
            irc.error(str(e))
            return
        t.write(search)
        t.write('\n')
        s = t.read_all()
        server = registrar = updated = created = expires = status = ''
        for line in s.splitlines():
            line = line.strip()
            if not line or ':' not in line:
                continue
            if not server and any(line.startswith, self._domain):
                server = ':'.join(line.split(':')[1:]).strip().lower()
                # Let's add this check so that we don't respond with info for
                # a different domain. E.g., doing a whois for microsoft.com
                # and replying with the info for microsoft.com.wanadoodoo.com
                if server != domain:
                    server = ''
                    continue
            if not server:
                continue
            if not registrar and any(line.startswith, self._registrar):
                registrar = ':'.join(line.split(':')[1:]).strip()
            elif not updated and any(line.startswith, self._updated):
                s = ':'.join(line.split(':')[1:]).strip()
                updated = 'updated %s' % s
            elif not created and any(line.startswith, self._created):
                s = ':'.join(line.split(':')[1:]).strip()
                created = 'registered %s' % s
            elif not expires and any(line.startswith, self._expires):
                s = ':'.join(line.split(':')[1:]).strip()
                expires = 'expires %s' % s
            elif not status and any(line.startswith, self._status):
                status = ':'.join(line.split(':')[1:]).strip().lower()
        if not status:
            status = 'unknown'
        try:
            t = telnetlib.Telnet('whois.pir.org', 43)
        except socket.error, e:
            irc.error(str(e))
            return
        t.write('registrar ')
        t.write(registrar.split('(')[0].strip())
        t.write('\n')
        s = t.read_all()
        url = ''
        for line in s.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith('Email'):
                url = ' <registered at %s>' % line.split('@')[-1]
            elif line.startswith('Registrar Organization:'):
                url = ' <registered by %s>' % line.split(':')[1].strip()
            elif line == 'Not a valid ID pattern':
                url = ''
        if server and status:
            info = filter(None, [status, created, updated, expires])
            s = '%s%s is %s.' % (server, url, utils.commaAndify(info))
            irc.reply(s)
        else:
            irc.error('I couldn\'t find such a domain.')
    whois = wrap(whois, ['lowered'])


Class = Internet

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
