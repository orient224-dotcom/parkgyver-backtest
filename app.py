import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
from dateutil.relativedelta import relativedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 페이지 웹 디자인 세팅 (모바일 반응형 & 최고급 프리미엄 UI CSS) ---
st.set_page_config(page_title="박가이버 통합 작전 사령부 V8 실전 라이브", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .stApp {
        background-color: #f8fafc;
    }
    @media (max-width: 768px) {
        .hero-title {
            font-size: 1.3rem !important;
        }
        .hero-banner {
            padding: 16px 18px !important;
        }
        div[data-testid="stMetric"] {
            padding: 12px 14px !important;
        }
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%) !important;
        padding: 16px 20px !important;
        border-radius: 14px !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
        transition: transform 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08) !important;
    }
    div[data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] * {
        color: #475569 !important;
        font-size: 0.85rem !important;
        font-weight: 800 !important;
    }
    div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] * {
        color: #0f172a !important;
        font-size: 1.25rem !important;
        font-weight: 900 !important;
    }
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 24px 28px;
        border-radius: 16px;
        color: #ffffff;
        border-left: 8px solid #38bdf8;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25);
        margin-bottom: 25px;
    }
    .hero-title {
        font-size: 1.8rem;
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
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.04);
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
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #eff6ff;
        color: #2563eb;
        border-color: #93c5fd;
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(37, 99, 235, 0.15);
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: #ffffff !important;
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.35) !important;
        border-color: #1d4ed8 !important;
        transform: translateY(-1px);
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

if "selected_stocks" not in st.session_state:
    st.session_state["selected_stocks"] = ["한미반도체", "테크윙", "HPSP", "리노공업", "ISC", "주성엔지니어링", "원익IPS"]

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
def analyze_stock_suitability(stock_dict, invest_amount=2000000):
    results = []
    tickers = list(stock_dict.values())
    if not tickers:
        return pd.DataFrame()
    try:
        data = yf.download(tickers, period="1y", progress=False)['Close']
        for name, code in stock_dict.items():
            s_data = data[code].dropna() if isinstance(data, pd.DataFrame) and code in data.columns else (data.dropna() if isinstance(data, pd.Series) else pd.Series())
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
                    sma200 = s_data.rolling(min(200, len(s_data))).mean().iloc[-1]
                    trend_score = 35 if curr_price >= sma200 else 20
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

# --- 3. 사이드바 조종간 (메인 모드 선택) ---
st.sidebar.title("🎛️ 박가이버 사령부 V8 Pro")
main_mode = st.sidebar.radio(
    "작전 모드 선택",
    [
        "📡 1. 실전 라이브 매매 터미널 (오늘의 시그널)", 
        "🛡️ 2. 실전 작전 통제실 (5개년 백테스트)", 
        "🔎 3. 작전 구역(섹터) 및 종목 탐색기"
    ],
    index=0
)
st.sidebar.markdown("---")

# =====================================================================
# 📡 모드 1: 실전 라이브 매매 터미널 (실시간 시그널 & 감시 레이더)
# =====================================================================
if main_mode == "📡 1. 실전 라이브 매매 터미널 (오늘의 시그널)":
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">📡 박가이버 실전 라이브 매매 레이더 터미널</div>
        <div class="hero-subtitle">매일 오후 3시 20분 동시호가 직전, 오늘 당장 종가로 매수해야 할 급락 타점 종목을 실시간으로 포착합니다!</div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.subheader("🎯 실전 라이브 감시 설정")
    live_stock_names = st.sidebar.multiselect(
        "실전 감시 종목 리스트",
        options=list(MASTER_STOCK_DICT.keys()),
        default=[s for s in st.session_state["selected_stocks"] if s in MASTER_STOCK_DICT]
    )
    LIVE_UNIVERSE = {s: MASTER_STOCK_DICT[s] for s in live_stock_names if s in MASTER_STOCK_DICT}

    live_buy_cond = st.sidebar.slider("🛒 실전 진입 기준 (-% 하락 시)", 1, 20, 5, 1, key="live_buy_slider")
    live_sell_target = st.sidebar.slider("🎯 실전 익절 목표 (+%)", 1, 30, 5, 1, key="live_sell_slider")
    live_stop_loss = st.sidebar.slider("🚨 실전 손절 기준 (-%)", 0, 50, 15, 1, key="live_stop_slider")
    live_capital = st.sidebar.number_input("🏦 총 실전 예산 (원)", value=10000000, step=1000000, key="live_cap")
    live_invest_amt = st.sidebar.number_input("💰 회당 1회 진입금 (원)", value=1500000, step=500000, key="live_inv")

    st.markdown("### 🕒 실전 동시호가 매매 실행 가이드 (월요일 루틴)")
    st.info("""
    * **1단계 (오후 3시 20분):** 본 앱을 열어 아래 **[오늘의 실전 출격 레이더]**를 확인합니다.
    * **2단계 (오후 3시 20분 ~ 3시 30분):** 포착된 종목이 있다면 증권사 MTS/HTS에서 **'종가(동시호가)'**로 진입금만큼 매수 주문을 넣습니다.
    * **3단계 (다음 날 아침):** 증권사 앱의 **'GTC 예약 매도'** 기능을 이용해 목표가(+5%)와 손절가(-15%)를 자동 예약 걸어둡니다.
    """)

    st.markdown("---")
    st.markdown("### 🚨 오늘의 실전 출격 레이더 (실시간 시세 감시)")

    if not LIVE_UNIVERSE:
        st.warning("⚠️ 감시할 종목이 선택되지 않았습니다. 사이드바에서 종목을 1개 이상 선택해 주세요.")
    else:
        with st.spinner("📡 실시간 시장 데이터를 조회하여 오늘 시그널을 분석 중입니다..."):
            try:
                tickers = list(LIVE_UNIVERSE.values())
                df_live = yf.download(tickers, period="5d", progress=False)['Close']
                
                live_results = []
                buy_signals_today = []

                for name, code in LIVE_UNIVERSE.items():
                    s_data = df_live[code].dropna() if isinstance(df_live, pd.DataFrame) and code in df_live.columns else (df_live.dropna() if isinstance(df_live, pd.Series) else pd.Series())
                    if len(s_data) >= 2:
                        today_p = float(s_data.iloc[-1])
                        yester_p = float(s_data.iloc[-2])
                        change_pct = ((today_p - yester_p) / yester_p) * 100
                        
                        is_signal = change_pct <= -float(live_buy_cond)
                        if is_signal:
                            buy_signals_today.append(name)

                        live_results.append({
                            "작전 구역": name,
                            "티커": code,
                            "현재가 (종가 추정)": format_exact_price(today_p),
                            "전일 대비 등락률": f"{change_pct:+.2f}%",
                            "시그널 상태": "🛒 [출격 타점 포착!]" if is_signal else "⏳ 관망 대기",
                            "추천 1회 진입금": format_money(live_invest_amt),
                            "목표가 (+5%)": format_exact_price(today_p * (1 + live_sell_target / 100)),
                            "손절가 (-15%)": format_exact_price(today_p * (1 - live_stop_loss / 100))
                        })

                if buy_signals_today:
                    st.error(f"⚡ **[실전 출격 시그널 발생]** 오늘 감시 종목 중 **{', '.join(buy_signals_today)}** 종목이 진입 기준(-{live_buy_cond}%) 이하로 하락하여 출격 타점에 포착되었습니다! 오늘 오후 3시 20분 동시호가에 종가 매수를 실행하세요.")
                else:
                    st.success("✅ **[관망 대기 중]** 현재 감시 구역 내 진입 기준(-%)에 도달한 종목이 없습니다. 차분히 다음 타점을 기다립니다.")

                st.markdown("#### 📊 실시간 감시 종목 레이더 현황판")
                st.dataframe(pd.DataFrame(live_results), use_container_width=True, hide_index=True)

            except Exception as e:
                st.error(f"❌ 실시간 시세 조회 중 에러가 발생했습니다: {e}")

# =====================================================================
# 🛡️ 모드 2: 실전 작전 통제실 (5개년 백테스트 시뮬레이터)
# =====================================================================
elif main_mode == "🛡️ 2. 실전 작전 통제실 (5개년 백테스트)":
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🛡️ 박가이버표 5개년 백테스트 시뮬레이터</div>
        <div class="hero-subtitle">검증된 알고리즘과 전략 파라미터를 과거 데이터에 대입하여 완벽한 성과를 시뮬레이션합니다.</div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.subheader("⚙️ 백테스트 전략 조종간")
    backtest_stock_names = st.sidebar.multiselect(
        "백테스트 감시 종목 리스트",
        options=list(MASTER_STOCK_DICT.keys()),
        default=[s for s in st.session_state["selected_stocks"] if s in MASTER_STOCK_DICT],
        key="bt_stocks"
    )
    PORTFOLIO_UNIVERSE = {s: MASTER_STOCK_DICT[s] for s in backtest_stock_names if s in MASTER_STOCK_DICT}

    use_market_filter = st.sidebar.checkbox("🌤️ 대세 하락장 자동 우산 스위치", value=True)
    use_sector_limit = st.sidebar.checkbox("🤹‍♂️ 동일 섹터 몰빵 방지 캡", value=True)
    use_time_cut = st.sidebar.checkbox("⏱️ 타임 컷 (최대 보유일 제한)", value=True)
    max_hold_days_input = st.sidebar.slider("⏳ 최대 보유 제한일 (일)", 5, 60, 30, 5) if use_time_cut else 9999

    total_capital_input = st.sidebar.number_input("🏦 총 작전 예산(원)", value=10000000, step=1000000, key="bt_cap")
    invest_amount_input = st.sidebar.number_input("💰 회당 초기 진입금액(원)", value=1500000, step=500000, key="bt_inv")
    max_active_slots = max(1, int(total_capital_input // invest_amount_input))
    st.sidebar.info(f"💡 동원 가능 요원 슬롯: **{max_active_slots}개**")

    use_compounding = st.sidebar.checkbox("🚀 복리 스케일업 모드", value=True)
    
    years_val = st.sidebar.slider("백테스트 기간(년)", 1, 10, 5, 1)
    months_input = years_val * 12
    period_label = f"{years_val}년"

    buy_cond_input = st.sidebar.slider("🛒 진입 기준 (-% 하락 시)", 1, 20, 5, 1, key="bt_buy")
    sell_target_input = st.sidebar.slider("🎯 익절 목표 (+%)", 1, 30, 5, 1, key="bt_sell")
    stop_loss_input = st.sidebar.slider("🚨 손절 기준 (-%)", 0, 50, 15, 1, key="bt_stop")

    reward_type = st.sidebar.selectbox(
        "🎁 전리품 수령 방식", 
        [
            "🌟 현금 50% + 열매 50% (하이브리드)", 
            "🌟 현금 40% + 열매 60% (하이브리드 강화)", 
            "전액 현금으로 챙기기", 
            "열매로 결실 모으기"
        ],
        key="bt_reward"
    )
    
    run_btn = st.sidebar.button("🚀 백테스트 검증 개시!", type="primary", key="bt_run")

    with st.expander("📖 [당귀다TV] 박가이버 사령부 V8 초간단 실전 사용 설명서", expanded=False):
        st.markdown("""
        ### 🛡️ 직장인을 위한 '하루 1분 동시호가 매매법' 핵심 수칙
        1. **👔 업무 수호 (장중 감시 금지):** 장중 주가창을 열어보며 조바심을 내지 않습니다. 본업에 온전히 집중하세요!
        2. **🕒 오후 3시 20분 동시호가 체크:** 퇴근 전 3시 20분, 이 앱을 열어 오늘 출격 시그널을 확인합니다.
        3. **🛒 원클릭 종가 매수:** 포착된 종목이 있다면 '종가(동시호가)'로 진입금만큼 매수 주문을 넣습니다.
        4. **🎯 자동 예약 주문:** 다음 날 아침 증권사 앱에서 목표가(+5%)와 손절가(-15%)를 예약 걸어둡니다.
        5. **📦 하이브리드 수확:** 수익금의 일부는 현금으로, 일부는 공짜 주식(열매)으로 평생 쌓아갑니다.
        """)

    if len(PORTFOLIO_UNIVERSE) > 0 and run_btn:
        with st.spinner("📡 슈퍼컴퓨터가 과거 파동, 벤치마크 지수, 타임컷 및 MDD 데이터를 퀀트 분석 중입니다..."):
            try:
                end_date = datetime.datetime.today()
                start_date = end_date - relativedelta(months=months_input)
                tickers = list(PORTFOLIO_UNIVERSE.values())
                
                bench_tickers = ["^KS11", "^KQ11"]
                raw_df = yf.download(tickers + bench_tickers, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), actions=True, progress=False)

                if isinstance(raw_df.columns, pd.MultiIndex):
                    close_df = raw_df['Close'][tickers]
                    bench_df = raw_df['Close'][bench_tickers] if '^KS11' in raw_df['Close'] else pd.DataFrame()
                    div_df = raw_df['Dividends'][tickers] if 'Dividends' in raw_df.columns.levels[0] else pd.DataFrame(index=raw_df.index, columns=tickers).fillna(0)
                else:
                    close_df = pd.DataFrame({tickers[0]: raw_df['Close']})
                    bench_df = pd.DataFrame()
                    div_df = pd.DataFrame({tickers[0]: raw_df['Dividends']}) if 'Dividends' in raw_df.columns else pd.DataFrame({tickers[0]: 0}, index=raw_df.index)

                return_df = close_df.pct_change() * 100
                sma200_df = close_df.rolling(window=200).mean()

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
                            duration_str = f"{days_taken}일 소요"

                            if gross_ret >= sell_target:
                                is_exit, exit_reason = True, f"🎯 정상 복귀(+{sell_target_input}%)"
                            elif stop_loss_limit is not None and gross_ret <= stop_loss_limit:
                                is_exit, exit_reason = True, f"🚨 강제 철수(-{stop_loss_input}%)"
                            elif use_time_cut and days_taken >= max_hold_days_input:
                                is_exit, exit_reason = True, f"⏳ 타임 컷 ({max_hold_days_input}일 초과)"

                            if is_exit:
                                sell_gross_val = pos['invest_amount'] * (curr_price / pos['entry_price'])
                                net_profit = (sell_gross_val - pos['invest_amount'])
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
                                    '소요기간': duration_str, '순수익률': f"{net_ret:.2f}%", '정산내역': log_reward, '구분': exit_reason
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
                                if use_market_filter and (t_code in sma200_df.columns) and date in sma200_df.index:
                                    sma_val = sma200_df.loc[date, t_code]
                                    curr_p = row[t_code]
                                    if pd.notna(sma_val) and pd.notna(curr_p) and curr_p < sma_val:
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
                                if current_sector_count >= (max_active_slots // 2):
                                    continue

                            if c_price > actual_invest or len(active_positions) >= max_active_slots or actual_invest < 500000 or current_cash < 500000:
                                continue
                            else:
                                agent_counter += 1
                                s_name, t_code, ret_val, c_price = cand
                                current_cash -= actual_invest
                                active_positions.append({
                                    'name': f"{agent_counter}호 요원", 'stock_name': s_name, 'ticker': t_code,
                                    'entry_price': c_price, 'entry_date': date_str, 'invest_amount': actual_invest, 'entry_day_ret': ret_val 
                                })

                    eval_pos = sum([p['invest_amount'] * (float(row[p['ticker']]) / p['entry_price']) for p in active_positions if p['ticker'] in row and not pd.isna(row[p['ticker']])])
                    today_total_asset = current_cash + eval_pos
                    if today_total_asset > peak_asset_value: peak_asset_value = today_total_asset
                    current_drawdown = ((today_total_asset - peak_asset_value) / peak_asset_value) * 100
                    if current_drawdown < max_drawdown_pct: max_drawdown_pct = current_drawdown
                    asset_history.append({"Date": date, "Total_Asset": today_total_asset, "Drawdown": current_drawdown})

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
                backtest_period_str = f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')} ({period_label})"

                st.markdown(f"### 🏆 백테스트 최종 성과 리포트 ({backtest_period_str})")
                m0, m1, m2, m3 = st.columns(4)
                m0.metric("💵 금고 잔고", format_money(current_cash))
                m1.metric("🏁 원금 예산", format_money(total_capital_input))
                m2.metric("✨ 최종 총자산", format_money(final_total_asset))
                m3.metric("📈 총 순수익금", format_money(total_net_profit), delta=f"{total_return_pct:.2f}%")

                m4, m5, m6, m7 = st.columns(4)
                m4.metric("🎯 작전 승률", f"{win_rate:.1f}%", delta=f"{total_trades}전 {total_success}승 {total_stop_loss}패")
                m5.metric("🌊 최대 낙폭 (MDD)", f"{max_drawdown_pct:.1f}%")
                m6.metric("📦 수확한 열매 평가액", format_money(total_free_shares_value), delta=f"총 {total_free_shares_count}주")
                m7.metric("🍯 누적 배당금", format_money(total_dividend_profit))

                st.markdown("---")
                st.write("### 📜 전체 백테스트 매매 장부")
                if trade_logs:
                    logs_df = pd.DataFrame(list(reversed(trade_logs)))
                    st.dataframe(logs_df, use_container_width=True)

            except Exception as e:
                st.error(f"❌ 백테스트 분석 중 에러가 발생했습니다: {e}")

# =====================================================================
# 🔎 모드 3: 작전 구역(섹터) 및 종목 탐색기
# =====================================================================
else:
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🔎 작전 구역 및 영구 종목 탐색기</div>
        <div class="hero-subtitle">대한민국 전 종목을 검색하고 감시 바구니에 영구 등록합니다.</div>
    </div>
    """, unsafe_allow_html=True)

    search_tab1, search_tab2 = st.tabs(["⚡ 스마트 종목/코드 직접 등록", "🔎 내장 장부에서 고르기"])
    with search_tab1:
        c1, c2, c3, c4 = st.columns([2, 1.5, 1, 1])
        input_name = c1.text_input("종목명 입력", placeholder="예: 대한전선, RFHIC")
        input_code = c2.text_input("6자리 코드", placeholder="예: 001440")
        input_market = c3.selectbox("시장", ["코스피 (.KS)", "코ส닥 (.KQ)"])
        if c4.button("➕ 바구니 추가", type="primary"):
            name_q = input_name.strip()
            code_q = input_code.strip()
            resolved_code = None
            if len(code_q) == 6 and code_q.isdigit():
                suffix = ".KS" if "코스피" in input_market else ".KQ"
                resolved_code = f"{code_q}{suffix}"
            if resolved_code and name_q:
                MASTER_STOCK_DICT[name_q] = resolved_code
                if name_q not in st.session_state["selected_stocks"]:
                    st.session_state["selected_stocks"].append(name_q)
                st.success(f"🎉 [{name_q} ({resolved_code})] 등록 완료!")
                st.rerun()
            else:
                st.error("종목명과 6자리 코드를 정확히 입력해 주세요.")
    with search_tab2:
        all_names = sorted(list(MASTER_STOCK_DICT.keys()))
        sel_drop = st.selectbox("종목 선택", options=[""] + all_names)
        if st.button("🛒 선택 종목 바구니 추가"):
            if sel_drop and sel_drop not in st.session_state["selected_stocks"]:
                st.session_state["selected_stocks"].append(sel_drop)
                st.success(f"🎉 [{sel_drop}] 추가 완료!")
                st.rerun()
