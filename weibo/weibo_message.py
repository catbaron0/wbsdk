# -*- coding: utf-8 -*-
from typing import Optional, List
import os


class WeiboMessage(object):
    """weibo message struct"""
    def __init__(self, text: str, images: Optional[List[str]] = None):
        '''
        :param text: str, text to send.
        :param images: Optional[List[str]], a list of image URLs.
        '''
        super(WeiboMessage, self).__init__()
        self.text = text
        # self.text = self.text.replace('@', 'rp @'+u'\ufeff')
        self.images = images
        self.pids = ""
        self.rt = False
        self.rt_mid = ""
        self.pids = ""

    @property
    def has_image(self):
        return self.images is not None and len(self.images) > 0

    @property
    def is_empty(self):
        return len(self.text) == 0 and not self.has_image

    @property
    def is_retweet(self):
        return self.rt

    def get_send_data(self):
        # if not pids:
        #     pids = self.pids
        data = {
            "location": "v6_content_home",
            "appkey": "",
            "style_type": "1",
            "pic_id": self.pids,
            "text": self.text,
            "pdetail": "",
            "rank": "0",
            "rankid": "",
            "module": "stissue",
            "pub_type": "dialog",
            "_t": "0",
        }
        return data

    def get_rt_data(self):
        # if not pids:
        #     pids = self.pids
        # if not mid:
        #     mid = '4380981861287509',
        data = {
            "location": "page_100505_home",
            "appkey": "",
            "style_type": "1",
            "pic_id": self.pids,
            "reason": self.text,
            "rank": "0",
            "rankid": "0",
            "module": '',
            "pic_src": "",
            "mid": self.rt_mid,
            "mark": "",
            "page_module_id": "",
            "refer_sort": "",
            "isReEdit": "false",
            "_t": "0"
        }
        return data

    def __str__(self):
        return "text: " + self.text + os.linesep \
            + "images: " + str(self.images)
