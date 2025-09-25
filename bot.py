import logging
import re
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

import os
import sys
import logging
from glob import glob
try:
    from gdrive_backup import upload_or_update
except Exception as e:
    logging.error(f"Failed to import gdrive_backup: {e}")
    upload_or_update = None

# Startup checks for required files
REQUIRED_FILES = [
    'credentials.json',
    # 'token.pickle',  # Not required on first run
]
for f in REQUIRED_FILES:
    if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), f)):
        logging.error(f"Required file missing: {f}. Please add it to the project directory.")
        sys.exit(1)

# Google Drive folder ID for backups
GDRIVE_FOLDER_ID = "1_zCcV7txijg6vn4urIeCYmTQcIq2sa30"
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes, ConversationHandler
)
from config import BOT_TOKEN, ADMINS, ALLOWED_DOMAINS, YOUTUBE_SCREENSHOT_GUIDE_LINK, YOUTUBE_LINK_GUIDE_LINK, YOUTUBE_CHANNEL_LINK, TELEGRAM_CHANNEL_LINK
from db import init_db, add_user, update_points, get_points, is_admin, add_viewed_link, get_viewed_links
from ocr_utils import extract_fields_from_image
from link_store import add_link, get_random_link
import datetime
import json

from payment_utils import get_invoice, precheckout_callback, successful_payment

logging.basicConfig(level=logging.INFO)

# States for ConversationHandler
RULES, SCREENSHOT, MAIN_MENU, GAIN_POINTS, POST_LINK, BUY_POINTS = range(6)

user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = user.id
    # Check if user is a member of the required channel
    try:
        member = await context.bot.get_chat_member(TELEGRAM_CHANNEL_LINK, chat_id)
        if member.status in ["member", "administrator", "creator"]:
            # User is a member, proceed as normal
            keyboard = [
                [InlineKeyboardButton('✅ Yes', callback_data='accept_rules_yes'), InlineKeyboardButton('❌ No', callback_data='accept_rules_no')]
            ]
            welcome = (
                f"👋 Hey {user.username or 'there'}!\n\n"
                "🐼 Welcome to Panda Clicker!\n\n"
                "This bot is a peer-to-peer (P2P) platform where we share our Opera News links to help each other increase our views. In exchange, you must also view others' links.\n\n"
                "📱 Rules are simple:\n"
                "1️⃣ You must have the Opera News app installed and be signed in. (You can't post or view links if you don't!)\n"
                "2️⃣ Be honest and help each other.\n"
                "3️⃣ We track all activity. If you cheat, you will be removed.\n\n"
                "Before you continue, we need to check a few things.\n\n"
                "Do you wish to continue?"
            )
            await update.message.reply_text(welcome, reply_markup=InlineKeyboardMarkup(keyboard))
            return RULES
        else:
            raise Exception("Not a member")
    except Exception:
        # User is not a member or error occurred
        join_keyboard = [
            [InlineKeyboardButton('Join Channel', url=TELEGRAM_CHANNEL_LINK)],
            [InlineKeyboardButton('✅ I Joined', callback_data='check_channel_joined')]
        ]
        join_msg = (
            "🚨 To use this bot, you must join our official channel first!\n\n"
            f"👉 [Join the Channel]({TELEGRAM_CHANNEL_LINK})\n\n"
            "After joining, click 'I Joined' below to continue."
        )
        await update.message.reply_text(join_msg, reply_markup=InlineKeyboardMarkup(join_keyboard), parse_mode="Markdown")
        return ConversationHandler.END

# Add a callback handler for 'check_channel_joined' to recheck membership
async def check_channel_joined_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    chat_id = user.id
    try:
        member = await context.bot.get_chat_member(TELEGRAM_CHANNEL_LINK, chat_id)
        if member.status in ["member", "administrator", "creator"]:
            # User is now a member, proceed
            keyboard = [
                [InlineKeyboardButton('✅ Yes', callback_data='accept_rules_yes'), InlineKeyboardButton('❌ No', callback_data='accept_rules_no')]
            ]
            welcome = (
                f"👋 Hey {user.username or 'there'}!\n\n"
                "🐼 Welcome to Panda Clicker!\n\n"
                "This bot is a peer-to-peer (P2P) platform where we share our Opera News links to help each other increase our views. In exchange, you must also view others' links.\n\n"
                "📱 Rules are simple:\n"
                "1️⃣ You must have the Opera News app installed and be signed in. (You can't post or view links if you don't!)\n"
                "2️⃣ Be honest and help each other.\n"
                "3️⃣ We track all activity. If you cheat, you will be removed.\n\n"
                "Before you continue, we need to check a few things.\n\n"
                "Do you wish to continue?"
            )
            await query.edit_message_text(welcome, reply_markup=InlineKeyboardMarkup(keyboard))
            return RULES
        else:
            raise Exception("Not a member")
    except Exception:
        join_keyboard = [
            [InlineKeyboardButton('Join Channel', url=TELEGRAM_CHANNEL_LINK)],
            [InlineKeyboardButton('✅ I Joined', callback_data='check_channel_joined')]
        ]
        join_msg = (
            "❌ You are still not a member of the channel. Please join and try again.\n\n"
            f"👉 [Join the Channel]({TELEGRAM_CHANNEL_LINK})\n\n"
            "After joining, click 'I Joined' below to continue."
        )
        await query.edit_message_text(join_msg, reply_markup=InlineKeyboardMarkup(join_keyboard), parse_mode="Markdown")
        return ConversationHandler.END

async def rules_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'accept_rules_yes':
        guide_msg = (
            "🖼️ We need a screenshot from your Opera News app to verify you have it installed.\n\n"
            f"▶️ Watch this quick guide: {YOUTUBE_SCREENSHOT_GUIDE_LINK}"
        )
        await query.edit_message_text(guide_msg)
        return SCREENSHOT
    else:
        await query.edit_message_text('❌ You must accept the rules to use this bot.')
        return ConversationHandler.END

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text('⚠️ Please send a screenshot photo from your Opera News app.')
        return SCREENSHOT
    await update.message.reply_text('⏳ Processing...')
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_path = f"temp_{update.message.from_user.id}.jpg"
    await file.download_to_drive(file_path)
    success, found = extract_fields_from_image(file_path)
    os.remove(file_path)
    if success:
        user = update.message.from_user
        add_user(user.id, user.username, is_admin=int(user.id in ADMINS))
        await update.message.reply_text('🎉 Hurray! You passed verification. You can now help others and get help!')
        return await show_main_menu(update, context)
    else:
        await update.message.reply_text('❌ Could not verify your screenshot. Please try again.')
        return SCREENSHOT

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton('Post Link'), KeyboardButton('Gain Points')],
        [KeyboardButton('Buy Points'), KeyboardButton('Explore YT')],
        [KeyboardButton('View My Points')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    if update.message:
        await update.message.reply_text('Main Menu:', reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text('Main Menu:')
        await update.callback_query.message.reply_text('Main Menu:', reply_markup=reply_markup)
    return MAIN_MENU

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text if update.message else None
    back_keyboard = ReplyKeyboardMarkup([[KeyboardButton('Back to Menu')]], resize_keyboard=True)
    # ...existing code...

    # Handle post link state
    if context.user_data.get('expecting_post_link'):
        if text == 'Back to Menu':
            context.user_data['expecting_post_link'] = False
            return await show_main_menu(update, context)
        processing_msg = await update.message.reply_text('⏳ Processing...')
        url = text.strip()
        if not (url.startswith('https://opr.news/') or 'operanewsapp.com' in url):
            await context.bot.delete_message(chat_id=update.message.chat_id, message_id=processing_msg.message_id)
            await update.message.reply_text('Please send a valid Opera News link (short or long format).')
            return
        user = update.message.from_user
        admin = is_admin(user.id)
        points = get_points(user.id)
        if not admin and (points is None or points < 1):
            await context.bot.delete_message(chat_id=update.message.chat_id, message_id=processing_msg.message_id)
            await update.message.reply_text('Not enough points to post a link. You need at least 1 point.')
            context.user_data['expecting_post_link'] = False
            return await show_main_menu(update, context)
        if not admin:
            update_points(user.id, -1)
        from link_store import normalize_opera_link, get_next_link_id, add_link
        short_url = normalize_opera_link(url)
        link_id = get_next_link_id()
        add_link({
            'id': link_id,
            'url': short_url,
            'user_id': user.id,
            'timestamp': datetime.datetime.now().isoformat(),
            'is_admin': admin
        })
        # After adding a link, update all links_*.json files in Google Drive
        for json_file in glob('links*.json'):
            upload_or_update(os.path.basename(json_file), os.path.abspath(json_file), folder_id=GDRIVE_FOLDER_ID)
        context.user_data['expecting_post_link'] = False
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=processing_msg.message_id)
        await update.message.reply_text(f'Link posted!')
        return await show_main_menu(update, context)

    if text == 'Post Link':
        processing_msg = await update.message.reply_text('⏳ Processing...')
        context.user_data['expecting_post_link'] = True
        post_msg = (
            "🔗 To post your Opera News link, copy the link from the Opera News app and send it here.\n\n"
            "If you don't know how to get your link, watch this video guide: "
            f"{YOUTUBE_LINK_GUIDE_LINK}"
        )
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=processing_msg.message_id)
        await update.message.reply_text(post_msg, reply_markup=back_keyboard)
        return
    elif text == 'Gain Points':
        # Show rules with inline buttons (no processing message here)
        rules = (
            "Gain Points Rules:\n"
            "1. Visit the provided link.\n"
            "2. Your view will be counted and verified.\n"
            "3. If verified, you will receive points.\n"
            "4. Do not try to cheat, as we check your view count!\n\n"
            "Do you want to continue?"
        )
        keyboard = [
            [InlineKeyboardButton('Yes, continue', callback_data='gain_points_yes')],
            [InlineKeyboardButton('No, back to menu', callback_data='gain_points_no')]
        ]
        await update.message.reply_text(rules, reply_markup=InlineKeyboardMarkup(keyboard))
        return GAIN_POINTS
    elif text == 'Buy Points':
        processing_msg = await update.message.reply_text('⏳ Processing...')
        invoice = get_invoice()
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=processing_msg.message_id)
        await update.message.reply_invoice(**invoice)
        return MAIN_MENU
    elif text == 'Explore YT':
        processing_msg = await update.message.reply_text('⏳ Processing...')
        motivational_msg = (
            "📰 Want to become a better news writer?\n\n"
            "👉 Visit our YouTube channel to learn how to write and publish your own news in seconds, get tips for stress-free writing, and discover secrets every news writer should know!\n"
            "🎥 Click below to explore and grow your skills!"
        )
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=processing_msg.message_id)
        await update.message.reply_text(f"{motivational_msg}\n{YOUTUBE_CHANNEL_LINK}", reply_markup=back_keyboard)
        return MAIN_MENU
    elif text == 'View My Points':
        processing_msg = await update.message.reply_text('⏳ Processing...')
        points = get_points(update.effective_user.id)
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=processing_msg.message_id)
        await update.message.reply_text(f"You have {points or 0:.1f} points.", reply_markup=back_keyboard)
        return MAIN_MENU
    elif text == 'Back to Menu':
        processing_msg = await update.message.reply_text('⏳ Processing...')
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=processing_msg.message_id)
        return await show_main_menu(update, context)
    else:
        processing_msg = await update.message.reply_text('⏳ Processing...')
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=processing_msg.message_id)
        await update.message.reply_text('Please use the menu.', reply_markup=back_keyboard)
        return MAIN_MENU



async def gain_points_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import random
    text = update.message.text.strip()
    if text == 'Back to Menu':
        return await show_main_menu(update, context)
    processing_msg = await update.message.reply_text('⏳ Processing...')
    start = context.user_data.get('timer_start')
    if not start:
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=processing_msg.message_id)
        await update.message.reply_text('No link in progress.')
        return await show_main_menu(update, context)
    link = context.user_data.get('current_link')
    if not link:
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=processing_msg.message_id)
        await update.message.reply_text('No link in progress.')
        return await show_main_menu(update, context)
    # Check time spent
    timer_start = context.user_data.get('timer_start')
    now = datetime.datetime.now()
    elapsed = (now - timer_start).total_seconds()
    required = context.user_data.get('required_seconds')
    if not required:
        required = random.randint(60, 90)
        context.user_data['required_seconds'] = required
    if elapsed >= required:
        add_viewed_link(update.effective_user.id, link.get('id'))
        update_points(update.effective_user.id, 0.1)
        points = get_points(update.effective_user.id)
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=processing_msg.message_id)
        # Clean up any previous link messages
        for msg_id in context.user_data.get('last_link_message_ids', []):
            try:
                await context.bot.delete_message(chat_id=update.message.chat_id, message_id=msg_id)
            except Exception:
                pass
        context.user_data.pop('last_link_message_ids', None)
        await update.message.reply_text(f'✅ Your view has been verified and points have been added! You now have {points:.1f} points.')
        # Prepare for next link
        from link_store import get_next_alternating_link
        viewed = get_viewed_links(update.effective_user.id)
        last_type = context.user_data.get('last_link_type', 'user')
        link_lists = get_next_alternating_link(update.effective_user.id, viewed)
        # Alternate: if last was user, show admin if available, else user; if last was admin, show user if available, else admin
        next_link = None
        if link_lists:
            if last_type == 'user' and link_lists['admin']:
                next_link = link_lists['admin'][0]
                context.user_data['last_link_type'] = 'admin'
            elif last_type == 'admin' and link_lists['user']:
                next_link = link_lists['user'][0]
                context.user_data['last_link_type'] = 'user'
            elif link_lists['admin']:
                next_link = link_lists['admin'][0]
                context.user_data['last_link_type'] = 'admin'
            elif link_lists['user']:
                next_link = link_lists['user'][0]
                context.user_data['last_link_type'] = 'user'
        if next_link:
            context.user_data['current_link'] = next_link
            context.user_data['timer_start'] = datetime.datetime.now()
            keyboard = ReplyKeyboardMarkup([[KeyboardButton("I'm done")],[KeyboardButton('Back to Menu')]], resize_keyboard=True)
            sent_link_msg = await update.message.reply_text(f"Visit this link: {next_link.get('url', 'No link available')}", reply_markup=keyboard)
            sent_info_msg = await update.message.reply_text('When you are done, press "I\'m done".', reply_markup=keyboard)
            context.user_data['last_link_message_ids'] = [sent_link_msg.message_id, sent_info_msg.message_id]
            return GAIN_POINTS
        else:
            # No more links, inform user and clear state, but do NOT force main menu loop
            context.user_data.pop('current_link', None)
            context.user_data.pop('timer_start', None)
            context.user_data.pop('required_seconds', None)
            await update.message.reply_text('🎉 No more links available right now. Returning to manu......', reply_markup=ReplyKeyboardMarkup([[KeyboardButton('Post Link'), KeyboardButton('Gain Points')],[KeyboardButton('Buy Points'), KeyboardButton('Explore YT')],[KeyboardButton('View My Points')]], resize_keyboard=True))
            # Do not return show_main_menu, just return MAIN_MENU so user can choose freely
            return MAIN_MENU
    else:
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=processing_msg.message_id)
        keyboard = ReplyKeyboardMarkup([[KeyboardButton("I'm done")],[KeyboardButton('Back to Menu')]], resize_keyboard=True)
        warn_msg = await update.message.reply_text('⚠️ Please stay on the page for at least 1 minute so your view is counted.', reply_markup=keyboard)
        # Add a split/space for clarity
        split_msg = await update.message.reply_text('------------------------------', reply_markup=keyboard)
        sent_link_msg = await update.message.reply_text(f"Visit this link: {link.get('url', 'No link available')}", reply_markup=keyboard)
        sent_info_msg = await update.message.reply_text('When you are done, press "I\'m done".', reply_markup=keyboard)
        context.user_data['last_link_message_ids'] = [warn_msg.message_id, split_msg.message_id, sent_link_msg.message_id, sent_info_msg.message_id]
        # Now delete the old link messages (after sending new ones)
        for msg_id in context.user_data.get('last_link_message_ids', [])[:-4]:
            try:
                await context.bot.delete_message(chat_id=update.message.chat_id, message_id=msg_id)
            except Exception:
                pass
        return GAIN_POINTS

async def fallback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if user is in a valid menu state or has just lost session
    main_menu_buttons = ['Post Link', 'Gain Points', 'Buy Points', 'Explore YT', 'View My Points', "I'm done", 'Back to Menu']
    user_text = update.message.text if update.message else None
    if user_text and any(btn.lower() in user_text.lower() for btn in main_menu_buttons):
        # If user is pressing a main menu button, show main menu
        await show_main_menu(update, context)
        return
    # Otherwise, session expired or invalid request
    keyboard = ReplyKeyboardMarkup([[KeyboardButton('Gain Points'), KeyboardButton('Post Link')],[KeyboardButton('Buy Points'), KeyboardButton('Explore YT')],[KeyboardButton('View My Points')]], resize_keyboard=True)
    await update.message.reply_text('Session expired or invalid request. Please use the menu below to continue.', reply_markup=keyboard)

async def main():
    init_db()

    # On startup, update all links_*.json and botdata.sqlite3 in Google Drive
    if upload_or_update:
        try:
            for json_file in glob('links*.json'):
                upload_or_update(os.path.basename(json_file), os.path.abspath(json_file), folder_id=GDRIVE_FOLDER_ID)
            if os.path.exists('botdata.sqlite3'):
                upload_or_update('botdata.sqlite3', os.path.abspath('botdata.sqlite3'), folder_id=GDRIVE_FOLDER_ID)
        except Exception as e:
            logging.error(f"Initial Google Drive sync failed: {e}")

    # Start hourly background sync and channel alert
    import threading, time
    def hourly_sync():
        while True:
            time.sleep(3600)  # 1 hour
            if upload_or_update:
                try:
                    for json_file in glob('links*.json'):
                        upload_or_update(os.path.basename(json_file), os.path.abspath(json_file), folder_id=GDRIVE_FOLDER_ID)
                    if os.path.exists('botdata.sqlite3'):
                        upload_or_update('botdata.sqlite3', os.path.abspath('botdata.sqlite3'), folder_id=GDRIVE_FOLDER_ID)
                except Exception as e:
                    logging.error(f"Hourly Google Drive sync failed: {e}")
    def hourly_channel_alert():
        import asyncio as aio
        from telegram.constants import ParseMode
        import random
        # Four rotating messages
        alert_messages = [
            (
                "🚀 <b>Panda Clicker Bot</b> is here to help you grow your Opera News views!\n\n"
                "• <b>Post your links</b> and get real views from others.\n"
                "• <b>Gain points</b> by viewing others' links.\n"
                "• <b>Buy points</b> for even more exposure.\n\n"
                "<a href='https://t.me/{0}'>Click here to start the bot</a> or DM me for help! 🐼"
            ),
            (
                "🐼 <b>Boost your Opera News!</b>\n\n"
                "1. Share your links\n2. Earn points by helping others\n3. Spend points to get more views\n\n"
                "<a href='https://t.me/{0}'>Start Panda Clicker Bot</a> now!"
            ),
            (
                "🔥 <b>Want more views on Opera News?</b>\n\n"
                "Panda Clicker lets you exchange views with real users.\n"
                "Just <a href='https://t.me/{0}'>click here to start</a> and join the fun!"
            ),
            (
                "💡 <b>How Panda Clicker Works:</b>\n\n"
                "- Post your Opera News link\n- View others' links\n- Earn and spend points\n\n"
                "<a href='https://t.me/{0}'>Start the bot now!</a> 🐼"
            )
        ]
        async def send_alert():
            # Get bot username each time to avoid cross-thread async issues
            try:
                bot_me = await app.bot.get_me()
                bot_username = bot_me.username
            except Exception:
                bot_username = "PandaClickerBot"
            msg = random.choice(alert_messages)
            msg = msg.format(bot_username)
            try:
                await app.bot.send_message(
                    chat_id=TELEGRAM_CHANNEL_LINK,
                    text=msg,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
            except Exception as e:
                logging.warning(f"Failed to send channel alert: {e}")
        loop = aio.new_event_loop()
        aio.set_event_loop(loop)
        while True:
            loop.run_until_complete(send_alert())
            time.sleep(3600)
    threading.Thread(target=hourly_sync, daemon=True).start()
    threading.Thread(target=hourly_channel_alert, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    from telegram.ext import PreCheckoutQueryHandler
    # /start command
    app.add_handler(CommandHandler('start', start))
    # Channel join check callback
    app.add_handler(CallbackQueryHandler(check_channel_joined_callback, pattern='check_channel_joined'))
    # Accept rules
    app.add_handler(CallbackQueryHandler(rules_response, pattern='accept_rules_.*'))
    # Screenshot verification
    app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    # Unified handler for all text and button actions
    app.add_handler(MessageHandler(filters.TEXT | filters.Regex(re.compile(r"^I'm done$|^Back to Menu$", re.IGNORECASE)), main_menu_handler))
    app.add_handler(CallbackQueryHandler(gain_points_rules_callback, pattern='gain_points_.*'))
    # Payment handlers
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    # Removed global fallback handler to prevent blocking valid actions
    await app.run_polling()
async def gain_points_rules_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # Delete the rules message before proceeding
    await query.delete_message()
    processing_msg = await query.message.reply_text('⏳ Processing...')
    if query.data == 'gain_points_no':
        try:
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=processing_msg.message_id)
        except Exception:
            pass
        await query.message.reply_text('Returning to menu.')
        return await show_main_menu(update, context)
    elif query.data == 'gain_points_yes':
        user_id = query.from_user.id
        from link_store import get_next_alternating_link
        viewed = get_viewed_links(user_id)
        last_type = context.user_data.get('last_link_type', 'user')
        link_lists = get_next_alternating_link(user_id, viewed)
        try:
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=processing_msg.message_id)
        except Exception:
            pass
        if not link_lists or (not link_lists['admin'] and not link_lists['user']):
            keyboard = ReplyKeyboardMarkup([[KeyboardButton('Back to Menu')]], resize_keyboard=True)
            await query.message.reply_text('😔 There are no links available at the moment. Please try again later!', reply_markup=keyboard)
            return GAIN_POINTS
        if last_type == 'user' and link_lists['admin']:
            link = link_lists['admin'][0]
            context.user_data['last_link_type'] = 'admin'
        elif last_type == 'admin' and link_lists['user']:
            link = link_lists['user'][0]
            context.user_data['last_link_type'] = 'user'
        elif link_lists['admin']:
            link = link_lists['admin'][0]
            context.user_data['last_link_type'] = 'admin'
        elif link_lists['user']:
            link = link_lists['user'][0]
            context.user_data['last_link_type'] = 'user'
        else:
            keyboard = ReplyKeyboardMarkup([[KeyboardButton('Back to Menu')]], resize_keyboard=True)
            await query.message.reply_text('😔 There are no links available at the moment. Please try again later!', reply_markup=keyboard)
            return GAIN_POINTS
        context.user_data['current_link'] = link
        context.user_data['timer_start'] = datetime.datetime.now()
        keyboard = ReplyKeyboardMarkup([[KeyboardButton("I'm done")],[KeyboardButton('Back to Menu')]], resize_keyboard=True)
        sent_link_msg = await query.message.reply_text(f"Visit this link: {link.get('url', 'No link available')}", reply_markup=keyboard)
        sent_info_msg = await query.message.reply_text('When you are done, press "I\'m done".', reply_markup=keyboard)
        context.user_data['last_link_message_ids'] = [sent_link_msg.message_id, sent_info_msg.message_id]
        return GAIN_POINTS

# Add handler for inline Back to Menu button
async def back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_main_menu(update, context)

if __name__ == '__main__':
    import asyncio
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if 'already running' in str(e):
            # For environments like Jupyter or where event loop is running
            import nest_asyncio
            nest_asyncio.apply()
            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
        else:
            raise
