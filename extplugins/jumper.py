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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

__author__ = 'Fenix - http://www.urbanterror.info'
__version__ = '2.5.1'

import b3
import b3.plugin
import b3.events
import ConfigParser
import urllib2
import json
import time
import datetime
import os
import re


class JumperPlugin(b3.plugin.Plugin):

    _adminPlugin = None

    _mapData = {}
    _demoRecord = False
    _minLevelDelete = 80

    _demoRecordRegEx = re.compile(r"""^startserverdemo: recording (?P<name>.+) to (?P<file>.+\.(?:dm_68|urtdemo))$""")
    _setWayNameRegEx = re.compile(r"""^(?P<way_id>\d+) (?P<way_name>.+)$""");

    _messages = dict(
        map_record_established="""^7%(client)s established a new ^1map record^7!""",
        personal_record_established="""^7You established a new ^3personal record ^7on this map!""",
        client_record_unknown="""^7No record found for %(client)s on ^3%(mapname)s""",
        client_record_header="""^7Listing record%(plural)s for %(client)s on ^3%(mapname)s^7:""",
        client_record_pattern="""^7[^3%(way)s^7] ^2(time)%s ^7since ^3%(date)s""",
        map_record_unknown="""^7No record found on ^3%(mapname)s""",
        map_record_header="""^7Listing record%(plural)s on ^3%(mapname)s^7:""",
        map_record_pattern="""^7[^3%(way)s^7] %(client)s with ^2%(time)s""",
        record_delete_denied="""^7You can't delete ^1%(client)s ^7record(s)""",
        mapinfo_failed="""^7Could not fetch data from the API""",
        mapinfo_empty="""^7Could not find info for map ^1%(mapname)s""",
        mapinfo_author_unknown="""^3I don't know who created ^7%(mapname)s""",
        mapinfo_author="""^7%(mapname)s ^3has been created by ^7%(author)s""",
        mapinfo_released="""^3It has been released on ^7%(date)s""",
        mapinfo_ways="""^3It's composed of ^7%(way)d ^3way%(plural)s""",
        mapinfo_jump_ways="""^3It's composed of ^7%(jumps)s ^3jumps and ^7%(way)d ^3way%(plural)s""",
        mapinfo_level="""^3Level: ^7%(level)d^3/^7100""",
    )

    _sql = dict(
        jr1="""SELECT * FROM `jumpruns`
                        WHERE `client_id` = '%s'
                        AND `mapname` = '%s'
                        AND `way_id` = '%d'""",

            jr2="""SELECT * FROM `jumpruns`
                            WHERE `mapname` = '%s'
                            AND `way_id` = '%d'
                            AND `way_time` < '%d'""",

            jr3="""SELECT `cl`.`name` AS `name`,
                          `jr`.`way_id` AS `way_id`,
                          `jr`.`way_time` AS `way_time`,
                          `jr`.`time_edit` AS `time_edit`,
                          `jw`.`way_name` AS `way_name`
                          FROM `clients` AS `cl`
                          INNER JOIN `jumpruns` AS `jr`
                          ON `cl`.`id` = `jr`.`client_id`
                          LEFT OUTER JOIN `jumpways` AS `jw`
                          ON `jr`.`way_id` =  `jw`.`way_id`
                          AND `jr`.`mapname` =  `jw`.`mapname`
                          WHERE `jr`.`mapname` = '%s'
                          AND `jr`.`way_time`
                          IN (
                              SELECT MIN(`way_time`)
                              FROM `jumpruns`
                              WHERE `mapname` = '%s'
                              GROUP BY  `way_id`)
                          ORDER BY  `jr`.`way_id` ASC """,

            jr4="""SELECT `jr`.`way_id` AS `way_id`,
                          `jr`.`way_time` AS `way_time`,
                          `jr`.`time_edit` AS `time_edit`,
                          `jr`.`demo` AS `demo`,
                          `jw`.`way_name` AS `way_name`
                          FROM  `jumpruns` AS `jr`
                          LEFT OUTER JOIN  `jumpways` AS `jw`
                          ON  `jr`.`way_id` = `jw`.`way_id`
                          AND `jr`.`mapname` = `jw`.`mapname`
                          WHERE `jr`.`client_id` =  '%s'
                          AND `jr`.`mapname` = '%s'
                          ORDER BY `jr`.`way_id` ASC""",

            jr5="""INSERT INTO `jumpruns` VALUES (NULL, '%s', '%s', '%d', '%d', '%d', '%d', '%s')""",

            jr6="""UPDATE `jumpruns` SET `way_time` = '%d', `time_edit` = '%d', `demo` = '%s'
                                     WHERE `client_id` = '%s'
                                     AND `mapname` = '%s'
                                     AND `way_id` = '%d'""",

            jr7="""DELETE FROM `jumpruns`
                          WHERE `client_id` = '%s'
                          AND `mapname` = '%s'""",

            jw1="""SELECT * FROM `jumpways`
                            WHERE `mapname` = '%s'
                            AND `way_id` = '%d'""",

            jw2="""INSERT INTO `jumpways` VALUES (NULL, '%s', '%d', '%s')""",

            jw3="""UPDATE `jumpways` SET `way_name` = '%s'
                                     WHERE `mapname` = '%s'
                                     AND `way_id` = '%d'""",)

    def __init__(self, console, config=None):
        """
        Build the plugin object
        """
        b3.plugin.Plugin.__init__(self, console, config)
        if self.console.gameName != 'iourt42':
            self.critical("unsupported game : %s" % self.console.gameName)
            raise SystemExit(220)

    def onLoadConfig(self):
        """\
        Load plugin configuration
        """
        try:
            self._demoRecord = self.config.getboolean('settings', 'demorecord')
            self.debug('loaded automatic demo record: %r' % self._demoRecord)
        except ConfigParser.NoOptionError:
            self.warning('could not find settings/demorecord in config file, using default: %s' % self._demoRecord)
        except ValueError, e:
            self.error('could not load settings/demorecord config value: %s' % e)
            self.debug('using default value (%s) for settings/demorecord' % self._demoRecord)

        try:
            self._minLevelDelete = self.config.getint('settings', 'minleveldelete')
            self.debug('loaded minimum level delete: %d' % self._minLevelDelete)
        except ConfigParser.NoOptionError:
            self.warning('could not find settings/minleveldelete in config file, using default: %s' % self._minLevelDelete)
        except ValueError, e:
            self.error('could not load settings/minleveldelete config value: %s' % e)
            self.debug('using default value (%s) for settings/minleveldelete' % self._minLevelDelete)

        # load in-game messages
        for msg in self.config.options('messages'):
            self._message[msg] = self.config.getint('settings', msg)
            self.debug('loaded message [%s] : %s' % (msg, self._messages[msg]))

    def onStartup(self):
        """\
        Initialize plugin settings
        """
        # get the admin plugin
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            self.error('could not find admin plugin')
            return False

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
        self.registerEvent(b3.events.EVT_CLIENT_JUMP_RUN_START)
        self.registerEvent(b3.events.EVT_CLIENT_JUMP_RUN_STOP)
        self.registerEvent(b3.events.EVT_CLIENT_JUMP_RUN_CANCEL)
        self.registerEvent(b3.events.EVT_CLIENT_TEAM_CHANGE)
        self.registerEvent(b3.events.EVT_CLIENT_DISCONNECT)
        self.registerEvent(b3.events.EVT_GAME_ROUND_START)

        # notice plugin startup
        self.debug('plugin started')

    # ######################################################################################### #
    # ##################################### HANDLE EVENTS ##################################### #        
    # ######################################################################################### #    

    def onEvent(self, event):
        """\
        Handle intercepted events
        """
        if event.type == b3.events.EVT_CLIENT_JUMP_RUN_START:
            self.onJumpRunStart(event)
        elif event.type == b3.events.EVT_CLIENT_JUMP_RUN_CANCEL:
            self.onJumpRunCancel(event)
        elif event.type == b3.events.EVT_CLIENT_JUMP_RUN_STOP:
            self.onJumpRunStop(event)
        elif event.type == b3.events.EVT_CLIENT_DISCONNECT:
            self.onDisconnect(event)
        elif event.type == b3.events.EVT_CLIENT_TEAM_CHANGE:
            self.onTeamChange(event)
        elif event.type == b3.events.EVT_GAME_ROUND_START:
            self.onRoundStart()

    # ######################################################################################### #
    # ####################################### FUNCTIONS ####################################### #
    # ######################################################################################### #

    def getCmd(self, cmd):
        cmd = 'cmd_%s' % cmd
        if hasattr(self, cmd):
            func = getattr(self, cmd)
            return func
        return None

    def getDateString(self, msec):
        """\
        Return a date string ['Thu, 28 Jun 2001']
        """
        gmtime = time.gmtime(msec)
        return time.strftime("%a, %d %b %Y", gmtime)

    def getTimeString(self, msec):
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
        mapdata = {}
        self.debug("contacting http://api.urtjumpers.com to retrieve necessary data...")

        try:

            js = urllib2.urlopen('http://api.urtjumpers.com/?key=B3urtjumpersplugin&liste=maps&format=json', timeout=4)
            jd = json.load(js)
            for data in jd:
                mapdata[data['pk3'].lower()] = data

        except urllib2.URLError, e:
            self.warning("could not connect to http://api.urtjumpers.com: %s" % e)
            return {}

        self.debug("retrieved %d maps from http://api.urtjumpers.com" % len(mapdata))
        return mapdata

    def getMapsFromListSoundingLike(self, mapname):
        """\
        Return a list of maps matching the given search key
        The search is performed on the maplist retrieved from the API
        """
        matches = []
        mapname = mapname.lower()

        # check exact match at first
        if mapname in self._mapData.keys():
            matches.append(mapname)
            return matches

        # check for substring match
        for key in self._mapData.keys():
            if mapname in key:
                matches.append(key)

        return matches

    def isPersonalRecord(self, event):
        """
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
            self.console.storage.query(self._sql['jr5'] % (cl.id, mp, wi, wt, tm, tm, dm))
            self.verbose("stored new jumprun for client %s [ mapname : %s | way_id : %d ]" % (cl.id, mp, wi))
            cursor.close()
            return True

        r = cursor.getRow()
        if wt < int(r['way_time']):
            if r['demo'] is not None:
                # remove previous stored demo
                self.unLinkDemo(r['demo'])

            self.console.storage.query(self._sql['jr6'] % (wt, tm, dm, cl.id, mp, wi))
            self.verbose("updated jumprun for client %s [ mapname : %s | way_id : %d ]" % (cl.id, mp, wi))
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
                self.debug('retrieved CVAR [fs_game] : %s' % self.console.game.fs_game)
            except Exception, e:
                self.warning('could not retrieve CVAR [fs_game] : %s' % e)
                self.console.game.fs_game = None
                return

        if self.console.game.fs_basepath is None:

            try:
                self.console.game.fs_basepath = self.console.getCvar('fs_basepath').getString().rstrip('/')
                self.debug('retrieved CVAR [fs_basepath] : %s' % self.console.game.fs_game)
            except Exception, e:
                self.warning('could not retrieve CVAR [fs_basepath] : %s' % e)
                self.console.game.fs_basepath = None

        # construct a possible demo filepath where to search the demo which is going to be deleted
        demopath = self.console.game.fs_basepath + '/' + self.console.game.fs_game + '/' + filename

        if not os.path.isfile(demopath):
            self.debug('could not find demo file at %s' % demopath)
            if self.console.game.fs_homepath is None:

                try:
                    self.console.game.fs_homepath = self.console.getCvar('fs_homepath').getString().rstrip('/')
                    self.debug('retrieved CVAR [fs_homepath] : %s' % self.console.game.fs_game)
                except Exception, e:
                    self.warning('could not retrieve CVAR [fs_homepath] : %s' % e)
                    self.console.game.fs_homepath = None

            # construct a possible demo filepath where to search the demo which is going to be deleted
            demopath = self.console.game.fs_homepath + '/' + self.console.game.fs_game + '/' + filename

        if not os.path.isfile(demopath):
            self.debug('could not find demo file at %s' % demopath)
            self.error('could not delete demo file: file not found!')
            return

        try:
            os.unlink(demopath)
            self.debug("removed file: %s" % demopath)
        except os.error, (errno, errstr):
            # when this happen is mostly a problem related to user permissions
            # log it as an error so the user will notice and change is configuration
            self.error("could not remove file: %s | [%d] %s" % (demopath, errno, errstr))

    def onJumpRunStart(self, event):
        """\
        Handle EVT_CLIENT_JUMP_RUN_START
        """
        cl = event.client

        if self._demoRecord and cl.var(self, 'jumprun').value \
                and cl.var(self, 'demoname').value is not None:

            self.console.write('stopserverdemo %s' % (cl.cid))
            self.unLinkDemo(cl.var(self, 'demoname').value)

        cl.setvar(self, 'jumprun', True)

        # if we are suppose to record a demo of the jumprun
        # start it and store the demo name in the client object
        if self._demoRecord:
            response = self.console.write('startserverdemo %s' % cl.cid)
            match = self._demoRecordRegEx.match(response)
            if match:
                demoname = match.group('file')
                cl.setvar(self, 'demoname', demoname)
            else:
                # something went wrong while retrieving the demo filename
                self.warning("could not retrieve demo filename for client %s <@%s>: %s" % (cl.name, cl.id, response))

    def onJumpRunCancel(self, event):
        """\
        Handle EVT_CLIENT_JUMP_RUN_CANCEL
        """
        cl = event.client
        cl.setvar(self, 'jumprun', False)

        if self._demoRecord and cl.var(self, 'demoname').value is not None:
            # stop the server side demo of this client
            self.console.write('stopserverdemo %s' % (cl.cid))
            self.unLinkDemo(cl.var(self, 'demoname').value)

    def onJumpRunStop(self, event):
        """\
        Handle EVT_CLIENT_JUMP_RUN_STOP
        """
        cl = event.client
        cl.setvar(self, 'jumprun', False)

        if self._demoRecord:
            # stop the server side demo of this client
            self.console.write('stopserverdemo %s' % cl.cid)

        if not self.isPersonalRecord(event):
            cl.message('^7You can do better! Try again!')
            # if we were recording a server demo, delete the file
            if self._demoRecord and cl.var(self, 'demoname').value is not None:
                self.unLinkDemo(cl.var(self, 'demoname').value)
                cl.setvar(self, 'demoname', None)

            return

        mp = self.console.game.mapName
        wi = int(event.data['way_id'])
        tm = self.getTimeString(int(event.data['way_time']))

        if self.isMapRecord(event):
            # we established a new map record...gg ^_^
            self.console.say(self._messages['map_record_established'] % {'client': cl.name})
            return

        # not a map record but at least is our new personal record
        cl.message(self._messages['personal_record_established'])

    def onRoundStart(self):
        """\
        Handle EVT_GAME_ROUND_START
        """
        for cl in self.console.clients.getList():
            if self._demoRecord and cl.var(self, 'jumprun').value \
                    and cl.var(self, 'demoname').value is not None:

                self.console.write('stopserverdemo %s' % cl.cid)
                self.unLinkDemo(cl.var(self, 'demoname').value)
                cl.setvar(self, 'jumprun', False)

        # refresh map informations
        self._mapData = self.getMapInfo()

    def onDisconnect(self, event):
        """\
        Handle EVT_CLIENT_DISCONNECT
        """
        cl = event.client
        if self._demoRecord and cl.var(self, 'jumprun').value \
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
            if self._demoRecord and cl.var(self, 'jumprun').value \
                    and cl.var(self, 'demoname').value is not None:

                self.console.write('stopserverdemo %s' % cl.cid)
                self.unLinkDemo(cl.var(self, 'demoname').value)
                cl.setvar(self, 'jumprun', False)

    # ######################################################################################### #
    # ######################################## COMMANDS ####################################### #        
    # ######################################################################################### #

    def cmd_jmprecord(self, data, client, cmd=None):
        """\
        [<client>] - Display the record(s) of a client on the current map
        """
        if not data:
            cl = client
        else:
            cl = self._adminPlugin.findClientPrompt(data, client)
            if not cl:
                return

        mp = self.console.game.mapName
        cu = self.console.storage.query(self._sql['jr4'] % (cl.id, mp))

        if cu.EOF:
            cmd.sayLoudOrPM(client, self._messages['client_record_unknown'] % {'client': cl.name, 'mapname': mp})
            cu.close()
            return

        # print a sort of a list header so players will know what's going on
        cmd.sayLoudOrPM(client, self._messages['client_record_header'] % {'plural': 's' if cu.rowcount > 1 else '',
                                                                          'client': cl.name,
                                                                          'mapname': mp})

        while not cu.EOF:
            rw = cu.getRow()
            wi = rw['way_name'] if rw['way_name'] else rw['way_id']
            tm = self.getTimeString(int(rw['way_time']))
            dt = self.getDateString(int(rw['time_edit']))
            cmd.sayLoudOrPM(client, self._messages['client_record_pattern'] % {'way': wi, 'time': tm, 'date': dt})
            cu.moveNext()

        cu.close()

    def cmd_jmpmaprecord(self, data, client, cmd=None):
        """\
        Display the current map record(s)
        """
        mp = self.console.game.mapName
        cu = self.console.storage.query(self._sql['jr3'] % (mp, mp))

        if cu.EOF:
            cmd.sayLoudOrPM(client, self._messages['map_record_unknown'] % {'mapname': mp})
            cu.close()
            return

        # print a sort of a list header so players will know what's going on
        cmd.sayLoudOrPM(client, self._messages['map_record_header'] % {'plural': 's' if cu.rowcount > 1 else '',
                                                                       'mapname': mp})

        while not cu.EOF:
            rw = cu.getRow()
            nm = rw['name']
            wi = rw['way_name'] if rw['way_name'] else rw['way_id']
            tm = self.getTimeString(int(rw['way_time']))
            cmd.sayLoudOrPM(client, self._messages['map_record_pattern'] % {'way': wi, 'client': nm, 'time': tm})
            cu.moveNext()

        cu.close()

    def cmd_jmpdelrecord(self, data, client, cmd=None):
        """\
        [<client>] - Remove current map client record(s) from the storage
        """
        if not data:
            cl = client
        else:
            cl = self._adminPlugin.findClientPrompt(data, client)
            if not cl:
                return

        if cl != client:
            if client.maxLevel < self._minLevelDelete or client.maxLevel < cl.maxLevel:
                client.message(self._messages['record_delete_denied'] % {'client': cl.name})
                return

        mp = self.console.game.mapName
        cu = self.console.storage.query(self._sql['jr4'] % (cl.id, mp))

        if cu.EOF:
            client.message(self._messages['client_record_unknown'] % (cl.name, mp))
            cu.close()
            return

        num = cu.rowcount
        if self._demoRecord:
            # removing old demo files if we were supposed to
            # auto record and if the demo has been recorded
            while not cu.EOF:
                r = cu.getRow()
                if r['demo'] is not None:
                    self.unLinkDemo(r['demo'])
                cu.moveNext()

        cu.close()

        # removing database tuples for the given client
        self.console.storage.query(self._sql['jr7'] % (cl.id, mp))
        self.verbose('removed %d record%s for %s[@%s] on %s' % (num, 's' if num > 1 else '', cl.name, cl.id, mp))
        client.message('^7Removed ^1%d ^7record%s for %s on ^3%s' % (num, 's' if num > 1 else '', cl.name, mp))

    def cmd_jmpmapinfo(self, data, client, cmd=None):
        """\
        [<mapname>] Display map specific informations
        """
        if not self._mapData:
            # retrieve data from the api
            self._mapData = self.getMapData()

        if not self._mapData:
            cmd.sayLoudOrPM(client, self._messages['mapinfo_failed'])
            return

        if not data:
            # search info for the current map
            mp = self.console.game.mapName
        else:
            # search info for the specified map
            matches = self.getMapsFromListSoundingLike(data)

            if len(matches) == 0:
                client.message('Could not find any map matching ^1%s' % data)
                return

            if len(matches) > 1:
                client.message('Do you mean: %s?' % ', '.join(matches[:5]))
                return

            mp = matches[0]

        mp = mp.lower()

        if mp not in self._mapData:
            cmd.sayLoudOrPM(client, self._messages['mapinfo_empty'] % {'mapname': mp})
            return

        # fetch informations
        n = self._mapData[mp]['nom']
        a = self._mapData[mp]['mapper']
        d = self._mapData[mp]['mdate']
        j = self._mapData[mp]['njump']
        t = int(datetime.datetime.strptime(d, '%Y-%m-%d').strftime('%s'))
        l = int(self._mapData[mp]['level'])
        w = int(self._mapData[mp]['nway'])

        if not a:
            cmd.sayLoudOrPM(client, self._messages['mapinfo_author_unknown'] % {'mapname': n})
        else:
            cmd.sayLoudOrPM(client, self._messages['mapinfo_author'] % {'mapname': n, 'author': a})

        # we always know when the map has been released
        cmd.sayLoudOrPM(client, self._messages['mapinfo_released'] % {'date': self.getDateString(t)})

        if not j:
            cmd.sayLoudOrPM(client, self._messages['mapinfo_ways'] % {'way': w, 'plural': 's' if w > 1 else ' only'})
        else:
            cmd.sayLoudOrPM(client, self._messages['mapinfo_jump_ways'] % {'jumps': j,
                                                                           'way': w,
                                                                           'plural': 's' if w > 1 else ''})

        if l > 0:
            cmd.sayLoudOrPM(client, self._messages['mapinfo_level'] % {'level': l})

    def cmd_jmpsetway(self, data, client, cmd=None):
        """\
        <way-id> <name> - Set a name for the speficied way id
        """
        if not data:
            client.message('Invalid data. Try ^3!^7help jmpsetway')
            return

        # parsing user input
        match = self._setWayNameRegEx.match(data)
        if not match:
            client.message('Invalid data. Try ^3!^7help jmpsetway')
            return

        wi = int(match.group('way_id'))
        wn = match.group('way_name')

        mp = self.console.game.mapName
        cu = self.console.storage.query(self._sql['jw1'] % (mp, wi))

        if cu.EOF:
            # new entry for this way_id on this map
            self.console.storage.query(self._sql['jw2'] % (mp, wi, wn))
            client.message('^7Added alias for way ^3%d^7: ^2%s' % (wi, wn))
        else:
            # update old entry with the new name
            self.console.storage.query(self._sql['jw3'] % (wn, mp, wi))
            client.message('^7Updated alias for way ^3%d^7: ^2%s' % (wi, wn))

        cu.close()