# -*- coding: utf-8 -*-
"""
SpaceXTV - Kodi side: settings, update scheduling, menu.

Update strategy (built for slow Android boxes):
  * Bulsat stream links carry a token that is valid for a fixed time
    (currently 600 min = 10 h). The channel list is refreshed shortly before
    the links expire - not on a blind hourly timer.
  * One update cycle = one login: playlist first (seconds), then the TV guide
    in the same session. The guide is refreshed together with the playlist
    whenever it is older than half its refresh interval.
  * Right after Kodi starts, the heavy guide download waits a few minutes so
    Kodi and Live TV can load first.
  * PVR IPTV Simple is reloaded ONLY when the playlist changed and never
    while something is playing (it waits until you stop).
  * Every sign-in gives new links, so a timed refresh never signs in while you
    are watching or using the remote - it waits for a quiet moment.
  * Bulsat can end a session early (same account signed in on another device),
    so the links stop working long before "10 h". The link doctor notices it
    (a channel fails to play, Kodi starts, or a quick check while someone uses
    Kodi), signs in again, reloads Live TV and restarts the channel you wanted.
"""

import json
import os
import re
import time
import traceback
from urllib.parse import urlparse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

import bulsat
import pvr

ADDON_ID = 'plugin.program.spacextv'
NAME = 'SpaceXTV'
LOCK_PROP = 'spacextv.busy'
PROMPT_PROP = 'spacextv.prompt'   # a sign-in window is open (service or menu)
LOCK_MAX_AGE = 20 * 60
TICK = 20                 # service wake-up interval (seconds)
BOOT_NET_WAIT = 10        # let Wi-Fi/Ethernet come up after boot
EPG_BOOT_DELAY = 180      # heavy guide download waits until Kodi has settled
RESTART_MIN_UPTIME = 45   # never reload PVR while it is still starting
WORKERS = 8

# link doctor (see Doctor)
WATCH_EVERY = 2           # read new lines of Kodi's log this often (seconds) - a channel failed?
START_WINDOW = 120        # Kodi just started: check the links even if nobody pressed a button yet
START_RETRY = 15          #   (no internet yet? try again soon)
CHECK_EVERY = 900         # someone uses Kodi but is not watching: check the links every 15 min
CHECK_RETRY = 120         # check inconclusive (no internet?): try again in 2 min
ACTIVE_IDLE = 120         # "someone uses Kodi" = a remote button within the last 2 min
QUIET_IDLE = 60           # timed refresh waits until the remote was not touched for 1 min...
URGENT_LEFT = 900         # ...unless the links run out within 15 min
REPLAY_WINDOW = 180       # restart the channel that failed if it was asked for within 3 min
RENEW_MAX = 3             # at most 3 automatic sign-ins per 30 min...
RENEW_WINDOW = 1800
HEAL_BLOCK = 1800         # ...and none for 30 min after Bulsat refused even fresh links

PROFILES = {
    '0': {'ua': ('Mozilla/5.0 (SMART-TV; Linux; Tizen 2.3) AppleWebkit/538.1 '
                 '(KHTML, like Gecko) SamsungBrowser/1.0 TV Safari/538.1'),
          'osid': 'samsungtv'},
    '1': {'ua': bulsat.ANDROID_UA, 'osid': 'androidtv'},
}


class MissingLogin(Exception):
    pass


class Aborted(Exception):
    pass


# --------------------------------------------------------------------------- #
# Kodi helpers
# --------------------------------------------------------------------------- #
_DEBUG = False


def log(msg, debug=False):
    if debug and not _DEBUG:
        return
    xbmc.log('[%s] %s' % (NAME, msg), xbmc.LOGINFO)


_ADDON = []


def L(sid):
    """Text in Kodi's language (Bulgarian or English) from strings.po."""
    if not _ADDON:
        _ADDON.append(xbmcaddon.Addon(ADDON_ID))
    return _ADDON[0].getLocalizedString(sid)


def notify(msg, ms=5000):
    try:
        icon = xbmcaddon.Addon(ADDON_ID).getAddonInfo('icon')
    except Exception:
        icon = xbmcgui.NOTIFICATION_INFO
    xbmcgui.Dialog().notification(NAME, msg, icon, ms, False)


def _home():
    return xbmcgui.Window(10000)


def acquire_lock():
    if is_busy():
        return False
    _home().setProperty(LOCK_PROP, str(time.time()))
    return True


def release_lock():
    _home().clearProperty(LOCK_PROP)


def is_busy():
    v = _home().getProperty(LOCK_PROP)
    try:
        return bool(v) and 0 <= time.time() - float(v) < LOCK_MAX_AGE
    except ValueError:
        return False


def _hash(obj):
    import hashlib
    return hashlib.sha1(json.dumps(obj, sort_keys=True).encode('utf-8')).hexdigest()[:16]


def _int(v, default):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _float(v, default):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def prompt_open():
    return bool(_home().getProperty(PROMPT_PROP))


def can_prompt():
    """Safe to pop up a sign-in window: no other window / prompt in the way."""
    return not prompt_open() and not xbmc.getCondVisibility('System.HasModalDialog') and not is_busy()


def ask_login(addon, welcome=False):
    """Ask for username + password with the on-screen keyboard. True if saved.

    Only one sign-in window can exist at a time (service welcome vs. menu).
    """
    _home().setProperty(PROMPT_PROP, '1')
    try:
        return _ask_login(addon, welcome)
    finally:
        _home().clearProperty(PROMPT_PROP)


def _ask_login(addon, welcome):
    d = xbmcgui.Dialog()
    if welcome and not d.yesno(NAME, L(30100), nolabel=L(30101), yeslabel=L(30102)):
        return False
    user = d.input(L(30103), addon.getSetting('username')).strip()
    if not user:
        return False
    pw = d.input(L(30104), type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT)
    if not pw:
        return False
    addon.setSetting('logontype', 'true')
    addon.setSetting('username', user)
    addon.setSetting('password', pw)
    return True


# --------------------------------------------------------------------------- #
# Settings + state
# --------------------------------------------------------------------------- #
class Settings(object):
    def __init__(self):
        global _DEBUG
        a = xbmcaddon.Addon(ADDON_ID)
        g = a.getSetting
        b = lambda k: g(k) == 'true'
        self.addon = a
        self.version = a.getAddonInfo('version')
        self.data_dir = xbmcvfs.translatePath(a.getAddonInfo('profile'))
        self.m3u_path = os.path.join(self.data_dir, bulsat.M3U_NAME)
        pvr.TUNE_FILE = os.path.join(self.data_dir, 'tuning.json')
        self.epg_path = os.path.join(self.data_dir, bulsat.EPG_NAME)
        # what IPTV Simple is told (portable special:// form)
        self.m3u_kodi = 'special://profile/addon_data/%s/%s' % (ADDON_ID, bulsat.M3U_NAME)
        self.epg_kodi = 'special://profile/addon_data/%s/%s' % (ADDON_ID, bulsat.EPG_NAME)

        self.base = g('base') or bulsat.DEFAULT_BASE
        self.login_with_user = g('logontype') != 'false'
        self.username = g('username').strip()
        self.password = g('password')
        self.login_url = g('urllogin').strip()
        self.use_rec = b('use_rec_new')
        dev = g('dev_id_new1')
        self.profile = '1' if self.use_rec else (dev if dev in PROFILES else '0')
        self.app_ver = g('app_ver') or '1.0.3'

        self.refresh_auto = g('refresh_auto') != 'false'
        self.refresh_min = max(10, _int(g('refresh_new'), 60))
        self.gen_epg = not b('ext_epg')
        self.epg_hours = max(1, _int(g('epg_refresh'), 12))
        self.epg_days = min(7, max(1, _int(g('epg_days'), 3)))
        self.show_progress = b('show_progress')
        self.reload_pvr = g('en_reload_pvr') != 'false'

        self.show_adult = b('xxx')
        self.group_by_genre = g('en_group_ch') != 'false'
        self.add_ua = g('use_ua_new') != 'false'
        self.use_ext_logos = b('use_ext_logos')
        self.use_local_logos = b('use_local_logos')
        self.logos_path = g('logos_path')
        self.logos_local_path = g('logos_local_path')

        self.repeats = min(10, max(1, _int(g('repeats'), 3)))
        self.timeout = min(60.0, max(2.0, _float(g('timeout'), 10.0)))
        self.debug = b('dbg')
        self.copy_out = b('en_cp')
        self.copy_path = g('w_path')
        self.custom_cmd = b('en_custom_cmd')
        self.builtin_cmd = g('builtin_cmd')
        self.script_cmd = g('script_cmd')
        self.pvr_checked = b('pvr_checked')
        _DEBUG = self.debug

    def has_login(self):
        if self.login_with_user:
            return bool(self.username and self.password)
        return bool(self.login_url)

    def _account(self):
        return [self.base, self.login_with_user, self.username if self.login_with_user else self.login_url,
                self.profile, self.app_ver]

    def playlist_sig(self):
        return _hash(self._account() + [self.use_rec, self.show_adult, self.group_by_genre, self.add_ua,
                                        self.use_ext_logos, self.use_local_logos, self.logos_path,
                                        self.logos_local_path])

    def epg_sig(self):
        return _hash(self._account() + [self.epg_days, self.use_rec, self.show_adult])


class State(object):
    """Small JSON file (state.json) remembering what was generated when."""

    def __init__(self, s):
        self.path = os.path.join(s.data_dir, 'state.json')
        self.d = {}
        try:
            with open(self.path, 'r') as f:
                self.d = json.load(f) or {}
        except (OSError, ValueError):
            self.d = {}

    def get(self, k, default=None):
        return self.d.get(k, default)

    def save(self, **kw):
        self.d.update(kw)
        try:
            bulsat._atomic_write(self.path, json.dumps(self.d, indent=1).encode('utf-8'))
        except OSError as e:
            log('Cannot save state: %s' % e)


def playlist_refresh_at(s, st):
    """When the playlist should be refreshed next (epoch seconds)."""
    ts = _float(st.get('ts'), 0)
    expires = _float(st.get('links_expire'), 0)
    if s.refresh_auto and expires > ts:
        ttl = expires - ts
        return expires - max(600, min(3600, ttl * 0.15))   # 1 h early for 10 h links
    return ts + s.refresh_min * 60


def due(s, st, now=None):
    """(playlist_due, epg_due) - cheap, no network."""
    now = now or time.time()
    ts = _float(st.get('ts'), 0)
    pl = (not os.path.exists(s.m3u_path)
          or st.get('sig') != s.playlist_sig()
          or now < ts                                   # clock went backwards
          or now >= playlist_refresh_at(s, st))
    epg = False
    if s.gen_epg:
        eage = now - _float(st.get('epg_ts'), 0)
        limit = s.epg_hours * 3600
        epg = (not os.path.exists(s.epg_path)
               or st.get('epg_sig') != s.epg_sig()
               or not (0 <= eage < limit)
               or (pl and eage >= limit / 2))           # ride along: one login per cycle
    return pl, epg


# --------------------------------------------------------------------------- #
# The update itself
# --------------------------------------------------------------------------- #
class Updater(object):
    def __init__(self, settings, monitor, progress=None):
        self.s = settings
        self.monitor = monitor
        self._progress = progress

    def _p(self, pct, msg):
        if self._progress:
            try:
                self._progress(int(pct), msg)
            except Exception:
                pass

    def _credentials(self):
        s = self.s
        if s.login_with_user:
            if not (s.username and s.password):
                raise MissingLogin()
            return s.username, s.password
        if not s.login_url:
            raise MissingLogin()
        import requests
        url = s.login_url if s.login_url.endswith('/') else s.login_url + '/'
        try:
            txt = requests.get(url + 'login.txt', timeout=s.timeout).text
        except requests.RequestException:
            raise bulsat.ApiError('Cannot read the login file')
        mu = re.search('user":"(.+?)"', txt)
        mp = re.search('pass":"(.+?)"', txt)
        if not (mu and mp):
            raise MissingLogin()
        return mu.group(1), mp.group(1)

    def _login(self, user, pw, prof):
        s = self.s
        err = None
        for attempt in range(s.repeats):
            if self.monitor.abortRequested():
                raise Aborted()
            client = bulsat.Client(s.base, user, pw, prof['osid'], prof['ua'], app_ver=s.app_ver,
                                   timeout=s.timeout, friendly_name=xbmc.getInfoLabel('System.FriendlyName'),
                                   workers=WORKERS, log=lambda m: log(m, debug=True))
            try:
                self._p(5, L(30140))
                client.login()
                self._p(15, L(30141))
                return client, client.channels()
            except bulsat.LoginError:
                client.close()
                raise
            except bulsat.ApiError as e:
                client.close()
                err = e
                log('Attempt %d/%d failed: %s' % (attempt + 1, s.repeats, e))
                if attempt + 1 < s.repeats and self.monitor.waitForAbort(5):
                    raise Aborted()
        raise err or bulsat.ApiError('Update failed')

    def run(self, with_epg, on_playlist=None, epg_not_before=0):
        """Login, refresh the playlist and (optionally) the TV guide.

        on_playlist(res) is called as soon as the playlist is saved (so Live TV
        can reload while the guide is still downloading). The guide download
        waits until `epg_not_before` (epoch) - used right after Kodi starts.
        """
        s = self.s
        t0 = time.time()
        if not os.path.isdir(s.data_dir):
            os.makedirs(s.data_dir)
        user, pw = self._credentials()
        prof = PROFILES[s.profile]
        st = State(s)
        res = {'m3u_changed': False, 'epg_written': False, 'epg_error': False,
               'channels': 0, 'programmes': 0, 'epg_failed': 0, 'link_hours': 0}

        client, channels = self._login(user, pw, prof)
        try:
            if s.debug:
                with open(os.path.join(s.data_dir, 'debug-channels.json'), 'w', encoding='utf-8') as f:
                    json.dump(channels, f, ensure_ascii=False, indent=1)

            # ---- playlist ------------------------------------------------- #
            self._p(20, L(30142))
            text, kept = bulsat.build_m3u(
                channels, show_adult=s.show_adult, group_by_genre=s.group_by_genre,
                add_ua=s.add_ua, user_agent=prof['ua'], use_rec=s.use_rec,
                use_ext_logos=s.use_ext_logos, use_local_logos=s.use_local_logos,
                logos_path=s.logos_path, logos_local_path=s.logos_local_path,
                default_group=NAME)
            res['channels'] = len(kept)
            res['m3u_changed'] = bulsat.write_m3u_if_changed(s.m3u_path, text)
            now = time.time()
            ttl = bulsat.link_ttl(kept)
            res['link_hours'] = (ttl or 0) / 3600.0
            st.save(ts=now, sig=s.playlist_sig(), channels=len(kept),
                    links_expire=(now + ttl) if ttl else 0, app_version=s.version)
            log('Playlist: %d channels, %s, links valid %s, next refresh %s (%.1fs)' % (
                len(kept), 'CHANGED' if res['m3u_changed'] else 'unchanged',
                ('%.1f h' % (ttl / 3600.0)) if ttl else 'unknown',
                time.strftime('%H:%M', time.localtime(playlist_refresh_at(s, st))), time.time() - t0))
            if on_playlist:
                on_playlist(res)

            # ---- TV guide ------------------------------------------------- #
            if with_epg and s.gen_epg:
                while time.time() < epg_not_before:
                    self._p(22, L(30143))
                    if self.monitor.waitForAbort(5):
                        raise Aborted()
                t1 = time.time()
                self._p(25, L(30144))

                def prog(i, n, title):
                    self._p(25 + 70 * i / n, L(30145) % (i, n, title))

                frags, total, failed = client.fetch_epg(
                    kept, days=s.epg_days, keep_past=s.use_rec, progress=prog,
                    should_stop=self.monitor.abortRequested)
                if self.monitor.abortRequested():
                    raise Aborted()
                res['programmes'], res['epg_failed'] = total, failed
                asked = sum(1 for c in kept if 'program' in c)
                if asked and failed > asked // 2 and os.path.exists(s.epg_path):
                    # keep the old (good) guide instead of replacing it with a broken one
                    res['epg_error'] = True
                    log('TV guide failed for %d of %d channels - keeping the old guide' % (failed, asked))
                else:
                    self._p(96, L(30146))
                    bulsat.write_epg(s.epg_path, kept, frags)
                    res['epg_written'] = True
                    st.save(epg_ts=time.time(), epg_sig=s.epg_sig(), programmes=total)
                    log('TV guide: %d programmes, %d days, %d failed (%.1fs)' % (
                        total, s.epg_days, failed, time.time() - t1))
        finally:
            client.close()

        if res['m3u_changed'] or res['epg_written']:
            self._after_update(res)
        self._p(100, '')            # the caller says "Done" once Live TV has the channels
        return res

    def _after_update(self, res):
        s = self.s
        if s.copy_out and s.copy_path:
            try:
                dst_dir = s.copy_path if s.copy_path.endswith(('/', '\\')) else s.copy_path + '/'
                if not xbmcvfs.exists(dst_dir):
                    xbmcvfs.mkdirs(dst_dir)
                for src, changed in ((s.m3u_path, res['m3u_changed']), (s.epg_path, res['epg_written'])):
                    dst = dst_dir + os.path.basename(src)
                    if os.path.isfile(src) and (changed or not xbmcvfs.exists(dst)):
                        xbmcvfs.copy(src, dst)
                log('Copied files to %s' % dst_dir, debug=True)
            except Exception as e:
                log('Copy to output folder failed: %s' % e)
        if s.custom_cmd:
            if s.builtin_cmd:
                log('Running built-in: %s' % s.builtin_cmd, debug=True)
                xbmc.executebuiltin(s.builtin_cmd)
            if s.script_cmd:
                log('Running script: %s' % s.script_cmd, debug=True)
                os.system(s.script_cmd)


class Progress(object):
    """Top-right progress bar that stays up across steps (update -> Live TV loading)."""

    def __init__(self, show, first_msg=None):
        self.dp = None
        if show:
            self.dp = xbmcgui.DialogProgressBG()
            self.dp.create(NAME, first_msg or L(30147))

    def __call__(self, pct, msg):
        if self.dp and msg:
            self.dp.update(max(0, min(100, int(pct))), NAME, msg)

    def close(self):
        if self.dp:
            self.dp.close()
            self.dp = None

    def part(self, lo, hi):
        """Same bar, mapped to lo..hi % (update 0-70, Live TV loading 70-100)."""
        return _Part(self, lo, hi)


class _Part(object):
    def __init__(self, prog, lo, hi):
        self.prog, self.lo, self.hi = prog, lo, hi

    def __call__(self, pct, msg):
        self.prog(self.lo + (self.hi - self.lo) * pct / 100.0, msg)

    def close(self):
        self.prog.close()


def _live_msgs():
    return {'stop': L(30150), 'load': L(30151)}


def setup_live_tv(s, monitor, create, progress=None):
    """Point PVR IPTV Simple at our files (fixes old paths automatically).
    Reloads Live TV (and waits until the channels are there) if it changed anything."""
    return pvr.setup_iptvsimple(monitor, s.m3u_kodi, s.epg_kodi, with_epg=s.gen_epg, create=create,
                                backup_dir=os.path.join(s.data_dir, 'backup'),
                                progress=progress, msgs=_live_msgs())


def reload_live_tv(monitor, progress=None):
    """Reload Live TV and wait until Kodi shows the channels."""
    own = progress is None
    prog = Progress(True, L(30151)) if own else progress
    try:
        return pvr.reload_pvr(monitor, progress=prog, msgs=_live_msgs())
    finally:
        if own:
            prog.close()


def early_off(s, monitor, res, setup_pending, with_epg, flag):
    """The user is waiting anyway: switch Live TV off right after the channel list
    arrived, so Kodi removes the old IPTV Simple WHILE the TV guide downloads.
    Switching it back on at the end is then instant (no settle pause)."""
    if not (res['m3u_changed'] or setup_pending or (with_epg and s.gen_epg)):
        return
    if not (s.reload_pvr or setup_pending):
        return
    if xbmc.Player().isPlaying():
        return      # watching: do it the normal way later
    if not pvr.pvr_ready() and pvr.iptvsimple_configured():
        return      # a real Live TV is still loading - don't disturb it
    # (a brand-new, empty IPTV Simple never finishes starting - nothing to wait for, switch it off now)
    if pvr.switch_off(monitor):
        flag.append(True)


def finish(s, monitor, res, first_setup, prog, allow_reload=True):
    """After an update the user is waiting for: get the new data into Live TV,
    WAIT until Kodi shows it, then say so. Returns True if a reload is still owed."""
    if pvr.addon_enabled(pvr.PVR_ID) is None:
        r = 'missing'               # install was already offered at the start - never ask twice
    else:
        r = setup_live_tv(s, monitor, create=first_setup, progress=prog)
    if not s.pvr_checked:
        s.addon.setSetting('pvr_checked', 'true')
        s.pvr_checked = True
    owed = False
    reloaded = r in ('created', 'updated')
    changed = res['m3u_changed'] or res['epg_written']
    if r == 'ok' and ((changed and s.reload_pvr) or pvr.is_off()):
        if allow_reload or pvr.is_off():
            pvr.reload_pvr(monitor, progress=prog, msgs=_live_msgs())
            reloaded = True
        else:
            owed = True             # something is playing - reload when it stops
    prog.close()
    if r == 'missing':
        notify(L(30112), 10000)
    elif reloaded and not pvr.pvr_ready():
        notify(L(30155), 12000)     # never say "Done" while Live TV is not up yet
    elif first_setup and r in ('created', 'updated', 'ok'):
        notify(L(30111) % res['channels'], 8000)        # "All set! N channels - open TV" 
    elif r == 'updated':
        notify(L(30110), 6000)
    elif res['epg_error']:
        notify(L(30126) % res['channels'])
    elif s.gen_epg:
        notify(L(30127) % (res['channels'], s.epg_days))
    else:
        notify(L(30128) % res['channels'])
    if r == 'none':
        notify(L(30129), 8000)
    return owed


# --------------------------------------------------------------------------- #
# Link doctor: keeps the channels playable
# --------------------------------------------------------------------------- #
def _read_text(path):
    try:
        with open(path, 'rb') as f:
            return f.read().decode('utf-8', 'replace')
    except OSError:
        return ''


def timed_refresh(s, st):
    """Only the clock asks for this update (not new settings, not a missing file)."""
    if st.get('sig') != s.playlist_sig() or not os.path.exists(s.m3u_path):
        return False
    if s.gen_epg and (st.get('epg_sig') != s.epg_sig() or not os.path.exists(s.epg_path)):
        return False
    return True


def quiet_moment(player, st, now=None):
    """Every sign-in gives new links and can end the old session, so a timed
    refresh waits until nobody is watching or using the remote - while nothing
    plays, at the latest shortly before the links run out."""
    now = now or time.time()
    if player.isPlaying():
        return False
    if xbmc.getGlobalIdleTime() >= QUIET_IDLE:
        return True
    expires = _float(st.get('links_expire'), 0)
    return bool(expires) and expires - now < URGENT_LEFT


class Player(xbmc.Player):
    """Tells the service when something failed to play / a Live TV channel really plays."""

    def __init__(self):
        xbmc.Player.__init__(self)
        self.error_at = 0.0
        self.live_ok_at = 0.0

    def onPlayBackError(self):
        self.error_at = time.time()

    def onAVStarted(self):
        try:
            if self.getPlayingFile().startswith('pvr://'):
                self.live_ok_at = time.time()
        except Exception:
            pass


class Doctor(object):
    """Bulsat can end our session early - e.g. when the same account signs in
    on another device of the same type. Every channel then says "Playback
    failed", although the links say "valid 10 h". The doctor notices it:

      * a channel failed to play -> check that link; refused? renew + restart that channel
      * Kodi just started        -> check the links once
      * someone uses Kodi (not watching) -> check every 15 min
      (one small request each; nothing happens if the links work)

    Renew = sign in again, load the fresh links into Live TV, wait until ready.
    It never signs in while nobody uses Kodi: that could end the session of
    someone watching Bulsat on another device.
    """

    def __init__(self, player, started):
        self.player = player
        self.watch = pvr.PlayWatch()
        self.polled = 0.0
        self.err_seen = 0.0
        self.started = started
        self.check_at = started
        self.start_check = True
        self.renewals = []
        self.blocked_until = 0.0
        self.last = None                    # result of the last renewal

    def reset(self):
        """Settings changed (other account / profile?): forget earlier refusals."""
        self.blocked_until = 0.0
        self.renewals = []

    # -- noticing ----------------------------------------------------------- #
    def wake(self):
        """Cheap - called about every second while the service sleeps.
        True = a channel just failed to play."""
        now = time.time()
        if self.player.error_at > self.err_seen or now - self.polled >= WATCH_EVERY:
            self.polled = now
            self.watch.poll()
        return self.watch.failed is not None or self.player.error_at > self.err_seen

    def _take_failure(self):
        self.watch.poll()
        f = self.watch.take()
        if self.player.error_at > self.err_seen:
            self.err_seen = self.player.error_at
            if f is None:
                # Kodi reported an error but its log did not say which item (or can't be read)
                lo = self.watch.last_open
                if lo and 0 <= self.player.error_at - lo['when'] < 120:
                    f = dict(lo, when=self.player.error_at)
                else:
                    f = {'when': self.player.error_at, 'path': None, 'url': None}
        return f

    def tick(self, s, monitor, ctx):
        """From the service loop. Does nothing while SpaceXTV is busy (failures wait)."""
        if is_busy():
            return
        if not (s.has_login() and s.reload_pvr and os.path.exists(s.m3u_path)):
            self._take_failure()                    # nothing SpaceXTV could fix yet
            return
        f = self._take_failure()
        if f:
            self._on_failure(s, monitor, ctx, f)
        else:
            self._maybe_check(s, monitor, ctx)

    def _on_failure(self, s, monitor, ctx, f):
        path = f.get('path')
        if path and not (path.startswith('pvr://') and pvr.PVR_ID in path):
            return                                  # not one of our Live TV channels
        if self.player.live_ok_at > f['when']:
            return                                  # a channel has played since - the links work
        url = (f.get('url') or '').split('|')[0]
        if url and '.bulsat.' not in '.' + urlparse(url).netloc:
            return
        if pvr.last_ready() > f['when']:
            # it failed while Live TV was being reloaded with fresh links: just start it again
            if time.time() - f['when'] < REPLAY_WINDOW:
                self._replay_failed(f)
            return
        if time.time() < self.blocked_until:
            log('A channel failed to play - Bulsat refused fresh links a moment ago, next try after %s' % (
                time.strftime('%H:%M', time.localtime(self.blocked_until))))
            return
        text = _read_text(s.m3u_path)
        links = dict((l[0], l[1]) for l in bulsat.playlist_links(text))
        if ctx['pending'] or (url and url not in links):
            # Live TV still has older links than the ones saved - are the saved ones good?
            if bulsat.playlist_link_state(text) != bulsat.LINK_DEAD:
                log('A channel failed to play - Live TV still had the previous links, loading the new ones')
                if self.renew(s, monitor, f, sign_in=False) == 'ok':
                    ctx['pending'] = False
            else:
                self._heal(s, monitor, ctx, f, 'a channel failed to play, saved links refused too')
            return
        state = bulsat.check_link(url, links[url]) if url else bulsat.playlist_link_state(text)
        log('A channel failed to play - link check: %s' % state)
        if state == bulsat.LINK_DEAD:
            self._heal(s, monitor, ctx, f, 'a channel failed to play')
        # ok: that channel itself has a problem; unknown: no internet - renewing would not help

    def _maybe_check(self, s, monitor, ctx):
        now = time.time()
        if now < max(self.check_at, self.blocked_until) or ctx['pending'] or self.player.isPlaying():
            return
        if self.player.live_ok_at > now - CHECK_EVERY:
            self.start_check = False                # a channel played fine just now
            self.check_at = self.player.live_ok_at + CHECK_EVERY
            return
        first = self.start_check and now - self.started < START_WINDOW
        if not first and xbmc.getGlobalIdleTime() >= ACTIVE_IDLE:
            return                                  # nobody at the remote: never sign in behind anyone's back
        t0 = time.time()
        state = bulsat.playlist_link_state(_read_text(s.m3u_path))
        if state == bulsat.LINK_UNKNOWN:
            self.check_at = time.time() + (START_RETRY if first else CHECK_RETRY)
            log('Link check inconclusive (no internet?) - trying again later', debug=True)
            return
        self.start_check = False
        self.check_at = time.time() + CHECK_EVERY
        why = 'Kodi start' if first else 'someone is using Kodi'
        log('Link check (%s): %s (%.1fs)' % (why, state, time.time() - t0), debug=state == bulsat.LINK_OK)
        if state == bulsat.LINK_DEAD:
            self._heal(s, monitor, ctx, None, why)

    # -- fixing ------------------------------------------------------------- #
    def _heal(self, s, monitor, ctx, f, why):
        now = time.time()
        if now < self.blocked_until:
            log('Links refused (%s) - not signing in again before %s' % (
                why, time.strftime('%H:%M', time.localtime(self.blocked_until))))
            return
        self.renewals = [t for t in self.renewals if now - t < RENEW_WINDOW]
        if len(self.renewals) >= RENEW_MAX:
            # the same thing keeps happening: give it a break (the error itself was already shown)
            self._refused('%d renewals in %d min' % (len(self.renewals), RENEW_WINDOW // 60),
                          quiet=self.last == 'error')
            return
        self.renewals.append(now)
        log('Bulsat no longer accepts our links (%s) - signing in again' % why)
        r = self.last = self.renew(s, monitor, f, sign_in=True)
        if r == 'ok':
            ctx['pending'] = False
        elif r == 'refused':
            self._refused('fresh links refused too')

    def _refused(self, why, quiet=False):
        self.blocked_until = time.time() + HEAL_BLOCK
        log('Not renewing the links for %d min (%s) - account in use on another device?' % (
            HEAL_BLOCK // 60, why))
        if not quiet:
            notify(L(30173), 12000)

    def renew(self, s, monitor, f=None, sign_in=True):
        """(Sign in again and) load the links into Live TV, wait until it shows
        the channels, then restart the channel that failed.
        Returns 'ok', 'refused', 'error' or 'busy'."""
        if not acquire_lock():
            return 'busy'
        t0 = time.time()
        want = self._remember(f)
        prog = Progress(True, L(30170) if sign_in else L(30150))
        try:
            if sign_in:
                res = Updater(s, monitor, prog.part(0, 25)).run(with_epg=False)
                if bulsat.playlist_link_state(_read_text(s.m3u_path)) == bulsat.LINK_DEAD:
                    log('Bulsat refuses the fresh links too (%d channels)' % res['channels'])
                    return 'refused'                # reloading Live TV would not help
            ready = pvr.reload_pvr(monitor, progress=prog.part(25 if sign_in else 0, 100), msgs=_live_msgs())
        except Aborted:
            return 'error'
        except MissingLogin:
            notify(L(30105), 8000)
            return 'error'
        except bulsat.LoginError:
            notify(L(30106), 8000)
            return 'error'
        except Exception as e:
            log('Renewing the links failed: %s' % e)
            log(traceback.format_exc(), debug=True)
            notify(L(30125), 8000)
            return 'error'
        finally:
            prog.close()
            release_lock()
        played = self._replay(want) if ready else None
        log('Links renewed%s - Live TV %s (%.0fs)%s' % (
            ' (signed in again)' if sign_in else '', 'ready' if ready else 'NOT ready',
            time.time() - t0, (' - restarted "%s"' % played) if played else ''))
        if not ready:
            notify(L(30155), 12000)
        elif played:
            notify(L(30172) % played, 6000)
        else:
            notify(L(30171), 6000)
        return 'ok' if ready else 'error'

    def _remember(self, f):
        """The channel that failed (asked for in the last few minutes) - looked up
        BEFORE Live TV reloads, in case IPTV Simple gives it a new id."""
        if not f or not f.get('path') or time.time() - f['when'] > REPLAY_WINDOW:
            return None
        group, uid = pvr.channel_group(f['path']), pvr.path_uid(f['path'])
        if uid is None:
            return None
        hit = pvr.find_channel(group, uid)
        return {'group': group, 'uid': uid, 'label': hit[1] if hit else None, 'when': f['when']}

    def _replay(self, want):
        """Start the channel the user wanted - the latest one, if they tried
        another while Live TV was reloading. Returns its name or None."""
        later = self._take_failure()
        cands = []
        if later and (later.get('path') or '').startswith('pvr://') and \
                (not want or later['when'] > want['when']):
            cands.append({'group': pvr.channel_group(later['path']), 'uid': pvr.path_uid(later['path']),
                          'label': None, 'when': later['when']})
        if want:
            cands.append(want)
        for c in cands:
            if self.player.isPlaying() or time.time() - c['when'] > REPLAY_WINDOW + 120:
                return None
            hit = pvr.find_channel(c['group'], c['uid'], c['label'])
            if hit and pvr.play_channel(hit[0]):
                return hit[1]
        return None

    def _replay_failed(self, f):
        if self.player.isPlaying() or not f.get('path'):
            return
        hit = pvr.find_channel(pvr.channel_group(f['path']), pvr.path_uid(f['path']))
        if hit and pvr.play_channel(hit[0]):
            log('Restarted "%s" - it was asked for while Live TV was reloading' % hit[1])
            notify(L(30172) % hit[1], 6000)


# --------------------------------------------------------------------------- #
# Background service
# --------------------------------------------------------------------------- #
class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.settings_changed = False

    def onSettingsChanged(self):
        self.settings_changed = True


def _nap(monitor, secs, wake=None):
    """Sleep up to `secs` but wake up as soon as settings change (or `wake()`
    says so - e.g. a channel just failed to play). True = Kodi closing."""
    end = time.time() + secs
    while True:
        if monitor.waitForAbort(min(1.0, max(0.0, end - time.time()))):
            return True
        if monitor.settings_changed or time.time() >= end or (wake and wake()):
            return False


def run_service():
    monitor = Monitor()
    player = Player()
    # older versions re-scheduled themselves with AlarmClock - cancel leftovers
    for aid in (ADDON_ID, pvr.OLD_ID):
        xbmc.executebuiltin('CancelAlarm(%s,true)' % aid)
    log('Service started')

    # cheap boxes often boot with a wrong date until NTP syncs
    for _ in range(36):
        if time.localtime().tm_year >= 2024:
            break
        if monitor.waitForAbort(5):
            return
    started = time.time()
    net_ready = started + BOOT_NET_WAIT     # network work waits for Wi-Fi; the sign-in window does not
    doctor = Doctor(player, started)

    # one-time move from the old "Space Plug-In" add-on
    if pvr.migrate_settings(xbmcaddon.Addon(ADDON_ID)):
        notify(L(30108))
    if pvr.disable_old_addon():
        notify(L(30109), 8000)
    s = Settings()
    monitor.settings_changed = False

    ctx = {'pending': False}
    next_try = 0.0          # back-off after errors
    epg_block = 0.0         # back-off for the TV guide only
    user_until = 0.0        # the user just changed settings: show progress + result
    fails = 0
    warned = None
    waiting = False         # a timed refresh is waiting for a quiet moment

    def can_reload():
        return (s.reload_pvr and not player.isPlaying()
                and time.time() - started > RESTART_MIN_UPTIME)

    while not monitor.abortRequested():
        if monitor.settings_changed:
            monitor.settings_changed = False
            s = Settings()
            next_try = epg_block = 0.0
            warned = None
            user_until = time.time() + 120
            doctor.reset()

        # a channel failed to play / Kodi just started / quick check: renew dead links
        doctor.tick(s, monitor, ctx)
        now = time.time()

        if now >= next_try and not is_busy():
            st = State(s)
            pl_due, epg_due = due(s, st, now)
            if epg_due and not pl_due and os.path.exists(s.epg_path) and \
                    (now - started < EPG_BOOT_DELAY or now < epg_block):
                epg_due = False     # guide-only update can wait: Kodi starting / recent failure
            if pl_due or epg_due:
                if not s.has_login():
                    welcomed = xbmcaddon.Addon(ADDON_ID).getSetting('welcomed') == 'true'
                    if not welcomed:
                        if can_prompt():            # fresh install: ask once, when the screen is free
                            s.addon.setSetting('welcomed', 'true')
                            if ask_login(s.addon, welcome=True):
                                s = Settings()
                                monitor.settings_changed = False
                                net_ready = 0       # user just typed - network is up
                                continue            # go straight to loading the channels
                    elif warned != 'login' and not prompt_open():
                        warned = 'login'
                        notify(L(30105), 8000)
                elif now < net_ready:
                    pass                            # just started: give Wi-Fi a few seconds
                else:
                    first_m3u = not os.path.exists(s.m3u_path)
                    first_epg = not os.path.exists(s.epg_path)
                    setup_pending = not s.pvr_checked
                    # someone is watching the screen (first install / just changed settings)?
                    user = first_m3u or setup_pending or now < user_until
                    hold = not user and timed_refresh(s, st) and not quiet_moment(player, st, now)
                    if hold != waiting:
                        waiting = hold
                        log('Timed refresh %s' % ('waits until nobody is watching or using the remote'
                                                   if hold else 'starts now'), debug=True)

                    def on_playlist(res):
                        if user:            # someone is waiting: overlap Kodi's work with the download
                            if not player.isPlaying():
                                early_off(s, monitor, res, setup_pending, epg_due or first_m3u, early)
                            return
                        # background: put fresh links into Live TV straight away
                        if not (res['m3u_changed'] and s.reload_pvr):
                            return
                        if can_reload():
                            reload_live_tv(monitor)
                        else:
                            ctx['pending'] = True

                    early = []
                    not_before = 0 if (user or first_epg) else started + EPG_BOOT_DELAY
                    if hold:
                        res, err, owed = None, None, False
                    else:
                        res, err, owed = _service_update(s, monitor, epg_due or first_m3u, on_playlist,
                                                         not_before, user, setup_pending,
                                                         allow_reload=not player.isPlaying(), early=early)
                    if res:
                        fails, next_try, warned, user_until = 0, 0.0, None, 0.0
                        if res['epg_error']:
                            epg_block = time.time() + 900
                        if owed or (not user and first_epg and res['epg_written']):
                            ctx['pending'] = True
                    elif err:
                        if warned != err:
                            notify(L({'login': 30105, 'badlogin': 30106}.get(err, 30107)), 8000)
                        warned = err
                        if err == 'net':
                            fails += 1
                            next_try = time.time() + min(300 * fails, 3600)
                        else:
                            next_try = time.time() + 1800

        if ctx['pending']:
            if not s.reload_pvr:
                ctx['pending'] = False
            elif can_reload() and not is_busy():
                ctx['pending'] = False
                reload_live_tv(monitor)

        # quick ticks in the first seconds; wakes up at once when settings change or a channel fails
        if _nap(monitor, TICK if time.time() > net_ready + TICK else 1, wake=doctor.wake):
            break
    log('Service stopped')


def _service_update(s, monitor, with_epg, on_playlist, not_before, user, setup_pending, allow_reload,
                    early=None):
    """One background update. Returns (result or None, error code or None, reload owed)."""
    if not acquire_lock():
        return None, None, False
    prog = Progress(s.show_progress or user)
    try:
        if user and setup_pending:
            pvr.ensure_installed(monitor, prog, L(30154))   # all questions first, then one loading bar
        res = Updater(s, monitor, prog.part(0, 70) if user else prog).run(with_epg, on_playlist, not_before)
        owed = False
        if user:
            owed = finish(s, monitor, res, setup_pending, prog.part(70, 100), allow_reload)
        return res, None, owed
    except Aborted:
        return None, None, False
    except MissingLogin:
        return None, 'login', False
    except bulsat.LoginError:
        return None, 'badlogin', False
    except Exception as e:
        log('Update failed: %s' % e)
        log(traceback.format_exc(), debug=True)
        return None, 'net', False
    finally:
        prog.close()
        if early and pvr.is_off():
            reload_live_tv(monitor)         # something went wrong half-way: never leave Live TV off
        release_lock()


# --------------------------------------------------------------------------- #
# Manual run (Add-ons > Program add-ons > SpaceXTV, or buttons in settings)
# --------------------------------------------------------------------------- #
def run_manual(action=None):
    s = Settings()
    if prompt_open():
        notify(L(30113))
        return
    if action is None:
        st = State(s)
        if st.get('ts'):
            info = L(30114) % (
                time.strftime('%d.%m %H:%M', time.localtime(_float(st.get('ts'), 0))), st.get('channels', '?'))
        else:
            info = L(30115)
        choice = xbmcgui.Dialog().select('%s  -  %s' % (NAME, info), [
            L(30050) if s.has_login() else L(30117),
            L(30051),
            L(30160),
            L(30119),
        ])
        action = {0: 'update', 1: 'setup_pvr', 2: 'log', 3: 'settings'}.get(choice)
    if action == 'log':
        show_log()
    elif action == 'settings':
        s.addon.openSettings()
    elif action == 'setup_pvr':
        _manual_setup(s)
    elif action == 'update':
        _manual_update(s)


def show_log():
    """Show SpaceXTV's own lines from Kodi's log on the TV (no file browsing needed)."""
    lines = []
    for name in ('kodi.old.log', 'kodi.log'):           # previous Kodi session first
        path = xbmcvfs.translatePath('special://logpath/' + name)
        try:
            with open(path, 'rb') as f:
                f.seek(0, 2)
                f.seek(max(0, f.tell() - 600000))
                data = f.read().decode('utf-8', 'replace')
        except OSError:
            continue
        for ln in data.splitlines():
            if '[SpaceXTV]' in ln or 'PVR Manager' in ln:
                m = re.match(r'\d{4}-(\d\d-\d\d) (\d\d:\d\d:\d\d)\S*\s+T:\S+\s+\S+\s+<[^>]*>:\s*(.*)', ln)
                lines.append('%s %s  %s' % (m.group(1), m.group(2), m.group(3)) if m else ln.strip())
    xbmcgui.Dialog().textviewer('%s - %s' % (NAME, L(30160)), '\n'.join(lines[-200:]) or L(30161))


def _manual_setup(s):
    if not os.path.exists(s.m3u_path):
        notify(L(30120))
        return
    if not acquire_lock():
        notify(L(30123))
        return
    prog = Progress(True, L(30151))
    try:
        r = setup_live_tv(s, xbmc.Monitor(), create=True, progress=prog)
    finally:
        prog.close()
        release_lock()
    s.addon.setSetting('pvr_checked', 'true')
    if r in ('created', 'updated'):
        notify(L(30111) % _int(State(s).get('channels'), 0), 8000)
    else:
        notify(L({'ok': 30121, 'missing': 30131}.get(r, 30130)), 6000)


def _manual_update(s):
    if not s.has_login():
        if not ask_login(s.addon):
            return
        s = Settings()
    if not acquire_lock():
        notify(L(30123))
        return
    monitor = xbmc.Monitor()
    prog = Progress(True, L(30148))
    early = []
    first = not s.pvr_checked
    try:
        if first:
            pvr.ensure_installed(monitor, prog, L(30154))   # all questions first, then one loading bar
        res = Updater(s, monitor, prog.part(0, 70)).run(
            with_epg=True, on_playlist=lambda r: early_off(s, monitor, r, first, True, early))
        finish(s, monitor, res, first, prog.part(70, 100))
    except Aborted:
        pass
    except MissingLogin:
        notify(L(30149))
    except bulsat.LoginError:
        notify(L(30106))
    except Exception as e:
        log('Update failed: %s' % e)
        log(traceback.format_exc())
        notify(L(30125))
    finally:
        prog.close()
        if early and pvr.is_off():
            reload_live_tv(monitor)         # something went wrong half-way: never leave Live TV off
        release_lock()
