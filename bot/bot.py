import vk_api
from random import randrange
from vk_api.longpoll import VkLongPoll, VkEventType
from datetime import date, datetime

from .database import DBInstance

BASE_URL = 'https://vk.com/'
USERS_SEARCH_CNT = 100
INF = -10000000


class VKBot:
    def __init__(self, bot_token, access_token):
        if bot_token is None:
            bot_token = input('Введите ключ доступа для работы VK бота: ')
        self.bot_session = vk_api.VkApi(token=bot_token)
        if access_token is None:
            access_token = input('Введите access_token для работы приложения: ')
        self.app_session = vk_api.VkApi(token=access_token)
        self.long_poll = VkLongPoll(self.bot_session)
        self.db = DBInstance()

    def write_msg(self, user_id, message):
        params = {
            'user_id': user_id,
            'message': message,
            'random_id': randrange(10 ** 7)
        }
        self.bot_session.method(method='messages.send',
                                values=params)

    def greet(self):
        for event in self.long_poll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                return int(event.user_id)

    def get_age(self, user_id):
        for event in self.long_poll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.user_id == user_id:
                ages = event.text.lower()
                if '-' in ages:
                    age_from, age_to = map(int, ages.split('-'))
                    return age_from, age_to
                elif ', ' in ages:
                    age_from, age_to = map(int, ages.split(', '))
                    return age_from, age_to
                elif ',' in ages:
                    age_from, age_to = map(int, ages.split(','))
                    return age_from, age_to
                elif ' ' in ages:
                    age_from, age_to = map(int, ages.split(' '))
                    return age_from, age_to
                else:
                    self.write_msg(event.user_id,
                                   'Некорректно указан возраст. Укажите минимальный и максимальный возраст '
                                   'через запятую, пробел или дефис')
                    continue

    def get_city(self, user_id):
        for event in self.long_poll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.user_id == user_id:
                city = event.text.lower()
                params = {
                    'country_id': 1,
                    'q': city,
                    'need_all': 0,
                    'count': 1
                }
                try:
                    city_ids = self.app_session.method(method='database.getCities',
                                                       values=params)
                    return int(city_ids['items'][0]['id'])
                except LookupError:
                    self.write_msg(event.user_id, 'Такого города не существует, попробуйте ещё раз.')
                    continue

    def get_sex(self, user_id):
        for event in self.long_poll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.user_id == user_id:
                sex = event.text.lower()
                if sex in {'мужчина', 'муж', 'м', 'мужчину'}:
                    return 2
                elif sex in {'женщина', 'жен', 'ж', 'женщину'}:
                    return 1
                else:
                    self.write_msg(event.user_id, 'Необходимо написать \'Мужчина\' или \'Женщина\' ')
                    continue

    def search_new_users(self, age_from, age_to, city, sex):
        params = {
            'is_closed': 'False',
            'count': USERS_SEARCH_CNT,
            'fields': 'city, domain, bdate, sex',
            'age_from': age_from,
            'age_to': age_to,
            'city': city,
            'sex': sex,
            'status': 1 or 6,
            'has_photo': 1
        }
        try:
            responce = self.app_session.method(method='users.search',
                                               values=params)
        except vk_api.exceptions.ApiError:
            return

        for user_data in responce['items']:
            if 'city' not in user_data.keys() or 'bdate' not in user_data.keys():
                continue
            today = date.today()
            bday = datetime.strptime(user_data['bdate'], '%d.%m.%Y').date()
            age = today.year - bday.year - ((today.month, today.day) < (bday.month, bday.day))
            item = {
                'user_id': user_data['id'],
                'first_name': user_data['first_name'],
                'last_name': user_data['last_name'],
                'age': age,
                'city': user_data['city']['id'],
                'seen': False,
                'user_url': BASE_URL + user_data['domain'],
                'sex': user_data['sex']
            }
            self.db.insert_searched_user(item)

    def search_users(self, user_id):
        age_from, age_to, city, sex = self.db.search_preferences(user_id)
        users_info = self.db.get_users_by_criteria(age_from, age_to, city, sex)
        while len(users_info) < 3:
            self.search_new_users(age_from, age_to, city, sex)
            users_info = self.db.get_users_by_criteria(age_from, age_to, city, sex)
        return users_info

    def get_data_to_send(self, ids):
        result_data = []
        for id in ids:
            params = {
                'owner_id': id,
                'extended': 1
            }
            try:
                user_photos = self.app_session.method(method='photos.getAll',
                                                      values=params)
            except vk_api.exceptions.ApiError:
                continue
            photos_count = user_photos['count']
            user_photos = user_photos['items']
            for photo in user_photos:
                local_params = {
                    'photo_id': photo['id']
                }
                try:
                    photo['comments'] = self.app_session.method(method='photos.getComments',
                                                                values=local_params)['count']
                except vk_api.exceptions.ApiError:
                    photo['comments'] = INF
                    continue
            user_photos.sort(key=lambda x: x['likes']['count'] + x['comments'],
                             reverse=True)
            best_user_photos = {
                'owner_id': id,
                'photos_cnt': min(3, photos_count)
            }
            for i in range(min(3, photos_count)):
                best_user_photos[f'photo{i}_url'] = f'photo{id}_{user_photos[i]["id"]}'
            result_data.append(best_user_photos)
        return result_data

    def send_users(self, user_id, data):
        for event in self.long_poll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.user_id == user_id:
                ans = event.text.lower()
                if ans == 'да':
                    match_users_ids = [user_data[0] for user_data in data]
                    responce_data = self.get_data_to_send(match_users_ids)
                    for user_data, user_photos in zip(data, responce_data):
                        self.write_msg(event.user_id,
                                       f'{user_data[2]} {user_data[3]}, '
                                       f'возраст - {user_data[5]}, {user_data[1]}')
                        for i in range(min(3, user_photos['photos_cnt'])):
                            params = {
                                'user_id': event.user_id,
                                'attachment': user_photos[f'photo{i}_url'],
                                'random_id': randrange(10 ** 7)
                            }
                            self.bot_session.method(method='messages.send',
                                                    values=params)
                    self.db.update_seen_users(match_users_ids)
                    return True
                elif ans == 'нет':
                    return False
                else:
                    self.write_msg(event.user_id,
                                   'Ответом должно быть \'Да\' или \'Нет\'')
                    continue

    def register_user(self, user_id):
        self.write_msg(user_id,
                       f'Привет. '
                       f'Укажите минимальный и максимальный возраст Вашего партнера '
                       f'(через пробел, запятую или дефис). '
                       f'Например: 20-25')
        age_from, age_to = self.get_age(user_id)
        self.write_msg(user_id, 'В каком городе ищем Вашу вторую половинку?')
        city = self.get_city(user_id)
        self.write_msg(user_id, 'Ваш избранник мужчина или женщина?')
        sex = self.get_sex(user_id)
        self.db.register_user(user_id, age_from, age_to, city, sex)

    def process_registered_user(self, user_id):
        self.write_msg(user_id,
                       'Найдена Ваша анкета. Осуществить поиск по ней? Ответьте \'Да\' или \'Нет\'')
        for event in self.long_poll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                ans = event.text.lower()
                if ans == 'да':
                    return
                elif ans == 'нет':
                    self.register_user(user_id)
                    return
                else:
                    self.write_msg(user_id,
                                   'Необходимо ответить \'Да\' или \'Нет\'')
                    continue

    def start_routine(self):
        while True:
            user_id = self.greet()
            if not self.db.is_registered(user_id):
                self.register_user(user_id)
            else:
                self.process_registered_user(user_id)

            res = self.search_users(user_id)
            self.write_msg(user_id,
                           'Есть несколько подходящих людей. Показать?')
            while self.send_users(user_id, res):
                res = self.search_users(user_id)
                self.write_msg(user_id, 'Отправить ещё?')
            self.write_msg(user_id, 'До свидания!')
