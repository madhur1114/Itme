import os
import time
import threading
import requests
from flask import Flask, render_template, request, jsonify
from telegram import Bot

app = Flask(__name__)

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "@YOUR_CHANNEL_USERNAME")
# Aap jo sticker Telegram par upload karenge, uska file_id yahan daal sakte hain:
CUSTOM_STICKER_FILE_ID = os.environ.get("STICKER_FILE_ID", "YOUR_STICKER_FILE_ID_HERE")

# In-Memory Database for Users & Status
users_db = {
    "GAMEGURUAI145": {"password": "GAMEGURUAI145", "status": "approved", "is_admin": True}
}

# Bot stats & memory for 24/7 background running
bot_stats = {
    "wins": 0,
    "losses": 0,
    "consecutiveWin": 0,
    "consecutiveLoss": 0,
    "highestWinStreak": 0,
    "highestLossStreak": 0,
    "totalBets": 0
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({"success": False, "message": "Username and password required"})
    
    if username == "GAMEGURUAI145":
        return jsonify({"success": True, "isAdmin": True, "status": "approved"})
    
    if username in users_db:
        if users_db[username]["password"] == password:
            return jsonify({"success": True, "isAdmin": False, "status": users_db[username]["status"]})
        else:
            return jsonify({"success": False, "message": "Incorrect password"})
    else:
        users_db[username] = {"password": password, "status": "pending", "is_admin": False}
        return jsonify({"success": True, "isAdmin": False, "status": "pending"})

@app.route('/api/admin/users', methods=['GET'])
def admin_users():
    u_list = [{"username": uname, "status": info["status"]} for uname, info in users_db.items() if not info.get("is_admin")]
    return jsonify({"users": u_list})

@app.route('/api/admin/update_user', methods=['POST'])
def admin_update_user():
    data = request.json or {}
    username = data.get('username')
    status = data.get('status')
    if username in users_db:
        users_db[username]["status"] = status
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "User not found"})

@app.route('/api/notify_telegram', methods=['POST'])
def notify_telegram():
    data = request.json or {}
    win = data.get('win', False)
    period = data.get('period', '')
    stats = data.get('stats', {})
    
    # Update global stats
    global bot_stats
    bot_stats.update(stats)
    
    if TELEGRAM_BOT_TOKEN != "YOUR_BOT_TOKEN_HERE":
        try:
            threading.Thread(target=send_telegram_sync, args=(win, period, bot_stats)).start()
        except Exception as e:
            print("Telegram error:", e)
            
    return jsonify({"success": True})

def send_telegram_sync(win, period, stats):
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(send_telegram_update_async(win, period, stats))

async def send_telegram_update_async(win, period, stats):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        if win:
            # Win hone par aapka custom sticker bhejein agar available ho
            if CUSTOM_STICKER_FILE_ID != "YOUR_STICKER_FILE_ID_HERE":
                try:
                    await bot.send_sticker(chat_id=TELEGRAM_CHANNEL_ID, sticker=CUSTOM_STICKER_FILE_ID)
                except Exception as e:
                    print("Sticker send error:", e)
            
            await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text="🎉 CONGRATULATIONS! PREDICTION WIN! 🚀")
            msg = (
                f"✅ *PERIOD {period} WIN*\n\n"
                f"🔥 *Win Streak*: {stats.get('consecutiveWin', 0)}\n"
                f"❄️ *Loss Streak*: {stats.get('consecutiveLoss', 0)}\n"
                f"🏆 *Highest Win Streak*: {stats.get('highestWinStreak', 0)}\n"
                f"📉 *Highest Loss Streak*: {stats.get('highestLossStreak', 0)}\n"
                f"📊 *Accuracy*: {stats.get('accuracy', 0)}%"
            )
            await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=msg, parse_mode="Markdown")
        else:
            msg = (
                f"❌ *PERIOD {period} LOSS*\n\n"
                f"🔥 *Win Streak*: {stats.get('consecutiveWin', 0)}\n"
                f"❄️ *Loss Streak*: {stats.get('consecutiveLoss', 0)}\n"
                f"🏆 *Highest Win Streak*: {stats.get('highestWinStreak', 0)}\n"
                f"📉 *Highest Loss Streak*: {stats.get('highestLossStreak', 0)}"
            )
            await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=msg, parse_mode="Markdown")
    except Exception as e:
        print("Telegram broadcast error:", e)

# 24/7 Background Daemon to keep service awake and process periodic checks
def background_worker():
    while True:
        try:
            # Yahan background ping ya lottery API check ho sakti hai taaki 24/7 active rahe
            requests.get("https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json", timeout=10)
        except Exception:
            pass
        time.sleep(60)

if __name__ == '__main__':
    # Start background worker thread for 24/7 uptime
    t = threading.Thread(target=background_worker, daemon=True)
    t.start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
