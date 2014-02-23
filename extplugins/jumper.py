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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#
# CHANGELOG:
#
# 09/08/2013 - 2.0 - Fenix
#   - created new version of the plugin compatible with Urban Terror 4.2 jump mode specific events
# 31/08/2013 - 2.1 - Fenix
#   - added command !jmpmapinfo: display map specific informations (thanks UrTJumpers community)
# 08/09/2013 - 2.2 - Fenix
#   - updated algorithm for map search
#   - added number of jumps and number of ways in !jmpinfo command output
# 25/10/2013 - 2.3 - Fenix
#   - fixed some in-game messages spelling
# 26/10/2013 - 2.4 - Fenix
#   - updated plugin syntax: get close to PEP8 coding style guide
#   - updated sql script: added a nre table 'jumpways'
#   - added command !jmpsetway: add an alias for the given way id
#   - escape single quote from demo file name: was breaking the sql query
# 11/11/2013 - 2.5 - Fenix
#   - improved plugin configuration loading: added more verbose logging
#   - fixed some logging messages
#   - make 'demorecord' option configuration value more user-friendly
# 07/12/2013 - 2.6 - Fenix
#   - updated GPL header with new information
#   - fixed missing mappings for string replacements
# 08/12/2013 - 2.7 - Fenix
#   - added possibility to autocycle non-jump maps: works with built-in maps
#   - let the plugin use the new built-in event dispatcher
# 08/12/2013 - 2.8 - Fenix
#   - stop all the running demos when the plugin gets disabled
# 23/12/2013 - 2.9 - Fenix
#   - double check timer correctly started upon EVT_CLIENT_JUMP_RUN_STOP
#   - changed default message for 'mapinfo_failed'
#   - fixed number of argument for string formatting in client record pattern
# 15/01/2014 - 2.10 - Fenix
#   - replaced .xml configuration file with .ini format
#   - use plugin default message structure instead of another dictionary
#   - implement onEnable hook: check that we are not playing a built-in map upon plugin enable
# 15/01/2014 - 2.10 - Fenix
#   - make use of getGroupLevel method while loading min_level_delete setting
# 15/01/2014 - 2.11 - Fenix
#   - override admin plugin command !maps: custom version which remove standard maps if specified in the config file
#   - override admin plugin command !map: custom version deny built-in maps if specified in the config file
#   - override command !pasetnextmap provided by poweradminurt: custom version which deny built-in maps if
#     specified in the configuration file
# 16/01/2014 - 2.12 - Fenix
#   - correctly remove built-in maps from map list in !maps command
# 29/01/2014 - 2.13 - Fenix
#   - overridden parser method getStuffSoundingLike: do not display standard map list if specified in the config file
# 30/01/2014 - 2.14 - Fenix
#   - updated readme: added new requirement and changed installation tutorial
# 05/02/2014 - 2.15 - Fenix
#   - fixed maplist filtering
#   - fixed string formatting: client name mapping was required
# 07/02/2014 - 2.16 - Fenix
#   - make sure to stop all the demos being recorded on plugin startup
# 09/02/2014 - 2.17 - Fenix
#   - register events using the event id: remove some warnings in PyCharm
#   - catch KeyError exception when using self.console.getGroupLevel(): raised if an invalid level/keyword is supplied
# 10/02/2014 - 2.18 - Fenix
#   - added command !jmptopruns: display specific map top 3 jump runs
#   - added optional parameter to !jmpmaprecord command
#   - added optional parameter to !jmpdelrecord command
#   - added optional parameter to !jmprecord command
#   - several code improvements

__author__ = 'Fenix'
__version__ = '2.18'

import b3
import b3.plugin
import b3.events
import urllib2
import json
import time
import datetime
import socket
import os
import re

from b3.functions import getStuffSoundingLike
from ConfigParser import NoOptionError


class JumperPlugin(b3.plugin.Plugin):

    _adminPlugin = None
    _poweradminurtPlugin = None

    _map_data = dict()

    _standard_maplist = ['ut4_abbey', 'ut4_abbeyctf', 'ut4_algiers', 'ut4_ambush', 'ut4_austria',
                         'ut4_bohemia', 'ut4_casa', 'ut4_cascade', 'ut4_commune', 'ut4_company', 'ut4_crossing',
                         'ut4_docks', 'ut4_dressingroom', 'ut4_eagle', 'ut4_elgin', 'ut4_firingrange',
                         'ut4_ghosttown_rc4', 'ut4_harbortown', 'ut4_herring', 'ut4_horror', 'ut4_kingdom',
                         'ut4_kingpin', 'ut4_mandolin', 'ut4_maya', 'ut4_oildepot', 'ut4_prague', 'ut4_prague_v2',
                         'ut4_raiders', 'ut4_ramelle', 'ut4_ricochet', 'ut4_riyadh', 'ut4_sanc', 'ut4_snoppis',
                         'ut4_suburbs', 'ut4_subway', 'ut4_swim', 'ut4_thingley', 'ut4_tombs', 'ut4_toxic',
                         'ut4_tunis', 'ut4_turnpike', 'ut4_uptown']

    _sql = dict(
        jr1="""SELECT * FROM jumpruns WHERE client_id = '%s' AND `mapname` = '%s' AND `way_id` = '%d'""",
        jr2="""SELECT * FROM `jumpruns` WHERE `mapname` = '%s' AND `way_id` = '%d' AND `way_time` < '%d'""",
        jr3="""SELECT `cl`.`name` AS `name`, `jr`.`way_id` AS `way_id`, `jr`.`way_time` AS `way_time`,"""
            """       `jr`.`time_edit` AS `time_edit`, `jw`.`way_name` AS `way_name` FROM `clients` AS `cl`"""
            """       INNER JOIN `jumpruns` AS `jr` ON `cl`.`id` = `jr`.`client_id` LEFT OUTER JOIN `jumpways`"""
            """       AS `jw` ON `jr`.`way_id` = `jw`.`way_id` AND `jr`.`mapname` = `jw`.`mapname` WHERE"""
            """       `jr`.`mapname` = '%s' AND `jr`.`way_time` IN (SELECT MIN(`way_time`) FROM `jumpruns` WHERE"""
            """       `mapname` = '%s' GROUP BY  `way_id`) ORDER BY  `jr`.`way_id` ASC""",
        jr4="""SELECT `jr`.`way_id` AS `way_id`, `jr`.`way_time` AS `way_time`, `jr`.`time_edit` AS `time_edit`,"""
            """       `jr`.`demo` AS `demo`, `jw`.`way_name` AS `way_name` FROM `jumpruns` AS `jr`"""
            """       LEFT OUTER JOIN  `jumpways` AS `jw` ON  `jr`.`way_id` = `jw`.`way_id`"""
            """       AND `jr`.`mapname` = `jw`.`mapname` WHERE `jr`.`client_id` = '%s' AND `jr`.`mapname` = '%s'"""
            """       ORDER BY `jr`.`way_id` ASC""",
        jr5="""SELECT DISTINCT  `way_id` FROM  `jumpruns` WHERE  `mapname` =  '%s' ORDER BY `way_id` ASC""",
        jr6="""SELECT `cl`.`name` AS `name`, `jr`.`way_id` AS `way_id`, `jr`.`way_time` AS `way_time`,"""
            """       `jr`.`time_edit` AS `time_edit`, `jw`.`way_name` AS `way_name` FROM `clients` AS `cl`"""
            """       INNER JOIN `jumpruns` AS `jr` ON `cl`.`id` = `jr`.`client_id` LEFT OUTER JOIN `jumpways`"""
            """       AS `jw` ON `jr`.`way_id` = `jw`.`way_id` AND `jr`.`mapname` = `jw`.`mapname`"""
            """       WHERE `jr`.`mapname` = '%s' AND `jr`.`way_id` = '%d' ORDER BY `jr`.`way_time` ASC LIMIT 3""",
        jr7="""INSERT INTO `jumpruns` VALUES (NULL, '%s', '%s', '%d', '%d', '%d', '%d', '%s')""",
        jr8="""UPDATE `jumpruns` SET `way_time` = '%d', `time_edit` = '%d', `demo` = '%s' WHERE `client_id` = '%s'"""
            """       AND `mapname` = '%s' AND `way_id` = '%d'""",
        jr9="""DELETE FROM `jumpruns` WHERE `client_id` = '%s' AND `mapname` = '%s'""",
        jw1="""SELECT * FROM `jumpways` WHERE `mapname` = '%s' AND `way_id` = '%d'""",
        jw2="""INSERT INTO `jumpways` VALUES (NULL, '%s', '%d', '%s')""",
        jw3="""UPDATE `jumpways` SET `way_name` = '%s' WHERE `mapname` = '%s' AND `way_id` = '%d'""")

    _settings = dict(demo_record=True,
                     skip_standard_maps=True,
                     min_level_delete=80,
                     max_cycle_count=5,
                     cycle_count=0)

    ####################################################################################################################
    ##                                                                                                                ##
    ##   STARTUP                                                                                                      ##
    ##                                                                                                                ##
    ####################################################################################################################

    def __init__(self, console, config=None):
        """
        Build the plugin object
        """
        b3.plugin.Plugin.__init__(self, console, config)
        if self.console.gameName != 'iourt42':
            self.critical("unsupported game : %s" % self.console.gameName)
            raise SystemExit(220)
        
        # get the admin plugin
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            self.critical('could not start without admin plugin')
            raise SystemExit(220)

        # get the poweradminurt plugin
        self._poweradminurtPlugin = self.console.getPlugin('poweradminurt')
        
        # set default messages
        self._default_messages = dict(
            client_record_unknown='''^7no record found for ^3$client ^7on ^3$mapname''',
            client_record_deleted='''^7removed ^3$num ^7record$plural for ^3$client ^7on ^3$mapname''',
            client_record_header='''^7listing records for ^3$client ^7on ^3$mapname^7:''',
            client_record_pattern='''^7[^3$way^7] ^2$time ^7since ^3$date''',
            map_record_established='''^3$client ^7established a new map record^7!''',
            map_record_unknown='''^7no record found on ^3$mapname''',
            map_record_header='''^7listing map records on ^3$mapname^7:''',
            map_record_pattern='''^7[^3$way^7] ^3$client ^7with ^2$time''',
            map_toprun_header='''^7listing top runs on ^3$mapname^7:''',
            map_toprun_pattern='''^7[^3$way^7] #$place ^3$client ^7with ^2$time''',
            mapinfo_failed='''^7could not query remote server to get map data''',
            mapinfo_empty='''^7could not find info for map ^1$mapname''',
            mapinfo_author_unknown='''^7I don't know who created ^3$mapname''',
            mapinfo_author='''^3$mapname ^7has been created by ^3$author''',
            mapinfo_released='''^7it has been released on ^3$date''',
            mapinfo_ways='''^7it's composed of ^3$way ^7way$plural''',
            mapinfo_jump_ways='''^7it's composed of ^3$jumps ^7jumps and ^3$way ^7way$plural''',
            mapinfo_level='''^7level: ^3$level^7/^3100''',
            personal_record_failed='''^7you can do better ^3$client^7...try again!''',
            personal_record_established='''^7you established a new personal record on ^3$mapname7!''',
            record_delete_denied='''^7you can't delete ^1$client ^7records''')

        # override parser functions
        self.console.getMapsSoundingLike = self.getMapsSoundingLike

        # override other plugin commands
        self._adminPlugin.cmd_maps = self.cmd_maps
        self._adminPlugin.cmd_map = self.cmd_map

        if self._poweradminurtPlugin:
            self._poweradminurtPlugin.cmd_pasetnextmap = self.cmd_pasetnextmap
     
    def onLoadConfig(self):
        """\
        Load plugin configuration
        """
        try:
            self._settings['demo_record'] = self.config.getboolean('settings', 'demorecord')
            self.debug('loaded settings/demorecord: %s' % self._settings['demo_record'])
        except NoOptionError:
            self.warning('could not find settings/demorecord in config file, '
                         'using default: %s' % self._settings['demo_record'])
        except ValueError, e:
            self.error('could not load settings/demorecord config value: %s' % e)
            self.debug('using default value (%s) for settings/demorecord' % self._settings['demo_record'])

        try:
            self._settings['skip_standard_maps'] = self.config.getboolean('settings', 'skipstandardmaps')
            self.debug('loaded settings/skipstandardmaps: %s' % self._settings['skip_standard_maps'])
        except NoOptionError:
            self.warning('could not find settings/skipstandardmaps in config file, '
                         'using default: %s' % self._settings['skip_standard_maps'])
        except ValueError, e:
            self.error('could not load settings/skipstandardmaps config value: %s' % e)
            self.debug('using default value (%s) for settings/skipstandardmaps' % self._settings['skip_standard_maps'])

        try:
            level = self.config.get('settings', 'minleveldelete')
            self._settings['min_level_delete'] = self.console.getGroupLevel(level)
            self.debug('loaded settings/minleveldelete: %d' % self._settings['min_level_delete'])
        except NoOptionError:
            self.warning('could not find settings/minleveldelete in config file, '
                         'using default: %s' % self._settings['min_level_delete'])
        except KeyError, e:
            self.error('could not load settings/minleveldelete config value: %s' % e)
            self.debug('using default value (%s) for settings/minleveldelete' % self._settings['min_level_delete'])

    def onStartup(self):
        """\
        Initialize plugin settings
        """
        # register our commands
        if 'commands' in self.config.sections():
            for cmd in self.config.options('commands'):
                level = self.config.get('commands', cmd)
                sp = cmd.split('-')
                alias = None
                if len(sp) == 2:
                    cmd, alias = sp

                func = self.getCmd(cmd)
                if func:
                    self._adminPlugin.registerCommand(self, cmd, level, func, alias)

        # register the events needed
        self.registerEvent(self.console.getEventID('EVT_CLIENT_JUMP_RUN_START'), self.onJumpRunStart)
        self.registerEvent(self.console.getEventID('EVT_CLIENT_JUMP_RUN_STOP'), self.onJumpRunStop)
        self.registerEvent(self.console.getEventID('EVT_CLIENT_JUMP_RUN_CANCEL'), self.onJumpRunCancel)
        self.registerEvent(self.console.getEventID('EVT_CLIENT_TEAM_CHANGE'), self.onTeamChange)
        self.registerEvent(self.console.getEventID('EVT_CLIENT_DISCONNECT'), self.onDisconnect)
        self.registerEvent(self.console.getEventID('EVT_GAME_ROUND_START'), self.onRoundStart)

        # make sure to stop all the demos being recorded or the plugin
        # will go out of sync: will not be able to retrieve demos for players
        # who are already in a jumprun and being recorded (happens on b3 reboots)
        self.console.write('stopserverdemo all')

        # notice plugin startup
        self.debug('plugin started')

    def onDisable(self):
        """\
        Called when the plugin is disabled
        """
        # remove all the demo files
        for cl in self.console.clients.getList():
            if self._settings['demo_record'] and cl.var(self, 'jumprun').value \
                    and cl.var(self, 'demoname').value is not None:

                self.console.write('stopserverdemo %s' % cl.cid)
                self.unLinkDemo(cl.var(self, 'demoname').value)
                cl.setvar(self, 'jumprun', False)

    def onEnable(self):
        """\
        Called when the plugin is enabled
        """
        if self._settings['skip_standard_maps']:
            mapname = self.console.game.mapName
            if mapname in self._standard_maplist:
                self._settings['cycle_count'] += 1
                self.console.say('^7built-in map detected: cycling map ^3%s...' % mapname)
                self.debug('built-in map detected: cycling map %s...' % mapname)
                self.console.write('cyclemap')

    ####################################################################################################################
    ##                                                                                                                ##
    ##   EVENTS                                                                                                       ##
    ##                                                                                                                ##
    ####################################################################################################################

    def onJumpRunStart(self, event):
        """\
        Handle EVT_CLIENT_JUMP_RUN_START
        """
        cl = event.client

        # remove previously started demo, if any
        if self._settings['demo_record'] and cl.var(self, 'jumprun').value \
                and cl.var(self, 'demoname').value is not None:
            self.console.write('stopserverdemo %s' % cl.cid)
            self.unLinkDemo(cl.var(self, 'demoname').value)

        cl.setvar(self, 'jumprun', True)

        # if we are suppose to record a demo of the jumprun
        # start it and store the demo name in the client object
        if self._settings['demo_record']:
            response = self.console.write('startserverdemo %s' % cl.cid)
            r = re.compile(r'''^startserverdemo: recording (?P<name>.+) to (?P<file>.+\.(?:dm_68|urtdemo))$''')
            m = r.match(response)
            if m:
                demoname = m.group('file')
                cl.setvar(self, 'demoname', demoname)
            else:
                # something went wrong while retrieving the demo filename
                self.warning("could not retrieve demo filename for client %s <@%s>: %s" % (cl.name, cl.id, response))
                cl.setvar(self, 'demoname', None)

    def onJumpRunCancel(self, event):
        """\
        Handle EVT_CLIENT_JUMP_RUN_CANCEL
        """
        cl = event.client
        cl.setvar(self, 'jumprun', False)

        if self._settings['demo_record'] and cl.var(self, 'demoname').value is not None:
            # stop the server side demo of this client
            self.console.write('stopserverdemo %s' % cl.cid)
            self.unLinkDemo(cl.var(self, 'demoname').value)

    def onJumpRunStop(self, event):
        """\
        Handle EVT_CLIENT_JUMP_RUN_STOP
        """
        cl = event.client
        if not cl.var(self, 'jumprun').value:
            # double check that we started recording this client correctly:
            # if b3 gets restarted meanwhile a jumprun is being recorded
            # we'll have no 'jumprun' variable in the client object
            return

        # set the jumprun stop flag
        cl.setvar(self, 'jumprun', False)

        if self._settings['demo_record']:
            # stop the server side demo of this client
            self.console.write('stopserverdemo %s' % cl.cid)

        if not self.isPersonalRecord(event):
            cl.message(self.getMessage('personal_record_failed', {'client': cl.name}))
            # if we were recording a server demo, delete the file
            if self._settings['demo_record'] and cl.var(self, 'demoname').value is not None:
                self.unLinkDemo(cl.var(self, 'demoname').value)
                cl.setvar(self, 'demoname', None)

            return

        if self.isMapRecord(event):
            self.console.saybig(self.getMessage('map_record_established', {'client': cl.name}))
            return

        # not a map record but at least is our new personal record
        cl.message(self.getMessage('personal_record_established', {'mapname': self.console.game.mapName}))

    def onRoundStart(self, event):
        """\
        Handle EVT_GAME_ROUND_START
        """
        # remove all the demo files, no matter if this map
        # is going to be cycled because being a non-jump one.
        for cl in self.console.clients.getList():
            if self._settings['demo_record'] and cl.var(self, 'jumprun').value \
                    and cl.var(self, 'demoname').value is not None:

                self.console.write('stopserverdemo %s' % cl.cid)
                self.unLinkDemo(cl.var(self, 'demoname').value)
                cl.setvar(self, 'jumprun', False)

        if self._settings['skip_standard_maps']:
            mapname = self.console.game.mapName
            if mapname in self._standard_maplist:
                # endless loop protection
                if self._settings['cycle_count'] < self._settings['max_cycle_count']:
                    self._settings['cycle_count'] += 1
                    self.debug('built-in map detected: cycling map %s...' % mapname)
                    self.console.write('cyclemap')
                    return

                # we should have cycled this map but too many consequent cyclemap
                # has been issued: this should never happen unless some idiots keep
                # voting for standard maps. However I'll handle this in another plugin
                self.debug('built-in map detected: could not cycle map %s due to endless loop protection...' % mapname)

        self._settings['cycle_count'] = 0
        self._map_data = self.getMapData()

    def onDisconnect(self, event):
        """\
        Handle EVT_CLIENT_DISCONNECT
        """
        cl = event.client
        if self._settings['demo_record'] and cl.var(self, 'jumprun').value \
                and cl.var(self, 'demoname').value is not None:

            # remove the demo file if we got one since the client
            # has disconnected from the server and we don't need it
            self.unLinkDemo(cl.var(self, 'demoname').value)

    def onTeamChange(self, event):
        """\
        Handle EVT_CLIENT_TEAM_CHANGE
        """
        if event.data == b3.TEAM_SPEC:

            cl = event.client
            if self._settings['demo_record'] and cl.var(self, 'jumprun').value \
                    and cl.var(self, 'demoname').value is not None:

                self.console.write('stopserverdemo %s' % cl.cid)
                self.unLinkDemo(cl.var(self, 'demoname').value)
                cl.setvar(self, 'jumprun', False)

    ####################################################################################################################
    ##                                                                                                                ##
    ##   FUNCTIONS                                                                                                    ##
    ##                                                                                                                ##
    ####################################################################################################################

    def getCmd(self, cmd):
        cmd = 'cmd_%s' % cmd
        if hasattr(self, cmd):
            func = getattr(self, cmd)
            return func
        return None

    @staticmethod
    def getDateString(msec):
        """\
        Return a date string ['Thu, 28 Jun 2001']
        """
        gmtime = time.gmtime(msec)
        return time.strftime("%a, %d %b %Y", gmtime)

    @staticmethod
    def getTimeString(msec):
        """\
        Return a time string given it's value
        expressed in milliseconds [H:mm:ss:ms]
        """
        secs = msec / 1000
        msec -= secs * 1000
        mins = secs / 60
        secs -= mins * 60
        hour = mins / 60
        mins -= hour * 60
        return "%01d:%02d:%02d.%03d" % (hour, mins, secs, msec)

    def getMapData(self):
        """\
        Retrieve map info from UrTJumpers API
        """
        mapdata = dict()
        self.debug('contacting http://api.urtjumpers.com to retrieve maps data...')

        try:

            js = urllib2.urlopen('http://api.urtjumpers.com/?key=B3urtjumpersplugin&liste=maps&format=json', timeout=4)
            jd = json.load(js)
            for data in jd:
                mapdata[data['pk3'].lower()] = data

        except (urllib2.URLError, socket.timeout), e:
            self.warning('could not connect to http://api.urtjumpers.com: %s' % e)
            return dict()

        self.debug('retrieved %d maps from http://api.urtjumpers.com' % len(mapdata))
        return mapdata

    def getMapsFromListSoundingLike(self, mapname):
        """\
        Return a list of maps matching the given search key
        The search is performed on the maplist retrieved from the API
        """
        matches = []
        mapname = mapname.lower()

        # check exact match at first
        if mapname in self._map_data.keys():
            matches.append(mapname)
            return matches

        # check for substring match
        for key in self._map_data.keys():
            if mapname in key:
                matches.append(key)

        return matches

    def isPersonalRecord(self, event):
        """\
        Return True if the client established his new personal record
        on this map and on the given way_id, False otherwise. The function will
        also update values in the database and perform some other operations
        if the client made a new personal record
        """
        cl = event.client
        mp = self.console.game.mapName
        wi = int(event.data['way_id'])
        wt = int(event.data['way_time'])
        dm = cl.var(self, 'demoname').value
        dm = dm.replace("'", "\'")
        tm = self.console.time()

        # check if the client made his personal record on this map and this way
        cursor = self.console.storage.query(self._sql['jr1'] % (cl.id, mp, wi))
        if cursor.EOF:
            # no record saved for this client on this map in this way_id
            self.console.storage.query(self._sql['jr7'] % (cl.id, mp, wi, wt, tm, tm, dm))
            self.debug('stored new jumprun for client %s [ mapname : %s | way_id : %d ]' % (cl.id, mp, wi))
            cursor.close()
            return True

        r = cursor.getRow()
        if wt < int(r['way_time']):
            if r['demo'] is not None:
                # remove previous stored demo
                self.unLinkDemo(r['demo'])

            self.console.storage.query(self._sql['jr8'] % (wt, tm, dm, cl.id, mp, wi))
            self.debug('updated jumprun for client %s [ mapname : %s | way_id : %d ]' % (cl.id, mp, wi))
            cursor.close()
            return True

        cursor.close()
        return False

    def isMapRecord(self, event):
        """\
        Return True if the client established a new absolute record
        on this map and on the given way_id, False otherwise
        """
        mp = self.console.game.mapName
        wi = int(event.data['way_id'])
        wt = int(event.data['way_time'])

        # check if the client made an absolute record on this map on the specified way_id
        cursor = self.console.storage.query(self._sql['jr2'] % (mp, wi, wt))

        if cursor.EOF:
            cursor.close()
            return True

        cursor.close()
        return False

    def unLinkDemo(self, filename):
        """\
        Remove a server side demo file
        """
        if self.console.game.fs_game is None:

            try:
                self.console.game.fs_game = self.console.getCvar('fs_game').getString().rstrip('/')
                self.debug('retrieved CVAR <fs_game> : %s' % self.console.game.fs_game)
            except Exception, e:
                self.warning('could not retrieve CVAR <fs_game> : %s' % e)
                self.console.game.fs_game = None
                return

        if self.console.game.fs_basepath is None:

            try:
                self.console.game.fs_basepath = self.console.getCvar('fs_basepath').getString().rstrip('/')
                self.debug('retrieved CVAR <fs_basepath> : %s' % self.console.game.fs_game)
            except Exception, e:
                self.warning('could not retrieve CVAR <fs_basepath> : %s' % e)
                self.console.game.fs_basepath = None

        # construct a possible demo filepath where to search the demo which is going to be deleted
        demopath = self.console.game.fs_basepath + '/' + self.console.game.fs_game + '/' + filename

        if not os.path.isfile(demopath):
            self.debug('could not find demo file at %s' % demopath)
            if self.console.game.fs_homepath is None:

                try:
                    self.console.game.fs_homepath = self.console.getCvar('fs_homepath').getString().rstrip('/')
                    self.debug('retrieved CVAR <fs_homepath> : %s' % self.console.game.fs_game)
                except Exception, e:
                    self.warning('could not retrieve CVAR <fs_homepath> : %s' % e)
                    self.console.game.fs_homepath = None

            # construct a possible demo filepath where to search the demo which is going to be deleted
            demopath = self.console.game.fs_homepath + '/' + self.console.game.fs_game + '/' + filename

        if not os.path.isfile(demopath):
            self.warning('could not delete file %s: file not found!' % demopath)
            return

        try:
            os.unlink(demopath)
            self.debug("removed file: %s" % demopath)
        except os.error, (errno, errstr):
            # when this happen is mostly a problem related to misconfiguration
            self.error("could not remove file: %s | [%d] %s" % (demopath, errno, errstr))

    ####################################################################################################################
    ##                                                                                                                ##
    ##   FUNCTIONS OVERRIDE                                                                                           ##
    ##                                                                                                                ##
    ####################################################################################################################

    def getMapsSoundingLike(self, mapname):
        """\
        Return a valid mapname.
        If no exact match is found, then return close candidates as a list
        """
        wanted_map = mapname.lower()
        supported_maps = self.console.getMaps()

        if self._settings['skip_standard_maps']:
            for m in supported_maps:
                if m in self._standard_maplist:
                    supported_maps.remove(m)

        if wanted_map in supported_maps:
            return wanted_map

        cleaned_supported_maps = dict()
        for map_name in supported_maps:
            cleaned_supported_maps[re.sub("^ut4?_", '', map_name, count=1)] = map_name

        if wanted_map in cleaned_supported_maps:
            return cleaned_supported_maps[wanted_map]

        cleaned_wanted_map = re.sub("^ut4?_", '', wanted_map, count=1)

        matches = [cleaned_supported_maps[match] for match in getStuffSoundingLike(cleaned_wanted_map,
                                                                                   cleaned_supported_maps.keys())]
        if len(matches) == 1:
            # one match, get the map id
            return matches[0]
        else:
            # multiple matches, provide suggestions
            return matches

    ####################################################################################################################
    ##                                                                                                                ##
    ##   COMMANDS                                                                                                     ##
    ##                                                                                                                ##
    ####################################################################################################################

    def cmd_jmprecord(self, data, client, cmd=None):
        """\
        [<client>] [<mapname>] - display the best run(s) of a client on a specific map
        """
        cl = client
        mp = self.console.game.mapName
        ps = self._adminPlugin.parseUserCmd(data)
        if ps:
            cl = self._adminPlugin.findClientPrompt(ps[0], client)
            if not cl:
                return

            if ps[1]:
                mp = self.console.getMapsSoundingLike(ps[1])
                if isinstance(mp, list):
                    client.message('do you mean: ^3%s?' % '^7, ^3'.join(mp[:5]))
                    return

                if not isinstance(mp, basestring):
                    client.message('^7could not find any map matching ^1%s' % ps[1])
                    return

        # get data from the storage layer
        cu = self.console.storage.query(self._sql['jr4'] % (cl.id, mp))

        if cu.EOF:
            cmd.sayLoudOrPM(client, self.getMessage('client_record_unknown', {'client': cl.name, 'mapname': mp}))
            cu.close()
            return

        if cu.rowcount > 1:
            # print a sort of a list header so players will know what's going on
            cmd.sayLoudOrPM(client, self.getMessage('client_record_header', {'client': cl.name, 'mapname': mp}))

        while not cu.EOF:
            rw = cu.getRow()
            wi = rw['way_name'] if rw['way_name'] else rw['way_id']
            tm = self.getTimeString(int(rw['way_time']))
            dt = self.getDateString(int(rw['time_edit']))
            cmd.sayLoudOrPM(client, self.getMessage('client_record_pattern', {'way': wi, 'time': tm, 'date': dt}))
            cu.moveNext()

        cu.close()

    def cmd_jmpmaprecord(self, data, client, cmd=None):
        """\
        [<mapname>] - display map best jump run(s)
        """
        mp = self.console.game.mapName
        if data:
            mp = self.console.getMapsSoundingLike(data)
            if isinstance(mp, list):
                client.message('do you mean: ^3%s?' % '^7, ^3'.join(mp[:5]))
                return

            if not isinstance(mp, basestring):
                client.message('^7could not find any map matching ^1%s' % data)
                return

        # get data from the storage layer
        cu = self.console.storage.query(self._sql['jr3'] % (mp, mp))

        if cu.EOF:
            cmd.sayLoudOrPM(client, self.getMessage('map_record_unknown', {'mapname': mp}))
            cu.close()
            return

        if cu.rowcount > 1:
            # print a sort of a list header so players will know what's going on
            cmd.sayLoudOrPM(client, self.getMessage('map_record_header', {'mapname': mp}))

        while not cu.EOF:
            rw = cu.getRow()
            nm = rw['name']
            wi = rw['way_name'] if rw['way_name'] else rw['way_id']
            tm = self.getTimeString(int(rw['way_time']))
            cmd.sayLoudOrPM(client, self.getMessage('map_record_pattern', {'way': wi, 'client': nm, 'time': tm}))
            cu.moveNext()

        cu.close()

    def cmd_jmptopruns(self, data, client, cmd=None):
        """\
        [<mapname>] - display map top runs
        """
        mp = self.console.game.mapName
        if data:
            mp = self.console.getMapsSoundingLike(data)
            if isinstance(mp, list):
                client.message('do you mean: ^3%s?' % '^7, ^3'.join(mp[:5]))
                return

            if not isinstance(mp, basestring):
                client.message('^7could not find any map matching ^1%s' % data)
                return

        # get the list of paths with jumpruns recorded
        c1 = self.console.storage.query(self._sql['jr5'] % mp)

        if c1.EOF:
            cmd.sayLoudOrPM(client, self.getMessage('map_record_unknown', {'mapname': mp}))
            c1.close()
            return

        if c1.rowcount > 1:
            # print a sort of a list header so players will know what's going on
            cmd.sayLoudOrPM(client, self.getMessage('map_toprun_header', {'mapname': mp}))

        while not c1.EOF:
            pl = 1
            r1 = c1.getRow()
            c2 = self.console.storage.query(self._sql['jr6'] % (mp, int(r1['way_id'])))
            while not c2.EOF:
                r2 = c2.getRow()
                nm = r2['name']
                wi = r2['way_name'] if r2['way_name'] else r2['way_id']
                tm = self.getTimeString(int(r2['way_time']))
                message = self.getMessage('map_toprun_pattern', {'way': wi, 'place': pl, 'client': nm, 'time': tm})
                cmd.sayLoudOrPM(client, message)
                c2.moveNext()
                pl += 1

            c1.moveNext()
            c2.close()

        c1.close()

    def cmd_jmpdelrecord(self, data, client, cmd=None):
        """\
        [<client>] [<mapname>] - delete the best run(s) of a client on a specific map
        """
        cl = client
        mp = self.console.game.mapName
        ps = self._adminPlugin.parseUserCmd(data)
        if ps:
            cl = self._adminPlugin.findClientPrompt(ps[0], client)
            if not cl:
                return

            if ps[1]:
                mp = self.console.getMapsSoundingLike(ps[1])
                if isinstance(mp, list):
                    client.message('do you mean: ^3%s?' % '^7, ^3'.join(mp[:5]))
                    return

                if not isinstance(mp, basestring):
                    client.message('^7could not find any map matching ^1%s' % ps[1])
                    return

        if cl != client:
            if client.maxLevel < self._settings['min_level_delete'] or client.maxLevel < cl.maxLevel:
                cmd.sayLoudOrPM(client, self.getMessage('record_delete_denied', {'client': cl.name}))
                return

        # check for jumpruns being stored in the storage layer
        cu = self.console.storage.query(self._sql['jr4'] % (cl.id, mp))

        if cu.EOF:
            cmd.sayLoudOrPM(client, self.getMessage('client_record_unknown', {'client': cl.name, 'mapname': mp}))
            cu.close()
            return

        num = cu.rowcount
        if self._settings['demo_record']:
            # removing old demo
            while not cu.EOF:
                r = cu.getRow()
                if r['demo'] is not None:
                    self.unLinkDemo(r['demo'])
                cu.moveNext()

        cu.close()

        # removing database records for the given client
        self.console.storage.query(self._sql['jr9'] % (cl.id, mp))
        self.verbose('removed %d record%s for %s[@%s] on %s' % (num, 's' if num > 1 else '', cl.name, cl.id, mp))
        cmd.sayLoudOrPM(client, self.getMessage('client_record_deleted', {'num': num,
                                                                          'plural': 's' if num > 1 else '',
                                                                          'client': cl.name,
                                                                          'mapname': mp}))

    def cmd_jmpmapinfo(self, data, client, cmd=None):
        """\
        [<mapname>] - display map specific informations
        """
        if not self._map_data:
            # retrieve data from the api
            self._map_data = self.getMapData()

        if not self._map_data:
            cmd.sayLoudOrPM(client, self.getMessage('mapinfo_failed'))
            return

        mp = self.console.game.mapName
        if data:
            # search info for the specified map
            match = self.getMapsFromListSoundingLike(data)

            if len(match) == 0:
                client.message('^7could not find any map matching ^1%s' % data)
                return

            if len(match) > 1:
                client.message('do you mean: ^3%s?' % '^7, ^3'.join(match[:5]))
                return

            mp = match[0]

        mp = mp.lower()
        if mp not in self._map_data:
            cmd.sayLoudOrPM(client, self.getMessage('mapinfo_empty', {'mapname': mp}))
            return

        # fetch informations
        n = self._map_data[mp]['nom']
        a = self._map_data[mp]['mapper']
        d = self._map_data[mp]['mdate']
        j = self._map_data[mp]['njump']
        t = int(datetime.datetime.strptime(d, '%Y-%m-%d').strftime('%s'))
        l = int(self._map_data[mp]['level'])
        w = int(self._map_data[mp]['nway'])

        if not a:
            message = self.getMessage('mapinfo_author_unknown', {'mapname': n})
        else:
            message = self.getMessage('mapinfo_author', {'mapname': n, 'author': a})

        # send the computed message
        cmd.sayLoudOrPM(client, message)

        # we always know when the map has been released
        cmd.sayLoudOrPM(client, self.getMessage('mapinfo_released', {'date': self.getDateString(t)}))

        if not j:
            message = self.getMessage('mapinfo_ways', {'way': w, 'plural': 's' if w > 1 else ' only'})
        else:
            message = self.getMessage('mapinfo_jump_ways', {'jumps': j, 'way': w, 'plural': 's' if w > 1 else ''})

        # send the computed message
        cmd.sayLoudOrPM(client, message)

        if l > 0:
            cmd.sayLoudOrPM(client, self.getMessage('mapinfo_level', {'level': l}))

    def cmd_jmpsetway(self, data, client, cmd=None):
        """\
        <way-id> <name> - set a name for the specified way id
        """
        if not data:
            client.message('invalid data, try ^3!^7help jmpsetway')
            return

        # parsing user input
        r = re.compile(r'''^(?P<way_id>\d+) (?P<way_name>.+)$''')
        m = r.match(data)
        if not m:
            client.message('invalid data, try ^3!^7help jmpsetway')
            return

        wi = int(m.group('way_id'))
        wn = m.group('way_name')

        mp = self.console.game.mapName
        cu = self.console.storage.query(self._sql['jw1'] % (mp, wi))

        if cu.EOF:
            # new entry for this way_id on this map
            self.console.storage.query(self._sql['jw2'] % (mp, wi, wn))
            client.message('^7added alias for way ^3%d^7: ^2%s' % (wi, wn))
        else:
            # update old entry with the new name
            self.console.storage.query(self._sql['jw3'] % (wn, mp, wi))
            client.message('^7updated alias for way ^3%d^7: ^2%s' % (wi, wn))

        cu.close()

    ####################################################################################################################
    ##                                                                                                                ##
    ##   COMMANDS OVERRIDE                                                                                            ##
    ##                                                                                                                ##
    ####################################################################################################################

    def cmd_map(self, data, client, cmd=None):
        """\
        <map> - switch current map
        """
        if not data:
            client.message('missing data, try ^3!^7help map')
            return

        match = self.console.getMapsSoundingLike(data)
        if isinstance(match, list):
            client.message('do you mean: ^3%s ?' % '^7, ^3'.join(match[:5]))
            return

        if isinstance(match, basestring):
            self.console.say('^7changing map to ^3%s' % match)
            time.sleep(1)
            self.console.write('map %s' % match)
            return

        # no map found
        client.message('^7could not find any map matching ^1%s' % data)

    def cmd_pasetnextmap(self, data, client=None, cmd=None):
        """\
        <mapname> - Set the nextmap (partial map name works)
        """
        if not data:
            client.message('missing data, try ^3!^7help pasetnextmap')
            return

        match = self.console.getMapsSoundingLike(data)
        if isinstance(match, list):
            client.message('do you mean: ^3%s?' % '^7, ^3'.join(match[:5]))
            return

        if isinstance(match, basestring):
            self.console.setCvar('g_nextmap', match)
            if client:
                client.message('^7nextmap set to ^3%s' % match)

            return

        # no map found
        client.message('^7could not find any map matching ^1%s' % data)

    def cmd_maps(self, data, client=None, cmd=None):
        """\
        List the server map rotation
        """
        if not self._adminPlugin.aquireCmdLock(cmd, client, 60, True):
            client.message('^7do not spam commands')
            return
        
        maps = self.console.getMaps()
        if maps is None:
            client.message('^1ERROR: ^7could not get map list')
            return
    
        if not len(maps):
            cmd.sayLoudOrPM(client, '^7map rotation list is empty')
            return
        
        maplist = []
        for m in maps:
            if self._settings['skip_standard_maps']:
                if m.lower() in self._standard_maplist:
                    continue
            maplist.append(m)

        if not len(maplist):
            cmd.sayLoudOrPM(client, '^7map rotation list is empty')
            return
            
        # display the map rotation
        cmd.sayLoudOrPM(client, '^7map rotation: ^3%s' % '^7, ^3'.join(maplist))
