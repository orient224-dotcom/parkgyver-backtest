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
st.set_page_config(page_title="박가이버 사령부 V10.38 (정밀엔진)", layout="wide", page_icon="🎛️")

def format_money(num):
    try:
        return f"{int(round(float(num))):,}"
    except:
        return str(num)

# ⚡ 데이터 고속 로딩을 위한 캐싱 (Speed Optimization)
@st.cache_data(ttl=3600)
def load_stock_data(ticker, start_date, end_date):
    try:
        return fdr.DataReader(ticker, start_date, end_date)
    except:
        return pd.DataFrame()

# --- 2. 사이드바 조종간 ---
st.sidebar.title("🎛️ 박가이버 사령부 V10.38")
st.sidebar.caption("은퇴 과수원 에디션 - 정밀 백테스트 엔진 탑재")

# 🎯 사령부 정예 종목 데이터베이스
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

# 🌟 V10.38 신규: 종목별 맞춤 중력선 설정부
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

# 🌟 V10.38 신규: 수익 보존 안전망
profit_preserve_active = st.sidebar.checkbox("🛡️ 수익 보존망 (+5% 도달 시 최소 +3% 락온)", value=True)

run_btn = st.sidebar.button("▶️ 박가이버 사령부 V10.38 작전 개시!", type="primary")

# --- 🚨 오후 3:20 PM 실전 신호등 모듈 ---
st.markdown("<div style='background:#154360;color:white;padding:12px;border-radius:6px;margin-bottom:12px;'><h3 style='margin:0;font-size:16px;'>🚨 [오후 3:20 PM 실전 작전 지시서] 실시간 신호등 통제실</h3></div>", unsafe_allow_html=True)

live_col1, live_col2 = st.columns([1, 3])
with live_col1:
    scan_live_btn = st.button("📡 [3시 20분] 실시간 시장 스캔 실행", type="primary", use_container_width=True)
with live_col2:
    st.caption("💡 당일 등락률과 V10.38 맞춤 타점을 적용해 즉시 실행할 지시서를 생성합니다.")

if scan_live_btn:
    if len(tickers_list) == 0:
        st.warning("⚠️ 종목을 먼저 선택해 주세요.")
    elif stock_alloc_pct * len(tickers_list) > 100.0:
        st.error("❌ 설정 오류: 비중 총합이 100%를 초과합니다.")
    else:
        with st.spinner("🔍 실시간 시세 및 안전 조건을 정밀 분석 중입니다..."):
            buy_orders, hold_stocks = [], []
            start_2mo = (datetime.datetime.today() - relativedelta(months=2)).strftime('%Y-%m-%d')
            
            # 실시간 데이터도 캐싱 함수 이용
            k_hist = load_stock_data('KS11', start_2mo, None)
            kd_hist = load_stock_data('KQ11', start_2mo, None)
            
            try:
                k_hist['MA20'] = k_hist['Close'].rolling(20).mean()
                kd_hist['MA20'] = kd_hist['Close'].rolling(20).mean()
                k_curr, k_ma20 = float(k_hist['Close'].iloc[-1]), float(k_hist['MA20'].iloc[-1])
                kd_curr, kd_ma20 = float(kd_hist['Close'].iloc[-1]), float(kd_hist['MA20'].iloc[-1])
                is_ks_safe = (k_curr >= k_ma20)
                is_kd_safe = (kd_curr >= kd_ma20)
            except:
                is_ks_safe = is_kd_safe = True

            if use_market_ma20_filter:
                warn_msg = []
                if not is_ks_safe: warn_msg.append("KOSPI 20일선 붕괴")
                if not is_kd_safe: warn_msg.append("KOSDAQ 20일선 붕괴")
                if warn_msg: st.warning(f"🚨 **[기상 특보] 지수 폭락 경보! ({', '.join(warn_msg)})** - 신규 진입 차단")

            for idx, t_code in enumerate(tickers_list):
                s_name = names_list[idx]
                is_ks = t_code in KS_CODES
                target_drop_rate = custom_drop_rates[t_code]
                
                try:
                    hist = load_stock_data(t_code, start_2mo, None)
                    if len(hist) >= 20:
                        hist['MA10'] = hist['Close'].rolling(window=10).mean()
                        hist['MA20'] = hist['Close'].rolling(window=20).mean()
                        
                        prev_close = float(hist['Close'].iloc[-2])
                        curr_price = float(hist['Close'].iloc[-1])
                        curr_ma10, curr_ma20, prev_ma20 = float(hist['MA10'].iloc[-1]), float(hist['MA20'].iloc[-1]), float(hist['MA20'].iloc[-2])
                        
                        daily_ret = ((curr_price - prev_close) / prev_close) * 100

                        if daily_ret <= target_drop_rate:
                            is_above_ma20 = (curr_price >= curr_ma20)
                            is_ma20_rising = (curr_ma20 > prev_ma20)
                            is_ma10_aligned = (curr_ma10 >= curr_ma20)
                            
                            market_safe = is_ks_safe if is_ks else is_kd_safe
                            if not use_market_ma20_filter: market_safe = True
                            
                            trend_safe = True
                            if use_trend_filter and not (is_ma20_rising and is_ma10_aligned): trend_safe = False
                            
                            if ((not use_ma20_filter) or is_above_ma20) and market_safe and trend_safe:
                                buy_budget = (total_capital * (stock_alloc_pct / 100.0)) / max_agents
                                est_shares = max(int(buy_budget // curr_price), 1)
                                buy_orders.append({'종목': s_name, '코드': t_code, '현재가': format_money(curr_price) + "원", '당일등락률': f"{daily_ret:+.2f}%", '추천수량': f"{est_shares}주", '예상주문금액': format_money(est_shares * curr_price) + "원"})
                            else:
                                reason = "지수 20일선 붕괴" if use_market_ma20_filter and not market_safe else ("20일선 꺾임/역배열" if use_trend_filter and not trend_safe else "개별 20일선 하회")
                                hold_stocks.append({'종목': s_name, '코드': t_code, '현재가': format_money(curr_price) + "원", '당일등락률': f"{daily_ret:+.2f}%", '상태': f"대기 ({reason})"})
                        else:
                            hold_stocks.append({'종목': s_name, '코드': t_code, '현재가': format_money(curr_price) + "원", '당일등락률': f"{daily_ret:+.2f}%", '상태': f"대기 (목표 타점 {target_drop_rate}% 미달)"})
                except Exception as e:
                    pass

            st.markdown("---")
            if buy_orders:
                st.markdown("<h4 style='color:#c0392b;margin-bottom:8px;'>🔴 [오늘 시장가 매수 실행 대상 종목]</h4>", unsafe_allow_html=True)
                for b in buy_orders: st.error(f"🎯 **{b['종목']} ({b['코드']})** | 현재가: **{b['현재가']}** ({b['당일등락률']}) ➔ **1호 요원 매수 발사!** (수량: **{b['추천수량']}** / 금액: {b['예상주문금액']})")
            else:
                st.success("🟢 **[매수 신호 없음]** 출격 조건을 만족하는 종목이 없습니다. 현금을 안전하게 유지합니다.")
            if hold_stocks:
                with st.expander("⚪ [오늘 관망/대기 종목 현황 보기]"):
                    st.table(pd.DataFrame(hold_stocks)[['종목', '코드', '현재가', '당일등락률', '상태']])
st.markdown("---")

# --- 3. 메인 백테스트 연산 엔진 (정밀 로직 탑재) ---
if run_btn or 'calculated' in st.session_state:
    st.session_state['calculated'] = True
    if not tickers_list: st.warning("⚠️ 작전을 수행할 종목을 선택해 주세요."); st.stop()
    if stock_alloc_pct * len(tickers_list) > 100.0: st.error("❌ 비중 총합이 100%를 초과합니다."); st.stop()

    buy_fee_rate, sell_tax_rate = buy_fee_val / 100.0, sell_tax_val / 100.0
    emergency_threshold = -abs(emergency_cut_pct) if emergency_cut_active else -999.0
    strategy_names_map = {'3tier': '3단 밸런스 과수원 전략', 'full_cash': '풀 현금 복리 재투자 전략', 'equal_alloc': '균등 배분 고정 전략'}
    current_strategy_name = strategy_names_map.get(selected_strategy, '전략')

    with st.spinner("📡 [박가이버 사령부 V10.38] 고가/저가 정밀 시뮬레이션 가동 중..."):
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
            target_drop_rate = custom_drop_rates[ticker]
            
            df = load_stock_data(ticker, start_str, end_str).copy()
            if df.empty: continue
            
            df['Prev_Close'] = df['Close'].shift(1)
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
                
                ma10 = float(row['MA10']) if not pd.isna(row['MA10']) else close
                ma20, ma20_prev = float(row['MA20']) if not pd.isna(row['MA20']) else close, float(row['MA20_prev']) if not pd.isna(row['MA20_prev']) else close
                ma60, ma120 = float(row['MA60']) if not pd.isna(row['MA60']) else close, float(row['MA120']) if not pd.isna(row['MA120']) else close
                date_str = date.strftime('%Y-%m-%d')

                # --- 정밀 매도 (장중 High/Low 반영 및 수익 보존) ---
                current_batch_trades = []
                positions_to_keep = []
                batch_reinvest_profit = 0.0

                for pos in positions:
                    if high > pos.get('max_price', pos['entry_price']):
                        pos['max_price'] = high
                        
                    target_price = pos['entry_price'] * (1 + pos['target_ret']/100)
                    stop_price = pos['entry_price'] * (1 + emergency_threshold/100) if emergency_cut_active else 0
                    
                    # 수익 보존 로직 (+5% 도달 시 +3% 락온)
                    safety_net_price = pos['entry_price'] * 1.03
                    if profit_preserve_active and pos.get('max_price', pos['entry_price']) >= pos['entry_price'] * 1.05:
                        pos['safety_active'] = True
                        
                    if pos.get('safety_active', False) and stop_price < safety_net_price:
                        stop_price = safety_net_price
                        
                    sell_price = None
                    sell_reason = ""
                    
                    if high >= target_price:
                        sell_price = target_price
                        sell_reason = "🎯 목표 익절"
                    elif low <= stop_price and stop_price > 0:
                        sell_price = stop_price
                        sell_reason = "🛡️ 수익 보존(+3%)" if pos.get('safety_active', False) else f"🚨 비상 탈출"

                    if sell_price:
                        shares = pos['shares']
                        buy_amount_net = (shares * pos['entry_price']) * (1 + buy_fee_rate)
                        sell_amount_net = (shares * sell_price) * (1 - sell_tax_rate)
                        trade_fee_total = (shares * pos['entry_price'] * buy_fee_rate) + (shares * sell_price * sell_tax_rate)
                        
                        stock_total_fees += trade_fee_total
                        total_fees_paid_all += trade_fee_total
                        profit_krw = sell_amount_net - buy_amount_net
                        ret = (profit_krw / buy_amount_net) * 100

                        reinvest_amt = profit_krw
                        if profit_krw > 0:
                            if selected_strategy == '3tier':
                                reinvest_amt = profit_krw * 0.60
                                reserve_cash += (profit_krw * 0.20)
                                core_shares += int((profit_krw * 0.20) // sell_price)
                            elif selected_strategy != 'full_cash':
                                reinvest_amt = 0.0

                        batch_reinvest_profit += reinvest_amt
                        total_trades += 1
                        is_win = profit_krw >= 0
                        if is_win: win_trades += 1
                        else: loss_trades += 1
                        
                        current_batch_trades.append({
                            '요원': pos['name'], '작전구역': s_name, '종목코드': ticker,
                            '출격일': pos['entry_date'], '진입일 등락률': f"{pos['entry_return']:+.2f}%",
                            '진입단가': format_money(pos['entry_price']) + "원", '진입금액': format_money(buy_amount_net) + "원",
                            '복귀일': date_str, '청산일 등락률': f"{((close - prev_close)/prev_close*100):+.2f}%",
                            '청산단가': format_money(sell_price) + "원", '매도금액': format_money(sell_amount_net) + "원",
                            '총수수료·세금': format_money(trade_fee_total) + "원",
                            '등락폭': f"{'+' if sell_price >= pos['entry_price'] else ''}{format_money(sell_price - pos['entry_price'])}원 ({ret:+.2f}%)",
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
                        threshold = current_capital * 0.10
                        if step_progress >= threshold:
                            level_up_count += 1; current_capital += threshold; step_progress = 0.0
                            event_effect_str = f"🚀 [레벨업 UP! Lv.{level_up_count}]"
                        elif step_progress <= -threshold and current_capital > s_capital:
                            step_down_count += 1; current_capital -= threshold; step_progress = 0.0
                            event_effect_str = f"📉 [스텝다운 DOWN]"

                    for t in current_batch_trades:
                        t['스노우볼 레벨'] = f"Lv.{max(1, level_up_count + 1)}" + (f" <br><span style='color:#c0392b; font-size:9px;'>{event_effect_str}</span>" if event_effect_str else "")
                    matched_trades.extend(current_batch_trades)

                # --- 정밀 매수 (장중 Low 및 맞춤 타점 반영) ---
                drop_target_price = prev_close * (1 + target_drop_rate / 100)
                if not pd.isna(row['Prev_Close']) and low <= drop_target_price and len(positions) < max_agents:
                    market_safe = True
                    if use_market_ma20_filter:
                        try:
                            bench = kospi_df if is_ks else kosdaq_df
                            if date in bench.index and float(bench.loc[date, 'Close']) < float(bench.loc[date, 'MA20']): market_safe = False
                        except: pass

                    is_above_ma20 = (close >= ma20)
                    trend_safe = True if not use_trend_filter else (ma20 > ma20_prev and ma10 >= ma20)
                    
                    if ((not use_ma20_filter) or is_above_ma20) and market_safe and trend_safe:
                        agent_counter += 1; total_agent_counter += 1
                        scale_ratio = current_capital / s_capital if selected_strategy != 'equal_alloc' else 1.0
                        shares = max(int((s_capital / max_agents * scale_ratio) // drop_target_price), 1)

                        is_super_bull = (close > ma20) and (ma20 > ma60) and (ma60 > ma120)
                        is_super_bear = (close < ma20) and (ma20 < ma60) and (ma60 < ma120)

                        positions.append({
                            'name': f"{s_name}-{agent_counter}호", 'entry_price': drop_target_price,
                            'entry_date': date_str, 'entry_dt': date, 'entry_return': target_drop_rate,
                            'shares': shares, 'target_ret': 15.0 if is_super_bull else (5.0 if is_super_bear else 10.0),
                            'max_price': drop_target_price, 'safety_active': False
                        })

                active_eval = sum(p['shares'] * close for p in positions)
                stock_equity = s_capital + sum([t['raw_profit'] for t in matched_trades]) + reserve_cash + (core_shares * close) + active_eval - sum(p['shares']*p['entry_price'] for p in positions)
                daily_log.append({'Date': date, 'Stock_Equity': stock_equity})

            for p in positions:
                cur_eval_p = p['shares'] * float(df['Close'].iloc[-1])
                pnl_p = cur_eval_p - (p['shares'] * p['entry_price'])
                all_active_positions.append({
                    '작전구역': s_name, '요원명': p['name'], '파견일': p['entry_date'], 'entry_dt': p['entry_dt'], 'holding_days': (end_date - p['entry_dt']).days,
                    '진입단가': format_money(p['entry_price']) + "원", '수량': f"{p['shares']}주", '진입금액': format_money(p['shares'] * p['entry_price']) + "원",
                    '평가금액': format_money(cur_eval_p) + "원", '평가손익': f"{'+' if pnl_p >= 0 else ''}{format_money(pnl_p)}원 ({(pnl_p / (p['shares'] * p['entry_price']) * 100):+.2f}%)",
                    'is_plus': pnl_p >= 0, 'pnl_val': pnl_p, 'pnl_pct': (pnl_p / (p['shares'] * p['entry_price'])) * 100
                })

            if daily_log: combined_equity_df[s_name] = pd.DataFrame(daily_log).set_index('Date')['Stock_Equity']

            stock_results[ticker] = {
                'name': s_name, 'total_trades': total_trades, 'win_trades': win_trades, 'loss_trades': loss_trades,
                'win_rate': (win_trades / total_trades * 100) if total_trades > 0 else 0,
                'net_profit': sum([t['raw_profit'] for t in matched_trades]),
                'reserve_cash': reserve_cash, 'core_shares': core_shares, 'core_eval': core_shares * float(df['Close'].iloc[-1]),
                'active_eval': sum(p['shares'] * float(df['Close'].iloc[-1]) for p in positions), 'active_count': len(positions),
                'total_cycles': total_cycles, 'full_launch_cycles': full_launch_cycles,
                'level_up_count': level_up_count, 'step_down_count': step_down_count
            }
            all_matched_trades.extend(matched_trades)

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
            total_trades_all = sum([res['total_trades'] for res in stock_results.values()])
            win_trades_all = sum([res['win_trades'] for res in stock_results.values()])
            loss_trades_all = sum([res['loss_trades'] for res in stock_results.values()])
            overall_win_rate = (win_trades_all / total_trades_all * 100) if total_trades_all > 0 else 0
            total_reserve_cash = sum([res['reserve_cash'] for res in stock_results.values()])
            total_core_eval = sum([res['core_eval'] for res in stock_results.values()])
            total_core_shares = sum([res['core_shares'] for res in stock_results.values()])
            total_active_eval = sum([res['active_eval'] for res in stock_results.values()])
            
            all_matched_trades.sort(key=lambda x: x['exit_date'], reverse=True)
            total_cash_all = portfolio_eq.iloc[-1] - total_active_eval - total_core_eval

            # --- 4. 백테스트 결과 UI 출력 ---
            st.markdown(f"<div style='background:#1b4f72;color:white;padding:12px 15px;border-radius:6px;margin-bottom:15px;'><h3 style='margin:0;font-size:16px;'>📊 [백테스트 종합 분석] 전략: {current_strategy_name} (정밀 체결 엔진 가동)</h3></div>", unsafe_allow_html=True)
            
            st.markdown(f"<div style='display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px;'><div style='flex:1 1 125px;background:#e8f8f5;padding:12px;border-radius:6px;border-left:5px solid #1abc9c;min-width:110px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>🎯 통합 청산 승률</span><div style='font-size:17px;font-weight:900;color:#2c3e50;margin:4px 0;'>{overall_win_rate:.1f}%</div><span style='font-size:10px;color:#16a085;'>익절 {win_trades_all} / 손절 {loss_trades_all}</span></div><div style='flex:1 1 115px;background:#fef5e7;padding:12px;border-radius:6px;border-left:5px solid #d35400;min-width:105px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>🚀 총자산 ({portfolio_total_return:+.1f}%)</span><div style='font-size:13px;font-weight:900;color:#2c3e50;margin:4px 0;'>{format_money(portfolio_eq.iloc[-1])}원</div><span style='font-size:10px;color:#7f8c8d;'>현금: {format_money(total_cash_all)}원</span></div><div style='flex:1 1 125px;background:#fadbd8;padding:12px;border-radius:6px;border-left:5px solid #c0392b;min-width:110px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>📉 최대 낙폭지수 (MDD)</span><div style='font-size:17px;font-weight:900;color:#78281f;margin:4px 0;'>{max_drawdown:.2f}%</div></div></div>", unsafe_allow_html=True)

            rc_html = f"<div style='background:#fdfefe;border:1px solid #1abc9c;border-radius:6px;padding:14px;margin-bottom:15px;'><h4 style='margin:0 0 10px 0;color:#117a65;font-size:14px;font-weight:bold;'>📊 [종목별 종합 성적표] 옥석 가리기 현황판</h4><div style='overflow-x:auto;'><table style='width:100%;border-collapse:collapse;text-align:center;font-size:12px;min-width:650px;'><thead style='background-color:#e8f8f5;color:#117a65;'><tr><th style='padding:8px;border:1px solid #d5dbdf;'>종목명 (코드)</th><th style='padding:8px;border:1px solid #d5dbdf;'>총 매매 (승/패)</th><th style='padding:8px;border:1px solid #d5dbdf;'>승률</th><th style='padding:8px;border:1px solid #d5dbdf;'>누적 순수익</th><th style='padding:8px;border:1px solid #d5dbdf;'>수익 기여도</th></tr></thead><tbody>"
            for t_code, res in stock_results.items():
                contrib = (res['net_profit'] / total_net_profit_all * 100) if total_net_profit_all > 0 else 0
                rc_html += f"<tr><td style='padding:7px;border:1px solid #eaeded;font-weight:bold;'>{res['name']}</td><td style='padding:7px;border:1px solid #eaeded;'>{res['total_trades']}회 ({res['win_trades']}승/{res['loss_trades']}패)</td><td style='padding:7px;border:1px solid #eaeded;font-weight:bold;'>{res['win_rate']:.1f}%</td><td style='padding:7px;border:1px solid #eaeded;color:#c0392b;font-weight:bold;'>{format_money(res['net_profit'])}원</td><td style='padding:7px;border:1px solid #eaeded;'>{contrib:.1f}%</td></tr>"
            rc_html += "</tbody></table></div></div>"
            st.markdown(rc_html, unsafe_allow_html=True)

            st.subheader("📈 오토파일럿 총자산 vs 시장 지수 비교 성장 곡선")
            chart_df = pd.DataFrame(index=combined_equity_df.index)
            chart_df[f'총자산 ({current_strategy_name})'] = combined_equity_df['Portfolio_Equity']
            chart_df['전액 현금'] = bench_df['All_Cash']
            try: chart_df['KOSPI 지수'] = bench_df['KOSPI_Normalized']
            except: pass
            st.line_chart(chart_df)

            st.markdown("<div style='margin-top:25px;margin-bottom:8px;font-size:14px;font-weight:bold;color:#2c3e50;'>📜 박가이버 사령부 공식 매매 장부 (정밀 체결)</div>", unsafe_allow_html=True)
            table_html = "<div style='max-height:430px;overflow-y:auto;border:1px solid #d6dbdf;border-radius:6px;margin-bottom:15px;'><table style='width:100%;border-collapse:collapse;text-align:center;font-size:11px;'><thead style='position:sticky;top:0;background-color:#f2f4f4;color:#2c3e50;'><tr><th>요원</th><th>출격일</th><th>복귀일</th><th>매수가</th><th>매도가</th><th>순수익률</th><th>정산내역</th><th>구분</th></tr></thead><tbody>"
            for t in all_matched_trades:
                row_bg = "#fdedec" if t['is_win'] else "#ebf5fb"
                table_html += f"<tr style='background-color:{row_bg};'><td>{t['요원']}</td><td>{t['출격일']}</td><td>{t['복귀일']}</td><td>{t['진입단가']}</td><td>{t['청산단가']}</td><td style='font-weight:bold;color:#c0392b;'>{t['순수익률']}</td><td>{t['정산내역']}</td><td style='font-weight:bold;'>{t['구분']}</td></tr>"
            table_html += "</tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)

            df_export = pd.DataFrame([{k: v for k, v in t.items() if k not in ['is_win', 'raw_profit', 'exit_date']} for t in all_matched_trades])
            csv_buffer = io.StringIO()
            df_export.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
            st.download_button("📜 엑셀 다운로드", data=csv_buffer.getvalue().encode('utf-8-sig'), file_name=f"박가이버_V10.38_정밀백테스트.csv", mime="text/csv")
else:
    st.info("👈 왼쪽 사이드바에서 종목별 타점 확인 후 [▶️ 작전 개시!] 버튼을 눌러주세요.")
