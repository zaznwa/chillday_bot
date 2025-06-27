from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)
import sqlite3

# === 🔐 Список разрешённых Telegram ID ===
ALLOWED_USERS = [638986363]  # ← сюда добавляй ID других, если нужно

# === Состояния ===
CHOOSING, ADD_NAME, ADD_PHONE, ORDER_PHONE = range(4)

# === Клавиатура ===
main_keyboard = ReplyKeyboardMarkup(
    [["🧍‍♂️ Добавить клиента", "🧋 Выдать напиток"], ["📋 Список клиентов"]],
    resize_keyboard=True
)

# === База данных ===
conn = sqlite3.connect("clients.db")
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        phone TEXT PRIMARY KEY,
        name TEXT,
        drinks INTEGER DEFAULT 0
    )
''')
conn.commit()

# === Проверка доступа ===
def is_allowed(update: Update) -> bool:
    return update.effective_user.id in ALLOWED_USERS

# === Обработчики ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    await update.message.reply_text(
        f"Привет, {username or 'гость'}!\n"
        f"Твой Telegram ID: {user_id}",
        reply_markup=main_keyboard
    )
    return CHOOSING

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await update.message.reply_text("❌ У тебя нет доступа к этой функции.")
        return CHOOSING

    text = update.message.text

    if text == "🧍‍♂️ Добавить клиента":
        await update.message.reply_text("Введи имя клиента:")
        return ADD_NAME

    elif text == "🧋 Выдать напиток":
        await update.message.reply_text("Введи номер клиента:")
        return ORDER_PHONE

    elif text == "📋 Список клиентов":
        cursor.execute("SELECT name, phone, drinks FROM clients")
        clients = cursor.fetchall()
        if not clients:
            await update.message.reply_text("🙅‍♂️ Пока клиентов нет.")
        else:
            msg = "📋 Список клиентов:\n\n"
            for name, phone, drinks in clients:
                msg += f"{name} ({phone}) — {drinks}/5 напитков\n"
            await update.message.reply_text(msg)
        return CHOOSING

    else:
        await update.message.reply_text("Выбери кнопку ⬇️", reply_markup=main_keyboard)
        return CHOOSING

async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Теперь введи номер телефона:")
    return ADD_PHONE

async def add_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await update.message.reply_text("❌ Нет доступа.")
        return CHOOSING

    name = context.user_data["name"]
    phone = update.message.text

    cursor.execute("INSERT OR IGNORE INTO clients (phone, name, drinks) VALUES (?, ?, 0)", (phone, name))
    conn.commit()
    await update.message.reply_text(f"✅ Клиент {name} с номером {phone} добавлен.", reply_markup=main_keyboard)
    return CHOOSING

async def order_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await update.message.reply_text("❌ Нет доступа.")
        return CHOOSING

    phone = update.message.text
    cursor.execute("SELECT name, drinks FROM clients WHERE phone = ?", (phone,))
    result = cursor.fetchone()

    if result:
        name, drinks = result
        drinks += 1
        if drinks >= 5:
            cursor.execute("UPDATE clients SET drinks = 0 WHERE phone = ?", (phone,))
            msg = f"🎉 {name} получил 5-й напиток бесплатно! Счётчик сброшен."
        else:
            cursor.execute("UPDATE clients SET drinks = ? WHERE phone = ?", (drinks, phone))
            msg = f"🥤 У {name} теперь {drinks}/5 напитков."
        conn.commit()
        await update.message.reply_text(msg, reply_markup=main_keyboard)
    else:
        await update.message.reply_text("❌ Клиент не найден.", reply_markup=main_keyboard)

    return CHOOSING

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено. Возвращаюсь в главное меню.", reply_markup=main_keyboard)
    return CHOOSING

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await update.message.reply_text("❌ Нет доступа.")
        return

    cursor.execute("DELETE FROM clients")
    conn.commit()
    await update.message.reply_text("🗑️ Все клиенты удалены! Список очищен.")

# === Запуск ===

app = ApplicationBuilder().token("7898159101:AAGhICr4HQ-lZbhfq78eJcWYsXwU7Lzd80w").build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_choice)],
        ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
        ADD_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_phone)],
        ORDER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_phone)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app.add_handler(conv_handler)
app.add_handler(CommandHandler("reset", reset))

print("🚀 Бот запущен! Ждёт клиентов...")
app.run_polling()
