from telebot import types

def createTransportMenu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        types.KeyboardButton('Карта Метро'),
        types.KeyboardButton('Автобусы'),
        types.KeyboardButton('Трамваи'),
        types.KeyboardButton('Парковки'),
        types.KeyboardButton('Назад в главное меню'),

    ]
    keyboard.add(*buttons)
    return keyboard
def createGosMenu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        types.KeyboardButton('Регистрация'),
        types.KeyboardButton('Документы'),
        types.KeyboardButton('Медицина'),
        types.KeyboardButton('Семья'),
        types.KeyboardButton('Жилье'),
        types.KeyboardButton('Назад в главное  меню')
    ]
    keyboard.add(*buttons)
    return keyboard
def createSocialMenu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        types.KeyboardButton('Пенсионерам'),
        types.KeyboardButton('Детям'),
        types.KeyboardButton('Студентам'),
        types.KeyboardButton('Субсидии ЖКХ'),
        types.KeyboardButton('Пособия'),
        types.KeyboardButton('Назад в главное  меню')
    ]
    keyboard.add(*buttons)
    return keyboard
def createIventsMenu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        types.KeyboardButton('Театры'),
        types.KeyboardButton('Выставки'),
        types.KeyboardButton('Кинотеатры'),
        types.KeyboardButton('Фестивали'),
        types.KeyboardButton('Назад в главное  меню')
    ]
    keyboard.add(*buttons)
    return keyboard
def createEstablishmentвMenu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        types.KeyboardButton('Детские сады'),
        types.KeyboardButton('Школы'),
        types.KeyboardButton('Колледжи'),
        types.KeyboardButton('Вузы'),
        types.KeyboardButton('Назад в главное  меню')
    ]
    keyboard.add(*buttons)
    return keyboard
