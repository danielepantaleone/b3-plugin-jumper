#
# Jumper Plugin for BigBrotherBot(B3) (www.bigbrotherbot.net)
# Copyright (C) 2013 Daniele Pantaleone <fenix@bigbrotherbot.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

import json
import logging
import unittest2

from textwrap import dedent
from mockito import when
from jumper import JumperPlugin
from b3.cvar import Cvar
from b3.config import XmlConfigParser
from b3.config import CfgConfigParser
from b3.plugins.admin import AdminPlugin
from b3 import __version__ as b3_version

try:
    from b3.parsers.iourt42 import Iourt42Parser
except ImportError:
    HAS_IOURT42_PARSER = False
else:
    HAS_IOURT42_PARSER = True

MAPDATA_JSON = '''{"ut4_uranus_beta1a": {"size": 1841559, "nom": "Uranus", "njump": "22", "mdate": "2013-01-16", "pk3":
"ut4_uranus_beta1a", "level": 50, "id": 308, "utversion": 2, "nway": 1, "howjump": "", "mapper": "Levant"},
"ut4_crouchtraining_a1": {"size": 993461, "nom": "Crouch Training", "njump": "11", "mdate": "2010-12-31",
"pk3": "ut4_crouchtraining_a1", "level": 79, "id": 346, "utversion": 2, "nway": 1, "howjump": "", "mapper": "spidercochon"}}'''

class logging_disabled(object):
    """
    Context manager that temporarily disable logging.

    USAGE:
        with logging_disabled():
            # do stuff
    """
    DISABLED = False

    def __init__(self):
        self.nested = logging_disabled.DISABLED

    def __enter__(self):
        if not self.nested:
            logging.getLogger('output').propagate = False
            logging_disabled.DISABLED = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.nested:
            logging.getLogger('output').propagate = True
            logging_disabled.DISABLED = False


@unittest2.skipUnless(HAS_IOURT42_PARSER, "B3 %s does not have the iourt42 parser" % b3_version)
class JumperTestCase(unittest2.TestCase):

    @classmethod
    def setUpClass(cls):
        with logging_disabled():
            from b3.parsers.q3a.abstractParser import AbstractParser
            from b3.fake import FakeConsole
            AbstractParser.__bases__ = (FakeConsole,)
            # Now parser inheritance hierarchy is :
            # Iourt41Parser -> abstractParser -> FakeConsole -> Parser

    def setUp(self):
        # create a Iourt42 parser
        self.parser_conf = XmlConfigParser()
        self.parser_conf.loadFromString(dedent(r"""
            <configuration>
                <settings name="server">
                    <set name="game_log"></set>
                </settings>
            </configuration>
        """))

        self.console = Iourt42Parser(self.parser_conf)

        # initialize some fixed cvars which will be used by both the plugin and the iourt42 parser
        when(self.console).getCvar('auth').thenReturn(Cvar('auth', value='0'))
        when(self.console).getCvar('fs_basepath').thenReturn(Cvar('g_maxGameClients', value='/fake/basepath'))
        when(self.console).getCvar('fs_homepath').thenReturn(Cvar('sv_maxclients', value='/fake/homepath'))
        when(self.console).getCvar('fs_game').thenReturn(Cvar('fs_game', value='q3ut4'))
        when(self.console).getCvar('gamename').thenReturn(Cvar('gamename', value='q3urt42'))

        # start the parser
        self.console.startup()

        with logging_disabled():
            self.adminPlugin = AdminPlugin(self.console, '@b3/conf/plugin_admin.ini')
            self.adminPlugin.onLoadConfig()
            self.adminPlugin.onStartup()

        # make sure the admin plugin obtained by other plugins is our admin plugin
        when(self.console).getPlugin('admin').thenReturn(self.adminPlugin)

        self.conf = CfgConfigParser()
        self.conf.loadFromString(dedent(r"""
            [settings]
            demorecord: no
            skipstandardmaps: yes
            minleveldelete: senioradmin

            [commands]
            jmprecord-record: guest
            jmpmaprecord-maprecord: guest
            jmptopruns-topruns: guest
            jmpdelrecord-delrecord: guest
            jmpmapinfo-mapinfo: guest
            jmpsetway-setway: senioradmin
        """))

        self.p = JumperPlugin(self.console, self.conf)
        self.p.onLoadConfig()
        self.p.onStartup()

        # load fixed json data (do not contact urtjumpers api for testing)
        when(self.p).getMapsData().thenReturn(json.loads(MAPDATA_JSON))

    def tearDown(self):
        self.console.working = False