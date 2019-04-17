import sys
import time
import requests
import socket
import threading
from bs4 import BeautifulSoup

SEND_XML_FORMAT = '<thread thread="{}" res_from="-1" version="{}" scores="1" />\0'
VERSION = '20061206'

def login(session, mail, password):
    url = 'https://account.nicovideo.jp/api/v1/login'
    params = {
        'mail_tel': mail,
        'password': password,
    }
    session.post(url, params=params)

def is_logined(session):
    url = 'http://www.nicovideo.jp/'
    res = session.get(url)
    return (res.headers['x-niconico-authflag'] == '1')

def get_player_status(session, live_id):
    url = 'http://live.nicovideo.jp/api/getplayerstatus/{}'.format(live_id)
    return session.get(url)

def fetch_rooms(session, addr, thread, port, is_community):
    rooms = [{'addr': addr, 'thread': thread, 'port': port}]
    rooms.extend(seek_adjacent_rooms(addr, thread, port, -1, is_community))
    rooms.extend(seek_adjacent_rooms(addr, thread, port,  1, is_community))
    rooms.sort(key=lambda x: x['thread'])
    return rooms

def seek_adjacent_rooms(addr, thread, port, direction, is_community):
    port_min = 2805
    port_max = 2854 if is_community else 2882
    step     = 10   if is_community else 13

    rooms = []

    while True:
        thread += direction
        port = port_min + (((port % port_min) + (step * direction)) % (port_max - port_min))

        if not is_exists_room(addr, thread, port):
            break

        rooms.append({'addr': addr, 'thread': thread, 'port': port})

    return rooms

def is_exists_room(addr, thread, port):
    res = make_socket(addr, port, thread).recv(1024)
    return True if BeautifulSoup(res, 'lxml').chat else False

def make_socket(addr, port, thread):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((addr, port))
    xml = SEND_XML_FORMAT.format(thread, VERSION)
    s.sendall(xml.encode('UTF-8'))
    return s

def receiver(index, s):
    while True:
        data = s.recv(1024)

        soup = BeautifulSoup(data, 'lxml', from_encoding='utf-8')
        if soup.error or (not soup.chat):
            continue

        key = ':'.join([soup.chat.get('user_id'), soup.chat.get('date')])
        if not memorize(key):
            continue

        print('ROOM[{:0>2}]: {}'.format(index, soup.chat.string))

def memorize(key, memo=set()):
    if key in memo:
        return False
    else:
        memo.add(key)
        return True

# for debug
def search_thread_port(addr, base_thread):
    thread_range = range(base_thread - 2, base_thread + 5)
    port_range   = range(2805, 2883)

    for thread in thread_range:
        for port in port_range:
            if is_exists_room(addr, thread, port):
                print(thread, port)

def usage():
    print('Usage: python fetch.py [mail] [password] [live id]')

def main():
    if len(sys.argv) != 4:
        return usage()

    session = requests.session()
    login(session, sys.argv[1], sys.argv[2])

    if not is_logined(session):
        return print('Failed to login')
        
    res = get_player_status(session, sys.argv[3])
    soup = BeautifulSoup(res.text, 'lxml')

    if soup.error:
        return print('Failed to get player status')

    status = {
        'title': soup.title.string,
        'description': soup.description.string,
        'provider_type': soup.provider_type.string,
        'watch_count': soup.watch_count.string,
        'comment_count': soup.comment_count.string,
        'start_time': soup.start_time.string,
        'end_time': soup.end_time.string,
        'room_label': soup.room_label.string,
    }

    rooms = fetch_rooms(
        session,
        soup.addr.string,
        int(soup.thread.string),
        int(soup.port.string),
        (soup.provider_type.string == 'community')
    )

    for index, room in enumerate(rooms):
        s = make_socket(room['addr'], room['port'], room['thread'])
        thread = threading.Thread(
            target=receiver,
            args=(index, s),
        )
        thread.daemon = True
        thread.start()

    while True:
        pass

if __name__ == '__main__':
    main()
