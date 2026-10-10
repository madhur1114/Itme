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
CUSTOM_STICKER_FILE_ID = os.environ.get("STICKER_FILE_ID", "YOUR_STICKER_FILE_ID_HERE")

# In-Memory Database for Users & Status
users_db = {
    "GAMEGURUAI145": {"password": "GAMEGURUAI145", "status": "approved", "is_admin": True}
}

# Stats tracking for streaks
bot_stats = {
    "wins": 0, "losses": 0,
    "consecutiveWin": 0, "consecutiveLoss": 0,
    "highestWinStreak": 0, "highestLossStreak": 0,
    "totalBets": 0
}

def to_bold(text):
    map_chars = {
        'A':'𝗔','B':'𝗕','C':'𝗖','D':'𝗗','E':'𝗘','F':'𝗙','G':'𝗚','H':'𝗛','I':'𝗜','J':'𝗝','K':'𝗞','L':'𝗟','M':'𝗠',
        'N':'𝗡','O':'𝗢','P':'𝗣','Q':'𝗤','R':'𝗥','S':'𝗦','T':'𝗧','U':'𝗨','V':'𝗩','W':'𝗪','X':'𝗫','Y':'𝗬','Z':'𝗭',
        'a':'𝗮','b':'𝗯','c':'𝗰','d':'𝗱','e':'𝗲','f':'𝗳','g':'𝗴','h':'𝗵','i':'𝗶','j':'𝗷','k':'𝗸','l':'𝗹','m':'𝗺',
        'n':'𝗻','o':'𝗼','p':'𝗽','q':'𝗾','r':'𝗿','s':'𝘀','t':'𝘁','u':'𝘂','v':'𝘃','w':'𝘄','x':'𝘅','y':'𝘆','z':'𝘇',
        '0':'𝟬','1':'𝟭','2':'𝟮','3':'𝟯','4':'𝟰','5':'𝟱','6':'𝟲','7':'𝟳','8':'𝟴','9':'𝟵'
    }
    return ''.join(map_chars.get(ch, ch) for ch in str(text))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
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

# 24/7 Automatic Background Prediction & Telegram Poster
def automated_bot_worker():
    last_processed_issue = ""
    while True:
        try:
            # Fetch latest lottery history from API
            res = requests.get("https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json?ts=" + str(time.time()), timeout=10)
            data = res.json()
            list_items = data.get('data', {}).get('list', [])
            
            if list_items:
                latest = list_items[0]
                current_issue = str(latest.get('issueNumber') or latest.get('issue') or latest.get('periodNumber'))
                
                if current_issue != last_processed_issue:
                    last_processed_issue = current_issue
                    next_issue = str(int(current_issue) + 1)
                    
                    # Simple robust prediction logic matching core engines
                    numbers = [int(item.get('number', 0)) for item in list_items[:10]]
                    n1 = numbers[0] if numbers else 8
                    n2 = numbers[1] if len(numbers) > 1 else 9
                    size = "BIG" if n1 >= 5 else "SMALL"
                    
                    # Format message exactly as requested
                    b = to_bold
                    short_issue = next_issue[-5:]
                    msg = (
                        f"••••••••••••••••••••••••••••••••••••\n"
                        f"🎮 {b('BY GAMEGURU.AI')} PRO MAX\n"
                        f"      ———————————--------\n"
                        f"{b('ISSUE')}  ➜ {b(short_issue)}\n"
                        f" {b('TARGET')} ➜  {b(size)}\n"
                        f"{b('NUMBERS')} ➜ {b(str(n1))} , {b(str(n2))}\n"
                        f"{b('BALLS')} ➜ {b(str(n1))}‚ {b(str(n2))}‚ {b('9')}‚ {b('7')}\n"
                        f"{b('SERVER')} ➜ {b('HYBRID')}\n"
                        f"{b('CONF')} ➜ {b('82%')}\n"
                        f"      ———————————---------\n"
                        f"🔥 {b('GIVE REACTION FOR MORE WINNING')}\n"
                        f"{b('OWNER')}:-@wingoman_chat_support_bot\n"
                        f"•••••••••••••••••••••••••••••••••••••"
                    )
                    
                    # Send to Telegram Channel via sync wrapper
                    if TELEGRAM_BOT_TOKEN != "YOUR_BOT_TOKEN_HERE":
                        send_telegram_message_sync(msg)
        except Exception as e:
            print("Background worker error:", e)
        
        time.sleep(30) # Check every 30 seconds

def send_telegram_message_sync(text):
    import asyncio
    async def send():
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        try:
            if CUSTOM_STICKER_FILE_ID != "YOUR_STICKER_FILE_ID_HERE":
                await bot.send_sticker(chat_id=TELEGRAM_CHANNEL_ID, sticker=CUSTOM_STICKER_FILE_ID)
            await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=text, parse_mode="Markdown")
        except Exception as e:
            print("Telegram send error:", e)
            
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(send())

if __name__ == '__main__':
    # Start 24/7 Automated Background Bot Worker Thread
    t = threading.Thread(target=automated_bot_worker, daemon=True)
    t.start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
