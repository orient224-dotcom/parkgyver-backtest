import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta

# --- 1. 페이지 웹 디자인 세팅 ---
st.set_page_config(page_title="박가이버 작전 통제실", page_icon="🛡️", layout="wide")

st.title("🛡️ 박가이버표 작전 통제실 (회전율 극대화 V4)")
st.caption("한정된 예산으로 다중 구역 자금 회전율을 극대화하여 목표를 달성하는 시뮬레이션 통제 시스템입니다.")
st.markdown("---")

# --- 2. 사전 정의 종목 사전 (인기 주도주 20선) ---
MASTER_STOCK_DICT = {
    "테크윙": "089030.KQ",
    "한미반도체": "042700.KS",
    "HPSP": "403870.KQ",
    "이오테크닉스": "039030.KQ",
    "리노공업": "058470.KQ",
    "ISC": "095340.KQ",
    "알테오젠": "196170.KQ",
    "셀트리온": "068270.KS",
    "에코프로비엠": "247540.KQ",
    "에코프로": "086520.KQ",
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "현대차": "005380.KS",
    "기아": "000270.KS",
    "NAVER": "035420.KS",
    "카카오": "035720.KS",
    "주성엔지니어링": "036930.KQ",
    "원익IPS": "240810.KQ",
    "솔브레인": "357780.KQ",
    "LG에너지솔루션": "373220.KS"
}

# --- 3. 왼쪽 사이드바 (조종간 세팅) ---
st.sidebar.header("🎛️ 작전 조종간")

# 작전 구역 커스터마이징 선택창
st.sidebar.subheader("🎯 작전 구역(종목) 설정")
selected_stock_names = st.sidebar.multiselect(
    "감시할 작전 구역 선택 (1개~10개)",
    options=list(MASTER_STOCK_DICT.keys()),
    default=["테크윙", "한미반도체", "HPSP", "이오테크닉스", "리노공업", "ISC", "알테오젠", "셀트리온", "에코프로비엠", "에코프로"],
    help="X 버튼을 눌러 제거하거나 목록에서 클릭하여 추가할 수 있습니다. (최대 10개 권장)"
)

use_custom = st.sidebar.checkbox("✍️ 목록에 없는 종목 직접 입력 추가")
custom_stock_name = ""
custom_stock_ticker = ""
if use_custom:
    custom_stock_name = st.sidebar.text_input("종목명 입력", value="삼성전자")
    custom_stock_ticker = st.sidebar.text_input("종목코드 입력 (예: 005930.KS)", value="005930.KS")

PORTFOLIO_UNIVERSE = {}
for s_name in selected_stock_names:
    PORTFOLIO_UNIVERSE[s_name] = MASTER_STOCK_DICT[s_name]

if use_custom and custom_stock_name and custom_stock_ticker:
    PORTFOLIO_UNIVERSE[custom_stock_name] = custom_stock_ticker

if len(PORTFOLIO_UNIVERSE) == 0:
    st.sidebar.error("⚠️ 적어도 1개 이상의 작전 구역을 선택해 주세요!")

st.sidebar.markdown("---")

total_capital_input = st.sidebar.number_input("🏦 총 작전 예산(원)", value=30000000, step=1000000, help="전체 총 자산 예산 설정")
invest_amount_input = st.sidebar.number_input("💰 회당 진입금액(원)", value=3000000, step=500000, help="특정 구역 상황 발생 시 1회 출격 금액")
max_active_slots = int(total_capital_input // invest_amount_input)
st.sidebar.info(f"💡 동시에 동원 가능한 최대 요원 슬롯: **{max_active_slots}개**")

time_unit = st.sidebar.radio("🗓️ 기간 단위 선택", ["월 단위 (개월)", "년 단위 (년)"], horizontal=True)

if time_unit == "월 단위 (개월)":
    months_input = st.sidebar.slider("백테스트 기간(개월)", min_value=1, max_value=120, value=60, step=1)
    period_label = f"{months_input}개월"
else:
    years_val = st.sidebar.slider("백테스트 기간(년)", min_value=1, max_value=10, value=5, step=1)
    months_input = years_val * 12
    period_label = f"{years_val}년"

# 진입, 익절, 손절 조종간
buy_cond_input = st.sidebar.slider("🛒 진입(출격) 기준 (-% 하락 시)", min_value=1, max_value=20, value=4, step=1)
sell_target_input = st.sidebar.slider("🎯 익절(복귀) 목표 (+%)", min_value=1, max_value=30, value=5, step=1)
stop_loss_input = st.sidebar.slider("🚨 강제 청산(손절) 기준 (-%)", min_value=0, max_value=50, value=15, step=5)

# 🌟 🌟 [신규 기능] 수수료 & 세금 조종간 🌟 🌟
st.sidebar.subheader("💸 실전 거래비용 반영")
use_fee = st.sidebar.checkbox("수수료 및 증권거래세 차감 적용", value=True)
if use_fee:
    broker_fee_pct = st.sidebar.number_input("위탁수수료율 (%) (매수/매도 각각)", value=0.015, format="%.3f") / 100
    tax_pct = st.sidebar.number_input("매도 거래세 (%)", value=0.18, format="%.2f") / 100
else:
    broker_fee_pct = 0.0
    tax_pct = 0.0

reward_type = st.sidebar.selectbox(
    "🎁 전리품 수령 방식",
    ["전액 현금으로 챙기기", "열매로 결실 모으기"]
)

run_btn = st.sidebar.button("🚀 작전 검증 개시!", type="primary")

def format_money(num):
    return f"{int(round(num)):,}"

# 상단 실시간 감시 작전 구역 목록표
st.write(f"### 🛡️ 현재 실시간 감시 중인 작전 구역 ({len(PORTFOLIO_UNIVERSE)}선)")
universe_list = []
for name, code in PORTFOLIO_UNIVERSE.items():
    market_type = "코스닥" if ".KQ" in code else ("코스피" if ".KS" in code else "기타")
    clean_code = code.split('.')[0]
    universe_list.append({
        "구역명(종목)": name,
        "식별 코드": clean_code,
        "소속 시장": market_type,
        "전략적 특성": "실시간 백테스트 대상 구역"
    })

st.dataframe(pd.DataFrame(universe_list), use_container_width=True, hide_index=True)
st.markdown("---")

# --- 4. 멀티 포트폴리오 시뮬레이션 엔진 ---
if run_btn:
    if len(PORTFOLIO_UNIVERSE) == 0:
        st.error("❌ 선택된 작전 구역이 없습니다. 왼쪽 조종간에서 종목을 1개 이상 선택해 주세요.")
    else:
        st.info(f"📡 구글 슈퍼컴퓨터가 {len(PORTFOLIO_UNIVERSE)}개 핵심 작전 구역의 통합 데이터를 분석 중입니다...")
        
        try:
            end_date = datetime.datetime.today()
            start_date = end_date - relativedelta(months=months_input)
            
            tickers = list(PORTFOLIO_UNIVERSE.values())
            raw_df = yf.download(tickers, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)

            if 'Close' in raw_df:
                close_df = raw_df['Close']
            else:
                close_df = raw_df

            if isinstance(close_df, pd.Series):
                close_df = pd.DataFrame({tickers[0]: close_df})

            return_df = close_df.pct_change() * 100

            buy_cond = -float(buy_cond_input)
            sell_target = float(sell_target_input)
            stop_loss_limit = -float(stop_loss_input) if stop_loss_input > 0 else None

            current_cash = float(total_capital_input)
            active_positions = []
            trade_logs = []
            agent_counter = 0

            yearly_stats = {}
            free_shares_dict = {s_name: 0 for s_name in PORTFOLIO_UNIVERSE.keys()}
            
            stock_win_stats = {
                s_name: {'success': 0, 'stop': 0, 'profit_gain': 0, 'loss_cost': 0} 
                for s_name in PORTFOLIO_UNIVERSE.keys()
            }

            total_success = 0
            total_stop_loss = 0
            total_cash_profit = 0
            total_fee_tax_paid = 0  # 🌟 총 지불한 수수료 및 거래세 합계

            max_deployed_count = 0
            peak_deployment_records = []

            for date, row in close_df.iterrows():
                date_str = date.strftime('%Y-%m-%d')
                year = date.year

                if year not in yearly_stats:
                    yearly_stats[year] = {'success': 0, 'stop': 0, 'shares': 0, 'cash': 0}
                
                # A. 기존 출격 포지션 익절/손절 체크
                survived_positions = []
                for pos in active_positions:
                    t_code = pos['ticker']
                    if t_code in row and not pd.isna(row[t_code]):
                        curr_price = float(row[t_code])
                        gross_ret = ((curr_price - pos['entry_price']) / pos['entry_price']) * 100
                        
                        is_exit = False
                        exit_reason = ""

                        if gross_ret >= sell_target:
                            is_exit = True
                            exit_reason = f"🎯 정상 복귀(+{sell_target_input}%)"
                        elif stop_loss_limit is not None and gross_ret <= stop_loss_limit:
                            is_exit = True
                            exit_reason = f"🚨 강제 철수(-{stop_loss_input}%)"

                        if is_exit:
                            # 🌟 수수료 및 거래세 계산
                            sell_gross_val = pos['invest_amount'] * (curr_price / pos['entry_price'])
                            buy_fee = pos['invest_amount'] * broker_fee_pct
                            sell_fee = sell_gross_val * broker_fee_pct
                            sell_tax = sell_gross_val * tax_pct
                            
                            total_trade_cost = buy_fee + sell_fee + sell_tax
                            total_fee_tax_paid += total_trade_cost

                            # 비용을 차감한 순수익
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
                                else:
                                    buyable = 0
                                    leftover = net_profit
                            else:
                                total_stop_loss += 1
                                yearly_stats[year]['stop'] += 1
                                stock_win_stats[s_name]['stop'] += 1
                                stock_win_stats[s_name]['loss_cost'] += net_profit
                                buyable = 0
                                leftover = net_profit

                            free_shares_dict[s_name] += buyable
                            total_cash_profit += leftover
                            
                            returned_cash = pos['invest_amount'] + leftover
                            current_cash += returned_cash

                            yearly_stats[year]['shares'] += buyable
                            yearly_stats[year]['cash'] += leftover

                            log_reward = f"열매 {buyable}개 + 잔돈 {format_money(leftover)}원" if buyable > 0 else f"{format_money(leftover)}원"

                            trade_logs.append({
                                '요원': pos['name'],
                                '작전 구역': pos['stock_name'],
                                '출격일': pos['entry_date'],
                                '진입단가': f"{format_money(pos['entry_price'])}원",
                                '복귀일': date_str,
                                '청산단가': f"{format_money(curr_price)}원",
                                '순수익률(수수료차감)': f"{net_ret:.2f}%",
                                '정산내역': log_reward,
                                '구분': exit_reason
                            })
                        else:
                            survived_positions.append(pos)
                    else:
                        survived_positions.append(pos)
                
                active_positions = survived_positions

                # B. 신규 출격 종목 탐색
                if current_cash >= invest_amount_input and len(active_positions) < max_active_slots:
                    day_returns = return_df.loc[date] if date in return_df.index else None
                    
                    if day_returns is not None:
                        candidates = []
                        for s_name, t_code in PORTFOLIO_UNIVERSE.items():
                            is_already_active = any(p['ticker'] == t_code for p in active_positions)
                            if not is_already_active and t_code in day_returns and not pd.isna(day_returns[t_code]):
                                ret_val = float(day_returns[t_code])
                                if ret_val <= buy_cond:
                                    candidates.append((s_name, t_code, ret_val, float(row[t_code])))

                        candidates.sort(key=lambda x: x[2])

                        for cand in candidates:
                            if current_cash >= invest_amount_input and len(active_positions) < max_active_slots:
                                agent_counter += 1
                                s_name, t_code, ret_val, c_price = cand
                                
                                current_cash -= invest_amount_input
                                active_positions.append({
                                    'name': f"{agent_counter}호 요원",
                                    'stock_name': s_name,
                                    'ticker': t_code,
                                    'entry_price': c_price,
                                    'entry_date': date_str,
                                    'invest_amount': invest_amount_input
                                })

                current_deployed_count = len(active_positions)
                if current_deployed_count > max_deployed_count:
                    max_deployed_count = current_deployed_count

                if current_deployed_count > 0:
                    peak_deployment_records.append({
                        "발생 일자": date_str,
                        "동원 요원 수": current_deployed_count,
                        "자금 소진율": f"{(current_deployed_count / max_active_slots) * 100:.1f}%",
                        "참여 구역 목록": ", ".join([p['stock_name'] for p in active_positions])
                    })

            # 최종 가치 평가
            last_date = close_df.index[-1]
            last_row = close_df.iloc[-1]
            active_eval_value = 0
            active_invest_total = len(active_positions) * invest_amount_input

            for pos in active_positions:
                t_code = pos['ticker']
                if t_code in last_row and not pd.isna(last_row[t_code]):
                    c_price = float(last_row[t_code])
                    active_eval_value += pos['invest_amount'] * (c_price / pos['entry_price'])

            total_free_shares_count = sum(free_shares_dict.values())
            total_free_shares_value = 0
            for s_name, count in free_shares_dict.items():
                if count > 0:
                    t_code = PORTFOLIO_UNIVERSE[s_name]
                    if t_code in last_row and not pd.isna(last_row[t_code]):
                        total_free_shares_value += count * float(last_row[t_code])

            final_total_asset = current_cash + active_eval_value + total_free_shares_value
            total_net_profit = final_total_asset - total_capital_input
            total_return_pct = (total_net_profit / total_capital_input) * 100
            total_trades = total_success + total_stop_loss
            win_rate = (total_success / total_trades * 100) if total_trades > 0 else 0

            # --- 5. 화면 출력 대시보드 ---
            st.subheader("🏆 작전 프로젝트 최종 검증 결과")
            st.caption(f"⚙️ 검증 조건: 선택된 {len(PORTFOLIO_UNIVERSE)}개 작전 구역 | {period_label} 백테스트 | 수수료/거래세 차감 적용 중")

            # 상단 핵심 성과 지표
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("🏁 초기 투입 자금", f"{format_money(total_capital_input)}원")
            col2.metric(f"✨ {period_label} 후 최종 총자산", f"{format_money(final_total_asset)}원")
            col3.metric("📈 총 순수익 (수익률)", f"{format_money(total_net_profit)}원", delta=f"{total_return_pct:.2f}%")
            
            if reward_type == '열매로 결실 모으기':
                col4.metric("💵 현금 잔고 (원금+잔돈)", f"{format_money(current_cash)}원", delta=f"누적 잔돈: +{format_money(total_cash_profit)}원")
                col5.metric("📦 결실 수확량 (열매)", f"{format_money(total_free_shares_count)}개", delta=f"가치: {format_money(total_free_shares_value)}원")
            else:
                col4.metric("💵 최종 현금 잔고", f"{format_money(current_cash)}원", delta=f"누적 현금수익: +{format_money(total_cash_profit)}원")
                col5.metric("🎯 전체 작전 승률", f"{win_rate:.1f}%", delta=f"총 {total_trades}회 중 {total_success}회 승리")

            if use_fee:
                st.info(f"💸 **실전 거래비용 차감 완료:** 백테스트 기간 동안 지불된 누적 증권 수수료 및 거래세 총액은 **-{format_money(total_fee_tax_paid)}원**입니다.")

            st.markdown("---")

            # 승률 + 정밀 손익계산서 합계 통합 센터
            st.write("### 📊 승률 데이터 & 구역별 정밀 손익계산서 (수수료 차감 후)")
            
            v_col1, v_col2 = st.columns([1, 1.2])

            with v_col1:
                st.write("#### 🗓️ 연도별 익절 vs 손절 건수 추이")
                yearly_chart_data = []
                for y, val in yearly_stats.items():
                    yearly_chart_data.append({"연도": str(y), "구분": "🎯 익절 성공", "건수": val['success']})
                    yearly_chart_data.append({"연도": str(y), "구분": "🚨 강제 손절", "건수": val['stop']})
                
                y_df = pd.DataFrame(yearly_chart_data)
                chart_pivot = y_df.pivot(index='연도', columns='구분', values='건수').fillna(0)
                st.bar_chart(chart_pivot)

            with v_col2:
                st.write("#### 🎯 작전 구역(종목)별 승률 & 손익계산 합계 표")
                stock_summary = []
                for s_name, stats in stock_win_stats.items():
                    s_total = stats['success'] + stats['stop']
                    s_win_rate = (stats['success'] / s_total * 100) if s_total > 0 else 0
                    s_net_profit = stats['profit_gain'] + stats['loss_cost']
                    
                    stock_summary.append({
                        "작전 구역": s_name,
                        "총작전": f"{s_total}회",
                        "승률": f"{s_win_rate:.1f}%",
                        "🎯 총 익절 수익금": f"+{format_money(stats['profit_gain'])}원",
                        "🚨 총 손절 손실금": f"{format_money(stats['loss_cost'])}원",
                        "✨ 구역 순손익 합계": f"{format_money(s_net_profit)}원"
                    })
                
                stock_summary_df = pd.DataFrame(stock_summary)
                st.dataframe(stock_summary_df, use_container_width=True, hide_index=True)

            st.markdown("---")

            # 역대 자금 소진 피크 추적
            st.write("### 🚨 역대 자금 소진 피크(최대 동원 요원 수) 분석")
            peak_rate = (max_deployed_count / max_active_slots) * 100
            st.info(f"📊 {period_label} 백테스트 기간 중 **역대 한날 최고 자금 소진 기록:** 총 {max_active_slots}명 슬롯 중 **최대 {max_deployed_count}명 출격 ({peak_rate:.1f}% 소진)**")

            if peak_deployment_records:
                peak_df = pd.DataFrame(peak_deployment_records)
                top_peak_days = peak_df[peak_df['동원 요원 수'] == max_deployed_count].drop_duplicates(subset=['발생 일자'])
                st.warning(f"⚠️ **최대 피크({max_deployed_count}명 출격)를 기록했던 대표 일자 목록:**")
                st.dataframe(top_peak_days, use_container_width=True, hide_index=True)

            st.markdown("---")

            # 연도별 성적표
            st.write("### 🗓️ 연도별 성적표 (연말 정산)")
            yearly_df = pd.DataFrame.from_dict(yearly_stats, orient='index')
            yearly_df.index.name = "연도"
            yearly_df.columns = ["익절 성공(회)", "강제 손절(회)", "획득 열매(개)", "누적 현금 수익(원)"]
            
            yearly_df["익절 성공(회)"] = yearly_df["익절 성공(회)"].astype(int)
            yearly_df["강제 손절(회)"] = yearly_df["강제 손절(회)"].astype(int)
            yearly_df["획득 열매(개)"] = yearly_df["획득 열매(개)"].apply(lambda x: f"{int(x):,}개")
            yearly_df["누적 현금 수익(원)"] = yearly_df["누적 현금 수익(원)"].apply(lambda x: f"{format_money(x)}원")
            
            st.dataframe(yearly_df, use_container_width=True)

            # 열매 보유 현황표
            if reward_type == '열매로 결실 모으기':
                st.write("### 📦 구역별 획득 열매 & 잔돈 정산 현황")
                st.info(f"💡 복귀 시 챙긴 **총 잔돈 현금 수익:** **{format_money(total_cash_profit)}원** (위 현금 잔고에 자동 합산되었습니다.)")
                
                if total_free_shares_count > 0:
                    free_shares_table = []
                    for s_name, count in free_shares_dict.items():
                        if count > 0:
                            t_code = PORTFOLIO_UNIVERSE[s_name]
                            c_price = float(last_row[t_code])
                            free_shares_table.append({
                                "작전 구역": s_name,
                                "획득 결실(열매)": f"{count:,}개",
                                "현재 가치": f"{format_money(c_price)}원",
                                "현재 평가 금액": f"{format_money(count * c_price)}원"
                            })
                    st.table(pd.DataFrame(free_shares_table))

            # ⚔️ 현재 대기 요원
            st.write("### ⚔️ 현재 현장에서 대기 중인 요원 (고립 포지션)")
            active_count = len(active_positions)
            available_slots = max_active_slots - active_count

            if active_count > 0:
                diff_eval = active_eval_value - active_invest_total
                diff_pct = (diff_eval / active_invest_total) * 100 if active_invest_total > 0 else 0

                status_text = f"⚔️ **현재 대기(고립) 요원:** **{active_count}명** / 최대 **{max_active_slots}명** (출격 가능: **{available_slots}명**)"

                if diff_eval < 0:
                    st.error(
                        f"{status_text} | 📊 **대기 요원 총 평가손실** | "
                        f"투입금: **{format_money(active_invest_total)}원** | 현재가치: **{format_money(active_eval_value)}원** | "
                        f"🚨 **평가손실액: {format_money(diff_eval)}원 ({diff_pct:.2f}%)**"
                    )
                else:
                    st.success(
                        f"{status_text} | 📊 **대기 요원 총 평가수익** | "
                        f"투입금: **{format_money(active_invest_total)}원** | 현재가치: **{format_money(active_eval_value)}원** | "
                        f"✨ **평가수익액: +{format_money(diff_eval)}원 (+{diff_pct:.2f}%)**"
                    )

                active_table = []
                for p in active_positions:
                    c_price = float(last_row[p['ticker']])
                    ret = ((c_price - p['entry_price']) / p['entry_price']) * 100
                    active_table.append({
                        '요원 이름': p['name'],
                        '작전 구역': p['stock_name'],
                        '출격일': p['entry_date'],
                        '진입 단가': f"{format_money(p['entry_price'])}원",
                        '현재 수익률': f"{ret:.2f}%",
                        '현재 평가금': f"{format_money(p['invest_amount'] * (c_price / p['entry_price']))}원"
                    })
                st.table(pd.DataFrame(active_table))
            else:
                st.success(f"🎉 현재 물려있는 요원이 전혀 없습니다! (대기 0명 / 출격 가능 {max_active_slots}명) 현금으로 100% 회수된 상태입니다!")

            # 매매 장부 및 엑셀 다운로드
            st.write(f"### 📜 {len(PORTFOLIO_UNIVERSE)}개 구역 통합 출격-복귀 매칭 장부 (최근 순)")
            if trade_logs:
                logs_df = pd.DataFrame(list(reversed(trade_logs)))
                st.dataframe(logs_df, use_container_width=True)

                csv_data = logs_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 작전 프로젝트 전체 매매 장부 엑셀(CSV) 다운로드",
                    data=csv_data,
                    file_name="parkgyver_operation_backtest.csv",
                    mime="text/csv"
                )

        except Exception as e:
            st.error(f"❌ 분석 중 에러가 발생했습니다: {e}")
