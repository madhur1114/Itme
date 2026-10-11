"""
GAMEGURU.AI Telegram prediction worker
Algorithms are ported from the supplied index.html. These are heuristic guesses,
not validated probabilities; random draw outcomes cannot be reliably predicted.
"""
import asyncio
import json
import logging
import os
import signal
import time
from pathlib import Path
from typing import Any

import requests
from telegram import Bot
from telegram.constants import ParseMode

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("gameguru")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "").strip()
STICKER_FILE_ID = os.getenv("STICKER_FILE_ID", "").strip()
GAME_TYPE = os.getenv("GAME_TYPE", "1M").upper()  # 1M or 30S
POLL_SECONDS = max(5, int(os.getenv("POLL_SECONDS", "8")))
STATE_FILE = Path(os.getenv("STATE_FILE", "gameguru_state.json"))
API_BASE = "https://draw.ar-lottery01.com/WinGo"

if GAME_TYPE not in {"1M", "30S"}:
    raise ValueError("GAME_TYPE must be 1M or 30S")

def to_bold(text: Any) -> str:
    mapping = {
        **dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭")),
        **dict(zip("abcdefghijklmnopqrstuvwxyz", "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇")),
        **dict(zip("0123456789", "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵")),
    }
    return "".join(mapping.get(ch, ch) for ch in str(text))

# History copied from the HTML's Sukuna engine database.
SUKUNA_HISTORY = [2,1,2,0,5,5,5,6,0,7,1,2,6,1,9,7,6,5,0,0,0,8,4,5,2,4,3,9,4,9,4,1,2,3,4,4,2,6,1,2,9,6,1,9,2,8,9,1,8,7, 2,9,5,9,5,6,3,0,6,8,2,9,3,8,6,8,5,0,6,8,6,9,8,5,3,1,4,4,9,8,9,1,4,8,3,4,3,5,2,1,3,3,2,3,6,8,2,9,4,5, 6,8,1,4,2,9,0,6,5,5,9,3,5,7,7,3,0,8,1,5,8,5,9,9,4,7,7,1,3,3,6,3,1,6,0,2,5,4,8,2,3,0,7,3,1,0,6,0,9,7, 1,3,8,0,6,9,3,2,0,4,5,3,2,4,0,8,6,3,5,3,8,5,3,6,3,2,8,8,0,5,4,2,4,6,3,4,4,6,5,5,0,5,1,3,6,9,7,0,2,9, 5,5,0,9,4,1,0,5,1,9,3,5,4,7,1,5,5,5,3,9,9,7,8,9,7,3,7,1,5,2,0,1,6,7,6,1,1,1,0,3,1,1,0,1,0,6,1,8,1,6, 2,1,0,3,3,8,7,4,7,3,2,5,5,0,6,9,5,1,3,3,0,0,3,4,6,6,8,6,8,4,2,5,4,4,9,1,7,7,8,6,0,3,0,6,4,1,3,2,4,3, 3,7,4,9,5,5,9,5,8,9,2,1,0,1,9,2,3,0,2,2,5,1,5,8,7,5,0,8,3,5,4,1,5,0,2,9,2,4,0,8,2,1,2,3,3,6,4,1,9,8, 4,7,5,5,0,5,6,8,3,7,9,2,1,0,7,2,5,0,8,0,5,1,6,2,2,6,4,9,1,5,3,4,3,7,1,7,3,3,2,6,7,6,1,1,1,4,8,7,6,1, 9,6,9,5,8,2,2,0,8,6,8,5,4,8,2,7,4,5,1,2,6,5,3,6,8,8,8,1,2,6,4,4,7,9,8,9,6,8,6,7,4,4,9,8,9,5,3,1,0,4, 6,5,6,4,0,9,9,1,1,9,4,4,9,3,2,6,2,3,7,5,8,0,8,2,5,8,8,8,9,7,0,5,3,8,5,7,8,6,9,3,6,3,6,4,3,6,3,4,3,0, 3,6,5,6,6,1,6,7,1,4,1,5,9,8,9,7,5,9,6,9,6,6,5,3,8,6,4,8,3,7,7,4,1,4,2,8,4,5,1,4,6,1,3,2,9,8,7,6,1,8, 1,2,7,7,6,1,7,9,0,5,9,2,5,5,9,2,6,1,7,0,2,7,4,2,8,5,1,6,7,9,7,2,3,7,4,9,7,9,5,3,5,2,6,9,1,8,6,6,0,7, 3,2,8,3,6,4,2,6,3,1,4,1,8,1,8,2,3,3,6,8,2,1,2,5,6,0,7,7,1,2,2,9,1,7,3,5,7,0,3,7,4,1,8,8,7,3,2,8,5,7, 4,7,7,8,7,1,7,1,8,8,8,0,4,4,1,1,2,4,2,2,4,3,8,9,7,7,4,5,8,8,9,9,0,3,7,2,2,4,1,0,1,2,8,2,0,4,9,5,4,2, 3,1,0,9,3,6,6,5,1,4,4,9,3,0,5,6,2,0,5,2,3,7,5,2,4,1,9,2,6,2,4,6,1,3,2,3,8,1,0,5,2,2,2,7,0,1,2,3,9,1, 6,0,3,7,6,6,8,9,5,2,7,6,2,3,1,7,1,7,9,7,7,4,4,3,2,1,9,7,9,5,3,8,5,3,6,7,8,6,0,1,7,9,7,2,4,5,8,9,2,3, 0,4,1,4,4,8,6,6,0,3,9,7,5,9,9,2,9,2,6,2,7,5,5,9,9,3,6,5,5,0,8,0,8,5,8,8,8,4,8,4,7,6,0,0,9,1,3,5,6,4, 6,8,3,8,9,4,2,1,0,2,8,0,8,7,4,1,1,0,7,3,5,0,9,6,7,2,9,2,2,0,7,9,8,1,9,2,5,4,6,3,7,0,2,3,3,5,8,2,6,6, 8,8,9,8,8,7,2,2,3,8,7,1,7,4,4,2,7,9,5,1,7,5,5,8,6,0,1,7,0,2,7,0,8,3,0,6,4,8,3,2,2,1,8,3,6,0,4,5,0,9, 5,2,0,0,7,2,2,8,9,5,3,0,7,5,5,8,2,8,8,2,4,1,5,2,4,0,1,7,8,3,6,6,8,7,1,4,2,5,1,4,9,3,2,8,2,7,0,8,9,2]


class UltimatePredictorV12:
    def __init__(self):
        self.hallOfFame = {"BIG_KINGS":[8,9], "SMALL_KINGS":[1,2]}
        self.directRules = {
            "BB":("SMALL",[1],78), "SS":("BIG",[8],78),
            "BBB":("SMALL",[1],80), "SSS":("BIG",[8],80),
            "BSB":("SMALL",[2],72), "SBS":("BIG",[9],72),
            "BBS":("BIG",[9],70), "SSB":("SMALL",[2],70)
        }
        self.consecutiveLoss=0; self.lastLossSize=None
    def predict(self, history):
        h = list(history)
        if len(h) >= 2:
            pat = "".join("B" if n >= 5 else "S" for n in h[:4])
            for ln in range(min(4,len(pat)),1,-1):
                rule = pat[:ln]
                if rule in self.directRules:
                    size, nums, score = self.directRules[rule]
                    return {"predictedNumber":nums[0],"predictedSize":size,"partnerNumber":9 if size=="BIG" else 2,"score":score}
        if len(h)>=2:
            direction = "BIG" if h[0]>=5 else "SMALL"
            streak=1
            for n in h[1:10]:
                if ("BIG" if n>=5 else "SMALL")==direction: streak+=1
                else: break
            if streak>=2:
                size = "SMALL" if direction=="BIG" else "BIG"
                pool = [8,9] if size=="BIG" else [1,2]
                return {"predictedNumber":pool[0],"predictedSize":size,"partnerNumber":pool[1],"score":min(85,68+streak*2)}
        big_recent=sum(n>=5 for n in h[:5])
        size="SMALL" if big_recent>=3 else "BIG"
        return {"predictedNumber":1 if size=="SMALL" else 8,"predictedSize":size,"partnerNumber":2 if size=="SMALL" else 9,"score":60}

class MohitEngine:
    def predict(self, latestIssue, historyNumbers):
        hist=list(historyNumbers or [])
        seed=int(str(latestIssue)[-3:] or 0)
        if not hist:
            return {"predictedNumber":8,"predictedSize":"BIG","partnerNumber":3,"score":74}
        bigBias=sum(n>=5 for n in hist[:10])
        size=("BIG" if hist[0]>=5 else "SMALL") if seed%2 else ("BIG" if bigBias>=5 else "SMALL")
        first=hist[0]
        if size=="BIG":
            n1=[5,6,7,8,9][(seed+first)%5]; n2=[0,1,2,3,4][(seed*3)%5]
        else:
            n1=[0,1,2,3,4][(seed+first)%5]; n2=[5,6,7,8,9][(seed*7)%5]
        return {"predictedNumber":n1,"predictedSize":size,"partnerNumber":n2,"score":74}

class SukunaEngine:
    def __init__(self):
        self.history=SUKUNA_HISTORY
    def predict(self, apiList):
        live=[int(x["number"]) for x in apiList[:20]][::-1]
        # Search exact historical sequences from longest to shortest, then vote.
        preds=[]
        for length in range(min(len(live),15),2,-1):
            pat=live[-length:]
            matches=[self.history[i+length] for i in range(len(self.history)-length) if self.history[i:i+length]==pat]
            if matches:
                counts={n:matches.count(n) for n in set(matches)}
                n=max(counts,key=counts.get)
                conf=100*counts[n]/len(matches)
                if conf>80: preds.append((n,conf)); break
        if not preds and len(live)>=2:
            pat=live[-2:]
            matches=[self.history[i+2] for i in range(len(self.history)-2) if self.history[i:i+2]==pat]
            if matches:
                counts={n:matches.count(n) for n in set(matches)}
                n=max(counts,key=counts.get); preds.append((n,100*counts[n]/len(matches)))
        if preds:
            n,conf=preds[0]
        else:
            n=8 if sum(x>=5 for x in live[:5])<3 else 1; conf=60
        return {"predictedNumber":n,"predictedSize":"BIG" if n>=5 else "SMALL","partnerNumber":9 if n>=5 else 2,"score":round(max(55,min(90,conf)))}

class ShinchanEngine:
    def predict(self, currentPeriodStr, historyNumbers):
        digits=[int(x) for x in str(currentPeriodStr) if x.isdigit()] or [1]
        total=sum(digits); tail=digits[-1]
        hist=list(historyNumbers[:5])
        historyScore=sum(v*(5-i) for i,v in enumerate(hist)) if len(hist)>=5 else total*3
        index=(total*5+tail*7+historyScore*11)%20
        size="BIG" if index%2==0 or total%2==1 else "SMALL"
        pool=[5,6,7,8,9] if size=="BIG" else [0,1,2,3,4]
        n1=pool[(total+1)%5]; n2=pool[(historyScore+2 if size=="BIG" else historyScore+1)%5]
        if n1==n2: n2=pool[(pool.index(n2)+1)%5]
        return {"predictedNumber":n1,"predictedSize":size,"partnerNumber":n2,"score":min(99,round(96.2+abs(historyScore)%3.5))}

def combineHybrid(kingg, mohit, sukuna, shinchan):
    votes={"BIG":0.0,"SMALL":0.0}
    votes[kingg["predictedSize"]]+=1.0
    votes[mohit["predictedSize"]]+=0.8
    votes[sukuna["predictedSize"]]+=1.0
    votes[shinchan["predictedSize"]]+=1.0
    size="BIG" if votes["BIG"]>=votes["SMALL"] else "SMALL"
    nums=[kingg["predictedNumber"],kingg["partnerNumber"],mohit["predictedNumber"],mohit["partnerNumber"],sukuna["predictedNumber"],sukuna["partnerNumber"],shinchan["predictedNumber"],shinchan["partnerNumber"]]
    n=sukuna["predictedNumber"]
    if (n>=5)!=(size=="BIG"):
        candidates=[shinchan["predictedNumber"],kingg["predictedNumber"]]
        n=next((x for x in candidates if (x>=5)==(size=="BIG")),8 if size=="BIG" else 1)
    pool=list(dict.fromkeys(x for x in nums if x is not None))
    partner=next((x for x in pool if x!=n and (x>=5)==(size=="BIG")),9 if size=="BIG" else 2)
    score=round(kingg["score"]*.28+mohit["score"]*.12+sukuna["score"]*.30+shinchan["score"]*.30)
    agree=len({kingg["predictedSize"],mohit["predictedSize"],sukuna["predictedSize"],shinchan["predictedSize"]})==1
    score=min(97,score+8) if agree else max(55,score-4)
    return {"predictedNumber":n,"predictedSize":size,"partnerNumber":partner,"balls":pool,"score":score,"label":"4/4 engines agree" if agree else f"Hybrid vote {votes['BIG']:.1f}B / {votes['SMALL']:.1f}S"}


def issue_of(item: dict) -> str:
    return str(item.get("issueNumber") or item.get("issue") or item.get("periodNumber") or "")

def number_of(item: dict) -> int | None:
    raw = item.get("number", item.get("openCode", item.get("winNumber")))
    try:
        n = int(raw)
        return n if 0 <= n <= 9 else None
    except (TypeError, ValueError):
        return None

def fetch_history(session: requests.Session) -> list[dict]:
    segment = "WinGo_30S" if GAME_TYPE == "30S" else "WinGo_1M"
    url = f"{API_BASE}/{segment}/GetHistoryIssuePage.json"
    response = session.get(url, params={"ts": int(time.time() * 1000)}, timeout=12)
    response.raise_for_status()
    payload = response.json()
    items = payload.get("data", {}).get("list") or payload.get("data", {}).get("gameslist") or []
    valid = []
    for item in items:
        issue, num = issue_of(item), number_of(item)
        if issue and num is not None:
            valid.append({**item, "_issue": issue, "_number": num})
    return valid

def next_issue(issue: str) -> str:
    # Keep issue IDs as strings except for the increment operation.
    try:
        return str(int(issue) + 1)
    except ValueError:
        raise ValueError(f"Non-numeric issue ID: {issue!r}")

def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"last_issue": "", "pending": None, "stats": {
            "wins": 0, "losses": 0, "streak_w": 0, "streak_l": 0, "best_streak": 0
        }}

def save_state(state: dict) -> None:
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)

async def send_telegram(text: str, sticker: bool = False) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        log.warning("Telegram not configured; set TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID.")
        return
    async with Bot(token=TELEGRAM_BOT_TOKEN) as bot:
        if sticker and STICKER_FILE_ID:
            try:
                await bot.send_sticker(chat_id=TELEGRAM_CHANNEL_ID, sticker=STICKER_FILE_ID)
            except Exception:
                log.exception("Sticker send failed; continuing with text")
        await bot.send_message(
            chat_id=TELEGRAM_CHANNEL_ID,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )

def make_prediction(history: list[dict], issue: str) -> dict:
    nums = [x["_number"] for x in history]
    api_list = [{"number": str(n)} for n in nums]
    king = UltimatePredictorV12()
    mohit = MohitEngine()
    sukuna = SukunaEngine()
    shinchan = ShinchanEngine()

    k = king.predict(nums)
    m = mohit.predict(issue, nums)
    s = sukuna.predict(api_list)
    sh = shinchan.predict(str(int(issue) + 1), nums)
    combo = combineHybrid(k, m, s, sh)

    # The HTML has four selectable engines; default to the hybrid ensemble.
    return {
        "number": int(combo["predictedNumber"]),
        "size": str(combo["predictedSize"]),
        "partner": int(combo["partnerNumber"]),
        "balls": [int(n) for n in combo["balls"] if n is not None][:6],
        "score": int(combo["score"]),
        "server": "HYBRID ALL",
        "label": str(combo["label"]),
        "target_issue": next_issue(issue),
        "source_issue": issue,
    }

def prediction_message(p: dict) -> str:
    balls = "  •  ".join(to_bold(n) for n in p["balls"])
    return (
        "╭━━━━━━━━━━━━━━━━━━╮\n"
        "⚡ <b>GAMEGURU.AI • PRO</b>\n"
        "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        f"🎯 <b>PERIOD</b>  ━  <code>{p['target_issue']}</code>\n"
        f"📌 <b>CALL</b>  ━  <b>{p['size']}</b>\n"
        f"🔢 <b>TOP NUMBER</b>  ━  <b>{p['number']}</b>\n"
        f"🎱 <b>NUMBER POOL</b>  ━  {balls}\n"
        f"🧠 <b>ENGINE</b>  ━  {p['server']}\n"
        f"📊 <b>HEURISTIC SCORE</b>  ━  {p['score']}%*\n\n"
        f"🧩 <i>{p['label']}</i>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "⚠️ <i>Entertainment-only heuristic. This score is not a verified win probability; "
        "draws may be random and no result is guaranteed.</i>"
    )

def result_message(p: dict, actual: int, stats: dict) -> tuple[str, bool]:
    actual_size = "BIG" if actual >= 5 else "SMALL"
    won = actual_size == p["size"] or actual == p["number"]
    total = stats["wins"] + stats["losses"]
    accuracy = round(stats["wins"] * 100 / total) if total else 0
    icon = "✅" if won else "❌"
    outcome = "WIN" if won else "LOSS"
    text = (
        f"{icon} <b>RESULT • {outcome}</b>\n\n"
        f"🧾 Period: <code>{p['target_issue']}</code>\n"
        f"🔮 Call: <b>{p['size']}</b> / number <b>{p['number']}</b>\n"
        f"🎲 Actual: <b>{actual_size}</b> / number <b>{actual}</b>\n"
        f"📈 Record: <b>{stats['wins']}W - {stats['losses']}L</b>\n"
        f"🎯 Historical hit rate: <b>{accuracy}%</b> ({total} settled calls)\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "<i>Past results do not predict future outcomes.</i>"
    )
    return text, won

def main() -> None:
    state = load_state()
    session = requests.Session()
    session.headers.update({"User-Agent": "GAMEGURU-PredictionWorker/1.0"})
    log.info("Starting worker for %s; poll=%ss", GAME_TYPE, POLL_SECONDS)

    while True:
        try:
            history = fetch_history(session)
            if not history:
                log.warning("API returned no valid history")
                time.sleep(POLL_SECONDS)
                continue

            latest = history[0]
            issue, actual = latest["_issue"], latest["_number"]
            pending = state.get("pending")

            # Settle the saved prediction only when the exact target issue appears.
            if pending and issue == pending.get("target_issue"):
                stats = state["stats"]
                won = ("BIG" if actual >= 5 else "SMALL") == pending["size"] or actual == pending["number"]
                if won:
                    stats["wins"] += 1
                    stats["streak_w"] += 1
                    stats["streak_l"] = 0
                    stats["best_streak"] = max(stats["best_streak"], stats["streak_w"])
                else:
                    stats["losses"] += 1
                    stats["streak_l"] += 1
                    stats["streak_w"] = 0
                msg, is_win = result_message(pending, actual, stats)
                asyncio.run(send_telegram(msg, sticker=is_win))
                state["pending"] = None
                save_state(state)

            if issue != state.get("last_issue"):
                # Issue changes: create one prediction for the next issue, once only.
                p = make_prediction(history, issue)
                asyncio.run(send_telegram(prediction_message(p)))
                state["last_issue"] = issue
                state["pending"] = p
                save_state(state)
                log.info("Prediction sent for target issue %s", p["target_issue"])

        except requests.RequestException:
            log.exception("History API request failed")
        except Exception:
            log.exception("Worker cycle failed")

        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()
