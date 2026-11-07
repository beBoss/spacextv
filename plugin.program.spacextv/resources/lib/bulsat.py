# -*- coding: utf-8 -*-
"""
SpaceXTV - Bulsat IPTV client and playlist / TV guide writer.

Network + file generation only (no Kodi GUI calls), shared by the background
service and the manual "Update now" script.

Why this is faster/lighter than the previous version:
  * stdlib json (C accelerated) instead of pure-Python simplejson
  * HTTP connection pool sized to the worker count (no extra TLS handshakes)
  * TV guide streamed as plain text (no ElementTree tree in RAM, no
    pretty-print pass), fast gzip level 1 instead of 9 (~12x faster, ~10%
    bigger), trimmed to the days you choose, and only for channels that are in the playlist
  * files are written to a temp file and swapped in atomically, so
    PVR IPTV Simple never reads a half-written file
  * the playlist is only rewritten when its content really changed
"""

import base64
import binascii
import gzip
import hashlib
import html
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, unquote, unquote_plus, urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter

try:
    from Cryptodome.Cipher import AES
except ImportError:  # some builds ship PyCryptodome as "Crypto"
    from Crypto.Cipher import AES

DEFAULT_BASE = 'https://api.iptv.bulsat.com'
REC_URL = 'http://lb-ndvr.iptv.bulsat.com'
ANDROID_UA = 'okhttp/3.12.12'

M3U_NAME = 'spacextv.m3u'
EPG_NAME = 'spacextv.xml.gz'


class LoginError(Exception):
    """Wrong username / password - no point retrying until settings change."""


class ApiError(Exception):
    """Network or server problem - worth retrying later."""


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def _pad16(data):
    # Same zero padding as before (always adds 1..16 bytes), but done on bytes
    # so non-ASCII passwords can no longer break the AES step.
    return data + b'\0' * (16 - len(data) % 16)


def _json(r):
    """Same decoding rules as requests' r.json(), but always the fast C json."""
    if r.encoding:
        return json.loads(r.content.decode(r.encoding, 'replace'))
    return json.loads(r.content)


_BAD_XML = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f]')
_TS = re.compile(r'^(\d{14})\s*([+-]\d{4})?')
_REQ_TIME = re.compile(r'request_time=\d+')


def _text(s):
    """Plain display text: decode HTML entities like &quot; that the API sends."""
    if s is None:
        return ''
    if not isinstance(s, str):
        s = str(s)
    if '&' in s:
        s = html.unescape(s)
    return s


def _x(s):
    """Text -> safe XML text/attribute value."""
    s = _text(s)
    if not s:
        return ''
    s = (s.replace('&', '&amp;').replace('<', '&lt;')
          .replace('>', '&gt;').replace('"', '&quot;'))
    return _BAD_XML.sub('', s)


def _cutoffs(sample, past_epoch, future_epoch):
    """Cut-off strings (YYYYmmddHHMMSS) in the same timezone as `sample`.

    Comparing 14-digit strings is much cheaper than parsing every programme
    time on a slow box. Returns None if the format is unknown (= no trimming).
    """
    m = _TS.match(sample or '')
    if not m:
        return None
    off = 0
    tz = m.group(2)
    if tz:
        off = (int(tz[1:3]) * 3600 + int(tz[3:5]) * 60) * (-1 if tz[0] == '-' else 1)
    fmt = '%Y%m%d%H%M%S'
    past = time.strftime(fmt, time.gmtime(past_epoch + off)) if past_epoch else None
    future = time.strftime(fmt, time.gmtime(future_epoch + off)) if future_epoch else None
    return past, future


def _atomic_write(path, data):
    tmp = path + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(data)
    os.replace(tmp, path)


_TOKEN = re.compile(r'wmsAuthSign=([A-Za-z0-9+/=%_-]+)')
_VALID = re.compile(r'validminutes=(\d+)')


def link_ttl(channels):
    """How long the stream links stay valid, in seconds (None if unknown).

    Bulsat links carry a Wowza token (wmsAuthSign) that says it itself,
    e.g. "validminutes=600" = 10 hours. Reading it lets us refresh the
    playlist just before the links expire instead of on a blind timer.
    """
    for ch in channels[:10]:
        m = _TOKEN.search(ch.get('ndvr') or ch.get('sources') or '')
        if not m:
            continue
        tok = unquote(m.group(1))
        try:
            raw = base64.b64decode(tok + '=' * (-len(tok) % 4)).decode('utf-8', 'replace')
        except (ValueError, binascii.Error):
            continue
        v = _VALID.search(raw)
        if v and int(v.group(1)) > 0:
            return int(v.group(1)) * 60
    return None


def m3u_fingerprint(text):
    # catch-up URLs contain a request timestamp that changes every run;
    # ignore it so an unchanged channel list is detected as unchanged
    return hashlib.sha1(_REQ_TIME.sub('', text).encode('utf-8')).hexdigest()


# --------------------------------------------------------------------------- #
# API client
# --------------------------------------------------------------------------- #
class Client(object):
    def __init__(self, base, user, password, os_type, user_agent,
                 app_ver='1.0.3', timeout=10.0, friendly_name='',
                 workers=8, log=None):
        self.base = (base or DEFAULT_BASE).rstrip('/')
        self.url_login = self.base + '/?auth'
        self.url_list = self.base + ('/tv/full/limit' if user_agent == ANDROID_UA else '/tv/')
        self.url_epg = self.base + '/epg/long'
        self.user = user or ''
        self.password = password or ''
        self.os_type = os_type
        self.app_ver = app_ver or '1.0.3'
        self.timeout = timeout
        self.friendly_name = friendly_name or ''
        self.workers = max(1, int(workers))
        self.log = log or (lambda msg: None)
        self.clock_offset = 0.0   # server time - box time (cheap boxes drift)

        self.headers = {
            'Host': urlparse(self.base).netloc or 'api.iptv.bulsat.com',
            'Connection': 'keep-alive',
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'bg-BG,en-US;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Pragma': 'no-cache',
        }
        self.s = requests.Session()
        adapter = HTTPAdapter(pool_connections=4, pool_maxsize=self.workers)
        self.s.mount('https://', adapter)
        self.s.mount('http://', adapter)

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass

    # -- low level ---------------------------------------------------------- #
    def _req(self, method, url, **kw):
        kw.setdefault('timeout', self.timeout)
        kw.setdefault('headers', self.headers)
        try:
            return self.s.request(method, url, **kw)
        except requests.RequestException as e:
            raise ApiError('Cannot reach the server (%s)' % e.__class__.__name__)

    def _sync_clock(self, r):
        try:
            server = parsedate_to_datetime(r.headers['Date']).timestamp()
            self.clock_offset = server - time.time()
        except Exception:
            self.clock_offset = 0.0

    def now(self):
        return time.time() + self.clock_offset

    # -- login -------------------------------------------------------------- #
    def login(self):
        r = self._req('POST', self.url_login)
        if r.status_code != 200:
            raise ApiError('Server error %d (session)' % r.status_code)
        self._sync_clock(r)
        try:
            key = r.headers['challenge']
            self.s.headers['SSBULSATAPI'] = r.headers['ssbulsatapi']
        except KeyError:
            raise ApiError('Unexpected server reply (no session)')

        osid = self.os_type
        form = {
            'user': [None, self.user],
            'device_id': [None, osid],
            'device_name': [None, osid],
            'os_version': [None, osid],
            'os_type': [None, osid],
            'app_version': [None, self.app_ver],
            'pass': [None, ''],
        }
        if osid == 'androidtv':
            digest = hashlib.md5()
            digest.update(b'ARTS*#234S')
            enc = AES.new(digest.hexdigest().encode('utf-8'), AES.MODE_ECB)
            text = (self.user + ':bulcrypt:' + self.password).encode('utf-8')
            form['pass'][1] = base64.b64encode(enc.encrypt(_pad16(text)))
            # stable 64-bit device id (same formula as before -> same device)
            digest.update((self.user + self.friendly_name).encode('utf-8'))
            form['device_id'][1] = digest.hexdigest()[0:16]
            form['device_name'][1] = 'unknown_google_atv'
            form['os_version'][1] = '7.1.2'
            form['app_version'][1] = '1.5.20'
        else:
            enc = AES.new(key.encode('utf-8'), AES.MODE_ECB)
            form['pass'][1] = base64.b64encode(enc.encrypt(_pad16(self.password.encode('utf-8'))))

        r = self._req('POST', self.url_login, files=form)
        if r.status_code != 200:
            raise ApiError('Server error %d (login)' % r.status_code)
        try:
            logged = str(_json(r).get('Logged', '')).lower()
        except (ValueError, AttributeError):
            raise ApiError('Unexpected server reply (login)')
        if logged != 'true':
            raise LoginError('Login failed')
        self.log('Login OK')

        # The session must stay logged in - streams need it (no logout).
        self.s.headers.update({'Access-Control-Request-Method': 'POST',
                               'Access-Control-Request-Headers': 'ssbulsatapi'})
        try:  # CORS pre-flight, same as the official web app
            self._req('OPTIONS', self.url_list)
        except ApiError:
            pass

    # -- channel list ------------------------------------------------------- #
    def channels(self):
        r = self._req('POST', self.url_list)
        if r.status_code != 200:
            raise ApiError('Server error %d (channel list)' % r.status_code)
        try:
            data = _json(r)
        except ValueError:
            raise ApiError('Unexpected server reply (channel list)')
        if not isinstance(data, list):
            raise ApiError('Unexpected server reply (channel list)')
        chans = [c for c in data if isinstance(c, dict) and c.get('epg_name')]
        if not chans:
            raise ApiError('The server returned an empty channel list')
        return chans

    # -- TV guide ----------------------------------------------------------- #
    def fetch_epg(self, channels, days=3, keep_past=False, progress=None, should_stop=None):
        """Download the guide for `channels` in parallel.

        Returns (fragments, programmes, failed) where fragments maps
        epg_name -> encoded <programme> XML block.
        """
        now = self.now()
        future_epoch = now + days * 86400 if days else None
        past_epoch = None if keep_past else now - 12 * 3600   # catch-up needs the past
        todo = [c for c in channels if 'program' in c]
        fragments, total, failed = {}, 0, 0
        if not todo:
            return fragments, 0, 0

        def work(ch):
            name = ch['epg_name']
            progs = None
            for attempt in (1, 2):
                if should_stop and should_stop():
                    return ch, None, 0
                try:
                    r = self.s.post(self.url_epg, timeout=self.timeout, headers=self.headers,
                                    data={'epg': '1week', 'channel': name})
                    if r.status_code == 200:
                        progs = list(_json(r).values())[0]['programme']
                        break
                    if r.status_code < 500:
                        break
                except requests.RequestException:
                    pass
                except (ValueError, KeyError, IndexError, TypeError, AttributeError):
                    break   # no guide for this channel
            ok = progs is not None
            if not ok:
                progs = ch.get('program')   # fall back to now/next from the list
            xml, n = programmes_xml(name, ch.get('genre'), progs, past_epoch, future_epoch)
            return ch, xml, (n if ok else -1)

        pool = ThreadPoolExecutor(max_workers=self.workers)
        futures = [pool.submit(work, ch) for ch in todo]
        step = max(1, len(todo) // 25)
        try:
            for i, fut in enumerate(as_completed(futures), 1):
                ch, xml, n = fut.result()
                if xml:
                    fragments[ch['epg_name']] = xml
                if n < 0:
                    failed += 1
                else:
                    total += n
                if progress and (i % step == 0 or i == len(todo)):
                    progress(i, len(todo), _text(ch.get('title')) or ch['epg_name'])
                if should_stop and should_stop():
                    for f in futures:
                        f.cancel()
                    break
        finally:
            pool.shutdown(wait=True)
        return fragments, total, failed


# --------------------------------------------------------------------------- #
# Writers
# --------------------------------------------------------------------------- #
def programmes_xml(name, genre, progs, past_epoch, future_epoch):
    """<programme> elements for one channel as UTF-8 bytes (+ count)."""
    if not isinstance(progs, list) or not progs:
        return b'', 0
    cid = _x(name)
    cat = _x(genre)
    cat_xml = '<category>%s</category>' % cat if cat else ''
    cut = None
    if past_epoch or future_epoch:
        first = progs[0].get('start') if isinstance(progs[0], dict) else None
        cut = _cutoffs(str(first or ''), past_epoch, future_epoch)
    past, future = cut if cut else (None, None)

    out = []
    for p in progs:
        try:
            start = str(p['start'])
            stop = str(p['stop'])
        except (KeyError, TypeError):
            continue
        if future and start[:14] >= future:
            continue
        if past and stop[:14] < past:
            continue
        desc = _x(p.get('desc'))
        out.append('<programme start="%s" stop="%s" channel="%s"><title>%s</title>%s%s</programme>\n' % (
            _x(start), _x(stop), cid, _x(p.get('title')),
            '<desc>%s</desc>' % desc if desc else '', cat_xml))
    return ''.join(out).encode('utf-8'), len(out)


def write_epg(path, channels, fragments):
    """Stream the XMLTV file straight into gzip (never builds a big tree)."""
    tmp = path + '.tmp'
    seen, order = set(), []
    with open(tmp, 'wb') as raw:
        with gzip.GzipFile(filename='spacextv.xml', mode='wb', fileobj=raw, compresslevel=1) as gz:
            gz.write(b'<?xml version="1.0" encoding="UTF-8"?>\n'
                     b'<tv generator-info-name="SpaceXTV">\n')
            head = []
            for ch in channels:
                name = ch['epg_name']
                if name in seen:
                    continue
                seen.add(name)
                order.append(name)
                head.append('<channel id="%s"><display-name lang="bg">%s</display-name>'
                            '<url>https://web.iptv.bulsat.com</url></channel>\n'
                            % (_x(name), _x(ch.get('title') or name)))
            gz.write(''.join(head).encode('utf-8'))
            for name in order:
                frag = fragments.get(name)
                if frag:
                    gz.write(frag)
            gz.write(b'</tv>\n')
    os.replace(tmp, path)


def build_m3u(channels, show_adult=False, group_by_genre=True, add_ua=True,
              user_agent='', use_rec=False, use_ext_logos=False,
              use_local_logos=False, logos_path='', logos_local_path='',
              default_group='SpaceXTV'):
    """Returns (m3u text, list of channels that made it into the playlist)."""
    def _dir(p):
        return p if (not p or p.endswith('/') or p.endswith('\\')) else p + '/'

    logos_path = _dir(logos_path or '')
    logos_local_path = _dir(logos_local_path or '')
    ua = '|User-Agent=%s' % quote_plus(user_agent) if add_ua else ''
    now_ms = str(round(time.time() * 1000))
    out = ['#EXTM3U\n']
    kept = []
    for ch in channels:
        genre = _text(ch.get('genre'))
        if not show_adult and genre == '18+':
            continue
        name = ch['epg_name']
        title = _text(ch.get('title')) or name
        group = genre if group_by_genre else default_group

        catch = ',' + title
        if use_rec and ch.get('ndvr'):
            try:
                ndvr = ch['ndvr']
                catch = ('catchup="default" catchup-source="' + REC_URL + ndvr[ndvr.index(':', 10):]
                         + '&wowzadvrplayliststart={utc:YmdHMS}&wowzadvrplaylistduration={duration}000'
                         + '&request_time=' + now_ms + 'token=38264607382"'
                         + ',' + title
                         + '\n#KODIPROP:inputstream=inputstream.ffmpegdirect'
                         + '\n#KODIPROP:mimetype=application/x-mpegURL'
                         + '\n#KODIPROP:inputstream.ffmpegdirect.stream_mode=timeshift'
                         + '\n#KODIPROP:inputstream.ffmpegdirect.is_realtime_stream=false')
            except ValueError:
                pass

        source = ch.get('ndvr') or ch.get('sources') or ''
        if not source:
            continue

        if use_ext_logos:
            logo = (logos_local_path if use_local_logos else logos_path) + name + '.png'
        else:
            logo = ch.get('logo_selected') or ''

        out.append('#EXTINF:-1 radio="%s" group-title="%s" tvg-logo="%s" tvg-id="%s" %s\n%s%s\n'
                   % (ch.get('radio', False), group, logo, name, catch, source, ua))
        kept.append(ch)
    return ''.join(out), kept


def write_m3u_if_changed(path, text):
    """Write the playlist only if it changed. Returns True if written."""
    new_fp = m3u_fingerprint(text)
    if os.path.exists(path):
        try:
            with open(path, 'rb') as f:
                old = f.read().decode('utf-8', 'replace')
            if m3u_fingerprint(old) == new_fp:
                return False
        except OSError:
            pass
    _atomic_write(path, text.encode('utf-8'))
    return True


# --------------------------------------------------------------------------- #
# Do Bulsat's servers still accept our links?
# --------------------------------------------------------------------------- #
# Links say "valid 600 minutes", but Bulsat ends a session early when the same
# account signs in again (e.g. on another device of the same type). Its links
# are then redirected to .../no_access/limits/... - a server that never answers,
# so Kodi only says "Playback failed". One small request tells the difference.
LINK_OK, LINK_DEAD, LINK_UNKNOWN = 'ok', 'dead', 'unknown'
_REDIRECTS = (301, 302, 303, 307, 308)


def playlist_links(text):
    """[(url, user_agent or None, is_radio)] for every channel in our M3U text."""
    out, radio = [], False
    for line in (text or '').splitlines():
        line = line.strip()
        if line.startswith('#EXTINF'):
            radio = 'radio="True"' in line
        elif line and not line.startswith('#'):
            url, _, opts = line.partition('|')
            ua = None
            for opt in opts.split('&'):
                k, _, v = opt.partition('=')
                if k == 'User-Agent':
                    ua = unquote_plus(v)
            out.append((url.strip(), ua, radio))
    return out


def sample_links(links, n=3):
    """A few TV links, from different servers where possible."""
    tv = [l for l in links if not l[2]] or list(links)
    picked, hosts = [], set()
    for l in tv:
        host = urlparse(l[0]).netloc
        if host not in hosts:
            hosts.add(host)
            picked.append(l)
            if len(picked) >= n:
                return picked
    for l in tv:
        if len(picked) >= n:
            break
        if l not in picked:
            picked.append(l)
    return picked


def _probe(url, user_agent=None, timeout=5.0):
    """'ok' | 'dead' | 'unknown' | 'net' (no connection at all) for one link."""
    headers = {'User-Agent': user_agent or 'Mozilla/5.0', 'Accept': '*/*'}
    for _ in range(4):
        try:
            r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=False, stream=True)
        except requests.RequestException:
            return 'net'
        try:
            code = r.status_code
            if code in _REDIRECTS:
                loc = r.headers.get('Location') or ''
                if 'no_access' in loc.lower():
                    return LINK_DEAD            # Bulsat's "this session has ended" - never follow it
                if not loc:
                    return LINK_UNKNOWN
                url = urljoin(url, loc)         # normal load-balancer hop
                continue
            if code in (401, 403):
                return LINK_DEAD
            if code != 200:
                return LINK_UNKNOWN             # 404 / 5xx: that channel or server, not the session
            try:
                head = next(r.iter_content(4096), b'')
            except Exception:
                return 'net'
            ctype = (r.headers.get('Content-Type') or '').lower()
            if b'#EXTM3U' in head or ctype.startswith(('video/', 'audio/')):
                return LINK_OK
            return LINK_UNKNOWN
        finally:
            r.close()
    return LINK_UNKNOWN


def check_link(url, user_agent=None, timeout=5.0):
    """LINK_OK / LINK_DEAD / LINK_UNKNOWN for one stream link (one small request)."""
    st = _probe(url, user_agent, timeout)
    return LINK_UNKNOWN if st == 'net' else st


def playlist_link_state(text, timeout=5.0, n=3):
    """Are the links in our playlist accepted? LINK_OK as soon as one works,
    LINK_DEAD only if two (or all, if fewer) are refused, else LINK_UNKNOWN
    (e.g. no internet - then renewing would not help anyway)."""
    samples = sample_links(playlist_links(text), n)
    if not samples:
        return LINK_UNKNOWN
    need, dead = min(2, len(samples)), 0
    for url, ua, _ in samples:
        st = _probe(url, ua, timeout)
        if st == LINK_OK:
            return LINK_OK
        if st == 'net':
            return LINK_UNKNOWN                 # no connection - don't wait for the others
        if st == LINK_DEAD:
            dead += 1
            if dead >= need:
                return LINK_DEAD
    return LINK_UNKNOWN
