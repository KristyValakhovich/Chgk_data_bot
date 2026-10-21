import sqlite3
import telebot
from telebot import types

TOKEN = "8631577489:AAGnrn_p4W-Tes7ZiYLUb-PiVEsGnUcE-hs"
bot = telebot.TeleBot(TOKEN)

# Словарь для отслеживания ввода (редактирование, теги, источники)
user_states = {}

def init_db():
    conn = sqlite3.connect('facts.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            status TEXT DEFAULT '🟡 На доработку'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Регистрация меню команд в Telegram
def set_commands():
    commands = [
        types.BotCommand("find", "Поиск по тексту или слову"),
        types.BotCommand("tag", "Поиск по хэштегу"),
        types.BotCommand("status", "Фильтр фактов по статусу"),
        types.BotCommand("start", "Справка и помощь")
    ]
    bot.set_my_commands(commands)

set_commands()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "Привет! Я твой бот для базы фактов ЧГК.\n\n"
        "📌 **Как добавлять:** Просто отправь текст факта (он получит статус 🟡 На доработку).\n"
        "🔍 **Поиск:** Используй меню слева (`/find`, `/tag`, `/status`)."
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

def send_fact_message(chat_id, fact_id, content, status):
    text = f"🆔 **ID:** {fact_id}\n📌 **Статус:** {status}\n\n{content}"
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🟡 Доработка", callback_data=f"status_work_{fact_id}"),
        types.InlineKeyboardButton("🔴 Фактчек", callback_data=f"status_check_{fact_id}"),
        types.InlineKeyboardButton("🟢 Готов", callback_data=f"status_ready_{fact_id}"),
        types.InlineKeyboardButton("✅ Использовано", callback_data=f"status_used_{fact_id}")
    )
    markup.add(
        types.InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_{fact_id}"),
        types.InlineKeyboardButton("➕ Хэштег", callback_data=f"addtag_{fact_id}"),
        types.InlineKeyboardButton("➕ Источник", callback_data=f"addsrc_{fact_id}")
    )
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
    cursor.execute("SELECT id, content, status FROM facts WHERE content LIKE ? ORDER BY id DESC", ('%' + query + '%',))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, f"🔍 По запросу **«{query}»** ничего не найдено.", parse_mode="Markdown")
        return

    bot.send_message(message.chat.id, f"🔍 Нашел совпадений: {len(rows)}", parse_mode="Markdown")
    for row in rows:
        send_fact_message(message.chat.id, row[0], row[1], row[2])

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
    cursor.execute("SELECT id, content, status FROM facts WHERE content LIKE ? ORDER BY id DESC", ('%' + query + '%',))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, f"🏷 С тегом **«{query}»** ничего не найдено.", parse_mode="Markdown")
        return

    bot.send_message(message.chat.id, f"🏷 Факты с тегом {query} ({len(rows)}):", parse_mode="Markdown")
    for row in rows:
        send_fact_message(message.chat.id, row[0], row[1], row[2])

@bot.message_handler(commands=['status'])
def choose_status_filter(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🟡 На доработку", callback_data="filter_🟡 На доработку"))
    markup.add(types.InlineKeyboardButton("🔴 Нужен фактчек", callback_data="filter_🔴 Нужен фактчек"))
    markup.add(types.InlineKeyboardButton("🟢 Готов", callback_data="filter_🟢 Готов"))
    markup.add(types.InlineKeyboardButton("✅ Использовано", callback_data="filter_✅ Использовано"))
    bot.send_message(message.chat.id, "📊 Выбери статус для просмотра фактов:", reply_markup=markup)

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
            bot.send_message(message.chat.id, f"✅ Факт #{fact_id} полностью обновлен!")
            
        elif action == 'addtag':
            tag = message.text if message.text.startswith('#') else '#' + message.text
            cursor.execute("SELECT content FROM facts WHERE id = ?", (fact_id,))
            row = cursor.fetchone()
            if row:
                new_content = row[0] + " " + tag
                cursor.execute("UPDATE facts SET content = ? WHERE id = ?", (new_content, fact_id))
                conn.commit()
                bot.send_message(message.chat.id, f"✅ Хэштег {tag} добавлен к факту #{fact_id}!")
                
        elif action == 'addsrc':
            source_text = f" [Источник: {message.text}]"
            cursor.execute("SELECT content FROM facts WHERE id = ?", (fact_id,))
            row = cursor.fetchone()
            if row:
                new_content = row[0] + source_text
                cursor.execute("UPDATE facts SET content = ? WHERE id = ?", (new_content, fact_id))
                conn.commit()
                bot.send_message(message.chat.id, f"✅ Источник добавлен к факту #{fact_id}!")
                
        conn.close()
        del user_states[user_id]
        return

    # Сохранение нового факта (по умолчанию: 🟡 На доработку)
    content = message.text
    conn = sqlite3.connect('facts.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO facts (content, status) VALUES (?, ?)', (content, '🟡 На доработку'))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "✅ Факт успешно сохранен со статусом **🟡 На доработку**!", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    conn = sqlite3.connect('facts.db')
    cursor = conn.cursor()
    
    if call.data.startswith("status_"):
        parts = call.data.split("_")
        action_type = parts[1]
        fact_id = parts[2]
        
        status_map = {
            'work': '🟡 На доработку',
            'check': '🔴 Нужен фактчек',
            'ready': '🟢 Готов',
            'used': '✅ Использовано'
        }
        new_status = status_map.get(action_type, '🟡 На доработку')
        
        cursor.execute("UPDATE facts SET status = ? WHERE id = ?", (new_status, fact_id))
        conn.commit()
        bot.answer_callback_query(call.id, f"Статус: {new_status}")
        
        try:
            lines = call.message.text.split('\n')
            if len(lines) > 1:
                lines[1] = f"📌 **Статус:** {new_status}"
            updated_text = '\n'.join(lines)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                                  text=updated_text, reply_markup=call.message.reply_markup, parse_mode="Markdown")
        except Exception:
            pass
            
    elif call.data.startswith("filter_"):
        target_status = call.data.replace("filter_", "")
        cursor.execute("SELECT id, content, status FROM facts WHERE status = ? ORDER BY id DESC", (target_status,))
        rows = cursor.fetchall()
        
        if not rows:
            bot.answer_callback_query(call.id, "Нет фактов с таким статусом")
            bot.send_message(call.message.chat.id, f"📭 Фактов со статусом **{target_status}** не найдено.", parse_mode="Markdown")
            conn.close()
            return

        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"📊 Факты со статусом **{target_status}** ({len(rows)}):", parse_mode="Markdown")
        for row in rows:
            send_fact_message(call.message.chat.id, row[0], row[1], row[2])

    elif call.data.startswith("edit_"):
        fact_id = call.data.split("_")[1]
        user_states[user_id] = {'action': 'edit', 'fact_id': fact_id}
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"✍️ Напиши новый текст для факта #{fact_id}:")
        
    elif call.data.startswith("addtag_"):
        fact_id = call.data.split("_")[1]
        user_states[user_id] = {'action': 'addtag', 'fact_id': fact_id}
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"🏷 Напиши хэштег для факта #{fact_id}:")
        
    elif call.data.startswith("addsrc_"):
        fact_id = call.data.split("_")[1]
        user_states[user_id] = {'action': 'addsrc', 'fact_id': fact_id}
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"🔗 Напиши источник для факта #{fact_id}:")
        
    elif call.data.startswith("delete_"):
        fact_id = call.data.split("_")[1]
        cursor.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "Факт удален")
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        
    conn.close()

print("Бот запущен...")
bot.infinity_polling()