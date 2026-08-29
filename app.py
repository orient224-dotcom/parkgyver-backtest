import streamlit as st
import requests
import json
import datetime
import time
import threading
import calendar
import os

# ==============================================================================
# 📱 1. 사령부 관제탑 모바일 최적화 설정
# ==============================================================================
st.set_page_config(page_title="박가이버 사령부", page_icon="🎖️", layout="centered")

st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    h1, h2, h3, h4 { margin-bottom: 0.3rem; }
    .stMetric { padding-bottom: 0.5rem; }
    div[data-testid="stMetricValue"] { font-size: 1.4rem; }
    </style>
""", unsafe_allow_html=True)

def get_secret(key, default=""):
    try:
        if key in st.secrets: return str(st.secrets[key])
    except: pass
    return os.environ.get(key, default)

APP_KEY = get_secret("APP_KEY")
APP_SECRET = get_secret("APP_SECRET")
CANO = get_secret("CANO", "44879076")
ACNT_PRDT_CD = get_secret("ACNT_PRDT_CD", "01")
GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
TELEGRAM_TOKEN = get_secret("TELEGRAM_TOKEN")
CHAT_ID = get_secret("CHAT_ID")
URL_BASE = "https://openapi.koreainvestment.com:9443"

TARGET_STOCKS = {
    "005930": {"name": "삼성전자", "drop_target": -3.0},
    "034020": {"name": "두산에너빌리티", "drop_target": -3.0},
    "047040": {"name": "대우건설", "drop_target": -3.0},
    "103590": {"name": "일진전기", "drop_target": -3.0}
}

TRAILING_START = 30.0   
TRAILING_DROP = -7.0    
EMERGENCY_CUT = -12.0   
MARKET_CRASH_LIMIT = -3.0 
ALLOCATION_PCT = 25.0   

STATE_FILE = "bot_state.json"
ACCESS_TOKEN = ""
token_date = ""

# ==============================================================================
# 💾 2. 사령부 통신 및 상태 관리 엔진
# ==============================================================================
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding='utf-8') as f: return json.load(f)
        except: pass
    return {"portfolio": {}, "free_stocks": {}, "locked_reserve": 0.0, "monthly_history": []}

def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding='utf-8') as f: json.dump(state, f, ensure_ascii=False, indent=4)
    except: pass

def format_money(num):
    try: return f"{int(round(float(num))):,}"
    except: return str(num)

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except: pass

def issue_token():
    global ACCESS_TOKEN, token_date
    if not APP_KEY or not APP_SECRET: return ""
    try:
        res = requests.post(f"{URL_BASE}/oauth2/tokenP", headers={"content-type": "application/json"}, data=json.dumps({"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}), timeout=10)
        token = res.json().get("access_token", "")
        ACCESS_TOKEN = token
        token_date = datetime.datetime.now().strftime("%Y%m%d")
        return token
    except: return ""

def get_account_status(token=None):
    tok = token or ACCESS_TOKEN or issue_token()
    if not tok: return 0, 0
    try:
        res = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/trading/inquire-balance", headers={"authorization": f"Bearer {tok}", "appkey": APP_KEY, "appsecret": APP_SECRET, "tr_id": "TTTC8434R"}, params={"CANO": CANO, "ACNT_PRDT_CD": ACNT_PRDT_CD, "AFHR_FLPR_YN": "N", "OFL_YN": "", "INQR_DVSN": "02", "UNPR_DVSN": "01", "FUND_STTL_ICLD_YN": "N", "FNCG_AMT_AUTO_RDPT_YN": "N", "PRCS_DVSN": "00", "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""}, timeout=10)
        out2 = res.json().get('output2', [{}])[0]
        return int(out2.get('tot_evlu_amt', 0)), int(out2.get('dnca_tot_amt', 0))
    except: return 0, 0

def get_current_price_and_rate(ticker, token=None):
    tok = token or ACCESS_TOKEN or issue_token()
    if not tok: return None, None
    try:
        res = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/quotations/inquire-price", headers={"authorization": f"Bearer {tok}", "appkey": APP_KEY, "appsecret": APP_SECRET, "tr_id": "FHKST01010100"}, params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": ticker}, timeout=5)
        out = res.json().get('output', {})
        if 'stck_prpr' in out: return float(out['stck_prpr']), float(out['prdy_ctrt'])
    except: pass
    return None, None

# 📰 뉴스 정찰 엔진 (다중 키 자동 감지 및 HTML 정제)
def get_stock_news(ticker):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        url = f"https://m.stock.naver.com/api/news/stock/{ticker}?pageSize=5"
        res = requests.get(url, headers=headers, timeout=5).json()
        
        items = res if isinstance(res, list) else res.get("items", res.get("itemList", []))
        news_list = []
        for n in items:
            title = n.get('title') or n.get('tit') or n.get('articleTitle') or n.get('subject') or n.get('body')
            if title:
                title = title.replace('&quot;', '"').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('<b>', '').replace('</b>', '')
                news_list.append(title)
        
        return news_list[:5] if news_list else ["최근 24시간 내 주요 뉴스가 없습니다."]
    except Exception:
        return ["뉴스 정찰 중 통신 지연이 발생했습니다."]

def get_kospi_rate():
    try:
        res = requests.get("https://m.stock.naver.com/api/index/KOSPI/basic", headers={"User-Agent": "Mozilla/5.0"}, timeout=5).json()
        return float(res['fluctuationsRatio'])
    except: return 0.0

def ask_gemini_strategy_report():
    if not GEMINI_API_KEY: return "⚠️ GEMINI_API_KEY 미설정"
    tot, cash = get_account_status()
    state = load_state()
    hist = "\n".join([f"- {h['date']} {h['name']}: {h['type']} ({h['ret']:+.1f}%)" for h in state.get("monthly_history", [])[-5:]]) or "기록 없음"
    stocks = ", ".join([v['name'] for v in TARGET_STOCKS.values()])
    prompt = f"박가이버 사령부의 AI CSO로서 4종목({stocks}) 진단, 메가트렌드 교체 후보 1~2종목 추천을 500자 이내로 텔레그램 양식 브리핑하라. 총자산:{tot:,}원\n기록:\n{hist}"
    
    try:
        avail = [m["name"] for m in requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}", timeout=10).json().get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
        for m_name in avail:
            try:
                res = requests.post(f"https://generativelanguage.googleapis.com/v1beta/{m_name}:generateContent?key={GEMINI_API_KEY}", headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=20).json()
                if "candidates" in res: return res['candidates'][0]['content']['parts'][0]['text']
            except: continue
        return "⚠️ 응답 실패"
    except Exception as e: return f"⚠️ 오류: {e}"

# ==============================================================================
# 🛰️ 3. 백그라운드 무전 데몬
# ==============================================================================
@st.cache_resource
def start_background_daemon():
    def telegram_command_loop():
        last_id = 0
        while True:
            try:
                if not TELEGRAM_TOKEN:
                    time.sleep(10)
                    continue
                res = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_id + 1}&timeout=30", timeout=35).json()
                if res.get("ok"):
                    for item in res.get("result", []):
                        last_id = item["update_id"]
                        msg = item.get("message", {}).get("text", "").strip().replace(" ", "").replace("/", "").upper()
                        sender = str(item.get("message", {}).get("chat", {}).get("id", ""))
                        if sender != CHAT_ID or not msg: continue
                        
                        if msg in ["상태", "현황"]:
                            t, c = get_account_status()
                            s = load_state()
                            rep = f"📊 [현황]\n총자산: {format_money(t)}원\n비상금: {format_money(s.get('locked_reserve', 0))}원"
                            send_telegram(rep)
                        elif msg in ["타점", "스캔"]:
                            scan = "🎯 [타점]\n"
                            for tk, cf in TARGET_STOCKS.items():
                                _, r = get_current_price_and_rate(tk)
                                scan += f"- {cf['name']}: {r:+.2f}%\n" if r is not None else ""
                            send_telegram(scan)
                        elif msg in ["AI진단"]:
                            send_telegram(f"📋 [AI 보고서]\n\n{ask_gemini_strategy_report()}")
                        elif msg.startswith("뉴스"):
                            parts = item.get("message", {}).get("text", "").split()
                            if len(parts) >= 2:
                                name = parts[1]
                                tk = next((k for k, v in TARGET_STOCKS.items() if v['name'] == name), None)
                                if tk:
                                    n_list = get_stock_news(tk)
                                    send_telegram(f"📰 [{name} 뉴스]\n" + "\n".join([f"▪️ {x}" for x in n_list[:3]]))
            except: time.sleep(5)
            time.sleep(1)
    t = threading.Thread(target=telegram_command_loop, daemon=True)
    t.start()
    return t

start_background_daemon()

# ==============================================================================
# 📱 4. 스마트폰 전용 탭(Tab) UI
# ==============================================================================
st.markdown("## 🎖️ 박가이버 사령부")
st.caption(f"기준: {datetime.datetime.now().strftime('%m-%d %H:%M')} | 📡 무전망 ONLINE")

token = ACCESS_TOKEN or issue_token()
tot_asset, avail_cash = get_account_status(token)
state = load_state()

tab1, tab2, tab3 = st.tabs(["🎯 타점스캔", "💼 자산·요원", "🧠 참모·뉴스"])

with tab1:
    col1, col2 = st.columns(2)
    col1.metric("👑 총 자산", f"{format_money(tot_asset)}원" if tot_asset else "조회 중")
    col2.metric("💵 예수금", f"{format_money(avail_cash)}원" if avail_cash else "조회 중")
    
    st.markdown("#### 🚨 4대 종목 타점")
    for ticker, conf in TARGET_STOCKS.items():
        price, rate = get_current_price_and_rate(ticker, token)
        if rate is not None:
            if rate <= conf['drop_target']:
                st.error(f"**{conf['name']}** 🎯 **출격 조건 충족**\n\n현재가: {int(price):,}원 (**{rate:+.2f}%**)")
            else:
                st.info(f"**{conf['name']}** ⚪ 관망 (필요: {rate - conf['drop_target']:+.2f}%p)\n\n현재가: {int(price):,}원 ({rate:+.2f}%)")
        else:
            st.warning(f"**{conf['name']}** : 장마감 대기")

with tab2:
    st.metric("🛡️ 잠금 비상금 (20%)", f"{format_money(state.get('locked_reserve', 0))}원")
    
    st.markdown("#### ⚔️ 파견 요원 (보유 중)")
    portfolio = state.get("portfolio", {})
    if portfolio:
        for t, d in portfolio.items():
            cur, _ = get_current_price_and_rate(t, token)
            cur = cur or d['entry_price']
            ret = ((cur - d['entry_price']) / d['entry_price']) * 100
            st.success(f"**{TARGET_STOCKS.get(t, {}).get('name', t)}** {d['quantity']}주\n\n단가 {int(d['entry_price']):,}원 ➔ 현재 {int(cur):,}원 (**{ret:+.2f}%**)")
    else:
        st.write("현금 대기 중인 요원만 있습니다.")
        
    st.markdown("#### 🎁 공짜주식 보관함")
    free_stocks = state.get("free_stocks", {})
    if free_stocks:
        for t, qty in free_stocks.items():
            st.warning(f"**{TARGET_STOCKS.get(t, {}).get('name', t)}** : {qty}주 보관 중")
    else:
        st.write("아직 수확된 과일이 없습니다.")

with tab3:
    st.markdown("#### 🧠 AI 참모 브리핑")
    if st.button("📋 브리핑 생성 및 텔레그램 발송", use_container_width=True):
        with st.spinner("AI가 분석 중입니다..."):
            rep = ask_gemini_strategy_report()
            st.success("발송 완료!")
            st.markdown(f"<div style='font-size:0.9rem; padding:10px; background:#f0f2f6; border-radius:5px;'>{rep}</div>", unsafe_allow_html=True)
            send_telegram(f"📋 [AI 수석 참모 전략 보고서]\n\n{rep}")

    st.markdown("---")
    st.markdown("#### 📰 종목별 긴급 뉴스")
    selected_stock = st.selectbox("정찰 종목 선택", list(TARGET_STOCKS.values()), format_func=lambda x: x["name"])
    selected_ticker = next(k for k, v in TARGET_STOCKS.items() if v["name"] == selected_stock["name"])
    
    if st.button("🔍 뉴스 스캔", use_container_width=True):
        with st.spinner("최신 뉴스 정찰 중..."):
            news = get_stock_news(selected_ticker)
            for n in news:
                st.markdown(f"▪️ {n}")
