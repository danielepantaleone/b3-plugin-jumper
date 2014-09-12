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
from b3.update import B3version
from b3 import __version__ as b3_version
from b3.events import Event
from jumper import JumpRun
from mock import Mock
from mockito import when
from tests import logging_disabled
from tests import JumperTestCase

if B3version(b3_version) >= B3version("1.10dev"):
    HAS_ENABLE_DISABLE_HOOKS = True
else:
    HAS_ENABLE_DISABLE_HOOKS = False

class Test_events(JumperTestCase):

    def setUp(self):

        JumperTestCase.setUp(self)

        with logging_disabled():
            from b3.fake import FakeClient

        # prevent the test to query the api: we handle this somewhere else
        when(self.p).getMapsData().thenReturn(dict())

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
        event = self.console.getEventID('EVT_CLIENT_JUMP_RUN_START')
        self.console.queueEvent(Event(event, client=self.mike, data={'way_id' : '1'}))
        # THEN
        self.assertEqual(True, self.mike.isvar(self.p, 'jumprun'))
        self.assertIsNone(self.mike.var(self.p, 'jumprun').value.demo)
        self.assertIsInstance(self.mike.var(self.p, 'jumprun').value, JumpRun)

    def test_event_client_jumprun_stopped(self):
        # WHEN
        event = self.console.getEventID('EVT_CLIENT_JUMP_RUN_STOP')
        self.console.queueEvent(Event(event, client=self.mike, data={'way_id' : '1', 'way_time' : '12345'}))
        # THEN
        self.assertEqual(False, self.mike.isvar(self.p, 'jumprun'))
        self.assertListEqual([], self.p.getClientRecords(self.mike, self.console.game.mapName))

    def test_event_client_jumprun_canceled(self):
        # WHEN
        event = self.console.getEventID('EVT_CLIENT_JUMP_RUN_CANCEL')
        self.console.queueEvent(Event(event, client=self.mike, data={'way_id' : '1'}))
        # THEN
        self.assertEqual(False, self.mike.isvar(self.p, 'jumprun'))
        self.assertListEqual([], self.p.getClientRecords(self.mike, self.console.game.mapName))

    def test_event_client_jumprun_started_stopped(self):
        # WHEN
        event1 = self.console.getEventID('EVT_CLIENT_JUMP_RUN_START')
        event2 = self.console.getEventID('EVT_CLIENT_JUMP_RUN_STOP')
        self.console.queueEvent(Event(event1, client=self.mike, data={'way_id' : '1'}))
        self.console.queueEvent(Event(event2, client=self.mike, data={'way_id' : '1', 'way_time' : '12345'}))
        # THEN
        self.assertEqual(False, self.mike.isvar(self.p, 'jumprun'))
        self.assertEqual(1, len(self.p.getClientRecords(self.mike, self.console.game.mapName)))

    def test_event_client_jumprun_started_canceled(self):
        # WHEN
        event1 = self.console.getEventID('EVT_CLIENT_JUMP_RUN_START')
        event2 = self.console.getEventID('EVT_CLIENT_JUMP_RUN_CANCEL')
        self.console.queueEvent(Event(event1, client=self.mike, data={'way_id' : '1'}))
        self.console.queueEvent(Event(event2, client=self.mike, data={'way_id' : '1'}))
        # THEN
        self.assertEqual(False, self.mike.isvar(self.p, 'jumprun'))
        self.assertEqual(0, len(self.p.getClientRecords(self.mike, self.console.game.mapName)))

    def test_event_client_jumprun_started_stopped_multiple_clients(self):
        # WHEN
        event1 = self.console.getEventID('EVT_CLIENT_JUMP_RUN_START')
        event2 = self.console.getEventID('EVT_CLIENT_JUMP_RUN_STOP')
        self.console.queueEvent(Event(event1, client=self.mike, data={'way_id' : '1'}))
        self.console.queueEvent(Event(event2, client=self.mike, data={'way_id' : '1', 'way_time' : '12345'}))
        self.console.queueEvent(Event(event1, client=self.bill, data={'way_id' : '1'}))
        self.console.queueEvent(Event(event2, client=self.bill, data={'way_id' : '1', 'way_time' : '12345'}))
        # THEN
        self.assertEqual(False, self.mike.isvar(self.p, 'jumprun'))
        self.assertEqual(False, self.bill.isvar(self.p, 'jumprun'))
        self.assertEqual(1, len(self.p.getClientRecords(self.mike, self.console.game.mapName)))
        self.assertEqual(1, len(self.p.getClientRecords(self.bill, self.console.game.mapName)))

    def test_event_client_jumprun_started_stopped_multiple_ways(self):
        # WHEN
        event1 = self.console.getEventID('EVT_CLIENT_JUMP_RUN_START')
        event2 = self.console.getEventID('EVT_CLIENT_JUMP_RUN_STOP')
        self.console.queueEvent(Event(event1, client=self.mike, data={'way_id' : '1'}))
        self.console.queueEvent(Event(event2, client=self.mike, data={'way_id' : '1', 'way_time' : '12345'}))
        self.console.queueEvent(Event(event1, client=self.mike, data={'way_id' : '2'}))
        self.console.queueEvent(Event(event2, client=self.mike, data={'way_id' : '2', 'way_time' : '12345'}))
        # THEN
        self.assertEqual(False, self.mike.isvar(self.p, 'jumprun'))
        self.assertEqual(2, len(self.p.getClientRecords(self.mike, self.console.game.mapName)))

    def test_event_client_jumprun_started_stopped_multiple_clients_multiple_ways(self):
        # WHEN
        event1 = self.console.getEventID('EVT_CLIENT_JUMP_RUN_START')
        event2 = self.console.getEventID('EVT_CLIENT_JUMP_RUN_STOP')
        self.console.queueEvent(Event(event1, client=self.mike, data={'way_id' : '1'}))
        self.console.queueEvent(Event(event2, client=self.mike, data={'way_id' : '1', 'way_time' : '12345'}))
        self.console.queueEvent(Event(event1, client=self.mike, data={'way_id' : '2'}))
        self.console.queueEvent(Event(event2, client=self.mike, data={'way_id' : '2', 'way_time' : '12345'}))
        self.console.queueEvent(Event(event1, client=self.bill, data={'way_id' : '1'}))
        self.console.queueEvent(Event(event2, client=self.bill, data={'way_id' : '1', 'way_time' : '12345'}))
        self.console.queueEvent(Event(event1, client=self.bill, data={'way_id' : '2'}))
        self.console.queueEvent(Event(event2, client=self.bill, data={'way_id' : '2', 'way_time' : '12345'}))
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

    def test_event_game_map_change(self):
        # WHEN
        event1 = self.console.getEventID('EVT_CLIENT_JUMP_RUN_START')
        event2 = self.console.getEventID('EVT_GAME_MAP_CHANGE')
        self.console.queueEvent(Event(event1, client=self.mike, data={'way_id' : '1'}))
        self.console.queueEvent(Event(event1, client=self.bill, data={'way_id' : '1'}))
        self.console.queueEvent(Event(event2, data='\sv_allowdownload\0\g_matchmode\0\g_gametype\9\sv_maxclients\32\sv_floodprotect\1'))
        # THEN
        self.assertEqual(False, self.mike.isvar(self.p, 'jumprun'))
        self.assertEqual(False, self.bill.isvar(self.p, 'jumprun'))
        self.assertListEqual([], self.p.getClientRecords(self.mike, self.console.game.mapName))
        self.assertListEqual([], self.p.getClientRecords(self.bill, self.console.game.mapName))

    def test_event_client_disconnect(self):
        # WHEN
        event1 = self.console.getEventID('EVT_CLIENT_JUMP_RUN_START')
        event2 = self.console.getEventID('EVT_CLIENT_DISCONNECT')
        self.console.queueEvent(Event(event1, client=self.mike, data={'way_id' : '1'}))
        self.console.queueEvent(Event(event2, client=self.mike, data=None))
        # THEN
        self.assertEqual(False, self.mike.isvar(self.p, 'jumprun'))

    def test_event_client_team_change(self):
        # WHEN
        event = self.console.getEventID('EVT_CLIENT_JUMP_RUN_START')
        self.console.queueEvent(Event(event, client=self.mike, data={'way_id' : '1'}))
        self.console.queueEvent(Event(event, client=self.bill, data={'way_id' : '1'}))
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

    @unittest2.skipUnless(HAS_ENABLE_DISABLE_HOOKS, "B3 %s doesn't provide onDisable() plugin hook" % b3_version)
    def test_plugin_disable(self):
        # WHEN
        event = self.console.getEventID('EVT_CLIENT_JUMP_RUN_START')
        self.console.queueEvent(Event(event, client=self.mike, data={'way_id' : '1'}))
        self.console.queueEvent(Event(event, client=self.bill, data={'way_id' : '1'}))
        self.p.disable()
        # THEN
        self.assertEqual(False, self.mike.isvar(self.p, 'jumprun'))
        self.assertEqual(False, self.bill.isvar(self.p, 'jumprun'))

    @unittest2.skipUnless(HAS_ENABLE_DISABLE_HOOKS, "B3 %s doesn't provide onEnable() plugin hook" % b3_version)
    def test_plugin_enable(self):
        # GIVEN
        self.p.console.write = Mock()
        self.p.disable()
        self.p.settings['cycle_count'] = 0
        self.console.game.mapName = 'ut4_casa'
        # WHEN
        self.p.enable()
        self.p.console.write.assert_called_with('cyclemap')
        self.assertEqual(1, self.p.settings['cycle_count'])
