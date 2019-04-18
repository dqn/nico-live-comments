import requests
import socket
import threading
from bs4 import BeautifulSoup

MIN_DEFAULT_PORT = 2805
MAX_DEFAULT_PORT = 2882
MAX_COMMUNITY_PORT = 2854
DEFAULT_PORT_STEP = 13
COMMUNITY_PORT_STEP = 10

SEND_XML_FORMAT = '<thread thread="{}" res_from="-1" version="{}" scores="1" />\0'
SEND_XML_VERSION = '20061206'
BUFSIZE = 1024

class NicoliveListener:
    def __init__(self, mail, password):
        self.mail = mail
        self.password = password
        self.session = requests.session()

    def execute(self, live_id):
        self.__login()

        if not self.__is_logined():
            return print('Failed to login')

        res = self.__get_player_status(live_id)
        soup = BeautifulSoup(res.text, 'lxml')

        if soup.error:
            return print('Failed to get player status')

        self.on_status(soup)

        rooms = self.__fetch_rooms(
            soup.addr.string,
            int(soup.thread.string),
            int(soup.port.string),
            (soup.provider_type.string == 'community')
        )

        for index, room in enumerate(rooms):
            s = self.__make_socket(room['addr'], room['port'], room['thread'])
            thread = threading.Thread(
                target=self.__receiver,
                args=(index, s),
            )
            thread.daemon = True
            thread.start()

        while True: pass

    def on_status(self, status):
        print(status)

    def on_chat(self, chat):
        print(chat)

    def __login(self):
        url = 'https://account.nicovideo.jp/api/v1/login'
        params = {
            'mail_tel': self.mail,
            'password': self.password,
        }
        self.session.post(url, params=params)

    def __is_logined(self):
        url = 'http://www.nicovideo.jp/'
        res = self.session.get(url)
        return (res.headers['x-niconico-authflag'] == '1')

    def __get_player_status(self, live_id):
        url = 'http://live.nicovideo.jp/api/getplayerstatus/{}'.format(live_id)
        return self.session.get(url)

    def __fetch_rooms(self, addr, thread, port, is_community):
        rooms = [{'addr': addr, 'thread': thread, 'port': port}]
        rooms.extend(self.__seek_adjacent_rooms(addr, thread, port, -1, is_community))
        rooms.extend(self.__seek_adjacent_rooms(addr, thread, port,  1, is_community))
        rooms.sort(key=lambda x: x['thread'])
        return rooms

    def __seek_adjacent_rooms(self, addr, thread, port, direction, is_community):
        min_port  = MIN_DEFAULT_PORT
        max_port  = MAX_COMMUNITY_PORT  if is_community else MAX_DEFAULT_PORT
        port_step = COMMUNITY_PORT_STEP if is_community else DEFAULT_PORT_STEP

        calc_port = lambda port: min_port + (((port % min_port) + (port_step * direction)) % (max_port - min_port)) 

        while True:
            thread += direction
            port = calc_port(port)

            if not self.__is_exists_room(addr, thread, port): return

            yield {'addr': addr, 'thread': thread, 'port': port}

    def __is_exists_room(self, addr, thread, port):
        res = self.__make_socket(addr, port, thread).recv(BUFSIZE)
        return True if BeautifulSoup(res, 'lxml').chat else False

    def __make_socket(self, addr, port, thread):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((addr, port))
        xml = SEND_XML_FORMAT.format(thread, SEND_XML_VERSION)
        s.sendall(xml.encode('UTF-8'))
        return s

    def __receiver(self, index, s):
        while True:
            data = s.recv(BUFSIZE)

            soup = BeautifulSoup(data, 'lxml', from_encoding='utf-8')
            if soup.error or (not soup.chat): continue

            key = ':'.join([soup.chat.get('user_id'), soup.chat.get('date')])
            if not self.__memorize(key): continue

            self.on_chat(soup.chat)

    def __memorize(self, key, memo=set()):
        return False if key in memo else (memo.add(key) or True)

    # for debug
    def __search_thread_port(self, addr, base_thread):
        diff = 5
        for thread in range(base_thread - diff, base_thread + diff):
            for port in range(MIN_DEFAULT_PORT, MAX_DEFAULT_PORT):
                if self.__is_exists_room(addr, thread, port):
                    print(thread, port)
