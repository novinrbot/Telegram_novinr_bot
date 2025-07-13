# Telegram_novinr_bot
import logging
import requests
import nest_asyncio
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
    ConversationHandler
)

# -------- تنظیمات --------
ADMIN_ID = 7261552302  # شناسه عددی ادمین
ADMIN_FIRST_NAME = "خلیج همیشه فارس"
ZARINPAL_MERCHANT = "MERCHANT-ID-HERE"  # اگر داری عوض کن
IDPAY_API_KEY = "YOUR-IDPAY-API-KEY"    # اگر داری عوض کن
CALLBACK_URL = "https://example.com/callback"  # اگه آدرس درست داری بزار

BOT_TOKEN = "7276288343:AAG9HxyhyxlPw-a8RRaoQqDe0aezwHgRmbA"

# -------- ذخیره‌سازی --------
products = {}
cart = {}
edit_id = None

# -------- استارت --------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"به ربات فروشگاه خوش آمدید {ADMIN_FIRST_NAME}! از /shop برای مشاهده محصولات استفاده کنید.")

# -------- افزودن محصول (ادمین) --------
ADD_NAME, ADD_PRICE, ADD_DESC = range(3)

async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("نام محصول را وارد کنید:")
    return ADD_NAME

async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("قیمت محصول را وارد کنید:")
    return ADD_PRICE

async def add_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['price'] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("لطفاً عدد صحیح وارد کنید.")
        return ADD_PRICE
    await update.message.reply_text("توضیحات محصول را وارد کنید:")
    return ADD_DESC

async def add_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['desc'] = update.message.text
    pid = str(len(products) + 1)
    products[pid] = context.user_data.copy()
    await update.message.reply_text("✅ محصول با موفقیت افزوده شد.")
    return ConversationHandler.END

# -------- مشاهده محصولات --------
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not products:
        await update.message.reply_text("هیچ محصولی وجود ندارد.")
        return

    keyboard = []
    for pid, product in products.items():
        name = product.get("name")
        price = product.get("price")
        qty = cart.get(pid, 0)
        keyboard.append([
            InlineKeyboardButton(f"🛒 {name} - {price} تومان", callback_data=f"buy_{pid}"),
            InlineKeyboardButton(f"❌ حذف", callback_data=f"remove_{pid}"),
            InlineKeyboardButton(f"تعداد: {qty}", callback_data="ignore")
        ])
    await update.message.reply_text("🛍 لیست محصولات:", reply_markup=InlineKeyboardMarkup(keyboard))

# -------- افزودن به سبد خرید --------
async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = update.callback_query.data.split('_')[1]
    cart[pid] = cart.get(pid, 0) + 1
    await update.callback_query.answer("به سبد خرید افزوده شد")

# -------- حذف از سبد خرید --------
async def remove_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = update.callback_query.data.split('_')[1]
    if pid in cart:
        del cart[pid]
    await update.callback_query.answer("از سبد خرید حذف شد")

# -------- درگاه پرداخت --------
async def start_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = sum(products[pid]["price"] * qty for pid, qty in cart.items())
    if total == 0:
        await update.message.reply_text("سبد خرید خالی است.")
        return
    keyboard = [[
        InlineKeyboardButton("💳 پرداخت با زرین‌پال", callback_data="pay_zarinpal")
    ], [
        InlineKeyboardButton("💳 پرداخت با IDPay", callback_data="pay_idpay")
    ]]
    await update.message.reply_text(f"مبلغ قابل پرداخت: {total} تومان", reply_markup=InlineKeyboardMarkup(keyboard))
    async def pay_zarinpal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = sum(products[pid]["price"] * qty for pid, qty in cart.items())
    data = {
        "merchant_id": ZARINPAL_MERCHANT,
        "amount": total,
        "callback_url": CALLBACK_URL,
        "description": "خرید از ربات"
    }
    res = requests.post("https://api.zarinpal.com/pg/v4/payment/request.json", json=data).json()
    if res.get("data", {}).get("code") == 100:
        link = f"https://www.zarinpal.com/pg/StartPay/{res['data']['authority']}"
        await update.callback_query.message.reply_text(f"پرداخت: {link}")
    else:
        await update.callback_query.message.reply_text("خطا در اتصال به زرین‌پال.")

async def pay_idpay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = sum(products[pid]["price"] * qty for pid, qty in cart.items())
    data = {
        "order_id": str(update.effective_user.id),
        "amount": total,
        "name": update.effective_user.full_name,
        "callback": CALLBACK_URL
    }
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": IDPAY_API_KEY,
        "X-SANDBOX": "1"
    }
    res = requests.post("https://api.idpay.ir/v1.1/payment", json=data, headers=headers).json()
    if "link" in res:
        await update.callback_query.message.reply_text(f"پرداخت: {res['link']}")
    else:
        await update.callback_query.message.reply_text("خطا در اتصال به IDPay")

# -------- اجرای ربات --------
async def main():
    logging.basicConfig(level=logging.INFO)
    nest_asyncio.apply()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CommandHandler("pay", start_payment))

    app.add_handler(CallbackQueryHandler(buy_callback, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(remove_callback, pattern="^remove_"))
    app.add_handler(CallbackQueryHandler(pay_zarinpal, pattern="^pay_zarinpal"))
    app.add_handler(CallbackQueryHandler(pay_idpay, pattern="^pay_idpay"))

    conv_add = ConversationHandler(
        entry_points=[CommandHandler("add", add_product)],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            ADD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_price)],
            ADD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_desc)],
        },
        fallbacks=[]
    )
    app.add_handler(conv_add)

    print("ربات با موفقیت اجرا شد ✅")
    await app.run_polling()

if name == 'main':
    asyncio.run(main())
