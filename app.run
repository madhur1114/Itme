import os
import asyncio
from flask import Flask, render_template, request, jsonify
from telegram import Bot

app = Flask(__name__)

# Telegram Configuration (Render Environment Variables se uthayega ya aap yahan direct daal sakte hain)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "
8670491836:AAGY2DH4cXy8kwFTYRDILhaL6RCOddR3VKE")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "@wingomanlottery")

# In-Memory Database for Users & Status
users_db = {
    "GAMEGURUAI145": {"password": "GAMEGURUAI145", "status": "approved", "is_admin": True}
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
            status = users_db[username]["status"]
            return jsonify({"success": True, "isAdmin": False, "status": status})
        else:
            return jsonify({"success": False, "message": "Incorrect password"})
    else:
        # Auto-register new user as pending
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
    status = data.get('status') # 'approved' or 'pending'
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
    
    # Send Telegram Message / Sticker async
    if TELEGRAM_BOT_TOKEN != "YOUR_BOT_TOKEN_HERE":
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(send_telegram_update(win, period, stats))
        except Exception as e:
            print("Telegram notification error:", e)
            
    return jsonify({"success": True})

async def send_telegram_update(win, period, stats):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    if win:
        # Win hone par sticker bhejein (Aap apne pasand ka sticker file_id ya emoji use kar sakte hain)
        await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text="🎉 CONGRATULATIONS! PREDICTION WIN! 🚀")
        # Win streak aur details
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

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
