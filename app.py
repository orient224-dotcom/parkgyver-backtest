import streamlit as st
import requests
import json
import datetime
import os

# ==============================================================================
# 🎨 1. 사령부 관제탑 웹 설정
# ==============================================================================
st.set_page_config(
    page_title="박가이버 사령부 관제탑",
    page_icon="🎖️",
    layout="wide"
)

# 🔐 보안 키 불러오기 (Streamlit Secrets 및 OS 환경변수 호환)
def get_secret(key, default=""):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except:
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

# ==============================================================================
# 📡 2. 통신 및 데이터 함수
# ==============================================================================
@st.cache_data(ttl=60)
def get_access_token():
    if not APP_KEY or not APP_SECRET:
        return None
    headers = {"content-type": "application/json"}
    body = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}
    try:
        res = requests.post(f"{URL_BASE}/oauth2/tokenP", headers=headers, json=body, timeout=10)
        return res.json().get("access_token")
    except:
        return None

def get_account_status(token):
    if not token:
        return 0, 0
    url = f"{URL_BASE}/uapi/domestic-stock/v1/trading/inquire-balance"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
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
    except:
        pass
    return 0, 0

def get_stock_price(token, ticker):
    if not token:
        return None, None
    url = f"{URL_BASE}/uapi/domestic-stock/v1/quotations/inquire-price"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
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
    except:
        pass
    return None, None

def ask_ai_cso(tot_asset, avail_cash):
    if not GEMINI_API_KEY:
        return "⚠️ Gemini API 키가 설정되지 않았습니다."
    
    stocks_str = ", ".join([v['name'] for v in TARGET_STOCKS.values()])
    prompt = f"""
당신은 '박가이버 사령부'의 수석 전략 참모(AI CSO)입니다.
사령관(박가이버님)께 현재 자산 운용 진단과 다음 달 종목 교체/유지 권고안을 간결하고 명쾌하게 브리핑하세요.

[사령부 현황]
- 총자산: {tot_asset:,}원 (가용예수금: {avail_cash:,}원)
- 현재 4대 타깃 종목: {stocks_str}
- 전략: 종가 -3% 분할 매수, +30% 레이더/-7% 익절(과수원 3분할), -12% 손절

[보고서 작성 가이드]
1. 🔍 [현재 4종목 컨디션 점검]: 유지 vs 교체 검토
2. 🌊 [차기 메가트렌드 추천]: AI 인프라/전력, 반도체, 원전, 로봇 등 유망 섹터 중 가성비 교체 후보 1~2종목 추천
3. 🎖️ [사령관 결재 요청 문구]: '자세한 심층 토론은 제미나이 웹 참모실에서 진행하시길 건의드립니다.' 마무리.
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
            except:
                continue
        return "⚠️ AI 응답 생성에 실패했습니다."
    except Exception as e:
        return f"⚠️ 시스템 오류: {e}"

# ==============================================================================
# 🖥️ 3. 대시보드 화면 구성
# ==============================================================================
st.title("🎖️ 박가이버 사령부 종합 관제탑")
st.caption(f"기준 시각: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

token = get_access_token()
tot_asset, avail_cash = get_account_status(token)

# 자산 현황 카드
col1, col2, col3 = st.columns(3)
col1.metric("👑 총 평가 자산", f"{tot_asset:,} 원" if tot_asset else "조회 대기")
col2.metric("💵 가용 예수금", f"{avail_cash:,} 원" if avail_cash else "조회 대기")
col3.metric("🛡️ 시스템 상태", "정상 가동 중 (ONLINE)" if token else "통신 대기 (OFFLINE)")

st.divider()

# 4대 종목 실시간 타점 현황
st.subheader("🎯 4대 정예 종목 실시간 타점 스캔")

stock_data = []
for ticker, conf in TARGET_STOCKS.items():
    price, rate = get_stock_price(token, ticker)
    status_text = "⚪ 관망"
    if rate is not None:
        if rate <= conf['drop_target']:
            status_text = "🎯 출격 충족 (-3% 이하)"
        else:
            status_text = f"⚪ 관망 ({rate - conf['drop_target']:+.2f}%p 필요)"
    
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

# AI 참모 브리핑 섹션
st.subheader("🧠 AI 수석 참모 실시간 전략 보고서")
if st.button("📋 AI 수석 참모 전략 브리핑 요청", type="primary"):
    with st.spinner("수석 참모가 시장 분석 보고서를 작성 중입니다..."):
        report = ask_ai_cso(tot_asset, avail_cash)
        st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #28a745; color: #111;">
            {report}
        </div>
        """, unsafe_allow_html=True)
