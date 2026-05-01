import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes


TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Каталог", callback_data="catalog")]
    ]

    await update.message.reply_text(
        "Привет! Добро пожаловать 👋\n\nНажми кнопку ниже, чтобы открыть каталог.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "catalog":
        keyboard = [
            [InlineKeyboardButton("iPhone", callback_data="category_iphone")],
            [InlineKeyboardButton("Samsung", callback_data="category_samsung")],
            [InlineKeyboardButton("Xiaomi", callback_data="category_xiaomi")],
        ]

        await query.edit_message_text(
            text="Каталог товаров:\n\nВыбери категорию:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "category_iphone":
        keyboard = [
            [InlineKeyboardButton("iPhone 15 Pro", callback_data="iphone_15_pro")],
            [InlineKeyboardButton("iPhone 15", callback_data="iphone_15")],
            [InlineKeyboardButton("iPhone 14 Pro", callback_data="iphone_14_pro")],
            [InlineKeyboardButton("⬅️ Назад в каталог", callback_data="catalog")],
        ]

        await query.edit_message_text(
            text="Каталог iPhone:\n\nВыбери модель:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "category_samsung":
        keyboard = [
            [InlineKeyboardButton("Samsung S24 Ultra", callback_data="samsung_s24_ultra")],
            [InlineKeyboardButton("Samsung S23", callback_data="samsung_s23")],
            [InlineKeyboardButton("⬅️ Назад в каталог", callback_data="catalog")],
        ]

        await query.edit_message_text(
            text="Каталог Samsung:\n\nВыбери модель:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "category_xiaomi":
        keyboard = [
            [InlineKeyboardButton("Xiaomi 14", callback_data="xiaomi_14")],
            [InlineKeyboardButton("Redmi Note 13", callback_data="redmi_note_13")],
            [InlineKeyboardButton("⬅️ Назад в каталог", callback_data="catalog")],
        ]

        await query.edit_message_text(
            text="Каталог Xiaomi:\n\nВыбери модель:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "iphone_15_pro":
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к iPhone", callback_data="category_iphone")],
        ]

        await query.edit_message_text(
            text=(
                "iPhone 15 Pro\n\n"
                "Память: 128GB / 256GB / 512GB\n"
                "Цвета: Black / White / Blue / Natural\n"
                "Цена: от 999$\n\n"
                "Для заказа напиши менеджеру."
            ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "iphone_15":
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к iPhone", callback_data="category_iphone")],
        ]

        await query.edit_message_text(
            text=(
                "iPhone 15\n\n"
                "Память: 128GB / 256GB\n"
                "Цвета: Black / Blue / Pink / Green\n"
                "Цена: от 799$\n\n"
                "Для заказа напиши менеджеру."
            ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "iphone_14_pro":
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к iPhone", callback_data="category_iphone")],
        ]

        await query.edit_message_text(
            text=(
                "iPhone 14 Pro\n\n"
                "Память: 128GB / 256GB / 512GB\n"
                "Цвета: Space Black / Silver / Gold / Deep Purple\n"
                "Цена: уточняйте у менеджера."
            ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "samsung_s24_ultra":
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к Samsung", callback_data="category_samsung")],
        ]

        await query.edit_message_text(
            text=(
                "Samsung S24 Ultra\n\n"
                "Память: 256GB / 512GB\n"
                "Цена: уточняйте у менеджера."
            ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "samsung_s23":
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к Samsung", callback_data="category_samsung")],
        ]

        await query.edit_message_text(
            text=(
                "Samsung S23\n\n"
                "Память: 128GB / 256GB\n"
                "Цена: уточняйте у менеджера."
            ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "xiaomi_14":
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к Xiaomi", callback_data="category_xiaomi")],
        ]

        await query.edit_message_text(
            text=(
                "Xiaomi 14\n\n"
                "Память: 256GB / 512GB\n"
                "Цена: уточняйте у менеджера."
            ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "redmi_note_13":
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к Xiaomi", callback_data="category_xiaomi")],
        ]

        await query.edit_message_text(
            text=(
                "Redmi Note 13\n\n"
                "Память: 128GB / 256GB\n"
                "Цена: уточняйте у менеджера."
            ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN не найден. Добавь переменную BOT_TOKEN в Railway.")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
