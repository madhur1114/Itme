"""
GAMEGURU.AI PRO MAX - Background Auto Prediction Bot
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

# Stats
bot_stats = {
    "wins": 0, "losses": 0,
    "consecutiveWin": 0, "consecutiveLoss": 0,
    "highestWinStreak": 0, "totalBets": 0,
    "jackpots": 0
}

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

# ============ ENGINE 1: KINGG v12 ============
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
        self.wins=0; self.losses=0; self.jackpots=0
        self.consecutiveLoss=0; self.consecutiveWin=0
        self.lastLossSize=None; self.totalBets=0

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

    def analyze_streak(self, h):
        if len(h)<2: return None
        streak=1; dir_ = 'BIG' if h[0]>=5 else 'SMALL'
        for i in range(1,min(10,len(h))):
            if ('BIG' if h[i]>=5 else 'SMALL')==dir_:
                streak+=1
            else: break
        if streak>=2:
            od='SMALL' if dir_=='BIG' else 'BIG'
            return {"prediction":od,"number":8 if od=='BIG' else 1,"score":min(85,68+streak*2),"streak":streak,"direction":dir_}
        return None

    def get_forced_reverse(self):
        if self.lastLossSize=='BIG': return {"prediction":'SMALL',"number":1,"score":72,"forced":True}
        if self.lastLossSize=='SMALL': return {"prediction":'BIG',"number":8,"score":72,"forced":True}
        return None

    def get_smart_number(self, size, h):
        pool = self.hall_of_fame["BIG_KINGS"] if size=='BIG' else self.hall_of_fame["SMALL_KINGS"]
        scored=[]
        for num in pool:
            s=50
            if num==8: s+=30
            elif num==9: s+=28
            elif num==1: s+=25
            elif num==2: s+=23
            for i in range(min(10,len(h))):
                if h[i]==num:
                    s+= (0.85**i)*10
            if num not in h:
                s+=15
            else:
                s+= min(10, len(h)-1 - h.index(num))
            scored.append((num,s))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]

    def predict(self, history):
        h=[int(x) for x in history if str(x).isdigit() or isinstance(x,int)]
        if self.consecutiveLoss>=1:
            f=self.get_forced_reverse()
            if f:
                return {"predictedNumber":f["number"],"predictedSize":f["prediction"],"partnerNumber":9 if f["prediction"]=='BIG' else 2,"score":f["score"],"logic":"REVERSE_AFTER_LOSS","label":f"🔄 Reverse after loss","forcedReverse":True}
        r=self.apply_direct_rules(h)
        if r:
            return {"predictedNumber":r["number"],"predictedSize":r["prediction"],"partnerNumber":9 if r["prediction"]=='BIG' else 2,"score":r["score"],"logic":"DIRECT_RULE","label":f"📐 Rule {r['rule']}"}
        s=self.analyze_streak(h)
        if s and s["streak"]>=2:
            num=self.get_smart_number(s["prediction"],h)
            return {"predictedNumber":num,"predictedSize":s["prediction"],"partnerNumber":9 if s["prediction"]=='BIG' else 2,"score":s["score"],"logic":"STREAK_ANALYSIS","label":f"📊 {s['streak']}x {s['direction']}→breaker"}
        rb=sum(1 for i in range(min(5,len(h))) if h[i]>=5)
        dp='SMALL' if rb>=3 else 'BIG'
        return {"predictedNumber":8 if dp=='BIG' else 1,"predictedSize":dp,"partnerNumber":9 if dp=='BIG' else 2,"score":60,"logic":"SMART_DEFAULT","label":"🔒 Trend default"}

# ============ ENGINE 2: MOHIT ============
class MohitEngine:
    def predict(self, latest_issue, history_numbers):
        hist=[n for n in (history_numbers or []) if isinstance(n,int)]
        try:
            seed=int(str(latest_issue)[-3:])
        except:
            seed=0
        hs=hist[:10]
        if not hs:
            return {"predictedNumber":8,"predictedSize":"BIG","partnerNumber":3,"score":74,"logic":"MOHIT","label":"🔥 Mohit Pure"}
        big_bias=sum(1 for n in hs if n>=5)
        if seed%2==0:
            trend = 'BIG' if big_bias>=5 else 'SMALL'
        else:
            trend = 'SMALL' if hs[0]>=5 else 'BIG'
        first=hs[0] if hs else 0
        if trend=='BIG':
            n1=[5,6,7,8,9][(seed+first)%5]
            n2=[0,1,2,3,4][(seed*3)%5]
        else:
            n1=[0,1,2,3,4][(seed+first)%5]
            n2=[5,6,7,8,9][(seed*7)%5]
        return {"predictedNumber":n1,"predictedSize":trend,"partnerNumber":n2,"score":74,"logic":"MOHIT","label":"🔥 Mohit Pure"}

# ============ ENGINE 3: SUKUNA v16 ============
class SukunaEngine:
    def __init__(self):
        self.history=SUKUNA_HISTORY
        self.cache={}

    def get_live_pattern(self, api_list, count=20):
        nums=[]
        for i in range(min(count,len(api_list))):
            nums.append(int(api_list[i]))
        return list(reversed(nums))

    def find_exact_matches(self, pattern, max_results=100):
        key=','.join(map(str,pattern))
        if key in self.cache:
            return self.cache[key]
        matches=[]
        l=len(pattern)
        if l==0 or l>20:
            self.cache[key]=matches
            return matches
        for i in range(len(self.history)-l):
            ok=True
            for j in range(l):
                if self.history[i+j]!=pattern[j]:
                    ok=False; break
            if ok:
                matches.append({"nextNumber":self.history[i+l]})
                if len(matches)>=max_results: break
        self.cache[key]=matches
        return matches

    def find_fuzzy_matches(self, pattern, tol=1, max_results=50):
        matches=[]
        l=len(pattern)
        for i in range(len(self.history)-l):
            diff=0
            for j in range(l):
                if self.history[i+j]!=pattern[j]:
                    diff+=1
                    if diff>tol: break
            if diff<=tol:
                matches.append({"nextNumber":self.history[i+l],"confidence":100-diff*10})
                if len(matches)>=max_results: break
        return matches

    def weighted(self, matches):
        if not matches: return None
        w={}; total=0
        for idx,m in enumerate(matches):
            pos_w=1+1/(idx+1)
            conf_w=(m.get("confidence",100))/100
            weight=pos_w*conf_w
            w[m["nextNumber"]]=w.get(m["nextNumber"],0)+weight
            total+=weight
        best=-1; bw=0
        for n,ww in w.items():
            if ww>bw: bw=ww; best=n
        return {"number":best,"confidence":min(99,(bw/total)*100) if total else 0}

    def markov(self, live):
        if len(live)<3: return None
        last3=live[-3:]; last2=live[-2:]; last1=[live[-1]]
        m3=self.find_exact_matches(last3,20)
        if m3:
            r=self.weighted(m3)
            if r and r["confidence"]>70: return {**r,"method":"MARKOV_3"}
        m2=self.find_exact_matches(last2,20)
        if m2:
            r=self.weighted(m2)
            if r and r["confidence"]>65: return {**r,"method":"MARKOV_2"}
        m1=self.find_exact_matches(last1,30)
        if m1:
            r=self.weighted(m1)
            if r: return {**r,"method":"MARKOV_1"}
        return None

    def trend(self, live):
        if len(live)<3: return None
        streak=1; dir_='BIG' if live[-1]>=5 else 'SMALL'
        for i in range(len(live)-2,-1,-1):
            if ('BIG' if live[i]>=5 else 'SMALL')==dir_:
                streak+=1
            else: break
        if streak>=2:
            od='SMALL' if dir_=='BIG' else 'BIG'
            pool=[8,9,7,6] if od=='BIG' else [1,2,3,4]
            return {"number":pool[0],"confidence":min(95,75+streak*3),"method":"TREND_BREAKER"}
        return None

    def cycle(self, live):
        if len(live)<6: return None
        l6=live[-6:]
        if l6[0]==l6[3] and l6[1]==l6[4] and l6[2]==l6[5]:
            return {"number":l6[2],"confidence":85,"method":"CYCLE_3"}
        if len(live)>=8:
            l8=live[-8:]
            ok=True
            for i in range(4):
                if l8[i]!=l8[i+4]: ok=False; break
            if ok: return {"number":l8[3],"confidence":88,"method":"CYCLE_4"}
        return None

    def neural(self, live):
        if len(live)<5: return None
        key=''.join(map(str,live[-5:]))
        mapping={
            '12345':6,'23456':7,'34567':8,'45678':9,'56789':0,
            '98765':4,'87654':3,'76543':2,'65432':1,'54321':0,
            '13579':2,'97531':8,'24680':5,'80246':1,'11223':4,
            '99887':6,'55443':2,'33221':0,'77665':8,'44112':9
        }
        if key in mapping:
            return {"number":mapping[key],"confidence":92,"method":"NEURAL_PATTERN"}
        return None

    def frequency(self, live, win=500):
        r=self.history[-win:]
        f=[0]*10
        for n in r: f[n]+=1
        for i in range(min(20,len(live))):
            n=live[i]
            if 0<=n<=9: f[n]=max(0,f[n]-2)
        mf=-1; best=0
        for i in range(10):
            if f[i]>mf: mf=f[i]; best=i
        conf=min(85,60+(mf/(len(r)/10))*30) if r else 60
        return {"number":best,"confidence":conf,"method":"FREQUENCY"}

    def predict(self, api_list):
        if not api_list:
            return {"predictedNumber":8,"predictedSize":"BIG","partnerNumber":3,"score":85,"logic":"SUKUNA","label":"🐉 Sukuna default"}
        live=self.get_live_pattern(api_list,20)
        preds=[]
        for length in range(min(len(live),15),2,-1):
            sp=live[-length:]
            m=self.find_exact_matches(sp,50)
            if m:
                r=self.weighted(m)
                if r and r["confidence"]>80:
                    preds.append({"number":r["number"],"confidence":r["confidence"],"method":f"EXACT_{length}"}); break
        if not preds:
            for length in range(min(len(live),10),2,-1):
                sp=live[-length:]
                m=self.find_fuzzy_matches(sp,1,30)
                if m:
                    r=self.weighted(m)
                    if r and r["confidence"]>70:
                        preds.append({"number":r["number"],"confidence":r["confidence"],"method":f"FUZZY_{length}"}); break
        mk=self.markov(live); 
        if mk and mk["confidence"]>70: preds.append(mk)
        tr=self.trend(live);
        if tr and tr["confidence"]>70: preds.append(tr)
        cy=self.cycle(live);
        if cy and cy["confidence"]>75: preds.append(cy)
        nn=self.neural(live);
        if nn and nn["confidence"]>80: preds.append(nn)
        fr=self.frequency(live);
        if fr and fr["confidence"]>65: preds.append(fr)

        votes=[0]*10; totalC=0
        for p in preds:
            w=p["confidence"]/100
            votes[p["number"]]+=w
            totalC+=w
        best=8; bs=0
        for i in range(10):
            if votes[i]>bs: bs=votes[i]; best=i
        conf=(bs/totalC)*100 if totalC>0 else 70
        if any(p.get("method","").startswith("EXACT") for p in preds): conf+=10
        if any(p.get("confidence",0)>85 for p in preds): conf+=5
        if len(preds)>=3: conf+=5
        conf=min(99,max(70,conf))

        second=-1; sb=-1
        for i in range(10):
            if i!=best and votes[i]>sb: sb=votes[i]; second=i
        if second<0:
            second=8 if best==9 else best+1 if best>=5 else 1 if best==0 else best+1

        return {"predictedNumber":best,"predictedSize":'BIG' if best>=5 else 'SMALL',"partnerNumber":second,"score":round(conf),"logic":"SUKUNA","label":f"🐉 Sukuna v16 — {len(preds)} layers"}

# ============ ENGINE 4: SHINCHAN v5.4 ============
class ShinchanEngine:
    def __init__(self):
        self.active_strategy=1

    def predict(self, current_period_str, history_numbers):
        period_str=str(current_period_str or '1000')
        digits=[int(c) for c in period_str if c.isdigit()]
        if not digits: digits=[1]
        s=sum(digits)
        tail=digits[-1]
        hist=(history_numbers or [])[:5]
        if len(hist)>=5:
            history_score=sum(val*(5-idx) for idx,val in enumerate(hist))
        else:
            history_score=s*3
        strat_factor=11 if self.active_strategy==1 else 7 if self.active_strategy==2 else 13
        calculated_index=(s*5 + tail*7 + history_score*strat_factor) % 20
        type_='BIG' if (calculated_index%2==0 or s%2==1) else 'SMALL'
        if type_=='BIG':
            big_pool=[5,6,7,8,9]
            i1=(s+self.active_strategy)%len(big_pool)
            i2=(history_score+2)%len(big_pool)
            if i1==i2: i2=(i2+1)%len(big_pool)
            n1=big_pool[i1]; n2=big_pool[i2]
        else:
            small_pool=[0,1,2,3,4]
            i1=(s+self.active_strategy)%len(small_pool)
            i2=(history_score+1)%len(small_pool)
            if i1==i2: i2=(i2+1)%len(small_pool)
            n1=small_pool[i1]; n2=small_pool[i2]
        conf=96.2 + (abs(history_score)%3.5)
        if conf>99.8: conf=99.5
        return {"predictedNumber":n1,"partnerNumber":n2,"predictedSize":type_,"score":round(conf),"logic":"SHINCHAN","label":f"🛡️ Shinchan Stable v5.4 — sum {s} · tail {tail}"}

# ============ HYBRID COMBINER ============
def combine_hybrid(kingg, mohit, sukuna, shinchan):
    votes={"BIG":0,"SMALL":0}
    votes[kingg["predictedSize"]]+=1.5 if kingg.get("forcedReverse") else 1.0
    votes[mohit["predictedSize"]]+=0.8
    votes[sukuna["predictedSize"]]+=1.0
    votes[shinchan["predictedSize"]]+=1.0

    final_size='BIG' if votes["BIG"]>=votes["SMALL"] else 'SMALL'
    agreement = kingg["predictedSize"]==mohit["predictedSize"]==sukuna["predictedSize"]==shinchan["predictedSize"]

    final_number=sukuna["predictedNumber"]
    if (final_number>=5 and final_size!='BIG') or (final_number<5 and final_size!='SMALL'):
        if (shinchan["predictedNumber"]>=5 and final_size=='BIG') or (shinchan["predictedNumber"]<5 and final_size=='SMALL'):
            final_number=shinchan["predictedNumber"]
        elif (kingg["predictedNumber"]>=5 and final_size=='BIG') or (kingg["predictedNumber"]<5 and final_size=='SMALL'):
            final_number=kingg["predictedNumber"]
        else:
            final_number=8 if final_size=='BIG' else 1

    all_nums=set()
    for n in [sukuna["predictedNumber"],sukuna.get("partnerNumber"),shinchan["predictedNumber"],shinchan.get("partnerNumber"),kingg["predictedNumber"],kingg.get("partnerNumber"),mohit["predictedNumber"],mohit.get("partnerNumber")]:
        if n is not None and isinstance(n,int) and 0<=n<=9:
            all_nums.add(n)
    balls=list(all_nums)

    partner=sukuna.get("partnerNumber")
    if partner==final_number or ((partner>=5 and final_size!='BIG') or (partner<5 and final_size!='SMALL')):
        for n in balls:
            if n!=final_number and ((n>=5 and final_size=='BIG') or (n<5 and final_size=='SMALL')):
                partner=n; break
        if partner is None or partner==final_number:
            partner=9 if final_size=='BIG' else 2

    score=round((kingg["score"]*0.28)+(mohit["score"]*0.12)+(sukuna["score"]*0.30)+(shinchan["score"]*0.30))
    if agreement: score=min(97,score+8)
    else: score=max(55,score-4)

    return {
        "predictedNumber":final_number,"predictedSize":final_size,"partnerNumber":partner,
        "balls":balls,"score":score,"agreement":agreement,
        "kinggSize":kingg["predictedSize"],"mohitSize":mohit["predictedSize"],
        "sukunaSize":sukuna["predictedSize"],"shinchanSize":shinchan["predictedSize"],
        "kinggScore":kingg["score"],"sukunaScore":sukuna["score"],"shinchanScore":shinchan["score"],
        "logic":"HYBRID","label": "⚡ Hybrid ALL — 4/4 engines AGREE" if agreement else f"⚡ Hybrid ALL — vote {votes['BIG']:.1f}B / {votes['SMALL']:.1f}S",
        "vote":votes
    }

# ============ TELEGRAM SENDER ============
def send_telegram_message(text, send_sticker=False):
    if TELEGRAM_BOT_TOKEN=="YOUR_BOT_TOKEN_HERE" or not TELEGRAM_BOT_TOKEN:
        print("[SKIP] Telegram token not set or default.", flush=True)
        return False
    try:
        if send_sticker and CUSTOM_STICKER_FILE_ID:
            try:
                url=f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendSticker"
                r_stk = requests.post(url, json={"chat_id":TELEGRAM_CHANNEL_ID,"sticker":CUSTOM_STICKER_FILE_ID}, timeout=10)
                print(f"[TG STICKER] Status: {r_stk.status_code}", flush=True)
            except Exception as e:
                print("Sticker error:", e, flush=True)

        url=f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload={"chat_id":TELEGRAM_CHANNEL_ID,"text":text,"parse_mode":"Markdown"}
        r=requests.post(url, json=payload, timeout=10)
        if r.status_code!=200:
            print("Telegram error response:", r.text, flush=True)
            return False
        print("[TG SENT] Message delivered successfully.", flush=True)
        return True
    except Exception as e:
        print("Telegram send error exception:", e, flush=True)
        return False

# ============ API FETCH ============
def fetch_wingo_history():
    segment = "WinGo_30S" if WINGO_TYPE=="30S" else "WinGo_1M"
    url=f"https://draw.ar-lottery01.com/WinGo/{segment}/GetHistoryIssuePage.json?ts={int(time.time()*1000)}"
    try:
        res=requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
        data=res.json()
        lst=data.get('data',{}).get('list',[])
        if lst:
            return lst
    except Exception as e:
        print("API fetch error:", e, flush=True)
    return None

def get_ist_time():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

# ============ BUILD RICH MESSAGES ============
def build_prediction_message(next_issue, result):
    B=to_bold
    short_issue = str(next_issue)[-5:]
    full_issue = str(next_issue)
    size = result["predictedSize"]
    n1 = result["predictedNumber"]
    n2 = result["partnerNumber"]
    balls = result.get("balls", [n1,n2,9,7])
    if len(balls)<4:
        extra=[9,7,8,2]
        for ex in extra:
            if ex not in balls and len(balls)<4:
                balls.append(ex)
    balls_str = '‚ '.join(B(str(b)) for b in balls[:4])

    vote = result.get("vote", {"BIG":0,"SMALL":0})
    breakdown = f"{B('KINGG')}:{B(result.get('kinggSize','-'))} | {B('MOHIT')}:{B(result.get('mohitSize','-'))} | {B('SUKUNA')}:{B(result.get('sukunaSize','-'))} | {B('SHINCHAN')}:{B(result.get('shinchanSize','-'))}"

    conf = result["score"]
    conf_bar = "🟩" * (conf//20) + "⬜" * (5 - conf//20)

    msg = (
        f"••••••••••••••••••••••••••••••••••••\n"
        f"🎮 {B('BY GAMEGURU.AI')} {B('PRO MAX')}\n"
        f"🚀 {B('WINGO')} {B(WINGO_TYPE)} {B('PREDICTION')}\n"
        f"      ———————————--------\n"
        f"{B('ISSUE')}  ➜ {B(short_issue)} ({full_issue[-6:]})\n"
        f"🎯 {B('TARGET')} ➜  {B(size)}\n"
        f"🔢 {B('NUMBERS')} ➜ {B(str(n1))} , {B(str(n2))}\n"
        f"🎱 {B('BALLS')} ➜ {balls_str}\n"
        f"🖥️ {B('SERVER')} ➜ {B('HYBRID ALL 4 ENGINES')}\n"
        f"📊 {B('CONF')} ➜ {B(str(conf)+'%')} {conf_bar}\n"
        f"🧠 {B('ENGINES')} ➜ {vote['BIG']:.1f}𝗕 / {vote['SMALL']:.1f}𝗦\n"
        f"      {breakdown}\n"
        f"      ———————————---------\n"
        f"🔥 {B('GIVE REACTION FOR MORE WINNING')}\n"
        f"👑 {B('OWNER')}:-@wingoman_chat_support_bot\n"
        f"•••••••••••••••••••••••••••••••••••••"
    )
    return msg

def build_win_message(target_issue, stats):
    B=to_bold
    acc = round((stats['wins']/stats['totalBets']*100)) if stats['totalBets'] else 0
    msg = (
        f"✅ {B('PERIOD')} {B(str(target_issue)[-5:])} {B('WIN')}\n\n"
        f"🔥 {B('Win Streak')}: {stats['consecutiveWin']}\n"
        f"🏆 {B('Highest Win Streak')}: {stats['highestWinStreak']}\n"
        f"📊 {B('Accuracy')}: {acc}% ({stats['wins']}W/{stats['totalBets']})\n"
        f"🎯 {B('Total Wins')}: {stats['wins']}"
    )
    return msg

def build_loss_message(target_issue, stats):
    B=to_bold
    acc = round((stats['wins']/stats['totalBets']*100)) if stats['totalBets'] else 0
    msg = (
        f"❌ {B('PERIOD')} {B(str(target_issue)[-5:])} {B('LOSS')}\n\n"
        f"❄️ {B('Loss Streak')}: {stats['consecutiveLoss']}\n"
        f"📊 {B('Accuracy')}: {acc}% ({stats['wins']}W/{stats['totalBets']})\n"
        f"🔄 {B('Next will be REVERSE')}"
    )
    return msg

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
            lst = fetch_wingo_history()
            if not lst:
                print("[WORKER] Waiting for history data...", flush=True)
                time.sleep(POLL_INTERVAL)
                continue

            latest = lst[0]
            current_issue = str(latest.get('issueNumber') or latest.get('issue') or latest.get('periodNumber'))
            try:
                actual_num = int(latest.get('number', 0))
            except:
                actual_num = 0
            actual_size = "BIG" if actual_num>=5 else "SMALL"

            # Step 1: Settle
            if active_prediction and current_issue == active_prediction['target_issue']:
                is_win = (actual_size == active_prediction['size']) or (actual_num == active_prediction['number'])
                bot_stats['totalBets']+=1
                if is_win:
                    bot_stats['wins']+=1
                    bot_stats['consecutiveWin']+=1
                    bot_stats['consecutiveLoss']=0
                    if bot_stats['consecutiveWin'] > bot_stats['highestWinStreak']:
                        bot_stats['highestWinStreak']=bot_stats['consecutiveWin']
                    win_msg = build_win_message(active_prediction['target_issue'], bot_stats)
                    send_telegram_message(win_msg, send_sticker=True)
                else:
                    bot_stats['losses']+=1
                    bot_stats['consecutiveLoss']+=1
                    bot_stats['consecutiveWin']=0
                    loss_msg = build_loss_message(active_prediction['target_issue'], bot_stats)
                    send_telegram_message(loss_msg, send_sticker=False)
                active_prediction=None
                kingg.consecutiveLoss = bot_stats['consecutiveLoss']
                kingg.consecutiveWin = bot_stats['consecutiveWin']
                if not is_win:
                    kingg.lastLossSize = actual_size
                else:
                    kingg.lastLossSize = None

            # Step 2: New prediction
            if current_issue != last_processed_issue:
                last_processed_issue=current_issue
                try:
                    next_issue=str(int(current_issue)+1)
                except:
                    next_issue=str(int(time.time()))

                numbers=[int(item.get('number',0)) for item in lst[:20]]

                kingg_pred = kingg.predict(numbers)
                mohit_pred = mohit.predict(current_issue, numbers)
                sukuna_pred = sukuna.predict(numbers)
                shinchan_pred = shinchan.predict(next_issue, numbers)

                hybrid_result = combine_hybrid(kingg_pred, mohit_pred, sukuna_pred, shinchan_pred)

                msg = build_prediction_message(next_issue, hybrid_result)
                print(f"[GENERATED] Sending prediction for issue {next_issue}...", flush=True)
                send_telegram_message(msg, send_sticker=False)

                active_prediction={
                    "target_issue": next_issue,
                    "size": hybrid_result["predictedSize"],
                    "number": hybrid_result["predictedNumber"]
                }

        except Exception as e:
            print("Background worker loop error:", e, flush=True)

        time.sleep(POLL_INTERVAL)

# ============ FLASK ROUTES (Supports GET & HEAD for UptimeRobot) ============
@app.route('/', methods=['GET', 'HEAD'])
def index():
    return jsonify({
        "status": "GAMEGURU.AI PRO MAX running",
        "wingo_type": WINGO_TYPE,
        "stats": bot_stats,
        "time_ist": get_ist_time().isoformat()
    })

@app.route('/stats', methods=['GET', 'HEAD'])
def stats_route():
    return jsonify(bot_stats)

# ============ AUTO-START BACKGROUND THREAD ON MODULE IMPORT ============
def start_worker():
    t = threading.Thread(target=automated_bot_worker, daemon=True)
    t.start()
    print("[INIT] Background prediction worker thread started successfully.", flush=True)

start_worker()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, use_reloader=False)
