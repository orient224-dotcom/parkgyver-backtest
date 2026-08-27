import streamlit as st
import requests
import json
import pandas as pd

# ==============================================================================
# 1. 페이지 레이아웃 설정
# ==============================================================================
st.set_page_config(page_title="박가이버 사령부 실전 관제탑", layout="wide", page_icon="📡")

# ==============================================================================
# 2. 통신 보안키 및 4종목 타깃 설정
# ==============================================================================
APP_KEY = "PSYQxdExos15R4GouvYt7sRAd7MgVW7Sh40O"
APP_SECRET = "H9Z0EktkYBp3xeQxEwyz7FEZGtS1CTSGxjKMMaAFh3Wg/xelongaLXWA9IeSZRqaAQFNUGlbv1VxmPhqw91EqqFCn6T3CfXz6iybBe89+BAfHowFa8pZFja9po31PErY0PZjBVpleSWehjvY2PJoA/eOGUgNAgXj01+/JOuBgDMe3Aa8pX8="
CANO = "44879076"
ACNT_PRDT_CD = "01"
URL_BASE = "https://openapi.koreainvestment.com:9443"

# 🎯 4종목 정예 타깃 (종목당 25% 배분)
TARGET_STOCKS = {
    "005930": {"name": "삼성전자", "drop_target": -3.0},
    "034020": {"name": "두산에너빌리티", "drop_target": -3.0},
    "047040": {"name": "대우건설", "drop_target": -3.0},
    "161890": {"name": "한국콜마", "drop_target": -3.0}
}

TRAILING_START = 30.0   # +30% 레이더 가동
EMERGENCY_CUT = -12.0   # -12% 비상 탈출

def format_money(num):
    try:
        return f"{int(round(float(num))):,}원"
    except:
        return str(num)

# ==============================================================================
# 3. 한투 API 통신 모듈
# ==============================================================================
@st.cache_data(ttl=60) # 1분 캐싱
def get_access_token():
    headers = {"content-type": "application/json"}
    body = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}
    url = f"{URL_BASE}/oauth2/tokenP"
    res = requests.post(url, headers=headers, data=json.dumps(body))
    return res.json().get("access_token")

def get_account_balance(token):
    url = f"{URL_BASE}/uapi/domestic-stock/v1/trading/inquire-balance"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY, "appsecret": APP_SECRET, "tr_id": "TTTC8434R"
    }
    params = {
        "CANO": CANO, "ACNT_PRDT_CD": ACNT_PRDT_CD, "AFHR_FLPR_YN": "N", "OFL_YN": "",
        "INQR_DVSN": "02", "UNPR_DVSN": "01", "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N", "PRCS_DVSN": "00", "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""
    }
    res = requests.get(url, headers=headers, params=params)
    if res.status_code == 200:
        data = res.json()
        return data.get('output2', [{}])[0], data.get('output1', [])
    return {}, []

def get_realtime_price(token, ticker):
    url = f"{URL_BASE}/uapi/domestic-stock/v1/quotations/inquire-price"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY, "appsecret": APP_SECRET, "tr_id": "FHKST01010100"
    }
    params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": ticker}
    res = requests.get(url, headers=headers, params=params)
    if res.status_code == 200:
        out = res.json()['output']
        return float(out['stck_prpr']), float(out['prdy_ctrt'])
    return 0.0, 0.0

# ==============================================================================
# 4. 실전 관제탑 대시보드 뷰
# ==============================================================================
st.markdown("<div style='background:#1b4f72;color:white;padding:12px 18px;border-radius:8px;margin-bottom:15px;display:flex;justify-content:space-between;align-items:center;'><h3 style='margin:0;'>📡 박가이버 사령부 실전 관제탑</h3><span>🟢 한국투자증권 실시간 연동 (4종목 체제)</span></div>", unsafe_allow_html=True)

if st.button("🔄 실시간 데이터 갱신", type="primary"):
    st.cache_data.clear()
    st.rerun()

token = get_access_token()

if token:
    summary, holdings = get_account_balance(token)
    tot_eval = float(summary.get('tot_evlu_amt', 0))
    dnca_cash = float(summary.get('dnca_tot_amt', 0))
    pnl_amt = float(summary.get('evlu_pfls_smtl_amt', 0))
    pnl_rate = ((pnl_amt / (tot_eval - pnl_amt)) * 100) if (tot_eval - pnl_amt) > 0 else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("👑 사령부 총자산", format_money(tot_eval))
    c2.metric("💵 가용 예수금", format_money(dnca_cash))
    c3.metric("📈 총 평가손익", format_money(pnl_amt), f"{pnl_rate:+.2f}%")

    st.markdown("---")

    # 1. 보유 종목 전황판
    st.subheader("🕵️ [실전 전장] 파견 요원 현황판")
    if holdings:
        active_list = []
        for h in holdings:
            name = h.get('prdt_name')
            code = h.get('pdno')
            qty = int(h.get('hld_qty', 0))
            buy_price = float(h.get('pchs_avg_pric', 0))
            cur_price = float(h.get('prpr', 0))
            profit_rate = float(h.get('evlu_pfls_rt', 0))
            profit_amt = float(h.get('evlu_pfls_amt', 0))
            
            radar_status = "🌌 레이더 가동 (+30% 돌파)" if profit_rate >= TRAILING_START else "⚔️ 전장 수색 중"
            if profit_rate <= EMERGENCY_CUT:
                radar_status = "🚨 비상 탈출 경보"

            active_list.append({
                "종목명": name,
                "종목코드": code,
                "보유수량": f"{qty}주",
                "매입평균가": format_money(buy_price),
                "현재가": format_money(cur_price),
                "평가손익": f"{format_money(profit_amt)} ({profit_rate:+.2f}%)",
                "전투 상태": radar_status
            })
        st.dataframe(pd.DataFrame(active_list), use_container_width=True)
    else:
        st.info("현재 파견된 요원이 없습니다. 전원 기지(현금 대기) 상태입니다.")

    st.markdown("---")

    # 2. 4종목 타점 레이더 (삼성전자, 두산에너빌리티, 대우건설, 한국콜마)
    st.subheader("🎯 [타점 레이더] 4종목 실시간 종가 스캔")
    radar_list = []
    for code, conf in TARGET_STOCKS.items():
        curr_price, daily_rate = get_realtime_price(token, code)
        is_in_pocket = any(h.get('pdno') == code for h in holdings)
        
        if is_in_pocket:
            signal = "🛡️ 이미 파견 중"
        elif daily_rate <= conf['drop_target']:
            signal = f"🎯 타점 포착! ({daily_rate:+.2f}%) ➔ 출격 대기"
        else:
            diff = daily_rate - conf['drop_target']
            signal = f"⚪ 관망 ({diff:+.2f}%p 여유)"

        radar_list.append({
            "종목명": conf['name'],
            "종목코드": code,
            "진입 기준 타점": f"{conf['drop_target']:.1f}%",
            "현재가": format_money(curr_price),
            "당일 실시간 등락률": f"{daily_rate:+.2f}%",
            "사령부 작전 신호": signal
        })

    st.dataframe(pd.DataFrame(radar_list), use_container_width=True)
else:
    st.error("한국투자증권 API 통신 토큰 발급에 실패했습니다.")
