import sqlite3
import string
import telebot
from telebot import types

TOKEN = "8631577489:AAGnrn_p4W-Tes7ZiYLUb-PiVEsGnUcE-hs"
bot = telebot.TeleBot(TOKEN)

# Словарь для отслеживания состояний
user_states = {}

def get_db_connection():
    conn = sqlite3.connect('facts.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                readiness TEXT DEFAULT '🟡 Доработка',
                usage_status TEXT DEFAULT '🟢 Свободен',
                factcheck_status TEXT DEFAULT '🔍 Фактчек'
            )
        ''')
        
        # Автоматическая миграция
        cursor.execute("PRAGMA table_info(facts)")
        columns = [column['name'] for column in cursor.fetchall()]
        
        if 'readiness' not in columns:
            cursor.execute("ALTER TABLE facts ADD COLUMN readiness TEXT DEFAULT '🟡 Доработка'")
        if 'usage_status' not in columns:
            cursor.execute("ALTER TABLE facts ADD COLUMN usage_status TEXT DEFAULT '🟢 Свободен'")
        if 'factcheck_status' not in columns:
            cursor.execute("ALTER TABLE facts ADD COLUMN factcheck_status TEXT DEFAULT '🔍 Фактчек'")
        conn.commit()

init_db()

# Регистрация меню команд в Telegram
def set_commands():
    commands = [
        types.BotCommand("find", "Поиск по тексту или слову"),
        types.BotCommand("tag", "Поиск по хэштегу"),
        types.BotCommand("random", "Случайный факт из базы"),
        types.BotCommand("status", "Фильтр фактов по статусам"),
        types.BotCommand("start", "Справка и помощь")
    ]
    bot.set_my_commands(commands)

set_commands()

# Умная функция выделения корня русского слова для поиска
def get_stem(word):
    word = word.lower()
    suffixes = [
        'ого', 'его', 'ому', 'ему', 'ыми', 'ими', 'ых', 'их', 'ами', 'ями', 'ах', 'ях',
        'ое', 'ее', 'ый', 'ий', 'ой', 'ая', 'яя', 'ою', 'ею',
        'ом', 'ем', 'ой', 'ей', 'ам', 'ям', 'у', 'ю', 'а', 'я', 'ы', 'и', 'о', 'е'
    ]
    if len(word) > 4:
        for s in suffixes:
            if word.endswith(s) and len(word) - len(s) >= 3:
                return word[:-len(s)]
    return word

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "Привет! Я твой бот для базы фактов ЧГК.\n\n"
        "📌 Как добавлять: Просто отправь текст факта.\n"
        "🔍 Команды:\n"
        "• /find слово — Поиск по тексту (автоматически по корню)\n"
        "• /tag тег — Поиск по хэштегу\n"
        "• /random — Случайный факт\n"
        "• /status — Фильтр по статусам"
    )
    bot.send_message(message.chat.id, welcome_text)

def send_fact_message(chat_id, fact_id, content, readiness, usage_status, factcheck_status):
    readiness = readiness or '🟡 Доработка'
    usage_status = usage_status or '🟢 Свободен'
    factcheck_status = factcheck_status or '🔍 Фактчек'

    text = (
        f"ID: {fact_id}\n"
        f"• Готовность: {readiness}\n"
        f"• Использование: {usage_status}\n"
        f"• Проверка: {factcheck_status}\n\n"
        f"{content}"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🟡 Доработка", callback_data=f"set_ready_work_{fact_id}"),
        types.InlineKeyboardButton("🟢 Готов", callback_data=f"set_ready_ready_{fact_id}")
    )
    markup.add(
        types.InlineKeyboardButton("🟢 Свободен", callback_data=f"set_usage_free_{fact_id}"),
        types.InlineKeyboardButton("✅ Использовано", callback_data=f"set_usage_used_{fact_id}")
    )
    markup.add(
        types.InlineKeyboardButton("🔍 Фактчек", callback_data=f"set_fc_check_{fact_id}"),
        types.InlineKeyboardButton("✅ Проверен", callback_data=f"set_fc_verified_{fact_id}")
    )
    markup.add(
        types.InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_{fact_id}"),
        types.InlineKeyboardButton("➕ Хэштеги", callback_data=f"addtag_{fact_id}"),
        types.InlineKeyboardButton("➕ Источник", callback_data=f"addsrc_{fact_id}")
    )
    markup.add(
        types.InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{fact_id}")
    )
    
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.message_handler(commands=['find'])
def find_facts(message):
    query_raw = message.text.replace('/find', '').strip()
    if not query_raw:
        bot.send_message(message.chat.id, "⚠️ Укажи слово для поиска, например: /find физик")
        return

    # Очищаем от знаков препинания и разбиваем на слова
    cleaned_query = query_raw.translate(str.maketrans('', '', string.punctuation))
    words = [w.strip() for w in cleaned_query.split() if w.strip()]
    
    if not words:
        bot.send_message(message.chat.id, "⚠️ Укажи корректное слово для поиска.")
        return

    stems = [get_stem(w) for w in words]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        sql = "SELECT id, content, readiness, usage_status, factcheck_status FROM facts WHERE "
        conditions = []
        params = []
        for stem in stems:
            conditions.append("LOWER(content) LIKE ?")
            params.append(f'%{stem}%')
        
        sql += " AND ".join(conditions) + " ORDER BY id DESC"
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()

    if not rows:
        bot.send_message(message.chat.id, f"🔍 По запросу «{query_raw}» ничего не найдено.")
        return

    bot.send_message(message.chat.id, f"🔍 Нашел совпадений: {len(rows)}")
    for row in rows:
        send_fact_message(message.chat.id, row['id'], row['content'], row['readiness'], row['usage_status'], row['factcheck_status'])

@bot.message_handler(commands=['tag'])
def find_by_tag(message):
    query = message.text.replace('/tag', '').strip()
    if not query:
        bot.send_message(message.chat.id, "⚠️ Укажи хэштег для поиска, например: /tag физика")
        return
    if not query.startswith('#'):
        query = '#' + query

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, content, readiness, usage_status, factcheck_status FROM facts WHERE LOWER(content) LIKE ? ORDER BY id DESC", ('%' + query.lower() + '%',))
        rows = cursor.fetchall()

    if not rows:
        bot.send_message(message.chat.id, f"🏷 С тегом «{query}» ничего не найдено.")
        return

    bot.send_message(message.chat.id, f"🏷 Факты с тегом {query} ({len(rows)}):")
    for row in rows:
        send_fact_message(message.chat.id, row['id'], row['content'], row['readiness'], row['usage_status'], row['factcheck_status'])

@bot.message_handler(commands=['random'])
def random_fact(message):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, content, readiness, usage_status, factcheck_status FROM facts ORDER BY RANDOM() LIMIT 1")
        row = cursor.fetchone()

    if not row:
        bot.send_message(message.chat.id, "📭 База данных пока пуста.")
        return

    bot.send_message(message.chat.id, "🎲 Случайный факт из базы:")
    send_fact_message(message.chat.id, row['id'], row['content'], row['readiness'], row['usage_status'], row['factcheck_status'])

@bot.message_handler(commands=['status'])
def choose_status_filter(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🟡 Доработка", callback_data="filter_readiness_🟡 Доработка"))
    markup.add(types.InlineKeyboardButton("🟢 Готов", callback_data="filter_readiness_🟢 Готов"))
    markup.add(types.InlineKeyboardButton("🟢 Свободен", callback_data="filter_usage_status_🟢 Свободен"))
    markup.add(types.InlineKeyboardButton("✅ Использовано", callback_data="filter_usage_status_✅ Использовано"))
    markup.add(types.InlineKeyboardButton("🔍 Фактчек", callback_data="filter_factcheck_status_🔍 Фактчек"))
    markup.add(types.InlineKeyboardButton("✅ Проверен", callback_data="filter_factcheck_status_✅ Проверен"))
    bot.send_message(message.chat.id, "📊 Выбери статус для фильтрации:", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.from_user.id
    
    if user_id in user_states:
        # Если пользователь передумал и отправил команду во время ввода — сбрасываем состояние
        if message.text.startswith('/'):
            del user_states[user_id]
            return

        state = user_states[user_id]
        action = state['action']
        fact_id = state['fact_id']
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if action == 'edit':
                cursor.execute("UPDATE facts SET content = ? WHERE id = ?", (message.text, fact_id))
                conn.commit()
                bot.send_message(message.chat.id, f"✅ Факт #{fact_id} полностью обновлен!")
                
            elif action == 'addtag':
                raw_tags = message.text.split(',')
                formatted_tags = []
                for t in raw_tags:
                    t = t.strip()
                    if t:
                        if not t.startswith('#'):
                            t = '#' + t
                        formatted_tags.append(t)
                
                tag_string = " ".join(formatted_tags)
                cursor.execute("SELECT content FROM facts WHERE id = ?", (fact_id,))
                row = cursor.fetchone()
                if row and tag_string:
                    new_content = row['content'] + " " + tag_string
                    cursor.execute("UPDATE facts SET content = ? WHERE id = ?", (new_content, fact_id))
                    conn.commit()
                    bot.send_message(message.chat.id, f"✅ Хэштеги добавлены к факту #{fact_id}!")
                    
            elif action == 'addsrc':
                source_text = f" [Источник: {message.text.strip()}]"
                cursor.execute("SELECT content FROM facts WHERE id = ?", (fact_id,))
                row = cursor.fetchone()
                if row:
                    new_content = row['content'] + source_text
                    cursor.execute("UPDATE facts SET content = ? WHERE id = ?", (new_content, fact_id))
                    conn.commit()
                    bot.send_message(message.chat.id, f"✅ Источник добавлен к факту #{fact_id}!")
                    
        del user_states[user_id]
        return

    # Сохранение нового факта
    content = message.text
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO facts (content) VALUES (?)', (content,))
        conn.commit()
    bot.send_message(message.chat.id, "✅ Факт успешно сохранен со статусами по умолчанию!")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    
    if call.data.startswith("set_"):
        parts = call.data.split("_")
        category = parts[1]
        value_key = parts[2]
        fact_id = parts[3]
        
        if category == 'ready':
            col = 'readiness'
            new_val = '🟡 Доработка' if value_key == 'work' else '🟢 Готов'
        elif category == 'usage':
            col = 'usage_status'
            new_val = '🟢 Свободен' if value_key == 'free' else '✅ Использовано'
        elif category == 'fc':
            col = 'factcheck_status'
            new_val = '🔍 Фактчек' if value_key == 'check' else '✅ Проверен'
        else:
            return
            
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE facts SET {col} = ? WHERE id = ?", (new_val, fact_id))
            conn.commit()
            
            cursor.execute("SELECT content, readiness, usage_status, factcheck_status FROM facts WHERE id = ?", (fact_id,))
            row = cursor.fetchone()
        
        if row:
            content = row['content']
            readiness = row['readiness'] or '🟡 Доработка'
            usage_status = row['usage_status'] or '🟢 Свободен'
            factcheck_status = row['factcheck_status'] or '🔍 Фактчек'

            updated_text = (
                f"ID: {fact_id}\n"
                f"• Готовность: {readiness}\n"
                f"• Использование: {usage_status}\n"
                f"• Проверка: {factcheck_status}\n\n"
                f"{content}"
            )
            try:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                                      text=updated_text, reply_markup=call.message.reply_markup)
            except Exception:
                pass
        bot.answer_callback_query(call.id, "Статус обновлен")
        return

    elif call.data.startswith("filter_"):
        parts = call.data.split("_", 2)
        col = parts[1]
        target_val = parts[2]
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT id, content, readiness, usage_status, factcheck_status FROM facts WHERE {col} = ? ORDER BY id DESC", (target_val,))
            rows = cursor.fetchall()
        
        if not rows:
            bot.answer_callback_query(call.id, "Нет фактов с таким статусом")
            bot.send_message(call.message.chat.id, f"📭 Фактов со статусом {target_val} не найдено.")
            return

        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"📊 Факты со статусом {target_val} ({len(rows)}):")
        for row in rows:
            send_fact_message(call.message.chat.id, row['id'], row['content'], row['readiness'], row['usage_status'], row['factcheck_status'])
        return

    elif call.data.startswith("edit_"):
        fact_id = call.data.split("_")[1]
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM facts WHERE id = ?", (fact_id,))
            row = cursor.fetchone()
        
        if row:
            user_states[user_id] = {'action': 'edit', 'fact_id': fact_id}
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, f"✍️ Скопируй текст ниже, исправь его и отправь мне ответным сообщением для факта #{fact_id}:")
            bot.send_message(call.message.chat.id, row['content'])
        return
        
    elif call.data.startswith("addtag_"):
        fact_id = call.data.split("_")[1]
        user_states[user_id] = {'action': 'addtag', 'fact_id': fact_id}
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"🏷 Напиши хэштеги через запятую (например: `#физика, #наука`) для факта #{fact_id}:")
        return
        
    elif call.data.startswith("addsrc_"):
        fact_id = call.data.split("_")[1]
        user_states[user_id] = {'action': 'addsrc', 'fact_id': fact_id}
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"🔗 Напиши источник для факта #{fact_id}:")
        return
        
    elif call.data.startswith("delete_"):
        fact_id = call.data.split("_")[1]
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
            conn.commit()
        bot.answer_callback_query(call.id, "Факт удален")
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)

print("Бот запущен...")
bot.infinity_polling()