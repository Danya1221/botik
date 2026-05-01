import os
from datetime import datetime

import psycopg

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


def get_env(name, default=None):
    value = os.environ.get(name, default)
    if isinstance(value, str):
        return value.strip()
    return value


def get_token():
    return get_env("BOT_TOKEN")


def get_database_url():
    return get_env("DATABASE_URL")


def get_admin_id():
    admin_id = get_env("ADMIN_ID")

    if not admin_id:
        return None

    try:
        return int(admin_id)
    except ValueError:
        return None


def get_admin_login():
    return get_env("ADMIN_LOGIN", "admin")


def get_admin_password():
    return get_env("ADMIN_PASSWORD", "123netizen321")


def db_connect():
    database_url = get_database_url()

    if not database_url:
        raise RuntimeError("DATABASE_URL не найден. Добавь DATABASE_URL в Railway Variables.")

    return psycopg.connect(database_url, autocommit=True)


def init_db():
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    price TEXT DEFAULT '',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    username TEXT,
                    full_name TEXT,
                    items TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)


def get_categories():
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM categories ORDER BY id;")
            return cur.fetchall()


def get_category(category_id):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM categories WHERE id = %s;", (category_id,))
            return cur.fetchone()


def add_category(name):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO categories (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id;",
                (name,)
            )
            row = cur.fetchone()
            return row[0] if row else None


def get_products_by_category(category_id):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, description, price
                FROM products
                WHERE category_id = %s AND is_active = TRUE
                ORDER BY id;
                """,
                (category_id,)
            )
            return cur.fetchall()


def get_product(product_id):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.id, p.name, p.description, p.price, c.name
                FROM products p
                JOIN categories c ON c.id = p.category_id
                WHERE p.id = %s AND p.is_active = TRUE;
                """,
                (product_id,)
            )
            return cur.fetchone()


def get_all_products():
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.id, p.name, p.description, p.price, c.name
                FROM products p
                JOIN categories c ON c.id = p.category_id
                WHERE p.is_active = TRUE
                ORDER BY c.id, p.id;
                """
            )
            return cur.fetchall()


def add_product(category_id, name, price, description):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO products (category_id, name, price, description)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                """,
                (category_id, name, price, description)
            )
            return cur.fetchone()[0]


def update_product_price(product_id, price):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE products SET price = %s WHERE id = %s;",
                (price, product_id)
            )


def delete_product(product_id):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE products SET is_active = FALSE WHERE id = %s;",
                (product_id,)
            )


def save_order(user_id, username, full_name, items):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO orders (user_id, username, full_name, items)
                VALUES (%s, %s, %s, %s);
                """,
                (user_id, username, full_name, items)
            )


reply_menu = ReplyKeyboardMarkup(
    keyboard=[
        ["📦 Каталог"]
    ],
    resize_keyboard=True
)


def is_admin_user(user_id):
    admin_id = get_admin_id()
    return admin_id is not None and user_id == admin_id


def is_admin_logged(context):
    return context.user_data.get("admin_logged") is True


def catalog_keyboard():
    categories = get_categories()

    keyboard = []

    for category_id, name in categories:
        keyboard.append([
            InlineKeyboardButton(name, callback_data=f"cat_{category_id}")
        ])

    keyboard.append([InlineKeyboardButton("🛒 Корзина", callback_data="cart")])

    return InlineKeyboardMarkup(keyboard)


def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить категорию", callback_data="admin_add_category")],
        [InlineKeyboardButton("➕ Добавить товар", callback_data="admin_add_product")],
        [InlineKeyboardButton("📋 Список товаров", callback_data="admin_products")],
        [InlineKeyboardButton("🚪 Выйти из админки", callback_data="admin_logout")],
    ])


async def delete_catalog_job(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    chat_id = job_data["chat_id"]
    message_id = job_data["message_id"]

    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        (
            'Добро пожаловать в Netizen! '
            '<tg-emoji emoji-id="5339547060859345402">☺</tg-emoji>\n\n'
            'Мы знаем, как найти то, что вам нужно. '
            'От мощных игровых станций до компактных смартфонов — '
            'поможем разобраться в мире гаджетов без лишнего шума.'
        ),
        reply_markup=reply_menu,
        parse_mode="HTML"
    )


async def send_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    categories = get_categories()

    if not categories:
        await update.message.reply_text(
            "Каталог пока пустой.\n\nСкоро здесь появятся товары.",
            reply_markup=reply_menu
        )
        return

    message = await update.message.reply_text(
        "Каталог товаров:\n\nВыбери категорию:",
        reply_markup=catalog_keyboard()
    )

    context.job_queue.run_once(
        delete_catalog_job,
        when=CATALOG_LIFETIME_SECONDS,
        data={
            "chat_id": message.chat_id,
            "message_id": message.message_id,
        },
        name=f"delete_catalog_{message.chat_id}_{message.message_id}"
    )


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_admin_user(user_id):
        await update.message.reply_text("У тебя нет доступа к админке.")
        return

    context.user_data["admin_state"] = "wait_login"
    context.user_data["admin_logged"] = False

    await update.message.reply_text("Введи логин админки:")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

    admin_state = context.user_data.get("admin_state")

    if admin_state == "wait_login":
        if text == get_admin_login():
            context.user_data["admin_state"] = "wait_password"
            await update.message.reply_text("Теперь введи пароль:")
        else:
            context.user_data["admin_state"] = None
            await update.message.reply_text("Неверный логин.")
        return

    if admin_state == "wait_password":
        if text == get_admin_password():
            context.user_data["admin_logged"] = True
            context.user_data["admin_state"] = None

            await update.message.reply_text(
                "Вход выполнен ✅\n\nАдмин-панель:",
                reply_markup=admin_keyboard()
            )
        else:
            context.user_data["admin_logged"] = False
            context.user_data["admin_state"] = None

            await update.message.reply_text("Неверный пароль.")
        return

    if admin_state == "add_category_name":
        if not is_admin_user(user_id) or not is_admin_logged(context):
            await update.message.reply_text("Нет доступа.")
            return

        category_name = text
        category_id = add_category(category_name)

        context.user_data["admin_state"] = None

        if category_id:
            await update.message.reply_text(
                f"Категория добавлена ✅\n\nНазвание: {category_name}",
                reply_markup=admin_keyboard()
            )
        else:
            await update.message.reply_text(
                "Такая категория уже есть.",
                reply_markup=admin_keyboard()
            )
        return

    if admin_state == "add_product_name":
        context.user_data["new_product_name"] = text
        context.user_data["admin_state"] = "add_product_price"

        await update.message.reply_text("Введи цену товара:")
        return

    if admin_state == "add_product_price":
        context.user_data["new_product_price"] = text
        context.user_data["admin_state"] = "add_product_description"

        await update.message.reply_text(
            "Введи описание товара.\n\n"
            "Например: 256GB, Blue, новый.\n"
            "Если описание не нужно, напиши -"
        )
        return

    if admin_state == "add_product_description":
        category_id = context.user_data.get("new_product_category_id")
        name = context.user_data.get("new_product_name")
        price = context.user_data.get("new_product_price")
        description = "" if text == "-" else text

        if not category_id or not name or not price:
            context.user_data["admin_state"] = None
            await update.message.reply_text(
                "Ошибка добавления товара. Попробуй заново.",
                reply_markup=admin_keyboard()
            )
            return

        product_id = add_product(category_id, name, price, description)

        context.user_data["admin_state"] = None
        context.user_data.pop("new_product_category_id", None)
        context.user_data.pop("new_product_name", None)
        context.user_data.pop("new_product_price", None)

        await update.message.reply_text(
            f"Товар добавлен ✅\n\n"
            f"ID: {product_id}\n"
            f"Название: {name}\n"
            f"Цена: {price}",
            reply_markup=admin_keyboard()
        )
        return

    if admin_state == "change_price":
        product_id = context.user_data.get("change_price_product_id")

        if not product_id:
            context.user_data["admin_state"] = None
            await update.message.reply_text("Ошибка. Попробуй заново.", reply_markup=admin_keyboard())
            return

        update_product_price(product_id, text)

        context.user_data["admin_state"] = None
        context.user_data.pop("change_price_product_id", None)

        await update.message.reply_text(
            f"Цена обновлена ✅\n\nНовая цена: {text}",
            reply_markup=admin_keyboard()
        )
        return

    if text == "📦 Каталог":
        await send_catalog(update, context)
        return

    await update.message.reply_text(
        "Нажми кнопку 📦 Каталог внизу.",
        reply_markup=reply_menu
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    cart = context.user_data.setdefault("cart", [])

    if data == "catalog":
        categories = get_categories()

        if not categories:
            await query.edit_message_text("Каталог пока пустой.")
            return

        await query.edit_message_text(
            text="Каталог товаров:\n\nВыбери категорию:",
            reply_markup=catalog_keyboard()
        )

    elif data.startswith("cat_"):
        category_id = int(data.replace("cat_", ""))
        category = get_category(category_id)

        if not category:
            await query.edit_message_text(
                text="Категория не найдена.",
                reply_markup=catalog_keyboard()
            )
            return

        products = get_products_by_category(category_id)

        keyboard = []

        for product_id, name, description, price in products:
            keyboard.append([
                InlineKeyboardButton(name, callback_data=f"product_{product_id}")
            ])

        keyboard.append([InlineKeyboardButton("⬅️ Назад в каталог", callback_data="catalog")])
        keyboard.append([InlineKeyboardButton("🛒 Корзина", callback_data="cart")])

        if not products:
            text = f"Категория: {category[1]}\n\nТоваров пока нет."
        else:
            text = f"Категория: {category[1]}\n\nВыбери товар:"

        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("product_"):
        product_id = int(data.replace("product_", ""))
        product = get_product(product_id)

        if not product:
            await query.edit_message_text(
                text="Товар не найден.",
                reply_markup=catalog_keyboard()
            )
            return

        product_id, name, description, price, category_name = product

        text = (
            f"{name}\n\n"
            f"Категория: {category_name}\n"
            f"Цена: {price}\n"
        )

        if description:
            text += f"\nОписание:\n{description}\n"

        keyboard = [
            [InlineKeyboardButton("➕ Добавить в корзину", callback_data=f"add_{product_id}")],
            [InlineKeyboardButton("⬅️ Назад", callback_data=f"cat_back_{category_name}")],
            [InlineKeyboardButton("🛒 Корзина", callback_data="cart")],
            [InlineKeyboardButton("📦 В каталог", callback_data="catalog")],
        ]

        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("cat_back_"):
        category_name = data.replace("cat_back_", "")

        categories = get_categories()
        category_id = None

        for cid, cname in categories:
            if cname == category_name:
                category_id = cid
                break

        if category_id:
            products = get_products_by_category(category_id)
            keyboard = []

            for product_id, name, description, price in products:
                keyboard.append([
                    InlineKeyboardButton(name, callback_data=f"product_{product_id}")
                ])

            keyboard.append([InlineKeyboardButton("⬅️ Назад в каталог", callback_data="catalog")])
            keyboard.append([InlineKeyboardButton("🛒 Корзина", callback_data="cart")])

            await query.edit_message_text(
                text=f"Категория: {category_name}\n\nВыбери товар:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text(
                text="Категория не найдена.",
                reply_markup=catalog_keyboard()
            )

    elif data.startswith("add_"):
        product_id = int(data.replace("add_", ""))
        product = get_product(product_id)

        if not product:
            await query.edit_message_text("Товар не найден.")
            return

        cart.append(product_id)

        _, name, description, price, category_name = product

        await query.edit_message_text(
            text=f"{name} добавлен в корзину ✅",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Перейти в корзину", callback_data="cart")],
                [InlineKeyboardButton("📦 В каталог", callback_data="catalog")],
            ])
        )

    elif data == "cart":
        if not cart:
            await query.edit_message_text(
                text="Корзина пустая 🛒",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 В каталог", callback_data="catalog")]
                ])
            )
            return

        lines = []
        for index, product_id in enumerate(cart, start=1):
            product = get_product(product_id)
            if product:
                _, name, description, price, category_name = product
                lines.append(f"{index}. {name} — {price}")

        text = "Твоя корзина:\n\n" + "\n".join(lines)

        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout")],
                [InlineKeyboardButton("🧹 Очистить корзину", callback_data="clear_cart")],
                [InlineKeyboardButton("📦 В каталог", callback_data="catalog")],
            ])
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
            await query.edit_message_text("Корзина пустая.")
            return

        admin_id = get_admin_id()

        if not admin_id:
            await query.edit_message_text("ADMIN_ID не настроен.")
            return

        user = query.from_user
        username = f"@{user.username}" if user.username else "username не указан"
        full_name = user.full_name
        user_id = user.id

        lines = []

        for index, product_id in enumerate(cart, start=1):
            product = get_product(product_id)
            if product:
                _, name, description, price, category_name = product
                lines.append(f"{index}. {name} — {price}")

        items_text = "\n".join(lines)

        order_text = (
            "🆕 Новый заказ!\n\n"
            f"Клиент: {full_name}\n"
            f"Username: {username}\n"
            f"Telegram ID: {user_id}\n\n"
            f"Товары:\n{items_text}\n\n"
            f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

        save_order(user_id, username, full_name, items_text)

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

    elif data == "admin_add_category":
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        context.user_data["admin_state"] = "add_category_name"

        await query.edit_message_text("Введи название новой категории:")

    elif data == "admin_add_product":
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        categories = get_categories()

        if not categories:
            await query.edit_message_text(
                text="Сначала добавь хотя бы одну категорию.",
                reply_markup=admin_keyboard()
            )
            return

        keyboard = []

        for category_id, name in categories:
            keyboard.append([
                InlineKeyboardButton(name, callback_data=f"admin_product_cat_{category_id}")
            ])

        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_menu")])

        await query.edit_message_text(
            text="Выбери категорию для товара:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("admin_product_cat_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        category_id = int(data.replace("admin_product_cat_", ""))

        context.user_data["new_product_category_id"] = category_id
        context.user_data["admin_state"] = "add_product_name"

        await query.edit_message_text("Введи название товара:")

    elif data == "admin_products":
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        products = get_all_products()

        if not products:
            await query.edit_message_text(
                text="Товаров пока нет.",
                reply_markup=admin_keyboard()
            )
            return

        keyboard = []

        for product_id, name, description, price, category_name in products:
            keyboard.append([
                InlineKeyboardButton(
                    f"{name} — {price}",
                    callback_data=f"admin_product_{product_id}"
                )
            ])

        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_menu")])

        await query.edit_message_text(
            text="Список товаров:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("admin_product_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        product_id = int(data.replace("admin_product_", ""))
        product = get_product(product_id)

        if not product:
            await query.edit_message_text(
                text="Товар не найден.",
                reply_markup=admin_keyboard()
            )
            return

        product_id, name, description, price, category_name = product

        text = (
            f"Товар #{product_id}\n\n"
            f"Название: {name}\n"
            f"Категория: {category_name}\n"
            f"Цена: {price}\n"
        )

        if description:
            text += f"\nОписание:\n{description}"

        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Изменить цену", callback_data=f"admin_price_{product_id}")],
                [InlineKeyboardButton("🗑 Удалить товар", callback_data=f"admin_delete_{product_id}")],
                [InlineKeyboardButton("⬅️ К товарам", callback_data="admin_products")],
            ])
        )

    elif data.startswith("admin_price_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        product_id = int(data.replace("admin_price_", ""))

        context.user_data["change_price_product_id"] = product_id
        context.user_data["admin_state"] = "change_price"

        await query.edit_message_text("Введи новую цену товара:")

    elif data.startswith("admin_delete_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        product_id = int(data.replace("admin_delete_", ""))
        delete_product(product_id)

        await query.edit_message_text(
            text="Товар удалён ✅",
            reply_markup=admin_keyboard()
        )

    elif data == "admin_menu":
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        await query.edit_message_text(
            text="Админ-панель:",
            reply_markup=admin_keyboard()
        )

    elif data == "admin_logout":
        context.user_data["admin_logged"] = False
        context.user_data["admin_state"] = None

        await query.edit_message_text("Ты вышел из админки.")


def main():
    token = get_token()

    print("Проверка BOT_TOKEN...")
    print("BOT_TOKEN найден:", bool(token))
    print("DATABASE_URL найден:", bool(get_database_url()))
    print("ADMIN_ID найден:", bool(get_admin_id()))

    if not token:
        print("Ошибка: BOT_TOKEN не найден.")
        return

    if not get_database_url():
        print("Ошибка: DATABASE_URL не найден.")
        return

    init_db()
    print("База данных готова.")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
