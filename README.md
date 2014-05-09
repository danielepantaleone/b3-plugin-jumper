Jumper Plugin for BigBrotherBot [![BigBrotherBot](http://i.imgur.com/7sljo4G.png)][B3]
===============================

Description
-----------

A [BigBrotherBot][B3] plugin provides an advanced statistics system for Urban Terror 4.2 Jump servers.
The plugin is capable of storing permanently all the timings performed during jump runs, offering also the
possibility to list player and map records.

Download
--------

Latest version available [here](https://github.com/FenixXx/b3-plugin-jumper/archive/master.zip).

Installation
------------

* copy the `jumper.py` file into `b3/extplugins`
* copy the `plugin_jumper.ini` file in `b3/extplugins/conf`
* add to the `plugins` section of your `b3.xml` config file:

  ```xml
  <plugin name="jumper" config="@b3/extplugins/conf/plugin_jumper.ini" />
  ```

Demo auto-recording
-------------------

In order for the demo autorecording feature to work properly, b3 needs to have privileges of **removing** demo files
from your UrT 4.2.x server directory. Because of that both b3 and the UrT needs to be executed by the same OS user
(so if the UrT server is executed by **FooBar** the b3 also needs to be executed by **FooBar**).

Requirements
------------

* Urban Terror 4.2 server [g_modversion >= 4.2.013]
* iourt42 parser [version >= 1.12]

In-game user guide
------------------

* **!jmprecord [&lt;client&gt;] [&lt;mapname&gt;]** - `display the best run(s) of a client on a specific map`
* **!jmpmaprecord [&lt;mapname&gt;]** - `display map best jump run(s)`
* **!jmptopruns [&lt;mapname&gt;]** - `display map top run(s)`
* **!jmpdelrecord [&lt;client&gt;] [&lt;mapname&gt;]** - `delete the best run(s) of a client on a specific map`
* **!jmpmapinfo [&lt;mapname&gt;]** - `display map specific informations`
* **!jmpsetway &lt;way-id&gt; &lt;name&gt;** - `set a name for the specified way id`

Credits
-------

Since version 2.1 this plugin provides a new command, **!jmpmapinfo**, which retrieves maps information (such as
author, release date, level, etc.) and display them in-game. This has been made possible thanks to the
[Urt Jumpers](http://www.urtjumpers.com/) community which provides such data.

Support
-------

If you have found a bug or have a suggestion for this plugin, please report it on the [B3 forums][Support].

[B3]: http://www.bigbrotherbot.net/ "BigBrotherBot (B3)"
[Support]: http://forum.bigbrotherbot.net/plugins-by-fenix/jumper-plugin-(by-mr-click)/ "Support topic on the B3 forums"

[![Build Status](https://travis-ci.org/FenixXx/b3-plugin-jumper.svg?branch=master)](https://travis-ci.org/FenixXx/b3-plugin-jumper)