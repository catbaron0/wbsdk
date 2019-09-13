from typing import Tuple, Dict, Optional
from requests import Session
from logger import logger
import requests
import base64
import re
import json
import rsa
import binascii
import time
import pickle

from .weibo_message import WeiboMessage

MAX_IMAGES = 9


def encrypt_passwd(
        passwd: str, pubkey: str, servertime: str, nonce: str
        ) -> str:
    key = rsa.PublicKey(int(pubkey, 16), int('10001', 16))
    message = str(servertime) + '\t' + str(nonce) + '\n' + str(passwd)
    passwd = rsa.encrypt(message.encode('utf-8'), key)
    return binascii.b2a_hex(passwd)


class Weibo:
    '''
    Weibo class.
    To initialize, pass username and password to login,
    or pass a session.
    '''
    def __init__(self, username: str, password: str, session: str = ''):
        '''
        Login and save the session and uid.
        :param usr/pwd: str, Optional[str], username and password for login.
        :param session: str, pickle file of saved session.
        '''
        self.username = username
        self.password = password
        self.user_agent = (
            'Mozilla/5.0 (Windows NT 5.1) '
            'AppleWebKit/536.11 (KHTML, like Gecko) '
            'Chrome/20.0.1132.57 Safari/536.11'
        )

        self.wc = 'ssologin.js(v1.4.18)'
        self.su = base64.b64encode(
            requests.utils.quote(username).encode('utf-8')
        )

        self.login_url = \
            'http://login.sina.com.cn/sso/prelogin.php?'\
            'entry=weibo&callback=sinaSSOController.preloginCallBack'\
            f'&su={self.su}&rsakt=mod&checkpin=1&client={self.wc}'
        self.login_data_url = \
            'http://weibo.com/ajaxlogin.php?framelogin=1'\
            '&callback=parent.sinaSSOController.feedBackUrlCallBack',
        self.login_list_url = \
            f'http://login.sina.com.cn/sso/login.php?client={self.wc}'

        if session:
            with open(session, 'rb') as f:
                self.session = pickle.load(f)
        else:
            self.session = self.login(self.username, self.password)

    @property
    def rt_url(self):
        t = int(time.time() * 100)
        return f'https://www.weibo.com/aj/v6/mblog/forward?ajwvr=6&__rnd={t}'

    @property
    def tw_url(self):
        t = int(time.time() * 100)
        return 'https://www.weibo.com/aj/mblog/add?'\
               f'ajwvr=6&domain=100505&__rnd={t}'

    @property
    def pic_url(self):
        t = int(time.time())
        url = 'http://picupload.service.weibo.com/interface/pic_upload.php?'\
              'mime=image%2Fjpeg&data=base64&url=0&markpos=1&logo=&nick=0&'\
              'marks=1&app=miniblog&cb=http://weibo.com/aj/static/'\
              f'upimgback.html?_wv=5&callback=STK_ijax_{t}'
        return url

    def login(self, username: str, password: str) -> Session:
        session = requests.session()
        session.headers['User-Agent'] = self.user_agent
        resp = session.get(self.login_url)

        # Read json data between `{}` from response
        pre_login_str = re.match(r'[^{]+({.+?})', resp.text).group(1)
        pre_login = json.loads(pre_login_str)
        sp = encrypt_passwd(
            password, pre_login['pubkey'],
            pre_login['servertime'], pre_login['nonce']
        )
        data = {
            'entry': 'weibo',
            'gateway': 1,
            'from': '',
            'savestate': 7,
            'userticket': 1,
            'ssosimplelogin': 1,
            'su': self.su,
            'service': 'miniblog',
            'servertime': pre_login['servertime'],
            'nonce': pre_login['nonce'],
            'vsnf': 1,
            'vsnval': '',
            'pwencode': 'rsa2',
            'sp': sp,
            'rsakv': pre_login['rsakv'],
            'encoding': 'UTF-8',
            'prelt': '53',
            'url': self.login_data_url,
            'returntype': 'META'
        }

        resp = session.post(self.login_list_url, data=data)
        match_obj = re.search('replace\\(\'([^\']+)\'\\)', resp.text)
        if match_obj is None:
            logger.info('Failed to login!')
            return None

        login_url = match_obj.group(1)
        resp = session.get(login_url)
        login_str = login_str = re.search('\((\{.*\})\)', resp.text).group(1)
        login_info = json.loads(login_str)
        logger.info('login success：[%s]', str(login_info))
        uid = login_info['userinfo']['uniqueid']
        session.headers['Referer'] = f'http://www.weibo.com/u/{uid}/home?wvr=5'
        with open('login.sess', 'wb') as f:
            pickle.dump(session, f)
        return session

    def retweet(self, wb_msg: WeiboMessage) -> Tuple[bool, Dict]:
        '''
        :param wb_msg: WeiboMessage, 
        '''
        if wb_msg.is_empty:
            logger.info('The weibo message is empty!')
            return
        data = wb_msg.get_rt_data()
        res = self.session.post(self.rt_url, data=data)
        try:
            res = json.loads(res.text)
        except Exception:
            res = {'code': '-1', 'msg': res.text}
        code: str = res['code']
        succ: bool = False
        if code == '100000':
            logger.info('微博[%s]转发成功' % str(weibo))
            succ = True
        else:
            logger.info('微博[%s]转发失败: %s: %s', str(weibo), code, res['msg'])
            logger.info('rt_mid: %s', str(weibo.rt_mid))
            succ = False
        return succ, res

    def tweet(self, weibo: WeiboMessage) -> Tuple[bool, Dict]:
        if weibo.is_empty:
            logger.info('没有获得信息，不发送')
            return

        data = weibo.get_send_data()
        res = self.session.post(self.tw_url, data=data)
        try:
            res = json.loads(res.text)
        except Exception:
            res = {'code': '-1', 'msg': res.text}

        code: str = res['code']
        succ: bool = False
        if code == '100000':
            logger.info('Sucessed! %s' % str(weibo))
            succ = True
        else:
            logger.info('Failed! %s: %s', code, res['msg'])
            succ = False
        return succ, res

    def upload_images(self, images):
        pids = ""
        if len(images) > MAX_IMAGES:
            images = images[0: MAX_IMAGES]
        for image in images:
            pid = self.upload_image_stream(image)
            if pid:
                pids += " " + pid
            time.sleep(10)
        return pids.strip()

    def upload_image_stream(self, img_fn):
        url = self.pic_url
        image_name = img_fn
        try:
            with open(img_fn, 'rb') as f:
                img = base64.b64encode(f.read())
            resp = self.session.post(url, data={'b64_data': img})
            upload_json = re.search('{.*}}', resp.text).group(0)
            result = json.loads(upload_json)
            code = result["code"]
            if code == "A00006":
                pid = result["data"]["pics"]["pic_1"]["pid"]
                return pid
        except Exception:
            logger.info(u"图片上传失败：%s" % image_name)
        return None
