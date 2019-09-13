import os


class WeiboMessage(object):
    """weibo message struct"""
    def __init__(self, text: str, pids: str = '', rt_mid: str = ''):
        '''
        :param text: str, text to send.
        :param images: Optional[List[str]], a list of image URLs.
        '''
        super(WeiboMessage, self).__init__()
        # self.text = self.text.replace('@', 'rp @'+u'\ufeff')
        self.text = text
        self.pids = pids
        self.rt_mid = rt_mid

    @property
    def has_image(self):
        return bool(self.pids)

    @property
    def is_empty(self):
        return len(self.text) == 0 and not self.has_image

    @property
    def is_retweet(self):
        return bool(self.rt_mid)

    @property
    def data(self):
        if self.is_retweet:
            return self.retweet_data
        else:
            return self.tweet_data

    @property
    def tweet_data(self):
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

    @property
    def retweet_data(self):
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
            + "images: " + self.pids
