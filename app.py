import streamlit as st
import requests
import json
import datetime
import pandas as pd

# ==============================================================================
# 🌟 페이지 기본 설정
# ==============================================================================
st.set_page_config(
    page_title="박가이버 사령부 V3.1 종합 관제탑",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 🔐 보안 금고(Secrets) 호출
# ==============================================================================
APP_KEY = st.secrets["APP_KEY"]
APP_SECRET = st.secrets["APP_SECRET"]
CANO = st.secrets["CANO"]
ACNT_PRDT_CD = st.secrets["ACNT_PRDT_CD"]
URL_BASE = "https://openapi.koreainvestment.com:9443"

TARGET_STOCKS = {
    "005930": {"name": "삼성전자", "drop_target": -3.0},
    "034020": {"name": "두산에너빌리티", "drop_target": -3.0},
    "047040": {"name": "대우건설", "drop_target": -3.0},
    "002700": {"name": "신일전자", "drop_target": -3.0}
}

# ==============================================================================
# 🛠️ 데이터 통신 함수군
# ==============================================================================
@st.cache_data(ttl=3600)
def get_token():
    headers = {"content-type": "application/json"}
    body = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}
    res = requests.post(f"{URL_BASE}/oauth2/tokenP", headers=headers, data=json.dumps(body))
    return res.json().get("access_token")

def get_balance(token):
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
    res = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/trading/inquire-balance", headers=headers, params=params)
    if res.status_code == 200:
        data = res.json()
        out2 = data['output2'][0]
        return int(out2['tot_evlu_amt']), int(out2['dnca_tot_amt']), int(out2['scts_evlu_amt']), data['output1']
    return 0, 0, 0, []

def get_stock_price(token, ticker):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY, "appsecret": APP_SECRET, "tr_id": "FHKST01010100"
    }
    params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": ticker}
    res = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/quotations/inquire-price", headers=headers, params=params)
    if res.status_code == 200:
        out = res.json()['output']
        return float(out['stck_prpr']), float(out['prdy_ctrt'])
    return 0, 0.0

def get_kospi_info():
    try:
        url = "https://m.stock.naver.com/api/index/KOSPI/basic"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5).json()
        return float(res['nowValue'].replace(',', '')), float(res['fluctuationsRatio'])
    except:
        return 0.0, 0.0

# ==============================================================================
# 📱 사이드바 (무전기 매뉴얼 및 전략 브리핑)
# ==============================================================================
with st.sidebar:
    st.header("🎖️ 박가이버 사령부")
    st.info("💡 **버전:** V3.1 과수원 최종 완전체\n\n🛡️ **기지국:** 24시간 스마트폰(Termux) 무인 가동")
    
    st.divider()
    st.subheader("📱 텔레그램 무전 명령어")
    st.code("/상태 : 자산 및 요원 전황\n/타점 : 4종목 타점 스캔\n/뉴스 삼성전자 : 최신 뉴스 요약\n/월말결산 : 월간 전투 정산서\n/도움말 : 명령어 안내", language="text")
    
    st.divider()
    st.subheader("🍎 과수원 3분할 룰")
    st.markdown("- **📈 60% :** 원금 합류 (재투자/복리)\n- **🎁 20% :** 공짜주식 평생 보관\n- **🛡️ 20% :** 비상금 영구 잠금")

# ==============================================================================
# 🖥️ 메인 관제 화면
# ==============================================================================
st.title("📡 박가이버 사령부 라이브 관제탑")
now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# 1. 상단 KOSPI 시장 방패 모니터링 배너
kospi_val, kospi_rate = get_kospi_info()
if kospi_rate <= -3.0:
    st.error(f"🚨 **[강철 방패 가동 중]** 코스피 지수 {kospi_val:,.2f} ({kospi_rate:+.2f}%) 폭락 감지! 오늘 오후 매수 진입은 전면 차단됩니다.")
else:
    st.success(f"🌐 **[시장 정상 순항]** 코스피 {kospi_val:,.2f} ({kospi_rate:+.2f}%) | 15:19 종가 타점 감시 정상 가동 중 (기준시각: {now_str})")

st.markdown("---")

try:
    token = get_token()
    tot_asset, cash_amt, stock_amt, holdings = get_balance(token)
    
    # 2. 사령부 금고 핵심 지표
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👑 사령부 총자산", f"{tot_asset:,} 원")
    c2.metric("💵 가용 예수금(현금)", f"{cash_amt:,} 원", delta=f"비중 { (cash_amt/tot_asset*100) if tot_asset else 0:.1f}%")
    c3.metric("📈 주식 평가총액", f"{stock_amt:,} 원", delta=f"비중 { (stock_amt/tot_asset*100) if tot_asset else 0:.1f}%")
    c4.metric("🛡️ 시스템 방어막", "코스피 -3% 킬스위치 ON")

    st.markdown("###")

    # 3. 4종목 타점 정찰대 (남은 거리 게이지)
    st.subheader("🎯 4종목 정예 정찰대 (15:19 종가 타점 감시)")
    cols = st.columns(4)
    
    for idx, (ticker, conf) in enumerate(TARGET_STOCKS.items()):
        price, rate = get_stock_price(token, ticker)
        gap = rate - conf['drop_target'] # -3.0%까지 남은 거리
        
        with cols[idx]:
            with st.container(border=True):
                st.markdown(f"**{conf['name']}** `{ticker}`")
                st.metric(label="현재가", value=f"{price:,.0f}원", delta=f"{rate:+.2f}%")
                
                if rate <= conf['drop_target']:
                    st.success(f"🎯 **타점 돌파 완료!** ({rate:.2f}%)")
                    st.caption("오후 3:19 조건 만족 시 자동 출격")
                else:
                    st.info(f"⚪ **관망 중** (타점까지 {gap:+.2f}%p)")
                    st.caption("진입 기준선: -3.00% 이하")

    st.markdown("---")

    # 4. 실전 파견 요원(보유 종목) 현황표
    st.subheader("⚔️ 현재 파견 요원(보유 주식) 전황")
    active_holdings = [h for h in holdings if int(h.get('hldg_qty', 0)) > 0]
    
    if active_holdings:
        table_list = []
        for h in active_holdings:
            table_list.append({
                "종목명": h['prdt_name'],
                "종목코드": h['pdno'],
                "보유수량": f"{int(h['hldg_qty']):,} 주",
                "매입단가": f"{float(h['pchs_avg_pric']):,.0f} 원",
                "현재가": f"{int(h['prpr']):,} 원",
                "평가손익": f"{int(h['evlu_pfls_amt']):,} 원",
                "수익률": f"{float(h['evlu_pfls_rt']):+.2f}%"
            })
        st.dataframe(pd.DataFrame(table_list), use_container_width=True, hide_index=True)
    else:
        st.info("🛡️ 현재 전장에 파견된 요원이 없습니다. (전원 100% 안전 현금 대기 중)")

except Exception as e:
    st.error(f"통신 연결 중 오류가 발생했습니다: {e}")

st.markdown("###")
if st.button("🔄 실시간 전황 새로고침", use_container_width=True):
    st.rerun()
