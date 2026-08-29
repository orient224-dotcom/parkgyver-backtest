import os
import requests
import json
import datetime
import time
import threading
import calendar

# ==============================================================================
# 🔐 1. 보안 환경변수 로드 (깃허브 Secrets 연동)
# ==============================================================================
APP_KEY = os.environ.get("APP_KEY", "")
APP_SECRET = os.environ.get("APP_SECRET", "")
CANO = os.environ.get("CANO", "")
ACNT_PRDT_CD = os.environ.get("ACNT_PRDT_CD", "01")

# 구글 Gemini AI 키
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 텔레그램 무전망
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
URL_BASE = "https://openapi.koreainvestment.com:9443"

# 4대 정예 타깃 종목
TARGET_STOCKS = {
    "005930": {"name": "삼성전자", "drop_target": -3.0},
    "034020": {"name": "두산에너빌리티", "drop_target": -3.0},
    "047040": {"name": "대우건설", "drop_target": -3.0},
    "103590": {"name": "일진전기", "drop_target": -3.0}
}

# 전략 파라미터
TRAILING_START = 30.0   
TRAILING_DROP = -7.0    
EMERGENCY_CUT = -12.0   
MARKET_CRASH_LIMIT = -3.0 
ALLOCATION_PCT = 25.0   

STATE_FILE = "bot_state.json"
portfolio = {} 
free_stocks = {}       
locked_reserve = 0.0   
monthly_history = []
ACCESS_TOKEN = ""
token_date = ""

def save_state():
    state = {
        "portfolio": portfolio,
        "free_stocks": free_stocks,
        "locked_reserve": locked_reserve,
        "monthly_history": monthly_history
    }
    try:
        with open(STATE_FILE, "w", encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def load_state():
    global portfolio, free_stocks, locked_reserve, monthly_history
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding='utf-8') as f:
                state = json.load(f)
                portfolio = state.get("portfolio", {})
                free_stocks = state.get("free_stocks", {})
                locked_reserve = state.get("locked_reserve", 0.0)
                monthly_history = state.get("monthly_history", [])
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
        return
    headers = {"content-type": "application/json"}
    body = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}
    url = f"{URL_BASE}/oauth2/tokenP"
    try:
        res = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
        ACCESS_TOKEN = res.json().get("access_token")
        token_date = datetime.datetime.now().strftime("%Y%m%d")
    except Exception:
        pass

def get_account_status():
    if not ACCESS_TOKEN:
        return 0, 0
    url = f"{URL_BASE}/uapi/domestic-stock/v1/trading/inquire-balance"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "TTTC8434R"
    }
    params = {
        "CANO": CANO, "ACNT_PRDT_CD": ACNT_PRDT_CD, "AFHR_FLPR_YN": "N",
        "OFL_YN": "", "INQR_DVSN": "02", "UNPR_DVSN": "01", "FUND_STTL_ICLD_YN": "N",
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

def get_current_price_and_rate(ticker):
    if not ACCESS_TOKEN:
        return None, None
    url = f"{URL_BASE}/uapi/domestic-stock/v1/quotations/inquire-price"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {ACCESS_TOKEN}",
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

def send_order(ticker, quantity, is_buy=True):
    if quantity <= 0 or not ACCESS_TOKEN:
        return
    url = f"{URL_BASE}/uapi/domestic-stock/v1/trading/order-cash"
    tr_id = "TTTC0802U" if is_buy else "TTTC0801U"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": tr_id
    }
    body = {
        "CANO": CANO, "ACNT_PRDT_CD": ACNT_PRDT_CD, "PDNO": ticker,
        "ORD_DVSN": "01", "ORD_QTY": str(quantity), "ORD_UNPR": "0"
    }
    try:
        requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
    except Exception:
        pass

def get_kospi_rate():
    try:
        url = "https://m.stock.naver.com/api/index/KOSPI/basic"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5).json()
        return float(res['fluctuationsRatio'])
    except Exception:
        return 0.0

def generate_monthly_report():
    tot, cash = get_account_status()
    now = datetime.datetime.now()
    report = f"📜 [{now.month}월 박가이버 사령부 결산서]\n👑 총자산: {format_money(tot)}원\n\n"
    if not monthly_history:
        report += "이번 달 완료된 청산 내역이 없습니다."
    else:
        wins = [x for x in monthly_history if x['type'] == '익절']
        losses = [x for x in monthly_history if x['type'] == '손절']
        win_rate = (len(wins) / len(monthly_history)) * 100
        tot_ret = sum(x['ret'] for x in monthly_history)
        report += f"전투: {len(monthly_history)}회 ({len(wins)}승 {len(losses)}패 / 승률 {win_rate:.1f}%)\n누적 수익률: {tot_ret:+.2f}%\n"
    return report

def ask_gemini_strategy_report():
    if not GEMINI_API_KEY:
        return "⚠️ GEMINI_API_KEY 환경변수가 설정되지 않았습니다."
    tot, cash = get_account_status()
    current_stocks = ", ".join([conf['name'] for conf in TARGET_STOCKS.values()])
    history_summary = "\n".join([f"- {h['date']} {h['name']}: {h['type']} ({h['ret']:+.1f}%)" for h in monthly_history[-5:]]) or "최근 매매 기록 없음"
    
    prompt = f"""
당신은 '박가이버 사령부'의 수석 전략 참모(AI CSO)입니다.
사령관(박가이버님)께 이번 달 운용 결과 진단과 다음 달 종목 교체/유지 권고안을 텔레그램 형식으로 간결하게 브리핑하세요.

[사령부 현황]
- 총자산: {tot:,}원 (가용예수금: {cash:,}원)
- 현재 4대 타깃 종목: {current_stocks}
- 사령부 전략: 종가 -3% 매수, +30% 레이더/-7% 익절, -12% 손절, 코스피 -3% 킬스위치
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
        if "error" in list_res:
            return f"⚠️ API 인증 에러: {list_res['error'].get('message')}"
        
        available_models = [m["name"] for m in list_res.get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
        
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        last_err = ""
        for m_name in available_models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/{m_name}:generateContent?key={GEMINI_API_KEY}"
                res = requests.post(url, headers=headers, json=payload, timeout=20).json()
                if "candidates" in res and res["candidates"]:
                    return res['candidates'][0]['content']['parts'][0]['text']
            except Exception as e:
                last_err = str(e)
                continue
        return f"⚠️ AI 참모 통신 연결 실패: {last_err}"
    except Exception as e:
        return f"⚠️ 시스템 오류: {e}"

# ==============================================================================
# 📡 2. 텔레그램 양방향 무전기
# ==============================================================================
def handle_commands():
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
                    
                    if msg in ["상태", "현황", "요원", "요원현황", "보유", "보유요원", "잔고"]:
                        tot, cash = get_account_status()
                        report = (f"📊 [사령부 실시간 현황]\n👑 총자산: {format_money(tot)}원\n💵 가용예수금: {format_money(cash)}원\n🛡️ 잠금 비상금: {format_money(locked_reserve)}원\n\n[⚔️ 실전 파견 요원]")
                        if portfolio:
                            for t, d in portfolio.items():
                                cur, _ = get_current_price_and_rate(t)
                                cur = cur or d['entry_price']
                                r = ((cur - d['entry_price']) / d['entry_price']) * 100
                                report += f"\n- {TARGET_STOCKS[t]['name']}: {d['quantity']}주 ({r:+.2f}%)"
                        else:
                            report += "\n- 파견 요원 없음 (전원 안전 현금 대기 중)"
                        if free_stocks:
                            report += "\n\n[🎁 공짜주식 보관함]"
                            for t, qty in free_stocks.items():
                                report += f"\n- {TARGET_STOCKS[t]['name']}: {qty}주"
                        send_telegram(report)
                        
                    elif msg in ["타점", "스캔", "대기", "대기요원", "정찰", "출격대기"]:
                        scan_rep = "🎯 [4종목 출격 대기 요원 타점]\n"
                        for t, conf in TARGET_STOCKS.items():
                            cur, rate = get_current_price_and_rate(t)
                            if rate is not None:
                                state = "🎯 충족 (오후 3:19 출격 준비)" if rate <= conf['drop_target'] else f"⚪ 관망 (기준까지 {rate - conf['drop_target']:+.2f}%p)"
                                scan_rep += f"- {conf['name']}: {rate:+.2f}% ({state})\n"
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
                        help_msg = (
                            "🤖 [박가이버 사령부 무전 사전]\n"
                            "1. /상태 : 자산 및 보유 종목\n"
                            "2. /타점 : 출격 대기 스캔\n"
                            "3. /AI진단 : AI 참모 종목 진단\n"
                            "4. /뉴스 종목명 : 최신 뉴스\n"
                            "5. /월말결산 : 전투 정산서"
                        )
                        send_telegram(help_msg)
                        
                    elif raw_msg.startswith("/뉴스") or raw_msg.startswith("뉴스"):
                        parts = raw_msg.split()
                        if len(parts) >= 2:
                            name = parts[1]
                            ticker = next((t for t, conf in TARGET_STOCKS.items() if conf['name'] == name), None)
                            if ticker:
                                try:
                                    n_url = f"https://m.stock.naver.com/api/news/stock/{ticker}?pageSize=3"
                                    n_res = requests.get(n_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5).json()
                                    n_msg = f"📰 [{name} 최신 뉴스 요약]\n"
                                    for n in n_res:
                                        title = n.get('tit', n.get('title', '제목 없음')).replace('&quot;', '"')
                                        n_msg += f"▪️ {title}\n"
                                    send_telegram(n_msg)
                                except Exception:
                                    send_telegram("⚠️ 뉴스 정찰 중 통신 장애 발생")
                            else:
                                send_telegram(f"⚠️ '{name}' 요원은 현재 타깃에 없습니다.")
                        else:
                            send_telegram("💡 사용법: /뉴스 일진전기")
        except Exception:
            time.sleep(5)
        time.sleep(1)

# ==============================================================================
# ⚔️ 3. 메인 감시 엔진
# ==============================================================================
if __name__ == "__main__":
    load_state() 
    print("🚀 박가이버 사령부 V3.3.3 (GitHub Secrets 연동 완료판) 시작")
    issue_token()

    threading.Thread(target=handle_commands, daemon=True).start()
    send_telegram("📡 [박가이버 사령부] 관제탑 업데이트 완료! 보안 환경변수 연동 완료.")

    market_closed_msg_sent = False
    monthly_report_sent_month = -1
    last_heartbeat_hour = -1

    while True:
        now = datetime.datetime.now()
        today_str = now.strftime("%Y%m%d")
        
        if now.weekday() < 5 and now.hour == 8 and now.minute == 40 and token_date != today_str:
            issue_token()
            send_telegram("🌅 [모닝 브리핑] 보안 출입증 자동 갱신 완료!")
            time.sleep(60)

        if now.weekday() < 5 and now.hour >= 9 and (now.hour < 15 or (now.hour == 15 and now.minute <= 30)):
            market_closed_msg_sent = False
            if now.hour in [10, 12, 14] and now.minute == 0 and last_heartbeat_hour != now.hour:
                send_telegram(f"💚 [생존 보고] {now.hour:02d}:00 기지국 이상 무! (잠금 비상금: {format_money(locked_reserve)}원)")
                last_heartbeat_hour = now.hour

            for ticker in list(portfolio.keys()):
                data = portfolio[ticker]
                name = TARGET_STOCKS.get(ticker, {}).get('name', ticker)
                price, _ = get_current_price_and_rate(ticker)
                if not price:
                    continue
                
                if price > data['max_price']:
                    portfolio[ticker]['max_price'] = price
                ret = ((price - data['entry_price']) / data['entry_price']) * 100
                pullback = ((price - portfolio[ticker]['max_price']) / portfolio[ticker]['max_price']) * 100
                
                if ret >= TRAILING_START and not data['trailing_active']:
                    portfolio[ticker]['trailing_active'] = True
                    save_state()
                    send_telegram(f"🚀 [레이더] {name} +{ret:.1f}% 돌파!")
                    
                if data['trailing_active'] and pullback <= TRAILING_DROP:
                    profit = (price - data['entry_price']) * data['quantity']
                    free_stock_budget = profit * 0.20
                    reserve_amt = profit * 0.20
                    free_qty = int(free_stock_budget // price)
                    sell_qty = data['quantity'] - free_qty
                    locked_reserve += reserve_amt 
                    
                    if free_qty > 0:
                        free_stocks[ticker] = free_stocks.get(ticker, 0) + free_qty
                        harvest_msg = (
                            f"🎯 [수확 완료] {name} 익절 (+{ret:.1f}%)\n"
                            f"💰 순수익: {format_money(profit)}원\n"
                            f"🛡️ 20% 비상금 잠금: +{format_money(reserve_amt)}원\n"
                            f"🎁 20% 공짜주식: {free_qty}주 영구 보관\n"
                            f"📈 60% 거름(재투자): 매도 대금 원금 합류 완료!"
                        )
                    else:
                        sell_qty = data['quantity']
                        harvest_msg = (
                            f"🎯 [수확 완료] {name} 익절 (+{ret:.1f}%)\n"
                            f"💰 순수익: {format_money(profit)}원\n"
                            f"🛡️ 20% 비상금 잠금: +{format_money(reserve_amt)}원\n"
                            f"⚠️ 20% 공짜주식 예산 부족으로 80% 거름(재투자) 일괄 합류 완료!"
                        )

                    send_order(ticker, sell_qty, is_buy=False)
                    send_telegram(harvest_msg)
                    monthly_history.append({'date': now.strftime("%m/%d"), 'name': name, 'ret': ret, 'type': '익절'})
                    del portfolio[ticker]
                    save_state()
                    continue
                    
                if ret <= EMERGENCY_CUT:
                    send_telegram(f"🚨 [비상탈출] {name} 손절 청산 ({ret:.1f}%)")
                    send_order(ticker, data['quantity'], is_buy=False)
                    monthly_history.append({'date': now.strftime("%m/%d"), 'name': name, 'ret': ret, 'type': '손절'})
                    del portfolio[ticker]
                    save_state()
                    
            if now.hour == 15 and now.minute == 19:
                kospi = get_kospi_rate()
                if kospi <= MARKET_CRASH_LIMIT:
                    send_telegram(f"🛡️ [강철 방패 가동] 코스피 {kospi:.2f}% 폭락! 굳게 문을 잠급니다.")
                else:
                    tot_asset, current_cash = get_account_status()
                    tradeable_asset = max(0, tot_asset - locked_reserve)
                    usable_cash = max(0, current_cash - locked_reserve)
                    send_telegram(f"🔍 [오후 3:19] 타점 스캔\n(운용 가능 자산: {format_money(tradeable_asset)}원 / 잠긴 비상금: {format_money(locked_reserve)}원)")
                    for ticker, conf in TARGET_STOCKS.items():
                        if ticker not in portfolio:
                            price, rate = get_current_price_and_rate(ticker)
                            if rate is not None and rate <= conf['drop_target']:
                                budget = tradeable_asset * (ALLOCATION_PCT / 100.0)
                                qty = min(int(budget // price), int(usable_cash // price))
                                if qty > 0:
                                    send_order(ticker, qty, is_buy=True)
                                    send_telegram(f"⚔️ [출격] {conf['name']} {qty}주 매수! (단가: {format_money(price)}원)")
                                    portfolio[ticker] = {
                                        'entry_price': price,
                                        'max_price': price,
                                        'quantity': qty,
                                        'trailing_active': False
                                    }
                                    usable_cash -= (qty * price)
                                    save_state()
                time.sleep(60)
            time.sleep(60)
            
        else:
            if not market_closed_msg_sent and now.weekday() < 5 and now.hour == 15 and now.minute > 30:
                end_asset, end_cash = get_account_status()
                send_telegram(f"🌙 [정규장 마감]\n👑 총자산: {format_money(end_asset)}원\n오늘 하루도 고생 많으셨습니다!")
                market_closed_msg_sent = True
                
                last_day = calendar.monthrange(now.year, now.month)[1]
                if now.day >= (last_day - 3) and monthly_report_sent_month != now.month:
                    tomorrow = now + datetime.timedelta(days=1)
                    if tomorrow.month != now.month or (now.weekday() == 4 and (now + datetime.timedelta(days=3)).month != now.month):
                        send_telegram(generate_monthly_report())
                        send_telegram("🧠 [AI 수석 참모 월말 전략 브리핑]\n" + ask_gemini_strategy_report())
                        monthly_report_sent_month = now.month
                        monthly_history.clear()
                        save_state()
            time.sleep(600)
