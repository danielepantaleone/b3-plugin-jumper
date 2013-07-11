CREATE TABLE IF NOT EXISTS `jumpruns` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `client_id` int(10) unsigned NOT NULL,
  `mapname` varchar(64) NOT NULL,
  `way_id` int(3) NOT NULL,
  `way_time` int(10) unsigned NOT NULL,
  `time_add` int(10) unsigned NOT NULL,
  `time_edit` int(10) unsigned NOT NULL,
  `demo` varchar(128) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;