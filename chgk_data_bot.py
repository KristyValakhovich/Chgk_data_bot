import sqlite3
import telebot
from telebot import types

# Сюда вставь свой токен от BotFather между кавычками
TOKEN = "8631577489:AAGnrn_p4W-Tes7ZiYLUb-PiVEsGnUcE-hs"
bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect('facts.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            status TEXT DEFAULT '🟢 Свободен'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "Привет! Я твой бот для базы фактов ЧГК.\n\n"
        "📌 **Как добавлять:** Просто напиши текст факта.\n"
        "🔍 **Как искать:** Отправь `/find ключевое слово` (например, `/find Исландия`).\n"
        "📋 **Список последних:** Отправь `/list`."
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['list'])
def list_facts(message):
    conn = sqlite3.connect('facts.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, content, status FROM facts ORDER BY id DESC LIMIT 10')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "📭 База данных пока пуста.")
        return

    for row in rows:
        fact_id, content, status = row
        text = f"🆔 **ID:** {fact_id}\n📌 **Статус:** {status}\n\n{content}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Использовано", callback_data=f"status_used_{fact_id}"),
            types.InlineKeyboardButton("🔴 Нужен фактчек", callback_data=f"status_check_{fact_id}")
        )
        markup.add(
            types.InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{fact_id}")
        )
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['find'])
def find_facts(message):
    query = message.text.replace('/find', '').strip()
    if not query:
        bot.send_message(message.chat.id, "⚠️ Укажи слово для поиска, например: `/find Эйнштейн`", parse_mode="Markdown")
        return

    conn = sqlite3.connect('facts.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, content, status FROM facts WHERE content LIKE ?", ('%' + query + '%',))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, f"🔍 По запросу **«{query}»** ничего не найдено.", parse_mode="Markdown")
        return

    bot.send_message(message.chat.id, f"🔍 Нашел совпадения ({len(rows)}):", parse_mode="Markdown")
    for row in rows:
        fact_id, content, status = row
        text = f"🆔 **ID:** {fact_id}\n📌 **Статус:** {status}\n\n{content}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Использовано", callback_data=f"status_used_{fact_id}"),
            types.InlineKeyboardButton("🔴 Нужен фактчек", callback_data=f"status_check_{fact_id}")
        )
        markup.add(
            types.InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{fact_id}")
        )
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def save_fact(message):
    content = message.text
    conn = sqlite3.connect('facts.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO facts (content) VALUES (?)', (content,))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "✅ Факт успешно сохранен в базу!")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    conn = sqlite3.connect('facts.db')
    cursor = conn.cursor()
    
    if call.data.startswith("status_used_"):
        fact_id = call.data.split("_")[2]
        cursor.execute("UPDATE facts SET status = '🟢 Использовано' WHERE id = ?", (fact_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "Статус изменен на 'Использовано'")
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text=call.message.text.replace("🟢 Свободен", "🟢 Использовано").replace("🔴 Нужен фактчек", "🟢 Использовано"),
                              reply_markup=call.message.reply_markup)
                              
    elif call.data.startswith("status_check_"):
        fact_id = call.data.split("_")[2]
        cursor.execute("UPDATE facts SET status = '🔴 Нужен фактчек' WHERE id = ?", (fact_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "Статус изменен на 'Нужен фактчек'")
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text=call.message.text.replace("🟢 Свободен", "🔴 Нужен фактчек").replace("🟢 Использовано", "🔴 Нужен фактчек"),
                              reply_markup=call.message.reply_markup)
                              
    elif call.data.startswith("delete_"):
        fact_id = call.data.split("_")[1]
        cursor.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "Факт удален")
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        
    conn.close()

print("Бот запущен...")
bot.infinity_polling()