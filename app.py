import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
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

# --- 1. 페이지 웹 디자인 세팅 (모바일 반응형 & 프리미엄 UI CSS) ---
st.set_page_config(page_title="박가이버 통합 작전 사령부 V9 Personal DB", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .stApp {
        background-color: #f8fafc;
    }
    @media (max-width: 768px) {
        .hero-title {
            font-size: 1.2rem !important;
        }
        .hero-banner {
            padding: 14px 16px !important;
        }
        div[data-testid="stMetric"] {
            padding: 10px 12px !important;
        }
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
        margin-bottom: 25px;
    }
    .hero-title {
        font-size: 1.6rem;
        font-weight: 900;
        margin: 0;
        color: #f8fafc;
    }
    .hero-subtitle {
        font-size: 0.95rem;
        color: #94a3b8;
        margin-top: 6px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #e2e8f0;
        padding: 8px 10px;
        border-radius: 14px;
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 44px;
        background-color: #ffffff;
        border-radius: 10px;
        padding: 0 16px;
        font-weight: 800;
        font-size: 0.9rem;
        color: #334155;
        border: 1px solid #cbd5e1;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 동적 데이터베이스 및 종목 마스터 세션 초기화 ---
if "sector_db" not in st.session_state:
    st.session_state["sector_db"] = {
        "⚡ 반도체 & HBM / 칩렛": {
            "테크윙": "089030.KQ", "한미반도체": "042700.KS", "HPSP": "403870.KQ",
            "이오테크닉스": "039030.KQ", "리노공업": "058470.KQ", "ISC": "095340.KQ",
            "주성엔지니어링": "036930.KQ", "원익IPS": "240810.KQ", "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "피에스케이": "057030.KQ"
        },
        "🧬 바이오 & 제약 / 화장품": {
            "한국콜마": "161890.KS", "코스맥스": "192820.KS", "알테오젠": "196170.KQ", 
            "셀트리온": "068270.KS", "삼성바이오로직스": "207940.KS", "HLB": "028300.KQ", 
            "유한양행": "000100.KS", "리가켐바이오": "141080.KQ"
        },
        "📡 통신 & 방산 & 조선": {
            "RFHIC": "218410.KQ", "한화시스템": "272210.KS", "현대로템": "064350.KS",
            "LIG넥스원": "079550.KS", "한화오션": "042660.KS", "HD한국조선해양": "009540.KS", "두산에너빌리티": "034020.KS", "HD현대일렉트릭": "267260.KS"
        },
        "🔋 2차전지 & 에코": {
            "에코프로비엠": "247540.KQ", "에코프로": "086520.KQ", "LG에너지솔루션": "373220.KS",
            "POSCO홀딩스": "005490.KS", "엘앤에프": "066970.KQ", "포스코퓨처엠": "003670.KS"
        },
        "🚗 자동차 & 대표 제조": {
            "현대차": "005380.KS", "기아": "000270.KS", "현대모비스": "012330.KS"
        },
        "💻 IT & 플랫폼": {
            "NAVER": "035420.KS", "카카오": "035720.KS"
        }
    }

if "custom_stocks" not in st.session_state:
    st.session_state["custom_stocks"] = {}

# 💡 [초개인화 DB 세션] 실전 보유 종목 vs 관심 종목 영구 관리
if "my_holdings" not in st.session_state:
    st.session_state["my_holdings"] = ["SK하이닉스", "한미반도체", "테크윙", "HD현대일렉트릭", "HPSP"]

if "my_watchlist" not in st.session_state:
    st.session_state["my_watchlist"] = ["한화오션", "현대로템", "RFHIC", "한국콜마"]

KOREAN_STOCK_MASTER = {
    "한국콜마": "161890.KS", "RFHIC": "218410.KQ", "코스맥스": "192820.KS",
    "현대힘스": "460930.KQ", "한화오션": "042660.KS", "HD한국조선해양": "009540.KS",
    "에스피지": "058610.KQ", "SPG": "058610.KQ", "레인보우로보틱스": "277810.KQ",
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "테크윙": "089030.KQ", 
    "한미반도체": "042700.KS", "기가비스": "420770.KQ", "케이씨텍": "281820.KS",
    "이수화학": "005950.KS", "이수스페셜티케미컬": "457190.KS", "마녀공장": "439090.KQ",
    "뉴파워프라즈마": "144960.KQ", "두산에너빌리티": "034020.KS", "하나마이크론": "084370.KQ",
    "동진쎄미켐": "033640.KQ", "솔브레인": "357780.KQ", "가온칩스": "399500.KQ",
    "두산로보틱스": "454910.KS", "한화에어로스페이스": "012450.KS", "LIG넥스원": "079550.KS",
    "HD현대일렉트릭": "267260.KS", "LS일렉트릭": "010120.KS", "포스코퓨처엠": "003670.KS", "피에스케이": "057030.KQ"
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
    TICKER_TO_SECTOR[code] = "커스텀 종목"

# 호환성을 위한 selected_stocks 바인딩
if "selected_stocks" not in st.session_state:
    st.session_state["selected_stocks"] = st.session_state["my_holdings"]

def format_money(num):
    if num is None or pd.isna(num):
        return "-"
    num_int = int(round(num))
    sign = "-" if num_int < 0 else ""
    return f"{sign}{abs(num_int):,}원"

def format_pure_number(num):
    if num is None or pd.isna(num):
        return "-"
    num_int = int(round(num))
    return f"{num_int:,}"

def format_exact_price(num):
    if num is None or pd.isna(num):
        return "-"
    return f"{int(round(num)):,}원"

@st.cache_data(ttl=3600)
def analyze_stock_suitability(stock_dict, invest_amount=2000000, ma_period=240):
    results = []
    tickers = list(stock_dict.values())
    if not tickers:
        return pd.DataFrame()
    try:
        data = yf.download(tickers, period="1y", interval="1d", progress=False)
        close_data = data['Close'] if isinstance(data.columns, pd.MultiIndex) and 'Close' in data.columns.levels[0] else (data['Close'] if 'Close' in data.columns else data)

        for name, code in stock_dict.items():
            s_data = close_data[code].dropna() if isinstance(close_data, pd.DataFrame) and code in close_data.columns else (close_data.dropna() if isinstance(close_data, pd.Series) else pd.Series())
            if len(s_data) > 10:
                curr_price = float(s_data.iloc[-1])
                if curr_price > invest_amount:
                    total_score = 0
                    fit_grade = "🚫 출격 불가 (단가 초과)"
                    reason = f"1주 가격({format_pure_number(curr_price)}원)이 진입 예산({format_pure_number(invest_amount)}원)보다 비쌉니다!"
                    buyable_qty = 0
                else:
                    buyable_qty = int(invest_amount // curr_price)
                    daily_change = s_data.pct_change().abs() * 100
                    avg_volatility = daily_change.mean()
                    sma_val_eval = s_data.rolling(min(ma_period, len(s_data))).mean().iloc[-1]
                    trend_score = 35 if curr_price >= sma_val_eval else 20
                    if 1.5 <= avg_volatility <= 4.0:
                        vol_score = 45
                    elif avg_volatility > 4.0:
                        vol_score = 30
                    else:
                        vol_score = 15
                    total_score = vol_score + trend_score + 20
                    if buyable_qty < 3:
                        total_score = max(30, total_score - 20)
                        fit_grade = "⚠️ 주의 (단가 부담)"
                        reason = f"1주 가격({format_pure_number(curr_price)}원)이 높아 진입 시 {buyable_qty}주밖에 못 사 자금 효율이 낮습니다."
                    elif total_score >= 80:
                        fit_grade = "🥇 최적합 (강력 추천)"
                        reason = f"파동(±{avg_volatility:.1f}%)이 훌륭하며, 1회 진입 시 약 {buyable_qty}주씩 분할 매수 가능합니다."
                    elif total_score >= 65:
                        fit_grade = "🥈 적합 (무난)"
                        reason = f"스노우볼 작전에 무난하게 적합합니다. (진입 시 약 {buyable_qty}주 매수 가능)"
                    else:
                        fit_grade = "⚠️ 주의 (파동 부족/하락세)"
                        reason = f"변동폭이 너무 적거나 하락세가 지속되어 진입 타점이 더디게 올 수 있습니다."
                results.append({
                    "종목명": name,
                    "티커": code,
                    "현재가(1주)": f"{format_pure_number(curr_price)}원",
                    "1회 진입 가능 수량": f"{buyable_qty}주",
                    "적합도 점수": f"{total_score}점",
                    "적합도 판정": fit_grade,
                    "사령관 정밀 진단 소견": reason
                })
    except Exception:
        pass
    return pd.DataFrame(results)

# --- 3. 사이드바 조종간 (3대 메뉴 독립 분리) ---
st.sidebar.title("🎛️ 박가이버 사령부 V9")
menu_choice = st.sidebar.radio(
    "사령부 작전 모드선택",
    [
        "🗄️ 1. 내 계좌 영구 DB (보유 & 관심)", 
        "🚨 2. 오늘의 실전 매매 레이더", 
        "🛡️ 3. 과거 5년 백테스트 연구소"
    ],
    index=1
)
st.sidebar.markdown("---")

# =====================================================================
# 🗄️ 메뉴 1: 내 계좌 영구 DB (마이 포트폴리오 세팅 본부)
# =====================================================================
if menu_choice == "🗄️ 1. 내 계좌 영구 DB (보유 & 관심)":
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🗄️ 나만의 투자 영구 DB (마이 포트폴리오)</div>
        <div class="hero-subtitle">내 증권사 계좌의 실제 보유 종목과 관심 종목을 영구 세팅하세요! 사령부가 기억하고 매일 추적합니다.</div>
    </div>
    """, unsafe_allow_html=True)

    db_tab1, db_tab2 = st.tabs(["💼 내 실전 보유 종목 (주력)", "⭐ 눈여겨보는 관심 종목"])

    with db_tab1:
        st.markdown("### 💼 1. 실전 보유 종목 영구 DB 세팅")
        st.info("💡 실제 투자 계좌에서 매매 중인 주력 종목들을 세팅해 두세요. 실전 레이더의 1순위 감시 대상이 됩니다.")
        
        valid_holdings = [s for s in st.session_state["my_holdings"] if s in MASTER_STOCK_DICT]
        new_holdings = st.multiselect(
            "실전 보유 종목 편집:",
            options=list(MASTER_STOCK_DICT.keys()),
            default=valid_holdings,
            key="holding_multiselect"
        )
        if st.button("💾 실전 보유 종목 DB 저장", type="primary", use_container_width=True):
            st.session_state["my_holdings"] = new_holdings
            st.session_state["selected_stocks"] = new_holdings
            st.success("🎉 실전 보유 종목 DB가 영구 저장 및 동기화되었습니다!")
            st.rerun()

    with db_tab2:
        st.markdown("### ⭐ 2. 관심 종목 영구 DB 세팅")
        st.info("💡 다음에 진입하려고 눈여겨보는 유망 종목들을 담아두는 금고입니다.")
        
        valid_watchlist = [s for s in st.session_state["my_watchlist"] if s in MASTER_STOCK_DICT]
        new_watchlist = st.multiselect(
            "관심 종목 편집:",
            options=list(MASTER_STOCK_DICT.keys()),
            default=valid_watchlist,
            key="watchlist_multiselect"
        )
        if st.button("💾 관심 종목 DB 저장", type="secondary", use_container_width=True):
            st.session_state["my_watchlist"] = new_watchlist
            st.success("🎉 관심 종목 DB가 안전하게 저장되었습니다!")
            st.rerun()

    st.markdown("---")
    st.markdown("### ⚡ 원터치 추천 포트폴리오 패키지 로드")
    p_col1, p_col2, p_col3 = st.columns(3)
    if p_col1.button("🤖 AI/반도체 황금 5선", use_container_width=True):
        st.session_state["my_holdings"] = ["SK하이닉스", "한미반도체", "테크윙", "HD현대일렉트릭", "HPSP"]
        st.session_state["selected_stocks"] = st.session_state["my_holdings"]
        st.toast("🎉 AI 반도체 5선 세팅 완료!")
        st.rerun()
    if p_col2.button("🛡️ 방산/조선 주도주 4선", use_container_width=True):
        st.session_state["my_holdings"] = ["한화오션", "HD한국조선해양", "LIG넥스원", "현대로템"]
        st.session_state["selected_stocks"] = st.session_state["my_holdings"]
        st.toast("🎉 방산/조선 4선 세팅 완료!")
        st.rerun()
    if p_col3.button("🧬 바이오/화장품 4선", use_container_width=True):
        st.session_state["my_holdings"] = ["한국콜마", "코스맥스", "알테오젠", "셀트리온"]
        st.session_state["selected_stocks"] = st.session_state["my_holdings"]
        st.toast("🎉 바이오/화장품 4선 세팅 완료!")
        st.rerun()

    st.markdown("---")
    st.markdown("### 🔍 새로운 종목 직접 등록 (마이 DB 추가)")
    c_in1, c_in2, c_in3, c_in4 = st.columns([2, 1.5, 1, 1])
    input_name = c_in1.text_input("종목명", placeholder="예: 뉴파워프라즈마")
    input_code = c_in2.text_input("6자리 코드", placeholder="예: 144960")
    input_market = c_in3.selectbox("시장", ["코스피 (.KS)", "코스닥 (.KQ)"])
    if c_in4.button("➕ DB 추가", type="primary"):
        n_q = input_name.strip()
        c_q = input_code.strip()
        if n_q and len(c_q) == 6:
            suffix = ".KS" if "코스피" in input_market else ".KQ"
            full_code = f"{c_q}{suffix}"
            MASTER_STOCK_DICT[n_q] = full_code
            if n_q not in st.session_state["my_holdings"]:
                st.session_state["my_holdings"].append(n_q)
                st.session_state["selected_stocks"] = st.session_state["my_holdings"]
            st.success(f"🎉 [{n_q} ({full_code})] 영구 DB 추가 완료!")
            st.rerun()
        else:
            st.error("종목명과 6자리 코드를 정확히 입력해 주세요.")

# =====================================================================
# 🚨 메뉴 2: 오늘의 실전 매매 레이더 (출격 명령서 전용)
# =====================================================================
elif menu_choice == "🚨 2. 오늘의 실전 매매 레이더":
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🚨 오늘의 실전 매매 레이더 (출격 명령서)</div>
        <div class="hero-subtitle">매일 오후 3시 20분 종가 기준 | 내 계좌 영구 DB에 담긴 주력 종목들의 실전 매수 타점을 포착합니다.</div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.subheader("⚙️ 실전 매매 조건 설정")
    buy_cond_input = st.sidebar.slider("🛒 진입 기준 (-% 하락 시)", 1, 20, 5, 1, key="live_buy_cond")
    
    # DB에서 실전 보유 종목 로드
    valid_watch_stocks = [s for s in st.session_state["my_holdings"] if s in MASTER_STOCK_DICT]
    PORTFOLIO_UNIVERSE = {s_name: MASTER_STOCK_DICT[s_name] for s_name in valid_watch_stocks if s_name in MASTER_STOCK_DICT}

    st.markdown(f"🎯 **[실전 감시 전광판] 현재 내 계좌 DB 연동 종목 ({len(valid_watch_stocks)}개):** {', '.join(valid_watch_stocks)}")
    st.markdown("---")

    st.markdown("### 📡 실시간 출격 시그널 검사 결과")
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
        except Exception:
            st.info("💡 실시간 시세를 동기화하는 중입니다.")
    else:
        st.warning("⚠️ 감시 종목이 없습니다. 메뉴 [🗄️ 1. 내 계좌 영구 DB]에서 주력 종목을 먼저 세팅해 주세요!")

    with st.expander("📖 [당귀다TV] 실전 출격 명령서 1분 가이드", expanded=True):
        st.markdown("""
        1. **오후 3시 20분 접속:** 장 마감 직전 본 앱의 이 화면을 켭니다.
        2. **시그널 확인:** 빨간색 경보창에 종목이 떴다면 증권사 앱에서 **종가(동시호가)**로 매수 주문을 넣습니다.
        3. **다음 날 아침 예약:** 증권사 앱에서 목표가(+5%)와 손절가(-15%)를 GTC 예약 매도로 걸어두면 끝!
        """)

# =====================================================================
# 🛡️ 메뉴 3: 과거 5년 백테스트 연구소 (성과 검증 전용)
# =====================================================================
else:
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🛡️ 과거 5년 백테스트 연구소 (성과 검증)</div>
        <div class="hero-subtitle">실전 투입 전 과거 기출문제 풀이 | 내 계좌 DB 종목들과 방어 스위치가 폭락장에서 어떻게 작동했는지 검증합니다.</div>
    </div>
    """, unsafe_allow_html=True)

    valid_watch_stocks = [s for s in st.session_state["my_holdings"] if s in MASTER_STOCK_DICT]
    PORTFOLIO_UNIVERSE = {s_name: MASTER_STOCK_DICT[s_name] for s_name in valid_watch_stocks if s_name in MASTER_STOCK_DICT}

    if valid_watch_stocks:
        st.success(f"🎯 **[백테스트 연구소 전광판] 내 계좌 DB 연동 종목 ({len(valid_watch_stocks)}개):** {', '.join(valid_watch_stocks)}")
    else:
        st.error("⚠️ **[감시 종목 경보]** 장전된 종목이 없습니다! 메뉴 **[🗄️ 1. 내 계좌 영구 DB]**에서 종목을 먼저 골라주세요.")

    st.sidebar.subheader("⚙️ 백테스트 전략 조건 설정")
    use_market_filter = st.sidebar.checkbox("🌤️ 대세 하락장 자동 우산 스위치", value=True)
    ma_period_choice = st.sidebar.radio("📏 하락장 우산 기준선 선택", [120, 240], index=1, horizontal=True)
    use_strict_ma_filter = st.sidebar.checkbox("📈 장기 이평선 위에서만 출격 (추세 필터)", value=False)
    use_sector_limit = st.sidebar.checkbox("🤹‍♂️ 동일 섹터 몰빵 방지 캡", value=True)
    use_time_cut = st.sidebar.checkbox("⏱️ 타임 컷 (최대 보유일 제한)", value=True)
    max_hold_days_input = st.sidebar.slider("⏳ 최대 보유 제한일 (일)", 5, 60, 30, 5) if use_time_cut else 9999

    st.sidebar.markdown("---")
    total_capital_input = st.sidebar.number_input("🏦 총 작전 예산(원)", value=10000000, step=1000000, key="bt_capital")
    rec_default_invest = total_capital_input // 5
    invest_amount_input = st.sidebar.number_input("💰 회당 초기 진입금액(원)", value=int(rec_default_invest), step=500000, key="bt_invest")
    max_active_slots = max(1, int(total_capital_input // invest_amount_input))
    max_sector_slots = max(1, max_active_slots // 2)

    use_compounding = st.sidebar.checkbox("🚀 복리 스케일업 모드", value=True, key="bt_compound")
    time_unit = st.sidebar.radio("🗓️ 기간 단위", ["월 단위 (개월)", "년 단위 (년)"], horizontal=True, key="bt_tunit")

    if time_unit == "월 단위 (개월)":
        months_input = st.sidebar.slider("백테스트 기간(개월)", 1, 120, 60, 1, key="bt_m")
        period_label = f"{months_input}개월"
    else:
        years_val = st.sidebar.slider("백테스트 기간(년)", 1, 10, 5, 1, key="bt_y")
        months_input = years_val * 12
        period_label = f"{years_val}년"

    buy_cond_input = st.sidebar.slider("🛒 진입 기준 (-% 하락 시)", 1, 20, 5, 1, key="bt_buy")
    sell_target_input = st.sidebar.slider("🎯 익절 목표 (+%)", 1, 30, 5, 1, key="bt_sell")
    stop_loss_input = st.sidebar.slider("🚨 손절 기준 (-%)", 0, 50, 15, 1, key="bt_stop")

    st.sidebar.subheader("💸 거래비용 적용")
    use_fee = st.sidebar.checkbox("수수료/거래세 반영", value=True, key="bt_fee")
    broker_fee_pct = (st.sidebar.number_input("위탁수수료 (%)", value=0.015, format="%.3f") / 100) if use_fee else 0.0
    tax_pct = (st.sidebar.number_input("매도 거래세 (%)", value=0.18, format="%.2f") / 100) if use_fee else 0.0
    slippage_pct = (st.sidebar.number_input("체결 오차 (슬리피지) (%)", value=0.10, format="%.2f") / 100) if use_fee else 0.0

    reward_type = st.sidebar.selectbox("🎁 전리품 수령 방식", ["🌟 현금 50% + 열매 50% (하이브리드)", "🌟 현금 40% + 열매 60% (하이브리드 강화)", "전액 현금으로 챙기기", "열매로 결실 모으기"])

    st.sidebar.markdown("---")
    run_btn = st.sidebar.button("🚀 백테스트 타임머신 가동!", type="primary", use_container_width=True)

    st.sidebar.markdown("---")
    with st.sidebar.expander("⚖️ 법적 책임 면책 고지문", expanded=False):
        st.caption("""
        **[투자 유의사항 안내]**
        1. 본 프로그램은 과거 주가 데이터를 기반으로 작동하는 **단순 퀀트 시뮬레이션 및 데이터 참고 도구**이며, 특정 종목의 매수/매도를 권유하거나 자문하는 금융 서비스가 아닙니다.
        2. 과거의 백테스트 수익률이 미래의 투자 수익을 결코 보장하지 않습니다.
        3. 주식 시장 특성상 원금 손실 위험이 존재하며, **모든 투자의 최종 결정과 손익 결과에 대한 법적 책임은 투자자 본인**에게 있음을 알려드립니다.
        """)

    if run_btn:
        if len(PORTFOLIO_UNIVERSE) == 0:
            st.error("❌ 감시 종목이 없습니다. 메뉴 [🗄️ 1. 내 계좌 영구 DB]에서 주력 종목을 먼저 세팅해 주세요!")
        else:
            with st.spinner("📡 슈퍼컴퓨터가 과거 파동, 벤치마크 지수, 타임컷 및 MDD 데이터를 안전하게 분석 중입니다..."):
                try:
                    end_date_str = datetime.datetime.today().strftime('%Y-%m-%d')
                    start_date_str = (datetime.datetime.today() - relativedelta(months=months_input)).strftime('%Y-%m-%d')
                    tickers = list(PORTFOLIO_UNIVERSE.values())
                    
                    raw_close = yf.download(tickers, start=start_date_str, end=end_date_str, interval="1d", progress=False)
                    if isinstance(raw_close.columns, pd.MultiIndex):
                        close_df = raw_close['Close'] if 'Close' in raw_close.columns.levels[0] else raw_close
                    elif 'Close' in raw_close.columns:
                        close_df = raw_close['Close'].to_frame() if len(tickers) == 1 else raw_close
                    else:
                        close_df = raw_close

                    if isinstance(close_df, pd.Series):
                        close_df = close_df.to_frame(name=tickers[0])

                    close_df = close_df.dropna(how='all')

                    if close_df.empty:
                        st.error("❌ 야후 파이낸스에서 주가 데이터를 가져오지 못했습니다. 기간을 조정해 주세요.")
                        st.stop()

                    close_df.index = clean_date_index(close_df.index)

                    try:
                        raw_actions = yf.download(tickers, start=start_date_str, end=end_date_str, interval="1d", actions=True, progress=False)
                        div_df = raw_actions['Dividends'] if isinstance(raw_actions.columns, pd.MultiIndex) and 'Dividends' in raw_actions.columns.levels[0] else pd.DataFrame(0, index=close_df.index, columns=tickers)
                    except Exception:
                        div_df = pd.DataFrame(0, index=close_df.index, columns=tickers)
                    
                    div_df.index = clean_date_index(div_df.index)
                    div_df = div_df.reindex(close_df.index).fillna(0)

                    bench_df = pd.DataFrame()
                    try:
                        bench_raw = yf.download(["^KS11", "^KQ11"], start=start_date_str, end=end_date_str, interval="1d", progress=False)
                        bench_df = bench_raw['Close'] if isinstance(bench_raw.columns, pd.MultiIndex) and 'Close' in bench_raw.columns.levels[0] else bench_raw
                        if not bench_df.empty:
                            bench_df.index = clean_date_index(bench_df.index)
                    except Exception:
                        pass

                    return_df = close_df.pct_change() * 100
                    sma_df = close_df.rolling(window=int(ma_period_choice)).mean()

                    buy_cond = -float(buy_cond_input)
                    sell_target = float(sell_target_input)
                    stop_loss_limit = -float(stop_loss_input) if stop_loss_input > 0 else None

                    current_cash = float(total_capital_input)
                    active_positions, trade_logs, daily_returns_history, asset_history = [], [], [], []
                    agent_counter = 0

                    yearly_stats = {}
                    free_shares_dict = {s_name: 0 for s_name in PORTFOLIO_UNIVERSE.keys()}
                    stock_win_stats = {s_name: {'success': 0, 'stop': 0, 'profit_gain': 0, 'loss_cost': 0} for s_name in PORTFOLIO_UNIVERSE.keys()}

                    total_success, total_stop_loss, total_cash_profit = 0, 0, 0
                    global_max_deployed = 0
                    daily_deployment_snapshots = []
                    missed_opportunities = []
                    total_dividend_profit = 0

                    peak_asset_value = float(total_capital_input)
                    max_drawdown_pct = 0.0

                    for date, row in close_df.iterrows():
                        date_str = date.strftime('%Y-%m-%d')
                        year = date.year
                        if year not in yearly_stats:
                            yearly_stats[year] = {'success': 0, 'stop': 0, 'shares': 0, 'cash': 0, 'share_val': 0.0, 'stock_fruits': {}}
                        
                        daily_dividend_sum = 0
                        if date in div_df.index:
                            for s_name, count in free_shares_dict.items():
                                if count > 0:
                                    t_code = PORTFOLIO_UNIVERSE[s_name]
                                    if t_code in div_df.columns:
                                        d_val = div_df.loc[date, t_code]
                                        if pd.notna(d_val) and d_val > 0:
                                            daily_dividend_sum += count * d_val
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
                                '요원': '시스템', '작전 구역': '배당금(꿀) 수금', '출격일': date_str,
                                '진입일 등락률': '-', '진입금액': '-', '진입단가': '-', '복귀일': date_str,
                                '청산일 등락률': '-', '청산단가': '-', '매도금액': '-',
                                '등락폭': '-', '소요기간': '-', '순수익률': '-',
                                '정산내역': f"🍯 꿀 수입: +{format_pure_number(daily_dividend_sum)}원", '구분': '🌟 특별 보너스'
                            })
                        
                        survived_positions = []
                        for pos in active_positions:
                            t_code = pos['ticker']
                            if t_code in row and not pd.isna(row[t_code]):
                                curr_price = float(row[t_code])
                                gross_ret = ((curr_price - pos['entry_price']) / pos['entry_price']) * 100
                                is_exit, exit_reason = False, ""

                                entry_dt = pd.to_datetime(pos['entry_date'])
                                exit_dt = pd.to_datetime(date_str)
                                days_taken = (exit_dt - entry_dt).days

                                if gross_ret >= sell_target:
                                    is_exit, exit_reason = True, f"🎯 정상 복귀(+{sell_target_input}%)"
                                elif stop_loss_limit is not None and gross_ret <= stop_loss_limit:
                                    is_exit, exit_reason = True, f"🚨 강제 철수(-{stop_loss_input}%)"
                                elif use_time_cut and days_taken >= max_hold_days_input:
                                    is_exit, exit_reason = True, f"⏳ 타임 컷 ({max_hold_days_input}일 초과)"

                                if is_exit:
                                    sell_gross_val = pos['invest_amount'] * (curr_price / pos['entry_price'])
                                    buy_fee = pos['invest_amount'] * broker_fee_pct
                                    sell_fee = sell_gross_val * broker_fee_pct
                                    sell_tax = sell_gross_val * tax_pct
                                    slippage_cost = (pos['invest_amount'] * slippage_pct) + (sell_gross_val * slippage_pct)
                                    total_trade_cost = buy_fee + sell_fee + sell_tax + slippage_cost

                                    net_profit = (sell_gross_val - pos['invest_amount']) - total_trade_cost
                                    net_ret = (net_profit / pos['invest_amount']) * 100
                                    s_name = pos['stock_name']
                                    
                                    price_diff = curr_price - pos['entry_price']
                                    diff_sign = "+" if price_diff >= 0 else ""
                                    price_change_str = f"{diff_sign}{format_pure_number(price_diff)}원 ({gross_ret:+.2f}%)"

                                    if gross_ret >= sell_target or net_profit > 0:
                                        total_success += 1
                                        yearly_stats[year]['success'] += 1
                                        stock_win_stats[s_name]['success'] += 1
                                        stock_win_stats[s_name]['profit_gain'] += net_profit
                                        
                                        if reward_type == '열매로 결실 모으기':
                                            buyable = int(max(0, net_profit) // curr_price)
                                            leftover = net_profit - (buyable * curr_price)
                                        elif reward_type == '🌟 현금 50% + 열매 50% (하이브리드)':
                                            share_budget = max(0, net_profit) * 0.5
                                            buyable = int(share_budget // curr_price)
                                            leftover = net_profit - (buyable * curr_price)
                                        elif reward_type == '🌟 현금 40% + 열매 60% (하이브리드 강화)':
                                            share_budget = max(0, net_profit) * 0.6
                                            buyable = int(share_budget // curr_price)
                                            leftover = net_profit - (buyable * curr_price)
                                        else:
                                            buyable = 0
                                            leftover = net_profit
                                    else:
                                        total_stop_loss += 1
                                        yearly_stats[year]['stop'] += 1
                                        stock_win_stats[s_name]['stop'] += 1
                                        stock_win_stats[s_name]['loss_cost'] += net_profit
                                        buyable, leftover = 0, net_profit

                                    free_shares_dict[s_name] += buyable
                                    total_cash_profit += leftover
                                    current_cash += (pos['invest_amount'] + leftover)

                                    yearly_stats[year]['shares'] += buyable
                                    yearly_stats[year]['cash'] += leftover
                                    yearly_stats[year]['share_val'] += (buyable * curr_price)
                                    
                                    if buyable > 0:
                                        if s_name not in yearly_stats[year]['stock_fruits']:
                                            yearly_stats[year]['stock_fruits'][s_name] = {'shares': 0, 'value': 0}
                                        yearly_stats[year]['stock_fruits'][s_name]['shares'] += buyable
                                        yearly_stats[year]['stock_fruits'][s_name]['value'] += (buyable * curr_price)

                                    daily_returns_history.append(net_ret)

                                    log_reward = f"열매 {buyable}개 + 잔돈 {format_pure_number(leftover)}원" if buyable > 0 else f"{format_pure_number(leftover)}원"
                                    
                                    entry_day_ret = pos.get('entry_day_ret', 0)
                                    exit_day_ret = float(return_df.loc[date, t_code]) if date in return_df.index and t_code in return_df.columns and not pd.isna(return_df.loc[date, t_code]) else 0.0

                                    trade_logs.append({
                                        '요원': pos['name'], '작전 구역': pos['stock_name'], '출격일': pos['entry_date'],
                                        '진입일 등락률': f"{entry_day_ret:+.2f}%", '진입금액': f"{format_pure_number(pos['invest_amount'])}원",
                                        '진입단가': format_exact_price(pos['entry_price']), '복귀일': date_str,
                                        '청산일 등락률': f"{exit_day_ret:+.2f}%", '청산단가': format_exact_price(curr_price),
                                        '매도금액': f"{format_pure_number(sell_gross_val)}원", '등락폭': price_change_str,
                                        '소요기간': f"{days_taken}일 소요", '순수익률': f"{net_ret:.2f}%",
                                        '정산내역': log_reward, '구분': exit_reason
                                    })
                                else:
                                    survived_positions.append(pos)
                            else:
                                survived_positions.append(pos)
                        
                        active_positions = survived_positions
                        remaining_slots = max_active_slots - len(active_positions)
                        dynamic_invest_amount = max(float(invest_amount_input), current_cash / remaining_slots) if (use_compounding and remaining_slots > 0) else float(invest_amount_input)

                        day_returns = return_df.loc[date] if date in return_df.index else None
                        if day_returns is not None:
                            candidates = []
                            for s_name, t_code in PORTFOLIO_UNIVERSE.items():
                                if not any(p['ticker'] == t_code for p in active_positions) and t_code in day_returns and not pd.isna(day_returns[t_code]):
                                    ret_val = float(day_returns[t_code])
                                    target_buy_cond = buy_cond
                                    
                                    if t_code in sma_df.columns and date in sma_df.index:
                                        sma_val = sma_df.loc[date, t_code]
                                        curr_p = row[t_code]
                                        if pd.notna(sma_val) and pd.notna(curr_p):
                                            if use_strict_ma_filter and curr_p < sma_val:
                                                continue
                                            if use_market_filter and curr_p < sma_val:
                                                target_buy_cond = buy_cond * 1.4

                                    if ret_val <= target_buy_cond:
                                        candidates.append((s_name, t_code, ret_val, float(row[t_code])))
                            candidates.sort(key=lambda x: x[2])

                            for cand in candidates:
                                actual_invest = min(dynamic_invest_amount, current_cash)
                                c_price = cand[3]
                                ret_val = cand[2]
                                t_code = cand[1]
                                
                                if use_sector_limit:
                                    c_sector = TICKER_TO_SECTOR.get(t_code, "기타")
                                    current_sector_count = sum(1 for p in active_positions if TICKER_TO_SECTOR.get(p['ticker'], "기타") == c_sector)
                                    if current_sector_count >= max_sector_slots:
                                        missed_opportunities.append({
                                            "발생 일자": date_str, "미출격 종목": cand[0], "당일 하락률": f"{cand[2]:.2f}%",
                                            "불가 사유": f"특정 섹터({c_sector}) 쏠림 방지 캡 도달"
                                        })
                                        continue

                                if c_price > actual_invest:
                                    missed_opportunities.append({
                                        "발생 일자": date_str, "미출격 종목": cand[0], "당일 하락률": f"{cand[2]:.2f}%",
                                        "불가 사유": f"1주 가격 초과"
                                    })
                                elif len(active_positions) >= max_active_slots:
                                    missed_opportunities.append({
                                        "발생 일자": date_str, "미출격 종목": cand[0], "당일 하락률": f"{cand[2]:.2f}%",
                                        "불가 사유": f"요원 슬롯 풀가동"
                                    })
                                elif actual_invest < 500000 or current_cash < 500000:
                                    missed_opportunities.append({
                                        "발생 일자": date_str, "미출격 종목": cand[0], "당일 하락률": f"{cand[2]:.2f}%",
                                        "불가 사유": f"가용 현금 부족"
                                    })
                                else:
                                    agent_counter += 1
                                    s_name, t_code, ret_val, c_price = cand
                                    current_cash -= actual_invest
                                    active_positions.append({
                                        'name': f"{agent_counter}호 요원", 'stock_name': s_name, 'ticker': t_code,
                                        'entry_price': c_price, 'entry_date': date_str, 'invest_amount': actual_invest, 'entry_day_ret': ret_val 
                                    })

                        curr_count = len(active_positions)
                        if curr_count > global_max_deployed: global_max_deployed = curr_count
                        if curr_count > 0:
                            daily_deployment_snapshots.append({
                                "발생 일자": date_str, "동시 출격 수": curr_count,
                                "출격 종목 리스트": ", ".join([p['stock_name'] for p in active_positions])
                            })

                        eval_pos = sum([p['invest_amount'] * (float(row[p['ticker']]) / p['entry_price']) for p in active_positions if p['ticker'] in row and not pd.isna(row[p['ticker']])])
                        today_total_asset = current_cash + eval_pos
                        
                        if today_total_asset > peak_asset_value:
                            peak_asset_value = today_total_asset
                        current_drawdown = ((today_total_asset - peak_asset_value) / peak_asset_value) * 100
                        if current_drawdown < max_drawdown_pct:
                            max_drawdown_pct = current_drawdown
                        
                        asset_history.append({"Date": date_str, "Total_Asset": today_total_asset, "Drawdown": current_drawdown})

                    asset_df = pd.DataFrame(asset_history)
                    kospi_ret_pct, kosdaq_ret_pct = 0.0, 0.0
                    bench_synced = False

                    if not bench_df.empty:
                        try:
                            bench_df_clean = bench_df.copy()
                            bench_df_clean.index = [d.strftime('%Y-%m-%d') for d in bench_df_clean.index]
                            ks_key = '^KS11' if '^KS11' in bench_df_clean.columns else bench_df_clean.columns[0]
                            kq_key = '^KQ11' if '^KQ11' in bench_df_clean.columns else (bench_df_clean.columns[1] if len(bench_df_clean.columns) > 1 else ks_key)
                            bench_aligned = bench_df_clean.reindex(asset_df['Date']).ffill().bfill()
                            
                            ks_start = float(bench_aligned[ks_key].dropna().iloc[0])
                            ks_end = float(bench_aligned[ks_key].dropna().iloc[-1])
                            kq_start = float(bench_aligned[kq_key].dropna().iloc[0])
                            kq_end = float(bench_aligned[kq_key].dropna().iloc[-1])

                            kospi_ret_pct = ((ks_end - ks_start) / ks_start) * 100 if ks_start > 0 else 0.0
                            kosdaq_ret_pct = ((kq_end - kq_start) / kq_start) * 100 if kq_start > 0 else 0.0

                            asset_df['KOSPI (지수)'] = (bench_aligned[ks_key].values / ks_start) * total_capital_input
                            asset_df['KOSDAQ (지수)'] = (bench_aligned[kq_key].values / kq_start) * total_capital_input
                            bench_synced = True
                        except Exception:
                            pass

                    asset_df['내 총자산'] = asset_df['Total_Asset']

                    last_row = close_df.iloc[-1]
                    active_eval_value = sum([p['invest_amount'] * (float(last_row[p['ticker']]) / p['entry_price']) for p in active_positions if p['ticker'] in last_row and not pd.isna(last_row[p['ticker']])])
                    total_free_shares_count = sum(free_shares_dict.values())
                    total_free_shares_value = sum([count * float(last_row[PORTFOLIO_UNIVERSE[s_name]]) for s_name, count in free_shares_dict.items() if count > 0 and PORTFOLIO_UNIVERSE[s_name] in last_row and not pd.isna(last_row[PORTFOLIO_UNIVERSE[s_name]])])

                    final_total_asset = current_cash + active_eval_value + total_free_shares_value
                    total_net_profit = final_total_asset - total_capital_input
                    total_return_pct = (total_net_profit / total_capital_input) * 100
                    total_trades = total_success + total_stop_loss
                    win_rate = (total_success / total_trades * 100) if total_trades > 0 else 0

                    current_query_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    backtest_period_str = f"{start_date_str} ~ {end_date_str} ({period_label})"
                    
                    st.markdown(f"""
                    <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 15px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; flex-wrap: wrap; gap: 10px;">
                        <div>
                            <h2 style="margin: 0; font-size: 1.5rem; color: #0f172a; font-weight: 800;">🏆 백테스트 최종 성과 대시보드</h2>
                            <p style="margin: 4px 0 0 0; font-size: 0.9rem; color: #475569; font-weight: 700;">
                                📅 검증 기간: <b style="color: #2563eb;">{backtest_period_str}</b> | 📏 기준선: <b style="color: #2563eb;">{ma_period_choice}일선 적용</b>
                            </p>
                        </div>
                        <span style="font-size: 0.9rem; color: #64748b; font-weight: 600; background: #f1f5f9; padding: 6px 12px; border-radius: 8px; border: 1px solid #cbd5e1;">
                            🕒 조회 시각: <b style="color: #0284c7;">{current_query_time}</b>
                        </span>
                    </div>
                    """, unsafe_allow_html=True)

                    m0, m1, m2, m3 = st.columns(4)
                    m0.metric("💵 금고 잔고 (가용 현금)", format_money(current_cash))
                    m1.metric("🏁 원금 예산", format_money(total_capital_input))
                    m2.metric(f"✨ {period_label} 후 총자산", format_money(final_total_asset))
                    m3.metric("📈 총 순수익금", format_money(total_net_profit), delta=f"{total_return_pct:.2f}%")
                    
                    st.write("") 
                    m4, m5, m6, m7 = st.columns(4)
                    m4.metric("🎯 작전 승률", f"{win_rate:.1f}%", delta=f"{total_trades}전 {total_success}승 {total_stop_loss}패")
                    m5.metric("🌊 최대 낙폭 (MDD)", f"{max_drawdown_pct:.1f}%")
                    m6.metric("📦 수확한 열매 평가액", format_money(total_free_shares_value))
                    m7.metric("🍯 누적 배당금", format_money(total_dividend_profit))

                    st.markdown("---")
                    st.markdown("### 📊 벤치마크 시장 지수 대비 수익률 초과 달성 리포트")
                    b_col1, b_col2, b_col3 = st.columns(3)
                    b_col1.metric("🛡️ 내 박가이버 작전 수익률", f"{total_return_pct:+.2f}%")
                    if bench_synced:
                        b_col2.metric("📉 KOSPI 지수", f"{kospi_ret_pct:+.2f}%", delta=f"지수 대비 {(total_return_pct - kospi_ret_pct):+.2f}%p 초과")
                        b_col3.metric("📉 KOSDAQ 지수", f"{kosdaq_ret_pct:+.2f}%", delta=f"지수 대비 {(total_return_pct - kosdaq_ret_pct):+.2f}%p 초과")
                    else:
                        b_col2.metric("📉 KOSPI 지수", "동기화 대기중")
                        b_col3.metric("📉 KOSDAQ 지수", "동기화 대기중")

                    if total_free_shares_count > 0:
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); padding: 18px 22px; border-radius: 12px; border-left: 6px solid #22c55e; margin-top: 15px; margin-bottom: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.03);">
                            <h4 style="margin-top: 0; color: #166534; font-size: 1.15rem; margin-bottom: 10px;">📦 내 열매(무료 주식) 금고 상세 현황</h4>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        fruit_list = []
                        for s_name, count in free_shares_dict.items():
                            if count > 0:
                                t_code = PORTFOLIO_UNIVERSE[s_name]
                                c_price = float(last_row[t_code]) if t_code in last_row and not pd.isna(last_row[t_code]) else 0
                                eval_val = count * c_price
                                fruit_list.append({
                                    "작전 구역 (종목명)": s_name,
                                    "보유 수량": f"{count}주",
                                    "현재 1주 단가": format_exact_price(c_price),
                                    "현재 평가액": format_money(eval_val)
                                })
                        st.dataframe(pd.DataFrame(fruit_list), use_container_width=True, hide_index=True)

                    tab1, tab2, tab3, tab4 = st.tabs([
                        "📊 1. 자산 성장 & MDD 차트", 
                        "🔍 2. 자금 회전율 & 미출격 진단", 
                        "📈 3. 종목/연도별 손익분석", 
                        "📜 4. 현장 투입요원 & 매매장부"
                    ])

                    with tab1:
                        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3], subplot_titles=("총자산 증식 추이", "계좌 최대 낙폭 (MDD)"))
                        fig.add_trace(go.Scatter(x=asset_df['Date'], y=asset_df['Total_Asset'], mode='lines', name='내 총자산', line=dict(color='#2563eb', width=3), fill='tozeroy', fillcolor='rgba(37, 99, 235, 0.08)'), row=1, col=1)
                        if bench_synced:
                            fig.add_trace(go.Scatter(x=asset_df['Date'], y=asset_df['KOSPI (지수)'], mode='lines', name='KOSPI 지수', line=dict(color='#94a3b8', width=1.5, dash='dash')), row=1, col=1)
                            fig.add_trace(go.Scatter(x=asset_df['Date'], y=asset_df['KOSDAQ (지수)'], mode='lines', name='KOSDAQ 지수', line=dict(color='#cbd5e1', width=1.5, dash='dot')), row=1, col=1)
                        fig.add_hline(y=total_capital_input, line_dash="solid", line_color="#ef4444", annotation_text="초기 원금", row=1, col=1)
                        fig.add_trace(go.Scatter(x=asset_df['Date'], y=asset_df['Drawdown'], mode='lines', name='낙폭(MDD)', line=dict(color='#dc2626', width=1.5), fill='tozeroy', fillcolor='rgba(220, 38, 38, 0.15)'), row=2, col=1)
                        fig.update_layout(height=650, template="plotly_white", margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                        st.plotly_chart(fig, use_container_width=True)

                    with tab2:
                        st.write("### 🔍 회전율 & 미출격 타점 분석 리포트")
                        st.warning(f"📊 기간 중 최대 동시 출격 수: **총 {global_max_deployed}개 종목** (전체 슬롯: {max_active_slots}개)")
                        if daily_deployment_snapshots:
                            snap_df = pd.DataFrame(daily_deployment_snapshots)
                            peak_df = snap_df[snap_df['동시 출격 수'] == global_max_deployed].drop_duplicates(subset=['발생 일자'])
                            st.write("▼ **역대 최고 자금 몰림(피크) 발생 일자 및 출격 목록:**")
                            st.dataframe(peak_df, use_container_width=True, hide_index=True)

                        st.markdown("---")
                        st.write("### 🚫 현금/슬롯/섹터 제한으로 놓쳐버린 출격 타점 추적기")
                        if missed_opportunities:
                            st.error(f"🚨 하락 타점이 맞았으나 제한으로 놓친 기회: 총 {len(missed_opportunities)}회")
                            st.dataframe(pd.DataFrame(missed_opportunities), use_container_width=True, hide_index=True)
                        else:
                            st.success("🎉 단 한 번도 현금이나 슬롯이 부족해서 출격 기회를 놓친 적이 없습니다!")

                    with tab3:
                        st.write("### 📊 종목 및 연도별 정밀 성적표")
                        c_col1, c_col2 = st.columns([1.2, 1])
                        with c_col1:
                            st.write("#### 🗓️ 연도별 익절 vs 손절 건수 그래프")
                            yearly_chart_data = []
                            for y, val in yearly_stats.items():
                                yearly_chart_data.append({"연도": str(y), "구분": "🎯 익절", "건수": val['success']})
                                yearly_chart_data.append({"연도": str(y), "구분": "🚨 손절", "건수": val['stop']})
                            fig_bar = px.bar(pd.DataFrame(yearly_chart_data), x="연도", y="건수", color="구분", barmode="group", color_discrete_map={"🎯 익절": "#22c55e", "🚨 손절": "#ef4444"})
                            st.plotly_chart(fig_bar, use_container_width=True)
                        with c_col2:
                            st.write("#### 🗓️ 연도별 정산 종합표")
                            yearly_summary_list = []
                            for y, val in sorted(yearly_stats.items()):
                                yearly_summary_list.append({"연도": str(y), "🎯 익절": f"{val['success']}회", "🚨 손절": f"{val['stop']}회", "📦 획득 열매": f"{int(val['shares'])}주", "💵 현금수익": format_money(val['cash'])})
                            st.dataframe(pd.DataFrame(yearly_summary_list), use_container_width=True, hide_index=True)

                        st.markdown("---")
                        st.write("#### 📦 종목별 누적 열매 수확 총합계 리포트")
                        total_stock_fruit_summary = []
                        for s_name in PORTFOLIO_UNIVERSE.keys():
                            total_shares = free_shares_dict.get(s_name, 0)
                            t_code = PORTFOLIO_UNIVERSE[s_name]
                            c_price = float(last_row[t_code]) if t_code in last_row and not pd.isna(last_row[t_code]) else 0
                            eval_val = total_shares * c_price
                            total_stock_fruit_summary.append({
                                "작전 구역 (종목명)": s_name,
                                "총 수확한 열매(주식) 수": f"{total_shares}주",
                                "현재 1주 단가": format_exact_price(c_price),
                                "현재 열매 총 평가액": format_money(eval_val)
                            })
                        st.dataframe(pd.DataFrame(total_stock_fruit_summary), use_container_width=True, hide_index=True)

                    with tab4:
                        st.write("### ⚔️ 현재 현장 투입 요원 현황")
                        if len(active_positions) > 0:
                            active_table = []
                            tot_inv, tot_eval, tot_prof = 0, 0, 0
                            for p in active_positions:
                                t_code = p['ticker']
                                curr_price = float(last_row[t_code]) if t_code in last_row and not pd.isna(last_row[t_code]) else p['entry_price']
                                eval_val = p['invest_amount'] * (curr_price / p['entry_price'])
                                eval_profit = eval_val - p['invest_amount']
                                ret = ((curr_price - p['entry_price']) / p['entry_price']) * 100
                                tot_inv += p['invest_amount']
                                tot_eval += eval_val
                                tot_prof += eval_profit

                                active_table.append({
                                    '요원': p['name'], '구역명': p['stock_name'], '출격일': p['entry_date'],
                                    '출격 당시 주가': format_exact_price(p['entry_price']),
                                    '진입금액': f"{format_pure_number(p['invest_amount'])}원",
                                    '현재 평가금액': f"{format_pure_number(eval_val)}원",
                                    '평가 손익': f"{format_pure_number(eval_profit)}원",
                                    '현재수익률': f"{ret:.2f}%"
                                })

                            st.success(f"⚔️ **현재 현장 교전(투입) 중인 요원: 총 {len(active_positions)}명**")
                            ac1, ac2, ac3 = st.columns(3)
                            ac1.metric("💰 투입 원금 합계", f"{format_pure_number(tot_inv)}원")
                            ac2.metric("📊 현재 평가금액 합계", f"{format_pure_number(eval_val)}원")
                            ac3.metric("📈 평가 손익 합계", f"{format_pure_number(tot_prof)}원")
                            st.dataframe(pd.DataFrame(active_table), use_container_width=True, hide_index=True)
                        else:
                            st.success("🎉 현재 현장에 대기 중인 요원이 없습니다! (100% 현금 회수 완료 상태)")

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
                            )

                except Exception as e:
                    st.error(f"❌ 분석 중 에러가 발생했습니다: {e}")
