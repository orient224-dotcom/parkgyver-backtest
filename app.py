import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
from dateutil.relativedelta import relativedelta
import plotly.express as px
import plotly.graph_objects as go

# --- 1. 페이지 웹 디자인 및 스타일링 (커스텀 CSS) ---
st.set_page_config(page_title="박가이버 통합 작전 사령부 V6 Pro", page_icon="🛡️", layout="wide")

# 고급 스튜디엄 느낌의 CSS 스타일링
st.markdown("""
<style>
    /* 메인 배경 및 폰트 레이아웃 */
    .main { background-color: #f8f9fa; }
    
    /* 카드형 컨테이너 디자인 */
    .stMetric {
        background-color: #ffffff;
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
    }
    
    /* 메인 타이틀 커스텀 */
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1e293b;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }
    
    /* 강조 안내 상자 */
    .highlight-card {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border-left: 5px solid #3b82f6;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 통합 종목 데이터베이스 ---
SECTOR_DATABASE = {
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

MASTER_STOCK_DICT = {}
for sector, stocks in SECTOR_DATABASE.items():
    for name, code in stocks.items():
        MASTER_STOCK_DICT[name] = code

# 세션 상태 기본값 초기화
if "selected_stocks" not in st.session_state:
    st.session_state["selected_stocks"] = ["테크윙", "한미반도체", "HPSP", "알테오젠", "에코프로비엠"]

def format_money(num):
    return f"{int(round(num)):,}"

# --- 3. 사이드바 메인 조종간 ---
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
    st.markdown('<div class="main-header">🔎 작전 구역(섹터/종목) 탐색기</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">관심 있는 테마별 알짜 종목을 자유롭게 둘러보고 담아서 [작전 통제실]로 한 번에 전송하세요.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])
    with col1:
        selected_sector = st.selectbox("🎯 탐색할 섹터/테마 선택", list(SECTOR_DATABASE.keys()))
    with col2:
        sector_stocks = list(SECTOR_DATABASE[selected_sector].keys())
        st.write(f"▼ **[{selected_sector}] 감시 종목군**")
        st.info(", ".join(sector_stocks))

    st.markdown("---")
    st.subheader("🛒 백테스트 바구니 담기")
    
    basket = st.multiselect(
        "검증을 진행할 종목들을 선택해 주세요 (1개~10개 권장):",
        options=list(MASTER_STOCK_DICT.keys()),
        default=st.session_state["selected_stocks"]
    )

    if basket:
        summary_data = []
        for name in basket:
            code = MASTER_STOCK_DICT[name]
            market_type = "코스닥" if ".KQ" in code else ("코스피" if ".KS" in code else "기타")
            summary_data.append({"종목명": name, "식별 코드": code.split('.')[0], "소속 시장": market_type})
        
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
        st.markdown("---")
        
        if st.button("🚀 선택한 종목들로 [작전 통제실 백테스트] 설정!", type="primary"):
            st.session_state["selected_stocks"] = basket
            st.success(f"🎉 총 {len(basket)}개 종목이 사령부로 성공적으로 설정되었습니다!")
            st.info("👈 왼쪽 사이드바 메뉴에서 [🛡️ 2. 실전 작전 통제실 (백테스트)]를 눌러 이동하세요!")

# =====================================================================
# 🛡️ 모드 2: 실전 작전 통제실 (백테스트 대시보드 V6)
# =====================================================================
else:
    st.markdown('<div class="main-header">🛡️ 박가이버표 실전 작전 통제실 (V6 Pro)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">1,000만 원 원금 보호 및 스노우볼 자산 증식 알고리즘 시뮬레이터입니다.</div>', unsafe_allow_html=True)

    # 🎛️ 사이드바 전략 조종간
    st.sidebar.subheader("⚙️ 빠른 전략 프리셋")
    preset_col1, preset_col2 = st.sidebar.columns(2)
    
    # 전략 원클릭 자동 세팅 기능
    buy_preset = 4
    sell_preset = 5
    if preset_col1.button("⚡ 적극 공격형"):
        buy_preset = 3
        sell_preset = 7
        st.sidebar.toast("적극 공격형 (-3% 진입 / +7% 익절) 설정 완료!")
    if preset_col2.button("🛡️ 안정 스노우볼"):
        buy_preset = 5
        sell_preset = 5
        st.sidebar.toast("안정 스노우볼 (-5% 진입 / +5% 익절) 설정 완료!")

    st.sidebar.subheader("🎯 감시 작전 구역 선택")
    selected_stock_names = st.sidebar.multiselect(
        "감시 종목 리스트",
        options=list(MASTER_STOCK_DICT.keys()),
        default=st.session_state["selected_stocks"]
    )

    use_custom = st.sidebar.checkbox("✍️ 종목 직접 추가")
    custom_stock_name, custom_stock_ticker = "", ""
    if use_custom:
        custom_stock_name = st.sidebar.text_input("종목명", value="삼성전자")
        custom_stock_ticker = st.sidebar.text_input("종목코드", value="005930.KS")

    PORTFOLIO_UNIVERSE = {s_name: MASTER_STOCK_DICT[s_name] for s_name in selected_stock_names}
    if use_custom and custom_stock_name and custom_stock_ticker:
        PORTFOLIO_UNIVERSE[custom_stock_name] = custom_stock_ticker

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

    reward_type = st.sidebar.selectbox("🎁 전리품 수령 방식", ["전액 현금으로 챙기기", "열매로 결실 모으기"])
    run_btn = st.sidebar.button("🚀 1,000만 원 작전 검증 개시!", type="primary")

    # 상단 요약 감시판
    st.write(f"### 🛡️ 감시 구역 요약 ({len(PORTFOLIO_UNIVERSE)}개 종목)")
    universe_list = []
    for name, code in PORTFOLIO_UNIVERSE.items():
        market_type = "코스닥" if ".KQ" in code else ("코스피" if ".KS" in code else "기타")
        universe_list.append({"구역명": name, "티커": code.split('.')[0], "시장": market_type, "상태": "실시간 감시 중"})
    st.dataframe(pd.DataFrame(universe_list), use_container_width=True, hide_index=True)
    st.markdown("---")

    # 백테스트 엔진 실행
    if run_btn:
        if len(PORTFOLIO_UNIVERSE) == 0:
            st.error("❌ 선택된 종목이 없습니다. 1개 이상 선택해 주세요.")
        else:
            with st.spinner("📡 슈퍼컴퓨터가 과거 파동 데이터를 분석 중입니다..."):
                try:
                    end_date = datetime.datetime.today()
                    start_date = end_date - relativedelta(months=months_input)
                    tickers = list(PORTFOLIO_UNIVERSE.values())
                    raw_df = yf.download(tickers, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)

                    close_df = raw_df['Close'] if 'Close' in raw_df else raw_df
                    if isinstance(close_df, pd.Series):
                        close_df = pd.DataFrame({tickers[0]: close_df})

                    return_df = close_df.pct_change() * 100
                    buy_cond = -float(buy_cond_input)
                    sell_target = float(sell_target_input)
                    stop_loss_limit = -float(stop_loss_input) if stop_loss_input > 0 else None

                    current_cash = float(total_capital_input)
                    active_positions = []
                    trade_logs = []
                    daily_returns_history = []
                    asset_history = [] # 차트용 타임라인 기록
                    agent_counter = 0

                    yearly_stats = {}
                    free_shares_dict = {s_name: 0 for s_name in PORTFOLIO_UNIVERSE.keys()}
                    stock_win_stats = {s_name: {'success': 0, 'stop': 0, 'profit_gain': 0, 'loss_cost': 0} for s_name in PORTFOLIO_UNIVERSE.keys()}

                    total_success, total_stop_loss, total_cash_profit, total_fee_tax_paid = 0, 0, 0, 0
                    global_max_deployed = 0
                    daily_deployment_snapshots = []

                    for date, row in close_df.iterrows():
                        date_str = date.strftime('%Y-%m-%d')
                        year = date.year
                        if year not in yearly_stats:
                            yearly_stats[year] = {'success': 0, 'stop': 0, 'shares': 0, 'cash': 0}
                        
                        # 청산 검사
                        survived_positions = []
                        for pos in active_positions:
                            t_code = pos['ticker']
                            if t_code in row and not pd.isna(row[t_code]):
                                curr_price = float(row[t_code])
                                gross_ret = ((curr_price - pos['entry_price']) / pos['entry_price']) * 100
                                is_exit = False
                                exit_reason = ""

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
                                        buyable = int(max(0, net_profit) // curr_price) if reward_type == '열매로 결실 모으기' else 0
                                        leftover = net_profit - (buyable * curr_price) if reward_type == '열매로 결실 모으기' else net_profit
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
                                    daily_returns_history.append(net_ret)

                                    log_reward = f"열매 {buyable}개 + 잔돈 {format_money(leftover)}원" if buyable > 0 else f"{format_money(leftover)}원"
                                    trade_logs.append({
                                        '요원': pos['name'], '작전 구역': pos['stock_name'], '출격일': pos['entry_date'],
                                        '진입단가': f"{format_money(pos['entry_price'])}원", '복귀일': date_str,
                                        '청산단가': f"{format_money(curr_price)}원", '순수익률': f"{net_ret:.2f}%",
                                        '정산내역': log_reward, '구분': exit_reason
                                    })
                                else:
                                    survived_positions.append(pos)
                            else:
                                survived_positions.append(pos)
                        
                        active_positions = survived_positions

                        # 신규 진입 검사
                        remaining_slots = max_active_slots - len(active_positions)
                        dynamic_invest_amount = max(float(invest_amount_input), current_cash / remaining_slots) if (use_compounding and remaining_slots > 0) else float(invest_amount_input)

                        if current_cash > 0 and len(active_positions) < max_active_slots:
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
                                    if actual_invest >= 500000 and len(active_positions) < max_active_slots:
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

                        # 차트용 일별 총 자산 평가액 추적
                        eval_pos = sum([p['invest_amount'] * (float(row[p['ticker']]) / p['entry_price']) for p in active_positions if p['ticker'] in row and not pd.isna(row[p['ticker']])])
                        asset_history.append({"Date": date, "Total_Asset": current_cash + eval_pos})

                    # 최종 결과 정산
                    last_row = close_df.iloc[-1]
                    active_eval_value = sum([p['invest_amount'] * (float(last_row[p['ticker']]) / p['entry_price']) for p in active_positions if p['ticker'] in last_row and not pd.isna(last_row[p['ticker']])])
                    total_free_shares_count = sum(free_shares_dict.values())
                    total_free_shares_value = sum([count * float(last_row[PORTFOLIO_UNIVERSE[s_name]]) for s_name, count in free_shares_dict.items() if count > 0 and PORTFOLIO_UNIVERSE[s_name] in last_row and not pd.isna(last_row[PORTFOLIO_UNIVERSE[s_name]])])

                    final_total_asset = current_cash + active_eval_value + total_free_shares_value
                    total_net_profit = final_total_asset - total_capital_input
                    total_return_pct = (total_net_profit / total_capital_input) * 100
                    total_trades = total_success + total_stop_loss
                    win_rate = (total_success / total_trades * 100) if total_trades > 0 else 0

                    # =========================================================
                    # 🎨 고도화 대시보드 출력 구역 (탭 기반 레이아웃)
                    # =========================================================
                    st.subheader("🏆 백테스트 최종 성과 지표")
                    
                    # 5대 핵심 지표 카드
                    m1, m2, m3, m4, m5 = st.columns(5)
                    m1.metric("🏁 원금 예산", f"{format_money(total_capital_input)}원")
                    m2.metric(f"✨ {period_label} 후 총자산", f"{format_money(final_total_asset)}원")
                    m3.metric("📈 총 순수익금", f"{format_money(total_net_profit)}원", delta=f"{total_return_pct:.2f}%")
                    
                    if reward_type == '열매로 결실 모으기':
                        m4.metric("💵 가용 현금", f"{format_money(current_cash)}원", delta=f"잔돈: +{format_money(total_cash_profit)}원")
                        m5.metric("📦 공짜 열매", f"{total_free_shares_count:,}주", delta=f"가치: {format_money(total_free_shares_value)}원")
                    else:
                        m4.metric("💵 최종 현금", f"{format_money(current_cash)}원", delta=f"수익금: +{format_money(total_cash_profit)}원")
                        m5.metric("🎯 작전 승률", f"{win_rate:.1f}%", delta=f"{total_trades}전 {total_success}승")

                    if use_fee:
                        st.caption(f"💸 **실전 거래비용 정산 완료:** 누적 수수료 및 거래세 -{format_money(total_fee_tax_paid)}원 이미 차감됨")

                    st.markdown("---")

                    # 🌟 4대 인터랙티브 탭 메뉴
                    tab1, tab2, tab3, tab4 = st.tabs([
                        "📊 1. 누적 자산 성장 곡선", 
                        "🔍 2. 자금 회전율 & 피크 진단", 
                        "📈 3. 종목/연도별 손익분석", 
                        "📜 4. 현장 대기요원 & 매매장부"
                    ])

                    # --- TAB 1: 누적 자산 성장 곡선 (Plotly 차트) ---
                    with tab1:
                        st.write("### 📈 백테스트 기간 자산 증식 추이 (Plotly 차트)")
                        asset_df = pd.DataFrame(asset_history)
                        
                        # Plotly 라인 차트 생성
                        fig_asset = px.line(
                            asset_df, x="Date", y="Total_Asset",
                            title=f"1,000만 원 자본금의 {period_label} 성취 곡선",
                            labels={"Total_Asset": "총 자산 가치 (원)", "Date": "날짜"}
                        )
                        fig_asset.add_hline(y=total_capital_input, line_dash="dash", line_color="red", annotation_text="원금 (1,000만 원)")
                        fig_asset.update_traces(line_color="#2563eb", line_width=2.5)
                        fig_asset.update_layout(hovermode="x unified", template="plotly_white")
                        st.plotly_chart(fig_asset, use_container_width=True)

                        # 몬테카를로 시뮬레이터
                        st.write("#### 🎲 몬테카를로 미래 5년 확률 시뮬레이터 (1,000회)")
                        if len(daily_returns_history) > 5:
                            mean_ret, std_ret = np.mean(daily_returns_history)/100, np.std(daily_returns_history)/100
                            mc_results = [total_capital_input * np.prod(1 + np.random.normal(mean_ret, std_ret, 80)) for _ in range(1000)]
                            mc_results = np.array(mc_results)
                            
                            mc1, mc2, mc3, mc4 = st.columns(4)
                            mc1.metric("🌧️ 최악 (하위 10%)", f"{format_money(np.percentile(mc_results, 10))}원")
                            mc2.metric("🌤️ 평균 (중위 50%)", f"{format_money(np.percentile(mc_results, 50))}원")
                            mc3.metric("☀️ 최선 (상위 10%)", f"{format_money(np.percentile(mc_results, 90))}원")
                            target_prob = (np.sum(mc_results >= (total_capital_input * 3)) / 1000) * 100
                            mc4.metric("🔥 3배(3,000만 원) 달성 확률", f"{target_prob:.1f}%")

                    # --- TAB 2: 자금 회전율 & 피크 진단 ---
                    with tab2:
                        st.write("### 🔍 회전율 극대화 리포트")
                        st.warning(f"📊 {period_label} 기간 중 역사적 절대 최고 동시 출격 수: **총 {global_max_deployed}개 종목** (전체 슬롯: {max_active_slots}개)")
                        
                        if daily_deployment_snapshots:
                            snap_df = pd.DataFrame(daily_deployment_snapshots)
                            peak_df = snap_df[snap_df['동시 출격 수'] == global_max_deployed].drop_duplicates(subset=['발생 일자'])
                            st.write(f"▼ **역대 최고 자금 몰림({global_max_deployed}개 출격)이 발생했던 날짜와 종목:**")
                            st.dataframe(peak_df, use_container_width=True, hide_index=True)

                            if global_max_deployed < max_active_slots:
                                st.success(f"💡 **[자금 최적화 팁]:** 최대 {global_max_deployed}개까지만 동시 출격했으므로, 슬롯 수를 {global_max_deployed}개로 맞추고 회당 진입금을 늘리면 회전율이 대폭 상승합니다!")

                    # --- TAB 3: 종목/연도별 손익 분석 ---
                    with tab3:
                        st.write("### 📊 종목 및 연도별 정밀 성적표")
                        c_col1, c_col2 = st.columns([1, 1.2])

                        with c_col1:
                            st.write("#### 🗓️ 연도별 익절 vs 손절 건수")
                            yearly_chart_data = []
                            for y, val in yearly_stats.items():
                                yearly_chart_data.append({"연도": str(y), "구분": "🎯 익절", "건수": val['success']})
                                yearly_chart_data.append({"연도": str(y), "구분": "🚨 손절", "건수": val['stop']})
                            y_df = pd.DataFrame(yearly_chart_data)
                            
                            # Plotly 바 차트
                            fig_bar = px.bar(y_df, x="연도", y="건수", color="구분", barmode="group", color_discrete_map={"🎯 익절": "#22c55e", "🚨 손절": "#ef4444"})
                            st.plotly_chart(fig_bar, use_container_width=True)

                        with c_col2:
                            st.write("#### 🎯 종목별 손익 합계 표")
                            stock_summary = []
                            for s_name, stats in stock_win_stats.items():
                                s_total = stats['success'] + stats['stop']
                                s_win_rate = (stats['success'] / s_total * 100) if s_total > 0 else 0
                                s_net_profit = stats['profit_gain'] + stats['loss_cost']
                                stock_summary.append({
                                    "작전 구역": s_name, "총작전": f"{s_total}회", "승률": f"{s_win_rate:.1f}%",
                                    "🎯 총 익절금": f"+{format_money(stats['profit_gain'])}원",
                                    "🚨 총 손절금": f"{format_money(stats['loss_cost'])}원",
                                    "✨ 순손익": f"{format_money(s_net_profit)}원"
                                })
                            st.dataframe(pd.DataFrame(stock_summary), use_container_width=True, hide_index=True)

                        st.markdown("---")
                        st.write("#### 🗓️ 연도별 정산 종합표")
                        yearly_df = pd.DataFrame.from_dict(yearly_stats, orient='index')
                        yearly_df.index.name = "연도"
                        yearly_df.columns = ["익절 성공(회)", "강제 손절(회)", "획득 열매(개)", "누적 현금 수익(원)"]
                        yearly_df["획득 열매(개)"] = yearly_df["획득 열매(개)"].apply(lambda x: f"{int(x):,}개")
                        yearly_df["누적 현금 수익(원)"] = yearly_df["누적 현금 수익(원)"].apply(lambda x: f"{format_money(x)}원")
                        st.dataframe(yearly_df, use_container_width=True)

                    # --- TAB 4: 현장 대기요원 & 매매장부 ---
                    with tab4:
                        st.write("### ⚔️ 현재 현장 대기 요원 (고립 포지션)")
                        active_count = len(active_positions)
                        if active_count > 0:
                            active_table = []
                            for p in active_positions:
                                c_price = float(last_row[p['ticker']])
                                ret = ((c_price - p['entry_price']) / p['entry_price']) * 100
                                active_table.append({
                                    '요원': p['name'], '구역명': p['stock_name'], '출격일': p['entry_date'],
                                    '진입단가': f"{format_money(p['entry_price'])}원", '현재수익률': f"{ret:.2f}%",
                                    '평가금액': f"{format_money(p['invest_amount'] * (c_price / p['entry_price']))}원"
                                })
                            st.table(pd.DataFrame(active_table))
                        else:
                            st.success("🎉 현재 현장에 대기 중인 요원이 없습니다! (100% 현금 회수 완료)")

                        st.markdown("---")
                        st.write("### 📜 전체 매매 장부 (최근 순)")
                        if trade_logs:
                            logs_df = pd.DataFrame(list(reversed(trade_logs)))
                            st.dataframe(logs_df, use_container_width=True)
                            csv_data = logs_df.to_csv(index=False).encode('utf-8-sig')
                            st.download_button("📥 전체 매매 장부 엑셀(CSV) 다운로드", data=csv_data, file_name="parkgyver_backtest.csv", mime="text/csv")

                except Exception as e:
                    st.error(f"❌ 분석 중 에러가 발생했습니다: {e}")
