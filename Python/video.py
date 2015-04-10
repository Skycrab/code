#coding:utf-8
'''
视屏真实地址解析
@author: root
'''
import re
import json
import time
import random
import base64
import urllib2
from urllib import urlencode


_headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Charset': 'UTF-8,*;q=0.5',
    'Accept-Language': 'en-US,en;q=0.8',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:13.0) Gecko/20100101 Firefox/13.0'
}

_headers_iphone = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Charset': 'UTF-8,*;q=0.5',
    'Accept-Language': 'en-US,en;q=0.8',
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 7_1 like Mac OS X) AppleWebKit/537.51.2 (KHTML, like Gecko) Version/7.0 Mobile/11D5145e Safari/9537.53'
}

def request(url,headers=_headers):
    req = urllib2.Request(url, headers=headers)
    try:
        content = urllib2.urlopen(req).read()
    except:
        content = ""
    return content

def match(txt, pattern, n=1):
    try:
        m = pattern.search(txt).group(n)
    except AttributeError:
        m = None
    return m


class Parser(object):
    EXTRACT = {}
    _SITE = re.compile(r".*\.(?P<site>.+?)\.com")

    def parse(self, url):
        try:
            site = self._SITE.search(url).group('site')
            site_parser = self.EXTRACT[site]
        except (AttributeError, KeyError):
            print "[%s] canot parse" %url
            return None, None
        return site_parser.parse(url), site

class VideoMeta(type):
    def __init__(cls, classname, bases, dict_):
        assert hasattr(cls, "parse")
        assert hasattr(cls, "NAME")
        Parser.EXTRACT[dict_["NAME"]] = cls()
        return type.__init__(cls, classname, bases, dict_)



class Video(object):
    __metaclass__ = VideoMeta
    NAME = "BASE"

    def parse(self, url):
        pass


class LeTv(Video):
    """乐视TV"""
    NAME = "letv"

    _vid1 = re.compile(r"http://www.letv.com/ptv/vplay/(\d+).html")
    _vid2 = re.compile(r'vid="(\d+)"')
    def parse(self, url):
        vid = match(url, self._vid1)
        if not vid:
            html = request(url)
            vid = match(html, self._vid2)
        return self.parse_by_vid(vid)

    def parse_by_vid(slef, vid):
        url= slef.video_info(vid)
        return url

    def video_info(self, vid):
        tn = self.get_timestamp()
        key = self.get_key(tn)
        #url ="http://api.letv.com/mms/out/common/geturl?platid=3&splatid=304&callback=&playid=0&vtype=9,13,21,124,125,126&version=2.0&tss=ios&vid={0}&domain=www.letv.com&tkey={1}&_r=0".format(vid, key)
        url ="http://api.letv.com/mms/out/common/geturl?platid=3&splatid=304&callback=&playid=0&vtype=9,13,21,124,125,126&version=2.0&tss=Linux&vid={0}&domain=www.letv.com&tkey={1}&_r=0".format(vid, key)
        print url
        r = request(url)
        url = json.loads(r)["data"][-1]["infos"][-1]["backUrl2"]
        print url
        return url

    def get_timestamp(self):
        tn = random.random()
        url = 'http://api.letv.com/time?tn={}'.format(tn)
        result = request(url)
        return json.loads(result)['stime']

    def get_key(self, t):
        for s in range(0, 8):
            e = 1 & t
            t >>= 1
            e <<= 31
            t += e
        return t ^ 185025305

        
class YouKu(Video):
    """优酷"""
    NAME = "youku"

    _vid = re.compile(r"youku\.com/v_show/id_([\w=]+)")
    def parse(self, url):
        vid = match(url, self._vid)
        return self.parse_by_vid(vid)

    def parse_by_vid(slef, vid):
        url= slef.video_info(vid)
        return url

    def video_info(self, vid):
        r = request('http://v.youku.com/player/getPlayList/VideoIDS/%s/Pf/4/ctype/12/ev/1' % vid)
        meta = json.loads(r)
        metadata0 = meta['data'][0]
        ep, ip = metadata0['ep'], metadata0['ip']
        new_ep, sid, token = self.generate_ep(vid, ep)
        m3u8_query = urlencode(dict(
            ctype=12,
            ep=new_ep,
            ev=1,
            keyframe=1,
            oip=ip,
            sid=sid,
            token=token,
            ts=int(time.time()),
            type='mp4',
            vid=vid,
        ))
        m3u8_url = 'http://pl.youku.com/playlist/m3u8?' + m3u8_query
        return m3u8_url


    def generate_ep(self, vid, ep):
        f_code_1 = 'becaf9be'
        f_code_2 = 'bf7e5f01'

        def trans_e(a, c):
            f = h = 0
            b = list(range(256))
            result = ''
            while h < 256:
                f = (f + b[h] + ord(a[h % len(a)])) % 256
                b[h], b[f] = b[f], b[h]
                h += 1
            q = f = h = 0
            while q < len(c):
                h = (h + 1) % 256
                f = (f + b[h]) % 256
                b[h], b[f] = b[f], b[h]
                if isinstance(c[q], int):
                    result += chr(c[q] ^ b[(b[h] + b[f]) % 256])
                else:
                    result += chr(ord(c[q]) ^ b[(b[h] + b[f]) % 256])
                q += 1

            return result

        e_code = trans_e(f_code_1, base64.b64decode(ep))
        sid, token = e_code.split('_')
        new_ep = trans_e(f_code_2, '%s_%s_%s' % (sid, vid, token))
        return base64.b64encode(new_ep), sid, token

parser = Parser()
#print parser.parse('http://www.letv.com/ptv/vplay/1856422.html')
