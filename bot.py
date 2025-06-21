import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from supabase import create_client, Client

# --- НАСТРОЙКИ ---
# Получаем данные для подключения к Supabase из переменных окружения
# Перед запуском выполните в терминале:
# export SUPABASE_URL="ВАШ_URL_ИЗ_НАСТРОЕК_API"
# export SUPABASE_SERVICE_KEY="ВАШ_SERVICE_ROLE_КЛЮЧ"
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

# --- Проверка наличия настроек ---
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL and Key must be set in environment variables.")

# --- Инициализация клиента Supabase ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Функции бота ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    user = update.effective_user
    user_id = user.id
    
    await update.message.reply_html(
        rf"👋 Привет, {user.mention_html()}!",
        reply_markup=None,
    )
    await update.message.reply_text(
        f"Я бот для обновления количества свободных сапов.\n\n"
        f"Ваш Telegram ID: `{user_id}`\n\n"
        f"Просто отправьте мне число (например, `5`), и я обновлю количество доступных сапов для вашей точки проката."
    )

async def update_sup_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик сообщений с числом."""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    if not message_text.isdigit():
        await update.message.reply_text("Пожалуйста, отправьте просто число. Например: 8")
        return

    new_count = int(message_text)
    
    try:
        # Обновляем данные в таблице 'locations'
        # Ищем строку, где owner_telegram_id равен ID пользователя, и меняем availableSups
        data, count = supabase.table('locations').update({'availableSups': new_count}).eq('owner_telegram_id', user_id).execute()
        
        # data[1] содержит список обновленных записей. Если он пуст, значит, владелец не найден.
        if not data[1]:
            await update.message.reply_text("❌ Не удалось найти вашу точку проката. Убедитесь, что ваш ID правильно указан в базе данных.")
            logger.warning(f"Owner with Telegram ID {user_id} not found in Supabase.")
            return
        
        # Получаем название точки для более информативного ответа
        location_data = data[1][0]
        location_name = location_data.get('name', 'Без названия')
        
        await update.message.reply_text(
            f"✅ Готово!\n\n"
            f"Для точки «{location_name}» установлено новое количество свободных сапов: *{new_count}*",
            parse_mode='Markdown'
        )
        logger.info(f"Updated availableSups to {new_count} for owner {user_id} at location '{location_name}'")

    except Exception as e:
        await update.message.reply_text("Произошла непредвиденная ошибка. Администратор уже уведомлен.")
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)


def main() -> None:
    """Основная функция для запуска бота."""
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN environment variable not set!")
        return

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, update_sup_count))

    logger.info("Starting bot...")
    application.run_polling()


if __name__ == "__main__":
    main()

