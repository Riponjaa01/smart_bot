from telethon import TelegramClient, events, Button
from datetime import datetime
import asyncio
import random
import math
import requests

# ✅ টেলিগ্রাম সেটআপ
api_id = 14494254
api_hash = '3843d03e08b3c897cf7f14d3e5d2b885'
bot_token = '7867817430:AAGI2FxQtvwtqdlui3jk9ivv5ksITJOm8f8'

client = TelegramClient('signal_bot', api_id, api_hash).start(bot_token=bot_token)

# 📊 ট্রেড পেয়ার লিস্ট
pairs = [
    'EUR/USD', 'GBP/JPY', 'USD/JPY', 'AUD/CAD', 'NZD/CHF',
    'EUR/GBP', 'USD/CAD', 'AUD/JPY', 'NZD/USD', 'CHF/JPY'
]

trades = ['📈 Buy', '📉 Sell']

entry_reasons = [
    "🕔 5m ক্যান্ডেলে বুলিশ পিনবার এবং শক্তিশালী রিভার্সাল দেখা গেছে।",
    "🔟 10m timeframe-এ Breakout-এর পর রিটেস্ট হয়েছে।",
    "🕒 15m ক্যান্ডেলে EMA ও Fibonacci কনফ্লুয়েন্সে রিজেকশন এসেছে।",
    "📐 10m RSI 70 থেকে নিচে নামছে – সম্ভাব্য রিভার্সাল।",
    "📊 15m ক্যান্ডেলে সুস্পষ্ট ট্রেন্ড কনটিনিউয়েশন সিগন্যাল।",
    "🟩 5m Support লেভেল থেকে শার্প বাউন্স।",
    "🟥 15m Bearish Engulfing দেখা গেছে – শক্তিশালী সেল সিগন্যাল।"
]

risk_levels = ['🔒 High Probability Setup', '🟡 Medium Confidence', '⚠️ Aggressive Entry']
strategies = [
    '📊 Price Action (5m)',
    '📐 Fibonacci + EMA (10m)',
    'RSI Divergence (10m)',
    'Breakout Strategy (15m)',
    'Support/Resistance (5m)',
    'Trend Continuation (15m)'
]

user_selected_pairs = {}

# 🟩 Binance থেকে ক্যান্ডেল ডেটা আনা
BINANCE_API = "https://api.binance.com/api/v3/klines"

def get_binance_candles(symbol='EURUSDT', interval='1m', limit=50):
    url = f"{BINANCE_API}?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return [{
                'open': float(c[1]),
                'close': float(c[4]),
                'high': float(c[2]),
                'low': float(c[3])
            } for c in data]
        else:
            return []
    except:
        return []

def analyze_candles_for_signal(candles):
    if not candles or len(candles) < 2:
        return '📉 Sell', 'ডেটা পর্যাপ্ত নয়'
    
    last = candles[-2]
    curr = candles[-1]

    if curr['close'] > curr['open'] and curr['open'] > last['close']:
        return '📈 Buy', 'বর্তমান ক্যান্ডেল শক্তিশালী বুলিশ এবং আগের ক্যান্ডেলের ওপরে ক্লোজ হয়েছে'
    elif curr['close'] < curr['open'] and curr['open'] < last['close']:
        return '📉 Sell', 'বর্তমান ক্যান্ডেল শক্তিশালী বেয়ারিশ এবং আগের ক্যান্ডেলের নিচে ক্লোজ হয়েছে'
    else:
        return random.choice(trades), 'সাধারণ মুভমেন্টের মধ্যে রয়েছে'

def log_user_signal(user_id, message, result=None):
    with open("signal_history.txt", "a", encoding='utf-8') as f:
        f.write(f"\nUSER: {user_id}\n{message}\n🎯 RESULT: {result}\n{'-'*30}\n")

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

@client.on(events.NewMessage(pattern='/getsignal'))
async def start(event):
    user_id = event.sender_id
    user_selected_pairs[user_id] = None
    await event.respond("📊 একটি ট্রেডিং পেয়ার নির্বাচন করুন:", buttons=get_pair_buttons())

@client.on(events.NewMessage(pattern='/stop'))
async def stop_signal(event):
    user_id = event.sender_id
    user_selected_pairs[user_id] = None
    await event.respond("🛑 সিগন্যাল বন্ধ করা হয়েছে। আপনি চাইলে আবার /getsignal দিয়ে শুরু করতে পারেন।")

async def wait_until_next_candle_minus_5s(interval):
    now = datetime.now()
    total_seconds = now.minute * 60 + now.second
    next_candle = math.ceil(total_seconds / interval) * interval
    wait_seconds = next_candle - total_seconds - 5
    if wait_seconds < 0:
        wait_seconds += interval
    print(f"⏱️ পরবর্তী সিগন্যাল আসছে {wait_seconds} সেকেন্ড পর...")
    await asyncio.sleep(wait_seconds)

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
        await event.edit(f"✅ আপনি নির্বাচন করেছেন: **{selected_pair}**\n\n🕒 মার্কেট পর্যবেক্ষণ চলছে...\nপ্রতি ক্যান্ডেল শুরুর ৫ সেকেন্ড আগে সিগন্যাল আসবে।\n\n🛑 বন্ধ করতে `/stop` লিখুন।")

        while user_selected_pairs.get(user_id):
            await wait_until_next_candle_minus_5s(interval=60)

            symbol = selected_pair.replace("/", "") + "T"
            candle_data = get_binance_candles(symbol=symbol, interval="1m", limit=50)
            trade_signal, reason = analyze_candles_for_signal(candle_data)
            now = datetime.now().strftime('%I:%M %p')
            entry_price = candle_data[-1]['close'] if candle_data else 0

            signal_message = f"""🚨 **ট্রেড এনালাইসিস সম্পন্ন হয়েছে** 🚨
💱 **পেয়ার:** {selected_pair}
🔁 **এন্ট্রি টাইপ:** {trade_signal}
🕒 **টাইম:** {now}
🧠 **এন্ট্রি বিশ্লেষণ:**  
{reason}
⏱️ *Trade Time: 1 Minute*
✅ গুড লাক ট্রেডার!
"""

            await client.send_message(user_id, signal_message)
            await asyncio.sleep(60)

            exit_candle = get_binance_candles(symbol=symbol, interval="1m", limit=2)
            exit_price = exit_candle[-1]['close'] if exit_candle else 0

            if trade_signal == '📈 Buy':
                result = "✅ Win" if exit_price > entry_price else "❌ Loss"
            else:
                result = "✅ Win" if exit_price < entry_price else "❌ Loss"

            await client.send_message(user_id, f"🎯 **ট্রেড রেজাল্ট**\nএন্ট্রি: {entry_price}\nএক্সিট: {exit_price}\n📊 ফলাফল: {result}")
            log_user_signal(user_id, signal_message, result)

print("🚀 XQ SIGNAL BOT চালু হয়েছে...")
client.run_until_disconnected()
