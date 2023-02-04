import os
from bot import VKBot

token = os.environ.get('BOT_TOKEN')
access_token = os.environ.get('ACCESS_TOKEN')


if __name__ == '__main__':
    vkinder = VKBot(bot_token=token, access_token=access_token)
    vkinder.start_routine()
