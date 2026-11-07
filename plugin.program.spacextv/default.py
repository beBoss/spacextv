# -*- coding: utf-8 -*-
# SpaceXTV - opened from Add-ons > Program add-ons (menu), or with an action:
#   RunScript(plugin.program.spacextv,update)     update channels + TV guide now
#   RunScript(plugin.program.spacextv,setup_pvr)  point PVR IPTV Simple at SpaceXTV
#   RunScript(plugin.program.spacextv,log)        show SpaceXTV's lines from the Kodi log
# Background updates are done by service.py.

import os
import sys

import xbmcaddon
import xbmcvfs

sys.path.insert(0, os.path.join(
    xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('path')), 'resources', 'lib'))

import core  # noqa: E402

core.run_manual(sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ('update', 'setup_pvr', 'settings', 'log') else None)
