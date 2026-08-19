import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import datetime
from dateutil.relativedelta import relativedelta
import io
import warnings

warnings.filterwarnings('ignore')

# --- 1. 페이지 기본 설정 ---
st.set_page_config(page_title="박가이버 사령부 V10.39 (추세추종 완전체)", layout="wide", page_icon="🎛️")

def format_money(num):
    try:
        return f"{int(round(float(num))):,}"
    except:
        return str(num)

# ⚡ 데이터 고속 로딩 캐싱
@st.cache_data(ttl=3600)
def load_stock_data(ticker, start_date, end_date):
    try:
        return fdr.DataReader(ticker, start_date, end_date)
    except:
        return pd.DataFrame()

# --- 2. 사이드바 조종간 ---
st.sidebar.title("🎛️ 박가이버 사령부 V10.39")
st.sidebar.caption("은퇴 과수원 에디션 - 무제한 추세추종 탑재")

stock_database = {
    "삼성전자 (005930)": "005930", "실리콘투 (257720)": "257720", "리노공업 (058470)": "058470",
    "HD현대일렉트릭 (267260)": "267260", "DN오토모티브 (007340)": "007340", "와이지원 (019210)": "019210",
    "테크윙 (089030)": "089030", "피에스케이 (319660)": "319660", "제주반도체 (080220)": "080220",
    "SK하이닉스 (000660)": "000660", "두산에너빌리티 (034020)": "034020", "원익QNC (074600)": "074600",
    "한미반도체 (042700)": "042700", "주성엔지니어링 (036930)": "036930", "LG에너지솔루션 (373220)": "373220",
    "셀트리온 (068270)": "068270", "클리오 (237880)": "237880"
}

KS_CODES = ['005930', '034020', '000660', '373220', '068270', '267260', '007340']

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 종목 간편 검색 및 선택")

default_selected = ["삼성전자 (005930)", "실리콘투 (257720)", "리노공업 (058470)", "HD현대일렉트릭 (267260)", "DN오토모티브 (007340)"]
selected_stocks = st.sidebar.multiselect("클릭하거나 검색해서 종목을 담으세요:", options=list(stock_database.keys()), default=default_selected)

tickers_list, names_list = [], []
for s in selected_stocks:
    tickers_list.append(stock_database[s])
    names_list.append(s.split(" (")[0])

with st.sidebar.expander("➕ 리스트에 없는 종목 직접 추가하기"):
    custom_input = st.text_input("종목코드 6자리 입력 (예: 000660):", value="")
    custom_name = st.text_input("종목이름 입력 (예: SK하이닉스):", value="")
    if custom_input and custom_name:
        if custom_input.strip() not in tickers_list:
            tickers_list.append(custom_input.strip())
            names_list.append(custom_name.strip())

raw_tickers = ", ".join(tickers_list)

st.sidebar.markdown("---")
strategy_option = st.sidebar.selectbox("📊 작전전략 선택:", [
    ('🌳 3단 밸런스 과수원 전략 (60%재투자/20%현금/20%코어)', '3tier'),
    ('🚀 풀 현금 복리 재투자 전략 (100% 컴파운딩)', 'full_cash'),
    ('⚖️ 균등 배분 고정 전략 (No Reinvest / Buy&Hold 1/N)', 'equal_alloc')
], format_func=lambda x: x[0])
selected_strategy = strategy_option[1]

total_capital = st.sidebar.number_input("💰 총 씨드머니(원):", value=10000000, step=1000000)
stock_alloc_pct = st.sidebar.number_input("📊 1종목당 최대 할당 비중 (%):", value=20.0, step=5.0, min_value=1.0, max_value=100.0)
max_agents = st.sidebar.number_input("⚔️ 종목당 최대 파견 요원 수:", value=2, min_value=1, max_value=10)

buy_fee_val = st.sidebar.number_input("📉 매수수수료(%):", value=0.015, step=0.005, format="%.3f")
sell_tax_val = st.sidebar.number_input("📈 매도세금+수수료(%):", value=0.20, step=0.01, format="%.2f")
years = st.sidebar.number_input("🗓️ 백테스트 조회기간(년):", value=1, min_value=1, max_value=10)

st.sidebar.markdown("---")
st.sidebar.subheader("🌌 무제한 추세추종 (수익 천장 파괴)")
use_trailing_stop = st.sidebar.checkbox("🚀 추세추종 가동 (고정 익절 무시)", value=True, help="체크 시 15% 고정 목표를 무시하고 꺾일 때까지 끝까지 수익을 추적합니다.")
trailing_start_pct = st.sidebar.number_input("추적 레이더 가동 기준선 (%)", value=5.0, step=1.0)
trailing_pullback_pct = st.sidebar.number_input("고점 대비 청산 하락률 (%)", value=3.0, step=0.5)

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 종목별 맞춤 급락 타점")
custom_drop_rates = {}
for s_name, t_code in zip(names_list, tickers_list):
    default_rate = -2.5 if t_code in KS_CODES else -5.0
    custom_drop_rates[t_code] = st.sidebar.number_input(f"{s_name} 타점 (%)", value=default_rate, step=0.5, format="%.1f")

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ 리스크 제어 3중 안전장치")
use_market_ma20_filter = st.sidebar.checkbox("🚨 지수 폭락 감시 락 (20일선 붕괴시 매수금지)", value=True)
use_ma20_filter = st.sidebar.checkbox("🛡️ 개별주 20일선 지지 (종가가 20일선 위 유지)", value=True)
use_trend_filter = st.sidebar.checkbox("📈 20일선 우상향 & 10일선 정배열 필터", value=True)
emergency_cut_active = st.sidebar.checkbox("🚨 비상 탈출 손절(Emergency Cut) 가동", value=True)
emergency_cut_pct = st.sidebar.number_input("비상 탈출 손실 기준선 (%)", value=25.0, step=5.0, min_value=5.0, max_value=50.0)

run_btn = st.sidebar.button("▶️ 박가이버 사령부 V10.39 작전 개시!", type="primary")

# --- 🚨 실시간 신호등 모듈 ---
st.markdown("<div style='background:#154360;color:white;padding:12px;border-radius:6px;margin-bottom:12px;'><h3 style='margin:0;font-size:16px;'>🚨 [오후 3:20 PM 실전 작전 지시서] 실시간 신호등 통제실</h3></div>", unsafe_allow_html=True)
if st.button("📡 [3시 20분] 실시간 시장 스캔 실행", type="primary"):
    if len(tickers_list) > 0 and stock_alloc_pct * len(tickers_list) <= 100.0:
        with st.spinner("🔍 실시간 시세 분석 중..."):
            buy_orders, hold_stocks = [], []
            start_2mo = (datetime.datetime.today() - relativedelta(months=2)).strftime('%Y-%m-%d')
            
            k_hist = load_stock_data('KS11', start_2mo, None)
            kd_hist = load_stock_data('KQ11', start_2mo, None)
            try:
                k_hist['MA20'], kd_hist['MA20'] = k_hist['Close'].rolling(20).mean(), kd_hist['Close'].rolling(20).mean()
                is_ks_safe = float(k_hist['Close'].iloc[-1]) >= float(k_hist['MA20'].iloc[-1])
                is_kd_safe = float(kd_hist['Close'].iloc[-1]) >= float(kd_hist['MA20'].iloc[-1])
            except: is_ks_safe = is_kd_safe = True

            for idx, t_code in enumerate(tickers_list):
                s_name, is_ks = names_list[idx], t_code in KS_CODES
                target_drop_rate = custom_drop_rates.get(t_code, -5.0)
                try:
                    hist = load_stock_data(t_code, start_2mo, None)
                    if len(hist) >= 20:
                        hist['MA10'], hist['MA20'] = hist['Close'].rolling(window=10).mean(), hist['Close'].rolling(window=20).mean()
                        prev_close, curr_price = float(hist['Close'].iloc[-2]), float(hist['Close'].iloc[-1])
                        curr_ma10, curr_ma20, prev_ma20 = float(hist['MA10'].iloc[-1]), float(hist['MA20'].iloc[-1]), float(hist['MA20'].iloc[-2])
                        daily_ret = ((curr_price - prev_close) / prev_close) * 100

                        if daily_ret <= target_drop_rate:
                            market_safe = is_ks_safe if is_ks else is_kd_safe
                            if not use_market_ma20_filter: market_safe = True
                            trend_safe = True if not use_trend_filter else (curr_ma20 > prev_ma20 and curr_ma10 >= curr_ma20)
                            
                            if ((not use_ma20_filter) or curr_price >= curr_ma20) and market_safe and trend_safe:
                                est_shares = max(int(((total_capital * (stock_alloc_pct / 100.0)) / max_agents) // curr_price), 1)
                                buy_orders.append({'종목': s_name, '코드': t_code, '현재가': format_money(curr_price)+"원", '당일등락률': f"{daily_ret:+.2f}%", '수량': f"{est_shares}주"})
                            else: hold_stocks.append({'종목': s_name, '상태': '필터 조건 미달', '당일등락률': f"{daily_ret:+.2f}%", '현재가': format_money(curr_price)+"원", '코드': t_code})
                        else: hold_stocks.append({'종목': s_name, '상태': f'목표 타점({target_drop_rate}%) 미달', '당일등락률': f"{daily_ret:+.2f}%", '현재가': format_money(curr_price)+"원", '코드': t_code})
                except: pass

            if buy_orders:
                for b in buy_orders: st.error(f"🎯 **{b['종목']}** 출격! (현재가: {b['현재가']} / 등락률: {b['당일등락률']} / 수량: {b['수량']})")
            else: st.success("🟢 신규 매수 조건 없음. 대기 유지.")
            
            if hold_stocks:
                with st.expander("⚪ [오늘 관망/대기 종목 현황 보기]"):
                    st.table(pd.DataFrame(hold_stocks)[['종목', '코드', '현재가', '당일등락률', '상태']])
    else: st.error("❌ 종목을 선택하지 않았거나 비중 총합이 100%를 초과합니다.")
st.markdown("---")

# --- 3. 메인 백테스트 연산 엔진 ---
if run_btn or 'calculated' in st.session_state:
    st.session_state['calculated'] = True
    if not tickers_list: st.warning("⚠️ 작전을 수행할 종목을 선택해 주세요."); st.stop()
    if stock_alloc_pct * len(tickers_list) > 100.0: st.error("❌ 비중 총합 100% 초과입니다."); st.stop()

    buy_fee_rate, sell_tax_rate = buy_fee_val / 100.0, sell_tax_val / 100.0
    emergency_threshold = -abs(emergency_cut_pct) if emergency_cut_active else -999.0
    current_strategy_name = {'3tier': '3단 밸런스 과수원 전략', 'full_cash': '풀 현금 복리 재투자 전략', 'equal_alloc': '균등 배분 고정 전략'}.get(selected_strategy, '전략')

    with st.spinner("📡 [V10.39] 무제한 추세추종 엔진으로 극한의 수익 스캔 중... (대시보드 렌더링 포함)"):
        end_date = datetime.datetime.today()
        start_date = end_date - relativedelta(years=years + 1)
        start_str, end_str = start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

        kospi_df = load_stock_data('KS11', start_str, end_str)
        kosdaq_df = load_stock_data('KQ11', start_str, end_str)
        if not kospi_df.empty: kospi_df['MA20'] = kospi_df['Close'].rolling(20).mean()
        if not kosdaq_df.empty: kosdaq_df['MA20'] = kosdaq_df['Close'].rolling(20).mean()

        all_matched_trades, stock_results = [], {}
        combined_equity_df = pd.DataFrame()
        all_active_positions = []
        total_cycles_all, full_launch_cycles_all = 0, 0
        total_agent_counter, total_fees_paid_all = 0, 0.0

        for idx, ticker in enumerate(tickers_list):
            s_name, is_ks = names_list[idx], ticker in KS_CODES
            s_capital = total_capital * (stock_alloc_pct / 100.0)
            target_drop_rate = custom_drop_rates.get(ticker, -5.0)

            df = load_stock_data(ticker, start_str, end_str).copy()
            if df.empty: continue

            df['Prev_Close'] = df['Close'].shift(1)
            df['Daily_Return'] = df['Close'].pct_change() * 100
            df['MA10'] = df['Close'].rolling(window=10).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA60'] = df['Close'].rolling(window=60).mean()
            df['MA120'] = df['Close'].rolling(window=120).mean()
            df['MA20_prev'] = df['MA20'].shift(1)
            
            df = df[df.index >= (end_date - relativedelta(years=years)).strftime('%Y-%m-%d')].copy()

            positions = []
            core_shares, reserve_cash = 0, 0.0
            total_trades, win_trades, loss_trades = 0, 0, 0
            total_cycles, full_launch_cycles, stock_total_fees = 0, 0, 0.0
            matched_trades = []
            agent_counter, level_up_count, step_down_count = 0, 0, 0
            current_capital, step_progress = float(s_capital), 0.0
            daily_log = []

            for date, row in df.iterrows():
                close = float(row['Close'])
                prev_close = float(row['Prev_Close']) if not pd.isna(row['Prev_Close']) else close
                high = float(row['High']) if 'High' in row and not pd.isna(row['High']) else close
                low = float(row['Low']) if 'Low' in row and not pd.isna(row['Low']) else close
                
                ma10, ma20, ma20_prev = float(row['MA10']) if not pd.isna(row['MA10']) else close, float(row['MA20']) if not pd.isna(row['MA20']) else close, float(row['MA20_prev']) if not pd.isna(row['MA20_prev']) else close
                ma60, ma120 = float(row['MA60']) if not pd.isna(row['MA60']) else close, float(row['MA120']) if not pd.isna(row['MA120']) else close
                date_str = date.strftime('%Y-%m-%d')
                if pd.isna(row['Daily_Return']): continue

                # 🌟 매도 감시 (무제한 추세추종 vs 고정 목표가)
                current_batch_trades = []
                positions_to_keep = []
                batch_reinvest_profit = 0.0

                for pos in positions:
                    if high > pos.get('max_price', pos['entry_price']):
                        pos['max_price'] = high
                        
                    sell_price = None
                    sell_reason = ""
                    stop_price = pos['entry_price'] * (1 + emergency_threshold/100) if emergency_cut_active else 0
                    
                    if use_trailing_stop:
                        if ((pos['max_price'] - pos['entry_price']) / pos['entry_price']) * 100 >= trailing_start_pct:
                            pos['trailing_active'] = True
                        pullback_price = pos['max_price'] * (1 - trailing_pullback_pct / 100)
                        
                        if pos.get('trailing_active', False) and low <= pullback_price:
                            sell_price = pullback_price
                            sell_reason = f"🌌 추세추종 (고점대비 -{trailing_pullback_pct}%)"
                        elif emergency_cut_active and low <= stop_price and stop_price > 0:
                            sell_price = stop_price
                            sell_reason = f"🚨 비상 탈출({emergency_threshold:.0f}%)"
                    else:
                        target_price = pos['entry_price'] * (1 + pos['target_ret']/100)
                        if high >= target_price:
                            sell_price = target_price
                            sell_reason = f"🎯 정상 복귀(+{pos['target_ret']:.0f}%)"
                        elif emergency_cut_active and low <= stop_price and stop_price > 0:
                            sell_price = stop_price
                            sell_reason = f"🚨 비상 탈출({emergency_threshold:.0f}%)"

                    if sell_price:
                        shares = pos['shares']
                        buy_amount_net = (shares * pos['entry_price']) * (1 + buy_fee_rate)
                        sell_amount_net = (shares * sell_price) * (1 - sell_tax_rate)
                        trade_fee_total = (shares * pos['entry_price'] * buy_fee_rate) + (shares * sell_price * sell_tax_rate)
                        
                        stock_total_fees += trade_fee_total
                        total_fees_paid_all += trade_fee_total
                        profit_krw = sell_amount_net - buy_amount_net
                        ret = (profit_krw / buy_amount_net) * 100

                        if profit_krw > 0:
                            if selected_strategy == '3tier':
                                reinvest_amt = profit_krw * 0.60
                                reserve_cash += (profit_krw * 0.20)
                                core_shares += int((profit_krw * 0.20) // sell_price)
                            elif selected_strategy == 'full_cash':
                                reinvest_amt = profit_krw * 1.00
                            else: reinvest_amt = 0.0
                        else: reinvest_amt = profit_krw

                        batch_reinvest_profit += reinvest_amt
                        total_trades += 1
                        is_win = profit_krw >= 0
                        if is_win: win_trades += 1
                        else: loss_trades += 1

                        current_batch_trades.append({
                            '요원': pos['name'], '작전구역': s_name, '종목코드': ticker,
                            '출격일': pos['entry_date'], '진입일 등락률': f"{pos['entry_return']:+.2f}%",
                            '진입단가': format_money(pos['entry_price'])+"원", '진입금액': format_money(buy_amount_net)+"원",
                            '복귀일': date_str, '청산일 등락률': f"{row['Daily_Return']:+.2f}%",
                            '최고달성가': format_money(pos['max_price'])+"원" if use_trailing_stop else "-",
                            '청산단가': format_money(sell_price)+"원", '매도금액': format_money(sell_amount_net)+"원",
                            '총수수료·세금': format_money(trade_fee_total)+"원", '등락폭': f"{format_money(sell_price - pos['entry_price'])}원 ({ret:+.2f}%)",
                            '소요기간': f"{(date - pos['entry_dt']).days}일 소요", '순수익률': f"{ret:+.2f}%",
                            '정산내역': f"{'+' if profit_krw >= 0 else ''}{format_money(profit_krw)}원",
                            '구분': sell_reason, 'is_win': is_win, 'raw_profit': profit_krw, 'exit_date': date
                        })
                    else:
                        positions_to_keep.append(pos)
                
                positions = positions_to_keep
                
                if current_batch_trades:
                    total_cycles += 1; total_cycles_all += 1
                    if len(positions) + len(current_batch_trades) == max_agents:
                        full_launch_cycles += 1; full_launch_cycles_all += 1
                        
                    event_effect_str = ""
                    if selected_strategy != 'equal_alloc':
                        step_progress += batch_reinvest_profit
                        if step_progress >= current_capital * 0.10:
                            level_up_count += 1; current_capital += current_capital * 0.10; step_progress = 0.0
                            event_effect_str = f"🚀 [레벨업 UP! Lv.{level_up_count}]"

                    for t in current_batch_trades:
                        t['스노우볼 레벨'] = f"Lv.{max(1, level_up_count + 1)}" + (f" <br><span style='color:#c0392b; font-size:9px;'>{event_effect_str}</span>" if event_effect_str else "")
                    matched_trades.extend(current_batch_trades)

                # --- 매수 감시 ---
                drop_target_price = prev_close * (1 + target_drop_rate / 100)
                if low <= drop_target_price and len(positions) < max_agents:
                    market_safe = True
                    if use_market_ma20_filter:
                        try:
                            bench = kospi_df if is_ks else kosdaq_df
                            if date in bench.index and float(bench.loc[date, 'Close']) < float(bench.loc[date, 'MA20']): market_safe = False
                        except: pass

                    trend_safe = True if not use_trend_filter else (ma20 > ma20_prev and ma10 >= ma20)
                    if ((not use_ma20_filter) or close >= ma20) and market_safe and trend_safe:
                        agent_counter += 1; total_agent_counter += 1
                        shares = max(int(((s_capital / max_agents) * (current_capital / s_capital if selected_strategy != 'equal_alloc' else 1.0)) // drop_target_price), 1)
                        is_super_bull = (close > ma20) and (ma20 > ma60) and (ma60 > ma120)
                        is_super_bear = (close < ma20) and (ma20 < ma60) and (ma60 < ma120)

                        positions.append({
                            'name': f"{s_name}-{agent_counter}호", 'entry_price': drop_target_price,
                            'entry_date': date_str, 'entry_dt': date, 'entry_return': target_drop_rate,
                            'shares': shares, 'target_ret': 15.0 if is_super_bull else (5.0 if is_super_bear else 10.0),
                            'max_price': drop_target_price, 'trailing_active': False
                        })

                active_eval = sum(p['shares'] * close for p in positions)
                stock_equity = s_capital + sum([t['raw_profit'] for t in matched_trades]) + reserve_cash + (core_shares * close) + active_eval - sum(p['shares']*p['entry_price'] for p in positions)
                daily_log.append({'Date': date, 'Stock_Equity': stock_equity})

            for p in positions:
                cur_eval_p = p['shares'] * float(df['Close'].iloc[-1])
                pnl_p = cur_eval_p - (p['shares'] * p['entry_price'])
                all_active_positions.append({
                    '작전구역': s_name, '요원명': p['name'], '파견일': p['entry_date'], 'entry_dt': p['entry_dt'], 'holding_days': (end_date - p['entry_dt']).days,
                    '진입단가': format_money(p['entry_price'])+"원", '수량': f"{p['shares']}주", '진입금액': format_money(p['shares'] * p['entry_price'])+"원",
                    '평가금액': format_money(cur_eval_p)+"원", '평가손익': f"{'+' if pnl_p >= 0 else ''}{format_money(pnl_p)}원 ({(pnl_p / (p['shares'] * p['entry_price']) * 100):+.2f}%)",
                    'is_plus': pnl_p >= 0, 'pnl_val': pnl_p, 'pnl_pct': (pnl_p / (p['shares'] * p['entry_price'])) * 100,
                    '고점추적': f"<span style='color:#8e44ad;font-weight:bold;'>+{((p['max_price']-p['entry_price'])/p['entry_price']*100):.1f}% 도달</span>" if use_trailing_stop else "-"
                })

            if daily_log: combined_equity_df[s_name] = pd.DataFrame(daily_log).set_index('Date')['Stock_Equity']

            stock_results[ticker] = {
                'name': s_name, 'total_trades': total_trades, 'win_trades': win_trades, 'loss_trades': loss_trades,
                'win_rate': (win_trades / total_trades * 100) if total_trades > 0 else 0,
                'net_profit': sum([t['raw_profit'] for t in matched_trades]), 'reserve_cash': reserve_cash, 'core_shares': core_shares, 'core_eval': core_shares * float(df['Close'].iloc[-1]),
                'active_eval': sum(p['shares'] * float(df['Close'].iloc[-1]) for p in positions), 'active_count': len(positions),
                'total_cycles': total_cycles, 'full_launch_cycles': full_launch_cycles, 'level_up_count': level_up_count, 'step_down_count': step_down_count
            }
            all_matched_trades.extend(matched_trades)

        # 자산 결산
        if not combined_equity_df.empty:
            combined_equity_df = combined_equity_df.ffill().bfill().dropna()
            total_unallocated_cash = total_capital - (total_capital * (stock_alloc_pct / 100.0) * len(tickers_list))
            combined_equity_df['Portfolio_Equity'] = combined_equity_df.sum(axis=1) + total_unallocated_cash

            portfolio_eq = combined_equity_df['Portfolio_Equity']
            max_drawdown = ((portfolio_eq - portfolio_eq.cummax()) / portfolio_eq.cummax() * 100).min()
            portfolio_total_return = (portfolio_eq.iloc[-1] - total_capital) / total_capital * 100

            try:
                bench_df = pd.DataFrame(index=combined_equity_df.index)
                if not kospi_df.empty:
                    bench_df['KOSPI_Normalized'] = total_capital * (kospi_df['Close'].reindex(bench_df.index, method='ffill') / kospi_df['Close'].reindex(bench_df.index, method='ffill').iloc[0])
                    kospi_return = ((bench_df['KOSPI_Normalized'].iloc[-1] - total_capital) / total_capital) * 100
                else: kospi_return = 0.0
                if not kosdaq_df.empty:
                    bench_df['KOSDAQ_Normalized'] = total_capital * (kosdaq_df['Close'].reindex(bench_df.index, method='ffill') / kosdaq_df['Close'].reindex(bench_df.index, method='ffill').iloc[0])
                    kosdaq_return = ((bench_df['KOSDAQ_Normalized'].iloc[-1] - total_capital) / total_capital) * 100
                else: kosdaq_return = 0.0
                bench_df['All_Cash'] = total_capital
            except: pass

            total_net_profit_all = sum([res['net_profit'] for res in stock_results.values()])
            win_trades_all = sum([res['win_trades'] for res in stock_results.values()])
            total_trades_all = sum([res['total_trades'] for res in stock_results.values()])
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
            total_cash_all = portfolio_eq.iloc[-1] - total_active_eval - total_core_eval
            
            all_matched_trades.sort(key=lambda x: x['exit_date'], reverse=True)

            # --- 4. 대시보드 UI (V10.37 100% 완전 복원) ---
            st.markdown(f"<div style='background:#1b4f72;color:white;padding:12px 15px;border-radius:6px;margin-bottom:15px;'><h3 style='margin:0;font-size:16px;'>📊 [백테스트 종합 분석] 전략: {current_strategy_name} ({len(tickers_list)}개 종목 / 최근 {years}년)</h3></div>", unsafe_allow_html=True)
            
            market_lock_status = 'ON (지수 폭락 감시)' if use_market_ma20_filter else 'OFF'
            filter_status = 'ON (기울기&정배열 필터)' if use_trend_filter else ('ON (20일선 지지)' if use_ma20_filter else 'OFF')
            cut_status = f'ON ({emergency_threshold:.0f}% 강제 탈출)' if emergency_cut_active else 'OFF'
            trail_status = f'ON (무제한 고점 추적)' if use_trailing_stop else 'OFF (고정 15% 익절)'

            st.markdown(f"<div style='background:#fef9e7;border:1px solid #f39c12;border-radius:6px;padding:14px;margin-bottom:15px;'><h4 style='margin:0 0 8px 0;color:#b7950b;font-size:14px;font-weight:bold;'>🤖 [제미니 분석 보고서] 스노우볼 오토 파일럿 작전 결과</h4><div style='font-size:12px;color:#7f8c8d;font-weight:bold;margin-bottom:6px;'>📋 적용된 핵심 알고리즘 조건 명세서 및 알파(Alpha) 성과</div><ul style='margin:0;padding-left:18px;font-size:11px;color:#2c3e50;line-height:1.6;'><li><b>초기 투자금액:</b> <b>{format_money(total_capital)}원</b> (1종목당 최대 할당: {stock_alloc_pct}%)</li><li><b>시장 락 & 추세 필터:</b> <b>시장지수 {market_lock_status}</b> / <b>개별주 {filter_status}</b></li><li><b>위기 관리 및 수익 극대화:</b> 손절 <b>{cut_status}</b> | 익절 <b>{trail_status}</b></li><li><b>지수 대비 초과 수익률(Alpha):</b> 포트폴리오 수익률(<b>{portfolio_total_return:+.1f}%</b>)이 동기간 KOSPI({kospi_return:+.1f}%), KOSDAQ({kosdaq_return:+.1f}%) 대비 각각 <b>+{portfolio_total_return - kospi_return:.1f}%p</b>, <b>+{portfolio_total_return - kosdaq_return:.1f}%p</b> 초과 달성</li></ul></div>", unsafe_allow_html=True)

            # 상단 KPI 카드 세트 1행 (5개 카드 완벽 복원)
            st.markdown(f"<div style='display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px;'><div style='flex:1 1 125px;background:#e8f8f5;padding:12px;border-radius:6px;border-left:5px solid #1abc9c;min-width:110px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>🎯 통합 청산 승률</span><div style='font-size:17px;font-weight:900;color:#2c3e50;margin:4px 0;'>{overall_win_rate:.1f}%</div><span style='font-size:10px;color:#16a085;'>익절 {win_trades_all} / 손절 {loss_trades_all}</span></div><div style='flex:1 1 125px;background:#ebf5fb;padding:12px;border-radius:6px;border-left:5px solid #3498db;min-width:110px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>⚔️ 총 투입 요원</span><div style='font-size:17px;font-weight:900;color:#2c3e50;margin:4px 0;'>{total_agent_counter}명</div><span style='font-size:10px;color:#2980b9;'>총 {total_cycles_all}회차 / 대기 {total_active_count}명</span></div><div style='flex:1 1 125px;background:#fdf2e9;padding:12px;border-radius:6px;border-left:5px solid #e67e22;min-width:110px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>🔥 최대 요원 풀출력</span><div style='font-size:17px;font-weight:900;color:#c0392b;margin:4px 0;'>{full_launch_cycles_all}회 <span style='font-size:10px;'>({full_launch_pct:.1f}%)</span></div><span style='font-size:10px;color:#d35400;'>{max_agents}명 풀가동 비중</span></div><div style='flex:1 1 125px;background:#fadbd8;padding:12px;border-radius:6px;border-left:5px solid #c0392b;min-width:110px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>📉 최대 낙폭지수 (MDD)</span><div style='font-size:17px;font-weight:900;color:#78281f;margin:4px 0;'>{max_drawdown:.2f}%</div><span style='font-size:9.5px;color:#c0392b;font-weight:bold;'>안전 자산 관리 최적화</span></div><div style='flex:1 1 125px;background:#fef9e7;padding:12px;border-radius:6px;border-left:5px solid #f1c40f;min-width:110px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>🚀 스노우볼 레벨UP</span><div style='font-size:17px;font-weight:900;color:#d35400;margin:4px 0;'>{total_level_up}회 <span style='font-size:9px;color:#7f8c8d;'>(다운:{total_step_down})</span></div><span style='font-size:10px;color:#b7950b;'>복리 예산 스텝 업</span></div></div>", unsafe_allow_html=True)

            # 상단 KPI 카드 세트 2행 (7개 카드 완벽 복원)
            st.markdown(f"<div style='display:flex;flex-wrap:wrap;gap:8px;margin-bottom:15px;'><div style='flex:1 1 135px;background:#f0fdf4;padding:12px;border-radius:6px;border-left:5px solid #16a34a;min-width:120px;'><span style='font-size:11px;color:#15803d;font-weight:bold;'>🚀 지수 대비 초과수익</span><div style='font-size:16px;font-weight:900;color:#166534;margin:4px 0;'>+{portfolio_total_return - kospi_return:.1f}%p</div><span style='font-size:9.5px;color:#15803d;font-weight:bold;'>KS({kospi_return:+.1f}%) 초과</span></div><div style='flex:1 1 115px;background:#eaf2f8;padding:12px;border-radius:6px;border-left:5px solid #2980b9;min-width:105px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>💵 총 보유 현금</span><div style='font-size:13px;font-weight:900;color:#1b4f72;margin:4px 0;'>{format_money(total_cash_all)}원</div><span style='font-size:10px;color:#5d6d7e;'>비상금 {format_money(total_reserve_cash)}원 포함</span></div><div style='flex:1 1 115px;background:#fef9e7;padding:12px;border-radius:6px;border-left:5px solid #f39c12;min-width:105px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>📈 대기주식 평가금</span><div style='font-size:13px;font-weight:900;color:#2c3e50;margin:4px 0;'>{format_money(total_active_eval)}원</div><span style='font-size:10px;color:#7f8c8d;'>대기 요원 평가가</span></div><div style='flex:1 1 115px;background:#fdf2e9;padding:12px;border-radius:6px;border-left:5px solid #e67e22;min-width:105px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>💰 실현 순수익</span><div style='font-size:13px;font-weight:900;color:#c0392b;margin:4px 0;'>{'+' if total_net_profit_all>0 else ''}{format_money(total_net_profit_all)}원</div><span style='font-size:10px;color:#7f8c8d;'>매매 실현 순익</span></div><div style='flex:1 1 115px;background:#f5b7b1;padding:12px;border-radius:6px;border-left:5px solid #c0392b;min-width:105px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>💸 수수료·세금</span><div style='font-size:13px;font-weight:900;color:#78281f;margin:4px 0;'>-{format_money(total_fees_paid_all)}원</div><span style='font-size:10px;color:#7f8c8d;'>총 납부 비용</span></div><div style='flex:1 1 115px;background:#fef5e7;padding:12px;border-radius:6px;border-left:5px solid #d35400;min-width:105px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>🚀 총자산 ({portfolio_total_return:+.1f}%)</span><div style='font-size:13px;font-weight:900;color:#2c3e50;margin:4px 0;'>{format_money(portfolio_eq.iloc[-1])}원</div><span style='font-size:10px;color:#7f8c8d;'>현금: {format_money(total_cash_all)}원</span></div><div style='flex:1 1 95px;background:#f4ecf7;padding:12px;border-radius:6px;border-left:5px solid #9b59b6;min-width:90px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>🍎 코어주식</span><div style='font-size:13px;font-weight:900;color:#8e44ad;margin:4px 0;'>{total_core_shares}주</div><span style='font-size:10px;color:#7f8c8d;'>{format_money(total_core_eval)}원</span></div></div>", unsafe_allow_html=True)

            # 옥석 가리기 현황판 (완벽 복원)
            rc_html = f"<div style='background:#fdfefe;border:1px solid #1abc9c;border-radius:6px;padding:14px;margin-bottom:15px;'><h4 style='margin:0 0 10px 0;color:#117a65;font-size:14px;font-weight:bold;'>📊 [종목별 종합 성적표] 옥석 가리기 현황판</h4>"
            rc_html += "<div style='overflow-x:auto;'><table style='width:100%;border-collapse:collapse;text-align:center;font-size:12px;min-width:650px;'><thead style='background-color:#e8f8f5;color:#117a65;'><tr><th style='padding:8px;border:1px solid #d5dbdf;'>종목명 (코드)</th><th style='padding:8px;border:1px solid #d5dbdf;'>총 매매 (승/패)</th><th style='padding:8px;border:1px solid #d5dbdf;'>승률</th><th style='padding:8px;border:1px solid #d5dbdf;'>누적 순수익</th><th style='padding:8px;border:1px solid #d5dbdf;'>수익 기여도</th><th style='padding:8px;border:1px solid #d5dbdf;'>평균 체류기간</th><th style='padding:8px;border:1px solid #d5dbdf;'>종합 판정</th></tr></thead><tbody>"
            for t_code, res in stock_results.items():
                contrib = (res['net_profit'] / total_net_profit_all * 100) if total_net_profit_all > 0 else 0
                avg_days = np.mean([int(str(t['소요기간']).replace('일 소요','').strip()) for t in all_matched_trades if t['종목코드'] == t_code]) if any(t['종목코드'] == t_code for t in all_matched_trades) else 0
                
                if res['net_profit'] < 0 or avg_days > 90 or (res['win_rate'] < 50 and res['total_trades'] > 0): status_tag, row_bg = "<span style='background:#fdedec;color:#c0392b;padding:3px 8px;border-radius:4px;font-weight:bold;'>🔴 교체 권고</span>", "#fdedec"
                elif contrib < 5.0 or avg_days > 60 or res['loss_trades'] >= 2: status_tag, row_bg = "<span style='background:#fef9e7;color:#d35400;padding:3px 8px;border-radius:4px;font-weight:bold;'>🟡 주의 요망</span>", "#fcf3cf"
                else: status_tag, row_bg = "<span style='background:#e8f8f5;color:#117a65;padding:3px 8px;border-radius:4px;font-weight:bold;'>🟢 계속 유지</span>", "#ffffff"

                rc_html += f"<tr style='background-color:{row_bg};'><td style='padding:7px;border:1px solid #eaeded;font-weight:bold;'>{res['name']} ({t_code})</td><td style='padding:7px;border:1px solid #eaeded;'>{res['total_trades']}회 ({res['win_trades']}승/{res['loss_trades']}패)</td><td style='padding:7px;border:1px solid #eaeded;font-weight:bold;'>{res['win_rate']:.1f}%</td><td style='padding:7px;border:1px solid #eaeded;color:#c0392b;font-weight:bold;'>{format_money(res['net_profit'])}원</td><td style='padding:7px;border:1px solid #eaeded;'>{contrib:.1f}%</td><td style='padding:7px;border:1px solid #eaeded;'>{avg_days:.1f}일</td><td style='padding:7px;border:1px solid #eaeded;'>{status_tag}</td></tr>"
            rc_html += "</tbody></table></div></div>"
            st.markdown(rc_html, unsafe_allow_html=True)

            # 코어주식 현황판 (완벽 복원)
            core_cards_html = f"<div style='background:#f4ecf7;border:1px solid #9b59b6;border-radius:6px;padding:14px;margin-bottom:15px;'><h4 style='margin:0 0 8px 0;color:#8e44ad;font-size:14px;font-weight:bold;'>🍎 [종목별 코어주식(나무) 적립 현황판] (총 적립: {total_core_shares}주)</h4><div style='display:flex;flex-wrap:wrap;gap:8px;'>"
            for t_code, res in stock_results.items():
                core_cards_html += f"<div style='flex:1 1 180px;background:white;border:1px solid #d2b4de;border-top:4px solid #9b59b6;padding:10px;border-radius:6px;min-width:160px;'><b style='font-size:12px;color:#512e5f;'>{res['name']}</b><div style='font-size:11px;color:#2c3e50;margin-top:4px;'>• 적립 코어: <b>{res['core_shares']}주</b><br>• 평가금액: <b>{format_money(res['core_eval'])}원</b></div></div>"
            core_cards_html += "</div></div>"
            st.markdown(core_cards_html, unsafe_allow_html=True)

            # TOP 3 장기 체류 순위표 (완벽 복원)
            sorted_active = sorted(all_active_positions, key=lambda x: x['holding_days'], reverse=True)
            top3_cards_html = "<div style='background:#fdf2e9;border:1px solid #e67e22;border-radius:6px;padding:14px;margin-bottom:15px;'><h4 style='margin:0 0 8px 0;color:#d35400;font-size:14px;font-weight:bold;'>🚨 [장기 체류 요원 TOP 3 경보 순위표] (청산 검토 대상)</h4><div style='display:flex;flex-wrap:wrap;gap:8px;'>"
            for rank, p in enumerate(sorted_active[:3] if len(sorted_active) >= 3 else sorted_active, 1):
                badge_color, icon = ("#e74c3c", "🚨") if p['holding_days'] >= 90 else ("#e67e22", "🔥") if p['holding_days'] >= 60 else ("#f1c40f", "⚠️") if p['holding_days'] >= 20 else ("#2ecc71", "✅")
                loss_tag = f"<br><span style='color:#e74c3c;font-weight:bold;font-size:11px;'>🚨 손실주의</span>" if p['pnl_pct'] <= -15.0 else ""
                top3_cards_html += f"<div style='flex:1 1 200px;background:white;border:1px solid #fadbd8;border-top:4px solid {badge_color};padding:10px;border-radius:6px;min-width:180px;'><div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'><b style='font-size:12px;color:#7d6608;'>🏆 {rank}위 - {p['작전구역']}</b><span style='background:{badge_color};color:white;padding:1px 6px;border-radius:4px;font-size:10px;font-weight:bold;'>{icon} {p['holding_days']}일 체류</span></div><div style='font-size:11px;color:#2c3e50;'>• 요원명: <b>{p['요원명']}</b><br>• 평가손익: <b style='color:#c0392b;'>{p['평가손익']}</b>{loss_tag}</div></div>"
            top3_cards_html += "</div></div>"
            st.markdown(top3_cards_html, unsafe_allow_html=True)

            # 실시간 대기 요원 현황판 (12열 - '고점추적' 추가)
            active_html = f"<div style='background:#fdfefe;border:1px solid #3498db;border-radius:6px;padding:12px;margin-bottom:15px;'><h4 style='margin:0 0 10px 0;color:#2980b9;font-size:13px;'>🕵️ [현재 파견 대기 중인 요원 실시간 현황판] (총 {len(all_active_positions)}명 대기 중)</h4>"
            if len(all_active_positions) > 0:
                active_html += "<div style='overflow-x:auto;'><table style='width:100%;border-collapse:collapse;text-align:center;font-size:11px;min-width:600px;'><thead style='background-color:#ebf5fb;color:#2980b9;'><tr><th style='padding:6px;border:1px solid #d5dbdf;'>No.</th><th style='padding:6px;border:1px solid #d5dbdf;'>상태</th><th style='padding:6px;border:1px solid #d5dbdf;'>작전구역</th><th style='padding:6px;border:1px solid #d5dbdf;'>요원명</th><th style='padding:6px;border:1px solid #d5dbdf;'>파견일</th><th style='padding:6px;border:1px solid #d5dbdf;'>체류일수</th><th style='padding:6px;border:1px solid #d5dbdf;'>진입단가</th><th style='padding:6px;border:1px solid #d5dbdf;'>수량</th><th style='padding:6px;border:1px solid #d5dbdf;background:#f4ecf7;color:#8e44ad;'>🚀 고점추적(최고)</th><th style='padding:6px;border:1px solid #d5dbdf;background:#d4e6f1;'>진입총액</th><th style='padding:6px;border:1px solid #d5dbdf;'>현재평가금액</th><th style='padding:6px;border:1px solid #d5dbdf;'>평가손익</th></tr></thead><tbody>"
                for idx_ap, ap in enumerate(all_active_positions, 1):
                    pnl_color = "#c0392b" if ap['is_plus'] else "#2980b9"
                    row_bg, s_icon = ("#fdedec", "🚨") if ap['holding_days'] >= 90 else ("#fdebd0", "🔥") if ap['holding_days'] >= 60 else ("#fef9e7", "⚠️") if ap['holding_days'] >= 20 else ("#ffffff", "✅")
                    loss_badge = "<br><span style='background:#e74c3c;color:white;padding:2px 4px;border-radius:3px;font-size:10px;'>🚨위험</span>" if ap['pnl_pct'] <= -25.0 else ""
                    active_html += f"<tr style='background-color:{row_bg};'><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;color:#7f8c8d;'>{idx_ap}</td><td style='padding:5px;border:1px solid #eaeded;font-size:14px;'>{s_icon}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;'>{ap['작전구역']}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;'>{ap['요원명']}</td><td style='padding:5px;border:1px solid #eaeded;'>{ap['파견일']}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;'>{ap['holding_days']}일</td><td style='padding:5px;border:1px solid #eaeded;'>{ap['진입단가']}</td><td style='padding:5px;border:1px solid #eaeded;'>{ap['수량']}</td><td style='padding:5px;border:1px solid #eaeded;background:#fdf2e9;'>{ap['고점추적']}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;color:#1e8449;'>{ap['진입금액']}</td><td style='padding:5px;border:1px solid #eaeded;'>{ap['평가금액']}</td><td style='padding:5px;border:1px solid #eaeded;color:{pnl_color};font-weight:bold;'>{ap['평가손익']}{loss_badge}</td></tr>"
                active_html += "</tbody></table></div>"
            else: active_html += "<div style='font-size:11px;color:#7f8c8d;text-align:center;padding:5px;'>파견 대기 중인 요원이 없습니다.</div>"
            active_html += "</div>"
            st.markdown(active_html, unsafe_allow_html=True)

            # 웹 차트
            st.subheader("📈 오토파일럿 총자산 vs 시장 지수 비교 성장 곡선 (추세추종 로직)")
            chart_df = pd.DataFrame(index=combined_equity_df.index)
            chart_df[f'오토파일럿 총자산'] = combined_equity_df['Portfolio_Equity']
            chart_df['전액 현금 전략'] = bench_df['All_Cash']
            try: chart_df['KOSPI 지수'] = bench_df['KOSPI_Normalized']
            except: pass
            st.line_chart(chart_df)

            # 🌟 공식 매매 장부 (18열 - 최고가 달성 기록 추가)
            st.markdown("<div style='margin-top:25px;margin-bottom:8px;font-size:14px;font-weight:bold;color:#2c3e50;'>📜 박가이버 사령부 공식 매매 장부 (최고가 달성 기록 추가)</div>", unsafe_allow_html=True)
            table_html = "<div style='max-height:430px;overflow-y:auto;border:1px solid #d6dbdf;border-radius:6px;margin-bottom:15px;'><table style='width:100%;border-collapse:collapse;text-align:center;font-size:11px;min-width:1000px;'><thead style='position:sticky;top:0;background-color:#f2f4f4;color:#2c3e50;z-index:1;'><tr><th style='padding:6px;border:1px solid #d5dbdf;width:40px;'>No.</th><th style='padding:6px;border:1px solid #d5dbdf;'>요원</th><th style='padding:6px;border:1px solid #d5dbdf;'>작전 구역</th><th style='padding:6px;border:1px solid #d5dbdf;'>출격일</th><th style='padding:6px;border:1px solid #d5dbdf;background:#fdedec;'>청산일</th><th style='padding:6px;border:1px solid #d5dbdf;background:#e8f8f5;color:#117a65;'>진입단가</th><th style='padding:6px;border:1px solid #d5dbdf;background:#f4ecf7;color:#8e44ad;'>🚀 장중 최고가</th><th style='padding:6px;border:1px solid #d5dbdf;background:#fef9e7;color:#b7950b;'>최종 청산가</th><th style='padding:6px;border:1px solid #d5dbdf;'>진입일 등락률</th><th style='padding:6px;border:1px solid #d5dbdf;'>진입금액</th><th style='padding:6px;border:1px solid #d5dbdf;'>매도금액</th><th style='padding:6px;border:1px solid #d5dbdf;'>총 수수료·세금</th><th style='padding:6px;border:1px solid #d5dbdf;'>등락폭</th><th style='padding:6px;border:1px solid #d5dbdf;'>소요기간</th><th style='padding:6px;border:1px solid #d5dbdf;'>순수익률</th><th style='padding:6px;border:1px solid #d5dbdf;'>정산내역</th><th style='padding:6px;border:1px solid #d5dbdf;'>구분 (청산사유)</th><th style='padding:6px;border:1px solid #d5dbdf;'>스노우볼 레벨</th></tr></thead><tbody>"

            for idx_t, t in enumerate(all_matched_trades, 1):
                row_no = len(all_matched_trades) - idx_t + 1
                row_bg, text_color = ("#fdedec", "#c0392b") if t['is_win'] else ("#ebf5fb", "#2980b9")
                table_html += f"<tr style='background-color:{row_bg};'><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;color:#7f8c8d;'>{row_no}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;'>{t['요원']}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;color:#2980b9;'>{t['작전구역']}</td><td style='padding:5px;border:1px solid #eaeded;'>{t['출격일']}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;color:#c0392b;'>{t['복귀일']}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;color:#117a65;'>{t['진입단가']}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;color:#8e44ad;background:#fdf2e9;'>{t.get('최고달성가','-')}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;color:#d35400;'>{t['청산단가']}</td><td style='padding:5px;border:1px solid #eaeded;'>{t['진입일 등락률']}</td><td style='padding:5px;border:1px solid #eaeded;'>{t['진입금액']}</td><td style='padding:5px;border:1px solid #eaeded;'>{t['매도금액']}</td><td style='padding:5px;border:1px solid #eaeded;color:#c0392b;'>{t['총수수료·세금']}</td><td style='padding:5px;border:1px solid #eaeded;color:{text_color};font-weight:bold;'>{t['등락폭']}</td><td style='padding:5px;border:1px solid #eaeded;'>{t['소요기간']}</td><td style='padding:5px;border:1px solid #eaeded;color:{text_color};font-weight:bold;'>{t['순수익률']}</td><td style='padding:5px;border:1px solid #eaeded;color:{text_color};font-weight:bold;'>{t['정산내역']}</td><td style='padding:5px;border:1px solid #eaeded;font-weight:bold;'>{t['구분']}</td><td style='padding:5px;border:1px solid #eaeded;color:#d35400;font-weight:bold;'>{t.get('스노우볼 레벨','-')}</td></tr>"

            table_html += "</tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)

            # CSV 다운로드
            df_export = pd.DataFrame([{k: v for k, v in t.items() if k not in ['is_win', 'raw_profit', 'exit_date']} for t in all_matched_trades])
            csv_buffer = io.StringIO()
            df_export.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
            st.download_button("📜 엑셀(CSV) 다운로드 (V10.39 풀버전)", data=csv_buffer.getvalue().encode('utf-8-sig'), file_name=f"박가이버사령부_V10.39_{selected_strategy}.csv", mime="text/csv")
else:
    st.info("👈 왼쪽 사이드바에서 [무제한 추세추종 엔진] 옵션을 켜고 [▶️ 작전 개시!] 버튼을 눌러주세요.")
