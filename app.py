import streamlit as st
import requests
import json
import datetime
import pandas as pd

# ==============================================================================
# 📱 모바일 최적화 페이지 설정
# ==============================================================================
st.set_page_config(
    page_title="사령부 관제탑",
    page_icon="📡",
    layout="centered"  # 모바일 화면에 최적화된 중앙 집중형 레이아웃
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
    "034020": {"name": "두산에너빌", "drop_target": -3.0},
    "047040": {"name": "대우건설", "drop_target": -3.0},
    "002700": {"name": "신일전자", "drop_target": -3.0}
}

# ==============================================================================
# 🛠️ 데이터 통신 함수군
# ==============================================================================
@st.cache_data(ttl=1800)
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
        res = requests.get(url, headers=headers, timeout=3).json()
        return float(res['nowValue'].replace(',', '')), float(res['fluctuationsRatio'])
    except:
        return 0.0, 0.0

# ==============================================================================
# 📱 모바일 헤더 및 상태 배너
# ==============================================================================
st.subheader("📡 박가이버 사령부 V3.1")
now_time = datetime.datetime.now().strftime('%H:%M:%S')

# 상단 코스피 한 줄 브리핑
kospi_val, kospi_rate = get_kospi_info()
if kospi_rate <= -3.0:
    st.error(f"🚨 코스피 {kospi_val:,.0f} ({kospi_rate:+.2f}%) [강철 방패 가동]")
else:
    st.caption(f"🌐 코스피: {kospi_val:,.1f} ({kospi_rate:+.2f}%) | 갱신 {now_time}")

# ==============================================================================
# 📑 모바일 핵심: 3단 가로 탭 분할 (스크롤 제거)
# ==============================================================================
tab1, tab2, tab3 = st.tabs(["💰 금고 / 요원", "🎯 4종목 타점", "📱 무전 매뉴얼"])

try:
    token = get_token()
    tot_asset, cash_amt, stock_amt, holdings = get_balance(token)
    
    # --------------------------------------------------------------------------
    # 탭 1: 자산 현황 및 실전 파견 요원
    # --------------------------------------------------------------------------
    with tab1:
        # 모바일용 2열 메트릭
        c1, c2 = st.columns(2)
        c1.metric("👑 총자산", f"{tot_asset:,}원")
        c2.metric("💵 예수금", f"{cash_amt:,}원")
        
        c3, c4 = st.columns(2)
        c3.metric("📈 주식평가", f"{stock_amt:,}원")
        c4.metric("🛡️ 킬스위치", "정상 작동 중")
        
        st.divider()
        
        st.markdown("**⚔️ 현재 보유 요원**")
        active_holdings = [h for h in holdings if int(h.get('hldg_qty', 0)) > 0]
        if active_holdings:
            for h in active_holdings:
                with st.container(border=True):
                    hc1, hc2 = st.columns([1.5, 1])
                    hc1.markdown(f"**{h['prdt_name']}** ({int(h['hldg_qty'])}주)")
                    hc1.caption(f"매입가: {float(h['pchs_avg_pric']):,.0f}원")
                    hc2.metric("수익률", f"{float(h['evlu_pfls_rt']):+.2f}%", f"{int(h['evlu_pfls_amt']):,}원")
        else:
            st.info("🛡️ 현재 파견 요원 없음 (100% 안전 현금 대기)")

    # --------------------------------------------------------------------------
    # 탭 2: 4종목 타점 정찰대 (2x2 모바일 그리드)
    # --------------------------------------------------------------------------
    with tab2:
        st.caption("🎯 오후 3시 19분 (-3.0% 이하) 진입 스캔")
        
        # 2개씩 2줄로 콤팩트 배치
        stock_items = list(TARGET_STOCKS.items())
        
        # 1행 (삼성전자, 두산에너빌)
        r1_c1, r1_c2 = st.columns(2)
        for idx, (t, conf) in enumerate(stock_items[:2]):
            price, rate = get_stock_price(token, t)
            col = r1_c1 if idx == 0 else r1_c2
            with col:
                with st.container(border=True):
                    st.markdown(f"**{conf['name']}**")
                    st.metric("현재가", f"{price:,.0f}원", f"{rate:+.2f}%")
                    if rate <= conf['drop_target']:
                        st.success("🎯 타점 진입!")
                    else:
                        st.caption(f"거리: {rate - conf['drop_target']:+.2f}%p")

        # 2행 (대우건설, 신일전자)
        r2_c1, r2_c2 = st.columns(2)
        for idx, (t, conf) in enumerate(stock_items[2:]):
            price, rate = get_stock_price(token, t)
            col = r2_c1 if idx == 0 else r2_c2
            with col:
                with st.container(border=True):
                    st.markdown(f"**{conf['name']}**")
                    st.metric("현재가", f"{price:,.0f}원", f"{rate:+.2f}%")
                    if rate <= conf['drop_target']:
                        st.success("🎯 타점 진입!")
                    else:
                        st.caption(f"거리: {rate - conf['drop_target']:+.2f}%p")

    # --------------------------------------------------------------------------
    # 탭 3: 텔레그램 무전 매뉴얼
    # --------------------------------------------------------------------------
    with tab3:
        st.markdown("**📱 텔레그램 무전 명령어**")
        st.code("/상태 : 계좌 총자산 및 요원 전황\n/타점 : 4종목 타점 실시간 스캔\n/뉴스 삼성전자 : 최신 뉴스 요약\n/월말결산 : 월간 전투 정산서\n/도움말 : 명령어 리스트", language="text")
        
        st.markdown("**🍎 과수원 3분할 룰**")
        st.info("📈 60% : 거름(재투자 복리)\n🎁 20% : 공짜주식 평생 보관\n🛡️ 20% : 비상금 영구 잠금")

except Exception as e:
    st.error(f"통신 연결 실패: {e}")

# 하단 한눈에 누르는 새로고침 버튼
st.markdown("---")
if st.button("🔄 실시간 전황 새로고침", use_container_width=True):
    st.rerun()
