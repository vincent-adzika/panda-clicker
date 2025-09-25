from db import update_points
from telegram.ext import ContextTypes

async def precheckout_callback(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment(update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    payment = update.message.successful_payment
    total_amount = payment.total_amount  # in the smallest currency unit (stars)
    from payment_utils import POINTS_PRICE_PER_UNIT
    points_to_add = total_amount // POINTS_PRICE_PER_UNIT
    update_points(user.id, points_to_add)
    await update.message.reply_text(f"Payment successful! {points_to_add} point(s) have been added to your account.")
    from bot import show_main_menu
    await show_main_menu(update, context)
from telegram import LabeledPrice

POINTS_PRICE_PER_UNIT = 1  # 10 stars per 1 point
PAYMENT_TITLE = "Buy Points"
PAYMENT_DESCRIPTION = "Purchase points to use in the bot."
PAYMENT_CURRENCY = "XTR"  # Telegram Stars currency

prices = [LabeledPrice(label="1 Point", amount=POINTS_PRICE_PER_UNIT)]

def get_invoice():
    return {
        "title": PAYMENT_TITLE,
        "description": PAYMENT_DESCRIPTION,
        "payload": "buy_points_payload",
        "provider_token": None,  # None for Stars
        "currency": PAYMENT_CURRENCY,
        "prices": prices,
        "need_name": False,
        "need_phone_number": False,
        "need_email": False,
        "need_shipping_address": False,
        "is_flexible": False
    }
