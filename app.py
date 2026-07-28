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
st.set_page_config(page_title="박가이버 통합 작전 사령부 V10.2 Ultimate", page_icon="🛡️", layout="wide")

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

# --- 2. 동적 데이터베이스 및 종목 마스터 세션 초기화 ---
if "sector_db" not in st.session_state:
    st.session_state["sector_db"] = {
        "⚡ 반도체 & HBM / 칩렛": {"테크윙": "089030.KQ", "한미반도체": "042700.KS", "HPSP": "403870.KQ", "이오테크닉스": "039030.KQ", "리노공업": "058470.KQ", "ISC": "095340.KQ", "주성엔지니어링": "036930.KQ", "원익IPS": "240810.KQ", "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "피에스케이": "057030.KQ"},
        "🧬 바이오 & 제약 / 화장품": {"한국콜마": "161890.KS", "코스맥스": "192820.KS", "알테오젠": "196170.KQ", "셀트리온": "068270.KS", "삼성바이오로직스": "207940.KS", "HLB": "028300.KQ", "유한양행": "000100.KS", "리가켐바이오": "141080.KQ"},
        "📡 통신 & 방산 & 조선": {"RFHIC": "218410.KQ", "한화시스템": "272210.KS", "현대로템": "064350.KS", "LIG넥스원": "079550.KS", "한화오션": "042660.KS", "HD한국조선해양": "009540.KS", "두산에너빌리티": "034020.KS", "HD현대일렉트릭": "267260.KS"},
        "🔋 2차전지 & 에코": {"에코프로비엠": "247540.KQ", "에코프로": "086520.KQ", "LG에너지솔루션": "373220.KS", "POSCO홀딩스": "005490.KS", "엘앤에프": "066970.KQ", "포스코퓨처엠": "003670.KS"},
        "🚗 자동차 & 대표 제조": {"현대차": "005380.KS", "기아": "000270.KS", "현대모비스": "012330.KS"},
        "💻 IT & 플랫폼": {"NAVER": "035420.KS", "카카오": "035720.KS"}
    }

if "custom_stocks" not in st.session_state: st.session_state["custom_stocks"] = {}
if "my_holdings" not in st.session_state: st.session_state["my_holdings"] = ["SK하이닉스", "한미반도체", "테크윙", "HD현대일렉트릭", "HPSP"]
if "my_watchlist" not in st.session_state: st.session_state["my_watchlist"] = ["한화오션", "현대로템", "RFHIC", "한국콜마"]

KOREAN_STOCK_MASTER = {
    "한국콜마": "161890.KS", "RFHIC": "218410.KQ", "코스맥스": "192820.KS", "현대힘스": "460930.KQ", "한화오션": "042660.KS", "HD한국조선해양": "009540.KS", "에스피지": "058610.KQ", "레인보우로보틱스": "277810.KQ", "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "테크윙": "089030.KQ", "한미반도체": "042700.KS", "기가비스": "420770.KQ", "케이씨텍": "281820.KS", "이수화학": "005950.KS", "이수스페셜티케미컬": "457190.KS", "마녀공장": "439090.KQ", "뉴파워프라즈마": "144960.KQ", "두산에너빌리티": "034020.KS", "하나마이크론": "084370.KQ", "동진쎄미켐": "033640.KQ", "솔브레인": "357780.KQ", "가온칩스": "399500.KQ", "두산로보틱스": "454910.KS", "한화에어로스페이스": "012450.KS", "LIG넥스원": "079550.KS", "HD현대일렉트릭": "267260.KS", "LS일렉트릭": "010120.KS", "포스코퓨처엠": "003670.KS", "피에스케이": "057030.KQ"
}

MASTER_STOCK_DICT = {}
for sector, stocks in st.session_state["sector_db"].items():
    for name, code in stocks.items(): MASTER_STOCK_DICT[name] = code
for name, code in KOREAN_STOCK_MASTER.items():
    if name not in MASTER_STOCK_DICT: MASTER_STOCK_DICT[name] = code

def format_money(num):
    if num is None or pd.isna(num): return "-"
    sign = "-" if int(round(num)) < 0 else ""
    return f"{sign}{abs(int(round(num))):,}원"

def format_pure_number(num):
    if num is None or pd.isna(num): return "-"
    return f"{int(round(num)):,}"

# --- 3. 센스 있는 구독자 가이드 함수 (펼침기능 UI) ---
def render_subscriber_guide():
    with st.expander("📖 [당귀다TV] 박가이버 작전 사령부 V10.2 1분 탑승 가이드 (처음 오신 분 필독!)", expanded=False):
        st.markdown("""
        ### 🛡️ 4050 바쁜 직장인을 위한 '본업 집중형' 퀀트 투자 수칙
        
        안녕하세요! **'박가이버 작전 사령부'**는 장중 주가창을 몰래 보며 애태우던 직장인들을 위해 만들어진 **자동화 데이터 전략 도구**입니다. 딱 4가지만 알고 계시면 됩니다!

        ---

        1. **🕒 1분 컷 '순수 종가 매매' (장중 감시 엄금!)**
           - 근무 시간에는 주식 창을 완전히 봉인하고 본업에 집중하세요.
           - 매일 **오후 3시 20분(장 마감 10분 전)** 본 프로그램에 접속해 `🚨 오늘의 실전 매매 레이더`를 확인 후 **'동시호가(종가)'**로 원클릭 주문만 넣으면 끝입니다.

        2. **🚁 전원 동반 탈출 ('헬기 복귀' 자금 회전 전술)**
           - 계좌에 출격한 특수부대 요원(종목) 중 **단 1명이라도 목표가를 터치하면, 대기 중인 모든 부대원이 전원 동반 복귀(청산)**합니다.
           - 자금이 오랫동안 묶이는 것을 차단하고 **계좌 회전율을 극대화**하는 핵심 전술입니다.

        3. **🧠 지능형 날씨 판독기 (추세 맞춤형 목표가)**
           - 프로그램이 차트의 이동평균선(20/60/120일)을 보고 현재 시장 날씨를 스스로 판단합니다.
           - **☀️ 화창한 상승장 (정배열):** **+10%**까지 느긋하게 길게 먹고 탈출!
           - **🌧️ 태풍 부는 하락장 (역배열):** **+5%**로 욕심을 버리고 짧고 빠르게 튀어 오를 때 잽싸게 철수!

        4. **⛄ 스노우볼 레벨UP (복리 스케일업)**
           - 수익금이 차곡차곡 쌓여 **총자산이 +10% 불어날 때마다, 1회 출격 예산이 자동으로 10%씩 커집니다.**
           - 마치 게임 캐릭터가 레벨업해서 더 강력한 무기를 장착하듯, 내 자산이 스노우볼처럼 굴러가는 과정을 눈으로 확인해 보세요.
        """)

# --- 4. 사이드바 조종간 ---
st.sidebar.title("🎛️ 박가이버 사령부 V10.2")
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
    index=2
)
st.sidebar.markdown("---")

# =====================================================================
# 🗄️ 메뉴 1: 내 계좌 영구 DB
# =====================================================================
if menu_choice == "🗄️ 1. 내 계좌 영구 DB (보유 & 관심)":
    st.markdown("""<div class="hero-banner"><div class="hero-title">🗄️ 나만의 투자 영구 DB (마이 포트폴리오)</div></div>""", unsafe_allow_html=True)
    render_subscriber_guide()
    
    valid_holdings = [s for s in st.session_state["my_holdings"] if s in MASTER_STOCK_DICT]
    new_holdings = st.multiselect("실전 보유 종목 편집:", list(MASTER_STOCK_DICT.keys()), default=valid_holdings)
    if st.button("💾 보유 종목 저장", type="primary"):
        st.session_state["my_holdings"] = new_holdings
        st.success("🎉 저장되었습니다!")
        st.rerun()

# =====================================================================
# 🚨 메뉴 2: 오늘의 실전 매매 레이더
# =====================================================================
elif menu_choice == "🚨 2. 오늘의 실전 매매 레이더":
    st.markdown("""<div class="hero-banner"><div class="hero-title">🚨 오늘의 실전 매매 레이더 (출격 명령서)</div></div>""", unsafe_allow_html=True)
    render_subscriber_guide()
    
    st.info("🕒 매일 오후 3시 20분! 장 마감 직전 접속하셔서 오늘 줍줍할 종목이 있는지 포착합니다.")

# =====================================================================
# 🛡️ 메뉴 3: 과거 5년 백테스트 연구소
# =====================================================================
else:
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🛡️ V10.2 과거 5년 백테스트 연구소 (통합 엔진)</div>
        <div class="hero-subtitle">전원 동반 탈출(연쇄 청산), 지능형 목표가, 스노우볼 레벨업 로직이 완벽하게 탑재되었습니다.</div>
    </div>
    """, unsafe_allow_html=True)
    
    render_subscriber_guide()

    valid_watch_stocks = [s for s in st.session_state["my_holdings"] if s in MASTER_STOCK_DICT]
    PORTFOLIO_UNIVERSE = {s_name: MASTER_STOCK_DICT[s_name] for s_name in valid_watch_stocks if s_name in MASTER_STOCK_DICT}

    st.sidebar.subheader("⚙️ V10.2 통합 알고리즘 설정")
    use_smart_target = st.sidebar.checkbox("🧠 지능형 자동 목표가 (날씨에 따른 변환)", value=True)
    sell_target_input = 5.0
    if not use_smart_target:
        sell_target_input = st.sidebar.slider("🎯 고정 익절 목표 (+%)", 1, 30, 5, 1)
    
    use_batch_exit = st.sidebar.checkbox("🚁 전원 동반 탈출 (연쇄 청산 활성화)", value=True)
    total_capital_input = st.sidebar.number_input("🏦 총 작전 예산(원)", value=10000000, step=1000000)
    max_active_slots = st.sidebar.slider("전체 파견 슬롯 (최대 요원 수)", 2, 10, 5)
    use_compounding = st.sidebar.checkbox("🚀 복리 스케일업 (자산 10% 증가 시 레벨업)", value=True)
    buy_cond_input = st.sidebar.slider("🛒 진입 기준 (-% 하락 시)", 1, 20, 5, 1)
    stop_loss_input = st.sidebar.slider("🚨 손절 기준 (-%)", 0, 50, 15, 1)

    st.sidebar.subheader("💸 수수료 및 보상 정산")
    broker_fee_pct = st.sidebar.number_input("위탁수수료 (%)", value=0.015, format="%.3f") / 100
    tax_pct = st.sidebar.number_input("매도 거래세 (%)", value=0.18, format="%.2f") / 100
    reward_type = st.sidebar.selectbox("🎁 전리품 수령 방식", ["🌟 현금 50% + 열매 50% (하이브리드)", "전액 현금으로 챙기기", "열매로 결실 모으기"])

    years_val = st.sidebar.slider("백테스트 기간(년)", 1, 10, 5, 1)
    months_input = years_val * 12

    if st.sidebar.button("🚀 V10.2 타임머신 가동!", type="primary", use_container_width=True):
        if len(PORTFOLIO_UNIVERSE) == 0:
            st.error("❌ 감시 종목이 없습니다. 1번 메뉴에서 보유 종목을 골라주세요.")
        else:
            with st.spinner("📡 V10.2 슈퍼컴퓨터가 동반 청산 및 스노우볼 궤적을 계산 중입니다..."):
                end_date_str = datetime.datetime.today().strftime('%Y-%m-%d')
                start_date_str = (datetime.datetime.today() - relativedelta(months=months_input)).strftime('%Y-%m-%d')
                tickers = list(PORTFOLIO_UNIVERSE.values())
                
                raw_close = yf.download(tickers, start=start_date_str, end=end_date_str, interval="1d", progress=False)
                close_df = raw_close['Close'] if 'Close' in raw_close.columns.levels[0] else raw_close
                if isinstance(close_df, pd.Series): close_df = close_df.to_frame(name=tickers[0])
                close_df = close_df.dropna(how='all')
                close_df.index = clean_date_index(close_df.index)

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
                peak_asset_value = base_capital
                max_drawdown_pct = 0.0

                # 💡 안전하게 정제된 백테스트 메인 순회 루프
                for date, row in close_df.iterrows():
                    date_str = date.strftime('%Y-%m-%d')
                    
                    # 🎯 전원 동반 탈출 (연쇄 청산) 체크
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
                        last_processed_stock = ""
                        last_processed_price = 0.0
                        
                        for pos in active_positions:
                            t_code = pos['ticker']
                            curr_price = float(row[t_code]) if t_code in row and not pd.isna(row[t_code]) else pos['entry_price']
                            sell_gross_val = pos['invest_amount'] * (curr_price / pos['entry_price'])
                            
                            buy_fee = pos['invest_amount'] * broker_fee_pct
                            sell_fee = sell_gross_val * broker_fee_pct
                            sell_tax = sell_gross_val * tax_pct
                            total_trade_cost = buy_fee + sell_fee + sell_tax
                            
                            net_profit = (sell_gross_val - pos['invest_amount']) - total_trade_cost
                            batch_net_profit += net_profit
                            batch_invested += pos['invest_amount']
                            
                            last_processed_stock = pos['stock_name']
                            last_processed_price = curr_price
                            
                            trade_logs.append({
                                '요원': pos['name'], '작전 구역': pos['stock_name'], '출격일': pos['entry_date'],
                                '진입금액': f"{format_pure_number(pos['invest_amount'])}원",
                                '복귀일': date_str, '순수익률': f"{(net_profit / pos['invest_amount']) * 100:.2f}%",
                                '구분': winner_reason
                            })
                        
                        total_success += 1
                        
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
                                
                            buyable_shares = int(harvest_amt // last_processed_price) if (harvest_amt > 0 and last_processed_price > 0) else 0
                            leftover = harvest_amt - (buyable_shares * last_processed_price)
                            
                            if buyable_shares > 0 and last_processed_stock in free_shares_dict:
                                free_shares_dict[last_processed_stock] += buyable_shares
                                
                            current_cash += (batch_invested + cash_amt + leftover)
                            
                            # 🚀 스노우볼 레벨UP
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
                                cost = (pos['invest_amount'] * broker_fee_pct) + (sell_gross * (broker_fee_pct + tax_pct))
                                net_profit = (sell_gross - pos['invest_amount']) - cost
                                current_cash += (pos['invest_amount'] + net_profit)
                                total_stop_loss += 1 if net_profit < 0 else 0
                                trade_logs.append({
                                    '요원': pos['name'], '작전 구역': pos['stock_name'], '출격일': pos['entry_date'],
                                    '진입금액': f"{format_pure_number(pos['invest_amount'])}원",
                                    '복귀일': date_str, '순수익률': f"{(net_profit / pos['invest_amount']) * 100:.2f}%",
                                    '구분': exit_reason
                                })
                            else:
                                survived_positions.append(pos)
                        active_positions = survived_positions

                    # 🛒 급락 타점 시 요원 파견
                    day_returns = return_df.loc[date] if date in return_df.index else None
                    if day_returns is not None and len(active_positions) < max_active_slots:
                        agent_budget = int(base_capital // max_active_slots)
                        
                        candidates = []
                        for s_name, t_code in PORTFOLIO_UNIVERSE.items():
                            if not any(p['ticker'] == t_code for p in active_positions) and t_code in day_returns and not pd.isna(day_returns[t_code]):
                                ret_val = float(day_returns[t_code])
                                if ret_val <= buy_cond:
                                    candidates.append((s_name, t_code, ret_val, float(row[t_code])))
                        
                        candidates.sort(key=lambda x: x[2])
                        
                        for cand in candidates:
                            if len(active_positions) >= max_active_slots: break
                            if current_cash < agent_budget: break
                            
                            s_name, t_code, ret_val, c_price = cand
                            
                            target_ret = sell_target_input if not use_smart_target else 5.0
                            regime_desc = "고정목표"
                            
                            if use_smart_target:
                                if t_code in ma20_df.columns and t_code in ma60_df.columns and t_code in ma120_df.columns:
                                    m20 = ma20_df.loc[date, t_code]
                                    m60 = ma60_df.loc[date, t_code]
                                    m120 = ma120_df.loc[date, t_code]
                                    
                                    if pd.notna(m20) and pd.notna(m60) and pd.notna(m120):
                                        is_super_bull = (c_price > m20) and (m20 > m60) and (m60 > m120)
                                        is_mid_bull = (m20 > m60) or (c_price > m60 > m120)
                                        
                                        if is_super_bull:
                                            target_ret = 10.0
                                            regime_desc = "🔥 완전정배열(+10%)"
                                        elif is_mid_bull:
                                            target_ret = 8.0
                                            regime_desc = "📈 중기정배열(+8%)"
                                        else:
                                            target_ret = 5.0
                                            regime_desc = "🌧️ 역배열/박스권(+5%)"
                                            
                            agent_counter += 1
                            current_cash -= agent_budget
                            active_positions.append({
                                'name': f"{agent_counter}호 요원", 'stock_name': s_name, 'ticker': t_code,
                                'entry_price': c_price, 'entry_date': date_str, 'invest_amount': agent_budget,
                                'target_ret': target_ret, 'regime_desc': regime_desc
                            })

                    eval_pos = sum([p['invest_amount'] * (float(row[p['ticker']]) / p['entry_price']) for p in active_positions if p['ticker'] in row and not pd.isna(row[p['ticker']])])
                    today_total_asset = current_cash + eval_pos
                    if today_total_asset > peak_asset_value: peak_asset_value = today_total_asset
                    current_drawdown = ((today_total_asset - peak_asset_value) / peak_asset_value) * 100
                    if current_drawdown < max_drawdown_pct: max_drawdown_pct = current_drawdown
                    asset_history.append({"Date": date_str, "Total_Asset": today_total_asset, "Drawdown": current_drawdown})

                last_row = close_df.iloc[-1]
                active_eval = sum([p['invest_amount'] * (float(last_row[p['ticker']]) / p['entry_price']) for p in active_positions if p['ticker'] in last_row and not pd.isna(last_row[p['ticker']])])
                fruit_eval = sum([count * float(last_row[PORTFOLIO_UNIVERSE[s_name]]) for s_name, count in free_shares_dict.items() if count > 0 and PORTFOLIO_UNIVERSE[s_name] in last_row and not pd.isna(last_row[PORTFOLIO_UNIVERSE[s_name]])])
                
                final_total = current_cash + active_eval + fruit_eval
                total_return_pct = ((final_total - total_capital_input) / total_capital_input) * 100
                
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">
                    <div>
                        <h2 style="margin: 0; color: #0f172a; font-weight: 800;">🏆 V10.2 최종 성과 대시보드</h2>
                        <p style="margin: 4px 0 0 0; font-size: 0.95rem; color: #475569; font-weight: 700;">
                            🚀 스노우볼 레벨UP 달성: <b style="color: #ef4444; font-size: 1.1rem;">총 {level_up_count}회</b> (예산 증액 성공!)
                        </p>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                m0, m1, m2, m3 = st.columns(4)
                m0.metric("🏁 원금 예산", format_money(total_capital_input))
                m1.metric(f"✨ 최종 총자산", format_money(final_total), delta=f"{total_return_pct:.2f}%")
                m2.metric("🌊 최대 낙폭 (MDD)", f"{max_drawdown_pct:.1f}%")
                m3.metric("📦 무료 주식(열매) 평가액", format_money(fruit_eval))
                
                st.markdown("---")
                tab1, tab2 = st.tabs(["📊 자산 성장 차트", "📜 교전 일지 (매매장부)"])
                
                with tab1:
                    asset_df = pd.DataFrame(asset_history)
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3])
                    fig.add_trace(go.Scatter(x=asset_df['Date'], y=asset_df['Total_Asset'], mode='lines', name='총자산', line=dict(color='#2563eb', width=3), fill='tozeroy'), row=1, col=1)
                    fig.add_hline(y=total_capital_input, line_dash="solid", line_color="#ef4444", annotation_text="초기 원금", row=1, col=1)
                    fig.add_trace(go.Scatter(x=asset_df['Date'], y=asset_df['Drawdown'], mode='lines', name='MDD', line=dict(color='#dc2626', width=1.5), fill='tozeroy'), row=2, col=1)
                    fig.update_layout(height=600, template="plotly_white")
                    st.plotly_chart(fig, use_container_width=True)
                    
                with tab2:
                    if trade_logs:
                        st.dataframe(pd.DataFrame(list(reversed(trade_logs))), use_container_width=True)
                    else:
                        st.info("거래 내역이 없습니다.")
