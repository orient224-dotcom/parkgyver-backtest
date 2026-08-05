import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import json
from dateutil.relativedelta import relativedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 0. 타임존(Timezone) 및 날짜 안전 정규화 함수 ---
def clean_date_index(obj):
    if isinstance(obj, pd.Series):
        s = pd.to_datetime(obj)
        if s.dt.tz is not None:
            s = s.dt.tz_convert(None)
        return s.dt.normalize()
    elif isinstance(obj, (pd.DatetimeIndex, pd.Index)):
        idx = pd.to_datetime(obj)
        if getattr(idx, 'tz', None) is not None:
            idx = idx.tz_convert(None)
        return idx.normalize()
    else:
        dt = pd.to_datetime(obj)
        if getattr(dt, 'tz', None) is not None:
            dt = dt.tz_convert(None)
        return dt.normalize()

# --- 1. 페이지 웹 디자인 세팅 ---
st.set_page_config(page_title="박가이버 통합 작전 사령부 V10.3 Typhoon Defense", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    @media (max-width: 768px) {
        .hero-title { font-size: 1.2rem !important; }
        .hero-banner { padding: 14px 16px !important; }
        div[data-testid="stMetric"] { padding: 10px 12px !important; }
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%) !important;
        padding: 16px 20px !important;
        border-radius: 14px !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
    }
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 22px 24px;
        border-radius: 16px;
        color: #ffffff;
        border-left: 8px solid #38bdf8;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25);
        margin-bottom: 20px;
    }
    .hero-title { font-size: 1.6rem; font-weight: 900; margin: 0; color: #f8fafc; }
    .hero-subtitle { font-size: 0.95rem; color: #94a3b8; margin-top: 6px; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: #e2e8f0; padding: 8px 10px; border-radius: 14px; margin-bottom: 20px; }
    .stTabs [data-baseweb="tab"] { height: 44px; background-color: #ffffff; border-radius: 10px; padding: 0 16px; font-weight: 800; font-size: 0.9rem; color: #334155; border: 1px solid #cbd5e1; }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important; color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. 세션 및 마스터 종목 DB 초기화 ---
if "sector_db" not in st.session_state:
    st.session_state["sector_db"] = {
        "⚡ 반도체 & HBM / 칩렛": {"테크윙": "089030.KQ", "한미반도체": "042700.KS", "HPSP": "403870.KQ", "이오테크닉스": "039030.KQ", "리노공업": "058470.KQ", "ISC": "095340.KQ", "주성엔지니어링": "036930.KQ", "원익IPS": "240810.KQ", "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "피에스케이": "057030.KQ"},
        "🧬 바이오 & 제약 / 화장품": {"한국콜마": "161890.KS", "코스맥스": "192820.KS", "알테오젠": "196170.KQ", "셀트리온": "068270.KS", "삼성바이오로직스": "207940.KS", "HLB": "028300.KQ", "유한양행": "000100.KS", "리가켐바이오": "141080.KQ"},
        "📡 통신 & 방산 & 조선": {"RFHIC": "218410.KQ", "한화시스템": "272210.KS", "현대로템": "064350.KS", "LIG넥스원": "079550.KS", "한화오션": "042660.KS", "HD한국조선해양": "009540.KS", "두산에너빌리티": "034020.KS", "HD현대일렉트릭": "267260.KS", "한화에어로스페이스": "012450.KS"},
        "🔋 2차전지 & 에코": {"에코프로비엠": "247540.KQ", "에코프로": "086520.KQ", "LG에너지솔루션": "373220.KS", "POSCO홀딩스": "005490.KS", "엘앤에프": "066970.KQ", "포스코퓨처엠": "003670.KS"},
        "🚗 자동차 & 대표 제조": {"현대차": "005380.KS", "기아": "000270.KS", "현대모비스": "012330.KS", "레인보우로보틱스": "277810.KQ", "두산로보틱스": "454910.KS"},
        "💻 IT & 플랫폼": {"NAVER": "035420.KS", "카카오": "035720.KS"}
    }

if "custom_stocks" not in st.session_state: st.session_state["custom_stocks"] = {}
if "my_holdings" not in st.session_state: st.session_state["my_holdings"] = ["SK하이닉스", "한미반도체", "테크윙", "HD현대일렉트릭", "HPSP"]
if "my_watchlist" not in st.session_state: st.session_state["my_watchlist"] = ["한화오션", "현대로템", "RFHIC", "한국콜마"]

KOREAN_STOCK_MASTER = {
    "한국콜마": "161890.KS", "RFHIC": "218410.KQ", "코스맥스": "192820.KS", "현대힘스": "460930.KQ", "한화오션": "042660.KS", "HD한국조선해양": "009540.KS", "에스피지": "058610.KQ", "레인보우로보틱스": "277810.KQ", "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "테크윙": "089030.KQ", "한미반도체": "042700.KS", "기가비스": "420770.KQ", "케이씨텍": "281820.KS", "이수화학": "005950.KS", "이수스페셜티케미컬": "457190.KS", "마녀공장": "439090.KQ", "뉴파워프라즈마": "144960.KQ", "두산에너빌리티": "034020.KS", "하나마이크론": "084370.KQ", "동진쎄미켐": "033640.KQ", "솔브레인": "357780.KQ", "가온칩스": "399500.KQ", "두산로보틱스": "454910.KS", "한화에어로스페이스": "012450.KS", "LIG넥스원": "079550.KS", "HD현대일렉트릭": "267260.KS", "LS일렉트릭": "010120.KS", "포스코퓨처엠": "003670.KS", "피에스케이": "057030.KQ"
}

MASTER_STOCK_DICT = {}
TICKER_TO_SECTOR = {}
for sector, stocks in st.session_state["sector_db"].items():
    for name, code in stocks.items():
        MASTER_STOCK_DICT[name] = code
        TICKER_TO_SECTOR[code] = sector
for name, code in KOREAN_STOCK_MASTER.items():
    if name not in MASTER_STOCK_DICT:
        MASTER_STOCK_DICT[name] = code
        TICKER_TO_SECTOR[code] = "기타 우량주"
for name, code in st.session_state["custom_stocks"].items():
    MASTER_STOCK_DICT[name] = code
    TICKER_TO_SECTOR[code] = "커스텀 직접등록 종목"

def format_money(num):
    if num is None or pd.isna(num): return "-"
    sign = "-" if int(round(num)) < 0 else ""
    return f"{sign}{abs(int(round(num))):,}원"

def format_pure_number(num):
    if num is None or pd.isna(num): return "-"
    return f"{int(round(num)):,}"

def format_exact_price(num):
    if num is None or pd.isna(num): return "-"
    return f"{int(round(num)):,}원"

# --- 3. 구독자 가이드 (펼침 UI) ---
def render_subscriber_guide():
    with st.expander("📖 [당귀다TV] 박가이버 작전 사령부 V10.3 1분 탑승 가이드 (필독!)", expanded=False):
        st.markdown("""
        ### 🛡️ 4050 바쁜 직장인을 위한 '본업 집중형' 퀀트 투자 수칙
        1. **🕒 1분 컷 '순수 종가 매매':** 근무 시간에는 주식 창을 완전히 봉인하고, 매일 오후 3시 20분에 접속해 레이더 신호 확인 후 동시호가 매수!
        2. **🚁 전원 동반 탈출 ('헬기 복귀'):** 출격 요원 중 단 1명이라도 목표가를 터치하면 전 부대원 동반 청산하여 계좌 회전율 극대화!
        3. **🧠 지능형 날씨 판독기:** 정배열(상승장)엔 **+10%**, 역배열/박스권엔 **+5%**로 목표가 자동 조절!
        4. **🌊 기상청 태풍 경보 시스템:** *"우리 배가 아무리 튼튼해도, 바다 전체에 '초대형 태풍 주의보'가 발령되면 출항하지 않는다!"* 코스피가 200일선 아래로 무너지면 신규 출격을 차단하고 현금을 지킵니다!
        5. **⛄ 스노우볼 레벨UP:** 자산이 +10% 찰 때마다 1회 출격 예산이 10%씩 커지는 복리의 마법!
        """)

# --- 4. 사이드바 조종간 ---
st.sidebar.title("🎛️ 박가이버 사령부 V10.3")
st.sidebar.subheader("💾 나만의 작전 세팅 (휴대폰 관리)")
uploaded_cfg = st.sidebar.file_uploader("📤 내 세팅 불러오기 (.json)", type=["json"])
if uploaded_cfg:
    try:
        cfg_data = json.load(uploaded_cfg)
        if "my_holdings" in cfg_data: st.session_state["my_holdings"] = cfg_data["my_holdings"]
        if "my_watchlist" in cfg_data: st.session_state["my_watchlist"] = cfg_data["my_watchlist"]
        st.sidebar.success("🎉 작전 세팅 파일 복원 완료!")
    except:
        st.sidebar.error("⚠️ 올바른 설정(.json) 파일이 아닙니다.")

st.sidebar.markdown("---")
menu_choice = st.sidebar.radio(
    "사령부 작전 모드선택",
    ["🗄️ 1. 내 계좌 영구 DB (보유 & 관심)", "🚨 2. 오늘의 실전 매매 레이더", "🛡️ 3. 과거 5년 백테스트 연구소"],
    index=0
)
st.sidebar.markdown("---")

# =====================================================================
# 🗄️ 메뉴 1: 내 계좌 영구 DB
# =====================================================================
if menu_choice == "🗄️ 1. 내 계좌 영구 DB (보유 & 관심)":
    st.markdown("""<div class="hero-banner"><div class="hero-title">🗄️ 나만의 투자 영구 DB (마이 포트폴리오)</div><div class="hero-subtitle">실전 보유 종목을 세팅하고 스마트폰 파일로 영구 저장해 두세요!</div></div>""", unsafe_allow_html=True)
    render_subscriber_guide()
    
    st.markdown("### 🔍 신규 종목 직접 검색 및 바구니 추가")
    col_s1, col_s2, col_s3 = st.columns([2, 2, 1])
    with col_s1:
        add_name = st.text_input("종목명 입력 (예: 한화에어로스페이스)", key="add_stock_name")
    with col_s2:
        add_code = st.text_input("종목코드 6자리 (예: 012450)", key="add_stock_code")
    with col_s3:
        market_type = st.selectbox("시장 구분", ["KOSPI (.KS)", "KOSDAQ (.KQ)"], key="add_market_type")

    if st.button("➕ 내 바구니에 종목 즉시 등록", type="primary", use_container_width=True):
        if add_name and add_code:
            code_clean = add_code.strip()
            suffix = ".KS" if "KOSPI" in market_type else ".KQ"
            full_code = code_clean if (code_clean.endswith(".KS") or code_clean.endswith(".KQ")) else f"{code_clean}{suffix}"

            st.session_state["custom_stocks"][add_name] = full_code
            if add_name not in st.session_state["my_holdings"]:
                st.session_state["my_holdings"].append(add_name)
            
            st.success(f"🎉 [{add_name}] ({full_code}) 종목이 내 바구니에 성공적으로 등록되었습니다!")
            st.rerun()
        else:
            st.warning("⚠️ 종목명과 종목코드를 모두 입력해 주세요.")

    st.markdown("---")

    db_tab1, db_tab2 = st.tabs(["💼 내 실전 보유 종목 (주력)", "⭐ 눈여겨보는 관심 종목"])
    with db_tab1:
        valid_holdings = [s for s in st.session_state["my_holdings"] if s in MASTER_STOCK_DICT]
        new_holdings = st.multiselect("실전 보유 종목 편집:", list(MASTER_STOCK_DICT.keys()), default=valid_holdings, key="holding_multi")
        if st.button("💾 실전 보유 종목 DB 저장", type="primary", use_container_width=True):
            st.session_state["my_holdings"] = new_holdings
            st.success("🎉 실전 보유 종목이 안전하게 저장되었습니다!")
            st.rerun()

    with db_tab2:
        valid_watchlist = [s for s in st.session_state["my_watchlist"] if s in MASTER_STOCK_DICT]
        new_watchlist = st.multiselect("관심 종목 편집:", list(MASTER_STOCK_DICT.keys()), default=valid_watchlist, key="watchlist_multi")
        if st.button("💾 관심 종목 DB 저장", use_container_width=True):
            st.session_state["my_watchlist"] = new_watchlist
            st.success("🎉 관심 종목이 안전하게 저장되었습니다!")
            st.rerun()

    st.markdown("---")
    st.markdown("### ⚡ 원터치 추천 포트폴리오 패키지 로드 (6대 풍성한 테마)")
    p_col1, p_col2, p_col3 = st.columns(3)
    p_col4, p_col5, p_col6 = st.columns(3)

    if p_col1.button("🤖 AI/HBM 반도체 황금 5선", use_container_width=True):
        st.session_state["my_holdings"] = ["SK하이닉스", "한미반도체", "테크윙", "HD현대일렉트릭", "HPSP"]
        st.toast("🎉 AI/HBM 반도체 5선 세팅 완료!")
        st.rerun()

    if p_col2.button("🛡️ K-방산 & 척척 조선 5선", use_container_width=True):
        st.session_state["my_holdings"] = ["한화오션", "HD한국조선해양", "LIG넥스원", "현대로템", "한화에어로스페이스"]
        st.toast("🎉 K-방산/조선 5선 세팅 완료!")
        st.rerun()

    if p_col3.button("🧬 바이오 & K-뷰티 5선", use_container_width=True):
        st.session_state["my_holdings"] = ["한국콜마", "코스맥스", "알테오젠", "셀트리온", "유한양행"]
        st.toast("🎉 바이오/K-뷰티 5선 세팅 완료!")
        st.rerun()

    if p_col4.button("🔋 2차전지 & 핵심 소재 5선", use_container_width=True):
        st.session_state["my_holdings"] = ["LG에너지솔루션", "POSCO홀딩스", "에코프로비엠", "포스코퓨처엠", "엘앤에프"]
        st.toast("🎉 2차전지/소재 5선 세팅 완료!")
        st.rerun()

    if p_col5.button("🚗 현대차그룹 & 미래로봇 4선", use_container_width=True):
        st.session_state["my_holdings"] = ["현대차", "기아", "레인보우로보틱스", "두산로보틱스"]
        st.toast("🎉 현대차그룹/로봇 4선 세팅 완료!")
        st.rerun()

    if p_col6.button("💻 IT플랫폼 & 전력/에너지 4선", use_container_width=True):
        st.session_state["my_holdings"] = ["NAVER", "카카오", "두산에너빌리티", "RFHIC"]
        st.toast("🎉 IT플랫폼/전력 4선 세팅 완료!")
        st.rerun()

    st.markdown("---")
    st.markdown("### 💾 나만의 세팅 휴대폰 파일로 백업하기")
    cfg_to_save = {
        "my_holdings": st.session_state.get("my_holdings", []),
        "my_watchlist": st.session_state.get("my_watchlist", [])
    }
    json_cfg_str = json.dumps(cfg_to_save, ensure_ascii=False, indent=2)
    st.download_button(
        label="📥 내 작전 세팅 휴대폰에 다운로드 (.json)",
        data=json_cfg_str,
        file_name="parkgyver_my_strategy.json",
        mime="application/json",
        use_container_width=True
    )

# =====================================================================
# 🚨 메뉴 2: 오늘의 실전 매매 레이더
# =====================================================================
elif menu_choice == "🚨 2. 오늘의 실전 매매 레이더":
    st.markdown("""<div class="hero-banner"><div class="hero-title">🚨 오늘의 실전 매매 레이더 (출격 명령서)</div></div>""", unsafe_allow_html=True)
    render_subscriber_guide()
    
    buy_cond_input = st.sidebar.slider("🛒 진입 기준 (-% 하락 시)", 1, 20, 5, 1)
    valid_watch_stocks = [s for s in st.session_state["my_holdings"] if s in MASTER_STOCK_DICT]
    PORTFOLIO_UNIVERSE = {s_name: MASTER_STOCK_DICT[s_name] for s_name in valid_watch_stocks if s_name in MASTER_STOCK_DICT}

    st.markdown(f"🎯 **[실전 감시 전광판] 현재 내 계좌 DB 연동 종목 ({len(valid_watch_stocks)}개):** {', '.join(valid_watch_stocks)}")
    st.markdown("---")

    if len(PORTFOLIO_UNIVERSE) > 0:
        try:
            live_tickers = list(PORTFOLIO_UNIVERSE.values())
            live_raw = yf.download(live_tickers, period="5d", interval="1d", progress=False)
            live_data = live_raw['Close'] if isinstance(live_raw.columns, pd.MultiIndex) and 'Close' in live_raw.columns.levels[0] else (live_raw['Close'] if 'Close' in live_raw.columns else live_raw)
            
            buy_signals = []
            for name, code in PORTFOLIO_UNIVERSE.items():
                s_data = live_data[code].dropna() if isinstance(live_data, pd.DataFrame) and code in live_data.columns else (live_data.dropna() if isinstance(live_data, pd.Series) else pd.Series())
                if len(s_data) >= 2:
                    today_p = float(s_data.iloc[-1])
                    yester_p = float(s_data.iloc[-2])
                    change_pct = ((today_p - yester_p) / yester_p) * 100
                    if change_pct <= -float(buy_cond_input):
                        buy_signals.append(f"🛒 **[{name}]** 당일 변동률: **{change_pct:.2f}%** (진입 타점 포착! 오늘 3시 20분 동시호가 출격 시그널)")
            
            if buy_signals:
                st.error("⚡ **오늘 실전 진입 타점에 포착된 종목이 있습니다!**\n\n" + "\n\n".join(buy_signals))
            else:
                st.success("✅ **현재 내 계좌 DB 종목 중 당일 급락 종목이 없습니다.** 사령부 요원들은 출격 대기 상태를 유지합니다.")
        except:
            st.info("💡 실시간 시세를 동기화하는 중입니다.")

# =====================================================================
# 🛡️ 메뉴 3: 과거 5년 백테스트 연구소 (태풍 경보 시스템 탑재)
# =====================================================================
else:
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🛡️ V10.3 과거 5년 백테스트 연구소 (태풍 방어판)</div>
        <div class="hero-subtitle">실전 검증 | 🌊 기상청 태풍 경보 시스템(코스피 200일선 방어), 전원 동반 탈출, 지능형 목표가 탑재</div>
    </div>
    """, unsafe_allow_html=True)
    
    render_subscriber_guide()

    valid_watch_stocks = [s for s in st.session_state["my_holdings"] if s in MASTER_STOCK_DICT]
    PORTFOLIO_UNIVERSE = {s_name: MASTER_STOCK_DICT[s_name] for s_name in valid_watch_stocks if s_name in MASTER_STOCK_DICT}

    if valid_watch_stocks:
        st.success(f"🎯 **[백테스트 연구소 전광판] 내 계좌 DB 연동 종목 ({len(valid_watch_stocks)}개):** {', '.join(valid_watch_stocks)}")
    else:
        st.error("⚠️ **[감시 종목 경보]** 장전된 종목이 없습니다! 메뉴 [🗄️ 1. 내 계좌 영구 DB]에서 종목을 먼저 골라주세요.")

    st.sidebar.subheader("⚙️ 백테스트 전략 조건 설정")
    use_typhoon_warning = st.sidebar.checkbox("🚨 KOSPI '기상청 태풍 경보 시스템'", value=True, help="코스피 지수가 200일선 아래로 내려앉으면 신규 출격을 전면 차단하고 현금(항구)에 대피합니다!")
    
    use_smart_target = st.sidebar.checkbox("🧠 지능형 자동 목표가 (날씨 연동)", value=True)
    sell_target_input = 5.0
    if not use_smart_target:
        sell_target_input = st.sidebar.slider("🎯 고정 익절 목표 (+%)", 1, 30, 5, 1)
    
    use_batch_exit = st.sidebar.checkbox("🚁 전원 동반 탈출 (연쇄 청산 활성화)", value=True)
    use_sector_limit = st.sidebar.checkbox("🤹‍♂️ 동일 섹터 몰빵 방지 캡", value=True)
    
    total_capital_input = st.sidebar.number_input("🏦 총 작전 예산(원)", value=10000000, step=1000000)
    max_active_slots = st.sidebar.slider("전체 파견 슬롯 (최대 요원 수)", 2, 10, 5)
    max_sector_slots = max(1, max_active_slots // 2)

    use_compounding = st.sidebar.checkbox("🚀 복리 스케일업 (자산 10% 증가시 레벨업)", value=True)
    buy_cond_input = st.sidebar.slider("🛒 진입 기준 (-% 하락 시)", 1, 20, 5, 1)
    stop_loss_input = st.sidebar.slider("🚨 손절 기준 (-%)", 0, 50, 15, 1)

    st.sidebar.subheader("💸 거래비용 적용")
    broker_fee_pct = st.sidebar.number_input("위탁수수료 (%)", value=0.015, format="%.3f") / 100
    tax_pct = st.sidebar.number_input("매도 거래세 (%)", value=0.18, format="%.2f") / 100
    slippage_pct = st.sidebar.number_input("체결 오차 슬리피지 (%)", value=0.10, format="%.2f") / 100

    reward_type = st.sidebar.selectbox("🎁 전리품 수령 방식", ["🌟 현금 50% + 열매 50% (하이브리드)", "전액 현금으로 챙기기", "열매로 결실 모으기"])
    years_val = st.sidebar.slider("백테스트 기간(년)", 1, 10, 5, 1)
    months_input = years_val * 12

    if st.sidebar.button("🚀 V10.3 태풍 방어 타임머신 가동!", type="primary", use_container_width=True):
        if len(PORTFOLIO_UNIVERSE) == 0:
            st.error("❌ 감시 종목이 없습니다. 1번 메뉴에서 보유 종목을 골라주세요.")
        else:
            with st.spinner("📡 슈퍼컴퓨터가 태풍 경보 시스템(코스피 200일선) 및 4대 정밀 리포트를 계산 중입니다..."):
                end_date_str = datetime.datetime.today().strftime('%Y-%m-%d')
                start_date_str = (datetime.datetime.today() - relativedelta(months=months_input)).strftime('%Y-%m-%d')
                tickers = list(PORTFOLIO_UNIVERSE.values())
                
                raw_close = yf.download(tickers, start=start_date_str, end=end_date_str, interval="1d", progress=False)
                close_df = raw_close['Close'] if 'Close' in raw_close.columns.levels[0] else raw_close
                if isinstance(close_df, pd.Series): close_df = close_df.to_frame(name=tickers[0])
                close_df = close_df.dropna(how='all')
                close_df.index = clean_date_index(close_df.index)

                try:
                    raw_actions = yf.download(tickers, start=start_date_str, end=end_date_str, interval="1d", actions=True, progress=False)
                    div_df = raw_actions['Dividends'] if 'Dividends' in raw_actions.columns.levels[0] else pd.DataFrame(0, index=close_df.index, columns=tickers)
                except:
                    div_df = pd.DataFrame(0, index=close_df.index, columns=tickers)
                div_df.index = clean_date_index(div_df.index)
                div_df = div_df.reindex(close_df.index).fillna(0)

                bench_df = pd.DataFrame()
                try:
                    bench_raw = yf.download(["^KS11", "^KQ11"], start=start_date_str, end=end_date_str, interval="1d", progress=False)
                    bench_df = bench_raw['Close'] if 'Close' in bench_raw.columns.levels[0] else bench_raw
                    if not bench_df.empty: bench_df.index = clean_date_index(bench_df.index)
                except:
                    pass

                # Calculate KOSPI 200 MA for Typhoon Warning
                kospi_series = pd.Series(dtype=float)
                kospi_ma200 = pd.Series(dtype=float)
                if not bench_df.empty:
                    ks_col = '^KS11' if '^KS11' in bench_df.columns else bench_df.columns[0]
                    kospi_series = bench_df[ks_col].reindex(close_df.index).ffill().bfill()
                    kospi_ma200 = kospi_series.rolling(window=200).mean()

                return_df = close_df.pct_change() * 100
                ma20_df = close_df.rolling(window=20).mean()
                ma60_df = close_df.rolling(window=60).mean()
                ma120_df = close_df.rolling(window=120).mean()

                buy_cond = -float(buy_cond_input)
                stop_loss_limit = -float(stop_loss_input) if stop_loss_input > 0 else None

                base_capital = float(total_capital_input)
                current_cash = base_capital
                step_progress = 0.0
                level_up_count = 0

                active_positions = []
                trade_logs, asset_history = [], []
                agent_counter = 0
                total_success, total_stop_loss = 0, 0
                free_shares_dict = {s_name: 0 for s_name in PORTFOLIO_UNIVERSE.keys()}
                yearly_stats = {}
                global_max_deployed = 0
                daily_deployment_snapshots = []
                missed_opportunities = []
                total_dividend_profit = 0
                typhoon_blocked_count = 0

                peak_asset_value = base_capital
                max_drawdown_pct = 0.0

                for date, row in close_df.iterrows():
                    date_str = date.strftime('%Y-%m-%d')
                    year = date.year
                    if year not in yearly_stats:
                        yearly_stats[year] = {'success': 0, 'stop': 0, 'shares': 0, 'cash': 0, 'share_val': 0.0}

                    # Check Typhoon Warning
                    is_typhoon_warning = False
                    if use_typhoon_warning and not kospi_series.empty and date in kospi_series.index and date in kospi_ma200.index:
                        k_val = kospi_series.loc[date]
                        m_val = kospi_ma200.loc[date]
                        if pd.notna(k_val) and pd.notna(m_val) and k_val < m_val:
                            is_typhoon_warning = True

                    daily_dividend_sum = 0
                    if date in div_df.index:
                        for s_name, count in free_shares_dict.items():
                            if count > 0:
                                t_code = PORTFOLIO_UNIVERSE[s_name]
                                if t_code in div_df.columns:
                                    d_val = div_df.loc[date, t_code]
                                    if pd.notna(d_val) and d_val > 0: daily_dividend_sum += count * d_val
                        for pos in active_positions:
                            t_code = pos['ticker']
                            if t_code in div_df.columns:
                                d_val = div_df.loc[date, t_code]
                                if pd.notna(d_val) and d_val > 0:
                                    pos_shares = pos['invest_amount'] / pos['entry_price']
                                    daily_dividend_sum += pos_shares * d_val

                    if daily_dividend_sum > 0:
                        current_cash += daily_dividend_sum
                        total_dividend_profit += daily_dividend_sum
                        trade_logs.append({
                            '요원': '시스템', '작전 구역': '배당금 수금', '출격일': date_str, '진입금액': '-',
                            '복귀일': date_str, '순수익률': '-', '정산내역': f"🍯 배당수입: +{format_pure_number(daily_dividend_sum)}원",
                            '구분': '🌟 특별 보너스'
                        })

                    has_winner = False
                    winner_reason = ""
                    for pos in active_positions:
                        t_code = pos['ticker']
                        if t_code in row and not pd.isna(row[t_code]):
                            curr_price = float(row[t_code])
                            gross_ret = ((curr_price - pos['entry_price']) / pos['entry_price']) * 100
                            if gross_ret >= pos['target_ret']:
                                has_winner = True
                                winner_reason = f"🎯 {pos['stock_name']} 목표({pos['target_ret']}%) 달성 ➡️ 전원 동반복귀!"
                                break

                    batch_net_profit = 0.0
                    batch_invested = 0.0

                    if has_winner and use_batch_exit:
                        last_stock_name = ""
                        last_price = 0.0
                        for pos in active_positions:
                            t_code = pos['ticker']
                            curr_price = float(row[t_code]) if t_code in row and not pd.isna(row[t_code]) else pos['entry_price']
                            sell_gross = pos['invest_amount'] * (curr_price / pos['entry_price'])
                            
                            buy_fee = pos['invest_amount'] * broker_fee_pct
                            sell_fee = sell_gross * broker_fee_pct
                            sell_tax = sell_gross * tax_pct
                            slippage = (pos['invest_amount'] + sell_gross) * slippage_pct
                            total_cost = buy_fee + sell_fee + sell_tax + slippage
                            
                            net_profit = (sell_gross - pos['invest_amount']) - total_cost
                            batch_net_profit += net_profit
                            batch_invested += pos['invest_amount']
                            
                            last_stock_name = pos['stock_name']
                            last_price = curr_price
                            
                            trade_logs.append({
                                '요원': pos['name'], '작전 구역': pos['stock_name'], '출격일': pos['entry_date'],
                                '진입금액': f"{format_pure_number(pos['invest_amount'])}원",
                                '복귀일': date_str, '순수익률': f"{(net_profit / pos['invest_amount']) * 100:.2f}%",
                                '정산내역': f"{format_pure_number(net_profit)}원", '구분': winner_reason
                            })

                        total_success += 1
                        yearly_stats[year]['success'] += 1

                        if batch_net_profit > 0:
                            if reward_type == '🌟 현금 50% + 열매 50% (하이브리드)':
                                harvest_amt = batch_net_profit * 0.5
                                cash_amt = batch_net_profit * 0.5
                            elif reward_type == '열매로 결실 모으기':
                                harvest_amt = batch_net_profit
                                cash_amt = 0
                            else:
                                harvest_amt = 0
                                cash_amt = batch_net_profit

                            buyable = int(harvest_amt // last_price) if last_price > 0 else 0
                            leftover = harvest_amt - (buyable * last_price)
                            
                            if buyable > 0: free_shares_dict[last_stock_name] += buyable
                            current_cash += (batch_invested + cash_amt + leftover)
                            yearly_stats[year]['shares'] += buyable
                            yearly_stats[year]['cash'] += cash_amt + leftover

                            if use_compounding:
                                step_progress += (cash_amt + leftover)
                                threshold = base_capital * 0.10
                                if step_progress >= threshold:
                                    level_up_count += 1
                                    base_capital += threshold
                                    step_progress -= threshold
                        else:
                            current_cash += (batch_invested + batch_net_profit)

                        active_positions = []

                    else:
                        survived_positions = []
                        for pos in active_positions:
                            t_code = pos['ticker']
                            is_exit = False
                            curr_price = pos['entry_price']
                            if t_code in row and not pd.isna(row[t_code]):
                                curr_price = float(row[t_code])
                                gross_ret = ((curr_price - pos['entry_price']) / pos['entry_price']) * 100
                                if stop_loss_limit is not None and gross_ret <= stop_loss_limit:
                                    is_exit = True
                                    exit_reason = f"🚨 강제 철수({stop_loss_limit}%)"
                                elif not use_batch_exit and gross_ret >= pos['target_ret']:
                                    is_exit = True
                                    exit_reason = f"🎯 개별 익절({pos['target_ret']}%)"

                            if is_exit:
                                sell_gross = pos['invest_amount'] * (curr_price / pos['entry_price'])
                                cost = (pos['invest_amount'] * broker_fee_pct) + (sell_gross * (broker_fee_pct + tax_pct)) + ((pos['invest_amount'] + sell_gross) * slippage_pct)
                                net_profit = (sell_gross - pos['invest_amount']) - cost
                                current_cash += (pos['invest_amount'] + net_profit)
                                
                                if net_profit < 0:
                                    total_stop_loss += 1
                                    yearly_stats[year]['stop'] += 1
                                else:
                                    total_success += 1
                                    yearly_stats[year]['success'] += 1
                                    
                                trade_logs.append({
                                    '요원': pos['name'], '작전 구역': pos['stock_name'], '출격일': pos['entry_date'],
                                    '진입금액': f"{format_pure_number(pos['invest_amount'])}원",
                                    '복귀일': date_str, '순수익률': f"{(net_profit / pos['invest_amount']) * 100:.2f}%",
                                    '정산내역': f"{format_pure_number(net_profit)}원", '구분': exit_reason
                                })
                            else:
                                survived_positions.append(pos)
                        active_positions = survived_positions

                    day_returns = return_df.loc[date] if date in return_df.index else None
                    if day_returns is not None and len(active_positions) < max_active_slots:
                        if is_typhoon_warning:
                            typhoon_blocked_count += 1
                        else:
                            agent_budget = int(base_capital // max_active_slots)
                            candidates = []
                            for s_name, t_code in PORTFOLIO_UNIVERSE.items():
                                if not any(p['ticker'] == t_code for p in active_positions) and t_code in day_returns and not pd.isna(day_returns[t_code]):
                                    ret_val = float(day_returns[t_code])
                                    if ret_val <= buy_cond:
                                        candidates.append((s_name, t_code, ret_val, float(row[t_code])))
                            
                            candidates.sort(key=lambda x: x[2])
                            
                            for cand in candidates:
                                s_name, t_code, ret_val, c_price = cand
                                if use_sector_limit:
                                    c_sector = TICKER_TO_SECTOR.get(t_code, "기타")
                                    if sum(1 for p in active_positions if TICKER_TO_SECTOR.get(p['ticker'], "기타") == c_sector) >= max_sector_slots:
                                        missed_opportunities.append({"발생 일자": date_str, "미출격 종목": s_name, "당일 하락률": f"{ret_val:.2f}%", "불가 사유": f"섹터({c_sector}) 쏠림 방지 캡"})
                                        continue
                                
                                if len(active_positions) >= max_active_slots:
                                    missed_opportunities.append({"발생 일자": date_str, "미출격 종목": s_name, "당일 하락률": f"{ret_val:.2f}%", "불가 사유": "요원 슬롯 풀가동"})
                                elif current_cash < agent_budget:
                                    missed_opportunities.append({"발생 일자": date_str, "미출격 종목": s_name, "당일 하락률": f"{ret_val:.2f}%", "불가 사유": "가용 현금 부족"})
                                else:
                                    target_ret = sell_target_input if not use_smart_target else 5.0
                                    if use_smart_target and t_code in ma20_df.columns and t_code in ma60_df.columns and t_code in ma120_df.columns:
                                        m20, m60, m120 = ma20_df.loc[date, t_code], ma60_df.loc[date, t_code], ma120_df.loc[date, t_code]
                                        if pd.notna(m20) and pd.notna(m60) and pd.notna(m120):
                                            if (c_price > m20) and (m20 > m60) and (m60 > m120): target_ret = 10.0
                                            elif (m20 > m60) or (c_price > m60 > m120): target_ret = 8.0
                                            else: target_ret = 5.0
                                    
                                    agent_counter += 1
                                    current_cash -= agent_budget
                                    active_positions.append({
                                        'name': f"{agent_counter}호 요원", 'stock_name': s_name, 'ticker': t_code,
                                        'entry_price': c_price, 'entry_date': date_str, 'invest_amount': agent_budget,
                                        'target_ret': target_ret
                                    })

                    curr_count = len(active_positions)
                    if curr_count > global_max_deployed: global_max_deployed = curr_count
                    if curr_count > 0:
                        daily_deployment_snapshots.append({"발생 일자": date_str, "동시 출격 수": curr_count, "출격 종목 리스트": ", ".join([p['stock_name'] for p in active_positions])})

                    eval_pos = sum([p['invest_amount'] * (float(row[p['ticker']]) / p['entry_price']) for p in active_positions if p['ticker'] in row and not pd.isna(row[p['ticker']])])
                    today_total_asset = current_cash + eval_pos
                    if today_total_asset > peak_asset_value: peak_asset_value = today_total_asset
                    current_drawdown = ((today_total_asset - peak_asset_value) / peak_asset_value) * 100
                    if current_drawdown < max_drawdown_pct: max_drawdown_pct = current_drawdown
                    asset_history.append({"Date": date_str, "Total_Asset": today_total_asset, "Drawdown": current_drawdown})

                asset_df = pd.DataFrame(asset_history)
                kospi_ret_pct, kosdaq_ret_pct = 0.0, 0.0
                bench_synced = False
                if not bench_df.empty:
                    try:
                        bench_clean = bench_df.copy()
                        bench_clean.index = [d.strftime('%Y-%m-%d') for d in bench_clean.index]
                        ks_key = '^KS11' if '^KS11' in bench_clean.columns else bench_clean.columns[0]
                        kq_key = '^KQ11' if '^KQ11' in bench_clean.columns else (bench_clean.columns[1] if len(bench_clean.columns)>1 else ks_key)
                        bench_aligned = bench_clean.reindex(asset_df['Date']).ffill().bfill()
                        
                        ks_start, ks_end = float(bench_aligned[ks_key].iloc[0]), float(bench_aligned[ks_key].iloc[-1])
                        kq_start, kq_end = float(bench_aligned[kq_key].iloc[0]), float(bench_aligned[kq_key].iloc[-1])
                        
                        kospi_ret_pct = ((ks_end - ks_start) / ks_start) * 100
                        kosdaq_ret_pct = ((kq_end - kq_start) / kq_start) * 100
                        
                        asset_df['KOSPI'] = (bench_aligned[ks_key].values / ks_start) * total_capital_input
                        asset_df['KOSDAQ'] = (bench_aligned[kq_key].values / kq_start) * total_capital_input
                        bench_synced = True
                    except: pass

                last_row = close_df.iloc[-1]
                active_eval = sum([p['invest_amount'] * (float(last_row[p['ticker']]) / p['entry_price']) for p in active_positions if p['ticker'] in last_row and not pd.isna(last_row[p['ticker']])])
                fruit_eval = sum([count * float(last_row[PORTFOLIO_UNIVERSE[s_name]]) for s_name, count in free_shares_dict.items() if count > 0 and PORTFOLIO_UNIVERSE[s_name] in last_row and not pd.isna(last_row[PORTFOLIO_UNIVERSE[s_name]])])
                
                final_total = current_cash + active_eval + fruit_eval
                total_net_profit = final_total - total_capital_input
                total_return_pct = (total_net_profit / total_capital_input) * 100
                total_trades = total_success + total_stop_loss
                win_rate = (total_success / total_trades * 100) if total_trades > 0 else 0

                st.markdown(f"""
                <div style="border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 15px;">
                    <h2 style="margin: 0; color: #0f172a; font-weight: 800;">🏆 백테스트 최종 성과 대시보드</h2>
                    <p style="margin: 4px 0 0 0; font-size: 0.9rem; color: #475569; font-weight: 700;">
                        📅 검증 기간: <b>{start_date_str} ~ {end_date_str} ({years_val}년)</b> | 
                        🚀 스노우볼 레벨UP: <b style="color: #ef4444;">총 {level_up_count}회 달성</b> |
                        🚨 태풍 경보로 출격 차단: <b style="color: #dc2626;">총 {typhoon_blocked_count}일 방어</b>
                    </p>
                </div>
                """, unsafe_allow_html=True)

                m0, m1, m2, m3 = st.columns(4)
                m0.metric("💵 가용 현금 잔고", format_money(current_cash))
                m1.metric("🏁 원금 예산", format_money(total_capital_input))
                m2.metric("✨ 최종 총자산", format_money(final_total))
                m3.metric("📈 총 순수익금", format_money(total_net_profit), delta=f"{total_return_pct:.2f}%")

                st.write("")
                m4, m5, m6, m7 = st.columns(4)
                m4.metric("🎯 작전 승률", f"{win_rate:.1f}%", delta=f"{total_trades}전 {total_success}승 {total_stop_loss}패")
                m5.metric("🌊 최대 낙폭 (MDD)", f"{max_drawdown_pct:.1f}%")
                m6.metric("📦 수확한 열매 평가액", format_money(fruit_eval))
                m7.metric("🍯 누적 배당금", format_money(total_dividend_profit))

                st.markdown("---")
                st.markdown("### 📊 벤치마크 시장 지수 대비 수익률 초과 달성 리포트")
                b_col1, b_col2, b_col3 = st.columns(3)
                b_col1.metric("🛡️ 내 박가이버 작전 수익률", f"{total_return_pct:+.2f}%")
                if bench_synced:
                    b_col2.metric("📉 KOSPI 지수", f"{kospi_ret_pct:+.2f}%", delta=f"지수 대비 {(total_return_pct - kospi_ret_pct):+.2f}%p 초과")
                    b_col3.metric("📉 KOSDAQ 지수", f"{kosdaq_ret_pct:+.2f}%", delta=f"지수 대비 {(total_return_pct - kosdaq_ret_pct):+.2f}%p 초과")
                else:
                    b_col2.metric("📉 KOSPI 지수", "동기화 중")
                    b_col3.metric("📉 KOSDAQ 지수", "동기화 중")

                if sum(free_shares_dict.values()) > 0:
                    st.markdown("#### 📦 내 열매(무료 주식) 금고 상세 현황")
                    fruit_list = []
                    for s_name, count in free_shares_dict.items():
                        if count > 0:
                            t_code = PORTFOLIO_UNIVERSE[s_name]
                            c_p = float(last_row[t_code]) if t_code in last_row and not pd.isna(last_row[t_code]) else 0
                            fruit_list.append({"종목명": s_name, "보유 수량": f"{count}주", "현재가": format_exact_price(c_p), "평가액": format_money(count * c_p)})
                    st.dataframe(pd.DataFrame(fruit_list), use_container_width=True, hide_index=True)

                tab1, tab2, tab3, tab4 = st.tabs([
                    "📊 1. 자산 성장 & MDD 차트", 
                    "🔍 2. 자금 회전율 & 미출격 진단", 
                    "📈 3. 종목/연도별 손익분석", 
                    "📜 4. 현장 투입요원 & 매매장부"
                ])

                with tab1:
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3], subplot_titles=("총자산 증식 추이", "계좌 최대 낙폭 (MDD)"))
                    fig.add_trace(go.Scatter(x=asset_df['Date'], y=asset_df['Total_Asset'], mode='lines', name='내 총자산', line=dict(color='#2563eb', width=3), fill='tozeroy'), row=1, col=1)
                    if bench_synced:
                        fig.add_trace(go.Scatter(x=asset_df['Date'], y=asset_df['KOSPI'], mode='lines', name='KOSPI 지수', line=dict(color='#94a3b8', width=1.5, dash='dash')), row=1, col=1)
                        fig.add_trace(go.Scatter(x=asset_df['Date'], y=asset_df['KOSDAQ'], mode='lines', name='KOSDAQ 지수', line=dict(color='#cbd5e1', width=1.5, dash='dot')), row=1, col=1)
                    fig.add_hline(y=total_capital_input, line_dash="solid", line_color="#ef4444", annotation_text="원금", row=1, col=1)
                    fig.add_trace(go.Scatter(x=asset_df['Date'], y=asset_df['Drawdown'], mode='lines', name='낙폭(MDD)', line=dict(color='#dc2626', width=1.5), fill='tozeroy'), row=2, col=1)
                    fig.update_layout(height=650, template="plotly_white", margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified")
                    st.plotly_chart(fig, use_container_width=True)

                with tab2:
                    st.write("### 🔍 회전율 & 미출격 타점 분석 리포트")
                    st.warning(f"📊 기간 중 최대 동시 출격 수: **총 {global_max_deployed}개 종목** (전체 슬롯: {max_active_slots}개) | 🚨 태풍 경보 방어 차단: 총 {typhoon_blocked_count}일")
                    if daily_deployment_snapshots:
                        snap_df = pd.DataFrame(daily_deployment_snapshots)
                        st.write("▼ **역대 최고 자금 몰림(피크) 발생 일자 및 출격 목록:**")
                        st.dataframe(snap_df[snap_df['동시 출격 수'] == global_max_deployed].drop_duplicates(subset=['발생 일자']), use_container_width=True, hide_index=True)
                    st.markdown("---")
                    st.write("### 🚫 현금/슬롯/섹터/태풍 경보로 놓쳐버린 출격 타점 추적기")
                    if missed_opportunities:
                        st.error(f"🚨 타점이 맞았으나 제한으로 놓친 기회: 총 {len(missed_opportunities)}회")
                        st.dataframe(pd.DataFrame(missed_opportunities), use_container_width=True, hide_index=True)
                    else:
                        st.success("🎉 한 번도 현금이나 슬롯이 부족해서 출격 기회를 놓친 적이 없습니다!")

                with tab3:
                    st.write("### 📊 연도별 및 종목별 성적표")
                    c_col1, c_col2 = st.columns([1.2, 1])
                    with c_col1:
                        yearly_chart_data = []
                        for y, val in yearly_stats.items():
                            yearly_chart_data.append({"연도": str(y), "구분": "🎯 익절", "건수": val['success']})
                            yearly_chart_data.append({"연도": str(y), "구분": "🚨 손절", "건수": val['stop']})
                        fig_bar = px.bar(pd.DataFrame(yearly_chart_data), x="연도", y="건수", color="구분", barmode="group", color_discrete_map={"🎯 익절": "#22c55e", "🚨 손절": "#ef4444"})
                        st.plotly_chart(fig_bar, use_container_width=True)
                    with c_col2:
                        yearly_summary_list = []
                        for y, val in sorted(yearly_stats.items()):
                            yearly_summary_list.append({"연도": str(y), "🎯 익절": f"{val['success']}회", "🚨 손절": f"{val['stop']}회", "📦 획득 열매": f"{int(val['shares'])}주", "💵 현금수익": format_money(val['cash'])})
                        st.dataframe(pd.DataFrame(yearly_summary_list), use_container_width=True, hide_index=True)

                with tab4:
                    st.write("### ⚔️ 현재 현장 투입 요원 현황")
                    if len(active_positions) > 0:
                        active_table = []
                        for p in active_positions:
                            t_code = p['ticker']
                            c_price = float(last_row[t_code]) if t_code in last_row and not pd.isna(last_row[t_code]) else p['entry_price']
                            eval_val = p['invest_amount'] * (c_price / p['entry_price'])
                            ret = ((c_price - p['entry_price']) / p['entry_price']) * 100
                            active_table.append({
                                '요원': p['name'], '구역명': p['stock_name'], '출격일': p['entry_date'],
                                '진입단가': format_exact_price(p['entry_price']),
                                '진입금액': f"{format_pure_number(p['invest_amount'])}원",
                                '현재 평가금액': f"{format_pure_number(eval_val)}원",
                                '현재수익률': f"{ret:.2f}%"
                            })
                        st.dataframe(pd.DataFrame(active_table), use_container_width=True, hide_index=True)
                    else:
                        st.success("🎉 현재 현장에 대기 중인 요원이 없습니다! (100% 현금 회수 완료)")

                    st.markdown("---")
                    st.write("### 📜 전체 매매 장부")
                    if trade_logs:
                        logs_df = pd.DataFrame(list(reversed(trade_logs)))
                        st.dataframe(logs_df, use_container_width=True)
                        
                        csv_data = logs_df.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label="📥 엑셀(CSV) 매매장부 다운로드",
                            data=csv_data,
                            file_name=f"당귀다TV_매매장부_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
