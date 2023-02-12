import vk_api
from random import randrange
from vk_api.longpoll import VkLongPoll, VkEventType
from datetime import date, datetime

from .database import DBInstance

BASE_URL = 'https://vk.com/'
USERS_SEARCH_CNT = 900
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

    def start(self):
        for event in self.long_poll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                self.write_msg(event.user_id,
                               f'Привет, добро пожаловать в бот для знакомств Vkinder! '
                               f'Бот подберет Вам пару на основе информации на Вашей странице. '
                               f'Для того, чтобы подобрать Вам партнера, скажите \'Окей\'')
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
                except {KeyError, LookupError}:
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

    def get_user_data(self, user_id):
        params = {
            'user_ids': [user_id],
            'fields': 'city, sex, bdate'
        }
        user_info = self.bot_session.method(method='users.get',
                                            values=params)[0]
        user_age = self.get_age_from_bdate(user_info.get('bdate', None))
        try:
            user_city = user_info['city']['id']
        except KeyError:
            user_city = None
        user_sex = user_info.get('sex', None)
        return user_age, user_city, user_sex

    def register_user(self, user_id):
        user_age, user_city, user_sex = self.get_user_data(user_id)
        if user_age is None:
            self.write_msg(user_id,
                           f'Укажите минимальный и максимальный возраст Вашего партнера '
                           f'(через пробел, запятую или дефис). '
                           f'Например: 20-25')
            age_from, age_to = self.get_age(user_id)
        else:
            age_from, age_to = user_age - 2, user_age + 2
        if user_city is None:
            self.write_msg(user_id, 'В каком городе ищем Вашу вторую половинку?')
            city = self.get_city(user_id)
        else:
            city = user_city
        if user_sex is None:
            self.write_msg(user_id, 'Ваш избранник мужчина или женщина?')
            sex = self.get_sex(user_id)
        else:
            sex = 2 if user_sex == 1 else 1
        self.db.register_user(user_id, age_from, age_to, city, sex)
        return age_from, age_to, city, sex

    def re_register(self, user_id):
        self.write_msg(user_id,
                       'Хотите зарегистрироваться заново? Ответьте \'Да\' или \'Нет\'')
        for event_ in self.long_poll.listen():
            if event_.type == VkEventType.MESSAGE_NEW and event_.to_me:
                ans = event_.text.lower()
                if ans == 'да':
                    age_from, age_to, city, sex = self.register_user(user_id)
                    return age_from, age_to, city, sex
                elif ans == 'нет':
                    return None, None, None, None
                else:
                    self.write_msg(user_id,
                                   'Необходимо ответить \'Да\' или \'Нет\'')
                    continue

    def process_registered_user(self, user_id):
        self.write_msg(user_id,
                       'Найдена Ваша анкета. Осуществить поиск по ней? Ответьте \'Да\' или \'Нет\'')
        for event in self.long_poll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                ans = event.text.lower()
                if ans == 'да':
                    age_from, age_to, city, sex = self.db.search_preferences(user_id)
                    return age_from, age_to, city, sex
                elif ans == 'нет':
                    age_from, age_to, city, sex = self.re_register(user_id)
                    return age_from, age_to, city, sex
                else:
                    self.write_msg(user_id,
                                   'Необходимо ответить \'Да\' или \'Нет\'')
                    continue

    @staticmethod
    def get_age_from_bdate(bdate):
        if bdate is None:
            return None
        today = date.today()
        try:
            bday = datetime.strptime(bdate, '%d.%m.%Y').date()
        except ValueError:
            return None
        age = today.year - bday.year - ((today.month, today.day) < (bday.month, bday.day))
        return age

    def search_new_users(self, age_from, age_to, city, sex):
        params = {
            'is_closed': 0,
            'count': USERS_SEARCH_CNT,
            'fields': 'city, domain, bdate, sex',
            'age_from': age_from,
            'age_to': age_to,
            'city': city,
            'sex': sex,
            'has_photo': 1,
        }
        data = []
        for status in (1, 6):
            params['status'] = status
            responce = self.app_session.method(method='users.search',
                                               values=params)
            try:
                data += responce['items']
            except KeyError:
                pass
        return_data = []
        for user_data in data:
            if 'city' not in user_data.keys() or 'bdate' not in user_data.keys() \
                    or user_data['is_closed'] is True:
                continue
            age = self.get_age_from_bdate(user_data['bdate'])
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
            return_data.append(item)
        return return_data

    def get_user_best_photos(self, user_id):
        params = {
            'owner_id': user_id,
            'extended': 1
        }
        user_photos = self.app_session.method(method='photos.getAll',
                                              values=params)
        try:
            user_photos['items']
        except KeyError:
            return {}
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
            'owner_id': user_id,
            'photos_cnt': min(3, photos_count)
        }
        for i in range(min(3, photos_count)):
            best_user_photos[f'photo{i}_url'] = f'photo{user_id}_{user_photos[i]["id"]}'
        return best_user_photos

    @staticmethod
    def get_next_matches(matches):
        res = []
        for i, user in enumerate(matches):
            if user['seen'] is True:
                continue
            else:
                user['match_index'] = i
                res.append(user)
            if len(res) == 3:
                break
        return res

    def send_users(self, user_id, data):
        for event in self.long_poll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.user_id == user_id:
                ans = event.text.lower()
                if ans == 'да':
                    for user_data in data:
                        self.write_msg(event.user_id,
                                       f'{user_data["first_name"]} {user_data["last_name"]}, '
                                       f'возраст - {user_data["age"]}.\n'
                                       f'Ссылка на страницу - {user_data["user_url"]}')
                        user_photos = self.get_user_best_photos(user_data['user_id'])
                        for i in range(user_photos['photos_cnt']):
                            params = {
                                'user_id': event.user_id,
                                'attachment': user_photos[f'photo{i}_url'],
                                'random_id': randrange(10 ** 7)
                            }
                            self.bot_session.method(method='messages.send',
                                                    values=params)
                    return [match['match_index'] for match in data]
                elif ans == 'нет':
                    return []
                else:
                    self.write_msg(event.user_id,
                                   'Ответом должно быть \'Да\' или \'Нет\'')
                    continue

    def start_routine(self):
        while True:
            user_id = self.start()
            for event in self.long_poll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.user_id == user_id:
                    if event.text.lower() == 'окей':
                        break
            if not self.db.is_registered(user_id):
                age_from, age_to, city, sex = self.register_user(user_id)
            else:
                age_from, age_to, city, sex = self.process_registered_user(user_id)

            if age_from is None:
                self.write_msg(user_id, 'До свидания!')
                continue

            matches = self.search_new_users(age_from, age_to, city, sex)
            res = self.get_next_matches(matches)
            self.write_msg(user_id,
                           'Есть несколько подходящих людей. Показать?')
            seen_ids = self.send_users(user_id, res)
            while seen_ids:
                for id_ in seen_ids:
                    matches[id_]['seen'] = True
                self.write_msg(user_id, 'Отправить ещё?')
                res = self.get_next_matches(matches)
                if len(res) < 3:
                    matches = self.search_new_users(age_from, age_to, city, sex)
                seen_ids = self.send_users(user_id, res)
            self.write_msg(user_id, 'До свидания!')
