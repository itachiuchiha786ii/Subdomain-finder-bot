
import asyncio
import telegram
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
import subprocess
import io
import os
import threading
from concurrent.futures import ThreadPoolExecutor
import logging
import time
from collections import deque

DOMAIN_FILE, THREAD_COUNT = range(2)
BOT_TOKEN = "8036829100:AAFWWcmdh4uwAoEB5jwToBPmQOzbp5Dn3Mo"
SUBFINDER_PATH = "subfinder"
MAX_THREADS = 20
ADMIN_USER_ID = 5798520543  # replace with your Telegram user ID

logging.basicConfig(
    filename="subfinder_bot.log",
    filemode="w",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def is_admin(user_id):
    return user_id == ADMIN_USER_ID

def enum_subdomains(domain, progress_data):
    try:
        start_time = time.time()
        result = subprocess.run(
            [SUBFINDER_PATH, "-d", domain],
            capture_output=True,
            text=True,
            check=True
        )
        subdomains = result.stdout.splitlines()
        duration = time.time() - start_time
        return domain, subdomains, duration
    except Exception as e:
        return domain, [f"Error: {e}"], 0
    finally:
        with progress_data["lock"]:
            progress_data["domains_processed"] += 1
            progress_data["total_time"] += duration
            progress_data["recent_times"].append(duration)
            if len(progress_data["recent_times"]) > 10:
                progress_data["recent_times"].popleft()

def create_result_file(results):
    output = io.StringIO()
    total = 0
    for domain, subdomains in results.items():
                for sub in subdomains:
                	output.write(f"{sub}\n")
                	total += len(subdomains)
    output.seek(0)
    return output, total

async def send_result_file(update: Update, context: ContextTypes.DEFAULT_TYPE, result_file, summary):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=summary)
    await context.bot.send_document(chat_id=update.effective_chat.id, document=io.BytesIO(result_file.read().encode()), filename="results.txt")
    result_file.close()
    if os.path.exists("subfinder_bot.log"):
        with open("subfinder_bot.log", "rb") as log_f:
            await context.bot.send_document(chat_id=update.effective_chat.id, document=log_f, filename="scan.log")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Unauthorized access.")
        return ConversationHandler.END
    await update.message.reply_text("Welcome! Use /cmd or /help.")
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("/start - Welcome\n/enum - Start scan\n/proc - Show progress\n/cancel - Cancel scan\n/help - Help")

async def list_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await help_command(update, context)

async def alive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("Bot is alive.")

async def enum_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    await update.message.reply_text("Send .txt file with domains.")
    return DOMAIN_FILE

async def receive_domain_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    document = update.message.document
    if document.mime_type != "text/plain":
        await update.message.reply_text("Only .txt files allowed.")
        return DOMAIN_FILE
    try:
        telegram_file = await context.bot.get_file(document.file_id)
        file_bytes = await telegram_file.download_as_bytearray()
        domain_list = file_bytes.decode().splitlines()
        domain_list = [d.strip() for d in domain_list if d.strip()]
        if not domain_list:
            await update.message.reply_text("Empty file.")
            return DOMAIN_FILE
        if len(domain_list) > 100:
            await update.message.reply_text("Max 100 domains.")
            return DOMAIN_FILE
        context.user_data["domain_list"] = domain_list
        await update.message.reply_text("Enter number of threads (1â€“20):")
        return THREAD_COUNT
    except Exception as e:
        logger.error(f"File error: {e}")
        await update.message.reply_text("Could not read file.")
        return DOMAIN_FILE

async def receive_thread_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    try:
        thread_count = int(update.message.text)
        if not (1 <= thread_count <= MAX_THREADS): raise ValueError
        domain_list = context.user_data["domain_list"]
        progress_data = {
            "domains_processed": 0,
            "total_domains": len(domain_list),
            "total_time": 0.0,
            "start_time": time.time(),
            "recent_times": deque(maxlen=10),
            "lock": threading.Lock(),
            "chat_id": update.effective_chat.id,
            "is_cancelled": False,
            "results": {}
        }
        context.user_data["progress_data"] = progress_data
        await update.message.reply_text("Enumeration started...")
        asyncio.create_task(process_domains_threaded(domain_list, thread_count, update, context))
        return ConversationHandler.END
    except:
        await update.message.reply_text("Invalid number.")
        return THREAD_COUNT

async def process_domains_threaded(domain_list, thread_count, update, context):
    progress_data = context.user_data["progress_data"]
    results = progress_data["results"]
    try:
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            loop = asyncio.get_running_loop()
            tasks = [loop.run_in_executor(executor, enum_subdomains, domain, progress_data) for domain in domain_list]
            for task in asyncio.as_completed(tasks):
                if progress_data["is_cancelled"]:
                    await update.message.reply_text("Cancelled.")
                    return
                domain, subs, duration = await task
                results[domain] = subs
        result_file, total_subs = create_result_file(results)
        avg_time = progress_data["total_time"] / progress_data["total_domains"]
        summary = f"Scan Summary:\nDomains: {progress_data['total_domains']}\nSubdomains: {total_subs}\nAvg Time: {avg_time:.2f}s"
        await send_result_file(update, context, result_file, summary)
    except Exception as e:
        logger.error(f"Process error: {e}")
        await update.message.reply_text("Scan failed.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    progress_data = context.user_data.get("progress_data")
    if progress_data:
        with progress_data["lock"]:
            progress_data["is_cancelled"] = True
        await update.message.reply_text("Scan cancelled.")
    else:
        await update.message.reply_text("No scan in progress.")
    return ConversationHandler.END

async def proc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    progress_data = context.user_data.get("progress_data")
    if not progress_data:
        await update.message.reply_text("Nothing running.")
        return
    with progress_data["lock"]:
        done = progress_data["domains_processed"]
        total = progress_data["total_domains"]
        elapsed = time.time() - progress_data["start_time"]
        await update.message.reply_text(f"Progress: {done}/{total}\nElapsed: {elapsed:.1f}s\nCancelled: {progress_data['is_cancelled']}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("enum", enum_start)],
        states={
            DOMAIN_FILE: [MessageHandler(filters.Document.MimeType("text/plain"), receive_domain_file)],
            THREAD_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_thread_count)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cmd", list_commands))
    app.add_handler(CommandHandler("alive", alive))
    app.add_handler(CommandHandler("proc", proc))
    app.add_handler(CommandHandler("cancel", cancel))
    app.run_polling()

if __name__ == "__main__":
    main()