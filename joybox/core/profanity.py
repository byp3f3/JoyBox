# Проверка текста на нецензурную лексику.
import re

# Минимальный список нецензурных слов.
PROFANITY_WORDS = frozenset([
    'бля', 'блять', 'блядь', 'хуй', 'хуя', 'пизда', 'хуйня', 'пизду', 'ебать', 'ебал', 'ёбаный',
    'сука', 'суки', 'мудак', 'мудила', 'дерьмо', 'гавно', 'жопа', 'залупа', 'хер',
    'нахер', 'похер', 'блядина', 'блядский', 'ебаный', 'ёб', 'выблядок', 'ублюдок',
])


def contains_profanity(text):
    if not text or not text.strip():
        return False
    normalized = re.sub(r'[^\w\s]', ' ', text.lower())
    words = set(re.findall(r'[а-яёa-z0-9]+', normalized))
    return bool(words & PROFANITY_WORDS)
