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

import unittest2

from b3 import TEAM_FREE
from b3 import TEAM_SPEC
from jumper import JumpRun
from tests import logging_disabled
from tests import JumperTestCase
from b3.update import B3version
from b3 import __version__ as b3_version

if B3version(b3_version) >= B3version("1.10dev"):
    HAS_ENABLE_DISABLE_HOOKS = True
else:
    HAS_ENABLE_DISABLE_HOOKS = False

class Test_events(JumperTestCase):

    def setUp(self):

        JumperTestCase.setUp(self)

        with logging_disabled():
            from b3.fake import FakeClient

        # create some clients
        self.mike = FakeClient(console=self.console, name="Mike", guid="mikeguid", team=TEAM_FREE, groupBits=1)
        self.bill = FakeClient(console=self.console, name="Bill", guid="billguid", team=TEAM_FREE, groupBits=1)
        self.mike.connects("1")
        self.bill.connects("2")

        # force fake mapname
        self.console.game.mapName = 'ut42_bstjumps_u2'

    def tearDown(self):
        self.mike.disconnects()
        self.bill.disconnects()
        JumperTestCase.tearDown(self)

    ####################################################################################################################
    ##                                                                                                                ##
    ##   JUMPRUN EVENTS                                                                                               ##
    ##                                                                                                                ##
    ####################################################################################################################

    def test_event_client_jumprun_started(self):
        # WHEN
        self.console.parseLine('''ClientJumpRunStarted: 1 - way: 1''')
        # THEN
        self.assertEqual(True, self.mike.isvar(self.p, 'jumprun'))
        self.assertIsNone(self.mike.var(self.p, 'jumprun').value.demo)
        self.assertIsInstance(self.mike.var(self.p, 'jumprun').value, JumpRun)

    def test_event_client_jumprun_stopped(self):
        # WHEN
        self.console.parseLine('''ClientJumpRunStopped: 1 - way: 1 - time: 12345''')
        # THEN
        self.assertEqual(False, self.mike.isvar(self.p, 'jumprun'))
        self.assertListEqual([], self.p.getClientRecords(self.mike, self.console.game.mapName))

    def test_event_client_jumprun_canceled(self):
        # WHEN
        self.console.parseLine('''ClientJumpRunCanceled: 1 - way: 1''')
        # THEN
        self.assertEqual(False, self.mike.isvar(self.p, 'jumprun'))
        self.assertListEqual([], self.p.getClientRecords(self.mike, self.console.game.mapName))

    def test_event_client_jumprun_started_stopped(self):
        # WHEN
        self.console.parseLine('''ClientJumpRunStarted: 1 - way: 1''')
        self.console.parseLine('''ClientJumpRunStopped: 1 - way: 1 - time: 12345''')
        # THEN
        self.assertEqual(False, self.mike.isvar(self.p, 'jumprun'))
        self.assertEqual(1, len(self.p.getClientRecords(self.mike, self.console.game.mapName)))

    def test_event_client_jumprun_started_canceled(self):
        # WHEN
        self.console.parseLine('''ClientJumpRunStarted: 1 - way: 1''')
        self.console.parseLine('''ClientJumpRunCanceled: 1 - way: 1''')
        # THEN
        self.assertEqual(False, self.mike.isvar(self.p, 'jumprun'))
        self.assertEqual(0, len(self.p.getClientRecords(self.mike, self.console.game.mapName)))

    def test_event_client_jumprun_started_stopped_multiple_clients(self):
        # WHEN
        self.console.parseLine('''ClientJumpRunStarted: 1 - way: 1''')
        self.console.parseLine('''ClientJumpRunStopped: 1 - way: 1 - time: 12345''')
        self.console.parseLine('''ClientJumpRunStarted: 2 - way: 1''')
        self.console.parseLine('''ClientJumpRunStopped: 2 - way: 1 - time: 12345''')
        # THEN
        self.assertEqual(False, self.mike.isvar(self.p, 'jumprun'))
        self.assertEqual(False, self.bill.isvar(self.p, 'jumprun'))
        self.assertEqual(1, len(self.p.getClientRecords(self.mike, self.console.game.mapName)))
        self.assertEqual(1, len(self.p.getClientRecords(self.bill, self.console.game.mapName)))

    def test_event_client_jumprun_started_stopped_multiple_ways(self):
        # WHEN
        self.console.parseLine('''ClientJumpRunStarted: 1 - way: 1''')
        self.console.parseLine('''ClientJumpRunStopped: 1 - way: 1 - time: 12345''')
        self.console.parseLine('''ClientJumpRunStarted: 1 - way: 2''')
        self.console.parseLine('''ClientJumpRunStopped: 1 - way: 2 - time: 12345''')
        # THEN
        self.assertEqual(False, self.mike.isvar(self.p, 'jumprun'))
        self.assertEqual(2, len(self.p.getClientRecords(self.mike, self.console.game.mapName)))

    def test_event_client_jumprun_started_stopped_multiple_clients_multiple_ways(self):
        # WHEN
        self.console.parseLine('''ClientJumpRunStarted: 1 - way: 1''')
        self.console.parseLine('''ClientJumpRunStopped: 1 - way: 1 - time: 12345''')
        self.console.parseLine('''ClientJumpRunStarted: 1 - way: 2''')
        self.console.parseLine('''ClientJumpRunStopped: 1 - way: 2 - time: 12345''')
        self.console.parseLine('''ClientJumpRunStarted: 2 - way: 1''')
        self.console.parseLine('''ClientJumpRunStopped: 2 - way: 1 - time: 12345''')
        self.console.parseLine('''ClientJumpRunStarted: 2 - way: 2''')
        self.console.parseLine('''ClientJumpRunStopped: 2 - way: 2 - time: 12345''')
        # THEN
        self.assertEqual(False, self.mike.isvar(self.p, 'jumprun'))
        self.assertEqual(False, self.bill.isvar(self.p, 'jumprun'))
        self.assertEqual(2, len(self.p.getClientRecords(self.mike, self.console.game.mapName)))
        self.assertEqual(2, len(self.p.getClientRecords(self.bill, self.console.game.mapName)))

    ####################################################################################################################
    ##                                                                                                                ##
    ##   OTHER EVENTS                                                                                                 ##
    ##                                                                                                                ##
    ####################################################################################################################

    def test_event_round_start(self):
        # WHEN
        self.console.parseLine('''ClientJumpRunStarted: 1 - way: 1''')
        self.console.parseLine('''ClientJumpRunStarted: 2 - way: 1''')
        self.console.parseLine('''InitGame: \sv_allowdownload\0\g_matchmode\0\g_gametype\9\sv_maxclients\32\sv_floodprotect\1''')
        # THEN
        self.assertEqual(False, self.mike.isvar(self.p, 'jumprun'))
        self.assertEqual(False, self.bill.isvar(self.p, 'jumprun'))
        self.assertListEqual([], self.p.getClientRecords(self.mike, self.console.game.mapName))
        self.assertListEqual([], self.p.getClientRecords(self.bill, self.console.game.mapName))

    def test_event_client_disconnect(self):
        # WHEN
        self.console.parseLine('''ClientJumpRunStarted: 1 - way: 1''')
        self.console.parseLine('''ClientDisconnect: 1''')
        # THEN
        self.assertEqual(False, self.mike.isvar(self.p, 'jumprun'))

    def test_event_client_team_change(self):
        # WHEN
        self.console.parseLine('''ClientJumpRunStarted: 1 - way: 1''')
        self.console.parseLine('''ClientJumpRunStarted: 2 - way: 1''')
        self.mike.team = TEAM_SPEC  # will raise EVT_CLIENT_TEAM_CHANGE
        self.bill.team = TEAM_FREE  # will not raise EVT_CLIENT_TEAM_CHANGE
        # THEN
        self.assertEqual(TEAM_SPEC, self.mike.team)
        self.assertEqual(TEAM_FREE, self.bill.team)
        self.assertEqual(False, self.mike.isvar(self.p, 'jumprun'))
        self.assertEqual(True, self.bill.isvar(self.p, 'jumprun'))
        self.assertIsInstance(self.bill.var(self.p, 'jumprun').value, JumpRun)

    ####################################################################################################################
    ##                                                                                                                ##
    ##   PLUGIN HOOKS                                                                                                 ##
    ##                                                                                                                ##
    ####################################################################################################################

    @unittest2.skipUnless(HAS_ENABLE_DISABLE_HOOKS, "B3 %s does provide onEnable() and onDisabled() hooks" % b3_version)
    def test_plugin_disable(self):
        # WHEN
        self.console.parseLine('''ClientJumpRunStarted: 1 - way: 1''')
        self.console.parseLine('''ClientJumpRunStarted: 2 - way: 1''')
        self.p.disable()
        # THEN
        self.assertEqual(False, self.mike.isvar(self.p, 'jumprun'))
        self.assertEqual(False, self.bill.isvar(self.p, 'jumprun'))

    @unittest2.skipUnless(HAS_ENABLE_DISABLE_HOOKS, "B3 %s does provide onEnable() and onDisabled() hooks" % b3_version)
    def test_plugin_enable(self):
        # GIVEN
        self.p.disable()
        self.console.game.mapName = 'ut4_casa'
        # WHEN
        self.p.enable()
        self.assertEqual(1, self.p.settings['cycle_count'])
