from telethon import TelegramClient, events, Button
from datetime import datetime
import asyncio
import random
import json
import websockets
import os

# টেলিগ্রাম সেটআপ
api_id = 14494254
api_hash = '3843d03e08b3c897cf7f14d3e5d2b885'
bot_token = '7867817430:AAGI2FxQtvwtqdlui3jk9ivv5ksITJOm8f8'

client = TelegramClient('signal_bot', api_id, api_hash).start(bot_token=bot_token)

# Deriv API সেটআপ
DERIV_API_TOKEN = 'cHiSjQqoP5GGQl3'  # আপনার Deriv API টোকেন এখানে বসান
DERIV_WS_URL = 'wss://ws.derivws.com/websockets/v3?app_id=1089'

# ট্রেড পেয়ার লিস্ট (Deriv-এর ফরেক্স পেয়ার)
pairs = [
    'EUR/USD', 'GBP/JPY', 'USD/JPY', 'AUD/CAD', 'NZD/CHF',
    'EUR/GBP', 'USD/CAD', 'AUD/JPY', 'NZD/USD', 'CHF/JPY'
]

# Deriv-এর ফরেক্স পেয়ার ম্যাপিং
pair_mapping = {
    'EUR/USD': 'frxEURUSD', 'GBP/JPY': 'frxGBPJPY', 'USD/JPY': 'frxUSDJPY',
    'AUD/CAD': 'frxAUDCAD', 'NZD/CHF': 'frxNZDCHF', 'EUR/GBP': 'frxEURGBP',
    'USD/CAD': 'frxUSDCAD', 'AUD/JPY': 'frxAUDJPY', 'NZD/USD': 'frxNZDUSD',
    'CHF/JPY': 'frxCHFJPY'
}

user_selected_pairs = {}

# Deriv থেকে টিক ডেটা আনা
async def get_deriv_ticks(symbol, count=50):
    async with websockets.connect(DERIV_WS_URL) as ws:
        # API অথেনটিকেশন
        auth_msg = {"authorize": DERIV_API_TOKEN}
        await ws.send(json.dumps(auth_msg))
        auth_response = json.loads(await ws.recv())
        if 'error' in auth_response:
            print("Deriv API Error:", auth_response['error']['message'])
            return None

        # টিক ডেটা রিকোয়েস্ট
        tick_msg = {
            "ticks_history": symbol,
            "end": "latest",
            "count": count,
            "style": "ticks"
        }
        await ws.send(json.dumps(tick_msg))
        tick_response = json.loads(await ws.recv())
        if 'error' in tick_response:
            print("Deriv Tick Error:", tick_response['error']['message'])
            return None

        # টিক প্রাইস সংগ্রহ
        prices = tick_response.get('history', {}).get('prices', [])
        return prices

# SMA গণনা
def calculate_sma(prices, period):
    if len(prices) < period:
        return [0] * len(prices)
    sma = []
    for i in range(len(prices)):
        if i < period - 1:
            sma.append(0)
        else:
            sma.append(sum(prices[i-period+1:i+1]) / period)
    return sma

# SMA ক্রসওভার বিশ্লেষণ
def analyze_candles_for_signal(prices):
    if not prices:
        return random.choice(['📈 Call', '📉 Put']), "ডেটা পাওয়া যায়নি, র‍্যান্ডম সিগন্যাল।"

    # SMA গণনা
    sma5 = calculate_sma(prices, 5)
    sma20 = calculate_sma(prices, 20)

    last_sma5 = sma5[-1] if len(sma5) > 0 else 0
    last_sma20 = sma20[-1] if len(sma20) > 0 else 0
    prev_sma5 = sma5[-2] if len(sma5) > 1 else 0
    prev_sma20 = sma20[-2] if len(sma20) > 1 else 0

    signal = None
    reason = ""

    # SMA ক্রসওভার
    if prev_sma5 < prev_sma20 and last_sma5 > last_sma20:
        signal = "📈 Call"
        reason += "SMA5 ক্রস করে SMA20 উপরে উঠেছে। "
    elif prev_sma5 > prev_sma20 and last_sma5 < last_sma20:
        signal = "📉 Put"
        reason += "SMA5 নিচে ক্রস করেছে SMA20। "

    if not signal:
        signal = random.choice(['📈 Call', '📉 Put'])
        reason = "স্পষ্ট ট্রেন্ড না থাকার কারণে র‍্যান্ডম সিগন্যাল।"

    return signal, reason

# ইউজার সিগন্যাল লগ
def log_user_signal(user_id, signal_text, result_text=None):
    folder = "user_logs"
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, f"{user_id}.txt")
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} - সিগন্যাল:\n{signal_text}\n")
        if result_text:
            f.write(f"{datetime.now()} - ফলাফল:\n{result_text}\n\n")

# পেয়ার বাটন তৈরি
def get_pair_buttons():
    button_list = []
    for i in range(0, len(pairs), 2):
        row = []
        for j in range(2):
            if i + j < len(pairs):
                row.append(Button.inline(pairs[i + j], f"PAIR_{pairs[i + j]}".encode()))
        button_list.append(row)
    button_list.append([Button.inline("🎲 Random Pair", b"PAIR_RANDOM")])
    return button_list

# দ্রুত সিগন্যাল অপেক্ষা ফাংশন
async def quick_signal_wait():
    wait_seconds = random.uniform(2, 10)
    print(f"⏱️ সিগন্যাল আসছে {wait_seconds:.2f} সেকেন্ড পর...")
    await asyncio.sleep(wait_seconds)

# সিগন্যাল ফলাফল বিশ্লেষণ (Deriv API দিয়ে)
async def analyze_signal_result(symbol, entry_price, trade_type, duration=60):
    async with websockets.connect(DERIV_WS_URL) as ws:
        # অথেনটিকেশন
        auth_msg = {"authorize": DERIV_API_TOKEN}
        await ws.send(json.dumps(auth_msg))
        await ws.recv()

        # সর্বশেষ প্রাইস পাওয়ার জন্য টিক সাবস্ক্রিপশন
        tick_msg = {"ticks": symbol, "subscribe": 1}
        await ws.send(json.dumps(tick_msg))

        # ৬০ সেকেন্ড অপেক্ষা
        start_time = asyncio.get_event_loop().time()
        latest_price = entry_price
        while asyncio.get_event_loop().time() - start_time < duration:
            response = json.loads(await ws.recv())
            if 'tick' in response:
                latest_price = response['tick']['quote']
            await asyncio.sleep(1)

        # টিক সাবস্ক্রিপশন বন্ধ
        unsubscribe_msg = {"forget": response.get('subscription', {}).get('id', '')}
        await ws.send(json.dumps(unsubscribe_msg))

        close_price = latest_price

        if trade_type == "📈 Call":
            if close_price > entry_price:
                result = "✅ লাভ"
                profit = close_price - entry_price
            else:
                result = "❌ লস"
                profit = close_price - entry_price
        elif trade_type == "📉 Put":
            if close_price < entry_price:
                result = "✅ লাভ"
                profit = entry_price - close_price
            else:
                result = "❌ লস"
                profit = entry_price - close_price

        result_message = f"📊 **ট্রেড ফলাফল** 📊\n\n💱 পেয়ার: {symbol.replace('frx', '')}\n🔁 এন্ট্রি টাইপ: {trade_type}\n💵 এন্ট্রি প্রাইস: {entry_price}\n💸 ক্লোজ প্রাইস: {close_price}\n📈 ফলাফল: {result}\n💰 পিপস: {profit:.4f}"
        return result_message, result

# /getsignal কমান্ড
@client.on(events.NewMessage(pattern='/getsignal'))
async def start(event):
    user_id = event.sender_id
    user_selected_pairs[user_id] = None
    await event.respond("📊 একটি ট্রেডিং পেয়ার নির্বাচন করুন:", buttons=get_pair_buttons())

# বাটন প্রেস হ্যান্ডলার
@client.on(events.CallbackQuery)
async def callback_handler(event):
    user_id = event.sender_id
    data = event.data.decode("utf-8")

    if data.startswith("PAIR_"):
        if data == "PAIR_RANDOM":
            selected_pair = random.choice(pairs)
        else:
            selected_pair = data.replace("PAIR_", "")
        user_selected_pairs[user_id] = selected_pair
        
        await event.edit(f"✅ আপনি নির্বাচন করেছেন: **{selected_pair}**\n\n🕒 মার্কেট পর্যবেক্ষণ চলছে...")
        await event.respond("⏳ দয়া করে একটু অপেক্ষা করুন, আপনাকে কিছুক্ষণের মধ্যেই সিগন্যাল দেওয়া হবে।")

        await quick_signal_wait()

        symbol = pair_mapping.get(selected_pair, 'frxEURUSD')
        tick_data = await get_deriv_ticks(symbol, count=50)

        trade_signal, reason = analyze_candles_for_signal(tick_data)

        entry_price = tick_data[-1] if tick_data else None

        now = datetime.now().strftime('%I:%M %p')

        signal_message = f"""🚨 **ট্রেড এনালাইসিস সম্পন্ন হয়েছে** 🚨

💱 পেয়ার: {selected_pair}
🔁 এন্ট্রি টাইপ: {trade_signal}
🕒 টাইম: {now}
🧠 এন্ট্রি বিশ্লেষণ:
{reason}
⏱️ Trade Time: 1 Minute
✅ গুড লাক ট্রেডার!
"""

        log_user_signal(user_id, signal_message)
        await event.respond(signal_message)

        if entry_price:
            result_message, result = await analyze_signal_result(symbol, entry_price, trade_signal)
            log_user_signal(user_id, signal_message, result_message)
            await event.respond(result_message)

# /history কমান্ড
@client.on(events.NewMessage(pattern='/history'))
async def show_history(event):
    user_id = event.sender_id
    filepath = os.path.join("user_logs", f"{user_id}.txt")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            history = f.read()
        await event.respond(f"📜 **আপনার ট্রেড হিস্ট্রি**:\n\n{history}")
    else:
        await event.respond("⚠️ কোনো হিস্ট্রি পাওয়া যায়নি।")

# বট চালু
print("🚀 XQ SIGNAL BOT চালু হয়েছে...")
client.run_until_disconnected()
