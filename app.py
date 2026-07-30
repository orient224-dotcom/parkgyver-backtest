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

# --- 1. 페이지 웹 디자인 세팅 (모바일 반응형 & 프리미엄 UI CSS) ---
st.set_page_config(page_title="박가이버 통합 작전 사령부 V10.6 Master", page_icon="🛡️", layout="wide")

# 🌟 사이렌 경고등 애니메이션 및 UI CSS 추가
st.markdown("""
<style>
    .stApp {
        background-color: #f8fafc;
    }
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
        margin-bottom: 25px;
    }
    .hero-title { font-size: 1.6rem; font-weight: 900; margin: 0; color: #f8fafc; }
    .hero-subtitle { font-size: 0.95rem; color: #94a3b8; margin-top: 6px; }
    
    /* 🌟 사이렌 및 맑음 박스 CSS */
    @keyframes blinker { 50% { opacity: 0.6; } }
    .siren-box {
        background-color: #ffebee; border: 2px solid #e74c3c; border-left: 10px solid #c0392b; 
        border-radius: 8px; padding: 20px; animation: blinker 1.5s linear infinite;
        box-shadow: 0 4px 6px rgba(231, 76, 60, 0.2);
    }
    .clear-box {
        background-color: #e8f8f5; border: 1px solid #2ecc71; border-left: 10px solid #27ae60; 
        border-radius: 8px; padding: 20px;
        box-shadow: 0 4px 6px rgba(46, 204, 113, 0.1);
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

if "selected_stocks" not in st.session_state:
    st.session_state["selected_stocks"] = st.session_state["my_holdings"]

def format_money(num):
    if num is None or pd.isna(num): return "-"
    num_int = int(round(num))
    sign = "-" if num_int < 0 else ""
    return f"{sign}{abs(num_int):,}원"

def format_pure_number(num):
    if num is None or pd.isna(num): return "-"
    return f"{int(round(num)):,}"

def format_exact_price(num):
    if num is None or pd.isna(num): return "-"
    return f"{int(round(num)):,}원"

# --- 3. 사이드바 조종간 ---
st.sidebar.title("🎛️ 박가이버 사령부 V10.6")

st.sidebar.subheader("💾 나만의 작전 세팅 (휴대폰 관리)")
uploaded_cfg = st.sidebar.file_uploader("📤 내 세팅 불러오기 (.json)", type=["json"])

if uploaded_cfg is not None:
    try:
        cfg_data = json.load(uploaded_cfg)
        if "my_holdings" in cfg_data:
            st.session_state["my_holdings"] = cfg_data["my_holdings"]
            st.session_state["selected_stocks"] = cfg_data["my_holdings"]
        if "my_watchlist" in cfg_data:
            st.session_state["my_watchlist"] = cfg_data["my_watchlist"]
        st.sidebar.success("🎉 작전 세팅 파일 복원 완료!")
    except Exception:
        st.sidebar.error("⚠️ 올바른 설정(.json) 파일이 아닙니다.")

st.sidebar.markdown("---")

menu_choice = st.sidebar.radio(
    "사령부 작전 모드선택",
    [
        "🗄️ 1. 내 계좌 영구 DB (보유 & 관심)", 
        "🚨 2. 오늘의 실전 매매 레이더", 
        "🛡️ 3. 과거 5년 백테스트 연구소"
    ],
    index=2
)
st.sidebar.markdown("---")

# =====================================================================
# 🗄️ 메뉴 1: 내 계좌 영구 DB
# =====================================================================
if menu_choice == "🗄️ 1. 내 계좌 영구 DB (보유 & 관심)":
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🗄️ 나만의 투자 영구 DB (마이 포트폴리오)</div>
        <div class="hero-subtitle">실전 보유 종목을 세팅하고 스마트폰 파일로 영구 저장해 두세요!</div>
    </div>
    """, unsafe_allow_html=True)

    db_tab1, db_tab2 = st.tabs(["💼 내 실전 보유 종목 (주력)", "⭐ 눈여겨보는 관심 종목"])

    with db_tab1:
        valid_holdings = [s for s in st.session_state["my_holdings"] if s in MASTER_STOCK_DICT]
        new_holdings = st.multiselect("실전 보유 종목 편집:", options=list(MASTER_STOCK_DICT.keys()), default=valid_holdings)
        if st.button("💾 실전 보유 종목 DB 저장", type="primary", use_container_width=True):
            st.session_state["my_holdings"] = new_holdings
            st.session_state["selected_stocks"] = new_holdings
            st.success("🎉 실전 보유 종목이 안전하게 저장되었습니다!")
            st.rerun()

    with db_tab2:
        valid_watchlist = [s for s in st.session_state["my_watchlist"] if s in MASTER_STOCK_DICT]
        new_watchlist = st.multiselect("관심 종목 편집:", options=list(MASTER_STOCK_DICT.keys()), default=valid_watchlist)
        if st.button("💾 관심 종목 DB 저장", type="secondary", use_container_width=True):
            st.session_state["my_watchlist"] = new_watchlist
            st.success("🎉 관심 종목이 저장되었습니다!")
            st.rerun()

# =====================================================================
# 🚨 메뉴 2: 오늘의 실전 매매 레이더
# =====================================================================
elif menu_choice == "🚨 2. 오늘의 실전 매매 레이더":
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🚨 오늘의 실전 매매 레이더 (출격 명령서)</div>
        <div class="hero-subtitle">매일 오후 3시 20분 종가 기준 | 내 계좌 DB 주력 종목 타점을 포착합니다.</div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.subheader("⚙️ 실전 매매 조건 설정")
    buy_cond_input = st.sidebar.slider("🛒 진입 기준 (-% 하락 시)", 1, 20, 5, 1)
    
    valid_watch_stocks = [s for s in st.session_state["my_holdings"] if s in MASTER_STOCK_DICT]
    PORTFOLIO_UNIVERSE = {s_name: MASTER_STOCK_DICT[s_name] for s_name in valid_watch_stocks if s_name in MASTER_STOCK_DICT}

    st.markdown(f"🎯 **[실전 감시 전광판] 현재 감시 종목 ({len(valid_watch_stocks)}개):** {', '.join(valid_watch_stocks)}")
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
                    today_p, yester_p = float(s_data.iloc[-1]), float(s_data.iloc[-2])
                    change_pct = ((today_p - yester_p) / yester_p) * 100
                    if change_pct <= -float(buy_cond_input):
                        buy_signals.append(f"🛒 **[{name}]** 변동률: **{change_pct:.2f}%** (출격 타점 포착!)")
            
            if buy_signals:
                st.error("⚡ **오늘 실전 진입 타점에 포착된 종목이 있습니다!**\n\n" + "\n\n".join(buy_signals))
            else:
                st.success("✅ **현재 당일 급락 종목이 없습니다.** 요원들은 출격 대기 상태를 유지합니다.")
        except Exception:
            st.info("💡 실시간 시세를 동기화하는 중입니다.")
    else:
        st.warning("⚠️ 감시 종목이 없습니다. 1번 메뉴에서 세팅해주세요!")

# =====================================================================
# 🛡️ 메뉴 3: 과거 5년 백테스트 연구소 (성과 검증)
# =====================================================================
else:
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🛡️ 과거 백테스트 연구소 (N빵 엔진 & 지수 기상청 탑재)</div>
        <div class="hero-subtitle">시장 지수 태풍 경보와 남은 현금 100% N빵 분배 엔진이 완벽하게 가동됩니다.</div>
    </div>
    """, unsafe_allow_html=True)

    valid_watch_stocks = [s for s in st.session_state["my_holdings"] if s in MASTER_STOCK_DICT]
    PORTFOLIO_UNIVERSE = {s_name: MASTER_STOCK_DICT[s_name] for s_name in valid_watch_stocks if s_name in MASTER_STOCK_DICT}

    if valid_watch_stocks:
        st.success(f"🎯 **[백테스트 연구소 전광판] 내 계좌 DB 연동 종목 ({len(valid_watch_stocks)}개):** {', '.join(valid_watch_stocks)}")
    else:
        st.error("⚠️ 감시 종목이 없습니다! 메뉴 [🗄️ 1. 내 계좌 영구 DB]에서 종목을 골라주세요.")

    st.sidebar.subheader("⚙️ 백테스트 전략 조건 설정")
    # 🌟 추가된 지수 기상청 옵션
    use_index_weather = st.sidebar.checkbox("🌦️ 지수 기상청 경보 (하락장 출격 원천 통제)", value=True, help="지수 20일선 이탈 시 요원 출동을 막고 계좌를 방어합니다.")
    
    use_market_filter = st.sidebar.checkbox("🌤️ 개별 종목 20일선 추세 필터", value=True)
    ma_period_choice = st.sidebar.radio("📏 종목 하락장 기준선 선택", [120, 240], index=1, horizontal=True)
    use_strict_ma_filter = st.sidebar.checkbox("📈 장기 이평선 위에서만 출격 (추세 필터)", value=False)
    use_sector_limit = st.sidebar.checkbox("🤹‍♂️ 동일 섹터 몰빵 방지 캡", value=True)
    use_time_cut = st.sidebar.checkbox("⏱️ 타임 컷 (최대 보유일 제한)", value=True)
    max_hold_days_input = st.sidebar.slider("⏳ 최대 보유 제한일 (일)", 5, 60, 30, 5) if use_time_cut else 9999

    st.sidebar.markdown("---")
    total_capital_input = st.sidebar.number_input("🏦 총 작전 예산(원)", value=10000000, step=1000000)
    max_active_slots = st.sidebar.number_input("⚔️ 전체 파견 슬롯 (최대 요원 수)", min_value=1, value=5, step=1)
    
    # 🌟 초기 1인당 기본 예산 (참고용)
    invest_amount_input = total_capital_input // max_active_slots
    max_sector_slots = max(1, max_active_slots // 2)

    use_compounding = st.sidebar.checkbox("🚀 복리 스케일업 모드", value=True)
    years_val = st.sidebar.slider("백테스트 기간(년)", 1, 10, 5, 1)
    months_input = years_val * 12
    period_label = f"{years_val}년"

    buy_cond_input = st.sidebar.slider("🛒 진입 기준 (-% 하락 시)", 1, 20, 5, 1)
    sell_target_input = st.sidebar.slider("🎯 익절 목표 (+%)", 1, 30, 5, 1)
    stop_loss_input = st.sidebar.slider("🚨 손절 기준 (-%)", 0, 50, 15, 1)

    st.sidebar.subheader("💸 거래비용 적용")
    use_fee = st.sidebar.checkbox("수수료/거래세 반영", value=True)
    broker_fee_pct = 0.00015 if use_fee else 0.0
    tax_pct = 0.0018 if use_fee else 0.0
    slippage_pct = 0.0010 if use_fee else 0.0

    reward_type = st.sidebar.selectbox("🎁 전리품 수령 방식", ["🌟 현금 50% + 열매 50% (하이브리드)", "전액 현금으로 챙기기"])

    st.sidebar.markdown("---")
    run_btn = st.sidebar.button("🚀 백테스트 타임머신 가동!", type="primary", use_container_width=True)

    if run_btn:
        if len(PORTFOLIO_UNIVERSE) == 0:
            st.error("❌ 종목을 먼저 세팅해 주세요!")
        else:
            with st.spinner("📡 슈퍼컴퓨터가 과거 파동, 양대 지수, N빵 분배 엔진을 가동하여 분석 중입니다..."):
                try:
                    end_date_str = datetime.datetime.today().strftime('%Y-%m-%d')
                    start_date_str = (datetime.datetime.today() - relativedelta(months=months_input)).strftime('%Y-%m-%d')
                    tickers = list(PORTFOLIO_UNIVERSE.values())
                    
                    # 1. 주가 데이터 다운로드
                    raw_close = yf.download(tickers, start=start_date_str, end=end_date_str, interval="1d", progress=False)
                    if isinstance(raw_close.columns, pd.MultiIndex):
                        close_df = raw_close['Close'] if 'Close' in raw_close.columns.levels[0] else raw_close
                    elif 'Close' in raw_close.columns:
                        close_df = raw_close['Close'].to_frame() if len(tickers) == 1 else raw_close
                    else:
                        close_df = raw_close
                    if isinstance(close_df, pd.Series): close_df = close_df.to_frame(name=tickers[0])
                    close_df = close_df.dropna(how='all')
                    if close_df.empty: st.stop()
                    close_df.index = clean_date_index(close_df.index)

                    # 2. 벤치마크 및 기상청 지수 다운로드
                    bench_df = pd.DataFrame()
                    kospi_ma20 = pd.Series(dtype=float)
                    kosdaq_ma20 = pd.Series(dtype=float)
                    kospi_close_series = pd.Series(dtype=float)
                    kosdaq_close_series = pd.Series(dtype=float)

                    try:
                        bench_raw = yf.download(["^KS11", "^KQ11"], start=start_date_str, end=end_date_str, interval="1d", progress=False)
                        bench_df = bench_raw['Close'] if isinstance(bench_raw.columns, pd.MultiIndex) and 'Close' in bench_raw.columns.levels[0] else bench_raw
                        if not bench_df.empty:
                            bench_df.index = clean_date_index(bench_df.index)
                            ks_key = '^KS11' if '^KS11' in bench_df.columns else bench_df.columns[0]
                            kq_key = '^KQ11' if '^KQ11' in bench_df.columns else (bench_df.columns[1] if len(bench_df.columns) > 1 else ks_key)
                            
                            kospi_close_series = bench_df[ks_key].ffill()
                            kosdaq_close_series = bench_df[kq_key].ffill()
                            
                            kospi_ma20 = kospi_close_series.rolling(20).mean()
                            kosdaq_ma20 = kosdaq_close_series.rolling(20).mean()
                    except Exception:
                        pass

                    return_df = close_df.pct_change() * 100
                    sma_df = close_df.rolling(window=int(ma_period_choice)).mean()

                    buy_cond = -float(buy_cond_input)
                    sell_target = float(sell_target_input)
                    stop_loss_limit = -float(stop_loss_input) if stop_loss_input > 0 else None

                    current_cash = float(total_capital_input)
                    active_positions, trade_logs, asset_history = [], [], []
                    agent_counter = 0

                    yearly_stats = {}
                    free_shares_dict = {s_name: 0 for s_name in PORTFOLIO_UNIVERSE.keys()}
                    
                    total_success, total_stop_loss, total_cash_profit = 0, 0, 0
                    global_max_deployed = 0
                    missed_opportunities = []

                    peak_asset_value = float(total_capital_input)
                    max_drawdown_pct = 0.0

                    # 3. 🌟 메인 퀀트 루프 시작
                    for date, row in close_df.iterrows():
                        date_str = date.strftime('%Y-%m-%d')
                        year = date.year
                        if year not in yearly_stats:
                            yearly_stats[year] = {'success': 0, 'stop': 0, 'shares': 0, 'cash': 0, 'share_val': 0.0}
                        
                        # 오늘 지수 기상청 정보
                        ks_c = float(kospi_close_series.loc[date]) if date in kospi_close_series.index and not pd.isna(kospi_close_series.loc[date]) else None
                        ks_ma = float(kospi_ma20.loc[date]) if date in kospi_ma20.index and not pd.isna(kospi_ma20.loc[date]) else None
                        kq_c = float(kosdaq_close_series.loc[date]) if date in kosdaq_close_series.index and not pd.isna(kosdaq_close_series.loc[date]) else None
                        kq_ma = float(kosdaq_ma20.loc[date]) if date in kosdaq_ma20.index and not pd.isna(kosdaq_ma20.loc[date]) else None

                        # [매도 로직]
                        survived_positions = []
                        for pos in active_positions:
                            t_code = pos['ticker']
                            if t_code in row and not pd.isna(row[t_code]):
                                curr_price = float(row[t_code])
                                gross_ret = ((curr_price - pos['entry_price']) / pos['entry_price']) * 100
                                is_exit, exit_reason = False, ""

                                entry_dt = pd.to_datetime(pos['entry_date'])
                                days_taken = (pd.to_datetime(date_str) - entry_dt).days

                                if gross_ret >= sell_target:
                                    is_exit, exit_reason = True, f"🎯 정상 복귀(+{sell_target_input}%)"
                                elif stop_loss_limit is not None and gross_ret <= stop_loss_limit:
                                    is_exit, exit_reason = True, f"🚨 강제 철수(-{stop_loss_input}%)"
                                elif use_time_cut and days_taken >= max_hold_days_input:
                                    is_exit, exit_reason = True, f"⏳ 타임 컷 ({max_hold_days_input}일)"

                                if is_exit:
                                    sell_gross_val = pos['invest_amount'] * (curr_price / pos['entry_price'])
                                    total_trade_cost = (pos['invest_amount']*broker_fee_pct) + (sell_gross_val*broker_fee_pct) + (sell_gross_val*tax_pct) + ((pos['invest_amount']+sell_gross_val)*slippage_pct)
                                    net_profit = (sell_gross_val - pos['invest_amount']) - total_trade_cost
                                    net_ret = (net_profit / pos['invest_amount']) * 100
                                    s_name = pos['stock_name']
                                    
                                    if gross_ret >= sell_target or net_profit > 0:
                                        total_success += 1
                                        yearly_stats[year]['success'] += 1
                                        if '현금 50% + 열매 50%' in reward_type:
                                            buyable = int(max(0, net_profit) * 0.5 // curr_price)
                                            leftover = net_profit - (buyable * curr_price)
                                        else:
                                            buyable, leftover = 0, net_profit
                                    else:
                                        total_stop_loss += 1
                                        yearly_stats[year]['stop'] += 1
                                        buyable, leftover = 0, net_profit

                                    free_shares_dict[s_name] += buyable
                                    current_cash += (pos['invest_amount'] + leftover)
                                    yearly_stats[year]['shares'] += buyable
                                    yearly_stats[year]['cash'] += leftover

                                    trade_logs.append({
                                        '요원': pos['name'], '작전 구역': s_name, '출격일': pos['entry_date'],
                                        '진입금액': f"{format_pure_number(pos['invest_amount'])}원",
                                        '복귀일': date_str, '순수익률': f"{net_ret:.2f}%",
                                        '정산내역': f"열매 {buyable}주 + {format_pure_number(leftover)}원" if buyable > 0 else f"{format_pure_number(leftover)}원", 
                                        '구분': exit_reason
                                    })
                                else:
                                    survived_positions.append(pos)
                            else:
                                survived_positions.append(pos)
                        
                        active_positions = survived_positions
                        
                        # [자산 갱신 MDD 체크]
                        eval_pos = sum([p['invest_amount'] * (float(row[p['ticker']]) / p['entry_price']) for p in active_positions if p['ticker'] in row and not pd.isna(row[p['ticker']])])
                        today_total_asset = current_cash + eval_pos
                        if today_total_asset > peak_asset_value: peak_asset_value = today_total_asset
                        current_drawdown = ((today_total_asset - peak_asset_value) / peak_asset_value) * 100
                        if current_drawdown < max_drawdown_pct: max_drawdown_pct = current_drawdown
                        asset_history.append({"Date": date_str, "Total_Asset": today_total_asset, "Drawdown": current_drawdown})

                        # [매수 로직 - N빵 엔진 탑재]
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
                                            if use_strict_ma_filter and curr_p < sma_val: continue
                                            if use_market_filter and curr_p < sma_val: target_buy_cond = buy_cond * 1.4

                                    if ret_val <= target_buy_cond:
                                        candidates.append((s_name, t_code, ret_val, float(row[t_code])))
                            
                            candidates.sort(key=lambda x: x[2]) # 하락이 깊은 순

                            for cand in candidates:
                                s_name, t_code, ret_val, c_price = cand

                                # 🌟 [혁신 1] 지수 기상청 태풍 필터 방어 로직
                                is_kq = t_code.endswith('.KQ') or '229200' in t_code or '233740' in t_code
                                idx_c = kq_c if is_kq else ks_c
                                idx_ma = kq_ma if is_kq else ks_ma

                                if use_index_weather and idx_c is not None and idx_ma is not None:
                                    if idx_c < idx_ma:
                                        missed_opportunities.append({"발생 일자": date_str, "미출격 종목": s_name, "불가 사유": "🚨 지수 기상청 태풍 경보 (20일선 이탈)"})
                                        continue

                                # 🌟 [혁신 2] N빵 유연 슬롯 엔진 로직
                                remaining_slots = max_active_slots - len(active_positions)
                                if remaining_slots <= 0:
                                    missed_opportunities.append({"발생 일자": date_str, "미출격 종목": s_name, "불가 사유": "요원 슬롯 풀가동"})
                                    continue
                                
                                # 현금을 남은 슬롯만큼 100% 똑같이 분할 (돈이 놀지 않음)
                                actual_invest = int(current_cash // remaining_slots)

                                if use_sector_limit:
                                    c_sector = TICKER_TO_SECTOR.get(t_code, "기타")
                                    current_sector_count = sum(1 for p in active_positions if TICKER_TO_SECTOR.get(p['ticker'], "기타") == c_sector)
                                    if current_sector_count >= max_sector_slots:
                                        missed_opportunities.append({"발생 일자": date_str, "미출격 종목": s_name, "불가 사유": "섹터 쏠림 방지"})
                                        continue

                                if c_price > actual_invest:
                                    missed_opportunities.append({"발생 일자": date_str, "미출격 종목": s_name, "불가 사유": "1주 가격 초과"})
                                elif actual_invest < 500000 or current_cash < 500000:
                                    missed_opportunities.append({"발생 일자": date_str, "미출격 종목": s_name, "불가 사유": "가용 현금 부족"})
                                else:
                                    agent_counter += 1
                                    current_cash -= actual_invest
                                    active_positions.append({
                                        'name': f"{agent_counter}호 요원", 'stock_name': s_name, 'ticker': t_code,
                                        'entry_price': c_price, 'entry_date': date_str, 'entry_dt': date, 
                                        'invest_amount': actual_invest
                                    })
                        
                        curr_count = len(active_positions)
                        if curr_count > global_max_deployed: global_max_deployed = curr_count

                    # --- 📊 결과 렌더링 ---
                    asset_df = pd.DataFrame(asset_history)
                    last_row = close_df.iloc[-1]
                    active_eval_value = sum([p['invest_amount'] * (float(last_row[p['ticker']]) / p['entry_price']) for p in active_positions if p['ticker'] in last_row and not pd.isna(last_row[p['ticker']])])
                    final_total_asset = current_cash + active_eval_value
                    total_net_profit = final_total_asset - total_capital_input
                    total_return_pct = (total_net_profit / total_capital_input) * 100
                    total_trades = total_success + total_stop_loss
                    win_rate = (total_success / total_trades * 100) if total_trades > 0 else 0

                    st.markdown("""
                    <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 15px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">
                        <h2 style="margin: 0; font-size: 1.5rem; color: #0f172a; font-weight: 800;">🏆 백테스트 최종 성과 대시보드</h2>
                    </div>
                    """, unsafe_allow_html=True)

                    # 🌟 1. 기상청 사이렌/맑음 UI 배너 출력 (최근 날짜 기준)
                    last_ks_c = float(kospi_close_series.dropna().iloc[-1]) if not kospi_close_series.empty else 0
                    last_ks_ma = float(kospi_ma20.dropna().iloc[-1]) if not kospi_ma20.empty else 0
                    last_kq_c = float(kosdaq_close_series.dropna().iloc[-1]) if not kosdaq_close_series.empty else 0
                    last_kq_ma = float(kosdaq_ma20.dropna().iloc[-1]) if not kosdaq_ma20.empty else 0

                    siren_html = f"""
                    <div style="display: flex; gap: 20px; margin-bottom: 20px; flex-wrap: wrap;">
                      <div class="{'siren-box' if last_ks_c < last_ks_ma else 'clear-box'}" style="flex: 1; min-width: 300px;">
                        <h3 style="color: {'#c0392b' if last_ks_c < last_ks_ma else '#27ae60'}; margin: 0 0 5px 0;">
                          {'🚨 KOSPI 태풍 경보 발령 중' if last_ks_c < last_ks_ma else '☀️ KOSPI 시장 날씨 맑음'}
                        </h3>
                        <p style="margin: 0; color: #2c3e50; font-size: 15px;">
                          현재 <b>{last_ks_c:,.1f}pt</b> (20일선: {last_ks_ma:,.1f}pt)
                        </p>
                      </div>
                      <div class="{'siren-box' if last_kq_c < last_kq_ma else 'clear-box'}" style="flex: 1; min-width: 300px;">
                        <h3 style="color: {'#c0392b' if last_kq_c < last_kq_ma else '#27ae60'}; margin: 0 0 5px 0;">
                          {'🚨 KOSDAQ 태풍 경보 발령 중' if last_kq_c < last_kq_ma else '☀️ KOSDAQ 시장 날씨 맑음'}
                        </h3>
                        <p style="margin: 0; color: #2c3e50; font-size: 15px;">
                          현재 <b>{last_kq_c:,.1f}pt</b> (20일선: {last_kq_ma:,.1f}pt)
                        </p>
                      </div>
                    </div>
                    """
                    st.markdown(siren_html, unsafe_allow_html=True)

                    # 🌟 2. 요약 메트릭 카드 (원본 st.columns, st.metric 복원!)
                    m0, m1, m2, m3 = st.columns(4)
                    m0.metric("💵 금고 잔고 (가용 현금)", format_money(current_cash))
                    m1.metric("🏁 원금 예산", format_money(total_capital_input))
                    m2.metric("✨ 백테스트 후 총자산", format_money(final_total_asset))
                    m3.metric("📈 총 순수익금", format_money(total_net_profit), delta=f"{total_return_pct:.2f}%")
                    
                    st.write("") 
                    m4, m5, m6, m7 = st.columns(4)
                    m4.metric("🎯 작전 승률", f"{win_rate:.1f}%", delta=f"{total_trades}전 {total_success}승 {total_stop_loss}패")
                    m5.metric("🌊 최대 낙폭 (MDD)", f"{max_drawdown_pct:.1f}%")
                    m6.metric("📦 동시 최대 투입 슬롯", f"{global_max_deployed}명")
                    m7.metric("⚔️ 현재 교전 중 요원", f"{len(active_positions)}명")

                    st.markdown("---")
                    
                    # 🌟 3. 상세 분석 탭 (원본 구조 복원)
                    tab1, tab2, tab3 = st.tabs([
                        "📊 1. 자산 성장 & MDD 차트", 
                        "📜 2. 전체 매매 장부 내역", 
                        "🔍 3. 현장 투입 & 미출격 진단"
                    ])

                    with tab1:
                        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3], subplot_titles=("총자산 증식 추이", "계좌 최대 낙폭 (MDD)"))
                        fig.add_trace(go.Scatter(x=asset_df['Date'], y=asset_df['Total_Asset'], mode='lines', name='내 총자산', line=dict(color='#2563eb', width=3), fill='tozeroy', fillcolor='rgba(37, 99, 235, 0.08)'), row=1, col=1)
                        fig.add_hline(y=total_capital_input, line_dash="solid", line_color="#ef4444", annotation_text="초기 원금", row=1, col=1)
                        fig.add_trace(go.Scatter(x=asset_df['Date'], y=asset_df['Drawdown'], mode='lines', name='낙폭(MDD)', line=dict(color='#dc2626', width=1.5), fill='tozeroy', fillcolor='rgba(220, 38, 38, 0.15)'), row=2, col=1)
                        fig.update_layout(height=650, template="plotly_white", margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified")
                        st.plotly_chart(fig, use_container_width=True)

                    with tab2:
                        st.write("### 📜 전체 청산 매매 장부")
                        if trade_logs:
                            logs_df = pd.DataFrame(list(reversed(trade_logs)))
                            st.dataframe(logs_df, use_container_width=True, hide_index=True)
                            
                            csv_data = logs_df.to_csv(index=False).encode('utf-8-sig')
                            st.download_button(
                                label="📥 엑셀(CSV) 매매장부 다운로드",
                                data=csv_data,
                                file_name=f"작전장부_V10.6_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                                mime="text/csv",
                            )
                        else:
                            st.info("청산 내역이 없습니다.")

                    with tab3:
                        st.write("### ⚔️ 현재 현장 교전(투입) 중인 미귀환 요원")
                        if active_positions:
                            st.dataframe(pd.DataFrame(active_positions), use_container_width=True)
                        else:
                            st.success("🎉 현재 현장에 대기 중인 요원이 없습니다! (100% 현금 회수 완료)")

                        st.markdown("---")
                        st.write("### 🚫 현금/슬롯/지수 제한으로 놓쳐버린 출격 타점 추적기")
                        if missed_opportunities:
                            st.error(f"🚨 타점이 왔으나 제한으로 미출격한 기회: 총 {len(missed_opportunities)}회")
                            st.dataframe(pd.DataFrame(missed_opportunities), use_container_width=True, hide_index=True)
                        else:
                            st.success("🎉 단 한 번도 기회를 놓친 적이 없습니다!")

                except Exception as e:
                    st.error(f"❌ 분석 중 에러가 발생했습니다: {e}")
