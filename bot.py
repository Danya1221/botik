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
ADMIN_PAGE_SIZE = 12

USE_PREMIUM_BUTTON_EMOJI = True
DEFAULT_PREMIUM_EMOJI_ID = "5339547060859345402"

ADMIN_PANEL_TEXT = (
    "⚙️ Админ-панель Netizen\n\n"
    "Выберите действие для управления каталогом:"
)

CATALOG_TEXT = (
    "Каталог товаров Netizen\n\n"
    "Выберите нужную категорию из списка ниже:"
)


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
                ALTER TABLE categories
                ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS models (
                    id SERIAL PRIMARY KEY,
                    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            cur.execute("""
                ALTER TABLE models
                ADD COLUMN IF NOT EXISTS description TEXT DEFAULT '';
            """)

            cur.execute("""
                ALTER TABLE models
                ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS variants (
                    id SERIAL PRIMARY KEY,
                    model_id INTEGER NOT NULL REFERENCES models(id) ON DELETE CASCADE,
                    color TEXT NOT NULL,
                    memory TEXT NOT NULL,
                    price TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            cur.execute("""
                ALTER TABLE variants
                ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
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

            cur.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username TEXT,
                    full_name TEXT,
                    role TEXT DEFAULT 'admin',
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin_login_attempts (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT,
                    username TEXT,
                    full_name TEXT,
                    login TEXT,
                    success BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)


def get_categories():
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name
                FROM categories
                WHERE is_active = TRUE
                ORDER BY id;
            """)
            return cur.fetchall()


def get_category(category_id):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name
                FROM categories
                WHERE id = %s AND is_active = TRUE;
            """, (category_id,))
            return cur.fetchone()


def add_category(name):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO categories (name, is_active)
                VALUES (%s, TRUE)
                ON CONFLICT (name)
                DO UPDATE SET is_active = TRUE
                RETURNING id;
            """, (name,))
            return cur.fetchone()[0]


def rename_category(category_id, new_name):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE categories
                SET name = %s
                WHERE id = %s;
            """, (new_name, category_id))


def delete_category(category_id):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE categories
                SET is_active = FALSE
                WHERE id = %s;
            """, (category_id,))


def get_models_by_category(category_id):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, description
                FROM models
                WHERE category_id = %s AND is_active = TRUE
                ORDER BY id;
            """, (category_id,))
            return cur.fetchall()


def get_model(model_id):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT m.id, m.name, m.description, c.id, c.name
                FROM models m
                JOIN categories c ON c.id = m.category_id
                WHERE m.id = %s
                  AND m.is_active = TRUE
                  AND c.is_active = TRUE;
            """, (model_id,))
            return cur.fetchone()


def get_all_models():
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT m.id, m.name, m.description, c.name
                FROM models m
                JOIN categories c ON c.id = m.category_id
                WHERE m.is_active = TRUE
                  AND c.is_active = TRUE
                ORDER BY c.id, m.id;
            """)
            return cur.fetchall()


def add_model(category_id, name, description):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO models (category_id, name, description)
                VALUES (%s, %s, %s)
                RETURNING id;
            """, (category_id, name, description))
            return cur.fetchone()[0]


def rename_model(model_id, new_name):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE models
                SET name = %s
                WHERE id = %s;
            """, (new_name, model_id))


def update_model_description(model_id, new_description):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE models
                SET description = %s
                WHERE id = %s;
            """, (new_description, model_id))


def delete_model(model_id):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE models
                SET is_active = FALSE
                WHERE id = %s;
            """, (model_id,))


def get_variants_by_model(model_id):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, color, memory, price
                FROM variants
                WHERE model_id = %s AND is_active = TRUE
                ORDER BY id;
            """, (model_id,))
            return cur.fetchall()


def get_variant(variant_id):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    v.id,
                    v.color,
                    v.memory,
                    v.price,
                    m.id,
                    m.name,
                    c.id,
                    c.name
                FROM variants v
                JOIN models m ON m.id = v.model_id
                JOIN categories c ON c.id = m.category_id
                WHERE v.id = %s
                  AND v.is_active = TRUE
                  AND m.is_active = TRUE
                  AND c.is_active = TRUE;
            """, (variant_id,))
            return cur.fetchone()


def get_all_variants():
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    v.id,
                    c.name,
                    m.name,
                    v.color,
                    v.memory,
                    v.price
                FROM variants v
                JOIN models m ON m.id = v.model_id
                JOIN categories c ON c.id = m.category_id
                WHERE v.is_active = TRUE
                  AND m.is_active = TRUE
                  AND c.is_active = TRUE
                ORDER BY c.id, m.id, v.id;
            """)
            return cur.fetchall()


def add_variant(model_id, color, memory, price):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO variants (model_id, color, memory, price)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            """, (model_id, color, memory, price))
            return cur.fetchone()[0]


def update_variant_color(variant_id, color):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE variants
                SET color = %s
                WHERE id = %s;
            """, (color, variant_id))


def update_variant_memory(variant_id, memory):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE variants
                SET memory = %s
                WHERE id = %s;
            """, (memory, variant_id))


def update_variant_price(variant_id, price):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE variants
                SET price = %s
                WHERE id = %s;
            """, (price, variant_id))


def delete_variant(variant_id):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE variants
                SET is_active = FALSE
                WHERE id = %s;
            """, (variant_id,))


def save_order(user_id, username, full_name, items):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO orders (user_id, username, full_name, items)
                VALUES (%s, %s, %s, %s);
            """, (user_id, username, full_name, items))


def is_admin_in_db(telegram_id):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id
                FROM admins
                WHERE telegram_id = %s;
            """, (telegram_id,))
            return cur.fetchone() is not None


def add_admin_to_db(telegram_id, username, full_name):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO admins (telegram_id, username, full_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (telegram_id)
                DO UPDATE SET
                    username = EXCLUDED.username,
                    full_name = EXCLUDED.full_name;
            """, (telegram_id, username, full_name))


def save_admin_login_attempt(telegram_id, username, full_name, login, success):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO admin_login_attempts
                (telegram_id, username, full_name, login, success)
                VALUES (%s, %s, %s, %s, %s);
            """, (telegram_id, username, full_name, login, success))


def is_admin_user(user_id):
    main_admin_id = get_admin_id()

    if main_admin_id and user_id == main_admin_id:
        return True

    return is_admin_in_db(user_id)


def is_admin_logged(context):
    return context.user_data.get("admin_logged") is True


reply_menu = ReplyKeyboardMarkup(
    keyboard=[
        ["📦 Каталог"]
    ],
    resize_keyboard=True
)


def pbutton(text, callback_data, emoji_id=DEFAULT_PREMIUM_EMOJI_ID):
    api_kwargs = {}

    if USE_PREMIUM_BUTTON_EMOJI and emoji_id:
        api_kwargs["icon_custom_emoji_id"] = emoji_id

    return InlineKeyboardButton(
        text=text,
        callback_data=callback_data,
        api_kwargs=api_kwargs
    )


def make_two_columns(buttons):
    keyboard = []

    for i in range(0, len(buttons), 2):
        keyboard.append(buttons[i:i + 2])

    return keyboard


def paginate_items(items, page, page_size=ADMIN_PAGE_SIZE):
    total = len(items)
    start = page * page_size
    end = start + page_size
    return items[start:end], total


def pagination_buttons(prefix, page, total, page_size=ADMIN_PAGE_SIZE):
    buttons = []
    max_page = (total - 1) // page_size if total > 0 else 0
    row = []

    if page > 0:
        row.append(pbutton("Назад", f"{prefix}_{page - 1}"))

    if page < max_page:
        row.append(pbutton("Вперёд", f"{prefix}_{page + 1}"))

    if row:
        buttons.append(row)

    return buttons


def catalog_keyboard():
    categories = get_categories()

    buttons = [
        pbutton(name, f"cat_{category_id}")
        for category_id, name in categories
    ]

    keyboard = make_two_columns(buttons)
    keyboard.append([pbutton("Открыть корзину", "cart")])

    return InlineKeyboardMarkup(keyboard)


def admin_keyboard():
    return InlineKeyboardMarkup([
        [pbutton("Добавить новую категорию", "admin_add_category")],
        [pbutton("Добавить новую модель", "admin_add_model")],
        [pbutton("Добавить вариант цвета/памяти", "admin_add_variant")],
        [pbutton("Редактор категорий", "admin_edit_categories")],
        [pbutton("Редактор моделей", "admin_edit_models")],
        [pbutton("Редактор вариантов", "admin_catalog")],
        [pbutton("Выйти из админ-панели", "admin_logout")],
    ])


def admin_choose_category_for_model_keyboard(page=0):
    categories = get_categories()
    page_items, total = paginate_items(categories, page)

    keyboard = []

    for category_id, name in page_items:
        keyboard.append([pbutton(name, f"admin_model_cat_{category_id}")])

    keyboard += pagination_buttons("admin_add_model_page", page, total)
    keyboard.append([pbutton("Назад в админ-панель", "admin_menu")])

    return InlineKeyboardMarkup(keyboard)


def admin_choose_model_for_variant_keyboard(page=0):
    models = get_all_models()
    page_items, total = paginate_items(models, page)

    keyboard = []

    for model_id, model_name, description, category_name in page_items:
        keyboard.append([
            pbutton(f"{category_name} → {model_name}", f"admin_variant_model_{model_id}")
        ])

    keyboard += pagination_buttons("admin_add_variant_page", page, total)
    keyboard.append([pbutton("Назад в админ-панель", "admin_menu")])

    return InlineKeyboardMarkup(keyboard)


def admin_edit_categories_keyboard(page=0):
    categories = get_categories()
    page_items, total = paginate_items(categories, page)

    keyboard = []

    for category_id, name in page_items:
        keyboard.append([pbutton(name, f"admin_edit_category_{category_id}")])

    keyboard += pagination_buttons("admin_edit_categories_page", page, total)
    keyboard.append([pbutton("Назад в админ-панель", "admin_menu")])

    return InlineKeyboardMarkup(keyboard)


def admin_edit_models_keyboard(page=0):
    models = get_all_models()
    page_items, total = paginate_items(models, page)

    keyboard = []

    for model_id, model_name, description, category_name in page_items:
        keyboard.append([
            pbutton(f"{category_name} → {model_name}", f"admin_edit_model_{model_id}")
        ])

    keyboard += pagination_buttons("admin_edit_models_page", page, total)
    keyboard.append([pbutton("Назад в админ-панель", "admin_menu")])

    return InlineKeyboardMarkup(keyboard)


def admin_edit_variants_keyboard(page=0):
    variants = get_all_variants()
    page_items, total = paginate_items(variants, page)

    keyboard = []

    for variant_id, category_name, model_name, color, memory, price in page_items:
        keyboard.append([
            pbutton(
                f"{model_name} / {color} / {memory} — {price}",
                f"admin_edit_variant_{variant_id}"
            )
        ])

    keyboard += pagination_buttons("admin_catalog_page", page, total)
    keyboard.append([pbutton("Назад в админ-панель", "admin_menu")])

    return InlineKeyboardMarkup(keyboard)


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
            (
                "Каталог Netizen\n\n"
                "Каталог пока пустой.\n\n"
                "Скоро здесь появятся товары."
            ),
            reply_markup=reply_menu
        )
        return

    message = await update.message.reply_text(
        CATALOG_TEXT,
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
    context.user_data["admin_state"] = "wait_login"
    context.user_data["admin_logged"] = False

    await update.message.reply_text(
        "🔐 Вход в админ-панель Netizen\n\nВведите логин:"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    user_id = user.id
    username = f"@{user.username}" if user.username else None
    full_name = user.full_name

    admin_state = context.user_data.get("admin_state")

    if admin_state == "wait_login":
        context.user_data["admin_login_input"] = text

        if text == get_admin_login():
            context.user_data["admin_state"] = "wait_password"
            await update.message.reply_text("Теперь введите пароль:")
        else:
            context.user_data["admin_state"] = None
            save_admin_login_attempt(user_id, username, full_name, text, False)
            await update.message.reply_text("Неверный логин.")
        return

    if admin_state == "wait_password":
        login = context.user_data.get("admin_login_input", "")

        if text == get_admin_password():
            context.user_data["admin_logged"] = True
            context.user_data["admin_state"] = None

            add_admin_to_db(user_id, username, full_name)
            save_admin_login_attempt(user_id, username, full_name, login, True)

            await update.message.reply_text(
                "Вход выполнен ✅\n\n" + ADMIN_PANEL_TEXT,
                reply_markup=admin_keyboard()
            )
        else:
            context.user_data["admin_logged"] = False
            context.user_data["admin_state"] = None
            save_admin_login_attempt(user_id, username, full_name, login, False)
            await update.message.reply_text("Неверный пароль.")
        return

    if admin_state == "add_category_name":
        if not is_admin_user(user_id) or not is_admin_logged(context):
            await update.message.reply_text("Нет доступа.")
            return

        if text == "📦 Каталог":
            await update.message.reply_text(
                "Сейчас вы добавляете категорию.\n\nВведите название категории текстом, например: iPhone"
            )
            return

        category_id = add_category(text)
        context.user_data["admin_state"] = None

        await update.message.reply_text(
            (
                "Категория добавлена ✅\n\n"
                f"ID: {category_id}\n"
                f"Название: {text}"
            ),
            reply_markup=admin_keyboard()
        )
        return

    if admin_state == "rename_category":
        if not is_admin_user(user_id) or not is_admin_logged(context):
            await update.message.reply_text("Нет доступа.")
            return

        category_id = context.user_data.get("edit_category_id")

        if not category_id:
            context.user_data["admin_state"] = None
            await update.message.reply_text("Ошибка. Категория не найдена.", reply_markup=admin_keyboard())
            return

        try:
            rename_category(category_id, text)
            await update.message.reply_text(
                f"Категория переименована ✅\n\nНовое название: {text}",
                reply_markup=admin_keyboard()
            )
        except Exception as e:
            await update.message.reply_text(
                f"Ошибка переименования категории:\n{e}",
                reply_markup=admin_keyboard()
            )

        context.user_data["admin_state"] = None
        context.user_data.pop("edit_category_id", None)
        return

    if admin_state == "add_model_name":
        if not is_admin_user(user_id) or not is_admin_logged(context):
            await update.message.reply_text("Нет доступа.")
            return

        if text == "📦 Каталог":
            await update.message.reply_text(
                "Сейчас вы добавляете модель.\n\nВведите название модели текстом, например: iPhone 17 Pro"
            )
            return

        context.user_data["new_model_name"] = text
        context.user_data["admin_state"] = "add_model_description"

        await update.message.reply_text(
            (
                "Введите описание модели.\n\n"
                "Например: Флагманская модель Apple.\n"
                "Если описание не нужно, напишите -"
            )
        )
        return

    if admin_state == "add_model_description":
        if not is_admin_user(user_id) or not is_admin_logged(context):
            await update.message.reply_text("Нет доступа.")
            return

        category_id = context.user_data.get("new_model_category_id")
        model_name = context.user_data.get("new_model_name")
        description = "" if text == "-" else text

        if not category_id or not model_name:
            context.user_data["admin_state"] = None
            await update.message.reply_text(
                "Ошибка добавления модели. Попробуйте заново.",
                reply_markup=admin_keyboard()
            )
            return

        model_id = add_model(category_id, model_name, description)

        context.user_data["admin_state"] = None
        context.user_data.pop("new_model_category_id", None)
        context.user_data.pop("new_model_name", None)

        await update.message.reply_text(
            (
                "Модель добавлена ✅\n\n"
                f"ID: {model_id}\n"
                f"Название: {model_name}"
            ),
            reply_markup=admin_keyboard()
        )
        return

    if admin_state == "rename_model":
        if not is_admin_user(user_id) or not is_admin_logged(context):
            await update.message.reply_text("Нет доступа.")
            return

        model_id = context.user_data.get("edit_model_id")

        if not model_id:
            context.user_data["admin_state"] = None
            await update.message.reply_text("Ошибка. Модель не найдена.", reply_markup=admin_keyboard())
            return

        rename_model(model_id, text)

        context.user_data["admin_state"] = None
        context.user_data.pop("edit_model_id", None)

        await update.message.reply_text(
            f"Модель переименована ✅\n\nНовое название: {text}",
            reply_markup=admin_keyboard()
        )
        return

    if admin_state == "edit_model_description":
        if not is_admin_user(user_id) or not is_admin_logged(context):
            await update.message.reply_text("Нет доступа.")
            return

        model_id = context.user_data.get("edit_model_id")
        new_description = "" if text == "-" else text

        if not model_id:
            context.user_data["admin_state"] = None
            await update.message.reply_text("Ошибка. Модель не найдена.", reply_markup=admin_keyboard())
            return

        update_model_description(model_id, new_description)

        context.user_data["admin_state"] = None
        context.user_data.pop("edit_model_id", None)

        await update.message.reply_text(
            "Описание модели обновлено ✅",
            reply_markup=admin_keyboard()
        )
        return

    if admin_state == "add_variant_color":
        if not is_admin_user(user_id) or not is_admin_logged(context):
            await update.message.reply_text("Нет доступа.")
            return

        if text == "📦 Каталог":
            await update.message.reply_text(
                "Сейчас вы добавляете цвет.\n\nВведите цвет текстом, например: Black"
            )
            return

        context.user_data["new_variant_color"] = text
        context.user_data["admin_state"] = "add_variant_memory"

        await update.message.reply_text(
            "Введите память.\n\nНапример: 128GB, 256GB, 512GB"
        )
        return

    if admin_state == "add_variant_memory":
        if not is_admin_user(user_id) or not is_admin_logged(context):
            await update.message.reply_text("Нет доступа.")
            return

        if text == "📦 Каталог":
            await update.message.reply_text(
                "Сейчас вы добавляете память.\n\nВведите память текстом, например: 256GB"
            )
            return

        context.user_data["new_variant_memory"] = text
        context.user_data["admin_state"] = "add_variant_price"

        await update.message.reply_text(
            "Введите цену.\n\nНапример: 999$, 120 000 ₽, 450 000 ₸"
        )
        return

    if admin_state == "add_variant_price":
        if not is_admin_user(user_id) or not is_admin_logged(context):
            await update.message.reply_text("Нет доступа.")
            return

        if text == "📦 Каталог":
            await update.message.reply_text(
                "Сейчас вы добавляете цену.\n\nВведите цену текстом, например: 999$"
            )
            return

        model_id = context.user_data.get("new_variant_model_id")
        color = context.user_data.get("new_variant_color")
        memory = context.user_data.get("new_variant_memory")
        price = text

        if not model_id or not color or not memory:
            context.user_data["admin_state"] = None
            await update.message.reply_text(
                "Ошибка добавления варианта. Попробуйте заново.",
                reply_markup=admin_keyboard()
            )
            return

        variant_id = add_variant(model_id, color, memory, price)

        context.user_data["admin_state"] = None
        context.user_data.pop("new_variant_model_id", None)
        context.user_data.pop("new_variant_color", None)
        context.user_data.pop("new_variant_memory", None)

        await update.message.reply_text(
            (
                "Вариант добавлен ✅\n\n"
                f"ID: {variant_id}\n"
                f"Цвет: {color}\n"
                f"Память: {memory}\n"
                f"Цена: {price}"
            ),
            reply_markup=admin_keyboard()
        )
        return

    if admin_state == "change_variant_color":
        if not is_admin_user(user_id) or not is_admin_logged(context):
            await update.message.reply_text("Нет доступа.")
            return

        variant_id = context.user_data.get("edit_variant_id")
        update_variant_color(variant_id, text)

        context.user_data["admin_state"] = None
        context.user_data.pop("edit_variant_id", None)

        await update.message.reply_text(
            f"Цвет обновлён ✅\n\nНовый цвет: {text}",
            reply_markup=admin_keyboard()
        )
        return

    if admin_state == "change_variant_memory":
        if not is_admin_user(user_id) or not is_admin_logged(context):
            await update.message.reply_text("Нет доступа.")
            return

        variant_id = context.user_data.get("edit_variant_id")
        update_variant_memory(variant_id, text)

        context.user_data["admin_state"] = None
        context.user_data.pop("edit_variant_id", None)

        await update.message.reply_text(
            f"Память обновлена ✅\n\nНовое значение: {text}",
            reply_markup=admin_keyboard()
        )
        return

    if admin_state == "change_variant_price":
        if not is_admin_user(user_id) or not is_admin_logged(context):
            await update.message.reply_text("Нет доступа.")
            return

        variant_id = context.user_data.get("edit_variant_id")
        update_variant_price(variant_id, text)

        context.user_data["admin_state"] = None
        context.user_data.pop("edit_variant_id", None)

        await update.message.reply_text(
            (
                "Цена обновлена ✅\n\n"
                f"Новая цена: {text}"
            ),
            reply_markup=admin_keyboard()
        )
        return

    if text == "📦 Каталог":
        await send_catalog(update, context)
        return

    await update.message.reply_text(
        "Нажмите кнопку 📦 Каталог внизу.",
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
            await query.edit_message_text("Каталог Netizen\n\nКаталог пока пустой.")
            return

        await query.edit_message_text(
            text=CATALOG_TEXT,
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

        models = get_models_by_category(category_id)

        buttons = [
            pbutton(name, f"model_{model_id}")
            for model_id, name, description in models
        ]

        keyboard = make_two_columns(buttons)
        keyboard.append([pbutton("Назад в каталог", "catalog")])
        keyboard.append([pbutton("Открыть корзину", "cart")])

        if not models:
            text_msg = f"Категория: {category[1]}\n\nМоделей пока нет."
        else:
            text_msg = f"Категория: {category[1]}\n\nВыберите модель из списка ниже:"

        await query.edit_message_text(
            text=text_msg,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("model_"):
        model_id = int(data.replace("model_", ""))
        model = get_model(model_id)

        if not model:
            await query.edit_message_text(
                text="Модель не найдена.",
                reply_markup=catalog_keyboard()
            )
            return

        model_id, model_name, description, category_id, category_name = model
        variants = get_variants_by_model(model_id)

        buttons = [
            pbutton(f"{color} / {memory}", f"variant_{variant_id}")
            for variant_id, color, memory, price in variants
        ]

        keyboard = make_two_columns(buttons)
        keyboard.append([pbutton("Назад к моделям", f"cat_{category_id}")])
        keyboard.append([pbutton("Открыть корзину", "cart")])
        keyboard.append([pbutton("Вернуться в каталог", "catalog")])

        text_msg = f"{model_name}\n\nКатегория: {category_name}\n"

        if description:
            text_msg += f"\nОписание:\n{description}\n"

        if not variants:
            text_msg += "\nВариантов пока нет."
        else:
            text_msg += "\nВыберите цвет и память:"

        await query.edit_message_text(
            text=text_msg,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("variant_"):
        variant_id = int(data.replace("variant_", ""))
        variant = get_variant(variant_id)

        if not variant:
            await query.edit_message_text(
                text="Вариант не найден.",
                reply_markup=catalog_keyboard()
            )
            return

        (
            variant_id,
            color,
            memory,
            price,
            model_id,
            model_name,
            category_id,
            category_name
        ) = variant

        text_msg = (
            f"{model_name}\n\n"
            f"Категория: {category_name}\n"
            f"Цвет: {color}\n"
            f"Память: {memory}\n"
            f"Цена: {price}\n\n"
            "Нажмите кнопку ниже, чтобы добавить этот вариант в корзину."
        )

        keyboard = [
            [pbutton("Добавить в корзину", f"add_{variant_id}")],
            [pbutton("Назад к вариантам", f"model_{model_id}")],
            [pbutton("Открыть корзину", "cart")],
            [pbutton("Вернуться в каталог", "catalog")],
        ]

        await query.edit_message_text(
            text=text_msg,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("add_"):
        variant_id = int(data.replace("add_", ""))
        variant = get_variant(variant_id)

        if not variant:
            await query.edit_message_text("Вариант не найден.")
            return

        cart.append(variant_id)

        (
            _,
            color,
            memory,
            price,
            model_id,
            model_name,
            category_id,
            category_name
        ) = variant

        await query.edit_message_text(
            text=(
                f"{model_name} добавлен в корзину ✅\n\n"
                f"Цвет: {color}\n"
                f"Память: {memory}\n"
                f"Цена: {price}\n\n"
                "Можно перейти в корзину или вернуться в каталог."
            ),
            reply_markup=InlineKeyboardMarkup([
                [pbutton("Перейти в корзину", "cart")],
                [pbutton("Назад к вариантам", f"model_{model_id}")],
                [pbutton("Вернуться в каталог", "catalog")],
            ])
        )

    elif data == "cart":
        if not cart:
            await query.edit_message_text(
                text="Корзина Netizen\n\nКорзина пока пустая.",
                reply_markup=InlineKeyboardMarkup([
                    [pbutton("Вернуться в каталог", "catalog")]
                ])
            )
            return

        lines = []
        total_count = 0

        for index, variant_id in enumerate(cart, start=1):
            variant = get_variant(variant_id)
            if variant:
                (
                    _,
                    color,
                    memory,
                    price,
                    model_id,
                    model_name,
                    category_id,
                    category_name
                ) = variant

                lines.append(f"{index}. {model_name} / {color} / {memory} — {price}")
                total_count += 1

        text_msg = (
            "Корзина Netizen\n\n"
            + "\n".join(lines)
            + f"\n\nПозиций в корзине: {total_count}"
        )

        await query.edit_message_text(
            text=text_msg,
            reply_markup=InlineKeyboardMarkup([
                [pbutton("Оформить заказ", "checkout")],
                [pbutton("Очистить корзину", "clear_cart")],
                [pbutton("Вернуться в каталог", "catalog")],
            ])
        )

    elif data == "clear_cart":
        cart.clear()

        await query.edit_message_text(
            text=(
                "Корзина очищена ✅\n\n"
                "Вы можете вернуться в каталог и выбрать новые товары."
            ),
            reply_markup=InlineKeyboardMarkup([
                [pbutton("Вернуться в каталог", "catalog")]
            ])
        )

    elif data == "checkout":
        if not cart:
            await query.edit_message_text("Корзина пустая. Сначала добавьте товар.")
            return

        main_admin_id = get_admin_id()

        if not main_admin_id:
            await query.edit_message_text("ADMIN_ID не настроен.")
            return

        user = query.from_user
        username = f"@{user.username}" if user.username else "username не указан"
        full_name = user.full_name
        user_id = user.id

        lines = []

        for index, variant_id in enumerate(cart, start=1):
            variant = get_variant(variant_id)
            if variant:
                (
                    _,
                    color,
                    memory,
                    price,
                    model_id,
                    model_name,
                    category_id,
                    category_name
                ) = variant

                lines.append(f"{index}. {model_name} / {color} / {memory} — {price}")

        items_text = "\n".join(lines)

        order_text = (
            "🆕 Новый заказ Netizen!\n\n"
            f"Клиент: {full_name}\n"
            f"Username: {username}\n"
            f"Telegram ID: {user_id}\n\n"
            f"Товары:\n{items_text}\n\n"
            f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

        save_order(user_id, username, full_name, items_text)

        await context.bot.send_message(
            chat_id=main_admin_id,
            text=order_text
        )

        cart.clear()

        await query.edit_message_text(
            text=(
                "Заказ оформлен ✅\n\n"
                "Менеджер скоро свяжется с вами."
            ),
            reply_markup=InlineKeyboardMarkup([
                [pbutton("Вернуться в каталог", "catalog")]
            ])
        )

    elif data == "admin_add_category":
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        context.user_data["admin_state"] = "add_category_name"
        await query.edit_message_text("➕ Добавление категории\n\nВведите название новой категории:")

    elif data == "admin_add_model":
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        categories = get_categories()

        if not categories:
            await query.edit_message_text(
                text="Категорий пока нет.\n\nСначала добавьте хотя бы одну категорию.",
                reply_markup=admin_keyboard()
            )
            return

        await query.edit_message_text(
            text="➕ Добавление модели\n\nВыберите категорию для новой модели:",
            reply_markup=admin_choose_category_for_model_keyboard(page=0)
        )

    elif data.startswith("admin_add_model_page_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        page = int(data.replace("admin_add_model_page_", ""))

        await query.edit_message_text(
            text="➕ Добавление модели\n\nВыберите категорию для новой модели:",
            reply_markup=admin_choose_category_for_model_keyboard(page=page)
        )

    elif data.startswith("admin_model_cat_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        category_id = int(data.replace("admin_model_cat_", ""))

        context.user_data["new_model_category_id"] = category_id
        context.user_data["admin_state"] = "add_model_name"

        await query.edit_message_text("Введите название модели.\n\nНапример: iPhone 17 Pro")

    elif data == "admin_add_variant":
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        models = get_all_models()

        if not models:
            await query.edit_message_text(
                text="Моделей пока нет.\n\nСначала добавьте хотя бы одну модель.",
                reply_markup=admin_keyboard()
            )
            return

        await query.edit_message_text(
            text=(
                "➕ Добавление варианта\n\n"
                "Выберите модель, для которой добавляем цвет/память/цену:"
            ),
            reply_markup=admin_choose_model_for_variant_keyboard(page=0)
        )

    elif data.startswith("admin_add_variant_page_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        page = int(data.replace("admin_add_variant_page_", ""))

        await query.edit_message_text(
            text=(
                "➕ Добавление варианта\n\n"
                "Выберите модель, для которой добавляем цвет/память/цену:"
            ),
            reply_markup=admin_choose_model_for_variant_keyboard(page=page)
        )

    elif data.startswith("admin_variant_model_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        model_id = int(data.replace("admin_variant_model_", ""))

        context.user_data["new_variant_model_id"] = model_id
        context.user_data["admin_state"] = "add_variant_color"

        await query.edit_message_text("Введите цвет.\n\nНапример: Black, White, Blue, Natural Titanium")

    elif data == "admin_edit_categories":
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        categories = get_categories()

        if not categories:
            await query.edit_message_text(
                text="Редактор категорий\n\nКатегорий пока нет.",
                reply_markup=admin_keyboard()
            )
            return

        await query.edit_message_text(
            text="Редактор категорий Netizen\n\nВыберите категорию для редактирования:",
            reply_markup=admin_edit_categories_keyboard(page=0)
        )

    elif data.startswith("admin_edit_categories_page_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        page = int(data.replace("admin_edit_categories_page_", ""))

        await query.edit_message_text(
            text="Редактор категорий Netizen\n\nВыберите категорию для редактирования:",
            reply_markup=admin_edit_categories_keyboard(page=page)
        )

    elif data.startswith("admin_edit_category_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        category_id = int(data.replace("admin_edit_category_", ""))
        category = get_category(category_id)

        if not category:
            await query.edit_message_text("Категория не найдена.", reply_markup=admin_keyboard())
            return

        category_id, category_name = category

        await query.edit_message_text(
            text=(
                f"Категория #{category_id}\n\n"
                f"Название: {category_name}\n\n"
                "Выберите действие:"
            ),
            reply_markup=InlineKeyboardMarkup([
                [pbutton("Переименовать категорию", f"admin_rename_category_{category_id}")],
                [pbutton("Удалить категорию", f"admin_delete_category_{category_id}")],
                [pbutton("Назад к категориям", "admin_edit_categories")],
            ])
        )

    elif data.startswith("admin_rename_category_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        category_id = int(data.replace("admin_rename_category_", ""))
        context.user_data["edit_category_id"] = category_id
        context.user_data["admin_state"] = "rename_category"

        await query.edit_message_text("Введите новое название категории:")

    elif data.startswith("admin_delete_category_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        category_id = int(data.replace("admin_delete_category_", ""))
        delete_category(category_id)

        await query.edit_message_text(
            text="Категория удалена ✅\n\nОна больше не отображается в каталоге.",
            reply_markup=admin_keyboard()
        )

    elif data == "admin_edit_models":
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        models = get_all_models()

        if not models:
            await query.edit_message_text(
                text="Редактор моделей\n\nМоделей пока нет.",
                reply_markup=admin_keyboard()
            )
            return

        await query.edit_message_text(
            text="Редактор моделей Netizen\n\nВыберите модель для редактирования:",
            reply_markup=admin_edit_models_keyboard(page=0)
        )

    elif data.startswith("admin_edit_models_page_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        page = int(data.replace("admin_edit_models_page_", ""))

        await query.edit_message_text(
            text="Редактор моделей Netizen\n\nВыберите модель для редактирования:",
            reply_markup=admin_edit_models_keyboard(page=page)
        )

    elif data.startswith("admin_edit_model_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        model_id = int(data.replace("admin_edit_model_", ""))
        model = get_model(model_id)

        if not model:
            await query.edit_message_text("Модель не найдена.", reply_markup=admin_keyboard())
            return

        model_id, model_name, description, category_id, category_name = model

        text_msg = (
            f"Модель #{model_id}\n\n"
            f"Категория: {category_name}\n"
            f"Название: {model_name}\n"
        )

        if description:
            text_msg += f"\nОписание:\n{description}\n"
        else:
            text_msg += "\nОписание: не указано\n"

        await query.edit_message_text(
            text=text_msg,
            reply_markup=InlineKeyboardMarkup([
                [pbutton("Переименовать модель", f"admin_rename_model_{model_id}")],
                [pbutton("Изменить описание", f"admin_model_desc_{model_id}")],
                [pbutton("Удалить модель", f"admin_delete_model_{model_id}")],
                [pbutton("Назад к моделям", "admin_edit_models")],
            ])
        )

    elif data.startswith("admin_rename_model_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        model_id = int(data.replace("admin_rename_model_", ""))
        context.user_data["edit_model_id"] = model_id
        context.user_data["admin_state"] = "rename_model"

        await query.edit_message_text("Введите новое название модели:")

    elif data.startswith("admin_model_desc_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        model_id = int(data.replace("admin_model_desc_", ""))
        context.user_data["edit_model_id"] = model_id
        context.user_data["admin_state"] = "edit_model_description"

        await query.edit_message_text(
            "Введите новое описание модели.\n\nЕсли описание нужно очистить, отправьте -"
        )

    elif data.startswith("admin_delete_model_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        model_id = int(data.replace("admin_delete_model_", ""))
        delete_model(model_id)

        await query.edit_message_text(
            text="Модель удалена ✅\n\nОна больше не отображается в каталоге.",
            reply_markup=admin_keyboard()
        )

    elif data == "admin_catalog":
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        variants = get_all_variants()

        if not variants:
            await query.edit_message_text(
                text="Редактор вариантов Netizen\n\nВариантов пока нет.",
                reply_markup=admin_keyboard()
            )
            return

        await query.edit_message_text(
            text="Редактор вариантов Netizen\n\nВыберите вариант для редактирования:",
            reply_markup=admin_edit_variants_keyboard(page=0)
        )

    elif data.startswith("admin_catalog_page_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        page = int(data.replace("admin_catalog_page_", ""))

        await query.edit_message_text(
            text="Редактор вариантов Netizen\n\nВыберите вариант для редактирования:",
            reply_markup=admin_edit_variants_keyboard(page=page)
        )

    elif data.startswith("admin_edit_variant_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        variant_id = int(data.replace("admin_edit_variant_", ""))
        variant = get_variant(variant_id)

        if not variant:
            await query.edit_message_text(
                text="Вариант не найден.",
                reply_markup=admin_keyboard()
            )
            return

        (
            variant_id,
            color,
            memory,
            price,
            model_id,
            model_name,
            category_id,
            category_name
        ) = variant

        text_msg = (
            f"Вариант #{variant_id}\n\n"
            f"Категория: {category_name}\n"
            f"Модель: {model_name}\n"
            f"Цвет: {color}\n"
            f"Память: {memory}\n"
            f"Цена: {price}"
        )

        await query.edit_message_text(
            text=text_msg,
            reply_markup=InlineKeyboardMarkup([
                [pbutton("Изменить цвет", f"admin_variant_color_{variant_id}")],
                [pbutton("Изменить память", f"admin_variant_memory_{variant_id}")],
                [pbutton("Изменить цену", f"admin_variant_price_{variant_id}")],
                [pbutton("Удалить вариант", f"admin_variant_delete_{variant_id}")],
                [pbutton("Назад к вариантам", "admin_catalog")],
            ])
        )

    elif data.startswith("admin_variant_color_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        variant_id = int(data.replace("admin_variant_color_", ""))
        context.user_data["edit_variant_id"] = variant_id
        context.user_data["admin_state"] = "change_variant_color"

        await query.edit_message_text("Введите новый цвет варианта:")

    elif data.startswith("admin_variant_memory_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        variant_id = int(data.replace("admin_variant_memory_", ""))
        context.user_data["edit_variant_id"] = variant_id
        context.user_data["admin_state"] = "change_variant_memory"

        await query.edit_message_text("Введите новое значение памяти:")

    elif data.startswith("admin_variant_price_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        variant_id = int(data.replace("admin_variant_price_", ""))
        context.user_data["edit_variant_id"] = variant_id
        context.user_data["admin_state"] = "change_variant_price"

        await query.edit_message_text("Введите новую цену варианта:")

    elif data.startswith("admin_variant_delete_"):
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        variant_id = int(data.replace("admin_variant_delete_", ""))
        delete_variant(variant_id)

        await query.edit_message_text(
            text="Вариант удалён ✅\n\nОн больше не будет отображаться в каталоге.",
            reply_markup=admin_keyboard()
        )

    elif data == "admin_menu":
        if not is_admin_user(query.from_user.id) or not is_admin_logged(context):
            await query.edit_message_text("Нет доступа.")
            return

        await query.edit_message_text(
            text=ADMIN_PANEL_TEXT,
            reply_markup=admin_keyboard()
        )

    elif data == "admin_logout":
        context.user_data["admin_logged"] = False
        context.user_data["admin_state"] = None

        await query.edit_message_text("Вы вышли из админ-панели.")


def main():
    token = get_token()

    print("Проверка переменных Railway...")
    print("BOT_TOKEN найден:", bool(token))
    print("DATABASE_URL найден:", bool(get_database_url()))
    print("ADMIN_ID найден:", bool(get_admin_id()))
    print("Premium emoji buttons:", USE_PREMIUM_BUTTON_EMOJI)

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
