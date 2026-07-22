import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta

# --- 1. 페이지 웹 디자인 세팅 ---
st.set_page_config(page_title="박가이버 작전 통제실", page_icon="🛡️", layout="wide")

st.title("🛡️ 박가이버표 작전 통제실 (실전 백테스터 V3)")
st.caption("위험은 확실히 막고, 진입·익절 타점을 자유롭게 조율하는 최고급 자동 매매 시뮬레이터입니다.")
st.markdown("---")

# --- 2. 왼쪽 사이드바 (조종간 세팅) ---
st.sidebar.header("🎛️ 작전 조종간")

stock_name = st.sidebar.text_input("🏷️ 종목명", value="테크윙")
ticker = st.sidebar.text_input("🎯 종목코드", value="089030.KQ")
invest_amount = st.sidebar.number_input("💰 회당 진입금액(원)", value=500000, step=100000)
max_agents = st.sidebar.slider("⚔️ 최대 요원 수(명)", min_value=1, max_value=10, value=5)
years = st.sidebar.slider("🗓️ 조회 기간(년)", min_value=1, max_value=10, value=5)

# 🛒 진입 조건 조종간
buy_cond_input = st.sidebar.slider(
    "🛒 진입(출격) 기준 (-% 하락 시)", 
    min_value=1, 
    max_value=20, 
    value=5, 
    step=1,
    help="당일 주가가 설정한 % 이상 하락했을 때 신규 요원이 출격합니다."
)

# 🎯 익절 목표 조종간 (추가)
sell_target_input = st.sidebar.slider(
    "🎯 익절(복귀) 목표 (+%)", 
    min_value=1, 
    max_value=30, 
    value=5, 
    step=1,
    help="요원의 수익률이 설정한 % 이상 도달 시 익절하고 복귀합니다."
)

# 🚨 손절 조종간
stop_loss_input = st.sidebar.slider(
    "🚨 강제 청산(손절) 기준 (-%)", 
    min_value=0, 
    max_value=50, 
    value=15, 
    step=5,
    help="0%로 설정하면 손절 없이 목표 수익 달성 시까지 무한 대기합니다."
)

reward_type = st.sidebar.selectbox(
    "🎁 전리품 수령 방식",
    ["전액 현금으로 챙기기", "주식으로 모으기 (공짜 주식)"]
)

run_btn = st.sidebar.button("▶️ 특수 요원 작전 개시!", type="primary")

def format_money(num):
    return f"{int(round(num)):,}"

# --- 3. 작전 시뮬레이션 알고리즘 ---
if run_btn:
    st.info(f"📡 구글 슈퍼컴퓨터가 [{ticker}] {stock_name} 데이터를 분석 중입니다...")
    
    try:
        end_date = datetime.datetime.today()
        start_date = end_date - relativedelta(years=years)

        df = yf.download(ticker, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False, auto_adjust=False)

        if df.empty:
            st.error("❌ 데이터를 찾을 수 없습니다. 종목 코드를 다시 확인해주세요. (예: 코스닥은 .KQ / 코스피는 .KS)")
        else:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df['Daily_Return'] = df['Close'].pct_change() * 100

            # 매매 조건 세팅
            buy_cond = -float(buy_cond_input)
            sell_target = float(sell_target_input)
            stop_loss_limit = -float(stop_loss_input) if stop_loss_input > 0 else None

            total_capital = max_agents * invest_amount  # 기준 총 예산
            initial_price = float(df['Close'].iloc[0])   # 시작 주가

            positions = []
            free_shares = 0
            cash_profit = 0
            total_trades = 0
            success_trades = 0
            stop_loss_trades = 0
            stop_loss_amount = 0
            yearly_stats = {}
            matched_trades = []
            agent_counter = 0

            # 그래프용 일별 자산 기록
            daily_history = []

            for date, row in df.iterrows():
                close = float(row['Close'])
                daily_return = float(row['Daily_Return'])
                year = date.year
                date_str = date.strftime('%Y-%m-%d')

                if pd.isna(daily_return): continue
                if year not in yearly_stats:
                    yearly_stats[year] = {'missions':0, 'shares':0, 'cash':0}

                survived_positions = []
                for pos in positions:
                    ret = ((close - pos['entry_price']) / pos['entry_price']) * 100
                    is_exit = False
                    exit_reason = ""

                    if ret >= sell_target:
                        is_exit = True
                        exit_reason = f"🎯 정상 타격 (+{sell_target_input}% 익절)"
                    elif stop_loss_limit is not None and ret <= stop_loss_limit:
                        is_exit = True
                        exit_reason = f"🚨 -{stop_loss_input}% 강제 청산 (손절)"

                    if is_exit:
                        profit = invest_amount * (ret / 100)
                        
                        if ret >= sell_target:
                            success_trades += 1
                            if reward_type == '주식으로 모으기 (공짜 주식)':
                                buyable = int(profit // close)
                                leftover = profit - (buyable * close)
                            else:
                                buyable = 0
                                leftover = profit
                        else:
                            stop_loss_trades += 1
                            stop_loss_amount += profit
                            buyable = 0
                            leftover = profit

                        free_shares += buyable
                        cash_profit += leftover
                        total_trades += 1

                        yearly_stats[year]['missions'] += 1
                        yearly_stats[year]['shares'] += buyable
                        yearly_stats[year]['cash'] += leftover

                        matched_trades.append({
                            'agent_name': pos['name'],
                            'entry_date': pos['entry_date'],
                            'entry_price': pos['entry_price'],
                            'entry_return': pos['entry_return'],
                            'exit_date': date_str,
                            'exit_price': close,
                            'exit_return': daily_return,
                            'ret': ret,
                            'shares': buyable,
                            'cash': leftover,
                            'exit_reason': exit_reason
                        })
                    else:
                        survived_positions.append(pos)

                positions = survived_positions

                # 🛒 신규 요원 진입
                if daily_return <= buy_cond and len(positions) < max_agents:
                    agent_counter += 1
                    positions.append({
                        'name': f"{agent_counter}호 요원",
                        'entry_price': close,
                        'entry_date': date_str,
                        'entry_return': daily_return
                    })

                # 일별 자산 가치 계산
                active_invested = len(positions) * invest_amount
                cash_balance = total_capital - active_invested + cash_profit
                active_val = sum([invest_amount * (close / p['entry_price']) for p in positions])
                free_val = free_shares * close
                strategy_asset = cash_balance + active_val + free_val
                
                # 단순 보유(Buy & Hold) 자산
                buy_hold_asset = total_capital * (close / initial_price)

                daily_history.append({
                    'Date': date,
                    '박가이버 전략 자산': strategy_asset,
                    '단순 보유(Buy&Hold)': buy_hold_asset
                })

            final_price = float(df['Close'].iloc[-1])
            free_shares_value = free_shares * final_price
            total_invested = len(positions) * invest_amount
            total_current_value = sum([invest_amount * (final_price / p['entry_price']) for p in positions])

            # 총 자산 가치 및 수익률 비교
            final_strategy_asset = total_capital - total_invested + cash_profit + total_current_value + free_shares_value
            strategy_return_pct = ((final_strategy_asset - total_capital) / total_capital) * 100
            buy_hold_return_pct = ((final_price - initial_price) / initial_price) * 100

            # --- 4. 화면 출력 (대시보드) ---
            st.subheader(f"🏆 [{ticker}] {stock_name} 작전 성과표")
            st.caption(f"⚙️ 작전 기준: 당일 **-{buy_cond_input}% 이하** 하락 시 출격 | **+{sell_target_input}%** 익절 | **-{stop_loss_input}%** 손절")
            
            # 상단 성과 지표 (5개 카드)
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("총 작전 종료", f"{total_trades}회")
            col2.metric(f"익절 성공(+{sell_target_input}%)", f"{success_trades}회")
            
            stop_loss_label = f"손절(-{stop_loss_input}%)" if stop_loss_input > 0 else "손절(미사용)"
            col3.metric(stop_loss_label, f"{stop_loss_trades}회", delta=f"{format_money(stop_loss_amount)}원", delta_color="inverse")
            
            if reward_type == '주식으로 모으기 (공짜 주식)':
                col4.metric("📦 획득 공짜 주식", f"{format_money(free_shares)}주", delta=f"가치 {format_money(free_shares_value)}원")
                col5.metric("💵 누적 잔돈 수익", f"{format_money(cash_profit)}원")
            else:
                col4.metric("📦 획득 공짜 주식", "0주 (전액 현금화)")
                col5.metric("💵 최종 누적 현금", f"{format_money(cash_profit)}원")

            st.markdown("---")

            # ⚔️ [신규 기능 1] 단순 보유 vs 박가이버 전략 한판 승부!
            st.write("### ⚔️ 단순 보유(Buy & Hold) vs 박가이버 전략 한판 승부")
            comp_col1, comp_col2, comp_col3 = st.columns(3)
            
            comp_col1.metric(
                "📌 단순 보유(Buy & Hold) 수익률", 
                f"{buy_hold_return_pct:.2f}%", 
                delta=f"최종 자산: {format_money(total_capital * (final_price / initial_price))}원"
            )
            
            diff_pct = strategy_return_pct - buy_hold_return_pct
            comp_col2.metric(
                "🛡️ 박가이버 전략 총 수익률", 
                f"{strategy_return_pct:.2f}%", 
                delta=f"최종 자산: {format_money(final_strategy_asset)}원"
            )
            
            comp_col3.metric(
                "🔥 전략 우위 (초과 수익)", 
                f"{diff_pct:+.2f}%p", 
                delta="전략의 승리!" if diff_pct >= 0 else "보유의 승리",
                delta_color="normal" if diff_pct >= 0 else "inverse"
            )

            # 📈 [신규 기능 2] 누적 자산 성장 곡선 그래프
            st.write("### 📈 누적 자산 성장 추이 그래프")
            chart_df = pd.DataFrame(daily_history).set_index('Date')
            st.line_chart(chart_df, height=350)

            st.markdown("---")

            # 연도별 정산
            st.write("### 🗓️ 연도별 성적표 (연말 정산)")
            yearly_df = pd.DataFrame.from_dict(yearly_stats, orient='index')
            yearly_df.index.name = "연도"
            yearly_df.columns = ["작전 횟수", "획득 주식(주)", "누적 현금(원)"]
            
            yearly_df["작전 횟수"] = yearly_df["작전 횟수"].astype(int)
            yearly_df["획득 주식(주)"] = yearly_df["획득 주식(주)"].apply(lambda x: f"{int(x):,}주")
            yearly_df["누적 현금(원)"] = yearly_df["누적 현금(원)"].apply(lambda x: f"{format_money(x)}원")
            
            st.dataframe(yearly_df, use_container_width=True)

            # ⚔️ 현재 대기 중인 요원 현황
            st.write("### ⚔️ 현재 대기 중인 요원 현황")
            if len(positions) > 0:
                total_diff = total_current_value - total_invested
                total_loss = total_invested - total_current_value
                total_loss_pct = (total_diff / total_invested) * 100 if total_invested > 0 else 0

                if total_diff < 0:
                    st.error(
                        f"📊 **대기 요원 총 평가손실 집계** | "
                        f"전체 투입금: **{format_money(total_invested)}원** − 현재 평가금액: **{format_money(total_current_value)}원** = "
                        f"🚨 **전체 평가손실액: -{format_money(total_loss)}원 ({total_loss_pct:.2f}%)**"
                    )
                else:
                    st.success(
                        f"📊 **대기 요원 총 평가수익 집계** | "
                        f"전체 투입금: **{format_money(total_invested)}원** | 현재 평가금액: **{format_money(total_current_value)}원** | "
                        f"✨ **전체 평가수익액: +{format_money(total_diff)}원 (+{total_loss_pct:.2f}%)**"
                    )

                unreturned_data = []
                for p in positions:
                    ret = ((final_price - p['entry_price']) / p['entry_price']) * 100
                    val = invest_amount * (final_price / p['entry_price'])
                    unreturned_data.append({
                        "요원 이름": p['name'],
                        "출격일": p['entry_date'],
                        "진입 단가": f"{format_money(p['entry_price'])}원",
                        "출격일 등락률": f"{p['entry_return']:.2f}%",
                        "현재 수익률": f"{ret:.2f}%",
                        "현재 평가금": f"{format_money(val)}원"
                    })
                st.table(pd.DataFrame(unreturned_data))
            else:
                st.success("🎉 현재 물려있는 요원이 없습니다! 전원 무사 귀환 완료!")

            # 1대1 완결 장부 및 📥 [신규 기능 3] 엑셀 다운로드
            st.write("### 📜 1대1 출격-복귀 매칭 장부 (최근 작전순)")
            if matched_trades:
                logs = []
                for t in reversed(matched_trades):
                    if t['shares'] > 0:
                        reward_detail = f"{t['shares']}주 + 잔돈 {format_money(t['cash'])}원"
                    else:
                        reward_detail = f"{format_money(t['cash'])}원"

                    logs.append({
                        "구분": t['exit_reason'],
                        "요원": t['agent_name'],
                        "출격일": t['entry_date'],
                        "진입단가": f"{format_money(t['entry_price'])}원 ({t['entry_return']:.2f}%)",
                        "복귀일": t['exit_date'],
                        "청산단가": f"{format_money(t['exit_price'])}원 ({t['exit_return']:.2f}%)",
                        "최종수익률": f"{t['ret']:.1f}%",
                        "정산 내역": reward_detail
                    })
                
                logs_df = pd.DataFrame(logs)
                st.dataframe(logs_df, use_container_width=True)

                # CSV 엑셀 다운로드 버튼 (한글 깨짐 방지 utf-8-sig)
                csv_data = logs_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label=f"📥 [{stock_name}] 백테스트 매매 장부 엑셀(CSV) 다운로드",
                    data=csv_data,
                    file_name=f"parkgyver_{stock_name}_backtest.csv",
                    mime="text/csv"
                )

    except Exception as e:
        st.error(f"❌ 에러가 발생했습니다: {e}")
