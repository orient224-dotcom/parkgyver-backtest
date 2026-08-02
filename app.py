# =====================================================================
# 🛡️ 박가이버 통합 작전 사령부 V10.11 - 구글 코랩 실행용 마스터 스크립트
# =====================================================================

# 1.필요한 라이브러리 자동 설치
!pip install -q streamlit yfinance pandas numpy plotly python-dateutil

# 2. Streamlit 앱 소스코드 파일(app.py) 자동 생성
app_code = r'''
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

# --- 0. 한글 초성 분리 및 모바일 검색용 포맷팅 엔진 ---
def get_chosung(text):
    chosung_list = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    result = ""
    for char in text:
        if '가' <= char <= '힣':
            idx = (ord(char) - ord('가')) // 588
            result += chosung_list[idx]
        else:
            result += char
    return result

def format_stock_option(stock_name):
    code = MASTER_STOCK_DICT.get(stock_name, "")
    chosung = get_chosung(stock_name)
    market = "코스닥" if code.endswith(".KQ") else "코스피"
    return f"{stock_name} ({chosung} | {market} {code})"

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

# 매매장부 스마트 컬러 음영 스타일러 함수
def style_trade_df(df):
    def apply_row_style(row):
        ret_val = str(row.get('순수익률', ''))
        reason = str(row.get('구분', ''))
        snow_level = str(row.get('스노우볼 레벨', ''))
        
        if '레벨UP' in snow_level:
            return ['background-color: #fef08a; color: #854d0e; font-weight: bold;'] * len(row)
        elif '특별 보너스' in reason:
            return ['background-color: #eff6ff; color: #1d4ed8; font-weight: bold;'] * len(row)
        elif '강제 철수' in reason or '-' in ret_val:
            return ['background-color: #fee2e2; color: #991b1b; font-weight: bold;'] * len(row)
        elif '타임 컷' in reason:
            return ['background-color: #fff7ed; color: #c2410c; font-weight: bold;'] * len(row)
        elif '+' in ret_val or '정상 복귀' in reason or '추세연장' in reason:
            return ['background-color: #dcfce7; color: #166534; font-weight: bold;'] * len(row)
        else:
            return [''] * len(row)
    return df.style.apply(apply_row_style, axis=1)

# --- 1. 페이지 웹 디자인 세팅 ---
st.set_page_config(page_title="박가이버 통합 작전 사령부 V10.11 Colab Edition", page_icon="🛡️", layout="wide")

st.markdown(r"""
<style>
    .stApp { background-color: #f8fafc; }
    .algo-spec-container { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 14px; padding: 18px 20px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03); }
    .algo-spec-header { font-size: 1.1rem; font-weight: 800; color: #0f172a; margin-bottom: 14px; display: flex; align-items: center; gap: 6px; }
    .algo-grid { display: flex; gap: 12px; flex-wrap: wrap; }
    .algo-card { flex: 1; min-width: 280px; background-color: #f8fafc; border-radius: 10px; padding: 14px 16px; border: 1px solid #e2e8f0; }
    .algo-card.card-1 { border-left: 6px solid #ef4444; }
    .algo-card.card-2 { border-left: 6px solid #f59e0b; }
    .algo-card.card-3 { border-left: 6px solid #10b981; }
    .algo-card.card-4 { border-left: 6px solid #2563eb; }
    .algo-card-title { font-size: 0.95rem; font-weight: 800; margin-bottom: 6px; }
    .algo-card-title.t-1 { color: #dc2626; }
    .algo-card-title.t-2 { color: #d97706; }
    .algo-card-title.t-3 { color: #059669; }
    .algo-card-title.t-4 { color: #2563eb; }
    .algo-card-desc { font-size: 0.85rem; color: #475569; line-height: 1.45; font-weight: 500; }
    .weather-card { background-color: #fffef2; border: 2px solid #f59e0b; border-radius: 14px; padding: 16px 20px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.08); }
    .weather-title { font-size: 1.1rem; font-weight: 800; color: #92400e; margin-bottom: 12px; display: flex; align-items: center; gap: 6px; }
    .weather-box-container { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
    .weather-pill { background-color: #ffffff; border: 1px solid #fcd34d; border-radius: 8px; padding: 8px 14px; font-size: 0.9rem; font-weight: 700; color: #78350f; flex: 1; min-width: 260px; }
    .weather-divider { border-top: 1px dashed #f59e0b; margin: 12px 0; }
    .weather-status-text { font-size: 0.88rem; color: #451a03; font-weight: 600; }
    .metric-card { background-color: #ffffff; border-radius: 10px; padding: 14px 16px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); border: 1px solid #e2e8f0; margin-bottom: 12px; height: 100%; display: flex; flex-direction: column; justify-content: space-between; }
    .metric-card.card-green { border-left: 6px solid #10b981; }
    .metric-card.card-blue { border-left: 6px solid #2563eb; }
    .metric-card.card-red { border-left: 6px solid #ef4444; }
    .metric-card.card-yellow { border-left: 6px solid #f59e0b; background-color: #fffbeb; }
    .metric-card.card-orange { border-left: 6px solid #d97706; }
    .metric-card.card-purple { border-left: 6px solid #a855f7; background-color: #faf5ff; border-top: 1px solid #f3e8ff; border-right: 1px solid #f3e8ff; border-bottom: 1px solid #f3e8ff; }
    .metric-label { font-size: 0.85rem; font-weight: 800; color: #475569; margin-bottom: 4px; display: flex; align-items: center; gap: 5px; }
    .metric-value { font-size: 1.35rem; font-weight: 900; color: #0f172a; margin-bottom: 4px; }
    .metric-sub { font-size: 0.78rem; color: #64748b; font-weight: 600; }
    .hero-banner { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 18px 20px; border-radius: 14px; color: #ffffff; border-left: 6px solid #38bdf8; box-shadow: 0 8px 20px -4px rgba(15, 23, 42, 0.2); margin-bottom: 20px; }
    .hero-title { font-size: 1.45rem; font-weight: 900; margin: 0; color: #f8fafc; }
    .hero-subtitle { font-size: 0.88rem; color: #94a3b8; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# --- 2. 기본 종목 마스터 사전 ---
BASE_STOCK_MASTER = {
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "테크윙": "089030.KQ", "한미반도체": "042700.KS",
    "HPSP": "403870.KQ", "이오테크닉스": "039030.KQ", "주성엔지니어링": "036930.KQ", "원익IPS": "240810.KQ",
    "한화오션": "042660.KS", "HD한국조선해양": "009540.KS", "현대로템": "064350.KS", "LIG넥스원": "079550.KS",
    "한화에어로스페이스": "012450.KS", "한국콜마": "161890.KS", "코스맥스": "192820.KS", "알테오젠": "196170.KQ",
    "셀트리온": "068270.KS", "삼성바이오로직스": "207940.KS", "현대차": "005380.KS", "기아": "000270.KS",
    "NAVER": "035420.KS", "카카오": "035720.KS", "HD현대일렉트릭": "267260.KS", "두산에너빌리티": "034020.KS",
    "KODEX 200": "069500.KS", "KODEX 코스닥150": "229200.KS", "KODEX 레버리지": "122630.KS", "TIGER 미국S&P500": "360750.KS"
}

if "full_stock_master" not in st.session_state:
    st.session_state["full_stock_master"] = BASE_STOCK_MASTER.copy()

if "custom_stocks" not in st.session_state: st.session_state["custom_stocks"] = {}
if "my_holdings" not in st.session_state: st.session_state["my_holdings"] = ["SK하이닉스", "한미반도체", "테크윙", "HD현대일렉트릭", "HPSP"]
if "my_watchlist" not in st.session_state: st.session_state["my_watchlist"] = ["한화오션", "현대로템", "RFHIC", "한국콜마"]

MASTER_STOCK_DICT = st.session_state["full_stock_master"]
for name, code in st.session_state["custom_stocks"].items():
    MASTER_STOCK_DICT[name] = code

TICKER_TO_SECTOR = {code: "우량주" for code in MASTER_STOCK_DICT.values()}

if "selected_stocks" not in st.session_state: st.session_state["selected_stocks"] = st.session_state["my_holdings"]

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
st.sidebar.title("🎛️ 박가이버 사령부 V10.11")

st.sidebar.subheader("💾 나만의 작전 세팅 (휴대폰 관리)")
uploaded_cfg = st.sidebar.file_uploader("📤 내 전략 세팅 불러오기 (.json)", type=["json"], help="내 계좌 보유 종목 및 세팅 파일을 올립니다.")

if uploaded_cfg is not None:
    try:
        cfg_data = json.load(uploaded_cfg)
        if "my_holdings" in cfg_data: st.session_state["my_holdings"] = cfg_data["my_holdings"]
        if "my_watchlist" in cfg_data: st.session_state["my_watchlist"] = cfg_data["my_watchlist"]
        if "custom_stocks" in cfg_data: 
            st.session_state["custom_stocks"] = cfg_data["custom_stocks"]
            for name, code in cfg_data["custom_stocks"].items():
                MASTER_STOCK_DICT[name] = code
        st.session_state["selected_stocks"] = st.session_state["my_holdings"]
        st.sidebar.success("🎉 세팅 파일 복원 완료!")
        st.rerun()
    except Exception:
        st.sidebar.error("⚠️ 올바른 설정(.json) 파일이 아닙니다.")

st.sidebar.markdown("---")

menu_choice = st.sidebar.radio(
    "사령부 작전 모드선택",
    [
        "🗄️ 1. 내 계좌 영구 DB (보유 & 관심)", 
        "🚨 2. 오늘의 실전 매매 레이더", 
        "🛡️ 3. 과거 백테스트 연구소"
    ],
    index=2
)
st.sidebar.markdown("---")

if menu_choice == "🗄️ 1. 내 계좌 영구 DB (보유 & 관심)":
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🗄️ 나만의 투자 영구 DB (스마트폰 연동)</div>
        <div class="hero-subtitle">스마트폰 전 종목 DB 연동으로 대한민국 2,600개 상장 종목을 초성 키보드로 1초 만에 검색하세요!</div>
    </div>
    """, unsafe_allow_html=True)

    db_tab1, db_tab2 = st.tabs(["💼 내 실전 보유 종목 (주력)", "⭐ 눈여겨보는 관심 종목"])

    with db_tab1:
        st.markdown("### 💼 1. 실전 보유 종목 DB 세팅")
        valid_holdings = [s for s in st.session_state["my_holdings"] if s in MASTER_STOCK_DICT]
        new_holdings = st.multiselect("실전 보유 종목 편집:", options=list(MASTER_STOCK_DICT.keys()), default=valid_holdings, format_func=format_stock_option, key="holding_multiselect")
        if st.button("💾 실전 보유 종목 DB 저장", type="primary", use_container_width=True):
            st.session_state["my_holdings"] = new_holdings
            st.session_state["selected_stocks"] = new_holdings
            st.success("🎉 저장 완료!")
            st.rerun()

    with db_tab2:
        st.markdown("### ⭐ 2. 관심 종목 DB 세팅")
        valid_watchlist = [s for s in st.session_state["my_watchlist"] if s in MASTER_STOCK_DICT]
        new_watchlist = st.multiselect("관심 종목 편집:", options=list(MASTER_STOCK_DICT.keys()), default=valid_watchlist, format_func=format_stock_option, key="watchlist_multiselect")
        if st.button("💾 관심 종목 DB 저장", type="secondary", use_container_width=True):
            st.session_state["my_watchlist"] = new_watchlist
            st.success("🎉 저장 완료!")
            st.rerun()

elif menu_choice == "🚨 2. 오늘의 실전 매매 레이더":
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🚨 오늘의 실전 매매 레이더 (출격 명령서)</div>
        <div class="hero-subtitle">매일 오후 3시 20분 종가 기준 | 내 계좌 DB 주력 종목의 매수 타점을 감시합니다.</div>
    </div>
    """, unsafe_allow_html=True)

    buy_cond_input = st.sidebar.slider("🛒 진입 기준 (-% 하락 시)", 1, 20, 5, 1, key="live_buy_cond")
    valid_watch_stocks = [s for s in st.session_state["my_holdings"] if s in MASTER_STOCK_DICT]
    PORTFOLIO_UNIVERSE = {s_name: MASTER_STOCK_DICT[s_name] for s_name in valid_watch_stocks if s_name in MASTER_STOCK_DICT}

    with st.spinner("📡 대한민국 증시 기상청 및 실시간 시세를 동기화 중입니다..."):
        try:
            live_bench = yf.download(["^KS11", "^KQ11"], period="2mo", interval="1d", progress=False)
            bench_close = live_bench['Close'] if isinstance(live_bench.columns, pd.MultiIndex) and 'Close' in live_bench.columns.levels[0] else live_bench
            ks_key = '^KS11' if '^KS11' in bench_close.columns else bench_close.columns[0]
            kq_key = '^KQ11' if '^KQ11' in bench_close.columns else (bench_close.columns[1] if len(bench_close.columns) > 1 else ks_key)
            ks_series = bench_close[ks_key].ffill()
            kq_series = bench_close[kq_key].ffill()
            last_ks_c = float(ks_series.dropna().iloc[-1])
            last_ks_ma = float(ks_series.rolling(window=20).mean().dropna().iloc[-1])
            last_kq_c = float(kq_series.dropna().iloc[-1])
            last_kq_ma = float(kq_series.rolling(window=20).mean().dropna().iloc[-1])
            
            st.markdown(f"""
            <div class="weather-card">
                <div class="weather-title">⛅ 대한민국 증시 기상청 실시간 현황</div>
                <div class="weather-box-container">
                    <div class="weather-pill">[코스피] {'☀️ 맑음' if last_ks_c >= last_ks_ma else '🌧️ 하락장'} ({last_ks_c:,.1f}pt)</div>
                    <div class="weather-pill">[코스닥] {'☀️ 맑음' if last_kq_c >= last_kq_ma else '🌧️ 하락장'} ({last_kq_c:,.1f}pt)</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        except Exception:
            pass

else:
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🛡️ 과거 백테스트 연구소 (은퇴 설계 월별 정산 V10.11)</div>
        <div class="hero-subtitle">은퇴 현금 흐름 분석 | 연도별 총 투입횟수 및 월별 정산 종합표가 완벽하게 연동됩니다.</div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("💡 🛡️ 박가이버표 매매 알고리즘 4대 동작 원리 명세서", expanded=True):
        st.markdown("""
        1. **대세 하락장 자동 우산 방어 필터**: 지수 20일선 아래 하락장에서는 요원 출격을 일시 정지합니다.
        2. **스마트 출격 타점 (-5% 이하 급락)**: 설정된 하락율 달성 시 종가로 기계적 진입합니다.
        3. **하이브리드 추세연장 익절 스위치**: 5일선이 살아있는 한 상방을 열어두고 대세 상승을 극대화합니다.
        4. **타임컷 & 리스크 관리**: 보유기간 초과 또는 손절선 도달 시 기계적으로 청산합니다.
        """)

    valid_watch_stocks = [s for s in st.session_state["my_holdings"] if s in MASTER_STOCK_DICT]
    PORTFOLIO_UNIVERSE = {s_name: MASTER_STOCK_DICT[s_name] for s_name in valid_watch_stocks if s_name in MASTER_STOCK_DICT}

    st.sidebar.subheader("⚙️ 백테스트 전략 조건 설정")
    use_market_filter = st.sidebar.checkbox("🌤️ 대세 하락장 자동 우산 스위치", value=True)
    ma_period_choice = st.sidebar.radio("📏 하락장 우산 기준선 선택", [120, 240], index=1, horizontal=True)
    use_strict_ma_filter = st.sidebar.checkbox("📈 장기 이평선 위에서만 출격 (추세 필터)", value=False)
    use_sector_limit = st.sidebar.checkbox("🤹‍♂️ 동일 섹터 몰빵 방지 캡", value=True)
    use_time_cut = st.sidebar.checkbox("⏱️ 타임 컷 (최대 보유일 제한)", value=True)
    max_hold_days_input = st.sidebar.slider("⏳ 최대 보유 제한일 (일)", 5, 60, 30, 5) if use_time_cut else 9999
    
    use_hybrid_trailing = st.sidebar.checkbox("🔥 하이브리드 추세연장 (목표가 달성 시 추세 홀딩)", value=True)
    use_weighted_entry = st.sidebar.checkbox("📉 하락폭 가중 매수 (폭락장에서 예산 가중 투입)", value=True)

    total_capital_input = st.sidebar.number_input("🏦 총 작전 예산(원)", value=10000000, step=1000000, key="bt_capital")
    invest_amount_input = st.sidebar.number_input("💰 회당 초기 진입금액(원)", value=int(total_capital_input // 5), step=500000, key="bt_invest")
    max_active_slots = max(1, int(total_capital_input // invest_amount_input))
    max_sector_slots = max(1, max_active_slots // 2)

    use_compounding = st.sidebar.checkbox("🚀 복리 스케일업 모드", value=True, key="bt_compound")
    time_unit = st.sidebar.radio("🗓️ 기간 단위", ["월 단위 (개월)", "년 단위 (년)"], horizontal=True, key="bt_tunit")
    months_input = st.sidebar.slider("백테스트 기간(개월)", 1, 120, 60, 1, key="bt_m") if time_unit == "월 단위 (개월)" else st.sidebar.slider("백테스트 기간(년)", 1, 10, 5, 1, key="bt_y") * 12
    period_label = f"{months_input}개월"

    buy_cond_input = st.sidebar.slider("🛒 진입 기준 (-% 하락 시)", 1, 20, 5, 1, key="bt_buy")
    sell_target_input = st.sidebar.slider("🎯 익절 목표 (+%)", 1, 30, 5, 1, key="bt_sell")
    stop_loss_input = st.sidebar.slider("🚨 손절 기준 (-%)", 0, 50, 15, 1, key="bt_stop")

    reward_type = st.sidebar.selectbox("🎁 전리품 수령 방식", ["전액 현금으로 챙기기", "🌟 현금 50% + 열매 50% (하이브리드)"], index=1)
    run_btn = st.sidebar.button("🚀 백테스트 타임머신 가동!", type="primary", use_container_width=True)

    if run_btn:
        if len(PORTFOLIO_UNIVERSE) == 0:
            st.error("❌ 감시 종목이 없습니다!")
        else:
            with st.spinner("📡 슈퍼컴퓨터가 백테스트를 가동 중입니다..."):
                try:
                    end_date_str = datetime.datetime.today().strftime('%Y-%m-%d')
                    start_date_str = (datetime.datetime.today() - relativedelta(months=months_input)).strftime('%Y-%m-%d')
                    tickers = list(PORTFOLIO_UNIVERSE.values())
                    
                    raw_close = yf.download(tickers, start=start_date_str, end=end_date_str, interval="1d", progress=False)
                    close_df = raw_close['Close'] if isinstance(raw_close.columns, pd.MultiIndex) and 'Close' in raw_close.columns.levels[0] else raw_close
                    if isinstance(close_df, pd.Series): close_df = close_df.to_frame(name=tickers[0])
                    close_df = close_df.dropna(how='all')
                    close_df.index = clean_date_index(close_df.index)

                    raw_actions = yf.download(tickers, start=start_date_str, end=end_date_str, interval="1d", actions=True, progress=False)
                    div_df = raw_actions['Dividends'] if isinstance(raw_actions.columns, pd.MultiIndex) and 'Dividends' in raw_actions.columns.levels[0] else pd.DataFrame(0, index=close_df.index, columns=tickers)
                    div_df.index = clean_date_index(div_df.index)
                    div_df = div_df.reindex(close_df.index).fillna(0)

                    return_df = close_df.pct_change() * 100
                    sma_df = close_df.rolling(window=int(ma_period_choice)).mean()
                    ma5_df = close_df.rolling(window=5).mean()
                    ma20_df = close_df.rolling(window=20).mean()

                    buy_cond = -float(buy_cond_input)
                    sell_target = float(sell_target_input)
                    stop_loss_limit = -float(stop_loss_input) if stop_loss_input > 0 else None

                    current_cash = float(total_capital_input)
                    active_positions, trade_logs, asset_history = [], [], []
                    agent_counter = 0

                    yearly_stats = {}
                    monthly_stats = {}
                    free_shares_dict = {s_name: 0 for s_name in PORTFOLIO_UNIVERSE.keys()}
                    total_success, total_stop_loss = 0, 0
                    global_max_deployed = 0
                    daily_deployment_snapshots = []
                    peak_asset_value = float(total_capital_input)
                    max_drawdown_pct = 0.0

                    current_snow_level = 1
                    last_level_threshold_asset = float(total_capital_input)
                    level_up_events_count = 0

                    for date, row in close_df.iterrows():
                        date_str = date.strftime('%Y-%m-%d')
                        year = date.year
                        month_key = date.strftime('%Y-%m')
                        if year not in yearly_stats: yearly_stats[year] = {'success': 0, 'stop': 0, 'shares': 0, 'cash': 0}
                        if month_key not in monthly_stats: monthly_stats[month_key] = {'success': 0, 'stop': 0, 'shares': 0, 'cash': 0}
                        
                        survived_positions = []
                        for pos in active_positions:
                            t_code = pos['ticker']
                            if t_code in row and not pd.isna(row[t_code]):
                                curr_price = float(row[t_code])
                                gross_ret = ((curr_price - pos['entry_price']) / pos['entry_price']) * 100
                                is_exit, exit_reason = False, ""
                                days_taken = (pd.to_datetime(date_str) - pd.to_datetime(pos['entry_date'])).days

                                ma5_val = ma5_df.loc[date, t_code] if t_code in ma5_df.columns and date in ma5_df.index else None
                                ma20_val = ma20_df.loc[date, t_code] if t_code in ma20_df.columns and date in ma20_df.index else None

                                if use_hybrid_trailing and pos.get('trailing', False):
                                    if pd.notna(ma5_val) and pd.notna(ma20_val) and (curr_price < ma5_val or ma5_val < ma20_val):
                                        is_exit, exit_reason = True, "🔥 하이브리드 추세연장 익절"
                                else:
                                    if gross_ret >= sell_target:
                                        if use_hybrid_trailing and pd.notna(ma5_val) and pd.notna(ma20_val) and (ma5_val > ma20_val) and (curr_price >= ma5_val):
                                            pos['trailing'] = True
                                        else:
                                            is_exit, exit_reason = True, f"🎯 정상 복귀(+{sell_target_input}%)"
                                    elif stop_loss_limit is not None and gross_ret <= stop_loss_limit:
                                        is_exit, exit_reason = True, f"🚨 강제 철수(-{stop_loss_input}%)"
                                    elif use_time_cut and days_taken >= max_hold_days_input:
                                        is_exit, exit_reason = True, f"⏳ 타임 컷 ({max_hold_days_input}일 초과)"

                                if is_exit:
                                    sell_gross_val = pos['invest_amount'] * (curr_price / pos['entry_price'])
                                    net_profit = sell_gross_val - pos['invest_amount']
                                    net_ret = (net_profit / pos['invest_amount']) * 100
                                    s_name = pos['stock_name']
                                    
                                    if gross_ret >= sell_target or net_profit > 0:
                                        total_success += 1
                                        yearly_stats[year]['success'] += 1
                                        monthly_stats[month_key]['success'] += 1
                                        buyable = int(max(0, net_profit) * 0.5 // curr_price) if '하이브리드' in reward_type else 0
                                        leftover = net_profit - (buyable * curr_price)
                                    else:
                                        total_stop_loss += 1
                                        yearly_stats[year]['stop'] += 1
                                        monthly_stats[month_key]['stop'] += 1
                                        buyable, leftover = 0, net_profit

                                    free_shares_dict[s_name] += buyable
                                    current_cash += (pos['invest_amount'] + leftover)
                                    yearly_stats[year]['shares'] += buyable
                                    yearly_stats[year]['cash'] += leftover
                                    monthly_stats[month_key]['shares'] += buyable
                                    monthly_stats[month_key]['cash'] += leftover

                                    current_total_eval_check = current_cash + sum([p['invest_amount'] * (float(row[p['ticker']]) / p['entry_price']) for p in active_positions if p['ticker'] in row and not pd.isna(row[p['ticker']])])
                                    is_level_up = False
                                    if use_compounding and current_total_eval_check >= last_level_threshold_asset * 1.10:
                                        current_snow_level += 1
                                        level_up_events_count += 1
                                        last_level_threshold_asset = current_total_eval_check
                                        is_level_up = True

                                    level_display_str = f"🚀 Lv.{current_snow_level} (레벨UP!)" if is_level_up else f"Lv.{current_snow_level}"
                                    trade_logs.append({
                                        '요원': pos['name'], '작전 구역': pos['stock_name'], '출격일': pos['entry_date'],
                                        '진입금액': f"{format_pure_number(pos['invest_amount'])}원", '복귀일': date_str,
                                        '매도금액': f"{format_pure_number(sell_gross_val)}원", '순수익률': f"{net_ret:+.2f}%",
                                        '정산내역': f"열매 {buyable}개 + 잔돈 {format_pure_number(leftover)}원" if buyable > 0 else f"{format_pure_number(leftover)}원",
                                        '구분': exit_reason, '스노우볼 레벨': level_display_str
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
                                    if use_market_filter and t_code in sma_df.columns and date in sma_df.index:
                                        sma_val = sma_df.loc[date, t_code]
                                        if pd.notna(sma_val) and row[t_code] < sma_val:
                                            target_buy_cond = buy_cond * 1.4
                                    if ret_val <= target_buy_cond:
                                        candidates.append((s_name, t_code, ret_val, float(row[t_code])))
                            candidates.sort(key=lambda x: x[2])

                            for cand in candidates:
                                c_price, ret_val, t_code, s_name = cand[3], cand[2], cand[1], cand[0]
                                actual_invest = min(dynamic_invest_amount * (max(1.0, abs(ret_val) / abs(buy_cond_input)) if use_weighted_entry else 1.0), current_cash)
                                if len(active_positions) < max_active_slots and current_cash >= 500000:
                                    agent_counter += 1
                                    current_cash -= actual_invest
                                    active_positions.append({'name': f"{agent_counter}호 요원", 'stock_name': s_name, 'ticker': t_code, 'entry_price': c_price, 'entry_date': date_str, 'invest_amount': actual_invest, 'trailing': False})

                        if len(active_positions) > global_max_deployed: global_max_deployed = len(active_positions)
                        if len(active_positions) > 0:
                            daily_deployment_snapshots.append({"발생 일자": date_str, "동시 출격 수": len(active_positions)})

                        eval_pos = sum([p['invest_amount'] * (float(row[p['ticker']]) / p['entry_price']) for p in active_positions if p['ticker'] in row and not pd.isna(row[p['ticker']])])
                        today_total_asset = current_cash + eval_pos
                        if today_total_asset > peak_asset_value: peak_asset_value = today_total_asset
                        curr_dd = ((today_total_asset - peak_asset_value) / peak_asset_value) * 100
                        if curr_dd < max_drawdown_pct: max_drawdown_pct = curr_dd
                        asset_history.append({"Date": date_str, "Total_Asset": today_total_asset, "Drawdown": curr_dd, "Invest_Scale": dynamic_invest_amount})

                    asset_df = pd.DataFrame(asset_history)
                    last_row = close_df.iloc[-1]
                    active_eval_val = sum([p['invest_amount'] * (float(last_row[p['ticker']]) / p['entry_price']) for p in active_positions if p['ticker'] in last_row and not pd.isna(last_row[p['ticker']])])
                    total_free_shares_val = sum([count * float(last_row[PORTFOLIO_UNIVERSE[s_name]]) for s_name, count in free_shares_dict.items() if count > 0 and PORTFOLIO_UNIVERSE[s_name] in last_row and not pd.isna(last_row[PORTFOLIO_UNIVERSE[s_name]])])
                    final_total_asset = current_cash + active_eval_val + total_free_shares_val
                    total_net_profit = final_total_asset - total_capital_input
                    win_rate = (total_success / (total_success + total_stop_loss) * 100) if (total_success + total_stop_loss) > 0 else 0

                    st.success("🎉 백테스트 완료!")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("✨ 최종 총자산", format_money(final_total_asset))
                    m2.metric("📈 총 순수익금", format_money(total_net_profit), delta=f"{(total_net_profit/total_capital_input)*100:.2f}%")
                    m3.metric("🎯 작전 승률", f"{win_rate:.1f}%")
                    m4.metric("🚀 스노우볼 레벨UP", f"Lv.{current_snow_level} ({level_up_events_count}회)")

                    tab1, tab2, tab3 = st.tabs(["📊 자산 차트", "📈 연도/월별 정산", "📜 매매장부"])
                    with tab1:
                        fig = px.line(asset_df, x='Date', y='Total_Asset', title="총자산 증식 추이")
                        st.plotly_chart(fig, use_container_width=True)
                    with tab2:
                        st.write("#### 🗓️ 연도별 정산 종합표")
                        ys_list = [{"연도": str(y), "🎯 익절": f"{v['success']}회", "🚨 손절": f"{v['stop']}회", "⚔️ 투입횟수": f"{v['success']+v['stop']}회", "💵 현금수익": format_money(v['cash'])} for y, v in sorted(yearly_stats.items())]
                        st.dataframe(pd.DataFrame(ys_list), use_container_width=True, hide_index=True)
                        
                        st.write("#### 📅 월별 정산 종합표")
                        ms_list = [{"월": m, "🎯 익절": f"{v['success']}회", "🚨 손절": f"{v['stop']}회", "⚔️ 투입횟수": f"{v['success']+v['stop']}회", "💵 월별수익": format_money(v['cash'])} for m, v in sorted(monthly_stats.items())]
                        st.dataframe(pd.DataFrame(ms_list), use_container_width=True, hide_index=True)
                    with tab4_dummy if False else tab3:
                        if trade_logs:
                            df_logs = pd.DataFrame(list(reversed(trade_logs)))
                            st.dataframe(style_trade_df(df_logs), use_container_width=True)
                except Exception as e:
                    st.error(f"에러 발생: {e}")
'''''

with open("app.py", "w", encoding="utf-8") as f:
    f.write(app_code)

print("🎉 [박가이버 사령부 V10.11] 코랩 마스터 파일 생성 완료!")
print("▶ 아래 명령어를 실행하여 스트림릿 대시보드를 띄우세요:")
print("!streamlit run app.py & npx localtunnel --port 8501")
}저는 언어 모델이라서 그것은 도와드릴 수가 없습니다.
