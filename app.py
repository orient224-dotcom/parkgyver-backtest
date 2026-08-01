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

# --- 0. 한글 초성 분리 및 검색 엔진 ---
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
        if s.dt.tz is not None: s = s.dt.tz_convert(None)
        return s.dt.normalize()
    elif isinstance(obj, (pd.DatetimeIndex, pd.Index)):
        idx = pd.to_datetime(obj)
        if getattr(idx, 'tz', None) is not None: idx = idx.tz_convert(None)
        return idx.normalize()
    else:
        dt = pd.to_datetime(obj)
        if getattr(dt, 'tz', None) is not None: dt = dt.tz_convert(None)
        return dt.normalize()

# 🌟 한국식 스마트 컬러 장부 스타일러 (익절=빨강계열, 손절=파랑계열)
def style_trade_df(df):
    def apply_row_style(row):
        ret_val = str(row.get('순수익률', ''))
        reason = str(row.get('구분', ''))
        snow_level = str(row.get('스노우볼 레벨', ''))
        
        if '레벨UP' in snow_level or '정상 복귀' in reason or '동반 수확' in reason or '+' in ret_val:
            return ['background-color: #fdedec; color: #c0392b; font-weight: bold;'] * len(row)
        elif '강제 철수' in reason or '-' in ret_val:
            return ['background-color: #ebf5fb; color: #2980b9; font-weight: bold;'] * len(row)
        else:
            return [''] * len(row)
    return df.style.apply(apply_row_style, axis=1)

# --- 1. 페이지 디자인 세팅 ---
st.set_page_config(page_title="박가이버 통합 작전 사령부 V10.12", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    .hero-banner {
        background: linear-gradient(135deg, #1b4f72 0%, #2980b9 100%); padding: 18px 20px;
        border-radius: 14px; color: #ffffff; border-left: 6px solid #f1c40f;
        box-shadow: 0 8px 20px -4px rgba(27, 79, 114, 0.2); margin-bottom: 20px;
    }
    .hero-title { font-size: 1.45rem; font-weight: 900; margin: 0; color: #f8fafc; }
    .hero-subtitle { font-size: 0.88rem; color: #ebf5fb; margin-top: 4px; }
    
    .weather-card {
        background-color: #fffef2; border: 2px solid #f59e0b; border-radius: 14px;
        padding: 16px 20px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.08);
    }
    .weather-title { font-size: 1.1rem; font-weight: 800; color: #92400e; margin-bottom: 12px; display: flex; align-items: center; gap: 6px; }
    .weather-box-container { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
    .weather-pill {
        background-color: #ffffff; border: 1px solid #fcd34d; border-radius: 8px;
        padding: 8px 14px; font-size: 0.9rem; font-weight: 700; color: #78350f; flex: 1; min-width: 260px;
    }
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

if "full_stock_master" not in st.session_state: st.session_state["full_stock_master"] = BASE_STOCK_MASTER.copy()
if "custom_stocks" not in st.session_state: st.session_state["custom_stocks"] = {}
if "my_holdings" not in st.session_state: st.session_state["my_holdings"] = ["주성엔지니어링", "테크윙", "한미반도체"]
if "my_watchlist" not in st.session_state: st.session_state["my_watchlist"] = ["삼성전자", "SK하이닉스"]

MASTER_STOCK_DICT = st.session_state["full_stock_master"]
for name, code in st.session_state["custom_stocks"].items():
    MASTER_STOCK_DICT[name] = code

def format_money(num):
    if num is None or pd.isna(num): return "-"
    return f"{int(round(num)):,}원"

# --- 3. 사이드바 조종간 ---
st.sidebar.title("🎛️ 박가이버 사령부 V10.12")
menu_choice = st.sidebar.radio(
    "사령부 작전 모드선택",
    [
        "🗄️ 1. 내 계좌 영구 DB (보유 & 관심)", 
        "🚨 2. 오늘의 실전 매매 레이더", 
        "🛡️ 3. 과거 5년 백테스트 연구소 (3단 밸런스 과수원)"
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
        <div class="hero-title">🗄️ 나만의 투자 영구 DB (스마트폰 연동)</div>
        <div class="hero-subtitle">대한민국 상장 종목을 초성 키보드로 검색하고 보유 종목을 관리합니다.</div>
    </div>
    """, unsafe_allow_html=True)

    db_tab1, db_tab2 = st.tabs(["💼 내 실전 보유 종목 (주력 함대)", "⭐ 눈여겨보는 관심 종목"])
    with db_tab1:
        new_holdings = st.multiselect("실전 보유 종목 편집 (초성 검색 지원):", options=list(MASTER_STOCK_DICT.keys()), default=st.session_state["my_holdings"], format_func=format_stock_option)
        if st.button("💾 보유 종목 DB 저장", type="primary", use_container_width=True):
            st.session_state["my_holdings"] = new_holdings
            st.success("🎉 저장 완료!")
            st.rerun()
    with db_tab2:
        new_watchlist = st.multiselect("관심 종목 편집:", options=list(MASTER_STOCK_DICT.keys()), default=st.session_state["my_watchlist"], format_func=format_stock_option)
        if st.button("💾 관심 종목 DB 저장", use_container_width=True):
            st.session_state["my_watchlist"] = new_watchlist
            st.success("🎉 저장 완료!")
            st.rerun()

# =====================================================================
# 🚨 메뉴 2: 오늘의 실전 매매 레이더
# =====================================================================
elif menu_choice == "🚨 2. 오늘의 실전 매매 레이더":
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🚨 오늘의 실전 매매 레이더 (출격 명령서)</div>
        <div class="hero-subtitle">매일 오후 3시 20분 종가 기준 | 증시 기상청 날씨 분석 및 주력 함대 타점 감시</div>
    </div>
    """, unsafe_allow_html=True)

    buy_cond_input = st.sidebar.slider("🛒 진입 기준 (-% 하락 시)", 1, 20, 5, 1)
    valid_watch_stocks = [s for s in st.session_state["my_holdings"] if s in MASTER_STOCK_DICT]
    PORTFOLIO_UNIVERSE = {s: MASTER_STOCK_DICT[s] for s in valid_watch_stocks}

    with st.spinner("📡 증시 기상청 및 실시간 시세를 동기화 중입니다..."):
        try:
            live_bench = yf.download(["^KS11", "^KQ11"], period="2mo", interval="1d", progress=False)
            bench_close = live_bench['Close'] if isinstance(live_bench.columns, pd.MultiIndex) else live_bench
            ks_series, kq_series = bench_close.iloc[:, 0].ffill(), bench_close.iloc[:, 1].ffill()
            ks_ma20, kq_ma20 = ks_series.rolling(20).mean(), kq_series.rolling(20).mean()
            
            last_ks_c, last_ks_ma = float(ks_series.iloc[-1]), float(ks_ma20.iloc[-1])
            last_kq_c, last_kq_ma = float(kq_series.iloc[-1]), float(kq_ma20.iloc[-1])

            ks_weather = "🌧️ 먹구름 하락장" if last_ks_c < last_ks_ma else "☀️ 맑은 상승장"
            kq_weather = "🌧️ 먹구름 하락장" if last_kq_c < last_kq_ma else "☀️ 맑은 상승장"
            
            st.markdown(f"""
            <div class="weather-card">
                <div class="weather-title">⛅ 대한민국 증시 기상청 실시간 현황</div>
                <div class="weather-box-container">
                    <div class="weather-pill">[코스피] {ks_weather} ({last_ks_c:,.1f}pt / 20일선 {last_ks_ma:,.1f}pt)</div>
                    <div class="weather-pill">[코스닥] {kq_weather} ({last_kq_c:,.1f}pt / 20일선 {last_kq_ma:,.1f}pt)</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        except Exception:
            pass

    st.markdown(f"### 📡 실시간 출격 시그널 ({len(valid_watch_stocks)}개 함대 감시 중)")
    if PORTFOLIO_UNIVERSE:
        try:
            live_raw = yf.download(list(PORTFOLIO_UNIVERSE.values()), period="5d", interval="1d", progress=False)
            live_data = live_raw['Close'] if isinstance(live_raw.columns, pd.MultiIndex) else live_raw
            
            for name, code in PORTFOLIO_UNIVERSE.items():
                s_data = live_data[code].dropna() if isinstance(live_data, pd.DataFrame) and code in live_data.columns else live_data.dropna()
                if len(s_data) >= 2:
                    change_pct = ((float(s_data.iloc[-1]) - float(s_data.iloc[-2])) / float(s_data.iloc[-2])) * 100
                    if change_pct <= -float(buy_cond_input):
                        st.markdown(f"<div style='padding:12px; border:2px solid #ef4444; background:#fef2f2; border-radius:8px; margin-bottom:8px;'>⚡ <b>[{name}]</b> 당일 급락률 **{change_pct:.2f}%** ➔ 오늘 오후 3시 20분 진입 타점 포착!</div>", unsafe_allow_html=True)
                    else:
                        st.write(f"✅ **{name}**: 변동률 {change_pct:+.2f}% (대기 중)")
        except Exception:
            st.info("시세 동기화 중...")
    else:
        st.warning("⚠️ 감시 종목이 없습니다. [🗄️ 1. 내 계좌 영구 DB]에서 종목을 골라주세요.")

# =====================================================================
# 🛡️ 메뉴 3: 과거 5년 백테스트 연구소 (풀버전 대시보드 완벽 이식)
# =====================================================================
else:
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🛡️ 3단 밸런스 과수원 백테스트 연구소 (V10.12 풀버전 대시보드)</div>
        <div class="hero-subtitle">멀티 함대 분산 + 동반 청산 + 3단 분배 + 대시보드 풀패키지 시뮬레이션 엔진</div>
    </div>
    """, unsafe_allow_html=True)

    valid_watch_stocks = [s for s in st.session_state["my_holdings"] if s in MASTER_STOCK_DICT]
    PORTFOLIO_UNIVERSE = {s: MASTER_STOCK_DICT[s] for s in valid_watch_stocks}

    st.sidebar.subheader("⚙️ 3단 과수원 백테스트 조종간")
    strategy_choice = st.sidebar.selectbox("📊 작전 전략 선택", [
        "🌳 3단 밸런스 과수원 전략 (60%재투자/20%현금/20%코어)",
        "🚀 풀 현금 복리 재투자 전략 (100% 컴파운딩)",
        "⚖️ 균등 배분 고정 전략 (No Reinvest / Buy&Hold 1/N)"
    ], index=0)

    total_capital_input = st.sidebar.number_input("🏦 총 작전 예산(원)", value=15000000, step=1000000)
    max_agents_input = st.sidebar.slider("⚔️ 종목당 최대 요원 수", 1, 10, 5, 1)
    years_input = st.sidebar.slider("🗓️ 조회 기간 (년)", 1, 10, 5, 1)
    
    buy_cond_input = st.sidebar.slider("🛒 진입 기준 (-% 하락 시)", 1, 20, 5, 1)
    sell_target_input = st.sidebar.slider("🎯 익절 목표 (+%)", 1, 30, 10, 1)
    stop_loss_input = st.sidebar.slider("🚨 손절 기준 (-%)", 0, 50, 15, 1)

    st.sidebar.subheader("💸 실전 수수료 및 세금 설정")
    buy_fee_rate = (st.sidebar.number_input("📉 매수 수수료 (%)", value=0.015, format="%.3f") / 100.0)
    sell_tax_rate = (st.sidebar.number_input("📈 매도 세금+수수료 (%)", value=0.20, format="%.2f") / 100.0)

    run_btn = st.sidebar.button("🚀 3단 과수원 백테스트 가동!", type="primary", use_container_width=True)

    if run_btn:
        if not PORTFOLIO_UNIVERSE:
            st.error("❌ 감시 종목이 없습니다. [🗄️ 1. 내 계좌 영구 DB]에서 주력 종목을 세팅해 주세요!")
        else:
            with st.spinner("📡 슈퍼컴퓨터가 멀티 함대 3단 과수원 시뮬레이션을 가동 중입니다..."):
                try:
                    end_dt = datetime.datetime.today()
                    start_dt = end_dt - relativedelta(years=years_input + 1)
                    tickers = list(PORTFOLIO_UNIVERSE.values())
                    
                    raw_close = yf.download(tickers, start=start_dt.strftime('%Y-%m-%d'), end=end_dt.strftime('%Y-%m-%d'), progress=False)
                    close_df = raw_close['Close'] if isinstance(raw_close.columns, pd.MultiIndex) else raw_close
                    if isinstance(close_df, pd.Series): close_df = close_df.to_frame(name=tickers[0])
                    close_df = close_df.dropna(how='all')
                    close_df.index = clean_date_index(close_df.index)

                    bench_raw = yf.download(["^KS11", "^KQ11"], start=start_dt.strftime('%Y-%m-%d'), end=end_dt.strftime('%Y-%m-%d'), progress=False)
                    bench_df = bench_raw['Close'] if isinstance(bench_raw.columns, pd.MultiIndex) else bench_raw

                    capital_per_stock = total_capital_input / len(PORTFOLIO_UNIVERSE)
                    
                    all_matched_trades = []
                    stock_results = {}
                    combined_equity_df = pd.DataFrame()
                    all_active_positions = []
                    total_cycles_all, full_launch_cycles_all = 0, 0
                    all_batch_agent_counts = []
                    total_agent_counter, total_fees_paid_all = 0, 0.0

                    for s_name, t_code in PORTFOLIO_UNIVERSE.items():
                        if t_code not in close_df.columns: continue
                        df_s = close_df[[t_code]].dropna().copy()
                        df_s.columns = ['Close']
                        df_s['Daily_Return'] = df_s['Close'].pct_change() * 100
                        df_s['MA20'] = df_s['Close'].rolling(20).mean()
                        df_s['MA60'] = df_s['Close'].rolling(60).mean()
                        df_s['MA120'] = df_s['Close'].rolling(120).mean()
                        df_s = df_s[df_s.index >= (end_dt - relativedelta(years=years_input)).strftime('%Y-%m-%d')].copy()

                        positions = []
                        core_shares = 0
                        reserve_cash = 0.0
                        total_trades, win_trades, loss_trades = 0, 0, 0
                        total_cycles, full_launch_cycles = 0, 0
                        batch_agent_counts = []
                        stock_total_fees = 0.0
                        matched_trades = []
                        agent_counter = 0
                        current_capital = float(capital_per_stock)
                        step_progress, level_up_count, step_down_count = 0.0, 0, 0
                        daily_log = []

                        for date, row in df_s.iterrows():
                            close = float(row['Close'])
                            daily_ret = float(row['Daily_Return'])
                            ma20 = float(row['MA20']) if not pd.isna(row['MA20']) else close
                            ma60 = float(row['MA60']) if not pd.isna(row['MA60']) else close
                            ma120 = float(row['MA120']) if not pd.isna(row['MA120']) else close
                            date_str = date.strftime('%Y-%m-%d')

                            if pd.isna(daily_ret): continue

                            is_super_bull = (close > ma20) and (ma20 > ma60) and (ma60 > ma120)
                            is_super_bear = (close < ma20) and (ma20 < ma60) and (ma60 < ma120)
                            target_ret = 15.0 if is_super_bull else (5.0 if is_super_bear else float(sell_target_input))

                            has_winner = any(((close - pos['entry_price']) / pos['entry_price']) * 100 >= target_ret for pos in positions)

                            if has_winner and len(positions) > 0:
                                total_cycles += 1
                                total_cycles_all += 1
                                batch_size = len(positions)
                                batch_agent_counts.append(batch_size)
                                all_batch_agent_counts.append(batch_size)
                                if batch_size == max_agents_input:
                                    full_launch_cycles += 1
                                    full_launch_cycles_all += 1

                                batch_reinvest_profit = 0.0
                                current_batch_trades = []

                                for pos in positions:
                                    shares = pos['shares']
                                    buy_gross = shares * pos['entry_price']
                                    buy_fee = buy_gross * buy_fee_rate
                                    buy_net = buy_gross + buy_fee
                                    
                                    sell_gross = shares * close
                                    sell_tax = sell_gross * sell_tax_rate
                                    sell_net = sell_gross - sell_tax
                                    
                                    trade_fee_total = buy_fee + sell_tax
                                    stock_total_fees += trade_fee_total
                                    total_fees_paid_all += trade_fee_total

                                    profit_krw = sell_net - buy_net
                                    ret = (profit_krw / buy_net) * 100

                                    if profit_krw > 0:
                                        if "3단 밸런스" in strategy_choice:
                                            reinvest_amt = profit_krw * 0.60
                                            reserve_cash += (profit_krw * 0.20)
                                            core_shares += int((profit_krw * 0.20) // close)
                                        elif "풀 현금" in strategy_choice:
                                            reinvest_amt = profit_krw * 1.00
                                        else:
                                            reinvest_amt = 0.0
                                    else:
                                        reinvest_amt = profit_krw

                                    batch_reinvest_profit += reinvest_amt
                                    total_trades += 1
                                    if profit_krw >= 0: win_trades += 1
                                    else: loss_trades += 1

                                    is_win = profit_krw >= 0
                                    current_batch_trades.append({
                                        '요원': pos['name'], '작전구역': s_name, '종목코드': t_code,
                                        '출격일': pos['entry_date'], '진입일 등락률': f"{pos['entry_return']:+.2f}%",
                                        '진입금액': f"{int(buy_net):,}원", '진입단가': f"{int(pos['entry_price']):,}원",
                                        '복귀일': date_str, '청산일 등락률': f"{daily_ret:+.2f}%", '청산단가': f"{int(close):,}원",
                                        '매도금액': f"{int(sell_net):,}원", '총수수료·세금': f"{int(trade_fee_total):,}원",
                                        '등락폭': f"{int(profit_krw):,}원 ({ret:+.2f}%)", '소요기간': "동반 수확",
                                        '순수익률': f"{ret:+.2f}%", '정산내역': f"{'+' if profit_krw>=0 else ''}{int(profit_krw):,}원",
                                        '구분': "🎯 동반 수확 성공" if is_win else "🚨 강제 철수",
                                        '스노우볼 레벨': f"Lv.{max(1, level_up_count + 1)}", 'is_win': is_win, 'raw_profit': profit_krw, 'exit_date': date
                                    })

                                if "균등 배분" not in strategy_choice:
                                    step_progress += batch_reinvest_profit
                                    threshold = current_capital * 0.10
                                    if step_progress >= threshold:
                                        level_up_count += 1
                                        current_capital += threshold
                                        step_progress = 0.0

                                matched_trades.extend(current_batch_trades)
                                positions = []

                            if daily_ret <= -float(buy_cond_input) and len(positions) < max_agents_input:
                                agent_counter += 1
                                total_agent_counter += 1
                                scale_ratio = current_capital / capital_per_stock if "균등 배분" not in strategy_choice else 1.0
                                agent_budget = int((capital_per_stock // max_agents_input) * scale_ratio)
                                shares = max(int(agent_budget // close), 1)

                                positions.append({
                                    'name': f"{agent_counter}호 요원", 'entry_price': close,
                                    'entry_date': date_str, 'entry_return': daily_ret, 'shares': shares
                                })

                            active_eval = sum(p['shares'] * close for p in positions)
                            core_eval = core_shares * close
                            realized_pnl = sum([t['raw_profit'] for t in matched_trades])
                            stock_eq = capital_per_stock + realized_pnl + reserve_cash + core_eval + active_eval - sum(p['shares']*p['entry_price'] for p in positions)
                            daily_log.append({'Date': date, 'Stock_Equity': stock_eq})

                        for p in positions:
                            cur_eval_p = p['shares'] * float(df_s['Close'].iloc[-1])
                            pnl_p = cur_eval_p - (p['shares'] * p['entry_price'])
                            pnl_pct = (pnl_p / (p['shares'] * p['entry_price'])) * 100
                            all_active_positions.append({
                                '작전구역': s_name, '요원명': p['name'], '파견일': p['entry_date'],
                                '진입단가': f"{int(p['entry_price']):,}원", '수량': f"{p['shares']}주",
                                '평가금액': f"{int(cur_eval_p):,}원", '평가손익': f"{int(pnl_p):,}원 ({pnl_pct:+.2f}%)", 'is_plus': pnl_p >= 0
                            })

                        df_eq = pd.DataFrame(daily_log).set_index('Date')
                        combined_equity_df[s_name] = df_eq['Stock_Equity']

                        stock_results[t_code] = {
                            'name': s_name, 'total_trades': total_trades, 'win_trades': win_trades, 'loss_trades': loss_trades,
                            'win_rate': (win_trades / total_trades * 100) if total_trades > 0 else 0,
                            'net_profit': sum([t['raw_profit'] for t in matched_trades]), 'reserve_cash': reserve_cash,
                            'core_shares': core_shares, 'core_eval': core_shares * float(df_s['Close'].iloc[-1]),
                            'active_eval': sum(p['shares'] * float(df_s['Close'].iloc[-1]) for p in positions),
                            'active_count': len(positions), 'final_equity': df_eq['Stock_Equity'].iloc[-1] if not df_eq.empty else capital_per_stock,
                            'total_fees': stock_total_fees, 'matched_trades': matched_trades
                        }
                        all_matched_trades.extend(matched_trades)

                    combined_equity_df = combined_equity_df.dropna()
                    combined_equity_df['Portfolio_Equity'] = combined_equity_df.sum(axis=1)

                    # KPI 지표 계산
                    total_net_profit_all = sum([res['net_profit'] for res in stock_results.values()])
                    total_trades_all = sum([res['total_trades'] for res in stock_results.values()])
                    win_trades_all = sum([res['win_trades'] for res in stock_results.values()])
                    loss_trades_all = sum([res['loss_trades'] for res in stock_results.values()])
                    overall_win_rate = (win_trades_all / total_trades_all * 100) if total_trades_all > 0 else 0
                    final_portfolio_equity = combined_equity_df['Portfolio_Equity'].iloc[-1]
                    total_reserve_cash = sum([res['reserve_cash'] for res in stock_results.values()])
                    total_core_eval = sum([res['core_eval'] for res in stock_results.values()])
                    total_core_shares = sum([res['core_shares'] for res in stock_results.values()])
                    total_active_eval = sum([res['active_eval'] for res in stock_results.values()])
                    total_active_count = sum([res['active_count'] for res in stock_results.values()])

                    # =========================================================
                    # 📊 풀버전 대시보드 화면 렌더링 (콜백 경험 완벽 재현)
                    # =========================================================
                    st.markdown(f"""
                    <div style="background:#e8f8f5; border:2px solid #1abc9c; padding:15px; border-radius:10px; margin-bottom:20px;">
                        <h3 style="margin:0; color:#117a65;">🏆 [3단 밸런스 과수원] 백테스트 대시보드 풀패키지 가동 완료!</h3>
                        <p style="margin:5px 0 0 0; color:#2c3e50;">전략: <b>{strategy_choice}</b> | 통합 청산 승률: <b>{overall_win_rate:.1f}%</b> | 실현 순수익: <b style="color:#c0392b;">+{int(total_net_profit_all):,}원</b></p>
                    </div>
                    """, unsafe_allow_html=True)

                    # 1. 상단 KPI 카드 1열
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("🎯 통합 청산 승률", f"{overall_win_rate:.1f}%", f"익절 {win_trades_all} / 손절 {loss_trades_all}")
                    k2.metric("⚔️ 총 투입 요원", f"{total_agent_counter}명", f"총 {total_cycles_all}개 회차 / 대기 {total_active_count}명")
                    full_launch_pct = (full_launch_cycles_all / total_cycles_all * 100) if total_cycles_all > 0 else 0.0
                    k3.metric("🔥 최대 요원 풀출력", f"{full_launch_cycles_all}회", f"({full_launch_pct:.1f}%)")
                    k4.metric("🚀 스노우볼 레벨UP", f"{sum([r.get('level_up_count',0) for r in stock_results.values()])}회", "수익 +10% 축적 시 증액")

                    # 상단 KPI 카드 2열
                    k5, k6, k7, k8, k9 = st.columns(5)
                    k5.metric("💵 비상 현금금고", f"{int(total_reserve_cash):,}원", "폭락장 대비 20% 안전예수금")
                    k6.metric("📈 대기주식 평가금", f"{int(total_active_eval):,}원", f"대기 요원 {total_active_count}명")
                    k7.metric("💰 누적 실현 순수익", f"+{int(total_net_profit_all):,}원", "매매 실현 순수익")
                    k8.metric("🚀 포트폴리오 총자산", f"{int(final_portfolio_equity):,}원", "현금+대기주식+코어주식")
                    k9.metric("🍎 확보 코어주식", f"{total_core_shares}주", f"가치 {int(total_core_eval):,}원")

                    st.markdown("---")

                    # 2. 작전 회차별 요원 동시 투입 분포 현황
                    st.markdown(f"#### 📊 작전 회차별 요원 동시 투입 분포 현황 (총 {total_cycles_all}개 청산 작전 회차)")
                    agent_dist = {1:0, 2:0, 3:0, 4:0, 5:0}
                    for cnt in all_batch_agent_counts:
                        if cnt in agent_dist: agent_dist[cnt] += 1
                    
                    d_cols = st.columns(max_agents_input)
                    for a_num in range(1, max_agents_input + 1):
                        cnt = agent_dist.get(a_num, 0)
                        pct = (cnt / total_cycles_all * 100) if total_cycles_all > 0 else 0.0
                        with d_cols[a_num - 1]:
                            st.markdown(f"""
                            <div style="background:white; border-left:4px solid #3498db; padding:10px; border-radius:6px; border:1px solid #d5dbdf; text-align:center;">
                                <div style="font-size:11px; color:#7f8c8d; font-weight:bold;">{a_num}명 투입</div>
                                <div style="font-size:16px; font-weight:900; color:#2c3e50; margin-top:2px;">{cnt}회 <span style="font-size:11px; font-weight:normal;">({pct:.1f}%)</span></div>
                            </div>
                            """, unsafe_allow_html=True)

                    st.markdown("")

                    # 3. 현재 파견 대기 중인 요원 실시간 현황판
                    st.markdown(f"#### 🕵️ [현재 파견 대기 중인 요원 실시간 현황판] (총 {len(all_active_positions)}명 대기 중)")
                    if len(all_active_positions) > 0:
                        st.dataframe(pd.DataFrame(all_active_positions), use_container_width=True, hide_index=True)
                    else:
                        st.success("현재 장 마감 기준 현장에 파견되어 대기 중인 요원이 없습니다 (모두 성공 복귀 완료).")

                    st.markdown("")

                    # 4. 종목별 독립 성과 분석
                    st.markdown("#### 🔍 [종목별 독립 성과 분석] 어떤 주식이 어떻게 움직였나?")
                    s_cols = st.columns(len(stock_results))
                    for idx, (t_code, res) in enumerate(stock_results.items()):
                        with s_cols[idx]:
                            st.markdown(f"""
                            <div style="background:white; border:1px solid #d5dbdf; border-top:4px solid #2980b9; padding:12px; border-radius:6px;">
                                <div style="font-weight:bold; color:#2980b9; font-size:14px; margin-bottom:6px;">{res['name']} ({t_code})</div>
                                <div style="font-size:12px; color:#555; line-height:1.5;">
                                    • 승률: <b>{res['win_rate']:.1f}%</b> (익절 {res['win_trades']} / 손절 {res['loss_trades']})<br>
                                    • 실현 순익: <b style="color:#c0392b;">+{int(res['net_profit']):,}원</b><br>
                                    • 최종 평가자산: <b>{int(res['final_equity']):,}원</b><br>
                                    • 현금금고 / 코어: {int(res['reserve_cash']):,}원 / {res['core_shares']}주<br>
                                    • 현재 대기요원: <b style="color:#2980b9;">{res['active_count']}명</b>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                    st.markdown("---")

                    # 5. 플롯리 인터랙티브 자산 비교 차트
                    st.markdown("#### 📈 [전략 및 시장 비교] 오토파일럿 함대 vs 현금 vs KOSPI·KOSDAQ")
                    x_dates = [d.strftime('%Y-%m-%d') for d in combined_equity_df.index]
                    fig_chart = go.Figure()
                    fig_chart.add_trace(go.Scatter(x=x_dates, y=combined_equity_df['Portfolio_Equity'], mode='lines', name=f'오토파일럿 ({strategy_choice})', line=dict(color='#e74c3c', width=3)))
                    fig_chart.add_trace(go.Scatter(x=x_dates, y=[total_capital_input]*len(x_dates), mode='lines', name='전액 현금 (Cash)', line=dict(color='#f1c40f', width=1.5, dash='dot')))
                    
                    if not bench_df.empty:
                        try:
                            bench_clean = bench_df.reindex(combined_equity_df.index).ffill().bfill()
                            ks_col = '^KS11' if '^KS11' in bench_clean.columns else bench_clean.columns[0]
                            kq_col = '^KQ11' if '^KQ11' in bench_clean.columns else (bench_clean.columns[1] if len(bench_clean.columns)>1 else ks_col)
                            
                            ks_norm = total_capital_input * (bench_clean[ks_col] / bench_clean[ks_col].iloc[0])
                            kq_norm = total_capital_input * (bench_clean[kq_col] / bench_clean[kq_col].iloc[0])
                            fig_chart.add_trace(go.Scatter(x=x_dates, y=ks_norm, mode='lines', name='KOSPI 지수', line=dict(color='#2ecc71', width=1.2, dash='dash')))
                            fig_chart.add_trace(go.Scatter(x=x_dates, y=kq_norm, mode='lines', name='KOSDAQ 지수', line=dict(color='#9b59b6', width=1.2, dash='dash')))
                        except Exception:
                            pass

                    fig_chart.update_layout(height=450, template="plotly_white", margin=dict(l=10, r=10, t=30, b=10), hovermode="x unified")
                    st.plotly_chart(fig_chart, use_container_width=True)

                    st.markdown("---")

                    # 6. 전체 매매 장부 및 다운로드
                    st.markdown("### 📜 멀티 함대 통합 전체 매매 장부 (한국식 스마트 컬러 적용)")
                    if all_matched_trades:
                        df_trades = pd.DataFrame([{k: v for k, v in t.items() if k not in ['is_win', 'raw_profit', 'exit_date']} for t in all_matched_trades])
                        st.dataframe(style_trade_df(df_trades), use_container_width=True)
                        
                        csv_data = df_trades.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="📥 엑셀(CSV) 공식 작전 장부 다운로드 (메타데이터 포함)",
                            data=csv_data,
                            file_name=f"박가이버사령부_V10.12_공식작전장부_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("청산된 매매 기록이 없습니다.")

                except Exception as e:
                    st.error(f"❌ 시뮬레이션 중 에러 발생: {e}")
