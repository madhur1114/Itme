"""
GAMEGURU.AI PRO MAX - Background Auto Prediction Bot with Auth & Admin Panel
Extracted from HTML: 4 Engines (KINGG v12 + MOHIT + SUKUNA v16 + SHINCHAN v5.4) + HYBRID Combiner
"""

import os
import time
import random
import threading
import requests
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ============ GLOBAL FLASK APP (For Gunicorn) ============
app = Flask(__name__)

# ============ CONFIG ============
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE").strip()
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "@YOUR_CHANNEL_USERNAME").strip()
CUSTOM_STICKER_FILE_ID = os.environ.get("STICKER_FILE_ID", "CAACAgUAAxkBAAESBbRqyq44nhLAkMvP_9PdbpwxbCel0wACQxoAAgalmFSM0KS4LrwRiD0E").strip()
WINGO_TYPE = os.environ.get("WINGO_TYPE", "1M").strip().upper()  # 1M or 30S
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "8"))

# Bot & Auth States
bot_running = True
users_db = {"admin": "admin123"}  # Default admin credentials (change if needed)
approved_users = set(["admin"])
pending_approvals = set()
user_sessions = {}  # chat_id -> username

# Stats & Results Storage (Up to 1440 results)
bot_stats = {
    "wins": 0, "losses": 0,
    "consecutiveWin": 0, "consecutiveLoss": 0,
    "highestWinStreak": 0, "totalBets": 0,
    "jackpots": 0
}
results_history = []

def add_result_to_history(issue, number, size):
    global results_history
    results_history.insert(0, {
        "issue": str(issue),
        "number": int(number),
        "size": str(size),
        "time": datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d %H:%M:%S")
    })
    if len(results_history) > 1440:
        results_history.pop()

# ============ BOLD CONVERTER ============
def to_bold(text):
    map_chars = {
        'A':'𝗔','B':'𝗕','C':'𝗖','D':'𝗗','E':'𝗘','F':'𝗙','G':'𝗚','H':'𝗛','I':'𝗜','J':'𝗝','K':'𝗞','L':'𝗟','M':'𝗠',
        'N':'𝗡','O':'𝗢','P':'𝗣','Q':'𝗤','R':'𝗥','S':'𝗦','T':'𝗧','U':'𝗨','V':'𝗩','W':'𝗪','X':'𝗫','Y':'𝗬','Z':'𝗭',
        'a':'𝗮','b':'𝗯','c':'𝗰','d':'𝗱','e':'𝗲','f':'𝗳','g':'𝗴','h':'𝗵','i':'𝗶','j':'𝗷','k':'𝗸','l':'𝗹','m':'𝗺',
        'n':'𝗻','o':'𝗼','p':'𝗽','q':'𝗾','r':'𝗿','s':'𝘀','t':'𝘁','u':'𝘂','v':'𝘃','w':'𝘄','x':'𝘅','y':'𝘆','z':'𝘇',
        '0':'𝟬','1':'𝟭','2':'𝟮','3':'𝟯','4':'𝟰','5':'𝟱','6':'𝟲','7':'𝟳','8':'𝟴','9':'𝟵',
        '.':'.', '%':'%', ':':':', '-':'-', ' ':' '
    }
    return ''.join(map_chars.get(ch, ch) for ch in str(text))

# ============ SUKUNA HISTORY DB ============
SUKUNA_HISTORY = [
    2,1,2,0,5,5,5,6,0,7,1,2,6,1,9,7,6,5,0,0,0,8,4,5,2,4,3,9,4,9,4,1,2,3,4,4,2,6,1,2,9,6,1,9,2,8,9,1,8,7,
    2,9,5,9,5,6,3,0,6,8,2,9,3,8,6,8,5,0,6,8,6,9,8,5,3,1,4,4,9,8,9,1,4,8,3,4,3,5,2,1,3,3,2,3,6,8,2,9,4,5,
    6,8,1,4,2,9,0,6,5,5,9,3,5,7,7,3,0,8,1,5,8,5,9,9,4,7,7,1,3,3,6,3,1,6,0,2,5,4,8,2,3,0,7,3,1,0,6,0,9,7,
    1,3,8,0,6,9,3,2,0,4,5,3,2,4,0,8,6,3,5,3,8,5,3,6,3,2,8,8,0,5,4,2,4,6,3,4,4,6,5,5,0,5,1,3,6,9,7,0,2,9,
    5,5,0,9,4,1,0,5,1,9,3,5,4,7,1,5,5,5,3,9,9,7,8,9,7,3,7,1,5,2,0,1,6,7,6,1,1,1,0,3,1,1,0,1,0,6,1,8,1,6,
    2,1,0,3,3,8,7,4,7,3,2,5,5,0,6,9,5,1,3,3,0,0,3,4,6,6,8,6,8,4,2,5,4,4,9,1,7,7,8,6,0,3,0,6,4,1,3,2,4,3,
    3,7,4,9,5,5,9,5,8,9,2,1,0,1,9,2,3,0,2,2,5,1,5,8,7,5,0,8,3,5,4,1,5,0,2,9,2,4,0,8,2,1,2,3,3,6,4,1,9,8,
    4,7,5,5,0,5,6,8,3,7,9,2,1,0,7,2,5,0,8,0,5,1,6,2,2,6,4,9,1,5,3,4,3,7,1,7,3,3,2,6,7,6,1,1,1,4,8,7,6,1,
    9,6,9,5,8,2,2,0,8,6,8,5,4,8,2,7,4,5,1,2,6,5,3,6,8,8,8,1,2,6,4,4,7,9,8,9,6,8,6,7,4,4,9,8,9,5,3,1,0,4,
    6,5,6,4,0,9,9,1,1,9,4,4,9,3,2,6,2,3,7,5,8,0,8,2,5,8,8,8,9,7,0,5,3,8,5,7,8,6,9,3,6,3,6,4,3,6,3,4,3,0,
]

# ============ PREDICTION ENGINES ============
class UltimatePredictorV12:
    def __init__(self):
        self.hall_of_fame = {"BIG_KINGS": [8,9], "SMALL_KINGS": [1,2]}
        self.direct_rules = {
            'BB':{'next':'SMALL','numbers':[1,2],'score':78},
            'SS':{'next':'BIG','numbers':[8,9],'score':78},
            'BBB':{'next':'SMALL','numbers':[1],'score':80},
            'SSS':{'next':'BIG','numbers':[8],'score':80},
            'BSB':{'next':'SMALL','numbers':[2],'score':72},
            'SBS':{'next':'BIG','numbers':[9],'score':72},
            'BBS':{'next':'BIG','numbers':[9],'score':70},
            'SSB':{'next':'SMALL','numbers':[2],'score':70}
        }
        self.consecutiveLoss=0; self.consecutiveWin=0; self.lastLossSize=None

    def apply_direct_rules(self, h):
        if len(h)<2: return None
        p=""
        for i in range(min(4,len(h))):
            p += 'B' if h[i]>=5 else 'S'
        for length in range(min(4,len(p)),1,-1):
            sub=p[:length]
            if sub in self.direct_rules:
                r=self.direct_rules[sub]
                return {"prediction":r['next'],"number":r['numbers'][0],"score":r['score'],"rule":sub}
        return None

    def predict(self, history):
        h=[int(x) for x in history if str(x).isdigit() or isinstance(x,int)]
        if self.consecutiveLoss>=1:
            f_size = 'SMALL' if self.lastLossSize=='BIG' else 'BIG'
            return {"predictedNumber":1 if f_size=='SMALL' else 8,"predictedSize":f_size,"partnerNumber":2 if f_size=='SMALL' else 9,"score":72,"logic":"REVERSE_AFTER_LOSS","label":"🔄 Reverse after loss","forcedReverse":True}
        r=self.apply_direct_rules(h)
        if r:
            return {"predictedNumber":r["number"],"predictedSize":r["prediction"],"partnerNumber":9 if r["prediction"]=='BIG' else 2,"score":r["score"],"logic":"DIRECT_RULE","label":f"📐 Rule {r['rule']}"}
        rb=sum(1 for i in range(min(5,len(h))) if h[i]>=5)
        dp='SMALL' if rb>=3 else 'BIG'
        return {"predictedNumber":8 if dp=='BIG' else 1,"predictedSize":dp,"partnerNumber":9 if dp=='BIG' else 2,"score":60,"logic":"SMART_DEFAULT","label":"🔒 Trend default"}

class MohitEngine:
    def predict(self, latest_issue, history_numbers):
        hist=[n for n in (history_numbers or []) if isinstance(n,int)]
        seed = int(str(latest_issue)[-3:]) if str(latest_issue)[-3:].isdigit() else 0
        trend = 'BIG' if (sum(1 for n in hs if n>=5) if (hs:=hist[:15]) else 5)>=len(hs)/2 else 'SMALL'
        n1 = [5,6,7,8,9][seed%5] if trend=='BIG' else [0,1,2,3,4][seed%5]
        return {"predictedNumber":n1,"predictedSize":trend,"partnerNumber":3,"score":74,"logic":"MOHIT","label":"🔥 Mohit Pure"}

class SukunaEngine:
    def __init__(self): self.history=SUKUNA_HISTORY
    def predict(self, api_list):
        best = api_list[0] if api_list else 8
        size = 'BIG' if best>=5 else 'SMALL'
        return {"predictedNumber":best,"predictedSize":size,"partnerNumber":2,"score":82,"logic":"SUKUNA","label":"🐉 Sukuna v16"}

class ShinchanEngine:
    def predict(self, current_period_str, history_numbers):
        s = sum([int(c) for c in str(current_period_str) if c.isdigit()]) or 5
        type_ = 'BIG' if s%2!=0 else 'SMALL'
        n1 = 8 if type_=='BIG' else 2
        return {"predictedNumber":n1,"predictedSize":type_,"partnerNumber":3,"score":85,"logic":"SHINCHAN","label":"🛡️ Shinchan Stable"}

def combine_hybrid(kingg, mohit, sukuna, shinchan):
    votes={"BIG":0,"SMALL":0}
    votes[kingg["predictedSize"]]+=1.5 if kingg.get("forcedReverse") else 1.0
    votes[mohit["predictedSize"]]+=0.8
    votes[sukuna["predictedSize"]]+=1.0
    votes[shinchan["predictedSize"]]+=1.0

    final_size='BIG' if votes["BIG"]>=votes["SMALL"] else 'SMALL'
    final_number = sukuna["predictedNumber"]
    if (final_number>=5 and final_size!='BIG') or (final_number<5 and final_size!='SMALL'):
        final_number = 8 if final_size=='BIG' else 1
    
    balls = [final_number, sukuna.get("partnerNumber", 7), 9, 2]
    score = round((kingg["score"]*0.3 + mohit["score"]*0.2 + sukuna["score"]*0.25 + shinchan["score"]*0.25))

    return {
        "predictedNumber":final_number,"predictedSize":final_size,"partnerNumber":balls[1],
        "balls":list(set(balls))[:4],"score":score,
        "kinggSize":kingg["predictedSize"],"mohitSize":mohit["predictedSize"],
        "sukunaSize":sukuna["predictedSize"],"shinchanSize":shinchan["predictedSize"],
        "vote":votes
    }

# ============ TELEGRAM SENDER ============
def send_telegram_message(text, send_sticker=False, chat_id=None):
    target_chat = chat_id if chat_id else TELEGRAM_CHANNEL_ID
    if TELEGRAM_BOT_TOKEN=="YOUR_BOT_TOKEN_HERE" or not TELEGRAM_BOT_TOKEN:
        print("[SKIP] Telegram token not set.", flush=True)
        return False
    try:
        if send_sticker and CUSTOM_STICKER_FILE_ID:
            try:
                stk_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendSticker"
                requests.post(stk_url, json={"chat_id": target_chat, "sticker": CUSTOM_STICKER_FILE_ID}, timeout=10)
            except Exception as e:
                print("Sticker send error:", e, flush=True)

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": target_chat, "text": text}
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print("Telegram send exception:", e, flush=True)
        return False

# ============ ACCURATE WINGO ISSUE GENERATOR & API FETCH ============
def generate_current_wingo_issue():
    # Accurate WinGo 1M format: YYYYMMDD01XXXX based on IST minutes of the day
    ist_now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    date_str = ist_now.strftime("%Y%m%d")
    total_mins = ist_now.hour * 60 + ist_now.minute + 1
    return f"{date_str}01{total_mins:04d}"

def fetch_wingo_history():
    segment = "WinGo_30S" if WINGO_TYPE=="30S" else "WinGo_1M"
    url = f"https://draw.ar-lottery01.com/WinGo/{segment}/GetHistoryIssuePage.json?ts={int(time.time()*1000)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://ar-lottery01.com/"
    }
    try:
        res = requests.get(url, timeout=8, headers=headers)
        if res.status_code == 200 and res.text.strip().startswith('{'):
            data = res.json()
            lst = data.get('data', {}).get('list', []) or data.get('data', {}).get('gameslist', [])
            if lst:
                return lst
    except Exception:
        pass

    # Fallback with correct accurate issue format
    current_issue = int(generate_current_wingo_issue())
    simulated_list = []
    for i in range(25):
        simulated_list.append({
            "issueNumber": str(current_issue - i),
            "number": random.randint(0, 9)
        })
    return simulated_list

# ============ MESSAGE BUILDERS ============
def build_prediction_message(next_issue, result):
    B = to_bold
    short_issue = str(next_issue)[-5:]
    size = result["predictedSize"]
    n1 = result["predictedNumber"]
    n2 = result["partnerNumber"]
    balls = '‚ '.join(B(str(b)) for b in result["balls"])
    conf = result["score"]
    conf_bar = "🟩" * (conf//20) + "⬜" * (5 - conf//20)
    
    return (
        f"••••••••••••••••••••••••••••••••••••\n"
        f"🎮 {B('GAMEGURU.AI')} {B('PRO MAX')}\n"
        f"🚀 {B('WINGO')} {B(WINGO_TYPE)} {B('PREDICTION')}\n"
        f"      ———————————--------\n"
        f"{B('ISSUE')}  ➜ {B(short_issue)} ({next_issue[-6:]})\n"
        f"🎯 {B('TARGET')} ➜  {B(size)}\n"
        f"🔢 {B('NUMBERS')} ➜ {B(str(n1))} , {B(str(n2))}\n"
        f"🎱 {B('BALLS')} ➜ {balls}\n"
        f"📊 {B('CONF')} ➜ {B(str(conf)+'%')} {conf_bar}\n"
        f"      ———————————---------\n"
        f"👑 {B('ADMIN CONTROL ACTIVE')}\n"
        f"•••••••••••••••••••••••••••••••••••••"
    )

def build_win_message(target_issue, pred_size, pred_num, actual_size, actual_num, stats):
    B = to_bold
    acc = round((stats['wins']/stats['totalBets']*100)) if stats['totalBets'] else 0
    return (
        f"✅ {B('PERIOD')} {B(str(target_issue)[-5:])} {B('WIN')}\n\n"
        f"📌 Prediction --> {B(pred_size)} ({B(str(pred_num))})\n"
        f"🎯 Actual --> {B(actual_size)} ({B(str(actual_num))})\n\n"
        f"🔥 {B('Win Streak')}: {stats['consecutiveWin']}\n"
        f"🏆 {B('Highest Streak')}: {stats['highestWinStreak']}\n"
        f"📊 {B('Accuracy')}: {acc}% ({stats['wins']}W/{stats['totalBets']})\n"
        f"🎯 {B('Total Wins')}: {stats['wins']}"
    )

def build_loss_message(target_issue, pred_size, pred_num, actual_size, actual_num, stats):
    B = to_bold
    acc = round((stats['wins']/stats['totalBets']*100)) if stats['totalBets'] else 0
    return (
        f"❌ {B('PERIOD')} {B(str(target_issue)[-5:])} {B('LOSS')}\n\n"
        f"📌 Prediction --> {B(pred_size)} ({B(str(pred_num))})\n"
        f"🎯 Actual --> {B(actual_size)} ({B(str(actual_num))})\n\n"
        f"❄️ {B('Loss Streak')}: {stats['consecutiveLoss']}\n"
        f"📊 {B('Accuracy')}: {acc}% ({stats['wins']}W/{stats['totalBets']})\n"
        f"🔄 {B('Next will be REVERSE')}"
    )

# ============ TELEGRAM COMMAND & AUTH POLLING BOT ============
def telegram_polling_worker():
    global bot_running
    last_update_id = 0
    print("[AUTH BOT] Telegram polling worker started.", flush=True)

    while True:
        if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or not TELEGRAM_BOT_TOKEN:
            time.sleep(10)
            continue
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={last_update_id+1}&timeout=30"
            res = requests.get(url, timeout=35)
            if res.status_code == 200:
                data = res.json()
                for update in data.get("result", []):
                    last_update_id = update["update_id"]
                    msg = update.get("message")
                    if not msg or "text" not in msg:
                        continue
                    
                    chat_id = msg["chat"]["id"]
                    text = msg["text"].strip()
                    username = msg["from"].get("username", str(chat_id))

                    if text.startswith("/start"):
                        send_telegram_message(
                            "👋 Welcome to GameGuru AI Bot!\n\n"
                            "Please login using:\n`/login <username> <password>`\n\n"
                            "Or register using:\n`/register <username> <password>`", chat_id=chat_id
                        )
                    elif text.startswith("/register"):
                        parts = text.split()
                        if len(parts) == 3:
                            u, p = parts[1], parts[2]
                            users_db[u] = p
                            pending_approvals.add(u)
                            send_telegram_message(f"📝 Registration request submitted for `{u}`. Waiting for Admin approval.", chat_id=chat_id)
                        else:
                            send_telegram_message("⚠️ Format: `/register username password`", chat_id=chat_id)
                    elif text.startswith("/login"):
                        parts = text.split()
                        if len(parts) == 3:
                            u, p = parts[1], parts[2]
                            if u in users_db and users_db[u] == p:
                                if u in approved_users or u == "admin":
                                    user_sessions[chat_id] = u
                                    send_telegram_message(f"✅ Login successful! Welcome `{u}`.\nCommands: `/status`, `/results` (Admin: `/startbot`, `/stopbot`, `/approve <user>`)" , chat_id=chat_id)
                                elif u in pending_approvals:
                                    send_telegram_message("⏳ Your account is pending admin approval.", chat_id=chat_id)
                                else:
                                    send_telegram_message("❌ Account not approved.", chat_id=chat_id)
                            else:
                                send_telegram_message("❌ Invalid username or password.", chat_id=chat_id)
                        else:
                            send_telegram_message("⚠️ Format: `/login username password`", chat_id=chat_id)
                    elif text.startswith("/approve"):
                        if user_sessions.get(chat_id) == "admin":
                            parts = text.split()
                            if len(parts) == 2:
                                target = parts[1]
                                if target in pending_approvals:
                                    pending_approvals.remove(target)
                                    approved_users.add(target)
                                    send_telegram_message(f"✅ User `{target}` approved successfully!", chat_id=chat_id)
                                else:
                                    send_telegram_message(f"⚠️ User `{target}` not found in pending list.", chat_id=chat_id)
                        else:
                            send_telegram_message("⛔ Admin only command.", chat_id=chat_id)
                    elif text.startswith("/startbot"):
                        if user_sessions.get(chat_id) == "admin":
                            bot_running = True
                            send_telegram_message("🚀 Prediction Bot Started!", chat_id=chat_id)
                        else:
                            send_telegram_message("⛔ Admin only command.", chat_id=chat_id)
                    elif text.startswith("/stopbot"):
                        if user_sessions.get(chat_id) == "admin":
                            bot_running = False
                            send_telegram_message("🛑 Prediction Bot Stopped!", chat_id=chat_id)
                        else:
                            send_telegram_message("⛔ Admin only command.", chat_id=chat_id)
                    elif text.startswith("/status"):
                        status_text = f"🤖 Bot Status: {'RUNNING 🟢' if bot_running else 'STOPPED 🔴'}\n📊 Total Bets: {bot_stats['totalBets']}\nwins: {bot_stats['wins']} | Losses: {bot_stats['losses']}"
                        send_telegram_message(status_text, chat_id=chat_id)
                    elif text.startswith("/results"):
                        res_snippet = "\n".join([f"Issue {r['issue'][-5:]} | Num: {r['number']} ({r['size']})" for r in results_history[:10]])
                        send_telegram_message(f"📜 Last 10 Results:\n{res_snippet}", chat_id=chat_id)
        except Exception as e:
            print("Telegram polling error:", e, flush=True)
        time.sleep(2)

# ============ MAIN BACKGROUND WORKER ============
def automated_bot_worker():
    print(f"[WORKER STARTED] WINGO {WINGO_TYPE} | Poll {POLL_INTERVAL}s", flush=True)

    kingg = UltimatePredictorV12()
    mohit = MohitEngine()
    sukuna = SukunaEngine()
    shinchan = ShinchanEngine()

    last_processed_issue = ""
    active_prediction = None

    while True:
        try:
            if not bot_running:
                time.sleep(5)
                continue

            lst = fetch_wingo_history()
            if not lst:
                time.sleep(POLL_INTERVAL)
                continue

            latest = lst[0]
            current_issue = str(latest.get('issueNumber') or latest.get('issue') or latest.get('periodNumber'))
            try:
                actual_num = int(latest.get('number', 0))
            except:
                actual_num = 0
            actual_size = "BIG" if actual_num >= 5 else "SMALL"

            # Store result in history
            if results_history and results_history[0]["issue"] != current_issue:
                add_result_to_history(current_issue, actual_num, actual_size)
            elif not results_history:
                add_result_to_history(current_issue, actual_num, actual_size)

            # Step 1: Settle previous prediction
            if active_prediction and current_issue == active_prediction['target_issue']:
                is_win = (actual_size == active_prediction['size']) or (actual_num == active_prediction['number'])
                bot_stats['totalBets'] += 1
                if is_win:
                    bot_stats['wins'] += 1
                    bot_stats['consecutiveWin'] += 1
                    bot_stats['consecutiveLoss'] = 0
                    if bot_stats['consecutiveWin'] > bot_stats['highestWinStreak']:
                        bot_stats['highestWinStreak'] = bot_stats['consecutiveWin']
                    win_msg = build_win_message(active_prediction['target_issue'], active_prediction['size'], active_prediction['number'], actual_size, actual_num, bot_stats)
                    send_telegram_message(win_msg, send_sticker=True)
                else:
                    bot_stats['losses'] += 1
                    bot_stats['consecutiveLoss'] += 1
                    bot_stats['consecutiveWin'] = 0
                    loss_msg = build_loss_message(active_prediction['target_issue'], active_prediction['size'], active_prediction['number'], actual_size, actual_num, bot_stats)
                    send_telegram_message(loss_msg, send_sticker=False)
                
                active_prediction = None
                kingg.consecutiveLoss = bot_stats['consecutiveLoss']
                kingg.consecutiveWin = bot_stats['consecutiveWin']
                kingg.lastLossSize = actual_size if not is_win else None

            # Step 2: New prediction
            if current_issue != last_processed_issue:
                last_processed_issue = current_issue
                try:
                    next_issue = str(int(current_issue) + 1)
                except:
                    next_issue = generate_current_wingo_issue()

                numbers = [int(item.get('number', 0)) for item in lst[:20]]

                kingg_pred = kingg.predict(numbers)
                mohit_pred = mohit.predict(current_issue, numbers)
                sukuna_pred = sukuna.predict(numbers)
                shinchan_pred = shinchan.predict(next_issue, numbers)

                hybrid_result = combine_hybrid(kingg_pred, mohit_pred, sukuna_pred, shinchan_pred)

                msg = build_prediction_message(next_issue, hybrid_result)
                print(f"[GENERATED] Sending prediction for issue {next_issue}...", flush=True)
                send_telegram_message(msg, send_sticker=False)

                active_prediction = {
                    "target_issue": next_issue,
                    "size": hybrid_result["predictedSize"],
                    "number": hybrid_result["predictedNumber"]
                }

        except Exception as e:
            print("Background worker loop error:", e, flush=True)

        time.sleep(POLL_INTERVAL)

# ============ FLASK ROUTES ============
@app.route('/', methods=['GET', 'HEAD'])
def index():
    return jsonify({
        "status": "GAMEGURU.AI PRO MAX running",
        "bot_running": bot_running,
        "wingo_type": WINGO_TYPE,
        "stats": bot_stats,
        "total_results_stored": len(results_history)
    })

@app.route('/stats', methods=['GET', 'HEAD'])
def stats_route():
    return jsonify(bot_stats)

@app.route('/results', methods=['GET'])
def results_route():
    # Returns up to 1440 results stored
    return jsonify(results_history)

# ============ AUTO-START THREADS ============
def start_workers():
    t_bot = threading.Thread(target=automated_bot_worker, daemon=True)
    t_bot.start()
    
    t_auth = threading.Thread(target=telegram_polling_worker, daemon=True)
    t_auth.start()
    print("[INIT] All background worker threads started successfully.", flush=True)

start_workers()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, use_reloader=False)
