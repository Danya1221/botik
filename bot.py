import os

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


CATALOG_LIFETIME_SECONDS = 24 * 60 * 60


def get_token():
    token = os.environ.get("BOT_TOKEN")
    if token:
        token = token.strip()
    return token


def get_admin_id():
    admin_id = os.environ.get("ADMIN_ID")
    if admin_id:
        admin_id = admin_id.strip()

    if not admin_id:
        return None

    try:
        return int(admin_id)
    except ValueError:
        return None


reply_menu = ReplyKeyboardMarkup(
    keyboard=[
        ["📦 Каталог"]
    ],
    resize_keyboard=True
)


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
}


def catalog_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("iPhone", callback_data="category_iphone")],
        [InlineKeyboardButton("Samsung", callback_data="category_samsung")],
        [InlineKeyboardButton("Xiaomi", callback_data="category_xiaomi")],
        [InlineKeyboardButton("🛒 Корзина", callback_data="cart")],
    ])


def category_iphone_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("iPhone 15 Pro", callback_data="product_iphone_15_pro")],
        [InlineKeyboardButton("iPhone 15", callback_data="product_iphone_15")],
        [InlineKeyboardButton("⬅️ Назад в каталог", callback_data="catalog")],
        [InlineKeyboardButton("🛒 Корзина", callback_data="cart")],
    ])


def category_samsung_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Samsung S24 Ultra", callback_data="product_samsung_s24_ultra")],
        [InlineKeyboardButton("⬅️ Назад в каталог", callback_data="catalog")],
        [InlineKeyboardButton("🛒 Корзина", callback_data="cart")],
    ])


def category_xiaomi_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Xiaomi 14", callback_data="product_xiaomi_14")],
        [InlineKeyboardButton("⬅️ Назад в каталог", callback_data="catalog")],
        [InlineKeyboardButton("🛒 Корзина", callback_data="cart")],
    ])


async def delete_catalog_job(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    chat_id = job_data["chat_id"]
    message_id = job_data["message_id"]

    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

    catalog_messages = context.bot_data.setdefault("catalog_messages", [])
    context.bot_data["catalog_messages"] = [
        item for item in catalog_messages
        if not (item["chat_id"] == chat_id and item["message_id"] == message_id)
    ]


async def send_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = await update.message.reply_text(
        "Каталог товаров:\n\nВыбери категорию:",
        reply_markup=catalog_keyboard()
    )

    catalog_messages = context.bot_data.setdefault("catalog_messages", [])
    catalog_messages.append({
        "chat_id": message.chat_id,
        "message_id": message.message_id,
    })

    context.job_queue.run_once(
        delete_catalog_job,
        when=CATALOG_LIFETIME_SECONDS,
        data={
            "chat_id": message.chat_id,
            "message_id": message.message_id,
        },
        name=f"delete_catalog_{message.chat_id}_{message.message_id}"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Добро пожаловать 👋\n\n"
        "Внизу всегда будет кнопка каталога.\n"
        "Нажми 📦 Каталог, чтобы посмотреть товары.",
        reply_markup=reply_menu
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📦 Каталог":
        await send_catalog(update, context)
    else:
        await update.message.reply_text(
            "Нажми кнопку 📦 Каталог внизу.",
            reply_markup=reply_menu
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
        await query.edit_message_text(
            text="Каталог iPhone:\n\nВыбери модель:",
            reply_markup=category_iphone_keyboard()
        )

    elif data == "category_samsung":
        await query.edit_message_text(
            text="Каталог Samsung:\n\nВыбери модель:",
            reply_markup=category_samsung_keyboard()
        )

    elif data == "category_xiaomi":
        await query.edit_message_text(
            text="Каталог Xiaomi:\n\nВыбери модель:",
            reply_markup=category_xiaomi_keyboard()
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

        await query.edit_message_text(
            text="Корзина очищена ✅",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 В каталог", callback_data="catalog")]
            ])
        )

    elif data == "checkout":
        if not cart:
            await query.edit_message_text(
                text="Корзина пустая. Сначала добавь товар 🛒",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 В каталог", callback_data="catalog")]
                ])
            )
            return

        admin_id = get_admin_id()

        if not admin_id:
            await query.edit_message_text(
                text="Ошибка: ADMIN_ID не настроен в Railway Variables."
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

        await query.edit_message_text(
            text="Заказ оформлен ✅\nМенеджер скоро свяжется с тобой.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 В каталог", callback_data="catalog")]
            ])
        )


async def prices_updated(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = get_admin_id()

    if update.effective_user.id != admin_id:
        await update.message.reply_text("У тебя нет доступа к этой команде.")
        return

    catalog_messages = context.bot_data.setdefault("catalog_messages", [])

    deleted_count = 0

    for item in catalog_messages:
        try:
            await context.bot.delete_message(
                chat_id=item["chat_id"],
                message_id=item["message_id"]
            )
            deleted_count += 1
        except Exception:
            pass

    context.bot_data["catalog_messages"] = []

    await update.message.reply_text(
        f"Старые каталоги удалены ✅\nУдалено сообщений: {deleted_count}",
        reply_markup=reply_menu
    )


def main():
    token = get_token()

    print("Проверка BOT_TOKEN...")
    print("BOT_TOKEN найден:", bool(token))

    if not token:
        print("Ошибка: Railway не передал BOT_TOKEN.")
        return

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("prices_updated", prices_updated))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
