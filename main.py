from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)
import sqlite3

# === 🔐 Пароль доступа ===
ACCESS_PASSWORD = "638986363"  # ← поменяй на свой

# === Состояния ===
AWAITING_PASSWORD, CHOOSING, ADD_NAME, ADD_PHONE, ORDER_PHONE, DELETE_PHONE = range(6)

# === Клавиатуры ===
main_keyboard = ReplyKeyboardMarkup(
    [["🧍‍♂️ Добавить клиента", "🧋 Выдать напиток"],
     ["📋 Список клиентов", "🗑️ Удалить клиента"]],
    resize_keyboard=True
)
back_keyboard = ReplyKeyboardMarkup(
    [["⬅️ Назад"]],
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

# === Авторизация по паролю ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data

    if user_data.get("is_authenticated"):
        await update.message.reply_text("✅ Ты уже вошёл. Добро пожаловать снова!", reply_markup=main_keyboard)
        return CHOOSING

    await update.message.reply_text("🔐 Введи пароль для доступа:")
    return AWAITING_PASSWORD

async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == ACCESS_PASSWORD:
        context.user_data["is_authenticated"] = True
        await update.message.reply_text("✅ Доступ разрешён! Добро пожаловать!", reply_markup=main_keyboard)
        return CHOOSING
    else:
        await update.message.reply_text("❌ Неверный пароль. Попробуй ещё раз:")
        return AWAITING_PASSWORD

# === Обработчики ===

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("is_authenticated"):
        await update.message.reply_text("❌ Сначала введи пароль. Напиши /start")
        return CHOOSING

    text = update.message.text

    if text == "🧍‍♂️ Добавить клиента":
        await update.message.reply_text("Введи имя клиента:", reply_markup=back_keyboard)
        return ADD_NAME

    elif text == "🧋 Выдать напиток":
        await update.message.reply_text("Введи номер клиента:", reply_markup=back_keyboard)
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

    elif text == "🗑️ Удалить клиента":
        await update.message.reply_text("Введи номер клиента, которого нужно удалить:", reply_markup=back_keyboard)
        return DELETE_PHONE

    else:
        await update.message.reply_text("Выбери кнопку ⬇️", reply_markup=main_keyboard)
        return CHOOSING

async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "⬅️ Назад":
        await update.message.reply_text("↩️ Возвращаюсь в меню.", reply_markup=main_keyboard)
        return CHOOSING

    context.user_data["name"] = update.message.text
    await update.message.reply_text("Теперь введи номер телефона:", reply_markup=back_keyboard)
    return ADD_PHONE

async def add_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "⬅️ Назад":
        await update.message.reply_text("↩️ Возвращаюсь в меню.", reply_markup=main_keyboard)
        return CHOOSING

    name = context.user_data["name"]
    phone = update.message.text

    cursor.execute("INSERT OR IGNORE INTO clients (phone, name, drinks) VALUES (?, ?, 0)", (phone, name))
    conn.commit()
    await update.message.reply_text(f"✅ Клиент {name} с номером {phone} добавлен.", reply_markup=main_keyboard)
    return CHOOSING

async def order_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "⬅️ Назад":
        await update.message.reply_text("↩️ Возвращаюсь в меню.", reply_markup=main_keyboard)
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

async def delete_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "⬅️ Назад":
        await update.message.reply_text("↩️ Возвращаюсь в меню.", reply_markup=main_keyboard)
        return CHOOSING

    phone = update.message.text
    cursor.execute("SELECT name FROM clients WHERE phone = ?", (phone,))
    result = cursor.fetchone()

    if result:
        name = result[0]
        cursor.execute("DELETE FROM clients WHERE phone = ?", (phone,))
        conn.commit()
        await update.message.reply_text(f"🗑️ Клиент {name} ({phone}) удалён.", reply_markup=main_keyboard)
    else:
        await update.message.reply_text("❌ Клиент не найден.", reply_markup=main_keyboard)

    return CHOOSING

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено. Возвращаюсь в главное меню.", reply_markup=main_keyboard)
    return CHOOSING

# === Запуск ===

app = ApplicationBuilder().token("7898159101:AAGhICr4HQ-lZbhfq78eJcWYsXwU7Lzd80w").build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        AWAITING_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_password)],
        CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_choice)],
        ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
        ADD_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_phone)],
        ORDER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_phone)],
        DELETE_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_phone)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app.add_handler(conv_handler)

print("🚀 Бот запущен! Ждёт клиентов...")
app.run_polling()
