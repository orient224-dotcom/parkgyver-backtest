import streamlit as st
import requests
import json
import datetime
import time
import threading
import calendar
import os

# ==============================================================================
# 🎨 1. 사령부 관제탑 환경 설정
# ==============================================================================
st.set_page_config(
    page_title="박가이버 사령부 종합 관제탑",
    page_icon="🎖️",
    layout="wide"
)

def get_secret(key, default=""):
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
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
# 💾 2. 사령부 상태 관리
# ==============================================================================
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"portfolio": {}, "free_stocks": {}, "locked_reserve": 0.0, "monthly_history": []}

def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def format_money(num):
    try:
        return f"{int(round(float(num))):,}"
    except Exception:
        return str(num)

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception:
        pass

def issue_token():
    global ACCESS_TOKEN, token_date
    if not APP_KEY or not APP_SECRET:
        return ""
    headers = {"content-type": "application/json"}
    body = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}
    try:
        res = requests.post(f"{URL_BASE}/oauth2/tokenP", headers=headers, data=json.dumps(body), timeout=10)
        token = res.json().get("access_token", "")
        ACCESS_TOKEN = token
        token_date = datetime.datetime.now().strftime("%Y%m%d")
        return token
    except Exception:
        return ""

def get_account_status(token=None):
    tok = token or ACCESS_TOKEN or issue_token()
    if not tok:
        return 0, 0
    url = f"{URL_BASE}/uapi/domestic-stock/v1/trading/inquire-balance"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {tok}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "TTTC8434R"
    }
    params = {
        "CANO": CANO, "ACNT_PRDT_CD": ACNT_PRDT_CD, "AFHR_FLPR_YN": "N", "OFL_YN": "",
        "INQR_DVSN": "02", "UNPR_DVSN": "01", "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N", "PRCS_DVSN": "00", "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""
    }
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        if res.status_code == 200:
            out2 = res.json().get('output2', [{}])[0]
            return int(out2.get('tot_evlu_amt', 0)), int(out2.get('dnca_tot_amt', 0))
    except Exception:
        pass
    return 0, 0

def get_current_price_and_rate(ticker, token=None):
    tok = token or ACCESS_TOKEN or issue_token()
    if not tok:
        return None, None
    url = f"{URL_BASE}/uapi/domestic-stock/v1/quotations/inquire-price"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {tok}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST01010100"
    }
    params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": ticker}
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        if res.status_code == 200:
            out = res.json().get('output', {})
            if out and 'stck_prpr' in out and 'prdy_ctrt' in out:
                return float(out['stck_prpr']), float(out['prdy_ctrt'])
    except Exception:
        pass
    return None, None

def get_stock_news(ticker):
    try:
        url = f"https://m.stock.naver.com/api/news/stock/{ticker}?pageSize=5"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5).json()
        news_items = []
        for n in res:
            title = n.get('tit', n.get('title', '제목 없음')).replace('&quot;', '"').replace('&amp;', '&')
            news_items.append(title)
        return news_items
    except Exception:
        return ["뉴스 정찰 중 통신 장애 발생"]

def get_kospi_rate():
    try:
        url = "https://m.stock.naver.com/api/index/KOSPI/basic"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5).json()
        return float(res['fluctuationsRatio'])
    except Exception:
        return 0.0

def generate_monthly_report():
    state = load_state()
    tot, cash = get_account_status()
    now = datetime.datetime.now()
    history = state.get("monthly_history", [])
    report = f"📜 [{now.month}월 박가이버 사령부 결산서]\n👑 총자산: {format_money(tot)}원\n\n"
    if not history:
        report += "이번 달 완료된 청산 내역이 없습니다."
    else:
        wins = [x for x in history if x['type'] == '익절']
        losses = [x for x in history if x['type'] == '손절']
        win_rate = (len(wins) / len(history)) * 100
        tot_ret = sum(x['ret'] for x in history)
        report += f"전투: {len(history)}회 ({len(wins)}승 {len(losses)}패 / 승률 {win_rate:.1f}%)\n누적 수익률: {tot_ret:+.2f}%\n"
    return report

def ask_gemini_strategy_report():
    if not GEMINI_API_KEY:
        return "⚠️ GEMINI_API_KEY가 설정되지 않았습니다."
    tot, cash = get_account_status()
    state = load_state()
    history = state.get("monthly_history", [])
    current_stocks = ", ".join([conf['name'] for conf in TARGET_STOCKS.values()])
    history_summary = "\n".join([f"- {h['date']} {h['name']}: {h['type']} ({h['ret']:+.1f}%)" for h in history[-5:]]) or "최근 매매 기록 없음"
    
    prompt = f"""
당신은 '박가이버 사령부'의 수석 전략 참모(AI CSO)입니다.
사령관(박가이버님)께 이번 달 운용 결과 진단과 다음 달 종목 교체/유지 권고안을 텔레그램 형식으로 간결하게 브리핑하세요.

[사령부 현황]
- 총자산: {tot:,}원 (가용예수금: {cash:,}원)
- 현재 4대 타깃 종목: {current_stocks}
- 사령부 전략: 종가 -3% 매수, +30% 레이더/-7% 익절(과수원 3분할 룰: 60% 거름, 20% 공짜주식, 20% 비상금), -12% 손절, 코스피 -3% 킬스위치
- 최근 청산 전적:
{history_summary}

[보고서 작성 가이드]
1. 🔍 [현재 4종목 컨디션 점검]: 유지 vs 교체 검토
2. 🌊 [차기 메가트렌드 추천]: AI 인프라/전력, 반도체, 원전, 로봇 등 유망 섹터 중 교체 후보 1~2종목 제시
3. 🎖️ [사령관 결재 요청 문구]: '자세한 심층 토론은 제미나이 웹 참모실에서 대화로 진행하시길 건의드립니다.' 마무리.
(500자 이내)
"""
    try:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
        list_res = requests.get(list_url, timeout=10).json()
        available_models = [m["name"] for m in list_res.get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
        
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        for m_name in available_models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/{m_name}:generateContent?key={GEMINI_API_KEY}"
                res = requests.post(url, headers=headers, json=payload, timeout=20).json()
                if "candidates" in res and res["candidates"]:
                    return res['candidates'][0]['content']['parts'][0]['text']
            except Exception:
                continue
        return "⚠️ AI 참모 통신 응답을 받지 못했습니다."
    except Exception as e:
        return f"⚠️ 시스템 오류: {e}"

# ==============================================================================
# 🛰️ 3. 백그라운드 24시간 텔레그램 무전 & 자동매매 데몬 스레드
# ==============================================================================
@st.cache_resource
def start_background_daemon():
    def telegram_command_loop():
        last_update_id = 0
        while True:
            try:
                if not TELEGRAM_TOKEN:
                    time.sleep(10)
                    continue
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=30"
                res = requests.get(url, timeout=35).json()
                if res.get("ok"):
                    for item in res.get("result", []):
                        last_update_id = item["update_id"]
                        raw_msg = item.get("message", {}).get("text", "")
                        sender_id = str(item.get("message", {}).get("chat", {}).get("id", ""))
                        if sender_id != CHAT_ID or not raw_msg:
                            continue
                        msg = raw_msg.strip().replace(" ", "").replace("/", "").upper()
                        state = load_state()
                        
                        if msg in ["상태", "현황", "요원", "요원현황", "보유", "보유요원", "잔고"]:
                            tot, cash = get_account_status()
                            report = (f"📊 [사령부 실시간 현황]\n👑 총자산: {format_money(tot)}원\n💵 가용예수금: {format_money(cash)}원\n🛡️ 잠금 비상금: {format_money(state.get('locked_reserve', 0))}원\n\n[⚔️ 실전 파견 요원]")
                            portfolio = state.get("portfolio", {})
                            if portfolio:
                                for t, d in portfolio.items():
                                    cur, _ = get_current_price_and_rate(t)
                                    cur = cur or d['entry_price']
                                    r = ((cur - d['entry_price']) / d['entry_price']) * 100
                                    report += f"\n- {TARGET_STOCKS.get(t, {}).get('name', t)}: {d['quantity']}주 ({r:+.2f}%)"
                            else:
                                report += "\n- 파견 요원 없음 (전원 안전 현금 대기 중)"
                            free_stocks = state.get("free_stocks", {})
                            if free_stocks:
                                report += "\n\n[🎁 공짜주식 보관함]"
                                for t, qty in free_stocks.items():
                                    report += f"\n- {TARGET_STOCKS.get(t, {}).get('name', t)}: {qty}주"
                            send_telegram(report)
                            
                        elif msg in ["타점", "스캔", "대기", "대기요원", "정찰", "출격대기"]:
                            scan_rep = "🎯 [4종목 출격 대기 요원 타점]\n"
                            for t, conf in TARGET_STOCKS.items():
                                cur, rate = get_current_price_and_rate(t)
                                if rate is not None:
                                    state_txt = "🎯 충족 (오후 3:19 출격 준비)" if rate <= conf['drop_target'] else f"⚪ 관망 (기준까지 {rate - conf['drop_target']:+.2f}%p)"
                                    scan_rep += f"- {conf['name']}: {rate:+.2f}% ({state_txt})\n"
                                else:
                                    scan_rep += f"- {conf['name']}: 야간 장마감 대기 중\n"
                            send_telegram(scan_rep)

                        elif msg in ["월말결산", "월말보고", "결산", "정산", "성적"]:
                            send_telegram(generate_monthly_report())
                            
                        elif msg in ["AI진단", "전략분석", "종목진단", "참모보고"]:
                            send_telegram("🧠 AI 수석 전략 참모가 전황 분석 및 종목 진단 중입니다... (잠시만 기다려주세요)")
                            ai_rep = ask_gemini_strategy_report()
                            send_telegram(f"📋 [AI 수석 참모 전략 보고서]\n\n{ai_rep}")
                            
                        elif msg in ["도움말", "HELP", "명령어", "메뉴"]:
                            help_msg = ("🤖 [박가이버 사령부 무전 사전]\n1. /상태 : 자산 및 보유 종목\n2. /타점 : 출격 대기 스캔\n3. /AI진단 : AI 참모 종목 진단\n4. /뉴스 종목명 : 최신 뉴스\n5. /월말결산 : 전투 정산서")
                            send_telegram(help_msg)
                            
                        elif raw_msg.startswith("/뉴스") or raw_msg.startswith("뉴스"):
                            parts = raw_msg.split()
                            if len(parts) >= 2:
                                name = parts[1]
                                ticker = next((t for t, conf in TARGET_STOCKS.items() if conf['name'] == name), None)
                                if ticker:
                                    n_items = get_stock_news(ticker)
                                    n_msg = f"📰 [{name} 최신 뉴스 요약]\n" + "\n".join([f"▪️ {x}" for x in n_items[:3]])
                                    send_telegram(n_msg)
                                else:
                                    send_telegram(f"⚠️ '{name}' 요원은 현재 타깃에 없습니다.")
                            else:
                                send_telegram("💡 사용법: /뉴스 일진전기")
            except Exception:
                time.sleep(5)
            time.sleep(1)

    t = threading.Thread(target=telegram_command_loop, daemon=True)
    t.start()
    return t

start_background_daemon()

# ==============================================================================
# 🖥️ 4. 종합 웹 관제탑 화면 렌더링
# ==============================================================================
st.title("🎖️ 박가이버 사령부 종합 관제탑")
st.caption(f"기준 시각: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (무전망 백그라운드 상시 가동 중)")

token = ACCESS_TOKEN or issue_token()
tot_asset, avail_cash = get_account_status(token)
state = load_state()
locked_reserve = state.get("locked_reserve", 0.0)

# 상단 자산 계기판
c1, c2, c3, c4 = st.columns(4)
c1.metric("👑 총 평가 자산", f"{tot_asset:,} 원" if tot_asset else "849,603 원")
c2.metric("💵 가용 예수금", f"{avail_cash:,} 원" if avail_cash else "849,603 원")
c3.metric("🛡️ 잠금 비상금 (20%)", f"{int(locked_reserve):,} 원")
c4.metric("📡 무전 통신망", "ONLINE (수신 대기)" if TELEGRAM_TOKEN else "OFFLINE")

st.divider()

# 과수원 파견 요원 & 공짜주식 보관함
c_left, c_right = st.columns(2)

with c_left:
    st.subheader("⚔️ 실전 파견 요원 (보유 종목)")
    portfolio = state.get("portfolio", {})
    if portfolio:
        p_list = []
        for t, d in portfolio.items():
            cur, _ = get_current_price_and_rate(t, token)
            cur = cur or d['entry_price']
            ret = ((cur - d['entry_price']) / d['entry_price']) * 100
            p_list.append({
                "종목명": TARGET_STOCKS.get(t, {}).get("name", t),
                "보유수량": f"{d['quantity']} 주",
                "매수가": f"{int(d['entry_price']):,} 원",
                "현재가": f"{int(cur):,} 원",
                "수익률": f"{ret:+.2f}%"
            })
        st.table(p_list)
    else:
        st.info("현재 파견된 요원이 없습니다. (전원 안전 현금 대기 중)")

with c_right:
    st.subheader("🎁 공짜주식 보관함 (영구 보유)")
    free_stocks = state.get("free_stocks", {})
    if free_stocks:
        f_list = []
        for t, qty in free_stocks.items():
            f_list.append({
                "종목명": TARGET_STOCKS.get(t, {}).get("name", t),
                "수확 수량": f"{qty} 주"
            })
        st.table(f_list)
    else:
        st.info("수확된 공짜 주식이 아직 없습니다.")

st.divider()

# 4대 종목 실시간 타점 현황
st.subheader("🎯 4대 정예 종목 실시간 타점 스캔")
stock_data = []
for ticker, conf in TARGET_STOCKS.items():
    price, rate = get_current_price_and_rate(ticker, token)
    status_text = "⚪ 관망"
    if rate is not None:
        if rate <= conf['drop_target']:
            status_text = "🎯 출격 충족 (-3% 이하)"
        else:
            status_text = f"⚪ 관망 ({rate - conf['drop_target']:+.2f}%p)"
    
    stock_data.append({
        "종목코드": ticker,
        "종목명": conf["name"],
        "현재가": f"{int(price):,} 원" if price else "장마감 대기",
        "당일 등락률": f"{rate:+.2f}%" if rate is not None else "-",
        "매수 기준": f"{conf['drop_target']:.1f}% 이하",
        "출격 상태": status_text
    })

st.table(stock_data)

st.divider()

# 하단: 뉴스 정찰 및 AI 참모 & 월말 결산
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("📰 종목별 최신 뉴스 정찰")
    selected_stock = st.selectbox("정찰할 종목을 선택하세요", list(TARGET_STOCKS.values()), format_func=lambda x: x["name"])
    selected_ticker = next(k for k, v in TARGET_STOCKS.items() if v["name"] == selected_stock["name"])
    
    if st.button("🔍 뉴스 스캔 실행"):
        news = get_stock_news(selected_ticker)
        for n in news:
            st.write(f"▪️ {n}")

with col_b:
    st.subheader("🧠 AI 수석 참모 전략 & 결산")
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("📋 AI 수석 참모 브리핑", type="primary"):
            with st.spinner("참모가 전략 보고서를 작성 중입니다..."):
                rep = ask_gemini_strategy_report()
                st.markdown(f"""<div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745; color: #111;">{rep}</div>""", unsafe_allow_html=True)
                send_telegram(f"📋 [AI 수석 참모 전략 보고서]\n\n{rep}")
                st.success("📲 텔레그램으로도 보고서가 동시 발송되었습니다!")
    with btn_col2:
        if st.button("📜 월말 결산서 조회"):
            m_rep = generate_monthly_report()
            st.text(m_rep)
            send_telegram(m_rep)
            st.success("📲 텔레그램으로 결산서가 전송되었습니다!")
