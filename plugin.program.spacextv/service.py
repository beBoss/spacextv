# -*- coding: utf-8 -*-
# SpaceXTV - background service.
# Runs for the whole Kodi session: keeps the channel list and TV guide fresh
# and reloads PVR IPTV Simple only when the channel list actually changed.

import os
import sys

import xbmcaddon
import xbmcvfs

sys.path.insert(0, os.path.join(
    xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('path')), 'resources', 'lib'))

import core  # noqa: E402

core.run_service()
