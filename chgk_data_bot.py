import sqlite3
import telebot
from telebot import types

TOKEN = "8631577489:AAGnrn_p4W-Tes7ZiYLUb-PiVEsGnUcE-hs"
bot = telebot.TeleBot(TOKEN)

# Словарь для отслеживания состояний (редактирование, теги, источники)
user_states = {}

def init_db():
    conn = sqlite3.connect('facts.db')
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
    conn.commit()
    conn.close()

init_db()

# Создаем постоянные кнопки под чатом для удобного ввода команд
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton('/find'), types.KeyboardButton('/tag'))
    markup.row(types.KeyboardButton('/status'))
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "Привет! Я твой бот для базы фактов ЧГК.\n\n"
        "📌 **Как добавлять:** Просто отправь текст факта (он получит статусы по умолчанию).\n"
        "🔍 **Поиск:** Используй кнопки внизу экрана."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

def send_fact_message(chat_id, fact_id, content, readiness, usage_status, factcheck_status):
    text = (
        f"🆔 **ID:** {fact_id}\n"
        f"• Готовность: {readiness}\n"
        f"• Статус: {usage_status}\n"
        f"• Проверка: {factcheck_status}\n\n"
        f"{content}"
    )
    
    markup = types.InlineKeyboardMarkup()
    # Ряд 1: Готовность
    markup.add(
        types.InlineKeyboardButton("🟡 Доработка", callback_data=f"set_ready_work_{fact_id}"),
        types.InlineKeyboardButton("🟢 Готов", callback_data=f"set_ready_ready_{fact_id}")
    )
    # Ряд 2: Использование
    markup.add(
        types.InlineKeyboardButton("🟢 Свободен", callback_data=f"set_usage_free_{fact_id}"),
        types.InlineKeyboardButton("✅ Использовано", callback_data=f"set_usage_used_{fact_id}")
    )
    # Ряд 3: Фактчек
    markup.add(
        types.InlineKeyboardButton("🔍 Фактчек", callback_data=f"set_fc_check_{fact_id}"),
        types.InlineKeyboardButton("✅ Проверен", callback_data=f"set_fc_verified_{fact_id}")
    )
    # Ряд 4: Редактирование
    markup.add(
        types.InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_{fact_id}"),
        types.InlineKeyboardButton("➕ Хэштеги", callback_data=f"addtag_{fact_id}"),
        types.InlineKeyboardButton("➕ Источник", callback_data=f"addsrc_{fact_id}")
    )
    # Ряд 5: Удаление
    markup.add(
        types.InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{fact_id}")
    )
    
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['find'])
def find_facts(message):
    query = message.text.replace('/find', '').strip()
    if not query:
        bot.send_message(message.chat.id, "⚠️ Укажи слово для поиска, например: `/find физик`", parse_mode="Markdown")
        return

    conn = sqlite3.connect('facts.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, content, readiness, usage_status, factcheck_status FROM facts WHERE content LIKE ? ORDER BY id DESC", ('%' + query + '%',))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, f"🔍 По запросу **«{query}»** ничего не найдено.", parse_mode="Markdown")
        return

    bot.send_message(message.chat.id, f"🔍 Нашел совпадений: {len(rows)}")
    for row in rows:
        send_fact_message(message.chat.id, row[0], row[1], row[2], row[3], row[4])

@bot.message_handler(commands=['tag'])
def find_by_tag(message):
    query = message.text.replace('/tag', '').strip()
    if not query:
        bot.send_message(message.chat.id, "⚠️ Укажи хэштег для поиска, например: `/tag физика`", parse_mode="Markdown")
        return
    if not query.startswith('#'):
        query = '#' + query

    conn = sqlite3.connect('facts.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, content, readiness, usage_status, factcheck_status FROM facts WHERE content LIKE ? ORDER BY id DESC", ('%' + query + '%',))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, f"🏷 С тегом **«{query}»** ничего не найдено.", parse_mode="Markdown")
        return

    bot.send_message(message.chat.id, f"🏷 Факты с тегом {query} ({len(rows)}):")
    for row in rows:
        send_fact_message(message.chat.id, row[0], row[1], row[2], row[3], row[4])

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
        state = user_states[user_id]
        action = state['action']
        fact_id = state['fact_id']
        
        conn = sqlite3.connect('facts.db')
        cursor = conn.cursor()
        
        if action == 'edit':
            cursor.execute("UPDATE facts SET content = ? WHERE id = ?", (message.text, fact_id))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ Факт #{fact_id} полностью обновлен!", reply_markup=get_main_keyboard())
            
        elif action == 'addtag':
            # Обработка хэштегов через запятую
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
                new_content = row[0] + " " + tag_string
                cursor.execute("UPDATE facts SET content = ? WHERE id = ?", (new_content, fact_id))
                conn.commit()
                bot.send_message(message.chat.id, f"✅ Хэштеги добавлены к факту #{fact_id}!", reply_markup=get_main_keyboard())
                
        elif action == 'addsrc':
            source_text = f" [Источник: {message.text.strip()}]"
            cursor.execute("SELECT content FROM facts WHERE id = ?", (fact_id,))
            row = cursor.fetchone()
            if row:
                new_content = row[0] + source_text
                cursor.execute("UPDATE facts SET content = ? WHERE id = ?", (new_content, fact_id))
                conn.commit()
                bot.send_message(message.chat.id, f"✅ Источник добавлен к факту #{fact_id}!", reply_markup=get_main_keyboard())
                
        conn.close()
        del user_states[user_id]
        return

    # Сохранение нового факта (со статусами по умолчанию)
    content = message.text
    conn = sqlite3.connect('facts.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO facts (content) VALUES (?)', (content,))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "✅ Факт успешно сохранен со статусами по умолчанию!", reply_markup=get_main_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    conn = sqlite3.connect('facts.db')
    cursor = conn.cursor()
    
    if call.data.startswith("set_"):
        # Пример: set_ready_ready_5 или set_fc_verified_5
        parts = call.data.split("_")
        category = parts[1] # ready, usage, fc
        value_key = parts[2] # work/ready, free/used, check/verified
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
            conn.close()
            return
            
        cursor.execute(f"UPDATE facts SET {col} = ? WHERE id = ?", (new_val, fact_id))
        conn.commit()
        
        # Получаем актуальные статусы для обновления сообщения
        cursor.execute("SELECT content, readiness, usage_status, factcheck_status FROM facts WHERE id = ?", (fact_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            content, readiness, usage_status, factcheck_status = row
            updated_text = (
                f"🆔 **ID:** {fact_id}\n"
                f"• Готовность: {readiness}\n"
                f"• Статус: {usage_status}\n"
                f"• Проверка: {factcheck_status}\n\n"
                f"{content}"
            )
            try:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                                      text=updated_text, reply_markup=call.message.reply_markup, parse_mode="Markdown")
            except Exception:
                pass
        bot.answer_callback_query(call.id, "Статус обновлен")
        return

    elif call.data.startswith("filter_"):
        # filter_column_value
        parts = call.data.split("_", 2)
        col = parts[1]
        target_val = parts[2]
        
        cursor.execute(f"SELECT id, content, readiness, usage_status, factcheck_status FROM facts WHERE {col} = ? ORDER BY id DESC", (target_val,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            bot.answer_callback_query(call.id, "Нет фактов с таким статусом")
            bot.send_message(call.message.chat.id, f"📭 Фактов со статусом **{target_val}** не найдено.", parse_mode="Markdown")
            return

        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"📊 Факты со статусом **{target_val}** ({len(rows)}):")
        for row in rows:
            send_fact_message(call.message.chat.id, row[0], row[1], row[2], row[3], row[4])
        return

    elif call.data.startswith("edit_"):
        fact_id = call.data.split("_")[1]
        cursor.execute("SELECT content FROM facts WHERE id = ?", (fact_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            user_states[user_id] = {'action': 'edit', 'fact_id': fact_id}
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, 
                             f"✍️ Скопируй этот текст, исправь его и отправь мне ответным сообщением для факта #{fact_id}:\n\n{row[0]}")
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
        cursor.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "Факт удален")
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        
    conn.close()

print("Бот запущен...")
bot.infinity_polling()