import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
from dateutil.relativedelta import relativedelta
import plotly.express as px

# --- 1. 페이지 웹 디자인 세팅 (모바일 다크모드 카드 가독성 극대화 CSS) ---
st.set_page_config(page_title="박가이버 통합 작전 사령부 V6 Pro", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        padding: 14px 16px !important;
        border-radius: 12px !important;
        border: 1px solid #94a3b8 !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.08) !important;
    }
    div[data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] * {
        color: #0f172a !important;
        font-size: 0.9rem !important;
        font-weight: 800 !important;
    }
    div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] * {
        color: #1e293b !important;
        font-size: 1.3rem !important;
        font-weight: 900 !important;
    }
    .main-header { font-size: 1.6rem !important; font-weight: 800; margin-bottom: 0.2rem; }
    .sub-header { font-size: 0.88rem !important; color: #64748b; margin-bottom: 1.0rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. 동적 데이터베이스 및 스마트 종목 마스터 세션 초기화 ---
if "sector_db" not in st.session_state:
    st.session_state["sector_db"] = {
        "⚡ 반도체 & HBM / 칩렛": {
            "테크윙": "089030.KQ", "한미반도체": "042700.KS", "HPSP": "403870.KQ",
            "이오테크닉스": "039030.KQ", "리노공업": "058470.KQ", "ISC": "095340.KQ",
            "주성엔지니어링": "036930.KQ", "원익IPS": "240810.KQ", "삼성전자": "005930.KS", "SK하이닉스": "000660.KS"
        },
        "🧬 바이오 & 제약": {
            "알테오젠": "196170.KQ", "셀트리온": "068270.KS", "삼성바이오로직스": "207940.KS",
            "HLB": "028300.KQ", "유한양행": "000100.KS", "리가켐바이오": "141080.KQ"
        },
        "🔋 2차전지 & 에코": {
            "에코프로비엠": "247540.KQ", "에코프로": "086520.KQ", "LG에너지솔루션": "373220.KS",
            "POSCO홀딩스": "005490.KS", "엘앤에프": "066970.KQ"
        },
        "🚗 자동차 & 대표 제조": {
            "현대차": "005380.KS", "기아": "000270.KS", "현대모비스": "012330.KS"
        },
        "💻 IT & 플랫폼": {
            "NAVER": "035420.KS", "카카오": "035720.KS"
        }
    }

# 🌟 대폭 확장된 한국 주요 종목 마스터 사전 (이수화학 등 추가)
KOREAN_STOCK_MASTER = {
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "LG에너지솔루션": "373220.KS",
    "삼성바이오로직스": "207940.KS", "현대차": "005380.KS", "기아": "000270.KS",
    "POSCO홀딩스": "005490.KS", "NAVER": "035420.KS", "카카오": "035720.KS",
    "셀트리온": "068270.KS", "한화에어로스페이스": "012450.KS", "LG전자": "066570.KS",
    "현대모비스": "012330.KS", "KB금융": "105560.KS", "신한지주": "055550.KS",
    "테크윙": "089030.KQ", "한미반도체": "042700.KS", "HPSP": "403870.KQ",
    "이오테크닉스": "039030.KQ", "리노공업": "058470.KQ", "ISC": "095340.KQ",
    "주성엔지니어링": "036930.KQ", "원익IPS": "240810.KQ", "알테오젠": "196170.KQ",
    "에코프로비엠": "247540.KQ", "에코프로": "086520.KQ", "엘앤에프": "066970.KQ",
    "HLB": "028300.KQ", "유한양행": "000100.KS", "리가켐바이오": "141080.KQ",
    "레인보우로보틱스": "277810.KQ", "두산에너빌리티": "034020.KS", "이수화학": "005950.KS",
    "POSCO엠텍": "009520.KS", "한화오션": "042660.KS", "삼성중공업": "010140.KS"
}

MASTER_STOCK_DICT = {}
for sector, stocks in st.session_state["sector_db"].items():
    for name, code in stocks.items():
        MASTER_STOCK_DICT[name] = code
for name, code in KOREAN_STOCK_MASTER.items():
    if name not in MASTER_STOCK_DICT:
        MASTER_STOCK_DICT[name] = code

if "selected_stocks" not in st.session_state:
    st.session_state["selected_stocks"] = ["테크윙", "한미반도체", "HPSP", "알테오젠", "에코프로비엠"]

# 🌟 선택된 종목이 마스터에 확실히 존재하도록 필터링 (에러 원천 방어)
st.session_state["selected_stocks"] = [s for s in st.session_state["selected_stocks"] if s in MASTER_STOCK_DICT]

def format_money(num):
    return f"{int(round(num)):,}"

# --- 3. 사이드바 조종간 ---
st.sidebar.title("🎛️ 박가이버 사령부")
menu_choice = st.sidebar.radio(
    "모드 선택",
    ["🔎 1. 작전 구역(섹터) 탐색기", "🛡️ 2. 실전 작전 통제실 (백테스트)"],
    index=1
)
st.sidebar.markdown("---")

# =====================================================================
# 🔎 모드 1: 작전 구역(섹터) 탐색기
# =====================================================================
if menu_choice == "🔎 1. 작전 구역(섹터) 탐색기":
    st.markdown('<div class="main-header">🔎 작전 구역 및 스마트 종목 탐색기</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">원하는 종목 이름을 검색하거나 섹터별로 둘러봐 바구니에 담을 수 있습니다.</div>', unsafe_allow_html=True)

    # 🌟 [최상단 배치] 스마트 종목 이름 검색 및 자동 등록 구역
    st.markdown("### 🔍 1. 스마트 종목 이름 검색 & 자동 등록")
    st.info("💡 종목 이름(예: 삼성전자, 이수화학, 셀트리온 등)을 입력하시면 코드가 자동으로 검색되어 아래 바구니에 쏙 담깁니다!")
    
    s_col1, s_col2, s_col3 = st.columns([2, 1, 1])
    search_input = s_col1.text_input("종목명 입력", placeholder="예: 삼성전자, 이수화학", key="smart_search_input_v4")
    market_choice = s_col2.selectbox("소속 시장", ["코스피 (.KS)", "코스닥 (.KQ)"], key="smart_market_choice_v4")
    
    if s_col3.button("➕ 검색해서 바구니 담기", type="primary"):
        query = search_input.strip()
        if not query:
            st.warning("⚠️ 검색할 종목 이름을 입력해 주세요.")
        else:
            resolved_code = None
            resolved_name = query
            
            if query in KOREAN_STOCK_MASTER:
                resolved_code = KOREAN_STOCK_MASTER[query]
            elif query in MASTER_STOCK_DICT:
                resolved_code = MASTER_STOCK_DICT[query]
            else:
                matched_key = next((k for k in MASTER_STOCK_DICT.keys() if query in k), None)
                if matched_key:
                    resolved_code = MASTER_STOCK_DICT[matched_key]
                    resolved_name = matched_key
                elif len(query) == 6 and query.isdigit():
                    suffix = ".KS" if "코스피" in market_choice else ".KQ"
                    resolved_code = query + suffix
                    resolved_name = query
            
            if resolved_code:
                MASTER_STOCK_DICT[resolved_name] = resolved_code
                if resolved_name not in st.session_state["selected_stocks"]:
                    st.session_state["selected_stocks"].append(resolved_name)
                    st.success(f"✨ [{resolved_name} ({resolved_code})] 종목이 바구니에 추가되었습니다!")
                    st.rerun()
                else:
                    st.info(f"💡 '{resolved_name}' 종목은 이미 바구니에 들어있습니다.")
            else:
                # 직접 신규 등록할 수 있도록 유도
                suffix = ".KS" if "코스피" in market_choice else ".KQ"
                st.error(f"❌ '{query}'에 해당하는 종목을 찾지 못했습니다. 아래 [탐색기 커스텀] 메뉴에서 종목코드를 직접 등록해 주세요!")

    st.markdown("---")

    st.markdown("### 🎯 2. 테마/섹터별 둘러보기")
    col_sec1, col_sec2 = st.columns([1, 2])
    with col_sec1:
        selected_sector = st.selectbox("📂 탐색할 섹터 선택", list(st.session_state["sector_db"].keys()))
    
    sector_stocks_dict = st.session_state["sector_db"][selected_sector]
    
    with col_sec2:
        st.write(f"▼ **[{selected_sector}] 보유 종목 리스트**")
        sector_target_list = st.multiselect(
            "바구니로 전송할 종목 선택:",
            options=list(sector_stocks_dict.keys()),
            default=list(sector_stocks_dict.keys()),
            key=f"sec_select_{selected_sector}"
        )
        
        if st.button(f"🛒 선택 종목 [백테스트 바구니] 추가", type="secondary"):
            added_count = 0
            for s_name in sector_target_list:
                if s_name not in st.session_state["selected_stocks"]:
                    st.session_state["selected_stocks"].append(s_name)
                    added_count += 1
            st.toast(f"🎉 {added_count}개 종목이 바구니에 담겼습니다!")

    st.markdown("---")

    with st.expander("🛠️ [탐색기 커스텀] 나만의 신규 섹터/종목 등록"):
        tab_cust1, tab_cust2 = st.tabs(["➕ 기존 섹터 종목 추가", "📂 신규 섹터 생성"])
        
        with tab_cust1:
            c_col1, c_col2, c_col3 = st.columns([1, 1, 1])
            target_sec = c_col1.selectbox("추가할 섹터", list(st.session_state["sector_db"].keys()))
            new_s_name = c_col2.text_input("종목명", value="삼성스파크", key="add_s_name")
            new_s_code = c_col3.text_input("종목코드 (예: 005930.KS)", value="005930.KS", key="add_s_code")
            
            if st.button("➕ 해당 섹터에 종목 추가"):
                if new_s_name and new_s_code:
                    st.session_state["sector_db"][target_sec][new_s_name] = new_s_code
                    MASTER_STOCK_DICT[new_s_name] = new_s_code
                    if new_s_name not in st.session_state["selected_stocks"]:
                        st.session_state["selected_stocks"].append(new_s_name)
                    st.success(f"✨ [{target_sec}] 섹터에 '{new_s_name}' 추가 및 바구니 담기 완료!")
                    st.rerun()

        with tab_cust2:
            s_col1, s_col2, s_col3 = st.columns([1, 1, 1])
            new_sec_name = s_col1.text_input("신규 섹터명", value="🤖 로봇 & AI")
            first_s_name = s_col2.text_input("첫 종목명", value="레인보우로보틱스")
            first_s_code = s_col3.text_input("첫 종목코드", value="277810.KQ")
            
            if st.button("📂 신규 섹터 생성하기"):
                if new_sec_name and first_s_name and first_s_code:
                    st.session_state["sector_db"][new_sec_name] = {first_s_name: first_s_code}
                    MASTER_STOCK_DICT[first_s_name] = first_s_code
                    if first_s_name not in st.session_state["selected_stocks"]:
                        st.session_state["selected_stocks"].append(first_s_name)
                    st.success(f"🎉 신규 섹터 [{new_sec_name}] 생성 및 종목 추가 완료!")
                    st.rerun()

    st.markdown("---")

    st.markdown("### 🛒 3. 작전 통제실로 전송할 종목 바구니 담기")

    st.session_state["selected_stocks"] = st.multiselect(
        "백테스트 검증을 진행할 종목들을 선택해 주세요 (1개~10개 권장):",
        options=list(MASTER_STOCK_DICT.keys()),
        default=st.session_state["selected_stocks"]
    )

    if st.session_state["selected_stocks"]:
        summary_data = []
        for name in st.session_state["selected_stocks"]:
            code = MASTER_STOCK_DICT.get(name, "")
            market_type = "코스닥" if ".KQ" in code else ("코스피" if ".KS" in code else "기타")
            summary_data.append({"종목명": name, "티커 코드": code, "소속 테마/섹터": market_type})
        
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
        st.markdown("---")
        
        if st.button("🚀 선택한 종목들을 [작전 통제실]로 즉시 전송!", type="primary"):
            st.success(f"🎉 총 {len(st.session_state['selected_stocks'])}개 종목 설정 완료!")
            st.info("👈 왼쪽 사이드바 메뉴에서 [🛡️ 2. 실전 작전 통제실]을 누르세요!")

# =====================================================================
# 🛡️ 모드 2: 실전 작전 통제실 (백테스트 대시보드 V6)
# =====================================================================
else:
    st.markdown('<div class="main-header">🛡️ 박가이버표 실전 작전 통제실</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">1,000만 원 원금 보호 및 스노우볼 자산 증식 알고리즘 시뮬레이터입니다.</div>', unsafe_allow_html=True)

    st.sidebar.subheader("⚙️ 빠른 전략 프리셋")
    preset_col1, preset_col2 = st.sidebar.columns(2)
    buy_preset, sell_preset = 5, 5
    if preset_col1.button("⚡ 적극 공격형"):
        buy_preset, sell_preset = 3, 7
        st.sidebar.info("적극 공격형 (-3% 진입 / +7% 익절) 설정 완료!")
    if preset_col2.button("🛡️ 안정 스노우볼"):
        buy_preset, sell_preset = 5, 5
        st.sidebar.info("안정 스노우볼 (-5% 진입 / +5% 익절) 설정 완료!")

    st.sidebar.subheader("🎯 감시 작전 구역 선택")
    selected_stock_names = st.sidebar.multiselect(
        "감시 종목 리스트",
        options=list(MASTER_STOCK_DICT.keys()),
        default=st.session_state["selected_stocks"]
    )

    PORTFOLIO_UNIVERSE = {s_name: MASTER_STOCK_DICT[s_name] for s_name in selected_stock_names if s_name in MASTER_STOCK_DICT}

    st.sidebar.markdown("---")
    total_capital_input = st.sidebar.number_input("🏦 총 작전 예산(원)", value=10000000, step=1000000)
    invest_amount_input = st.sidebar.number_input("💰 회당 초기 진입금액(원)", value=2000000, step=500000)
    max_active_slots = max(1, int(total_capital_input // invest_amount_input))
    st.sidebar.info(f"💡 동원 가능 요원 슬롯: **{max_active_slots}개**")

    use_compounding = st.sidebar.checkbox("🚀 복리 스케일업 모드", value=True)
    time_unit = st.sidebar.radio("🗓️ 기간 단위", ["월 단위 (개월)", "년 단위 (년)"], horizontal=True)

    if time_unit == "월 단위 (개월)":
        months_input = st.sidebar.slider("백테스트 기간(개월)", 1, 120, 60, 1)
        period_label = f"{months_input}개월"
    else:
        years_val = st.sidebar.slider("백테스트 기간(년)", 1, 10, 5, 1)
        months_input = years_val * 12
        period_label = f"{years_val}년"

    buy_cond_input = st.sidebar.slider("🛒 진입 기준 (-% 하락 시)", 1, 20, buy_preset, 1)
    sell_target_input = st.sidebar.slider("🎯 익절 목표 (+%)", 1, 30, sell_preset, 1)
    stop_loss_input = st.sidebar.slider("🚨 손절 기준 (-%)", 0, 50, 15, 5)

    st.sidebar.subheader("💸 거래비용 적용")
    use_fee = st.sidebar.checkbox("수수료/거래세 반영", value=True)
    broker_fee_pct = (st.sidebar.number_input("위탁수수료 (%)", value=0.015, format="%.3f") / 100) if use_fee else 0.0
    tax_pct = (st.sidebar.number_input("매도 거래세 (%)", value=0.18, format="%.2f") / 100) if use_fee else 0.0

    reward_type = st.sidebar.selectbox(
        "🎁 전리품 수령 방식", 
        ["전액 현금으로 챙기기", "열매로 결실 모으기", "🌟 현금 50% + 열매 50% (하이브리드)"]
    )
    
    run_btn = st.sidebar.button("🚀 1,000만 원 작전 검증 개시!", type="primary")

    st.write(f"### 🛡️ 감시 구역 요약 ({len(PORTFOLIO_UNIVERSE)}개 종목)")
    universe_list = []
    for name, code in PORTFOLIO_UNIVERSE.items():
        market_type = "코스닥" if ".KQ" in code else ("코스피" if ".KS" in code else "기타")
        universe_list.append({"구역명": name, "티커": code.split('.')[0], "시장": market_type, "상태": "실시간 감시 중"})
    st.dataframe(pd.DataFrame(universe_list), use_container_width=True, hide_index=True)
    st.markdown("---")

    if run_btn:
        if len(PORTFOLIO_UNIVERSE) == 0:
            st.error("❌ 선택된 종목이 없습니다. 1개 이상 선택해 주세요.")
        else:
            with st.spinner("📡 슈퍼컴퓨터가 과거 파동 및 배당금 데이터를 분석 중입니다..."):
                try:
                    end_date = datetime.datetime.today()
                    start_date = end_date - relativedelta(months=months_input)
                    tickers = list(PORTFOLIO_UNIVERSE.values())
                    
                    raw_df = yf.download(tickers, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), actions=True, progress=False)

                    if isinstance(raw_df.columns, pd.MultiIndex):
                        close_df = raw_df['Close']
                        div_df = raw_df['Dividends'] if 'Dividends' in raw_df.columns.levels[0] else pd.DataFrame(index=raw_df.index, columns=tickers).fillna(0)
                    else:
                        close_df = pd.DataFrame({tickers[0]: raw_df['Close']})
                        div_df = pd.DataFrame({tickers[0]: raw_df['Dividends']}) if 'Dividends' in raw_df.columns else pd.DataFrame({tickers[0]: 0}, index=raw_df.index)

                    return_df = close_df.pct_change() * 100
                    buy_cond = -float(buy_cond_input)
                    sell_target = float(sell_target_input)
                    stop_loss_limit = -float(stop_loss_input) if stop_loss_input > 0 else None

                    current_cash = float(total_capital_input)
                    active_positions, trade_logs, daily_returns_history, asset_history = [], [], [], []
                    agent_counter = 0

                    yearly_stats = {}
                    free_shares_dict = {s_name: 0 for s_name in PORTFOLIO_UNIVERSE.keys()}
                    stock_win_stats = {s_name: {'success': 0, 'stop': 0, 'profit_gain': 0, 'loss_cost': 0} for s_name in PORTFOLIO_UNIVERSE.keys()}

                    total_success, total_stop_loss, total_cash_profit, total_fee_tax_paid = 0, 0, 0, 0
                    global_max_deployed = 0
                    daily_deployment_snapshots = []
                    missed_opportunities = []
                    total_dividend_profit = 0

                    for date, row in close_df.iterrows():
                        date_str = date.strftime('%Y-%m-%d')
                        year = date.year
                        if year not in yearly_stats:
                            yearly_stats[year] = {'success': 0, 'stop': 0, 'shares': 0, 'cash': 0, 'share_val': 0.0}
                        
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
                                '진입금액': '-', '매도금액': '-', '진입단가': '-', '복귀일': date_str,
                                '청산단가': '-', '순수익률': '-',
                                '정산내역': f"🍯 꿀 수입: +{format_money(daily_dividend_sum)}원", '구분': '🌟 특별 보너스'
                            })
                        
                        survived_positions = []
                        for pos in active_positions:
                            t_code = pos['ticker']
                            if t_code in row and not pd.isna(row[t_code]):
                                curr_price = float(row[t_code])
                                gross_ret = ((curr_price - pos['entry_price']) / pos['entry_price']) * 100
                                is_exit, exit_reason = False, ""

                                if gross_ret >= sell_target:
                                    is_exit, exit_reason = True, f"🎯 정상 복귀(+{sell_target_input}%)"
                                elif stop_loss_limit is not None and gross_ret <= stop_loss_limit:
                                    is_exit, exit_reason = True, f"🚨 강제 철수(-{stop_loss_input}%)"

                                if is_exit:
                                    sell_gross_val = pos['invest_amount'] * (curr_price / pos['entry_price'])
                                    buy_fee = pos['invest_amount'] * broker_fee_pct
                                    sell_fee = sell_gross_val * broker_fee_pct
                                    sell_tax = sell_gross_val * tax_pct
                                    total_trade_cost = buy_fee + sell_fee + sell_tax
                                    total_fee_tax_paid += total_trade_cost

                                    net_profit = (sell_gross_val - pos['invest_amount']) - total_trade_cost
                                    net_ret = (net_profit / pos['invest_amount']) * 100
                                    s_name = pos['stock_name']
                                    
                                    if gross_ret >= sell_target:
                                        total_success += 1
                                        yearly_stats[year]['success'] += 1
                                        stock_win_stats[s_name]['success'] += 1
                                        stock_win_stats[s_name]['profit_gain'] += net_profit
                                        
                                        if reward_type == '열매로 결실 모으기':
                                            buyable = int(max(0, net_profit) // curr_price)
                                            leftover = net_profit - (buyable * curr_price)
                                        elif reward_type == '🌟 현금 50% + 열매 50% (하이브리드)':
                                            share_budget = max(0, net_profit) / 2
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
                                    daily_returns_history.append(net_ret)

                                    log_reward = f"열매 {buyable}개 + 잔돈/수익 {format_money(leftover)}원" if buyable > 0 else f"{format_money(leftover)}원"
                                    trade_logs.append({
                                        '요원': pos['name'], '작전 구역': pos['stock_name'], '출격일': pos['entry_date'],
                                        '진입금액': f"{format_money(pos['invest_amount'])}원",
                                        '매도금액': f"{format_money(sell_gross_val)}원",
                                        '진입단가': f"{format_money(pos['entry_price'])}원", '복귀일': date_str,
                                        '청산단가': f"{format_money(curr_price)}원", '순수익률': f"{net_ret:.2f}%",
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
                                    if ret_val <= buy_cond:
                                        candidates.append((s_name, t_code, ret_val, float(row[t_code])))
                            candidates.sort(key=lambda x: x[2])

                            for cand in candidates:
                                actual_invest = min(dynamic_invest_amount, current_cash)
                                
                                if len(active_positions) >= max_active_slots:
                                    missed_opportunities.append({
                                        "발생 일자": date_str, "미출격 종목": cand[0], "당일 하락률": f"{cand[2]:.2f}%",
                                        "불가 사유": f"요원 슬롯 풀가동 ({max_active_slots}/{max_active_slots}개)"
                                    })
                                elif actual_invest < 500000 or current_cash < 500000:
                                    missed_opportunities.append({
                                        "발생 일자": date_str, "미출격 종목": cand[0], "당일 하락률": f"{cand[2]:.2f}%",
                                        "불가 사유": f"가용 현금 부족 ({format_money(current_cash)}원)"
                                    })
                                else:
                                    agent_counter += 1
                                    s_name, t_code, ret_val, c_price = cand
                                    current_cash -= actual_invest
                                    active_positions.append({
                                        'name': f"{agent_counter}호 요원", 'stock_name': s_name, 'ticker': t_code,
                                        'entry_price': c_price, 'entry_date': date_str, 'invest_amount': actual_invest
                                    })

                        curr_count = len(active_positions)
                        if curr_count > global_max_deployed: global_max_deployed = curr_count
                        if curr_count > 0:
                            daily_deployment_snapshots.append({
                                "발생 일자": date_str, "동시 출격 수": curr_count,
                                "출격 종목 리스트": ", ".join([p['stock_name'] for p in active_positions])
                            })

                        eval_pos = sum([p['invest_amount'] * (float(row[p['ticker']]) / p['entry_price']) for p in active_positions if p['ticker'] in row and not pd.isna(row[p['ticker']])])
                        asset_history.append({"Date": date, "Total_Asset": current_cash + eval_pos})

                    last_row = close_df.iloc[-1]
                    active_eval_value = sum([p['invest_amount'] * (float(last_row[p['ticker']]) / p['entry_price']) for p in active_positions if p['ticker'] in last_row and not pd.isna(last_row[p['ticker']])])
                    total_free_shares_count = sum(free_shares_dict.values())
                    total_free_shares_value = sum([count * float(last_row[PORTFOLIO_UNIVERSE[s_name]]) for s_name, count in free_shares_dict.items() if count > 0 and PORTFOLIO_UNIVERSE[s_name] in last_row and not pd.isna(last_row[PORTFOLIO_UNIVERSE[s_name]])])

                    final_total_asset = current_cash + active_eval_value + total_free_shares_value
                    total_net_profit = final_total_asset - total_capital_input
                    total_return_pct = (total_net_profit / total_capital_input) * 100
                    total_trades = total_success + total_stop_loss
                    win_rate = (total_success / total_trades * 100) if total_trades > 0 else 0

                    st.subheader("🏆 백테스트 최종 성과 지표")
                    
                    with st.expander("📖 [클릭] 최종 성과 지표가 무슨 뜻인가요? (초보자용 알기 쉬운 해설서)"):
                        st.markdown("""
                        * **🏁 원금 예산:** 작전을 시작하기 위해 사령부 금고에 처음으로 밀어 넣은 **종잣돈(씨앗 돈)**입니다. (마법의 씨앗 주머니)
                        * **✨ 총자산:** 백테스트 기간이 끝난 후, 내 통장(현금)과 현장(주식)에 남아 있는 모든 재산을 싹싹 끌어모은 **지갑 속 최종 재산 총액**입니다.
                        * **📈 총 순수익금:** 내 원금을 제외하고, 순수하게 내 주머니로 불어나서 들어온 **진짜 알짜배기 순이익**입니다.
                        * **💵 최종 현금:** 다음 작전 때 더 큰 덩치로 출격할 수 있도록 내 통장에 현금으로 차곡차곡 챙겨둔 **비상금이자 실탄 곳간**입니다.
                        * **🎯 작전 승률:** 요원들이 출격했다가 목표가(익절)를 찍고 웃으며 돌아온 **작전 성공 확률**입니다. (야구 경기 승률처럼 70% 안팎이면 매우 훌륭합니다!)
                        * **🍯 누적 배당금:** 주식을 보유하는 동안 기업들이 고맙다고 통장에 꽂아준 **나무에서 툭툭 떨어진 달콤한 보너스 꿀(배당금)**입니다.
                        * **🐣 연금통장 변환기:** 불어난 총자산을 연 4% 배당 ETF에 넣어두었을 때, 원금 손실 없이 평생 매월 따박따박 받을 수 있는 **제2의 월급(연금) 환산 금액**입니다!
                        """)

                    m1, m2, m3 = st.columns(3)
                    m1.metric("🏁 원금 예산", f"{format_money(total_capital_input)}원")
                    m2.metric(f"✨ {period_label} 후 총자산", f"{format_money(final_total_asset)}원")
                    m3.metric("📈 총 순수익금", f"{format_money(total_net_profit)}원", delta=f"{total_return_pct:.2f}%")
                    
                    st.write("") 
                    
                    m4, m5, m6 = st.columns(3)
                    if reward_type in ['열매로 결실 모으기', '🌟 현금 50% + 열매 50% (하이브리드)']:
                        m4.metric("💵 가용 현금", f"{format_money(current_cash)}원", delta=f"매매 잔돈/수익: +{format_money(total_cash_profit)}원")
                        m5.metric("📦 공짜 열매", f"{total_free_shares_count:,}주", delta=f"가치: {format_money(total_free_shares_value)}원")
                    else:
                        m4.metric("💵 최종 현금", f"{format_money(current_cash)}원", delta=f"매매 수익금: +{format_money(total_cash_profit)}원")
                        m5.metric("🎯 작전 승률", f"{win_rate:.1f}%", delta=f"{total_trades}전 {total_success}승")
                        
                    m6.metric("🍯 누적 배당금 (보너스)", f"{format_money(total_dividend_profit)}원", delta="나무에서 떨어진 달콤한 꿀")

                    if use_fee:
                        st.caption(f"💸 **실전 거래비용 정산 완료:** 누적 수수료 및 거래세 -{format_money(total_fee_tax_paid)}원 이미 차감됨")

                    monthly_pension = (final_total_asset * 0.04) / 12
                    st.markdown(f"""
                    <div style="background: linear-gradient(to right, #fffbeb, #fef3c7); padding: 20px; border-radius: 12px; border-left: 6px solid #f59e0b; margin-top: 15px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                        <h4 style="margin-top: 0; color: #d97706; font-size: 1.2rem;">🐣 은퇴자를 위한 '제2의 연금통장' 변환기</h4>
                        <p style="font-size: 1.05rem; color: #451a03; margin-bottom: 0; line-height: 1.5;">
                            이 백테스트로 달성한 총자산 <b>{format_money(final_total_asset)}원</b>을 연 4% 배당 ETF에 재투자한다면?<br>
                            원금을 단 1원도 까먹지 않고, 매월 <b>💰 {format_money(monthly_pension)}원의 제2의 월급(연금)</b>을 평생 받을 수 있습니다!
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

                    if reward_type in ['열매로 결실 모으기', '🌟 현금 50% + 열매 50% (하이브리드)'] and total_free_shares_count > 0:
                        with st.expander("🍎 내 보물상자 (수집한 공짜 열매 상세 내역) 열어보기"):
                            fruit_details = []
                            for s_name, count in free_shares_dict.items():
                                if count > 0:
                                    t_code = PORTFOLIO_UNIVERSE[s_name]
                                    s_val = count * float(last_row[t_code]) if t_code in last_row and not pd.isna(last_row[t_code]) else 0
                                    fruit_details.append({
                                        "종목명(작전 구역)": s_name,
                                        "수집한 열매": f"{count:,}주",
                                        "현재 평가 가치": f"{format_money(s_val)}원"
                                    })
                            st.dataframe(pd.DataFrame(fruit_details), use_container_width=True, hide_index=True)

                    st.markdown("---")

                    tab1, tab2, tab3, tab4 = st.tabs([
                        "📊 1. 누적 자산 성장 곡선", 
                        "🔍 2. 자금 회전율 & 미출격 진단", 
                        "📈 3. 종목/연도별 손익분석", 
                        "📜 4. 현장 대기요원 & 매매장부"
                    ])

                    with tab1:
                        st.write("### 📈 백테스트 기간 자산 증식 추이")
                        asset_df = pd.DataFrame(asset_history)
                        fig_asset = px.line(asset_df, x="Date", y="Total_Asset", title=f"1,000만 원 자본금의 {period_label} 성취 곡선")
                        fig_asset.add_hline(y=total_capital_input, line_dash="dash", line_color="red", annotation_text="원금")
                        fig_asset.update_traces(line_color="#2563eb", line_width=2.5)
                        st.plotly_chart(fig_asset, use_container_width=True)

                    with tab2:
                        st.write("### 🔍 회전율 & 미출격 타점 분석 리포트")
                        st.warning(f"📊 {period_label} 기간 중 역사적 절대 최고 동시 출격 수: **총 {global_max_deployed}개 종목** (전체 슬롯: {max_active_slots}개)")
                        
                        if daily_deployment_snapshots:
                            snap_df = pd.DataFrame(daily_deployment_snapshots)
                            peak_df = snap_df[snap_df['동시 출격 수'] == global_max_deployed].drop_duplicates(subset=['발생 일자'])
                            st.write("▼ **역대 최고 자금 몰림(피크) 발생 일자 및 출격 목록:**")
                            st.dataframe(peak_df, use_container_width=True, hide_index=True)

                        st.markdown("---")
                        st.write("### 🚫 현금/슬롯 부족으로 놓쳐버린 출격 타점 추적기")
                        if missed_opportunities:
                            st.error(f"🚨 지난 {period_label} 동안 하락 타점(-{buy_cond_input}%)이 맞았으나, **현금 부족/슬롯 제한으로 놓친 기회가 총 {len(missed_opportunities)}회** 발생했습니다!")
                            st.dataframe(pd.DataFrame(missed_opportunities), use_container_width=True, hide_index=True)
                            st.info("💡 **전략 가이드:** 전체 슬롯 수를 올리거나 1회 진입금 비율을 조금 낮추면 이 타점들까지 알뜰하게 다 잡아채서 수익을 극대화할 수 있습니다!")
                        else:
                            st.success("🎉 단 한 번도 현금이나 슬롯이 부족해서 출격 기회를 놓친 적이 없습니다! 자금 관리가 100% 완벽했습니다!")

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
                                yearly_summary_list.append({
                                    "연도": str(y),
                                    "🎯 익절": f"{val['success']}회",
                                    "🚨 손절": f"{val['stop']}회",
                                    "📦 열매": f"{int(val['shares'])}주",
                                    "💎 열매 획득금액": f"{format_money(val['share_val'])}원",
                                    "💵 현금수익": f"{format_money(val['cash'])}원"
                                })
                            st.dataframe(pd.DataFrame(yearly_summary_list), use_container_width=True, hide_index=True)

                        st.markdown("---")
                        st.write("#### 🎯 종목별 손익 합계 표")
                        stock_summary = []
                        for s_name, stats in stock_win_stats.items():
                            s_total = stats['success'] + stats['stop']
                            s_win_rate = (stats['success'] / s_total * 100) if s_total > 0 else 0
                            
                            gained_shares = free_shares_dict.get(s_name, 0)
                            share_val = 0
                            if gained_shares > 0 and PORTFOLIO_UNIVERSE[s_name] in last_row and not pd.isna(last_row[PORTFOLIO_UNIVERSE[s_name]]):
                                share_val = gained_shares * float(last_row[PORTFOLIO_UNIVERSE[s_name]])

                            stock_summary.append({
                                "작전 구역": s_name, "총작전": f"{s_total}회", "승률": f"{s_win_rate:.1f}%",
                                "🎯 익절금": f"+{format_money(stats['profit_gain'])}원",
                                "🚨 손절금": f"{format_money(stats['loss_cost'])}원",
                                "✨ 순손익": f"{format_money(stats['profit_gain'] + stats['loss_cost'])}원",
                                "📦 획득 열매": f"{gained_shares}주",
                                "💎 열매 가치": f"{format_money(share_val)}원"
                            })
                        st.dataframe(pd.DataFrame(stock_summary), use_container_width=True, hide_index=True)

                    with tab4:
                        st.write("### ⚔️ 현재 현장 대기 요원 (평가 현황)")
                        if len(active_positions) > 0:
                            active_table = []
                            tot_inv = 0
                            tot_eval = 0
                            tot_prof = 0

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
                                    '요원': p['name'], 
                                    '구역명': p['stock_name'], 
                                    '출격일': p['entry_date'],
                                    '출격 당시 주가': f"{format_money(p['entry_price'])}원",
                                    '진입금액': f"{format_money(p['invest_amount'])}원",
                                    '현재 평가금액': f"{format_money(eval_val)}원",
                                    '평가 손익': f"{format_money(eval_profit)}원",
                                    '현재수익률': f"{ret:.2f}%"
                                })

                            tot_ret_pct = (tot_prof / tot_inv * 100) if tot_inv > 0 else 0
                            ac1, ac2, ac3 = st.columns(3)
                            ac1.metric("💰 현장 투입 원금 합계", f"{format_money(tot_inv)}원")
                            ac2.metric("📊 현재 총 평가금액 합계", f"{format_money(tot_eval)}원", delta=f"{tot_ret_pct:.2f}%")
                            ac3.metric("📈 총 평가 손익 합계", f"{format_money(tot_prof)}원")

                            st.write("")
                            st.dataframe(pd.DataFrame(active_table), use_container_width=True, hide_index=True)
                        else:
                            st.success("🎉 현재 현장에 대기 중인 요원이 없습니다! (100% 현금 회수 완료)")

                        st.markdown("---")
                        st.write("### 📜 전체 매매 장부 (최근 순)")
                        if trade_logs:
                            logs_df = pd.DataFrame(list(reversed(trade_logs)))
                            st.dataframe(logs_df, use_container_width=True)

                    # 🌟 자동 채점 및 종합 진단 리포트 (네이티브 컴포넌트 방식)
                    perf_score = min(100, max(50, int(70 + (total_return_pct / 15) + (win_rate - 50))))
                    grade_title = "🏆 S급 (마스터 최우수 작전)" if perf_score >= 90 else ("🔥 A급 (우수 성장 작전)" if perf_score >= 75 else "🛡️ B급 (안정 방어 작전)")
                    
                    missed_cnt = len(missed_opportunities)
                    pros_text = f"총자산이 초기 대비 **{total_return_pct:.1f}%** 폭발적으로 성장했으며, 작전 승률이 **{win_rate:.1f}%**로 매우 탄탄하게 방어 및 수익을 창출했습니다."
                    cons_text = f"백테스트 기간 중 총 **{missed_cnt}회**의 미출격 타점(현금/슬롯 부족)이 발생하여 아쉽게 놓친 기회가 존재합니다." if missed_cnt > 0 else "현금 관리와 슬롯 회전율이 100% 완벽하여 자금 공백이 거의 없었습니다."
                    advice_text = "복리 스케일업 모드를 적극 활용하여 덩치를 키우되, 후반부 거대한 실탄 진입 시 변동성에 대비한 분할 매수 슬롯 관리를 병행하는 것이 핵심입니다."

                    st.markdown("---")
                    st.markdown("### 🎖️ 박가이버 사령관의 종합 진단 및 실전 리포트")
                    
                    col_sc1, col_sc2 = st.columns(2)
                    col_sc1.metric("작전 종합 점수", f"{perf_score}점 / 100점")
                    col_sc2.metric("종합 평가 등급", grade_title)

                    st.success(f"**✨ 1. 잘된 점 (강점):** {pros_text}")
                    if missed_cnt > 0:
                        st.warning(f"**⚠️ 2. 아쉬운 점 (한계):** {cons_text}")
                    else:
                        st.info(f"**⚠️ 2. 아쉬운 점 (한계):** {cons_text}")
                    st.info(f"**🛠️ 3. 향후 개선할 점:** 1회 진입 금액 비율과 최대 슬롯 개수를 본인의 투자 성향(공격형 vs 안정형)에 맞게 미세조정하여 회전율을 극대화하세요.")
                    st.error(f"**💡 종합 실전 어드바이스:** {advice_text}")

                except Exception as e:
                    st.error(f"❌ 분석 중 에러가 발생했습니다: {e}")
