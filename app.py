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

# --- 2. 작전 구역 유니버스 (적정 변동성 알짜 10선) ---
PORTFOLIO_UNIVERSE = {
    "테크윙": "089030.KQ",
    "한미반도체": "042700.KS",
    "HPSP": "403870.KQ",
    "이오테크닉스": "039030.KQ",
    "리노공업": "058470.KQ",
    "ISC": "095340.KQ",
    "알테오젠": "196170.KQ",
    "셀트리온": "068270.KS",
    "에코프로비엠": "247540.KQ",
    "에코프로": "086520.KQ"
}

# --- 3. 왼쪽 사이드바 (조종간 세팅) ---
st.sidebar.header("🎛️ 작전 조종간")

total_capital_input = st.sidebar.number_input("🏦 총 작전 예산(원)", value=30000000, step=1000000, help="전체 총 자산 예산 설정")
invest_amount_input = st.sidebar.number_input("💰 회당 진입금액(원)", value=3000000, step=500000, help="특정 구역 상황 발생 시 1회 출격 금액")
max_active_slots = int(total_capital_input // invest_amount_input)
st.sidebar.info(f"💡 동시에 동원 가능한 최대 요원 슬롯: **{max_active_slots}개**")

years_input = st.sidebar.slider("🗓️ 백테스트 검증 기간(년)", min_value=1, max_value=10, value=5)

# 진입, 익절, 손절 조종간
buy_cond_input = st.sidebar.slider("🛒 진입(출격) 기준 (-% 하락 시)", min_value=1, max_value=20, value=4, step=1)
sell_target_input = st.sidebar.slider("🎯 익절(복귀) 목표 (+%)", min_value=1, max_value=30, value=5, step=1)
stop_loss_input = st.sidebar.slider("🚨 강제 청산(손절) 기준 (-%)", min_value=0, max_value=50, value=15, step=5)

# 전리품 수령 방식 스위치 (보안 용어 적용)
reward_type = st.sidebar.selectbox(
    "🎁 전리품 수령 방식",
    ["전액 현금으로 챙기기", "열매로 결실 모으기"]
)

run_btn = st.sidebar.button("🚀 작전 검증 개시!", type="primary")

def format_money(num):
    return f"{int(round(num)):,}"

# 🌟 🌟 [신규 추가] 상단 실시간 감시 작전 구역 목록표 🌟 🌟
st.write("### 🛡️ 현재 실시간 감시 중인 작전 구역 (10선)")
universe_list = []
for name, code in PORTFOLIO_UNIVERSE.items():
    market_type = "코스닥" if ".KQ" in code else "코스피"
    clean_code = code.split('.')[0]
    universe_list.append({
        "구역명(종목)": name,
        "식별 코드": clean_code,
        "소속 시장": market_type,
        "전략적 특성": "주도 테마 / 고회전 알짜 구역"
    })

# 2줄 카드로 깔끔하게 표출
st.dataframe(pd.DataFrame(universe_list), use_container_width=True, hide_index=True)
st.markdown("---")

# --- 4. 멀티 포트폴리오 시뮬레이션 엔진 ---
if run_btn:
    st.info("📡 구글 슈퍼컴퓨터가 10개 핵심 작전 구역의 통합 데이터를 분석 중입니다...")
    
    try:
        end_date = datetime.datetime.today()
        start_date = end_date - relativedelta(years=years_input)
        
        tickers = list(PORTFOLIO_UNIVERSE.values())
        raw_df = yf.download(tickers, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)

        if 'Close' in raw_df:
            close_df = raw_df['Close']
        else:
            close_df = raw_df

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

        total_success = 0
        total_stop_loss = 0
        total_cash_profit = 0

        for date, row in close_df.iterrows():
            date_str = date.strftime('%Y-%m-%d')
            year = date.year

            if year not in yearly_stats:
                yearly_stats[year] = {'missions': 0, 'shares': 0, 'cash': 0}
            
            # A. 기존 출격 포지션 익절/손절 체크
            survived_positions = []
            for pos in active_positions:
                t_code = pos['ticker']
                if t_code in row and not pd.isna(row[t_code]):
                    curr_price = float(row[t_code])
                    ret = ((curr_price - pos['entry_price']) / pos['entry_price']) * 100
                    
                    is_exit = False
                    exit_reason = ""

                    if ret >= sell_target:
                        is_exit = True
                        exit_reason = f"🎯 정상 복귀(+{sell_target_input}%)"
                    elif stop_loss_limit is not None and ret <= stop_loss_limit:
                        is_exit = True
                        exit_reason = f"🚨 강제 철수(-{stop_loss_input}%)"

                    if is_exit:
                        profit = pos['invest_amount'] * (ret / 100)
                        
                        if ret >= sell_target:
                            total_success += 1
                            if reward_type == '열매로 결실 모으기':
                                buyable = int(profit // curr_price)
                                leftover = profit - (buyable * curr_price)
                            else:
                                buyable = 0
                                leftover = profit
                        else:
                            total_stop_loss += 1
                            buyable = 0
                            leftover = profit

                        free_shares_dict[pos['stock_name']] += buyable
                        total_cash_profit += leftover
                        
                        returned_cash = pos['invest_amount'] + leftover
                        current_cash += returned_cash

                        # 연도별 통계 집계
                        yearly_stats[year]['missions'] += 1
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
                            '수익률': f"{ret:.2f}%",
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

        # 모아둔 열매(주식)의 현재 가치 평가
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

        # --- 5. 화면 출력 대시보드 ---
        st.subheader("🏆 작전 프로젝트 최종 검증 결과")
        st.caption(f"⚙️ 검증 조건: 주요 10개 작전 구역 | {years_input}년 백테스트 | 당일 **-{buy_cond_input}% 이하** 진입 | **+{sell_target_input}%** 복귀 | **-{stop_loss_input}%** 철수")

        # 상단 핵심 성과 지표
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("🏁 초기 투입 자금", f"{format_money(total_capital_input)}원")
        col2.metric(f"✨ {years_input}년 후 최종 총자산", f"{format_money(final_total_asset)}원")
        col3.metric("📈 총 순수익 (수익률)", f"{format_money(total_net_profit)}원", delta=f"{total_return_pct:.2f}%")
        
        if reward_type == '열매로 결실 모으기':
            col4.metric("💵 현금 잔고 (원금+잔돈)", f"{format_money(current_cash)}원", delta=f"누적 잔돈: +{format_money(total_cash_profit)}원")
            col5.metric("📦 결실 수확량 (열매)", f"{format_money(total_free_shares_count)}개", delta=f"가치: {format_money(total_free_shares_value)}원")
        else:
            col4.metric("💵 최종 현금 잔고", f"{format_money(current_cash)}원", delta=f"누적 현금수익: +{format_money(total_cash_profit)}원")
            col5.metric("🔄 작전 성공률", f"{total_trades}회 중 {total_success}회", delta=f"승률 {(total_success/total_trades*100 if total_trades>0 else 0):.1f}%")

        st.markdown("---")

        # 연도별 성적표 (연말 정산)
        st.write("### 🗓️ 연도별 성적표 (연말 정산)")
        yearly_df = pd.DataFrame.from_dict(yearly_stats, orient='index')
        yearly_df.index.name = "연도"
        yearly_df.columns = ["작전 종료 횟수", "획득 열매(개)", "누적 현금 수익(원)"]
        
        yearly_df["작전 종료 횟수"] = yearly_df["작전 종료 횟수"].astype(int)
        yearly_df["획득 열매(개)"] = yearly_df["획득 열매(개)"].apply(lambda x: f"{int(x):,}개")
        yearly_df["누적 현금 수익(원)"] = yearly_df["누적 현금 수익(원)"].apply(lambda x: f"{format_money(x)}원")
        
        st.dataframe(yearly_df, use_container_width=True)

        # 열매(주식) 보유 현황표
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

        # ⚔️ 현재 현장에서 대기 중인 요원
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
        st.write("### 📜 10개 구역 통합 출격-복귀 매칭 장부 (최근 순)")
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
