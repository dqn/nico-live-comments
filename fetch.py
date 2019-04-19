import sys
from nicolive_listener import NicoliveListener

class MyListener(NicoliveListener):
    def on_status(self, status):
        print('title: {}'.format(status.title.string))
        print('description: {}'.format(status.description.string))
        print('provider_type: {}'.format(status.provider_type.string))
        print('watch_count: {}'.format(status.watch_count.string))
        print('comment_count: {}'.format(status.comment_count.string))
        print('start_time: {}'.format(status.start_time.string))
        print('end_time: {}'.format(status.end_time.string))
        print('room_label: {}'.format(status.room_label.string))
        print()

    def on_chat(self, chat):
        print('thread[{}]: {}'.format(chat.get('thread'), chat.string))

def usage():
    print('Usage: python fetch.py <mail> <password> <live_id>')

def main():
    if len(sys.argv) != 4:
        return usage()

    listener = MyListener(sys.argv[1], sys.argv[2])
    listener.execute(sys.argv[3])

if __name__ == '__main__':
    main()
