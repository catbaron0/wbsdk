from typing import Tuple, Dict
from requests import Session
from logger import logger
import requests
import base64
import re
import json
import rsa
import binascii
import time

from weibo_message import WeiboMessage


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
    def __init__(self, username: Optional[str], password: Optional[str]):
        '''
        Login and save the session and uid.
        :param usr/pwd: Optional[str], username and password for login.
        '''
        self.username = username
        self.password = password
        self.user_agent = (
            'Mozilla/5.0 (Windows NT 5.1) '
            'AppleWebKit/536.11 (KHTML, like Gecko) '
            'Chrome/20.0.1132.57 Safari/536.11'
        )
        self.webclient = 'ssologin.js(v1.4.18)'
        # self.session, self.uid = self.login(self.username, self.password)
        self.session = self.login(self.username, self.password)

        self.login_url = 'http://login.sina.com.cn/sso/prelogin.php?entry=weibo'\
                         '&callback=sinaSSOController.preloginCallBack&' \
                         'su=%s&rsakt=mod&checkpin=1&client=%s' % \
                         (base64.b64encode(username.encode('utf-8')), self.webclient) 
    def login(self, username: str, password: str) -> Session:
        session = requests.session()
        session.headers['User-Agent'] = self.user_agent
        resp = session.get(
            'http://login.sina.com.cn/sso/prelogin.php?'
            'entry=weibo&callback=sinaSSOController.preloginCallBack&'
            'su=%s&rsakt=mod&checkpin=1&client=%s' %
            (base64.b64encode(username.encode('utf-8')), self.webclient)
        )

        # Read json data between `{}` from response
        pre_login_str = re.match(r'[^{]+({.+?})', resp.text).group(1)
        pre_login = json.loads(pre_login_str)
        su = base64.b64encode(requests.utils.quote(username).encode('utf-8')),
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
            'su': su,
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
            'url': 'http://weibo.com/ajaxlogin.php?framelogin=1'
                   '&callback=parent.sinaSSOController.feedBackUrlCallBack',
            'returntype': 'META'
        }

        login_url_list = 'http://login.sina.com.cn/sso/' \
                         + f'login.php?client={self.webclient}'

        resp = session.post(login_url_list, data=data)
        logger.debug(resp.text)
        match_obj = re.search('replace\\(\'([^\']+)\'\\)', resp.text)
        if match_obj is None:
            logger.info('登录失败，请检查登录信息')
            return (None, None)

        login_url = match_obj.group(1)
        resp = session.get(login_url)
        # login_str = login_str = re.search('\((\{.*\})\)', resp.text).group(1)
        login_str = login_str = re.search('\((\{.*\})\)', resp.text).group(1)
        login_info = json.loads(login_str)
        logger.info('login success：[%s]', str(login_info))
        uid = login_info['userinfo']['uniqueid']
        session.headers['Referer'] = f'http://www.weibo.com/u/{uid}/home?wvr=5'
        # return (session, uid)
        return session

    def retweet(self, wb_msg: WeiboMessage) -> Tuple[bool, Dict]:
        if wb_msg.is_empty:
            logger.info('The weibo message is empty!')
            return
        data = wb_msg.get_rt_data()
        t = int(time.time() * 100)
        rt_url = f'https://www.weibo.com/aj/v6/mblog/forward?ajwvr=6&__rnd={t}'
        res = self.session.post(rt_url, data=data)
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

    def send_weibo(self, weibo) -> Tuple[bool, Dict]:
        if weibo.is_empty:
            logger.info('没有获得信息，不发送')
            return

        data = weibo.get_send_data()
        self.session.headers["Referer"] = self.Referer
        send_url = "https://www.weibo.com/aj/mblog/add?\
                    ajwvr=6&domain=100505&__rnd=%d" % int(time.time() * 1000)
        res = self.session.post(send_url, data=data)
        try:
            res = json.loads(res.text)
        except Exception:
            res = {'code': '-1', 'msg': res.text}
        code: str = res['code']
        succ: bool = False
        if code == '100000':
            logger.info('微博[%s]发送成功' % str(weibo))
            succ = True
        else:
            logger.info('微博[%s]发送失败: %s: %s', str(weibo), code, res['msg'])
            succ = False
            # raise Exception(f'Failed to send weibo: {res["msg"]}')
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

    def upload_image_stream(self, image_url):
        if ADD_WATERMARK:
            url = "http://picupload.service.weibo.com/interface/pic_upload.php?\
            app=miniblog&data=1&url=" \
                + WATERMARK_URL + "&markpos=1&logo=1&nick=" \
                + WATERMARK_NIKE + \
                "&marks=1&mime=image/jpeg&ct=0.5079312645830214"

        else:
            url = "http://picupload.service.weibo.com/interface/pic_upload.php?\
            rotate=0&app=miniblog&s=json&mime=image/jpeg&data=1&wm="

        # self.http.headers["Content-Type"] = "application/octet-stream"
        image_name = image_url
        try:
            f = self.session.get(image_name, timeout=30)
            img = f.content
            resp = self.session.post(url, data=img)
            upload_json = re.search('{.*}}', resp.text).group(0)
            result = json.loads(upload_json)
            code = result["code"]
            if code == "A00006":
                pid = result["data"]["pics"]["pic_1"]["pid"]
                return pid
        except Exception:
            logger.info(u"图片上传失败：%s" % image_name)
        return None



    # if __name__ == '__main__':
    #     (http, uid) = wblogin()
    #     text = http.get('http://weibo.com/').text
    #     print(text)