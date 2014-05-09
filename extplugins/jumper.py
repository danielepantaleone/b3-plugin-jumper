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
# 31/08/2013 - 2.1 - Fenix, jmarc
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
# 23/02/2014 - 2.19 - Fenix
#   - catch also socket.timeout exception while retrieving maps data from urtjumpers api
#   - set client var 'demoname' to None if the regex fails in parsing the server response
#   - do not print in-game jumprun list header if we retrieved just one value
#   - changed some log messages level: just for debugging
# 13/03/2014 - 2.20 - Fenix
#   - updated sql queries not to bother ourselves with character espacing
# 18/03/2014 - 2.21 - Fenix
#   - automatically create necessary database tables
#   - added backward compatibility: support b3 version < 1.10dev
# 24/03/2014 - 2.22 - Fenix
#   - changed back SQL queries to use % notation for string substitution
# 06/05/2014 - 2.23 - Fenix
#   - rewrite dictionary creation as literals
#   - fixed local version of getMapsSoundingLike() not working properly
#   - redid object methods override : using a less brutal approach
#   - added dedicated jumprun code: following a more OOP approach
#   - added sqlite compatibility
#   - added automated tests
#   - minor syntax changes
#

__author__ = 'Fenix'
__version__ = '2.23'

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

try:
    # import the getCmd function
    import b3.functions.getCmd as getCmd
except ImportError:
    # keep backward compatibility
    def getCmd(instance, cmd):
        cmd = 'cmd_%s' % cmd
        if hasattr(instance, cmd):
            func = getattr(instance, cmd)
            return func
        return None

########################################################################################################################
##                                                                                                                    ##
##   JUMPRUN DEDICATED CODE                                                                                           ##
##                                                                                                                    ##
########################################################################################################################

class JumpRun(object):

    p = None

    client = None
    mapname = None
    way_id = None
    demo = None
    way_time = None
    time_add = None
    time_edit = None
    jumprun_id = None

    def __init__(self, plugin, client, mapname, way_id,
                 demo=None, way_time=None, way_name=None,
                 time_add=None, time_edit=None, jumprun_id=None):
        """
        Object constructor
        """
        self.p = plugin
        self.client = client
        self.mapname = mapname
        self.demo = demo
        self.way_id = way_id
        self.way_time = way_time
        self.way_name = way_name
        self.time_add = time_add
        self.time_edit = time_edit
        self.jumprun_id = jumprun_id

    def start(self):
        """
        Perform operations on jumprun start
        """
        self.startdemo()

    def stop(self, way_time):
        """
        Perform operations on jumprun stop
        """
        self.way_time = way_time
        self.time_add = self.p.console.time()
        self.time_edit = self.p.console.time()
        self.stopdemo()

        if not self.is_personal_record():
            self.client.message(self.p.getMessage('personal_record_failed', {'client': self.client.name}))
            self.unlinkdemo()
            return

        if self.is_map_record():
            self.p.console.saybig(self.p.getMessage('map_record_established', {'client': self.client.name}))
            return

        # not a map record but at least is our new personal record
        self.client.message(self.p.getMessage('personal_record_established', {'mapname': self.mapname}))

    def cancel(self):
        """
        Perform operations on jumprun cancel
        """
        if self.p.settings['demo_record'] and self.demo is not None:
            self.stopdemo()
            self.unlinkdemo()

    ####################################################################################################################
    ##                                                                                                                ##
    ##   OTHER METHODS                                                                                                ##
    ##                                                                                                                ##
    ####################################################################################################################

    def startdemo(self):
        """
        Start recording the client's jumprun
        """
        if self.p.settings['demo_record']:
            response = self.p.console.write('startserverdemo %s' % self.client.cid)
            r = re.compile(r'''^startserverdemo: recording (?P<name>.+) to (?P<file>.+\.(?:dm_68|urtdemo))$''')
            m = r.match(response)
            if not m:
                self.p.warning('could not retrieve demo filename for client @%s : %s' % (self.client.id, response))
                self.demo = None
            else:
                self.p.debug('started recording demo for client @%s : %s' % (self.client.id, m.group('file')))
                self.demo = m.group('file')

    def stopdemo(self):
        """
        Stop recording the client's jumprun
        """
        if self.p.settings['demo_record']:
            self.p.console.write('stopserverdemo %s' % self.client.cid)

    def unlinkdemo(self):
        """
        Delete the demo connected to this jumprun
        """
        if not self.p.settings['demo_record']:
            return

        if self.demo is None:
            self.p.debug('not removing jumprun demo for client @%s : no demo has been recorded' % self.client.id)
            return

        if self.p.console.game.fs_game is None:

            try:
                self.p.console.game.fs_game = self.p.console.getCvar('fs_game').getString().rstrip('/')
                self.p.debug('retrieved server cvar <fs_game> : %s' % self.p.console.game.fs_game)
            except AttributeError, e:
                self.p.warning('could not retrieve server cvar <fs_game> : %s' % e)
                self.p.console.game.fs_game = None
                return

        if self.p.console.game.fs_basepath is None:

            try:
                self.p.console.game.fs_basepath = self.p.console.getCvar('fs_basepath').getString().rstrip('/')
                self.p.debug('retrieved server cvar <fs_basepath> : %s' % self.p.console.game.fs_basepath)
            except AttributeError, e:
                self.p.warning('could not retrieve server cvar <fs_basepath> : %s' % e)
                self.p.console.game.fs_basepath = None
                return

        # construct a possible demo filepath where to search the demo which is going to be deleted
        path = self.p.console.game.fs_basepath + '/' + self.p.console.game.fs_game + '/' + self.demo

        if not os.path.isfile(path):
            # could not find a demo under fs_basepath: try fs_homepath
            self.p.debug('could not find jumprun demo file : %s' % path)
            if self.p.console.game.fs_homepath is None:

                try:
                    self.p.console.game.fs_homepath = self.p.console.getCvar('fs_homepath').getString().rstrip('/')
                    self.p.debug('retrieved server cvar <fs_homepath> : %s' % self.p.console.game.fs_basepath)
                except AttributeError, e:
                    self.p.warning('could not retrieve server cvar <fs_homepath> : %s' % e)
                    self.p.console.game.fs_homepath = None
                    return

            # construct a possible demo filepath where to search the demo which is going to be deleted
            path = self.p.console.game.fs_homepath + '/' + self.p.console.game.fs_game + '/' + self.demo

        if not os.path.isfile(path):
            self.p.warning('could not delete jumprun demo file %s : file not found!' % path)
            return

        try:
            os.unlink(path)
            self.p.debug('removed jumprun demo file : %s' % path)
        except os.error, (errno, errstr):
            # when this happen is mostly a problem related to misconfiguration
            self.p.error("could not remove jumprun demo file : %s | [%d] %s" % (path, errno, errstr))

    def is_personal_record(self):
        """
        Return True if the client established his new personal record
        on this map and on the given way_id, False otherwise. The function will
        also update values in the database and perform some other operations
        if the client made a new personal record
        """
        # check if the client made his personal record on this map and this way
        cursor = self.p.console.storage.query(self.p.sql['jr1'] % (self.client.id, self.mapname, self.way_id))
        if cursor.EOF:
            self.insert()
            cursor.close()
            return True

        r = cursor.getRow()
        if self.way_time < int(r['way_time']):
            if r['demo'] is not None:
                jumprun = JumpRun(plugin=self.p,
                                  client=self.client,
                                  mapname=r['mapname'],
                                  way_id=int(r['way_id']),
                                  demo=r['demo'],
                                  way_time=int(r['way_time']),
                                  time_add=int(r['time_add']),
                                  time_edit=int(r['time_edit']),
                                  jumprun_id=int(r['id']))

                # remove previously stored demo
                jumprun.unlinkdemo()
                del jumprun

            self.update()
            cursor.close()
            return True

        cursor.close()
        return False

    def is_map_record(self):
        """
        Return True if the client established a new absolute record
        on this map and on the given way_id, False otherwise
        """
        # check if the client made an absolute record on this map on the specified way_id
        cursor = self.p.console.storage.query(self.p.sql['jr2'] % (self.mapname, self.way_id, self.way_time))
        if cursor.EOF:
            cursor.close()
            return True

        cursor.close()
        return False

    ####################################################################################################################
    ##                                                                                                                ##
    ##   STORAGE METHODS                                                                                              ##
    ##                                                                                                                ##
    ####################################################################################################################

    def insert(self):
        """
        Insert the jumprun in the storage
        """
        demo = self.demo.replace("'", "\'") if self.demo else None
        self.p.console.storage.query(self.p.sql['jr7'] % (self.client.id, self.mapname, self.way_id, self.way_time,
                                                          self.time_add, self.time_edit, demo))
        self.p.debug('stored new jumprun for client @%s [ mapname : %s | way_id : %d ]' % (self.client.id,
                                                                                           self.mapname,
                                                                                           self.way_id))

    def update(self):
        """
        Update the jumprun in the storage
        """
        demo = self.demo.replace("'", "\'") if self.demo else None
        self.p.console.storage.query(self.p.sql['jr8'] % (self.way_time, self.time_add, demo,
                                                          self.client.id, self.mapname, self.way_id))
        self.p.debug('updated jumprun for client @%s [ mapname : %s | way_id : %d ]' % (self.client.id,
                                                                                        self.mapname,
                                                                                        self.way_id))

    def delete(self):
        """
        Delete the jumprun from the storage
        """
        self.unlinkdemo()
        self.p.console.storage.query(self.p.sql['jr9'] % self.jumprun_id)
        self.p.debug('removed jumprun <id:%s> for client @%s' % (self.jumprun_id, self.client.id))

########################################################################################################################
##                                                                                                                    ##
##   PLUGIN IMPLEMENTATION                                                                                            ##
##                                                                                                                    ##
########################################################################################################################

class JumperPlugin(b3.plugin.Plugin):

    adminPlugin = None
    powerAdminUrtPlugin = None

    mapsdata = {}
    standard_maplist = ['ut4_abbey', 'ut4_abbeyctf', 'ut4_algiers', 'ut4_ambush', 'ut4_austria',
                        'ut4_bohemia', 'ut4_casa', 'ut4_cascade', 'ut4_commune', 'ut4_company', 'ut4_crossing',
                        'ut4_docks', 'ut4_dressingroom', 'ut4_eagle', 'ut4_elgin', 'ut4_firingrange',
                        'ut4_ghosttown_rc4', 'ut4_harbortown', 'ut4_herring', 'ut4_horror', 'ut4_kingdom',
                        'ut4_kingpin', 'ut4_mandolin', 'ut4_maya', 'ut4_oildepot', 'ut4_prague', 'ut4_prague_v2',
                        'ut4_raiders', 'ut4_ramelle', 'ut4_ricochet', 'ut4_riyadh', 'ut4_sanc', 'ut4_snoppis',
                        'ut4_suburbs', 'ut4_subway', 'ut4_swim', 'ut4_thingley', 'ut4_tombs', 'ut4_toxic',
                        'ut4_tunis', 'ut4_turnpike', 'ut4_uptown']

    sql = {
        'jr1': """SELECT * FROM jumpruns WHERE client_id = '%s' AND mapname = '%s' AND way_id = '%d'""",
        'jr2': """SELECT * FROM jumpruns WHERE mapname = '%s' AND way_id = '%d' AND way_time < '%d'""",
        'jr3': """SELECT jr.id AS jumprun_id, jr.client_id AS client_id, jr.way_id AS way_id, jr.way_time AS way_time,
                  jr.time_add AS time_add, jr.time_edit AS time_edit, jr.demo AS demo, jw.way_name
                  AS way_name FROM jumpruns AS jr LEFT OUTER JOIN jumpways AS jw ON jr.way_id = jw.way_id
                  AND jr.mapname = jw.mapname WHERE jr.mapname = '%s' AND jr.way_time IN (SELECT MIN(way_time)
                  FROM jumpruns WHERE mapname = '%s' GROUP BY way_id) ORDER BY jr.way_id ASC""",
        'jr4': """SELECT jr.id AS jumprun_id, jr.way_id AS way_id, jr.way_time AS way_time, jr.time_add AS time_add,
                  jr.time_edit AS time_edit, jr.demo AS demo, jw.way_name AS way_name FROM jumpruns AS jr
                  LEFT OUTER JOIN  jumpways AS jw ON  jr.way_id = jw.way_id
                  AND jr.mapname = jw.mapname WHERE jr.client_id = '%s' AND jr.mapname = '%s'
                  ORDER BY jr.way_id ASC""",
        'jr5': """SELECT DISTINCT way_id FROM jumpruns WHERE mapname = '%s' ORDER BY way_id ASC""",
        'jr6': """SELECT jr.id AS jumprun_id, jr.client_id AS client_id, jr.way_id AS way_id, jr.way_time AS way_time,
                  jr.time_add AS time_add, jr.time_edit AS time_edit, jr.demo AS demo, jw.way_name AS way_name
                  FROM jumpruns AS jr LEFT OUTER JOIN jumpways AS jw ON jr.way_id = jw.way_id
                  AND jr.mapname = jw.mapname WHERE jr.mapname = '%s' AND jr.way_id = '%d'
                  ORDER BY jr.way_time ASC LIMIT 3""",
        'jr7': """INSERT INTO jumpruns VALUES (NULL, '%s', '%s', '%d', '%d', '%d', '%d', '%s')""",
        'jr8': """UPDATE jumpruns SET way_time = '%d', time_edit = '%d', demo = '%s' WHERE client_id = '%s'
                  AND mapname = '%s' AND way_id = '%d'""",
        'jr9': """DELETE FROM jumpruns WHERE id = '%d'""",
        'jw1': """SELECT * FROM jumpways WHERE mapname = '%s' AND way_id = '%d'""",
        'jw2': """INSERT INTO jumpways VALUES (NULL, '%s', '%d', '%s')""",
        'jw3': """UPDATE jumpways SET way_name = '%s' WHERE mapname = '%s' AND way_id = '%d'""",
        'my1': """CREATE TABLE IF NOT EXISTS jumpruns (
                      id int(10) unsigned NOT NULL AUTO_INCREMENT,
                      client_id int(10) unsigned NOT NULL,
                      mapname varchar(64) NOT NULL,
                      way_id int(3) NOT NULL,
                      way_time int(10) unsigned NOT NULL,
                      time_add int(10) unsigned NOT NULL,
                      time_edit int(10) unsigned NOT NULL,
                      demo varchar(128) DEFAULT NULL,
                      PRIMARY KEY (id)
                  ) ENGINE=MyISAM DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;""",
        'my2': """CREATE TABLE IF NOT EXISTS jumpways (
                      id int(10) NOT NULL AUTO_INCREMENT,
                      mapname varchar(64) NOT NULL,
                      way_id int(3) NOT NULL,
                      way_name varchar(64) NOT NULL,
                      PRIMARY KEY (id)
                  ) ENGINE=MyISAM DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;""",
        'sq1': """CREATE TABLE IF NOT EXISTS jumpruns (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      client_id INTEGER(10) NOT NULL,
                      mapname VARCHAR(64) NOT NULL,
                      way_id INTEGER(3) NOT NULL,
                      way_time INTEGER(10) NOT NULL,
                      time_add INTEGER(10) NOT NULL,
                      time_edit INTEGER(10) NOT NULL,
                      demo VARCHAR(128) DEFAULT NULL);""",
        'sq2': """CREATE TABLE IF NOT EXISTS jumpways (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  mapname VARCHAR(64) NOT NULL,
                  way_id INTEGER(3) NOT NULL,
                  way_name VARCHAR(64) NOT NULL);"""
    }

    settings = {
        'demo_record': True,
        'skip_standard_maps': True,
        'min_level_delete': 80,
        'max_cycle_count': 5,
        'cycle_count': 0
    }

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
        self.adminPlugin = self.console.getPlugin('admin')
        if not self.adminPlugin:
            self.critical('could not start without admin plugin')
            raise SystemExit(220)

        # get the poweradminurt plugin
        self.powerAdminUrtPlugin = self.console.getPlugin('poweradminurt')
        
        # set default messages
        self._default_messages = {
            'client_record_unknown': '''^7no record found for ^3$client ^7(^4@$id^7) on ^3$mapname''',
            'client_record_deleted': '''^7removed ^3$num ^7record$plural for ^3$client ^7(^4@$id^7) on ^3$mapname''',
            'client_record_header': '''^7listing records for ^3$client ^7(^4@$id^7) on ^3$mapname^7:''',
            'client_record_pattern': '''^7[^3$way^7] ^2$time ^7since ^3$date''',
            'map_record_established': '''^3$client ^7established a new map record^7!''',
            'map_record_unknown': '''^7no record found on ^3$mapname''',
            'map_record_header': '''^7listing map records on ^3$mapname^7:''',
            'map_record_pattern': '''^7[^3$way^7] ^3$client ^7(^4@$id^7) with ^2$time''',
            'map_toprun_header': '''^7listing top runs on ^3$mapname^7:''',
            'map_toprun_pattern': '''^7[^3$way^7] #$place ^3$client ^7(^4@$id^7) with ^2$time''',
            'mapinfo_failed': '''^7could not query remote server to get maps data''',
            'mapinfo_empty': '''^7could not find info for map ^1$mapname''',
            'mapinfo_author_unknown': '''^7I don't know who created ^3$mapname''',
            'mapinfo_author': '''^3$mapname ^7has been created by ^3$author''',
            'mapinfo_released': '''^7it has been released on ^3$date''',
            'mapinfo_ways': '''^7it's composed of ^3$way ^7way$plural''',
            'mapinfo_jump_ways': '''^7it's composed of ^3$jumps ^7jumps and ^3$way ^7way$plural''',
            'mapinfo_level': '''^7level: ^3$level^7/^3100''',
            'personal_record_failed': '''^7you can do better ^3$client^7...try again!''',
            'personal_record_established': '''^7you established a new personal record on ^3$mapname7!''',
            'record_delete_denied': '''^7you can't delete ^1$client ^7(^4@$id^7) records'''
        }
     
    def onLoadConfig(self):
        """
        Load plugin configuration
        """
        try:
            self.settings['demo_record'] = self.config.getboolean('settings', 'demorecord')
            self.debug('loaded settings/demorecord: %s' % self.settings['demo_record'])
        except NoOptionError:
            self.warning('could not find settings/demorecord in config file, '
                         'using default: %s' % self.settings['demo_record'])
        except ValueError, e:
            self.error('could not load settings/demorecord config value: %s' % e)
            self.debug('using default value (%s) for settings/demorecord' % self.settings['demo_record'])

        try:
            self.settings['skip_standard_maps'] = self.config.getboolean('settings', 'skipstandardmaps')
            self.debug('loaded settings/skipstandardmaps: %s' % self.settings['skip_standard_maps'])
        except NoOptionError:
            self.warning('could not find settings/skipstandardmaps in config file, '
                         'using default: %s' % self.settings['skip_standard_maps'])
        except ValueError, e:
            self.error('could not load settings/skipstandardmaps config value: %s' % e)
            self.debug('using default value (%s) for settings/skipstandardmaps' % self.settings['skip_standard_maps'])

        try:
            level = self.config.get('settings', 'minleveldelete')
            self.settings['min_level_delete'] = self.console.getGroupLevel(level)
            self.debug('loaded settings/minleveldelete: %d' % self.settings['min_level_delete'])
        except NoOptionError:
            self.warning('could not find settings/minleveldelete in config file, '
                         'using default: %s' % self.settings['min_level_delete'])
        except KeyError, e:
            self.error('could not load settings/minleveldelete config value: %s' % e)
            self.debug('using default value (%s) for settings/minleveldelete' % self.settings['min_level_delete'])

    def onStartup(self):
        """
        Initialize plugin settings
        """
        # create database tables if needed
        tables = self.console.storage.getTables()

        if not 'jumpruns' in tables:
            if self.console.storage.dsnDict['protocol'] == 'mysql':
                self.console.storage.query(self.sql['my1'])
            else:
                self.console.storage.query(self.sql['sq1'])

        if not 'jumpways' in tables:
            if self.console.storage.dsnDict['protocol'] == 'mysql':
                self.console.storage.query(self.sql['my2'])
            else:
                self.console.storage.query(self.sql['sq2'])

        # register our commands
        if 'commands' in self.config.sections():
            for cmd in self.config.options('commands'):
                level = self.config.get('commands', cmd)
                sp = cmd.split('-')
                alias = None
                if len(sp) == 2:
                    cmd, alias = sp

                func = getCmd(self, cmd)
                if func:
                    self.adminPlugin.registerCommand(self, cmd, level, func, alias)

        try:
            # override !maps command
            self.adminPlugin._commands['maps'].plugin = self
            self.adminPlugin._commands['maps'].func = self.cmd_maps
            self.adminPlugin._commands['maps'].help = self.cmd_maps.__doc__
        except KeyError:
            self.debug('not overriding command !maps: it has not been registered by the Admin plugin')

        try:
            # override !map command
            self.adminPlugin._commands['map'].plugin = self
            self.adminPlugin._commands['map'].func = self.cmd_map
            self.adminPlugin._commands['map'].help = self.cmd_map.__doc__
        except KeyError:
            self.debug('not overriding command !map: it has not been registered by the Admin plugin')
            pass

        if self.powerAdminUrtPlugin:
            try:
                # override !pasetnextmap command
                self.adminPlugin._commands['pasetnextmap'].plugin = self
                self.adminPlugin._commands['pasetnextmap'].func = self.cmd_pasetnextmap
                self.adminPlugin._commands['pasetnextmap'].help = self.cmd_pasetnextmap.__doc__
            except KeyError:
                self.debug('not overriding command !pasetnextmap: it has not been registered by the PowerAdminUrt plugin')
                pass

        try:
            self.registerEvent(self.console.getEventID('EVT_CLIENT_JUMP_RUN_START'), self.onJumpRunStart)
            self.registerEvent(self.console.getEventID('EVT_CLIENT_JUMP_RUN_STOP'), self.onJumpRunStop)
            self.registerEvent(self.console.getEventID('EVT_CLIENT_JUMP_RUN_CANCEL'), self.onJumpRunCancel)
            self.registerEvent(self.console.getEventID('EVT_CLIENT_TEAM_CHANGE'), self.onTeamChange)
            self.registerEvent(self.console.getEventID('EVT_CLIENT_DISCONNECT'), self.onDisconnect)
            self.registerEvent(self.console.getEventID('EVT_GAME_ROUND_START'), self.onRoundStart)
        except TypeError:
            self.registerEvent(self.console.getEventID('EVT_CLIENT_JUMP_RUN_START'))
            self.registerEvent(self.console.getEventID('EVT_CLIENT_JUMP_RUN_STOP'))
            self.registerEvent(self.console.getEventID('EVT_CLIENT_JUMP_RUN_CANCEL'))
            self.registerEvent(self.console.getEventID('EVT_CLIENT_TEAM_CHANGE'))
            self.registerEvent(self.console.getEventID('EVT_CLIENT_DISCONNECT'))
            self.registerEvent(self.console.getEventID('EVT_GAME_ROUND_START'))

        # make sure to stop all the demos being recorded or the plugin
        # will go out of sync: will not be able to retrieve demos for players
        # who are already in a jumprun and being recorded
        self.console.write('stopserverdemo all')

        # notice plugin startup
        self.debug('plugin started')

    def onDisable(self):
        """
        Called when the plugin is disabled
        """
        # stop all the jumpruns
        for client in self.console.clients.getList():
            if client.isvar(self, 'jumprun'):
                jumprun = client.var(self, 'jumprun').value
                jumprun.cancel()
                client.delvar(self, 'jumprun')

    def onEnable(self):
        """
        Called when the plugin is enabled
        """
        if self.settings['skip_standard_maps']:
            mapname = self.console.game.mapName
            if mapname in self.standard_maplist:
                self.console.say('^7built-in map detected: cycling map ^3%s...' % mapname)
                self.debug('built-in map detected: cycling map %s...' % mapname)
                self.settings['cycle_count'] += 1
                self.console.write('cyclemap')

    ####################################################################################################################
    ##                                                                                                                ##
    ##   EVENTS                                                                                                       ##
    ##                                                                                                                ##
    ####################################################################################################################

    def onEvent(self, event):
        """
        Old event system dispatcher
        """
        if event.type == self.console.getEventID('EVT_CLIENT_JUMP_RUN_START'):
            self.onJumpRunStart(event)
        elif event.type == self.console.getEventID('EVT_CLIENT_JUMP_RUN_STOP'):
            self.onJumpRunStop(event)
        elif event.type == self.console.getEventID('EVT_CLIENT_JUMP_RUN_CANCEL'):
            self.onJumpRunCancel(event)
        elif event.type == self.console.getEventID('EVT_CLIENT_TEAM_CHANGE'):
            self.onTeamChange(event)
        elif event.type == self.console.getEventID('EVT_CLIENT_DISCONNECT'):
            self.onDisconnect(event)
        elif event.type == self.console.getEventID('EVT_GAME_ROUND_START'):
            self.onRoundStart(event)

    def onJumpRunStart(self, event):
        """
        Handle EVT_CLIENT_JUMP_RUN_START
        """
        client = event.client
        if client.isvar(self, 'jumprun'):
            jumprun = client.var(self, 'jumprun').value
            jumprun.cancel()
            client.delvar(self, 'jumprun')

        jumprun = JumpRun(plugin=self,
                          client=client,
                          mapname=self.console.game.mapName,
                          way_id=int(event.data['way_id']))

        jumprun.start()
        client.setvar(self, 'jumprun', jumprun)

    def onJumpRunCancel(self, event):
        """
        Handle EVT_CLIENT_JUMP_RUN_CANCEL
        """
        client = event.client
        if client.isvar(self, 'jumprun'):
            jumprun = client.var(self, 'jumprun').value
            jumprun.cancel()
            client.delvar(self, 'jumprun')

    def onJumpRunStop(self, event):
        """
        Handle EVT_CLIENT_JUMP_RUN_STOP
        """
        client = event.client
        if client.isvar(self, 'jumprun'):
            jumprun = client.var(self, 'jumprun').value
            jumprun.stop(int(event.data['way_time']))
            client.delvar(self, 'jumprun')

    def onRoundStart(self, event):
        """
        Handle EVT_GAME_ROUND_START
        """
        # cancel all the jumpruns
        for client in self.console.clients.getList():
            if client.isvar(self, 'jumprun'):
                jumprun = client.var(self, 'jumprun').value
                jumprun.cancel()
                client.delvar(self, 'jumprun')

        if self.settings['skip_standard_maps']:
            mapname = self.console.game.mapName
            if mapname in self.standard_maplist:
                # endless loop protection
                if self.settings['cycle_count'] < self.settings['max_cycle_count']:
                    self.debug('built-in map detected: cycling map %s...' % mapname)
                    self.settings['cycle_count'] += 1
                    self.console.write('cyclemap')
                    return

                # we should have cycled this map but too many consequent cyclemap
                # has been issued: this should never happen unless some idiots keep
                # voting for standard maps. However I'll handle this in another plugin
                self.debug('built-in map detected: could not cycle map %s due to endless loop protection...' % mapname)

        self.settings['cycle_count'] = 0
        self.mapsdata = self.getMapsData()

    def onDisconnect(self, event):
        """
        Handle EVT_CLIENT_DISCONNECT
        """
        client = event.client
        if client.isvar(self, 'jumprun'):
            jumprun = client.var(self, 'jumprun').value
            jumprun.unlinkdemo()
            client.delvar(self, 'jumprun')

    def onTeamChange(self, event):
        """
        Handle EVT_CLIENT_TEAM_CHANGE
        """
        if event.data == b3.TEAM_SPEC:
            client = event.client
            if client.isvar(self, 'jumprun'):
                jumprun = client.var(self, 'jumprun').value
                jumprun.cancel()
                client.delvar(self, 'jumprun')

    ####################################################################################################################
    ##                                                                                                                ##
    ##   OTHER METHODS                                                                                                ##
    ##                                                                                                                ##
    ####################################################################################################################

    @staticmethod
    def getDateString(msec):
        """
        Return a date string ['Thu, 28 Jun 2001']
        """
        gmtime = time.gmtime(msec)
        return time.strftime("%a, %d %b %Y", gmtime)

    @staticmethod
    def getTimeString(msec):
        """
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

    def getMapsData(self):
        """
        Retrieve map info from UrTJumpers API
        """
        mapsdata = {}
        self.debug('contacting http://api.urtjumpers.com to retrieve maps data...')

        try:
            js = urllib2.urlopen('http://api.urtjumpers.com/?key=B3urtjumpersplugin&liste=maps&format=json', timeout=4)
            jd = json.load(js)
            for data in jd:
                mapsdata[data['pk3'].lower()] = data
        except (urllib2.URLError, socket.timeout), e:
            self.warning('could not connect to http://api.urtjumpers.com: %s' % e)
            return {}

        self.debug('retrieved %d maps from http://api.urtjumpers.com' % len(mapsdata))
        return mapsdata

    def getMapsFromListSoundingLike(self, mapname):
        """
        Return a list of maps matching the given search key
        The search is performed on the maplist retrieved from the API
        """
        matches = []
        mapname = mapname.lower()

        # check exact match at first
        if mapname in self.mapsdata.keys():
            matches.append(mapname)
            return matches

        # check for substring match
        for key in self.mapsdata.keys():
            if mapname in key:
                matches.append(key)

        return matches

    ####################################################################################################################
    ##                                                                                                                ##
    ##   STORAGE METHODS                                                                                              ##
    ##                                                                                                                ##
    ####################################################################################################################

    def getMapRecords(self, mapname):
        """
        Return a list of jumprun records for the given map
        """
        cursor = self.console.storage.query(self.sql['jr3'] % (mapname, mapname))
        if cursor.EOF:
            cursor.close()
            return []

        records = []
        while not cursor.EOF:
            r = cursor.getRow()
            client = self.adminPlugin.findClientPrompt('@%s' % r['client_id'])
            if not client:
                self.warning('could not retrieve client @%s but have been found in jumpruns table' % r['client_id'])
                continue

            jumprun = JumpRun(self,
                              client=client,
                              mapname=mapname,
                              way_id=int(r['way_id']),
                              demo=r['demo'],
                              way_time=int(r['way_time']),
                              way_name=r['way_name'],
                              time_add=int(r['time_add']),
                              time_edit=int(r['time_edit']),
                              jumprun_id=int(r['jumprun_id']))

            records.append(jumprun)
            cursor.moveNext()

        cursor.close()
        return records

    def getClientRecords(self, client, mapname):
        """
        Return a list of jumprun records for the given client on the given mapname
        """
        cursor = self.console.storage.query(self.sql['jr4'] % (client.id, mapname))
        if cursor.EOF:
            cursor.close()
            return []

        records = []
        while not cursor.EOF:
            r = cursor.getRow()
            jumprun = JumpRun(self,
                              client=client,
                              mapname=mapname,
                              way_id=int(r['way_id']),
                              demo=r['demo'],
                              way_time=int(r['way_time']),
                              way_name=r['way_name'],
                              time_add=int(r['time_add']),
                              time_edit=int(r['time_edit']),
                              jumprun_id=int(r['jumprun_id']))

            records.append(jumprun)
            cursor.moveNext()

        cursor.close()
        return records

    def getTopRuns(self, mapname):
        """
        Return a list of top jumpruns for the given mapname
        """
        c1 = self.console.storage.query(self.sql['jr5'] % mapname)
        if c1.EOF:
            c1.close()
            return []

        records = []
        while not c1.EOF:
            r1 = c1.getRow()
            c2 = self.console.storage.query(self.sql['jr6'] % (mapname, int(r1['way_id'])))
            while not c2.EOF:
                r2 = c2.getRow()
                client = self.adminPlugin.findClientPrompt('@%s' % r2['client_id'])
                if not client:
                    self.warning('could not retrieve client @%s but have been found in jumpruns table' % r2['client_id'])
                    continue

                jumprun = JumpRun(self,
                                  client=client,
                                  mapname=mapname,
                                  way_id=int(r2['way_id']),
                                  demo=r2['demo'],
                                  way_time=int(r2['way_time']),
                                  way_name=r2['way_name'],
                                  time_add=int(r2['time_add']),
                                  time_edit=int(r2['time_edit']),
                                  jumprun_id=int(r2['jumprun_id']))

                records.append(jumprun)
                c2.moveNext()

            c1.moveNext()
            c2.close()

        c1.close()
        return records

    ####################################################################################################################
    ##                                                                                                                ##
    ##   METHODS OVERRIDE                                                                                             ##
    ##                                                                                                                ##
    ####################################################################################################################

    def getMapsSoundingLike(self, mapname):
        """
        Return a valid mapname.
        If no exact match is found, then return close candidates as a list.
        """
        wanted_map = mapname.lower()
        maps = self.console.getMaps()

        supported_maps = []
        if not self.settings['skip_standard_maps']:
            supported_maps = maps
        else:
            for m in maps:
                if self.settings['skip_standard_maps']:
                    if m.lower() in self.standard_maplist:
                        continue
                supported_maps.append(m)

        if wanted_map in supported_maps:
            return wanted_map

        cleaned_supported_maps = {}
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

        # multiple matches, provide suggestions
        return matches

    ####################################################################################################################
    ##                                                                                                                ##
    ##   COMMANDS                                                                                                     ##
    ##                                                                                                                ##
    ####################################################################################################################

    def cmd_jmprecord(self, data, client, cmd=None):
        """
        [<client>] [<mapname>] - display the best run(s) of a client on a specific map
        """
        cl = client
        mp = self.console.game.mapName
        ps = self.adminPlugin.parseUserCmd(data)
        if ps:
            cl = self.adminPlugin.findClientPrompt(ps[0], client)
            if not cl:
                # a list of closest matches will be displayed
                # to the client so he can retry with a more specific handle
                return

            if ps[1]:
                mp = self.console.getMapsSoundingLike(ps[1])
                if isinstance(mp, list):
                    client.message('do you mean: ^3%s?' % '^7, ^3'.join(mp[:5]))
                    return

                if not isinstance(mp, basestring):
                    client.message('^7could not find any map matching ^1%s' % ps[1])
                    return

        # get the records of the client
        records = self.getClientRecords(cl, mp)
        if len(records) == 0:
            cmd.sayLoudOrPM(client, self.getMessage('client_record_unknown', {'client': cl.name,
                                                                              'id': cl.id,
                                                                              'mapname': mp}))
            return

        if len(records) > 1:
            # print a sort of a list header so players will know what's going on
            cmd.sayLoudOrPM(client, self.getMessage('client_record_header', {'client': cl.name,
                                                                             'id': cl.id,
                                                                             'mapname': mp}))

        for jumprun in records:
            wi = jumprun.way_name if jumprun.way_name else str(jumprun.way_id)
            tm = self.getTimeString(jumprun.way_time)
            dt = self.getDateString(jumprun.time_edit)
            cmd.sayLoudOrPM(client, self.getMessage('client_record_pattern', {'way': wi, 'time': tm, 'date': dt}))

    def cmd_jmpmaprecord(self, data, client, cmd=None):
        """
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

        # get the map records
        records = self.getMapRecords(mp)
        if len(records) == 0:
            cmd.sayLoudOrPM(client, self.getMessage('map_record_unknown', {'mapname': mp}))
            return

        if len(records) > 1:
            # print a sort of a list header so players will know what's going on
            cmd.sayLoudOrPM(client, self.getMessage('map_record_header', {'mapname': mp}))

        for jumprun in records:
            wi = jumprun.way_name if jumprun.way_name else str(jumprun.way_id)
            tm = self.getTimeString(jumprun.way_time)
            cmd.sayLoudOrPM(client, self.getMessage('map_record_pattern', {'way': wi,
                                                                           'client': jumprun.client.name,
                                                                           'id':  jumprun.client.id,
                                                                           'time': tm}))

    def cmd_jmptopruns(self, data, client, cmd=None):
        """
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

        # get the top runs
        records = self.getTopRuns(mp)
        if len(records) == 0:
            cmd.sayLoudOrPM(client, self.getMessage('map_record_unknown', {'mapname': mp}))
            return

        if len(records) > 1:
            # print a sort of a list header so players will know what's going on
            cmd.sayLoudOrPM(client, self.getMessage('map_toprun_header', {'mapname': mp}))

        place = 0
        last_way_id = None
        for jumprun in records:

            # if the way id changed, reset the place counter
            if last_way_id and last_way_id != jumprun.way_id:
                place = 0

            place += 1
            last_way_id = jumprun.way_id
            way_id = jumprun.way_name if jumprun.way_name else str(jumprun.way_id)
            way_time = self.getTimeString(jumprun.way_time)
            cmd.sayLoudOrPM(client, self.getMessage('map_toprun_pattern', {'way': way_id,
                                                                           'place': place,
                                                                           'client': jumprun.client.name,
                                                                           'id': jumprun.client.id,
                                                                           'time': way_time}))

    def cmd_jmpdelrecord(self, data, client, cmd=None):
        """
        [<client>] [<mapname>] - delete the best run(s) of a client on a specific map
        """
        cl = client
        mp = self.console.game.mapName
        ps = self.adminPlugin.parseUserCmd(data)
        if ps:
            cl = self.adminPlugin.findClientPrompt(ps[0], client)
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
            if client.maxLevel < self.settings['min_level_delete'] or client.maxLevel < cl.maxLevel:
                cmd.sayLoudOrPM(client, self.getMessage('record_delete_denied', {'client': cl.name, 'id': cl.id}))
                return

        records = self.getClientRecords(cl, mp)
        if len(records) == 0:
            cmd.sayLoudOrPM(client, self.getMessage('client_record_unknown', {'client': cl.name, 'id': cl.id, 'mapname': mp}))
            return

        for jumprun in records:
            jumprun.delete()

        num = len(records)
        self.verbose('removed %d record%s for client @%s on %s' % (num, 's' if num > 1 else '', cl.id, mp))
        cmd.sayLoudOrPM(client, self.getMessage('client_record_deleted', {'num': num,
                                                                          'plural': 's' if num > 1 else '',
                                                                          'client': cl.name,
                                                                          'id': cl.id,
                                                                          'mapname': mp}))

    def cmd_jmpmapinfo(self, data, client, cmd=None):
        """
        [<mapname>] - display map specific informations
        """
        if not self.mapsdata:
            # retrieve data from the api
            self.mapsdata = self.getMapsData()

        if not self.mapsdata:
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
        if mp not in self.mapsdata:
            cmd.sayLoudOrPM(client, self.getMessage('mapinfo_empty', {'mapname': mp}))
            return

        # fetch informations
        n = self.mapsdata[mp]['nom']
        a = self.mapsdata[mp]['mapper']
        d = self.mapsdata[mp]['mdate']
        j = self.mapsdata[mp]['njump']
        t = int(datetime.datetime.strptime(d, '%Y-%m-%d').strftime('%s'))
        l = int(self.mapsdata[mp]['level'])
        w = int(self.mapsdata[mp]['nway'])

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
        """
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

        way_id = int(m.group('way_id'))
        way_name = m.group('way_name')

        mapname = self.console.game.mapName
        cursor = self.console.storage.query(self.sql['jw1'] % (mapname, way_id))

        if cursor.EOF:
            # new entry for this way_id on this map
            self.console.storage.query(self.sql['jw2'] % (mapname, way_id, way_name))
            client.message('^7added alias for way ^3%d^7: ^2%s' % (way_id, way_name))
        else:
            # update old entry with the new name
            self.console.storage.query(self.sql['jw3'] % (way_name, mapname, way_id))
            client.message('^7updated alias for way ^3%d^7: ^2%s' % (way_id, way_name))

        cursor.close()

    ####################################################################################################################
    ##                                                                                                                ##
    ##   COMMANDS OVERRIDE                                                                                            ##
    ##                                                                                                                ##
    ####################################################################################################################

    def cmd_map(self, data, client, cmd=None):
        """
        <map> - switch current map
        """
        if not data:
            client.message('missing data, try ^3!^7help map')
            return

        match = self.getMapsSoundingLike(data)
        if isinstance(match, list):
            client.message('do you mean: ^3%s?' % '^7, ^3'.join(match[:5]))
            return

        if isinstance(match, basestring):
            cmd.sayLoudOrPM(client, '^7changing map to ^3%s' % match)
            time.sleep(1)
            self.console.write('map %s' % match)
            return

        # no map found
        client.message('^7could not find any map matching ^1%s' % data)

    def cmd_pasetnextmap(self, data, client=None, cmd=None):
        """
        <mapname> - Set the nextmap (partial map name works)
        """
        if not data:
            client.message('missing data, try ^3!^7help pasetnextmap')
            return

        match = self.getMapsSoundingLike(data)
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
        """
        List the server map rotation
        """
        if not self.adminPlugin.aquireCmdLock(cmd, client, 60, True):
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
            if self.settings['skip_standard_maps']:
                if m.lower() in self.standard_maplist:
                    continue
            maplist.append(m)

        if not len(maplist):
            cmd.sayLoudOrPM(client, '^7map rotation list is empty')
            return
            
        # display the map rotation
        cmd.sayLoudOrPM(client, '^7map rotation: ^3%s' % '^7, ^3'.join(maplist))