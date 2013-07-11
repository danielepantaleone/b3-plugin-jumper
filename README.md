Jumper Plugin for BigBrotherBot
===============================

## NOTE

## Description

This plugin provides an advanced statistics system for Urban Terror 4.2.x Jump Servers.<br /> 
The plugin is capable of storing permanently all the timings performed during jump runs, offering also the possibility to list player and map records.<br />
The plugin also offer a system of server side demo auto recording whenever a jump run is started. The demo is kept on the server only if the client made at least his personal record on the current map.<br />
The demo auto recording feature can be disabled during the plugin configuration (the feature will work depending on your system configuration).<br />
**NOTE:** *This plugin is currently under development, and is not to be considered stable nor complete.*

## How to install

### Installing the plugin

* Copy **jumper.py** into **b3/extplugins**
* Copy **jumper.xml** into **b3/extplugins/conf**
* Import **jumper.sql** into your b3 database
* Load the plugin in your **b3.xml** configuration file

### Demo auto recording

In order for the demo autorecording feature to work properly, b3 needs to have privileges of **removing** demo files from your UrT 4.2.x server directory.<br />
Because of that both b3 and the UrT needs to be executed by the same OS user (so if the UrT server is started by **FooBar** the b3 also needs to be started by **FooBar**).

### Requirements

* Urban Terror 4.2 server [g_modversion > 4.2.013]
* iourt42 parser [version > 1.12]

## In-game user guide

* **!record [<client>]** *Display the record(s) of a client on the current map*
* **!delrecord [<client>]** *Remove current map client record(s) from the storage*
* **!maprecord** *Display the current map record(s)*

## Support

For support regarding this very plugin you can find me on IRC on **#urbanterror / #goreclan** @ **Quakenet**<br>
For support regarding Big Brother Bot you may ask for help on the official website: http://www.bigbrotherbot.net
