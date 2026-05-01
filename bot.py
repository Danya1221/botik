import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes


def get_token():
    token = os.environ.get("8764879626:AAFblZOgO1GWINprG1Zp1kj5AvyiboejkuQ")
    if token:
        token = token.strip()
    return token


def get_admin_id():
    admin_id = os.environ.get("707131428")
    if admin_id:
        admin_id = admin_id.strip()

    if not admin_id:
        return None

    try:
        return int(admin_id)
    except ValueError:
        return None


PRODUCTS = {
    "iphone_15_pro": {
        "name": "iPhone 15 Pro",
        "text": (
            "iPhone 15 Pro\n\n"
            "Память: 128GB / 256GB / 512GB\n"
            "Цвета: Black / White / Blue / Natural\n"
            "Цена: от 999$\n\n"
            "Нажми кнопку ниже, чтобы добавить товар в корзину."
        ),
        "back": "category_iphone",
    },
    "iphone_15": {
        "name": "iPhone 15",
        "text": (
            "iPhone 15\n\n"
            "Память: 128GB / 256GB\n"
            "Цвета: Black / Blue / Pink / Green\n"
            "Цена: от 799$\n\n"
            "Нажми кнопку ниже, чтобы добавить товар в корзину."
        ),
        "back": "category_iphone",
    },
    "iphone_14_pro": {
        "name": "iPhone 14 Pro",
        "text": (
            "iPhone 14 Pro\n\n"
            "Память: 128GB / 256GB / 512GB\n"
            "Цвета: Space Black / Silver / Gold / Deep Purple\n"
            "Цена: уточняйте у менеджера.\n\n"
            "Нажми кнопку ниже, чтобы добавить товар в корзину."
        ),
        "back": "category_iphone",
    },
    "samsung_s24_ultra": {
        "name": "Samsung S24 Ultra",
        "text": (
            "Samsung S24 Ultra\n\n"
            "Память: 256GB / 512GB\n"
            "Цена: уточняйте у менеджера.\n\n"
            "Нажми кнопку ниже, чтобы добавить товар в корзину."
        ),
        "back": "category_samsung",
    },
    "samsung_s23": {
        "name": "Samsung S23",
        "text": (
            "Samsung S23\n\n"
            "Память: 128GB / 256GB\n"
            "Цена: уточняйте у менеджера.\n\n"
            "Нажми кнопку ниже, чтобы добавить товар в корзину."
        ),
        "back": "category_samsung",
    },
    "xiaomi_14": {
        "name": "Xiaomi 14",
        "text": (
            "Xiaomi 14\n\n"
            "Память: 256GB / 512GB\n"
            "Цена: уточняйте у менеджера.\n\n"
            "Нажми кнопку ниже, чтобы добавить товар в корзину."
        ),
        "back": "category_xiaomi",
    },
    "redmi_note_13": {
        "name": "Redmi Note 13",
        "text": (
            "Redmi Note 13\n\n"
            "Память: 128GB / 256GB\n"
            "Цена: уточняйте у менеджера.\n\n"
            "Нажми кнопку ниже, чтобы добавить товар в корзину."
        ),
        "back": "category_xiaomi",
    },
}


def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Каталог", callback_data="catalog")],
        [InlineKeyboardButton("🛒 Корзина", callback_data="cart")],
    ])


def catalog_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("iPhone", callback_data="category_iphone")],
        [InlineKeyboardButton("Samsung", callback_data="category_samsung")],
        [InlineKeyboardButton("Xiaomi", callback_data="category_xiaomi")],
        [InlineKeyboardButton("🛒 Корзина", callback_data="cart")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Добро пожаловать 👋\n\nНажми кнопку ниже, чтобы открыть каталог.",
        reply_markup=main_menu_keyboard()
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cart = context.user_data.setdefault("cart", [])
    data = query.data

    if data == "catalog":
        await query.edit_message_text(
            text="Каталог товаров:\n\nВыбери категорию:",
            reply_markup=catalog_keyboard()
        )

    elif data == "category_iphone":
        keyboard = [
            [InlineKeyboardButton("iPhone 15 Pro", callback_data="product_iphone_15_pro")],
            [InlineKeyboardButton("iPhone 15", callback_data="product_iphone_15")],
            [InlineKeyboardButton("iPhone 14 Pro", callback_data="product_iphone_14_pro")],
            [InlineKeyboardButton("⬅️ Назад в каталог", callback_data="catalog")],
            [InlineKeyboardButton("🛒 Корзина", callback_data="cart")],
        ]

        await query.edit_message_text(
            text="Каталог iPhone:\n\nВыбери модель:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "category_samsung":
        keyboard = [
            [InlineKeyboardButton("Samsung S24 Ultra", callback_data="product_samsung_s24_ultra")],
            [InlineKeyboardButton("Samsung S23", callback_data="product_samsung_s23")],
            [InlineKeyboardButton("⬅️ Назад в каталог", callback_data="catalog")],
            [InlineKeyboardButton("🛒 Корзина", callback_data="cart")],
        ]

        await query.edit_message_text(
            text="Каталог Samsung:\n\nВыбери модель:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "category_xiaomi":
        keyboard = [
            [InlineKeyboardButton("Xiaomi 14", callback_data="product_xiaomi_14")],
            [InlineKeyboardButton("Redmi Note 13", callback_data="product_redmi_note_13")],
            [InlineKeyboardButton("⬅️ Назад в каталог", callback_data="catalog")],
            [InlineKeyboardButton("🛒 Корзина", callback_data="cart")],
        ]

        await query.edit_message_text(
            text="Каталог Xiaomi:\n\nВыбери модель:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("product_"):
        product_id = data.replace("product_", "")
        product = PRODUCTS.get(product_id)

        if not product:
            await query.edit_message_text(
                text="Товар не найден.",
                reply_markup=catalog_keyboard()
            )
            return

        keyboard = [
            [InlineKeyboardButton("➕ Добавить в корзину", callback_data=f"add_{product_id}")],
            [InlineKeyboardButton("⬅️ Назад", callback_data=product["back"])],
            [InlineKeyboardButton("🛒 Корзина", callback_data="cart")],
        ]

        await query.edit_message_text(
            text=product["text"],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("add_"):
        product_id = data.replace("add_", "")
        product = PRODUCTS.get(product_id)

        if not product:
            await query.edit_message_text(
                text="Товар не найден.",
                reply_markup=catalog_keyboard()
            )
            return

        cart.append(product["name"])

        keyboard = [
            [InlineKeyboardButton("🛒 Перейти в корзину", callback_data="cart")],
            [InlineKeyboardButton("⬅️ Назад", callback_data=product["back"])],
            [InlineKeyboardButton("📦 В каталог", callback_data="catalog")],
        ]

        await query.edit_message_text(
            text=f"{product['name']} добавлен в корзину ✅",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "cart":
        if not cart:
            text = "Корзина пустая 🛒"
            keyboard = [
                [InlineKeyboardButton("📦 В каталог", callback_data="catalog")],
            ]
        else:
            items = "\n".join([f"{i + 1}. {item}" for i, item in enumerate(cart)])
            text = f"Твоя корзина:\n\n{items}"

            keyboard = [
                [InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout")],
                [InlineKeyboardButton("🧹 Очистить корзину", callback_data="clear_cart")],
                [InlineKeyboardButton("📦 В каталог", callback_data="catalog")],
            ]

        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "clear_cart":
        cart.clear()

        keyboard = [
            [InlineKeyboardButton("📦 В каталог", callback_data="catalog")],
        ]

        await query.edit_message_text(
            text="Корзина очищена ✅",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "checkout":
        if not cart:
            keyboard = [
                [InlineKeyboardButton("📦 В каталог", callback_data="catalog")],
            ]

            await query.edit_message_text(
                text="Корзина пустая. Сначала добавь товар 🛒",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        admin_id = get_admin_id()

        if not admin_id:
            await query.edit_message_text(
                text=(
                    "Ошибка: ADMIN_ID не настроен.\n\n"
                    "Добавь ADMIN_ID в Railway Variables."
                ),
                reply_markup=main_menu_keyboard()
            )
            return

        user = query.from_user

        username = f"@{user.username}" if user.username else "username не указан"
        full_name = user.full_name
        user_id = user.id

        items = "\n".join([f"{i + 1}. {item}" for i, item in enumerate(cart)])

        order_text = (
            "🆕 Новый заказ!\n\n"
            f"Клиент: {full_name}\n"
            f"Username: {username}\n"
            f"Telegram ID: {user_id}\n\n"
            f"Товары:\n{items}"
        )

        await context.bot.send_message(
            chat_id=admin_id,
            text=order_text
        )

        cart.clear()

        keyboard = [
            [InlineKeyboardButton("📦 В каталог", callback_data="catalog")],
        ]

        await query.edit_message_text(
            text="Заказ оформлен ✅\nМенеджер скоро свяжется с тобой.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


def main():
    token = get_token()

    print("Проверка BOT_TOKEN...")
    print("BOT_TOKEN найден:", bool(token))

    if not token:
        print("Ошибка: Railway не передал BOT_TOKEN в приложение.")
        print("Проверь Railway → worker → Variables.")
        return

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
