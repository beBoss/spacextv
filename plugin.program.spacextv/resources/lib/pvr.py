# -*- coding: utf-8 -*-
"""
SpaceXTV - PVR IPTV Simple helpers and one-time migration from the old
"Space Plug-In" add-on (plugin.program.spaceplugin).
"""

import glob
import json
import os
import re
import shutil
import time
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

import xbmc
import xbmcgui
import xbmcvfs

PVR_ID = 'pvr.iptvsimple'
OLD_ID = 'plugin.program.spaceplugin'
TUNE_FILE = None        # set by core: addon_data/.../tuning.json
_last_off = [0.0]       # when SpaceXTV last switched IPTV Simple off
_off_log = [None]       # kodi.log size at that moment (None = log not readable)
_off_running = [False]  # was Live TV running when it was switched off?
_last_ready = [0.0]      # when a SpaceXTV reload last got Live TV up
READY_PROP = 'spacextv.ready'
BUSY_WAIT = 45          # Live TV still loading from before? wait this long before touching it
STOP_TIMEOUT = 30       # max seconds for Kodi to stop Live TV after IPTV Simple is switched off
SETTLE_DEFAULT = 10     # Kodi removes the old IPTV Simple in the background AFTER Live TV stops;
SETTLE_MIN = 4          #   switching it on before that is finished gets lost ("PVR manager is
SETTLE_MAX = 30         #   starting up" forever). Learned per box and saved (tuning.json).
KICK_AFTER = 20         # Live TV not up after this -> the "on" got lost: off/on once more
KICK_SETTLE = 3         # nothing left to remove at that point, so a short pause is enough
LOG_WAIT_MAX = 45       # max wait for Kodi's own "PVR Manager: Stopped" log line
LOG_QUIET = 2.0         # ...then no PVR activity in the log for this long = safe to switch on
QUIET_MAX = 15          # (learned per box, like the pause; never more than this)
READY_TIMEOUT = 150     # max seconds to wait for Live TV to load the channels (slow boxes)

# settings copied from the old add-on (same ids)
MIGRATE_KEYS = (
    'logontype', 'username', 'password', 'urllogin', 'dev_id_new1', 'use_rec_new',
    'xxx', 'en_group_ch', 'use_ua_new', 'use_ext_logos', 'use_local_logos',
    'logos_path', 'logos_local_path', 'repeats', 'timeout', 'dbg', 'en_reload_pvr',
    'ext_epg', 'en_custom_cmd', 'builtin_cmd', 'script_cmd', 'en_cp', 'w_path',
    'epg_refresh', 'epg_days', 'show_progress',
)
# a playlist path containing any of these belongs to us (old or new add-on)
OUR_MARKERS = (OLD_ID, 'plugin.program.spacextv', 'bulsat.m3u', 'spacextv.m3u')


def _log(msg):
    xbmc.log('[SpaceXTV] %s' % msg, xbmc.LOGINFO)


def rpc(method, params=None):
    req = {'jsonrpc': '2.0', 'id': 1, 'method': method}
    if params:
        req['params'] = params
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(req)))
    except Exception:
        return {}


def addon_enabled(addon_id):
    """True / False, or None if the add-on is not installed."""
    det = rpc('Addons.GetAddonDetails', {'addonid': addon_id, 'properties': ['enabled']})
    if 'result' not in det:
        return None
    return bool(det['result'].get('addon', {}).get('enabled'))


def set_enabled(addon_id, enabled):
    rpc('Addons.SetAddonEnabled', {'addonid': addon_id, 'enabled': bool(enabled)})


def pvr_ready():
    """True when Kodi's Live TV is started (channels loaded, 'starting up' gone)."""
    return bool(rpc('PVR.GetProperties', {'properties': ['available']}).get('result', {}).get('available'))


def tv_channels():
    r = rpc('PVR.GetChannels', {'channelgroupid': 'alltv', 'limits': {'start': 0, 'end': 1}})
    return int(r.get('result', {}).get('limits', {}).get('total', 0) or 0)


def other_pvr_clients():
    """Other enabled PVR add-ons keep Live TV running while IPTV Simple is off."""
    res = rpc('Addons.GetAddons', {'type': 'xbmc.pvrclient', 'enabled': True}).get('result')
    addons = (res.get('addons') or []) if isinstance(res, dict) else []
    return [a.get('addonid') for a in addons if isinstance(a, dict) and a.get('addonid') != PVR_ID]


def wait_until(monitor, cond, timeout, step=0.5, on_tick=None):
    """Poll `cond` until true (True) or timeout / Kodi closing (False)."""
    end = time.time() + timeout
    while True:
        if cond():
            return True
        if on_tick:
            on_tick()
        if time.time() >= end or monitor.waitForAbort(step):
            return False


def _tune():
    d = {}
    try:
        with open(TUNE_FILE, 'r') as f:
            d = json.load(f) or {}
    except Exception:
        pass
    return {'settle': float(d.get('settle', SETTLE_DEFAULT)), 'floor': float(d.get('floor', 0)),
            'quiet': float(d.get('quiet', LOG_QUIET)), 'qfloor': float(d.get('qfloor', 0))}


def _settle():
    return min(SETTLE_MAX, max(SETTLE_MIN, _tune()['settle']))


def _quiet():
    return min(QUIET_MAX, max(LOG_QUIET, _tune()['quiet']))


def _learn(ok, how, gap, quiet):
    """Remember what this box needs. Never shrinks back to a value that failed.

    how='log':   quiet moment after Kodi's "PVR Manager: Stopped" line
    how='pause': fixed pause after "off" (only when Kodi's log can't be read)
    """
    if not TUNE_FILE or how not in ('log', 'pause'):
        return
    t = _tune()
    if how == 'log':
        if not ok:
            t['qfloor'] = max(t['qfloor'], quiet)
            t['quiet'] = t['qfloor'] + 3
        else:
            t['quiet'] = max(LOG_QUIET, t['qfloor'] + 1 if t['qfloor'] else LOG_QUIET, t['quiet'] - 0.5)
    else:
        if not ok:
            t['floor'] = max(t['floor'], gap)
            t['settle'] = t['floor'] + 6
        elif gap <= t['settle'] + 1:
            t['settle'] = max(t['floor'] + 2, t['settle'] - 1)
    t['settle'] = min(SETTLE_MAX, max(SETTLE_MIN, t['settle']))
    t['quiet'] = min(QUIET_MAX, max(LOG_QUIET, t['quiet']))
    try:
        with open(TUNE_FILE, 'w') as f:
            json.dump(dict((k, round(v, 1)) for k, v in t.items()), f)
    except OSError:
        pass


# --------------------------------------------------------------------------- #
# Kodi's own log tells exactly when it has finished stopping Live TV
# (measured on an X88 Pro 10: 5.6 s once, 11 s another time - a fixed pause can't be right)
# --------------------------------------------------------------------------- #
_PVR_LINE = re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)(\.\d+)?.*?'
                       r'(PVR Manager: (?:Stopping|Stopped|Start aborted|Starting|Started)'
                       r'|UpdateClients: \w+ PVR client)')


def _log_path():
    return xbmcvfs.translatePath('special://logpath/kodi.log')


def _log_size():
    try:
        return os.path.getsize(_log_path())
    except OSError:
        return None


def _pvr_log_events(pos):
    """[(epoch, text)] of Kodi's PVR start/stop lines written after byte `pos`."""
    try:
        with open(_log_path(), 'rb') as f:
            f.seek(pos)
            data = f.read(4 * 1024 * 1024).decode('utf-8', 'replace')
    except (OSError, ValueError):
        return None
    out = []
    for ln in data.splitlines():
        m = _PVR_LINE.match(ln)
        if m:
            try:
                ts = time.mktime(time.strptime(m.group(1), '%Y-%m-%d %H:%M:%S')) + float(m.group(2) or 0)
            except ValueError:
                ts = time.time()
            out.append((ts, m.group(3)))
    return out


def _wait_safe_to_switch_on(monitor, fallback_pause, on_tick=None):
    """Wait until Kodi has really finished stopping Live TV after our "off".

    Uses Kodi's own log ("PVR Manager: Stopped" / "Start aborted", then a quiet
    moment). Works the same on fast and slow boxes. Falls back to a pause if
    the log can't be read. Returns (how, quiet): how = 'log', 'pause' or 'timeout'.
    """
    t_off = _last_off[0]
    quiet = _quiet()
    if not t_off or time.time() - t_off > 600:
        return 'none', quiet                # it was off already (not by us) - nothing to wait for
    pos = _off_log[0]
    if pos is None or _pvr_log_events(pos) is None:
        left = t_off + fallback_pause - time.time()
        if left > 0:
            wait_until(monitor, lambda: False, left, step=0.5, on_tick=on_tick)
        return 'pause', quiet
    min_after_off = 0.0 if _off_running[0] else KICK_SETTLE

    def safe():
        ev = _pvr_log_events(pos) or []
        done = (not _off_running[0]) or any(t in ('PVR Manager: Stopped', 'PVR Manager: Start aborted') for _, t in ev)
        last = max([ts for ts, _ in ev] + [t_off])
        return done and time.time() - t_off >= min_after_off and time.time() - last >= quiet

    if wait_until(monitor, safe, max(0.0, t_off + LOG_WAIT_MAX - time.time()), step=0.5, on_tick=on_tick):
        return 'log', quiet
    return 'timeout', quiet


# --------------------------------------------------------------------------- #
# Which channel failed to play? (Kodi only says "One or more items failed to play")
# --------------------------------------------------------------------------- #
_TS = re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)(\.\d+)?')
_OPEN = re.compile(r'VideoPlayer::OpenFile: (\S+)')
_STREAM = re.compile(r'Live Stream URL: (\S+)')
_FAIL = re.compile(r'OpenDemuxStream - Error creating demuxer|OpenInputStream - error opening')
_EOF = re.compile(r'Process - eof reading from demuxer')     # the stream ran dry (live TV never ends)
_UID = re.compile(r'_(\d+)\.pvr$')


def _line_time(line):
    m = _TS.match(line)
    if m:
        try:
            return time.mktime(time.strptime(m.group(1), '%Y-%m-%d %H:%M:%S')) + float(m.group(2) or 0)
        except ValueError:
            pass
    return time.time()


def _mark_ready():
    _last_ready[0] = time.time()
    try:        # shared with the other SpaceXTV process (menu "Update now" vs. background service)
        xbmcgui.Window(10000).setProperty(READY_PROP, '%.3f' % _last_ready[0])
    except Exception:
        pass


def last_ready():
    """When SpaceXTV last got Live TV up after a reload (from either process)."""
    try:
        other = float(xbmcgui.Window(10000).getProperty(READY_PROP) or 0)
    except Exception:
        other = 0.0
    return max(_last_ready[0], other)


class PlayWatch(object):
    """Follows Kodi's log (only the new lines, a few bytes every couple of
    seconds) and remembers the last live channel that failed to start or
    stopped by itself: {'when', 'path' (pvr://...), 'url' (the stream link
    IPTV Simple used)}."""

    def __init__(self):
        self.pos = _log_size()          # start at the end: only what happens from now on
        self.readable = self.pos is not None
        self.rest = b''
        self.url = None
        self.last_open = None
        self.failed = None
        self.ended = None

    def poll(self):
        size = _log_size()
        self.readable = size is not None
        if size is None:
            return
        if self.pos is None:
            self.pos = size
        if size < self.pos:              # a new log file (Kodi restarted)
            self.pos, self.rest = 0, b''
        if size == self.pos:
            return
        try:
            with open(_log_path(), 'rb') as f:
                f.seek(self.pos)
                data = f.read(min(size - self.pos, 1 << 20))
        except (OSError, ValueError):
            return
        self.pos += len(data)
        lines = (self.rest + data).split(b'\n')
        self.rest = lines.pop()
        for raw in lines:
            if not (b'Live Stream URL' in raw or b'OpenFile' in raw or b'demuxer' in raw or b'error opening' in raw):
                continue                # cheap filter: most lines are about something else
            line = raw.decode('utf-8', 'replace')
            m = _STREAM.search(line)
            if m:
                self.url = m.group(1)
                continue
            m = _OPEN.search(line)
            if m:
                path = m.group(1)
                self.last_open = {'path': path, 'url': self.url if path.startswith('pvr://') else None,
                                  'when': _line_time(line)}
                self.url = None
                continue
            if self.last_open and _FAIL.search(line):
                self.failed = dict(self.last_open, when=_line_time(line))
            elif self.last_open and _EOF.search(line) and is_live(self.last_open):
                self.ended = dict(self.last_open, when=_line_time(line))

    def take(self):
        f, self.failed = self.failed, None
        return f

    def take_ended(self):
        e, self.ended = self.ended, None
        return e


def is_live(item):
    """A live TV/radio channel (not a recording or catch-up programme, which do end)."""
    path, url = (item or {}).get('path') or '', (item or {}).get('url') or ''
    return path.startswith('pvr://channels/') and 'wowzadvrplaylist' not in url


def channel_group(path):
    return 'allradio' if '/channels/radio/' in (path or '') else 'alltv'


def path_uid(path):
    m = _UID.search(path or '')
    return int(m.group(1)) if m else None


def channel_list(group='alltv'):
    """[(channelid, label, uniqueid)] of Live TV's channels."""
    res = rpc('PVR.GetChannels', {'channelgroupid': group, 'properties': ['uniqueid']}).get('result')
    chans = (res.get('channels') or []) if isinstance(res, dict) else []
    return [(c.get('channelid'), c.get('label') or '', c.get('uniqueid'))
            for c in chans if isinstance(c, dict) and c.get('channelid') is not None]


def find_channel(group, uid, label=None):
    """(channelid, label) by IPTV Simple's id, else by name (None if not found)."""
    chans = channel_list(group)
    for cid, lab, u in chans:
        if uid is not None and u == uid:
            return cid, lab
    if label:
        for cid, lab, u in chans:
            if lab == label:
                return cid, lab
    return None


def play_channel(channelid):
    return 'result' in rpc('Player.Open', {'item': {'channelid': int(channelid)}})


def iptvsimple_configured():
    """True if any IPTV Simple configuration has a playlist (False = brand-new / empty)."""
    d = _pvr_dir()
    files = glob.glob(os.path.join(d, 'instance-settings-*.xml')) or glob.glob(os.path.join(d, 'settings.xml'))
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                text = fh.read()
        except OSError:
            continue
        if _get(text, 'm3uPath') or _get(text, 'm3uUrl'):
            return True
    return False


def switch_off(monitor, on_tick=None):
    """Switch IPTV Simple off and wait until Kodi has stopped Live TV.
    Returns True if it was on. Remembers the time for the settle pause."""
    if not addon_enabled(PVR_ID):
        return False
    _off_running[0] = pvr_ready()
    _off_log[0] = _log_size()               # Kodi's log lines after this point are about our "off"
    set_enabled(PVR_ID, False)
    _last_off[0] = time.time()
    if not other_pvr_clients():
        stopped = wait_until(monitor, lambda: not pvr_ready(), STOP_TIMEOUT, on_tick=on_tick)
        _log('Live TV %s after %.1fs' % ('stopped' if stopped else 'did NOT stop', time.time() - _last_off[0]))
    return True


def is_off():
    return addon_enabled(PVR_ID) is False


def reload_pvr(monitor, edit=None, progress=None, msgs=None):
    """Switch IPTV Simple off and on so it re-reads playlist + settings,
    then WAIT until Live TV has really loaded the channels.

    Kodi gets stuck on "PVR manager is starting up" if IPTV Simple is switched
    back on before Kodi has finished removing the old one. So:
      1. never touch Live TV while it is still loading from before,
      2. switch on only after the settle pause (often already over, because
         SpaceXTV switches off early - while the TV guide downloads),
      3. if it still does not come up, switch off/on once more (self-heal),
         and remember a longer pause for next time.

    `edit` (optional) runs while it is off - the only safe moment to change
    its settings files. IPTV Simple is ALWAYS switched back on, even if Kodi
    is closing, so Live TV is never left disabled.
    Returns True when Live TV is up, None if it did not come up, False if not installed.
    """
    state = addon_enabled(PVR_ID)
    if state is None:
        _log('PVR IPTV Simple is not installed')
        return False
    p = progress or (lambda pct, msg: None)
    msgs = msgs or {}
    t0 = time.time()
    settle = _settle()

    def say(pct, key):
        msg, secs = msgs.get(key, ''), int(time.time() - t0)
        p(pct, ('%s  %ds' % (msg, secs)) if msg and secs >= 3 else msg)   # visible "still alive" counter

    def creep():
        e = time.time() - t0
        say(40 + int(55 * e / (e + 15)), 'load')                         # slowly towards 95 %

    alone = not other_pvr_clients()
    if state and alone and not pvr_ready() and iptvsimple_configured():
        _log('Live TV is still loading from before - waiting before reloading')
        wait_until(monitor, pvr_ready, BUSY_WAIT, on_tick=lambda: say(5, 'load'))

    ready, gap, first_gap, first_ok, first_how, first_quiet = None, 0.0, 0.0, False, 'none', LOG_QUIET
    for attempt in (1, 2):
        try:
            if addon_enabled(PVR_ID):
                say(10, 'stop')
                switch_off(monitor, on_tick=lambda: say(15, 'stop'))
            if edit and attempt == 1:
                edit()
        finally:
            how, quiet = 'abort', LOG_QUIET
            if not monitor.abortRequested():
                how, quiet = _wait_safe_to_switch_on(monitor, settle if attempt == 1 else KICK_SETTLE,
                                                     on_tick=lambda: say(25, 'stop'))
            gap = time.time() - _last_off[0]
            set_enabled(PVR_ID, True)
        if not alone:
            monitor.waitForAbort(3)         # other clients keep Live TV "up" - give it a moment
        ready = wait_until(monitor, pvr_ready, KICK_AFTER if attempt == 1 else READY_TIMEOUT,
                           step=0.5, on_tick=creep)
        if attempt == 1:
            first_ok, first_gap, first_how, first_quiet = bool(ready), gap, how, quiet
            _log('Live TV switched on %.1fs after off (%s) -> %s' % (
                gap, {'log': 'Kodi log said stopped', 'pause': 'pause', 'timeout': 'log timeout',
                      'abort': 'closing', 'none': 'was off already'}[how],
                'loaded' if ready else 'NOT loaded (lost)'))
        if ready or monitor.abortRequested():
            break
        _log('Live TV did not come up within %ds - switching IPTV Simple off/on once more' % KICK_AFTER)

    # learn the pause this box needs
    if alone and not monitor.abortRequested():
        _learn(first_ok, first_how, first_gap, first_quiet)
    if ready:
        _mark_ready()
        _log('Live TV ready: %d channels (%.0fs, learned: quiet %.1fs, pause %.0fs)' % (
            tv_channels(), time.time() - t0, _quiet(), _settle()))
        p(100, '')
        return True
    _log('Live TV still not up after %.0fs' % (time.time() - t0))
    return None


def ensure_installed(monitor, progress=None, msg=''):
    """IPTV Simple missing (not Android / Windows / Mac)? Offer Kodi's own installer.

    Asked BEFORE the long loading starts, so all questions come first.
    True when IPTV Simple is installed. (Kodi starts it by itself; the reload
    later waits until that start is finished before touching it.)
    """
    if addon_enabled(PVR_ID) is not None:
        return True
    if progress:
        progress(2, msg)
    xbmc.executebuiltin('InstallAddon(%s)' % PVR_ID, True)     # Kodi asks "Install?" itself
    t0 = time.time()
    while addon_enabled(PVR_ID) is None:
        # keep waiting while Kodi's install window / progress is on screen; declined -> stop fast
        limit = 120 if xbmc.getCondVisibility('System.HasModalDialog') else 3
        if time.time() - t0 > limit or monitor.waitForAbort(1):
            _log('IPTV Simple was not installed')
            return False
    _log('IPTV Simple installed')
    return True


# --------------------------------------------------------------------------- #
# Point IPTV Simple at our files
# --------------------------------------------------------------------------- #
def _pvr_dir():
    return xbmcvfs.translatePath('special://profile/addon_data/%s/' % PVR_ID)


def _kodi_major():
    try:
        return int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0])
    except ValueError:
        return 21


def _get(text, sid):
    m = re.search(r'<setting id="%s"[^>]*?(?:/>|>(.*?)</setting>)' % re.escape(sid), text, re.S)
    return (m.group(1) or '') if m else ''


def _put(text, sid, value):
    el = '<setting id="%s">%s</setting>' % (sid, escape(value))
    pat = re.compile(r'<setting id="%s"[^>]*?(?:/>|>.*?</setting>)' % re.escape(sid), re.S)
    if pat.search(text):
        return pat.sub(lambda m: el, text, count=1)
    return text.replace('</settings>', '    %s\n</settings>' % el)


def _point(text, m3u, epg, with_epg):
    text = _put(text, 'm3uPathType', '0')
    text = _put(text, 'm3uPath', m3u)
    if with_epg:
        text = _put(text, 'epgPathType', '0')
        text = _put(text, 'epgPath', epg)
    return text


def setup_iptvsimple(monitor, m3u, epg, with_epg=True, create=False, backup_dir=None,
                     progress=None, msgs=None):
    """Make PVR IPTV Simple use our playlist / guide.

    Fixes every IPTV Simple configuration that points at the old or new
    SpaceXTV files. With create=True and none found, adds a new "SpaceXTV"
    configuration. Returns 'ok' (nothing to do), 'updated', 'created',
    'none' (not set up, create=False) or 'missing' (IPTV Simple not installed).
    """
    if addon_enabled(PVR_ID) is None and not (create and ensure_installed(monitor)):
        return 'missing'
    d = _pvr_dir()
    files = sorted(glob.glob(os.path.join(d, 'instance-settings-*.xml')))
    if not files and _kodi_major() < 20 and os.path.exists(os.path.join(d, 'settings.xml')):
        files = [os.path.join(d, 'settings.xml')]

    changes, already_ok, empty = {}, False, []
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                text = fh.read()
        except OSError:
            continue
        if not any(k in _get(text, 'm3uPath') for k in OUR_MARKERS):
            if not _get(text, 'm3uPath') and not _get(text, 'm3uUrl'):
                empty.append((f, text))   # never configured (e.g. created by Kodi on install)
            continue                      # another provider - leave it alone
        new = _point(text, m3u, epg, with_epg)
        if new != text:
            changes[f] = new
        else:
            already_ok = True

    if changes:
        result = 'updated'
    elif already_ok:
        return 'ok'
    elif not create:
        return 'none'
    elif empty:
        # use the empty configuration Kodi made, so there is only one (no "no channels" errors)
        f, text = empty[0]
        if _kodi_major() >= 20:
            text = _put(text, 'kodi_addon_instance_name', 'SpaceXTV')
        changes = {f: _point(text, m3u, epg, with_epg)}
        result = 'created'
    else:
        # nothing points at us yet -> add a new "SpaceXTV" configuration
        if _kodi_major() >= 20:
            used = [int(n) for n in re.findall(r'instance-settings-(\d+)\.xml', ' '.join(files))]
            target = os.path.join(d, 'instance-settings-%d.xml' % ((max(used) + 1) if used else 1))
            text = ('<settings version="2">\n'
                    '    <setting id="kodi_addon_instance_name">SpaceXTV</setting>\n'
                    '    <setting id="kodi_addon_instance_enabled">true</setting>\n'
                    '</settings>\n')
        else:
            target = os.path.join(d, 'settings.xml')
            text = '<settings version="2">\n</settings>\n'
        changes = {target: _point(text, m3u, epg, with_epg)}
        result = 'created'

    def write():
        if not os.path.isdir(d):
            os.makedirs(d)
        for f, text in changes.items():
            if backup_dir and os.path.exists(f):
                try:
                    if not os.path.isdir(backup_dir):
                        os.makedirs(backup_dir)
                    shutil.copy(f, os.path.join(backup_dir, '%s.%d.bak' % (os.path.basename(f), int(time.time()))))
                except OSError:
                    pass
            with open(f + '.tmp', 'w', encoding='utf-8') as fh:
                fh.write(text)
            os.replace(f + '.tmp', f)
            _log('IPTV Simple settings updated: %s' % os.path.basename(f))

    reload_pvr(monitor, edit=write, progress=progress, msgs=msgs)
    return result


# --------------------------------------------------------------------------- #
# One-time migration from "Space Plug-In"
# --------------------------------------------------------------------------- #
def migrate_settings(addon):
    """Copy login + preferences from the old add-on. Returns True if copied."""
    if addon.getSetting('migrated') == 'true':
        return False
    addon.setSetting('migrated', 'true')
    if addon.getSetting('username') or addon.getSetting('urllogin'):
        return False            # already configured - never overwrite
    path = xbmcvfs.translatePath('special://profile/addon_data/%s/settings.xml' % OLD_ID)
    if not os.path.exists(path):
        return False
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return False
    vals = {}
    for el in root.iter('setting'):
        sid = el.get('id')
        if sid in MIGRATE_KEYS and el.get('default') != 'true':
            vals[sid] = el.text or ''
    # the old "copy to folder" pointed inside the old add-on - don't carry that over
    if OLD_ID in vals.get('w_path', ''):
        vals.pop('w_path', None)
        vals.pop('en_cp', None)
    for sid, v in vals.items():
        addon.setSetting(sid, v)
    _log('Imported %d settings from Space Plug-In' % len(vals))
    return bool(vals)


def disable_old_addon():
    """Switch off the old add-on so two services don't fight. True if done."""
    if addon_enabled(OLD_ID):
        set_enabled(OLD_ID, False)
        _log('Old Space Plug-In switched off')
        return True
    return False
