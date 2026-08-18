import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import datetime
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt
import os
import io
import warnings

warnings.filterwarnings('ignore')

# --- 1. 페이지 기본 설정 ---
st.set_page_config(page_title="박가이버 사령부 V10.36", layout="wide", page_icon="🎛️")

def format_money(num):
    try:
        return f"{int(round(float(num))):,}"
    except:
        return str(num)

# --- 2. 사이드바 조종간 ---
st.sidebar.title("🎛️ 박가이버 사령부 V10.36")
st.sidebar.caption("은퇴 과수원 에디션 - 제미나이 정예 발굴 편대 탑재")

# 🎯 사령부 정예 종목 데이터베이스 (기본축 + 신규 발굴 + 관심종목)
stock_database = {
    # 🏛️ 핵심 기둥 (기본축)
    "삼성전자 (005930)": "005930",
    
    # 🚀 신규 발굴 정예 편대 (고마진/알짜 턴어라운드)
    "실리콘투 (257720)": "257720",
    "리노공업 (058470)": "058470",
    "HD현대일렉트릭 (267260)": "267260",
    "DN오토모티브 (007340)": "007340",
    
    # 📋 관심 및 기존 작전 종목군
    "와이지원 (019210)": "019210",
    "테크윙 (089030)": "089030",
    "피에스케이 (319660)": "319660",
    "제주반도체 (080220)": "080220",
    "SK하이닉스 (000660)": "000660",
    "두산에너빌리티 (034020)": "034020",
    "원익QNC (074600)": "074600",
    "한미반도체 (042700)": "042700",
    "주성엔지니어링 (036930)": "036930",
    "LG에너지솔루션 (373220)": "373220",
    "셀트리온 (068270)": "068270",
    "클리오 (237880)": "237880"
}

# 🛡️ 코스피 소속 종목 코드 (지수 폭락 감시 락 연동용)
KS_CODES = ['005930', '034020', '000660', '373220', '068270', '267260', '007340']

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 종목 간편 검색 및 선택")

# 기본 세팅: 삼성전자 중심축 + 신규 발굴 정예 4종목
default_selected = [
    "삼성전자 (005930)", 
    "실리콘투 (257720)", 
    "리노공업 (058470)", 
    "HD현대일렉트릭 (267260)", 
    "DN오토모티브 (007340)"
]

selected_stocks = st.sidebar.multiselect(
    "클릭하거나 검색해서 종목을 담으세요:",
    options=list(stock_database.keys()),
    default=default_selected
)

tickers_list = []
names_list = []

for s in selected_stocks:
    code = stock_database[s]
    name = s.split(" (")[0]
    tickers_list.append(code)
    names_list.append(name)

with st.sidebar.expander("➕ 리스트에 없는 종목 직접 추가하기"):
    custom_input = st.text_input("종목코드 6자리 입력 (예: 000660):", value="")
    custom_name = st.text_input("종목이름 입력 (예: SK하이닉스):", value="")
    if custom_input and custom_name:
        if custom_input.strip() not in tickers_list:
            tickers_list.append(custom_input.strip())
            names_list.append(custom_name.strip())

raw_tickers = ", ".join(tickers_list)
raw_names = ", ".join(names_list)

st.sidebar.markdown("---")
strategy_option = st.sidebar.selectbox(
    "📊 작전전략 선택:",
    [
        ('🌳 3단 밸런스 과수원 전략 (60%재투자/20%현금/20%코어)', '3tier'),
        ('🚀 풀 현금 복리 재투자 전략 (100% 컴파운딩)', 'full_cash'),
        ('⚖️ 균등 배분 고정 전략 (No Reinvest / Buy&Hold 1/N)', 'equal_alloc')
    ],
    format_func=lambda x: x[0]
)
selected_strategy = strategy_option[1]

buy_fee_val = st.sidebar.number_input("📉 매수수수료(%):", value=0.015, step=0.005, format="%.3f")
sell_tax_val = st.sidebar.number_input("📈 매도세금+수수료(%):", value=0.20, step=0.01, format="%.2f")
total_capital = st.sidebar.number_input("💰 총 씨드머니(원):", value=10000000, step=1000000)
max_agents = st.sidebar.number_input("⚔️ 종목당 최대 요원 수:", value=1, min_value=1, max_value=10)
years = st.sidebar.number_input("🗓️ 백테스트 조회기간(년):", value=1, min_value=1, max_value=10)

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ 리스크 제어 3중 안전장치")

# 시장 지수 폭락 감시 락 옵션
use_market_ma20_filter = st.sidebar.checkbox("🚨 지수 폭락 감시 락 (KOSPI/KQ 20일선 붕괴시 매수금지)", value=True)
use_ma20_filter = st.sidebar.checkbox("🛡️ 개별주 20일선 아래 매수 금지 (추세 필터)", value=True)

# 비상 탈출 옵션
emergency_cut_active = st.sidebar.checkbox("🚨 비상 탈출 손절(Emergency Cut) 가동", value=True)
emergency_cut_pct = st.sidebar.number_input("비상 탈출 손실 기준선 (%)", value=15.0, step=5.0, min_value=5.0, max_value=50.0)

run_btn = st.sidebar.button("▶️ 박가이버 사령부 V10.36 작전 개시!", type="primary")

# --- 🚨 오후 3:20 PM 실전 신호등 모듈 ---
st.markdown("<div style='background:#154360;color:white;padding:12px;border-radius:6px;margin-bottom:12px;'><h3 style='margin:0;font-size:16px;'>🚨 [오후 3:20 PM 실전 작전 지시서] 실시간 신호등 통제실</h3></div>", unsafe_allow_html=True)

live_col1, live_col2 = st.columns([1, 3])

with live_col1:
    scan_live_btn = st.button("📡 [3시 20분] 실시간 시장 스캔 실행", type="primary", use_container_width=True)

with live_col2:
    st.caption("💡 매일 오후 3시 20분 동시호가 시작 전 클릭하시면, 오늘의 당일 등락률을 정밀 계산하여 즉시 실행할 매수/매도 주문 지시서를 생성합니다.")

if scan_live_btn:
    with st.spinner("🔍 실시간 시세 데이터 및 요원 파견 조건을 정밀 분석 중입니다..."):
        buy_orders = []
        sell_orders = []
        hold_stocks = []
        
        start_2mo = (datetime.datetime.today() - relativedelta(months=2)).strftime('%Y-%m-%d')

        try:
            k_hist = fdr.DataReader('KS11', start_2mo)
            kd_hist = fdr.DataReader('KQ11', start_2mo)
            k_hist['MA20'] = k_hist['Close'].rolling(20).mean()
            kd_hist['MA20'] = kd_hist['Close'].rolling(20).mean()
            
            k_curr = float(k_hist['Close'].iloc[-1])
            k_ma20 = float(k_hist['MA20'].iloc[-1])
            kd_curr = float(kd_hist['Close'].iloc[-1])
            kd_ma20 = float(kd_hist['MA20'].iloc[-1])
            
            is_ks_safe = (k_curr >= k_ma20)
            is_kd_safe = (kd_curr >= kd_ma20)
        except:
            is_ks_safe = True
            is_kd_safe = True

        if use_market_ma20_filter:
            warn_msg = []
            if not is_ks_safe: warn_msg.append("KOSPI 20일선 붕괴")
            if not is_kd_safe: warn_msg.append("KOSDAQ 20일선 붕괴")
            if warn_msg:
                st.warning(f"🚨 **[기상 특보] 지수 폭락 경보 발령 중! ({', '.join(warn_msg)})** - 해당 시장 종목의 신규 진입이 차단됩니다.")

        for idx, t_code in enumerate(tickers_list):
            s_name = names_list[idx]
            is_ks = t_code in KS_CODES
            
            try:
                hist = fdr.DataReader(t_code, start_2mo)
                
                if len(hist) >= 20:
                    hist['MA20'] = hist['Close'].rolling(window=20).mean()
                    prev_close = float(hist['Close'].iloc[-2])
                    curr_price = float(hist['Close'].iloc[-1])
                    curr_ma20 = float(hist['MA20'].iloc[-1])
                    daily_ret = ((curr_price - prev_close) / prev_close) * 100

                    if daily_ret <= -5.0:
                        is_above_ma20 = (curr_price >= curr_ma20)
                        market_safe = is_ks_safe if is_ks else is_kd_safe
                        if not use_market_ma20_filter: market_safe = True
                        
                        if ((not use_ma20_filter) or is_above_ma20) and market_safe:
                            buy_budget = (total_capital / len(tickers_list)) / max_agents
                            est_shares = max(int(buy_budget // curr_price), 1)
                            buy_orders.append({
                                '종목': s_name,
                                '코드': t_code,
                                '현재가': format_money(curr_price) + "원",
                                '당일등락률': f"{daily_ret:+.2f}%",
                                '추천수량': f"{est_shares}주",
                                '예상주문금액': format_money(est_shares * curr_price) + "원"
                            })
                        else:
                            reason = ""
                            if use_market_ma20_filter and not market_safe:
                                reason = "지수 20일선 붕괴(시장위험)"
                            elif use_ma20_filter and not is_above_ma20:
                                reason = "개별 20일선 하회"
                                
                            hold_stocks.append({
                                '종목': s_name,
                                '코드': t_code,
                                '현재가': format_money(curr_price) + "원",
                                '당일등락률': f"{daily_ret:+.2f}%",
                                '상태': f"대기 ({reason}로 진입 보류)"
                            })
                    else:
                        hold_stocks.append({
                            '종목': s_name,
                            '코드': t_code,
                            '현재가': format_money(curr_price) + "원",
                            '당일등락률': f"{daily_ret:+.2f}%",
                            '상태': "대기 (매수 조건 미충족)"
                        })
            except Exception as e:
                st.error(f"⚠️ {s_name}({t_code}) 데이터 수집 실패: {e}")

        st.markdown("---")
        if buy_orders:
            st.markdown("<h4 style='color:#c0392b;margin-bottom:8px;'>🔴 [오늘 시장가 매수 실행 대상 종목]</h4>", unsafe_allow_html=True)
            for b in buy_orders:
                st.error(f"🎯 **{b['종목']} ({b['코드']})** | 현재가: **{b['현재가']}** ({b['당일등락률']}) ➔ **1호 요원 매수 발사!** (추천 수량: **{b['추천수량']}** / 예상 금액: {b['예상주문금액']})")
        else:
            st.success("🟢 **[매수 신호 없음]** 출격 조건을 만족하는 종목이 없습니다. 전액 현금을 안전하게 유지합니다.")

        if hold_stocks:
            with st.expander("⚪ [오늘 관망/대기 종목 현황 보기]"):
                hold_df = pd.DataFrame(hold_stocks)
                st.table(hold_df[['종목', '코드', '현재가', '당일등락률', '상태']])

st.markdown("---")

# --- 3. 메인 백테스트 연산 엔진 ---
if run_btn or 'calculated' in st.session_state:
    st.session_state['calculated'] = True

    if not tickers_list:
        st.warning("⚠️ 작전을 수행할 종목을 최소 1개 이상 선택해 주세요.")
        st.stop()

    buy_fee_rate = buy_fee_val / 100.0
    sell_tax_rate = sell_tax_val / 100.0
    capital_per_stock = total_capital / len(tickers_list)
    emergency_threshold = -abs(emergency_cut_pct) if emergency_cut_active else -999.0

    strategy_names_map = {
        '3tier': '3단 밸런스 과수원 전략 (60%재투자/20%현금/20%코어)',
        'full_cash': '풀 현금 복리 재투자 전략 (100% 컴파운딩)',
        'equal_alloc': '균등 배분 고정 전략 (No Reinvest / Buy&Hold 1/N)'
    }
    current_strategy_name = strategy_names_map.get(selected_strategy, '전략')

    with st.spinner("📡 [박가이버 사령부] 최신 시장 데이터를 수집 및 연산 중입니다..."):
        end_date = datetime.datetime.today()
        start_date = end_date - relativedelta(years=years + 1)
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        try:
            kospi_df = fdr.DataReader('KS11', start_str, end_str)
            kosdaq_df = fdr.DataReader('KQ11', start_str, end_str)
            kospi_df['MA20'] = kospi_df['Close'].rolling(window=20).mean()
            kosdaq_df['MA20'] = kosdaq_df['Close'].rolling(window=20).mean()
        except:
            kospi_df = pd.DataFrame()
            kosdaq_df = pd.DataFrame()

        all_matched_trades = []
        stock_results = {}
        combined_equity_df = pd.DataFrame()
        all_active_positions = []

        total_cycles_all = 0
        full_launch_cycles_all = 0
        agent_perf_dist = {i: {'wins': 0, 'losses': 0} for i in range(1, max_agents + 1)}
        total_agent_counter = 0
        total_fees_paid_all = 0.0

        for idx, ticker in enumerate(tickers_list):
            s_name = names_list[idx]
            s_capital = capital_per_stock
            is_ks = ticker in KS_CODES

            try:
                df = fdr.DataReader(ticker, start_str, end_str)
            except:
                continue
                
            if df.empty: continue

            df['Daily_Return'] = df['Close'].pct_change() * 100
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA60'] = df['Close'].rolling(window=60).mean()
            df['MA120'] = df['Close'].rolling(window=120).mean()
            df = df[df.index >= (end_date - relativedelta(years=years)).strftime('%Y-%m-%d')].copy()

            positions = []
            core_shares = 0
            reserve_cash = 0.0
            total_trades = 0
            win_trades = 0
            loss_trades = 0
            total_cycles = 0
            full_launch_cycles = 0
            stock_total_fees = 0.0

            matched_trades = []
            agent_counter = 0
            current_capital = float(s_capital)
            step_progress = 0.0
            level_up_count = 0
            step_down_count = 0
            daily_log = []

            for date, row in df.iterrows():
                close = float(row['Close'])
                daily_return = float(row['Daily_Return'])
                ma20 = float(row['MA20']) if not pd.isna(row['MA20']) else close
                ma60 = float(row['MA60']) if not pd.isna(row['MA60']) else close
                ma120 = float(row['MA120']) if not pd.isna(row['MA120']) else close
                date_str = date.strftime('%Y-%m-%d')

                if pd.isna(daily_return): continue

                is_super_bull = (close > ma20) and (ma20 > ma60) and (ma60 > ma120)
                is_super_bear = (close < ma20) and (ma20 < ma60) and (ma60 < ma120)
                target_ret = 15.0 if is_super_bull else (5.0 if is_super_bear else 10.0)

                # 1. 익절 조건 달성 판별
                has_winner = any(((close - pos['entry_price']) / pos['entry_price']) * 100 >= pos['target_ret'] for pos in positions)
                
                # 2. 비상 탈출 손절 조건 판별
                has_emergency_cut = False
                if emergency_cut_active and len(positions) > 0:
                    has_emergency_cut = any(((close - pos['entry_price']) / pos['entry_price']) * 100 <= emergency_threshold for pos in positions)

                if has_winner or has_emergency_cut:
                    total_cycles += 1
                    total_cycles_all += 1
                    batch_size = len(positions)
                    if batch_size == max_agents:
                        full_launch_cycles += 1
                        full_launch_cycles_all += 1

                    batch_reinvest_profit = 0.0
                    current_batch_trades = []

                    for pos in positions:
                        shares = pos['shares']
                        buy_gross = shares * pos['entry_price']
                        buy_fee_cost = buy_gross * buy_fee_rate
                        buy_amount_net = buy_gross + buy_fee_cost

                        sell_gross = shares * close
                        sell_tax_cost = sell_gross * sell_tax_rate
                        sell_amount_net = sell_gross - sell_tax_cost

                        trade_fee_total = buy_fee_cost + sell_tax_cost
                        stock_total_fees += trade_fee_total
                        total_fees_paid_all += trade_fee_total

                        profit_krw = sell_amount_net - buy_amount_net
                        ret = (profit_krw / buy_amount_net) * 100

                        if profit_krw > 0:
                            if selected_strategy == '3tier':
                                reinvest_amt = profit_krw * 0.60
                                reserve_cash += (profit_krw * 0.20)
                                buyable_core = int((profit_krw * 0.20) // close)
                                core_shares += buyable_core
                            elif selected_strategy == 'full_cash':
                                reinvest_amt = profit_krw * 1.00
                            else:
                                reinvest_amt = 0.0
                        else:
                            reinvest_amt = profit_krw

                        batch_reinvest_profit += reinvest_amt
                        total_trades += 1
                        is_win = profit_krw >= 0
                        if is_win: win_trades += 1
                        else: loss_trades += 1

                        if batch_size in agent_perf_dist:
                            if is_win: agent_perf_dist[batch_size]['wins'] += 1
                            else: agent_perf_dist[batch_size]['losses'] += 1

                        duration_days = (date - pos['entry_dt']).days if 'entry_dt' in pos else 0
                        
                        trade_label = "🎯 정상 복귀(+5%)" if is_win else f"🚨 비상 탈출({emergency_threshold:.0f}%)"

                        current_batch_trades.append({
                            '요원': pos['name'], '작전구역': s_name, '종목코드': ticker,
                            '출격일': pos['entry_date'], '진입일 등락률': f"{pos['entry_return']:+.2f}%",
                            '진입단가': format_money(pos['entry_price']) + "원", '진입금액': format_money(buy_amount_net) + "원",
                            '복귀일': date_str, '청산일 등락률': f"{daily_return:+.2f}%",
                            '청산단가': format_money(close) + "원", '매도금액': format_money(sell_amount_net) + "원",
                            '총수수료·세금': format_money(trade_fee_total) + "원",
                            '등락폭': f"{'+' if close >= pos['entry_price'] else ''}{format_money(close - pos['entry_price'])}원 ({ret:+.2f}%)",
                            '소요기간': f"{duration_days}일 소요", '순수익률': f"{ret:+.2f}%",
                            '정산내역': f"{'+' if profit_krw >= 0 else ''}{format_money(profit_krw)}원",
                            '구분': trade_label,
                            'is_win': is_win, 'raw_profit': profit_krw, 'exit_date': date
                        })

                    event_effect_str = ""
                    if selected_strategy != 'equal_alloc':
                        step_progress += batch_reinvest_profit
                        threshold = current_capital * 0.10
                        if step_progress >= threshold:
                            level_up_count += 1; current_capital += threshold; step_progress = 0.0
                            event_effect_str = f"🚀 [레벨업 UP! Lv.{level_up_count}]"
                        elif step_progress <= -threshold and current_capital > s_capital:
                            step_down_count += 1; current_capital -= threshold; step_progress = 0.0
                            event_effect_str = f"📉 [스텝다운 DOWN]"

                    for t in current_batch_trades:
                        lvl_text = f"Lv.{max(1, level_up_count + 1)}"
                        if event_effect_str: lvl_text += f" <br><span style='color:#c0392b; font-size:9px;'>{event_effect_str}</span>"
                        t['스노우볼 레벨'] = lvl_text

                    matched_trades.extend(current_batch_trades)
                    positions = []

                # 시장 지수 폭락 감시 락 검증 로직
                market_safe = True
                if use_market_ma20_filter:
                    try:
                        if is_ks:
                            if date in kospi_df.index:
                                k_c = float(kospi_df.loc[date, 'Close'].iloc[0]) if isinstance(kospi_df.loc[date, 'Close'], pd.Series) else float(kospi_df.loc[date, 'Close'])
                                k_m = float(kospi_df.loc[date, 'MA20'].iloc[0]) if isinstance(kospi_df.loc[date, 'MA20'], pd.Series) else float(kospi_df.loc[date, 'MA20'])
                                if not pd.isna(k_m) and k_c < k_m: market_safe = False
                        else:
                            if date in kosdaq_df.index:
                                kd_c = float(kosdaq_df.loc[date, 'Close'].iloc[0]) if isinstance(kosdaq_df.loc[date, 'Close'], pd.Series) else float(kosdaq_df.loc[date, 'Close'])
                                kd_m = float(kosdaq_df.loc[date, 'MA20'].iloc[0]) if isinstance(kosdaq_df.loc[date, 'MA20'], pd.Series) else float(kosdaq_df.loc[date, 'MA20'])
                                if not pd.isna(kd_m) and kd_c < kd_m: market_safe = False
                    except:
                        pass

                # 신규 매수 진입 로직
                if daily_return <= -5.0 and len(positions) < max_agents:
                    is_above_ma20 = (close >= ma20)
                    
                    if ((not use_ma20_filter) or is_above_ma20) and market_safe:
                        agent_counter += 1; total_agent_counter += 1
                        scale_ratio = current_capital / s_capital if selected_strategy != 'equal_alloc' else 1.0
                        agent_budget = int((s_capital // max_agents) * scale_ratio)
                        shares = max(int(agent_budget // close), 1)

                        positions.append({
                            'name': f"{s_name}-{agent_counter}호", 'entry_price': close,
                            'entry_date': date_str, 'entry_dt': date, 'entry_return': daily_return,
                            'shares': shares, 'target_ret': target_ret
                        })

                active_eval = sum(p['shares'] * close for p in positions)
                core_eval = core_shares * close
                realized_pnl = sum([t['raw_profit'] for t in matched_trades])
                stock_equity = s_capital + realized_pnl + reserve_cash + core_eval + active_eval - (sum(p['shares']*p['entry_price'] for p in positions))

                daily_log.append({'Date': date, 'Stock_Equity': stock_equity})

            for p in positions:
                cur_eval_p = p['shares'] * float(df['Close'].iloc[-1])
                pnl_p = cur_eval_p - (p['shares'] * p['entry_price'])
                pnl_pct = (pnl_p / (p['shares'] * p['entry_price'])) * 100
                holding_days = (end_date - p['entry_dt']).days
                entry_amount = p['shares'] * p['entry_price']

                all_active_positions.append({
                    '작전구역': s_name, '요원명': p['name'], '파견일': p['entry_date'],
                    'entry_dt': p['entry_dt'], 'holding_days': holding_days,
                    '진입단가': format_money(p['entry_price']) + "원", '수량': f"{p['shares']}주",
                    '진입금액': format_money(entry_amount) + "원",
                    '평가금액': format_money(cur_eval_p) + "원",
                    '평가손익': f"{'+' if pnl_p >= 0 else ''}{format_money(pnl_p)}원 ({pnl_pct:+.2f}%)",
                    'is_plus': pnl_p >= 0,
                    'pnl_val': pnl_p, 'pnl_pct': pnl_pct
                })

            if daily_log:
                df_stock_eq = pd.DataFrame(daily_log).set_index('Date')
                combined_equity_df[s_name] = df_stock_eq['Stock_Equity']

            final_close_price = float(df['Close'].iloc[-1])
            stock_results[ticker] = {
                'name': s_name, 'total_trades': total_trades, 'win_trades': win_trades, 'loss_trades': loss_trades,
                'win_rate': (win_trades / total_trades * 100) if total_trades > 0 else 0,
                'net_profit': sum([t['raw_profit'] for t in matched_trades]),
                'reserve_cash': reserve_cash, 'core_shares': core_shares,
                'core_eval': core_shares * final_close_price,
                'active_eval': sum(p['shares'] * final_close_price for p in positions),
                'active_count': len(positions),
                'final_equity': df_stock_eq['Stock_Equity'].iloc[-1] if 'df_stock_eq' in locals() and not df_stock_eq.empty else s_capital,
                'total_cycles': total_cycles, 'full_launch_cycles': full_launch_cycles,
                'level_up_count': level_up_count, 'step_down_count': step_down_count,
                'total_fees': stock_total_fees, 'matched_trades': matched_trades
            }
            all_matched_trades.extend(matched_trades)

        if not combined_equity_df.empty:
            combined_equity_df = combined_equity_df.ffill().bfill().dropna()
            combined_equity_df['Portfolio_Equity'] = combined_equity_df.sum(axis=1)

            portfolio_eq = combined_equity_df['Portfolio_Equity']
            rolling_max = portfolio_eq.cummax()
            drawdown = (portfolio_eq - rolling_max) / rolling_max * 100
            max_drawdown = drawdown.min()

            final_portfolio_equity = portfolio_eq.iloc[-1]
            portfolio_total_return = (final_portfolio_equity - total_capital) / total_capital * 100

            try:
                bench_df = pd.DataFrame(index=combined_equity_df.index)
                if not kospi_df.empty:
                    bench_df['KOSPI'] = kospi_df['Close'].reindex(bench_df.index, method='ffill')
                    bench_df['KOSPI_Normalized'] = total_capital * (bench_df['KOSPI'] / bench_df['KOSPI'].iloc[0])
                    k_rolling_max = bench_df['KOSPI'].cummax()
                    kospi_mdd = ((bench_df['KOSPI'] - k_rolling_max) / k_rolling_max * 100).min()
                    kospi_return = ((bench_df['KOSPI'].iloc[-1] - bench_df['KOSPI'].iloc[0]) / bench_df['KOSPI'].iloc[0]) * 100
                    alpha_vs_kospi = portfolio_total_return - kospi_return
                else:
                    bench_df['KOSPI_Normalized'] = total_capital; kospi_mdd = 0.0; kospi_return = 0.0; alpha_vs_kospi = 0.0

                if not kosdaq_df.empty:
                    bench_df['KOSDAQ'] = kosdaq_df['Close'].reindex(bench_df.index, method='ffill')
                    bench_df['KOSDAQ_Normalized'] = total_capital * (bench_df['KOSDAQ'] / bench_df['KOSDAQ'].iloc[0])
                    kd_rolling_max = bench_df['KOSDAQ'].cummax()
                    kosdaq_mdd = ((bench_df['KOSDAQ'] - kd_rolling_max) / kd_rolling_max * 100).min()
                    kosdaq_return = ((bench_df['KOSDAQ'].iloc[-1] - bench_df['KOSDAQ'].iloc[0]) / bench_df['KOSDAQ'].iloc[0]) * 100
                    alpha_vs_kosdaq = portfolio_total_return - kosdaq_return
                else:
                    bench_df['KOSDAQ_Normalized'] = total_capital; kosdaq_mdd = 0.0; kosdaq_return = 0.0; alpha_vs_kosdaq = 0.0

                bench_df['All_Cash'] = total_capital

            except Exception as e:
                kospi_mdd = 0.0; kosdaq_mdd = 0.0; kospi_return = 0.0; kosdaq_return = 0.0
                alpha_vs_kospi = portfolio_total_return; alpha_vs_kosdaq = portfolio_total_return
                bench_df = pd.DataFrame(index=combined_equity_df.index)
                bench_df['KOSPI_Normalized'] = total_capital; bench_df['KOSDAQ_Normalized'] = total_capital; bench_df['All_Cash'] = total_capital

            total_net_profit_all = sum([res['net_profit'] for res in stock_results.values()])
            total_trades_all = sum([res['total_trades'] for res in stock_results.values()])
            win_trades_all = sum([res['win_trades'] for res in stock_results.values()])
            loss_trades_all = sum([res['loss_trades'] for res in stock_results.values()])
            overall_win_rate = (win_trades_all / total_trades_all * 100) if total_trades_all > 0 else 0
            total_reserve_cash = sum([res['reserve_cash'] for res in stock_results.values()])
            total_core_eval = sum([res['core_eval'] for res in stock_results.values()])
            total_core_shares = sum([res['core_shares'] for res in stock_results.values()])
            total_active_eval = sum([res['active_eval'] for res in stock_results.values()])
            total_active_count = sum([res['active_count'] for res in stock_results.values()])
            total_level_up = sum([res['level_up_count'] for res in stock_results.values()])
            total_step_down = sum([res['step_down_count'] for res in stock_results.values()])
            full_launch_pct = (full_launch_cycles_all / total_cycles_all * 100) if total_cycles_all > 0 else 0.0

            all_matched_trades.sort(key=lambda x: x['exit_date'], reverse=True)
            start_date_str = combined_equity_df.index[0].strftime('%Y-%m-%d')
            end_date_str = combined_equity_df.index[-1].strftime('%Y-%m-%d')

            total_cash_all = final_portfolio_equity - total_active_eval - total_core_eval

            # --- 4. 백테스트 결과 UI 출력 ---
            st.markdown(f"<div style='background:#1b4f72;color:white;padding:12px 15px;border-radius:6px;margin-bottom:15px;'><h3 style='margin:0;font-size:16px;'>📊 [백테스트 종합 분석] 전략: {current_strategy_name} ({len(tickers_list)}개 종목 / 최근 {years}년)</h3></div>", unsafe_allow_html=True)

            market_lock_status = 'ON (지수 폭락 감시)' if use_market_ma20_filter else 'OFF'
            filter_status = 'ON (개별주 추세방어)' if use_ma20_filter else 'OFF'
            cut_status = f'ON ({emergency_threshold:.0f}% 강제 탈출)' if emergency_cut_active else 'OFF'
            
            st.markdown(f"<div style='background:#fef9e7;border:1px solid #f39c12;border-radius:6px;padding:14px;margin-bottom:15px;'><h4 style='margin:0 0 8px 0;color:#b7950b;font-size:14px;font-weight:bold;'>🤖 [제미니 분석 보고서] 스노우볼 오토 파일럿 작전 결과 ({raw_tickers})</h4><div style='font-size:12px;color:#7f8c8d;font-weight:bold;margin-bottom:6px;'>📋 적용된 핵심 알고리즘 조건 명세서 및 알파(Alpha) 성과</div><ul style='margin:0;padding-left:18px;font-size:11px;color:#2c3e50;line-height:1.6;'><li><b>초기 투자금액:</b> <b>{format_money(total_capital)}원</b> (총 씨드)</li><li><b>시장 락 & 추세 필터:</b> <b>시장지수 {market_lock_status}</b> / <b>개별주 {filter_status}</b></li><li><b>비상 탈출 손절(Emergency Cut):</b> <b>{cut_status}</b></li><li><b>지수 대비 초과 수익률(Alpha):</b> 포트폴리오 수익률(<b>{portfolio_total_return:+.1f}%</b>)이 동기간 KOSPI({kospi_return:+.1f}%), KOSDAQ({kosdaq_return:+.1f}%) 대비 각각 <b>+{alpha_vs_kospi:.1f}%p</b>, <b>+{alpha_vs_kosdaq:.1f}%p</b> 초과 달성</li><li><b>하락장 방어 및 리스크 제어:</b> MDD {max_drawdown:.2f}% 기록</li></ul></div>", unsafe_allow_html=True)

            # 상단 KPI 카드 세트
            st.markdown(f"<div style='display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px;'><div style='flex:1 1 125px;background:#e8f8f5;padding:12px;border-radius:6px;border-left:5px solid #1abc9c;min-width:110px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>🎯 통합 청산 승률</span><div style='font-size:17px;font-weight:900;color:#2c3e50;margin:4px 0;'>{overall_win_rate:.1f}%</div><span style='font-size:10px;color:#16a085;'>익절 {win_trades_all} / 손절 {loss_trades_all}</span></div><div style='flex:1 1 125px;background:#ebf5fb;padding:12px;border-radius:6px;border-left:5px solid #3498db;min-width:110px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>⚔️ 총 투입 요원</span><div style='font-size:17px;font-weight:900;color:#2c3e50;margin:4px 0;'>{total_agent_counter}명</div><span style='font-size:10px;color:#2980b9;'>총 {total_cycles_all}회차 / 대기 {total_active_count}명</span></div><div style='flex:1 1 125px;background:#fdf2e9;padding:12px;border-radius:6px;border-left:5px solid #e67e22;min-width:110px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>🔥 최대 요원 풀출력</span><div style='font-size:17px;font-weight:900;color:#c0392b;margin:4px 0;'>{full_launch_cycles_all}회 <span style='font-size:10px;'>({full_launch_pct:.1f}%)</span></div><span style='font-size:10px;color:#d35400;'>{max_agents}명 풀가동 비중</span></div><div style='flex:1 1 125px;background:#fadbd8;padding:12px;border-radius:6px;border-left:5px solid #c0392b;min-width:110px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>📉 최대 낙폭지수 (MDD)</span><div style='font-size:17px;font-weight:900;color:#78281f;margin:4px 0;'>{max_drawdown:.2f}%</div><span style='font-size:9.5px;color:#c0392b;font-weight:bold;'>지수: KS {kospi_mdd:.1f}% | KQ {kosdaq_mdd:.1f}%</span></div><div style='flex:1 1 125px;background:#fef9e7;padding:12px;border-radius:6px;border-left:5px solid #f1c40f;min-width:110px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>🚀 스노우볼 레벨UP</span><div style='font-size:17px;font-weight:900;color:#d35400;margin:4px 0;'>{total_level_up}회 <span style='font-size:9px;color:#7f8c8d;'>(다운:{total_step_down})</span></div><span style='font-size:10px;color:#b7950b;'>복리 예산 스텝 업</span></div></div>", unsafe_allow_html=True)

            st.markdown(f"<div style='display:flex;flex-wrap:wrap;gap:8px;margin-bottom:15px;'><div style='flex:1 1 135px;background:#f0fdf4;padding:12px;border-radius:6px;border-left:5px solid #16a34a;min-width:120px;'><span style='font-size:11px;color:#15803d;font-weight:bold;'>🚀 지수 대비 초과수익 (Alpha)</span><div style='font-size:16px;font-weight:900;color:#166534;margin:4px 0;'>+{alpha_vs_kospi:.1f}%p</div><span style='font-size:9.5px;color:#15803d;font-weight:bold;'>KS({kospi_return:+.1f}%) | KQ({kosdaq_return:+.1f}%) 초과</span></div><div style='flex:1 1 115px;background:#eaf2f8;padding:12px;border-radius:6px;border-left:5px solid #2980b9;min-width:105px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>💵 총 보유 현금</span><div style='font-size:13px;font-weight:900;color:#1b4f72;margin:4px 0;'>{format_money(total_cash_all)}원</div><span style='font-size:10px;color:#5d6d7e;'>비상금 {format_money(total_reserve_cash)}원 포함</span></div><div style='flex:1 1 115px;background:#fef9e7;padding:12px;border-radius:6px;border-left:5px solid #f39c12;min-width:105px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>📈 대기주식 평가금</span><div style='font-size:13px;font-weight:900;color:#2c3e50;margin:4px 0;'>{format_money(total_active_eval)}원</div><span style='font-size:10px;color:#7f8c8d;'>대기 요원 평가가</span></div><div style='flex:1 1 115px;background:#fdf2e9;padding:12px;border-radius:6px;border-left:5px solid #e67e22;min-width:105px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>💰 실현 순수익</span><div style='font-size:13px;font-weight:900;color:#c0392b;margin:4px 0;'>{'+' if total_net_profit_all>0 else ''}{format_money(total_net_profit_all)}원</div><span style='font-size:10px;color:#7f8c8d;'>매매 실현 순익</span></div><div style='flex:1 1 115px;background:#f5b7b1;padding:12px;border-radius:6px;border-left:5px solid #c0392b;min-width:105px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>💸 수수료·세금</span><div style='font-size:13px;font-weight:900;color:#78281f;margin:4px 0;'>-{format_money(total_fees_paid_all)}원</div><span style='font-size:10px;color:#7f8c8d;'>총 납부 비용</span></div><div style='flex:1 1 115px;background:#fef5e7;padding:12px;border-radius:6px;border-left:5px solid #d35400;min-width:105px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>🚀 총자산 ({portfolio_total_return:+.1f}%)</span><div style='font-size:13px;font-weight:900;color:#2c3e50;margin:4px 0;'>{format_money(final_portfolio_equity)}원</div><span style='font-size:10px;color:#7f8c8d;'>현금: {format_money(total_cash_all)}원</span></div><div style='flex:1 1 95px;background:#f4ecf7;padding:12px;border-radius:6px;border-left:5px solid #9b59b6;min-width:90px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>🍎 코어주식</span><div style='font-size:13px;font-weight:900;color:#8e44ad;margin:4px 0;'>{total_core_shares}주</div><span style='font-size:10px;color:#7f8c8d;'>{format_money(total_core_eval)}원</span></div></div>", unsafe_allow_html=True)

            # 종목별 종합 성적표
            rc_html = f"<div style='background:#fdfefe;border:1px solid #1abc9c;border-radius:6px;padding:14px;margin-bottom:15px;'><h4 style='margin:0 0 10px 0;color:#117a65;font-size:14px;font-weight:bold;'>📊 [종목별 종합 성적표] 옥석 가리기 현황판</h4>"
            rc_html += "<div style='overflow-x:auto;'><table style='width:100%;border-collapse:collapse;text-align:center;font-size:12px;min-width:650px;'><thead style='background-color:#e8f8f5;color:#117a65;'><tr><th style='padding:8px;border:1px solid #d5dbdf;'>종목명 (코드)</th><th style='padding:8px;border:1px solid #d5dbdf;'>총 매매 (승/패)</th><th style='padding:8px;border:1px solid #d5dbdf;'>승률</th><th style='padding:8px;border:1px solid #d5dbdf;'>누적 순수익</th><th style='padding:8px;border:1px solid #d5dbdf;'>수익 기여도</th><th style='padding:8px;border:1px solid #d5dbdf;'>평균 체류기간</th><th style='padding:8px;border:1px solid #d5dbdf;'>종합 판정</th></tr></thead><tbody>"
            
            for t_code, res in stock_results.items():
                s_name = res['name']
                net_p = res['net_profit']
                contrib = (net_p / total_net_profit_all * 100) if total_net_profit_all > 0 else 0
                win_r = res['win_rate']
                tot_t = res['total_trades']
                w_t = res['win_trades']
                l_t = res['loss_trades']
                
                stock_trades = [t for t in all_matched_trades if t['종목코드'] == t_code]
                avg_days = np.mean([int(str(t['소요기간']).replace('일 소요','').strip()) for t in stock_trades]) if stock_trades else 0
                
                if net_p < 0 or avg_days > 90 or (win_r < 50 and tot_t > 0):
                    status_tag = "<span style='background:#fdedec;color:#c0392b;padding:3px 8px;border-radius:4px;font-weight:bold;'>🔴 교체 권고</span>"
                    row_bg = "#fdedec"
                elif contrib < 5.0 or avg_days > 60 or l_t >= 2:
                    status_tag = "<span style='background:#fef9e7;color:#d35400;padding:3px 8px;border-radius:4px;font-weight:bold;'>🟡 주의 요망</span>"
                    row_bg = "#fcf3cf"
                else:
                    status_tag = "<span style='background:#e8f8f5;color:#117a65;padding:3px 8px;border-radius:4px;font-weight:bold;'>🟢 계속 유지</span>"
                    row_bg = "#ffffff"

                rc_html += f"<tr style='background-color:{row_bg};'><td style='padding:7px;border:1px solid #eaeded;font-weight:bold;'>{s_name} ({t_code})</td><td style='padding:7px;border:1px solid #eaeded;'>{tot_t}회 ({w_t}승/{l_t}패)</td><td style='padding:7px;border:1px solid #eaeded;font-weight:bold;'>{win_r:.1f}%</td><td style='padding:7px;border:1px solid #eaeded;color:#c0392b;font-weight:bold;'>{format_money(net_p)}원</td><td style='padding:7px;border:1px solid #eaeded;'>{contrib:.1f}%</td><td style='padding:7px;border:1px solid #eaeded;'>{avg_days:.1f}일</td><td style='padding:7px;border:1px solid #eaeded;'>{status_tag}</td></tr>"
            
            rc_html += "</tbody></table></div></div>"
            st.markdown(rc_html, unsafe_allow_html=True)

            # 종목별 코어주식 적립 현황판
            core_cards_html = f"<div style='background:#f4ecf7;border:1px solid #9b59b6;border-radius:6px;padding:14px;margin-bottom:15px;'><h4 style='margin:0 0 8px 0;color:#8e44ad;font-size:14px;font-weight:bold;'>🍎 [종목별 코어주식(나무) 적립 현황판] (총 적립: {total_core_shares}주)</h4><div style='font-size:11px;color:#4a5568;margin-bottom:10px;'>각 작전구역별로 복리 재투자 수익을 통해 영구 적립된 코어 주식(나무) 현황입니다.</div><div style='display:flex;flex-wrap:wrap;gap:8px;'>"
            for t_code, res in stock_results.items():
                core_cards_html += f"<div style='flex:1 1 180px;background:white;border:1px solid #d2b4de;border-top:4px solid #9b59b6;padding:10px;border-radius:6px;min-width:160px;'><b style='font-size:12px;color:#512e5f;'>{res['name']}</b><div style='font-size:11px;color:#2c3e50;margin-top:4px;'>• 적립 코어: <b>{res['core_shares']}주</b><br>• 평가금액: <b>{format_money(res['core_eval'])}원</b></div></div>"
            core_cards_html += "</div></div>"
            st.markdown(core_cards_html, unsafe_allow_html=True)

            # TOP 3 장기 체류 순위표
            sorted_active_positions = sorted(all_active_positions, key=lambda x: x['holding_days'], reverse=True)
            top3_long_term = sorted_active_positions[:3] if len(sorted_active_positions) >= 3 else sorted_active_positions

            top3_cards_html = "<div style='background:#fdf2e9;border:1px solid #e67e22;border-radius:6px;padding:14px;margin-bottom:15px;'><h4 style='margin:0 0 8px 0;color:#d35400;font-size:14px;font-weight:bold;'>🚨 [장기 체류 요원 TOP 3 경보 순위표] (청산 검토 대상)</h4><div style='font-size:11px;color:#7f8c8d;margin-bottom:10px;'>파견 이후 가장 오래 머물며 묶여있는 장기 체류 요원 순위입니다. (90일 이상 🚨 / 60일 이상 🔥 / 20일 이상 ⚠️)</div><div style='display:flex;flex-wrap:wrap;gap:8px;'>"
            for rank, p in enumerate(top3_long_term, 1):
                if p['holding_days'] >= 90:
                    badge_color = "#e74c3c"
                    icon = "🚨"
                elif p['holding_days'] >= 60:
                    badge_color = "#e67e22"
                    icon = "🔥"
                elif p['holding_days'] >= 20:
                    badge_color = "#f1c40f"
                    icon = "⚠️"
                else:
                    badge_color = "#2ecc71"
                    icon = "✅"

                pnl_pct_val = p['pnl_pct']
                if pnl_pct_val <= -25.0:
                    loss_tag = "<br><span style='color:#e74c3c;font-weight:bold;font-size:11px;'>🚨 -25% 돌파 (강제철수)</span>"
                elif pnl_pct_val <= -20.0:
                    loss_tag = "<br><span style='color:#e67e22;font-weight:bold;font-size:11px;'>🔥 -20% 돌파 (비중조절)</span>"
                elif pnl_pct_val <= -15.0:
                    loss_tag = "<br><span style='color:#f39c12;font-weight:bold;font-size:11px;'>⚠️ -15% 돌파 (손실주의)</span>"
                else:
                    loss_tag = ""

                top3_cards_html += f"<div style='flex:1 1 200px;background:white;border:1px solid #fadbd8;border-top:4px solid {badge_color};padding:10px;border-radius:6px;min-width:180px;'><div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'><b style='font-size:12px;color:#7d6608;'>🏆 {rank}위 - {p['작전구역']}</b><span style='background:{badge_color};color:white;padding:1px 6px;border-radius:4px;font-size:10px;font-weight:bold;'>{icon} {p['holding_days']}일 체류</span></div><div style='font-size:11px;color:#2c3e50;'>• 요원명: <b>{p['요원명']}</b><br>• 파견일: {p['파견일']}<br>• 평가손익: <b style='color:#c0392b;'>{p['평가손익']}</b>{loss_tag}</div></div>"
            top3_cards_html += "</div></div>"
            st.markdown(top3_cards_html, unsafe_allow_html=True)

            # 실시간 대기 요원 현황판
            active_html = f"<div style='background:#fdfefe;border:1px solid #3498db;border-radius:6px;padding:12px;margin-bottom:15px;'><h4 style='margin:0 0 10px 0;color:#2980b9;font-size:13px;'>🕵️ [현재 파견 대기 중인 요원 실시간 현황판] (총 {len(all_active_positions)}명 대기 중)</h4><div style='font-size:11px;color:#7f8c8d;margin-bottom:10px;'>⏱️ 체류경보: 90일 이상 🚨 / 60일 이상 🔥 / 20일 이상 ⚠️<br>📉 손실경보: -25% 이상 🚨 / -20% 이상 🔥 / -15% 이상 ⚠️</div>"
            if len(all_active_positions) > 0:
                active_html += "<div style='overflow-x:auto;'><table style='width:100%;border-collapse:collapse;text-align:center;font-size:11px;min-width:600px;'><thead style='background-color:#ebf5fb;color:#2980b9;'><tr><th style='padding:6px;border:1px solid #d5dbdf;width:40px;'>No.</th><th style='padding:6px;border:1px solid #d5dbdf;'>상태</th><th style='padding:6px;border:1px solid #d5dbdf;'>작전구역</th><th style='padding:6px;border:1px solid #d5dbdf;'>요원명</th><th style='padding:6px;border:1px solid #d5dbdf;'>파견일</th><th style='padding:6px;border:1px solid #d5dbdf;'>체류일수</th><th style='padding:6px;border:1px solid #d5dbdf;'>진입단가</th><th style='padding:6px;border:1px solid #d5dbdf;'>수량</th><th style='padding:6px;border:1px solid #d5dbdf;background:#d4e6f1;'>진입금액(총액)</th><th style='padding:6px;border:1px solid #d5dbdf;'>현재평가금액</th><th style='padding:6px;border:1px solid #d5dbdf;'>평가손익</th></tr></thead><tbody>"
                for idx_ap, ap in enumerate(all_active_positions, 1):
                    pnl_color = "#c0392b" if ap['is_plus'] else "#2980b9"
                    
                    if ap['holding_days'] >= 90:
                        row_bg = "#fdedec"
                        s_icon = "🚨"
                    elif ap['holding_days'] >= 60:
                        row_bg = "#fdebd0"
                        s_icon = "🔥"
                    elif ap['holding_days'] >= 20:
                        row_bg = "#fef9e7"
                        s_icon = "⚠️"
                    else:
                        row_bg = "#ffffff"
                        s_icon = "✅"

                    pnl_pct_val = ap['pnl_pct']
                    if pnl_pct_val <= -25.0:
                        loss_badge = "<br><span style='background:#e74c3c;color:white;padding:2px 4px;border-radius:3px;font-size:10px;display:inline-block;margin-top:3px;'>🚨 손실 -25%↓</span>"
                    elif pnl_pct_val <= -20.0:
                        loss_badge = "<br><span style='background:#e67e22;color:white;padding:2px 4px;border-radius:3px;font-size:10px;display:inline-block;margin-top:3px;'>🔥 손실 -20%↓</span>"
                    elif pnl_pct_val <= -15.0:
                        loss_badge = "<br><span style='background:#f39c12;color:white;padding:2px 4px;border-radius:3px;font-size:10px;display:inline-block;margin-top:3px;'>⚠️ 손실 -15%↓</span>"
                    else:
                        loss_badge = ""

                    active_html += f"<tr style='background-color:{row_bg};'><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;color:#7f8c8d;'>{idx_ap}</td><td style='padding:5px;border:1px solid #eaeded;font-size:14px;'>{s_icon}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;'>{ap['작전구역']}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;'>{ap['요원명']}</td><td style='padding:5px;border:1px solid #eaeded;'>{ap['파견일']}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;'>{ap['holding_days']}일</td><td style='padding:5px;border:1px solid #eaeded;'>{ap['진입단가']}</td><td style='padding:5px;border:1px solid #eaeded;'>{ap['수량']}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;color:#1e8449;'>{ap['진입금액']}</td><td style='padding:5px;border:1px solid #eaeded;'>{ap['평가금액']}</td><td style='padding:5px;border:1px solid #eaeded;color:{pnl_color};font-weight:bold;vertical-align:middle;'>{ap['평가손익']}{loss_badge}</td></tr>"
                active_html += "</tbody></table></div>"
            else:
                active_html += "<div style='font-size:11px;color:#7f8c8d;text-align:center;padding:5px;'>현재 장 마감 기준 현장에 파견되어 대기 중인 요원이 없습니다.</div>"
            active_html += "</div>"
            st.markdown(active_html, unsafe_allow_html=True)

            # 웹 차트
            st.subheader("📈 오토파일럿 총자산 vs 시장 지수 비교 성장 곡선")
            chart_df = pd.DataFrame(index=combined_equity_df.index)
            chart_df[f'오토파일럿 총자산 ({current_strategy_name})'] = combined_equity_df['Portfolio_Equity']
            chart_df['전액 현금 전략'] = bench_df['All_Cash']
            chart_df['KOSPI 지수'] = bench_df['KOSPI_Normalized']
            chart_df['KOSDAQ 지수'] = bench_df['KOSDAQ_Normalized']

            st.line_chart(chart_df)

            # 🌟 공식 매매 장부 (매수가/매도가 단가 컬럼)
            st.markdown("<div style='margin-top:25px;margin-bottom:8px;font-size:14px;font-weight:bold;color:#2c3e50;'>📜 박가이버 사령부 V10.36 공식 매매 장부 (익절=연분홍 / 손절=연파랑)</div>", unsafe_allow_html=True)
            
            table_html = "<div style='max-height:430px;overflow-y:auto;border:1px solid #d6dbdf;border-radius:6px;margin-bottom:15px;'><table style='width:100%;border-collapse:collapse;text-align:center;font-size:11px;min-width:920px;'><thead style='position:sticky;top:0;background-color:#f2f4f4;color:#2c3e50;z-index:1;'><tr><th style='padding:6px;border:1px solid #d5dbdf;width:40px;'>No.</th><th style='padding:6px;border:1px solid #d5dbdf;'>요원</th><th style='padding:6px;border:1px solid #d5dbdf;'>작전 구역</th><th style='padding:6px;border:1px solid #d5dbdf;'>출격일</th><th style='padding:6px;border:1px solid #d5dbdf;background:#fdedec;'>청산일(복귀)</th><th style='padding:6px;border:1px solid #d5dbdf;background:#e8f8f5;color:#117a65;'>매수가(진입단가)</th><th style='padding:6px;border:1px solid #d5dbdf;background:#fef9e7;color:#b7950b;'>매도가(청산단가)</th><th style='padding:6px;border:1px solid #d5dbdf;'>진입일 등락률</th><th style='padding:6px;border:1px solid #d5dbdf;'>진입금액</th><th style='padding:6px;border:1px solid #d5dbdf;'>매도금액</th><th style='padding:6px;border:1px solid #d5dbdf;'>총 수수료·세금</th><th style='padding:6px;border:1px solid #d5dbdf;'>등락폭</th><th style='padding:6px;border:1px solid #d5dbdf;'>소요기간</th><th style='padding:6px;border:1px solid #d5dbdf;'>순수익률</th><th style='padding:6px;border:1px solid #d5dbdf;'>정산내역</th><th style='padding:6px;border:1px solid #d5dbdf;'>구분</th><th style='padding:6px;border:1px solid #d5dbdf;'>스노우볼 레벨</th></tr></thead><tbody>"

            total_m_trades = len(all_matched_trades)
            for idx_t, t in enumerate(all_matched_trades, 1):
                row_no = total_m_trades - idx_t + 1
                row_bg = "#fdedec" if t['is_win'] else "#ebf5fb"
                text_color = "#c0392b" if t['is_win'] else "#2980b9"
                
                table_html += f"<tr style='background-color:{row_bg};'><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;color:#7f8c8d;'>{row_no}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;'>{t['요원']}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;color:#2980b9;'>{t['작전구역']}</td><td style='padding:5px;border:1px solid #eaeded;'>{t['출격일']}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;color:#c0392b;'>{t['복귀일']}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;color:#117a65;'>{t['진입단가']}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;color:#d35400;'>{t['청산단가']}</td><td style='padding:5px;border:1px solid #eaeded;'>{t['진입일 등락률']}</td><td style='padding:5px;border:1px solid #eaeded;'>{t['진입금액']}</td><td style='padding:5px;border:1px solid #eaeded;'>{t['매도금액']}</td><td style='padding:5px;border:1px solid #eaeded;color:#c0392b;'>{t['총수수료·세금']}</td><td style='padding:5px;border:1px solid #eaeded;color:{text_color};font-weight:bold;'>{t['등락폭']}</td><td style='padding:5px;border:1px solid #eaeded;'>{t['소요기간']}</td><td style='padding:5px;border:1px solid #eaeded;color:{text_color};font-weight:bold;'>{t['순수익률']}</td><td style='padding:5px;border:1px solid #eaeded;color:{text_color};font-weight:bold;'>{t['정산내역']}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;'>{t['구분']}</td><td style='padding:5px;border:1px solid #eaeded;color:#d35400;font-weight:bold;'>{t['스노우볼 레벨']}</td></tr>"

            table_html += "</tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)

            # CSV 다운로드
            df_export_data = []
            for t in all_matched_trades:
                clean_row = {k: v for k, v in t.items() if k not in ['is_win', 'raw_profit', 'exit_date']}
                df_export_data.append(clean_row)

            df_export = pd.DataFrame(df_export_data)

            csv_buffer = io.StringIO()
            df_export.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
            st.download_button(
                label="📜 엑셀(CSV) V10.36 공식 작전장부 다운로드",
                data=csv_buffer.getvalue().encode('utf-8-sig'),
                file_name=f"박가이버사령부_V10.36_{selected_strategy}.csv",
                mime="text/csv"
            )
        else:
            st.error("❌ 분석할 수 있는 데이터가 없습니다. 종목 코드를 확인해 주세요.")
else:
    st.info("👈 왼쪽 사이드바에서 종목과 조건 설정 후 [▶️ 박가이버 사령부 V10.36 작전 개시!] 버튼을 눌러주세요.")
