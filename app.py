import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import datetime
from dateutil.relativedelta import relativedelta
import io
import warnings
import plotly.graph_objects as go

warnings.filterwarnings('ignore')

# --- 1. 페이지 기본 설정 ---
st.set_page_config(page_title="박가이버 사령부 V10.56 (연속손절 방어)", layout="wide", page_icon="🎛️")

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

# ⚡ 대한민국 전 종목(2,500개) DB 고속 캐싱 엔진
@st.cache_data(ttl=86400)
def get_krx_stock_database():
    try:
        df_krx = fdr.StockListing('KRX')
        df_krx['Code'] = df_krx['Code'].astype(str).str.zfill(6)
        df_krx['Market'] = df_krx.get('Market', 'KOSPI')
        df_krx['Label'] = df_krx['Name'] + " (" + df_krx['Code'] + ") - " + df_krx['Market']
        
        stock_dict = {}
        for _, row in df_krx.iterrows():
            stock_dict[row['Label']] = {
                'code': row['Code'],
                'name': row['Name'],
                'market': row['Market']
            }
        return stock_dict
    except:
        fallback = {
            "삼성전자 (005930) - KOSPI": {"code": "005930", "name": "삼성전자", "market": "KOSPI"},
            "한미반도체 (042700) - KOSDAQ": {"code": "042700", "name": "한미반도체", "market": "KOSDAQ"},
            "주성엔지니어링 (036930) - KOSDAQ": {"code": "036930", "name": "주성엔지니어링", "market": "KOSDAQ"},
            "제주반도체 (080220) - KOSDAQ": {"code": "080220", "name": "제주반도체", "market": "KOSDAQ"},
            "두산에너빌리티 (034020) - KOSPI": {"code": "034020", "name": "두산에너빌리티", "market": "KOSPI"},
            "HD현대일렉트릭 (267260) - KOSPI": {"code": "267260", "name": "HD현대일렉트릭", "market": "KOSPI"},
            "실리콘투 (257720) - KOSDAQ": {"code": "257720", "name": "실리콘투", "market": "KOSDAQ"},
            "리노공업 (058470) - KOSDAQ": {"code": "058470", "name": "리노공업", "market": "KOSDAQ"},
            "DN오토모티브 (007340) - KOSPI": {"code": "007340", "name": "DN오토모티브", "market": "KOSPI"}
        }
        return fallback

# --- 2. 사이드바 조종간 ---
st.sidebar.title("🎛️ 박가이버 사령부 V10.56")
st.sidebar.caption("은퇴 과수원 에디션 - 연속 손절 감지 및 진입금지 권고")

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 HTS급 전 종목 실시간 검색기")

stock_db = get_krx_stock_database()
all_labels = list(stock_db.keys())

default_targets = ['삼성전자 (005930)', '한미반도체 (042700)', '주성엔지니어링 (036930)', '제주반도체 (080220)', '두산에너빌리티 (034020)']
default_keys = [k for k in all_labels if any(t in k for t in default_targets)]
if not default_keys:
    default_keys = all_labels[:5]

selected_labels = st.sidebar.multiselect(
    "종목명 또는 6자리 코드로 검색하여 담으세요:",
    options=all_labels,
    default=default_keys
)

tickers_list, names_list, markets_list = [], [], []
for label in selected_labels:
    info = stock_db[label]
    tickers_list.append(info['code'])
    names_list.append(info['name'])
    markets_list.append(info['market'])

raw_tickers = ", ".join([f"{n}({c})" for n, c in zip(names_list, tickers_list)])

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
use_trailing_stop = st.sidebar.checkbox("🚀 추세추종 가동 (고정 익절 무시)", value=True)
trailing_start_pct = st.sidebar.number_input("추적 레이더 가동 기준선 (%)", value=5.0, step=1.0)
trailing_pullback_pct = st.sidebar.number_input("고점 대비 청산 하락률 (%)", value=7.0, step=0.5)

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 종목별 맞춤 급락 타점")
custom_drop_rates = {}
for s_name, t_code, mkt in zip(names_list, tickers_list, markets_list):
    is_ks = (mkt == 'KOSPI' or 'KOSPI' in str(mkt))
    default_rate = -2.5 if is_ks else -5.0
    custom_drop_rates[t_code] = st.sidebar.number_input(f"{s_name} ({mkt}) 타점 (%)", value=default_rate, step=0.5, format="%.1f")

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ 리스크 제어 (안전장치 & 쿨다운)")
use_market_ma20_filter = st.sidebar.checkbox("🚨 지수 20일선 붕괴 감시 락", value=True)
use_kospi_crash_filter = st.sidebar.checkbox("⚡ 코스피 당일 급락 감시 락", value=True)
kospi_crash_threshold = st.sidebar.number_input("코스피 폭락 기준선 (%)", value=-3.0, step=0.5, max_value=-0.5, min_value=-10.0, format="%.1f")
use_ma20_filter = st.sidebar.checkbox("🛡️ 개별주 20일선 지지 필터", value=True)
use_trend_filter = st.sidebar.checkbox("📈 10일선/20일선 정배열 필터", value=True)
emergency_cut_active = st.sidebar.checkbox("🚨 비상 탈출 손절 (Emergency Cut)", value=True)
emergency_cut_pct = st.sidebar.number_input("비상 탈출 손실 기준선 (%)", value=15.0, step=1.0, min_value=10.0, max_value=20.0)

st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
use_cooldown = st.sidebar.checkbox("❄️ 손절 발생 시 연쇄 진입 금지 (쿨다운 가동)", value=True)
cooldown_days = st.sidebar.number_input("손절 후 쿨다운 유지 기간 (영업일)", value=10, step=1, min_value=1, max_value=30)

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 AI 자동 최적화 탐색기")
tune_btn = st.sidebar.button("🔍 AI 오토튜너 가동!", type="secondary")
run_btn = st.sidebar.button("▶️ 박가이버 사령부 V10.56 작전 개시!", type="primary")

# --- 🤖 AI 오토튜너 작동 모듈 ---
if tune_btn:
    if not tickers_list:
        st.warning("⚠️ 탐색할 종목을 먼저 선택해 주세요.")
        st.stop()
    
    st.markdown("<h3 style='color:#2c3e50; margin-bottom: 20px;'>🤖 [AI 오토튜너] 25가지 가상 시나리오 고속 탐색 중...</h3>", unsafe_allow_html=True)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    end_date = datetime.datetime.today()
    start_date = end_date - relativedelta(years=years + 1)
    start_str, end_str = start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    kospi_df = load_stock_data('KS11', start_str, end_str)
    kosdaq_df = load_stock_data('KQ11', start_str, end_str)
    if not kospi_df.empty: 
        kospi_df['MA20'] = kospi_df['Close'].rolling(20).mean()
        kospi_df['Daily_Return'] = kospi_df['Close'].pct_change() * 100
    if not kosdaq_df.empty: 
        kosdaq_df['MA20'] = kosdaq_df['Close'].rolling(20).mean()
        
    cached_data = {}
    for t in tickers_list:
        df = load_stock_data(t, start_str, end_str).copy()
        if not df.empty:
            df['Prev_Close'] = df['Close'].shift(1)
            df['Daily_Return'] = df['Close'].pct_change() * 100
            df['MA10'] = df['Close'].rolling(10).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            df['MA60'] = df['Close'].rolling(60).mean()
            df['MA120'] = df['Close'].rolling(120).mean()
            df['MA20_prev'] = df['MA20'].shift(1)
            cached_data[t] = df[df.index >= (end_date - relativedelta(years=years)).strftime('%Y-%m-%d')].copy()

    cut_options = [10.0, 12.0, 15.0, 18.0, 20.0]
    cd_options = [0, 3, 5, 7, 10]
    total_iters = len(cut_options) * len(cd_options)
    iter_cnt = 0
    results = []
    buy_fee_rate, sell_tax_rate = buy_fee_val / 100.0, sell_tax_val / 100.0

    for cut in cut_options:
        for cd in cd_options:
            iter_cnt += 1
            status_text.text(f"시뮬레이션 가동 중... {iter_cnt}/{total_iters} (테스트 조건: 손절 -{cut:.0f}%, 쿨다운 {cd}일)")
            progress_bar.progress(iter_cnt / total_iters)
            
            emergency_threshold = -abs(cut)
            sim_use_cd = True if cd > 0 else False
            total_net_profit_all = 0
            win_trades_all = 0
            total_trades_all = 0
            
            for idx, ticker in enumerate(tickers_list):
                mkt = markets_list[idx]
                is_ks = (mkt == 'KOSPI' or 'KOSPI' in str(mkt))
                s_capital = total_capital * (stock_alloc_pct / 100.0)
                target_drop_rate = custom_drop_rates.get(ticker, -5.0)
                df = cached_data.get(ticker)
                if df is None or df.empty: continue
                
                positions = []
                current_capital = float(s_capital)
                cooldown_remaining = 0
                
                for date, row in df.iterrows():
                    if cooldown_remaining > 0: cooldown_remaining -= 1
                    
                    close = float(row['Close'])
                    prev_close = float(row['Prev_Close']) if not pd.isna(row['Prev_Close']) else close
                    high = float(row['High']) if 'High' in row and not pd.isna(row['High']) else close
                    low = float(row['Low']) if 'Low' in row and not pd.isna(row['Low']) else close
                    ma10 = float(row['MA10']) if not pd.isna(row['MA10']) else close
                    ma20 = float(row['MA20']) if not pd.isna(row['MA20']) else close
                    ma20_prev = float(row['MA20_prev']) if not pd.isna(row['MA20_prev']) else close
                    
                    if pd.isna(row['Daily_Return']): continue
                    
                    positions_to_keep = []
                    batch_reinvest_profit = 0.0
                    
                    for pos in positions:
                        if high > pos.get('max_price', pos['entry_price']): pos['max_price'] = high
                        sell_price = None
                        stop_price = pos['entry_price'] * (1 + emergency_threshold/100)
                        
                        if use_trailing_stop:
                            if ((pos['max_price'] - pos['entry_price']) / pos['entry_price']) * 100 >= trailing_start_pct: pos['trailing_active'] = True
                            pullback_price = pos['max_price'] * (1 - trailing_pullback_pct / 100)
                            if pos.get('trailing_active', False) and low <= pullback_price: sell_price = pullback_price
                            elif low <= stop_price and stop_price > 0: sell_price = stop_price
                        else:
                            target_price = pos['entry_price'] * (1 + pos['target_ret']/100)
                            if high >= target_price: sell_price = target_price
                            elif low <= stop_price and stop_price > 0: sell_price = stop_price
                            
                        if sell_price:
                            shares = pos['shares']
                            buy_amount_net = (shares * pos['entry_price']) * (1 + buy_fee_rate)
                            sell_amount_net = (shares * sell_price) * (1 - sell_tax_rate)
                            profit_krw = sell_amount_net - buy_amount_net
                            reinvest_amt = profit_krw * 0.60 if selected_strategy == '3tier' else (profit_krw * 1.00 if selected_strategy == 'full_cash' else 0.0) if profit_krw > 0 else profit_krw
                            batch_reinvest_profit += reinvest_amt
                            total_trades_all += 1
                            if profit_krw >= 0: win_trades_all += 1
                            else: 
                                if sim_use_cd: cooldown_remaining = cd
                            total_net_profit_all += profit_krw
                        else:
                            positions_to_keep.append(pos)
                            
                    positions = positions_to_keep
                    if selected_strategy != 'equal_alloc':
                        current_capital += batch_reinvest_profit
                        current_capital = max(current_capital, 0.0)
                        
                    drop_target_price = prev_close * (1 + target_drop_rate / 100)
                    if close <= drop_target_price and len(positions) < max_agents:
                        market_safe = True
                        if use_market_ma20_filter:
                            try:
                                bench = kospi_df if is_ks else kosdaq_df
                                if date in bench.index and float(bench.loc[date, 'Close']) < float(bench.loc[date, 'MA20']): market_safe = False
                            except: pass
                            
                        kospi_crash_safe = True
                        if use_kospi_crash_filter and not kospi_df.empty and date in kospi_df.index:
                            try:
                                k_ret = float(kospi_df.loc[date, 'Daily_Return']) if isinstance(kospi_df.loc[date, 'Daily_Return'], (float, int, np.floating)) else float(kospi_df.loc[date, 'Daily_Return'].iloc[0])
                                if not pd.isna(k_ret) and k_ret <= kospi_crash_threshold: kospi_crash_safe = False
                            except: pass
                            
                        trend_safe = True if not use_trend_filter else (ma20 > ma20_prev and ma10 >= ma20)
                        cooldown_safe = True
                        if sim_use_cd and cooldown_remaining > 0: cooldown_safe = False
                        
                        if ((not use_ma20_filter) or close >= ma20) and market_safe and trend_safe and kospi_crash_safe and cooldown_safe:
                            shares = max(int(((s_capital / max_agents) * (current_capital / s_capital if selected_strategy != 'equal_alloc' else 1.0)) // close), 1)
                            positions.append({'entry_price': close, 'shares': shares, 'target_ret': 15.0, 'max_price': close, 'trailing_active': False})
            
            win_rate = (win_trades_all / total_trades_all * 100) if total_trades_all > 0 else 0
            results.append({'cut': cut, 'cd': cd, 'profit': total_net_profit_all, 'win_rate': win_rate, 'trades': total_trades_all})
            
    res_df = pd.DataFrame(results)
    res_df = res_df.sort_values(by='profit', ascending=False).head(3).reset_index(drop=True)
    
    status_text.empty()
    progress_bar.empty()
    
    st.success("🎉 AI 로보-어드바이저의 가상 시뮬레이션이 완료되었습니다! 아래 추천 세팅을 좌측 옵션에 적용해보세요.")
    medals = ["🥇 1위 (최우수 황금 비율)", "🥈 2위 (안정형 대안)", "🥉 3위 (참고용)"]
    colors = ["#f1c40f", "#bdc3c7", "#cd7f32"]
    
    cols = st.columns(3)
    for i in range(3):
        row = res_df.iloc[i]
        cd_str = f"{int(row['cd'])}일" if row['cd'] > 0 else "OFF(가동 안함)"
        with cols[i]:
            card_html = f"<div style='background: white; border-radius: 8px; border-top: 5px solid {colors[i]}; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 10px;'>"
            card_html += f"<h4 style='margin-top:0; color: {colors[i]};'>{medals[i]}</h4>"
            card_html += f"<div style='font-size:13px; color:#34495e; margin-bottom:5px;'><b>🚨 비상탈출 손절선:</b> -{row['cut']:.0f}%</div>"
            card_html += f"<div style='font-size:13px; color:#34495e; margin-bottom:10px;'><b>❄️ 손절 후 쿨다운:</b> {cd_str}</div><hr style='margin:10px 0;'>"
            card_html += f"<div style='font-size:12px; color:#7f8c8d;'>예상 누적 순수익</div>"
            card_html += f"<div style='font-size:20px; font-weight:bold; color:#27ae60;'>{format_money(row['profit'])}원</div>"
            card_html += f"<div style='font-size:11px; color:#95a5a6; margin-top:3px;'>승률 {row['win_rate']:.1f}% (총 {row['trades']}회 매매)</div></div>"
            st.markdown(card_html, unsafe_allow_html=True)
            
    st.stop()

# --- 🚨 실시간 신호등 모듈 ---
if st.button("📡 [3시 20분] 실시간 시장 스캔 실행", type="primary"):
    if len(tickers_list) > 0 and stock_alloc_pct * len(tickers_list) <= 100.0:
        with st.spinner("🔍 실시간 시세 및 코스피 지수 분석 중..."):
            buy_orders, hold_stocks = [], []
            start_2mo = (datetime.datetime.today() - relativedelta(months=2)).strftime('%Y-%m-%d')
            
            k_hist = load_stock_data('KS11', start_2mo, None)
            kd_hist = load_stock_data('KQ11', start_2mo, None)
            
            try:
                k_hist['MA20'], kd_hist['MA20'] = k_hist['Close'].rolling(20).mean(), kd_hist['Close'].rolling(20).mean()
                is_ks_safe = float(k_hist['Close'].iloc[-1]) >= float(k_hist['MA20'].iloc[-1])
                is_kd_safe = float(kd_hist['Close'].iloc[-1]) >= float(kd_hist['MA20'].iloc[-1])
            except: is_ks_safe = is_kd_safe = True

            kospi_crash_safe = True
            kospi_daily_ret = 0.0
            if use_kospi_crash_filter and len(k_hist) >= 2:
                k_prev, k_curr = float(k_hist['Close'].iloc[-2]), float(k_hist['Close'].iloc[-1])
                kospi_daily_ret = ((k_curr - k_prev) / k_prev) * 100
                if kospi_daily_ret <= kospi_crash_threshold:
                    kospi_crash_safe = False
                    st.error(f"🚨 **[태풍 경보] KOSPI 지수 당일 {kospi_daily_ret:+.2f}% 급락 중! (기준: {kospi_crash_threshold}%)** ➔ 전 종목 신규 진입 차단.")

            for idx, t_code in enumerate(tickers_list):
                s_name, mkt = names_list[idx], markets_list[idx]
                is_ks = (mkt == 'KOSPI' or 'KOSPI' in str(mkt))
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
                            
                            if ((not use_ma20_filter) or curr_price >= curr_ma20) and market_safe and trend_safe and kospi_crash_safe:
                                est_shares = max(int(((total_capital * (stock_alloc_pct / 100.0)) / max_agents) // curr_price), 1)
                                buy_orders.append({'종목': s_name, '코드': t_code, '현재가': format_money(curr_price)+"원", '당일등락률': f"{daily_ret:+.2f}%", '수량': f"{est_shares}주"})
                            else: 
                                reason = "코스피 당일 폭락" if not kospi_crash_safe else "필터 조건 미달"
                                hold_stocks.append({'종목': s_name, '상태': reason, '당일등락률': f"{daily_ret:+.2f}%", '현재가': format_money(curr_price)+"원", '코드': t_code})
                        else: hold_stocks.append({'종목': s_name, '상태': f'목표 타점({target_drop_rate}%) 미달', '당일등락률': f"{daily_ret:+.2f}%", '현재가': format_money(curr_price)+"원", '코드': t_code})
                except: pass

            if buy_orders:
                for b in buy_orders: st.error(f"🎯 **{b['종목']}** 출격! (현재가: {b['현재가']} / 등락률: {b['당일등락률']} / 수량: {b['수량']})")
            else: st.success("🟢 신규 매수 조건 없음 (또는 지수 방어 발동). 대기 유지.")
            
            if hold_stocks:
                with st.expander("⚪ [오늘 관망/대기 종목 현황 보기] (※ 쿨다운 상태는 백테스트에서만 계산됨)"):
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

    with st.spinner("📡 [V10.56] 연속 손절 분석 및 클래식 대시보드 생성 중..."):
        end_date = datetime.datetime.today()
        start_date = end_date - relativedelta(years=years + 1)
        start_str, end_str = start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

        kospi_df = load_stock_data('KS11', start_str, end_str)
        kosdaq_df = load_stock_data('KQ11', start_str, end_str)
        
        kospi_mdd, kosdaq_mdd = 0.0, 0.0
        if not kospi_df.empty: 
            kospi_df['MA20'] = kospi_df['Close'].rolling(20).mean()
            kospi_df['Daily_Return'] = kospi_df['Close'].pct_change() * 100
            k_cummax = kospi_df['Close'].cummax()
            kospi_mdd = ((kospi_df['Close'] - k_cummax) / k_cummax * 100).min()
        if not kosdaq_df.empty: 
            kosdaq_df['MA20'] = kosdaq_df['Close'].rolling(20).mean()
            kq_cummax = kosdaq_df['Close'].cummax()
            kosdaq_mdd = ((kosdaq_df['Close'] - kq_cummax) / kq_cummax * 100).min()

        all_matched_trades, stock_results = [], {}
        combined_equity_df, combined_active_df, combined_core_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        all_active_positions = []
        total_cycles_all, full_launch_cycles_all = 0, 0
        total_agent_counter, total_fees_paid_all = 0, 0.0
        stock_data_dict = {}

        for idx, ticker in enumerate(tickers_list):
            s_name, mkt = names_list[idx], markets_list[idx]
            is_ks = (mkt == 'KOSPI' or 'KOSPI' in str(mkt))
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
            
            stock_data_dict[ticker] = df.copy()
            df = df[df.index >= (end_date - relativedelta(years=years)).strftime('%Y-%m-%d')].copy()

            positions = []
            core_shares, reserve_cash = 0, 0.0
            total_trades, win_trades, loss_trades = 0, 0, 0
            total_cycles, full_launch_cycles, stock_total_fees = 0, 0, 0.0
            matched_trades = []
            agent_counter, level_up_count, step_down_count = 0, 0, 0
            current_capital = float(s_capital)
            
            cooldown_remaining = 0
            daily_log = []

            for date, row in df.iterrows():
                if cooldown_remaining > 0: cooldown_remaining -= 1

                close = float(row['Close'])
                prev_close = float(row['Prev_Close']) if not pd.isna(row['Prev_Close']) else close
                high = float(row['High']) if 'High' in row and not pd.isna(row['High']) else close
                low = float(row['Low']) if 'Low' in row and not pd.isna(row['Low']) else close
                daily_return = float(row['Daily_Return']) if not pd.isna(row['Daily_Return']) else 0.0
                
                ma10 = float(row['MA10']) if not pd.isna(row['MA10']) else close
                ma20 = float(row['MA20']) if not pd.isna(row['MA20']) else close
                ma20_prev = float(row['MA20_prev']) if not pd.isna(row['MA20_prev']) else close
                ma60 = float(row['MA60']) if not pd.isna(row['MA60']) else close
                ma120 = float(row['MA120']) if not pd.isna(row['MA120']) else close
                date_str = date.strftime('%Y-%m-%d')
                
                if pd.isna(row['Daily_Return']): continue

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
                        else: 
                            reinvest_amt = profit_krw

                        batch_reinvest_profit += reinvest_amt
                        total_trades += 1
                        is_win = profit_krw >= 0
                        if is_win: 
                            win_trades += 1
                        else: 
                            loss_trades += 1
                            if use_cooldown: cooldown_remaining = cooldown_days

                        current_batch_trades.append({
                            '요원': pos['name'], '작전구역': s_name, '종목코드': ticker, '출격일': pos['entry_date'], '진입일 등락률': f"{pos['entry_return']:+.2f}%",
                            '진입단가': format_money(pos['entry_price'])+"원", '진입금액': format_money(buy_amount_net)+"원", '복귀일': date_str, '청산일 등락률': f"{row['Daily_Return']:+.2f}%",
                            '최고달성가': format_money(pos['max_price'])+"원" if use_trailing_stop else "-", '청산단가': format_money(sell_price)+"원", '매도금액': format_money(sell_amount_net)+"원",
                            '총수수료·세금': format_money(trade_fee_total)+"원", '등락폭': f"{format_money(sell_price - pos['entry_price'])}원 ({ret:+.2f}%)",
                            '소요기간': f"{(date - pos['entry_dt']).days}일 소요", '순수익률': f"{ret:+.2f}%", '정산내역': f"{'+' if profit_krw >= 0 else ''}{format_money(profit_krw)}원",
                            '구분': sell_reason, 'is_win': is_win, 'raw_profit': profit_krw, 'exit_date': date,
                            'raw_entry_dt': pos['entry_dt'], 'raw_exit_dt': date, 'raw_entry_price': pos['entry_price'], 'raw_exit_price': sell_price
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
                        current_capital += batch_reinvest_profit
                        current_capital = max(current_capital, 0.0)
                        
                        if current_capital >= s_capital * (1 + (level_up_count + 1) * 0.10):
                            level_up_count += 1
                            event_effect_str = f"🚀 [자본 레벨업 UP!]"
                        elif current_capital <= s_capital * (1 - (step_down_count + 1) * 0.10):
                            step_down_count += 1
                            event_effect_str = f"📉 [자본 축소 DOWN]"

                    for t in current_batch_trades:
                        t['스노우볼 레벨'] = f"Lv.{max(1, level_up_count + 1)}" + (f" <br><span style='color:#c0392b; font-size:9px;'>{event_effect_str}</span>" if event_effect_str else "")
                    matched_trades.extend(current_batch_trades)

                drop_target_price = prev_close * (1 + target_drop_rate / 100)
                if close <= drop_target_price and len(positions) < max_agents:
                    market_safe = True
                    if use_market_ma20_filter:
                        try:
                            bench = kospi_df if is_ks else kosdaq_df
                            if date in bench.index and float(bench.loc[date, 'Close']) < float(bench.loc[date, 'MA20']): market_safe = False
                        except: pass

                    kospi_crash_safe = True
                    if use_kospi_crash_filter and not kospi_df.empty and date in kospi_df.index:
                        try:
                            k_ret = float(kospi_df.loc[date, 'Daily_Return']) if isinstance(kospi_df.loc[date, 'Daily_Return'], (float, int, np.floating)) else float(kospi_df.loc[date, 'Daily_Return'].iloc[0])
                            if not pd.isna(k_ret) and k_ret <= kospi_crash_threshold: kospi_crash_safe = False
                        except: pass

                    trend_safe = True if not use_trend_filter else (ma20 > ma20_prev and ma10 >= ma20)
                    cooldown_safe = True
                    if use_cooldown and cooldown_remaining > 0: cooldown_safe = False
                    
                    if ((not use_ma20_filter) or close >= ma20) and market_safe and trend_safe and kospi_crash_safe and cooldown_safe:
                        agent_counter += 1; total_agent_counter += 1
                        shares = max(int(((s_capital / max_agents) * (current_capital / s_capital if selected_strategy != 'equal_alloc' else 1.0)) // close), 1)
                        is_super_bull = (close > ma20) and (ma20 > ma60) and (ma60 > ma120)
                        is_super_bear = (close < ma20) and (ma20 < ma60) and (ma60 < ma120)

                        positions.append({
                            'name': f"{s_name}-{agent_counter}호", 'entry_price': close, 'entry_date': date_str, 'entry_dt': date, 'entry_return': daily_return,
                            'shares': shares, 'target_ret': 15.0 if is_super_bull else (5.0 if is_super_bear else 10.0), 'max_price': close, 'trailing_active': False
                        })

                active_eval = sum(p['shares'] * close for p in positions)
                core_eval = core_shares * close
                stock_equity = s_capital + sum([t['raw_profit'] for t in matched_trades]) + reserve_cash + core_eval + active_eval - sum(p['shares']*p['entry_price'] for p in positions)
                daily_log.append({'Date': date, 'Stock_Equity': stock_equity, 'Active_Eval': active_eval, 'Core_Eval': core_eval})

            for p in positions:
                cur_eval_p = p['shares'] * float(df['Close'].iloc[-1])
                pnl_p = cur_eval_p - (p['shares'] * p['entry_price'])
                all_active_positions.append({
                    '작전구역': s_name, '요원명': p['name'], '파견일': p['entry_date'], 'holding_days': (end_date - p['entry_dt']).days,
                    '진입단가': format_money(p['entry_price'])+"원", '수량': f"{p['shares']}주", '진입금액': format_money(p['shares'] * p['entry_price'])+"원",
                    '평가금액': format_money(cur_eval_p)+"원", '평가손익': f"{'+' if pnl_p >= 0 else ''}{format_money(pnl_p)}원 ({(pnl_p / (p['shares'] * p['entry_price']) * 100):+.2f}%)",
                    'is_plus': pnl_p >= 0, 'pnl_val': pnl_p, 'pnl_pct': (pnl_p / (p['shares'] * p['entry_price'])) * 100,
                    '고점추적': f"<span style='color:#8e44ad;font-weight:bold;'>+{((p['max_price']-p['entry_price'])/p['entry_price']*100):.1f}% 도달</span>" if use_trailing_stop else "-",
                    'raw_entry_dt': p['entry_dt'], 'raw_entry_price': p['entry_price']
                })

            if daily_log: 
                df_log = pd.DataFrame(daily_log).set_index('Date')
                combined_equity_df[s_name] = df_log['Stock_Equity']
                combined_active_df[s_name] = df_log['Active_Eval']
                combined_core_df[s_name] = df_log['Core_Eval']

            # 🌟 [신규] 최근 연속 손절 횟수(Streak) 정밀 계산
            consecutive_losses = 0
            sorted_trades = sorted(matched_trades, key=lambda x: x['exit_date'], reverse=True)
            for t in sorted_trades:
                if not t['is_win']:
                    consecutive_losses += 1
                else:
                    break

            stock_results[ticker] = {
                'name': s_name, 'total_trades': total_trades, 'win_trades': win_trades, 'loss_trades': loss_trades,
                'win_rate': (win_trades / total_trades * 100) if total_trades > 0 else 0,
                'net_profit': sum([t['raw_profit'] for t in matched_trades]), 'reserve_cash': reserve_cash, 'core_shares': core_shares, 'core_eval': core_shares * float(df['Close'].iloc[-1]),
                'active_eval': sum(p['shares'] * float(df['Close'].iloc[-1]) for p in positions), 'active_count': len(positions),
                'total_cycles': total_cycles, 'full_launch_cycles': full_launch_cycles, 'level_up_count': level_up_count, 'step_down_count': step_down_count,
                'consecutive_losses': consecutive_losses
            }
            all_matched_trades.extend(matched_trades)

        # 🌟 전체 포트폴리오 자산 결산
        if not combined_equity_df.empty:
            combined_equity_df = combined_equity_df.ffill().bfill().dropna()
            combined_active_df = combined_active_df.reindex(combined_equity_df.index).ffill().bfill().fillna(0)
            combined_core_df = combined_core_df.reindex(combined_equity_df.index).ffill().bfill().fillna(0)

            total_unallocated_cash = total_capital - (total_capital * (stock_alloc_pct / 100.0) * len(tickers_list))
            portfolio_eq = combined_equity_df.sum(axis=1) + total_unallocated_cash
            total_active_val = combined_active_df.sum(axis=1)
            total_core_val = combined_core_df.sum(axis=1)
            dynamic_cash_line = portfolio_eq - total_active_val - total_core_val
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
            full_launch_pct = (full_launch_cycles_all / total_cycles_all * 100) if total_cycles_all > 0 else 0.0
            
            total_cash_all = portfolio_eq.iloc[-1] - total_active_eval - total_core_eval
            operational_cash = max(0.0, total_cash_all - total_reserve_cash) if selected_strategy == '3tier' else total_cash_all
            
            all_matched_trades.sort(key=lambda x: x['exit_date'], reverse=True)

            # --- 🌟 4. 대시보드 UI ---
            market_lock_status = 'ON' if use_market_ma20_filter else 'OFF'
            kospi_crash_status = f'ON({kospi_crash_threshold:.1f}%)' if use_kospi_crash_filter else 'OFF'
            cut_status = f'ON({emergency_threshold:.0f}%)' if emergency_cut_active else 'OFF'
            trail_status = f'ON' if use_trailing_stop else 'OFF'
            cooldown_status = f'ON({cooldown_days}일)' if use_cooldown else 'OFF'

            # 1. 옐로우 박스: 제미니 분석 보고서
            yellow_box_html = f"<div style='background-color:#fdfae6; border:1px solid #f1c40f; padding:15px; border-radius:5px; margin-bottom:15px;'>"
            yellow_box_html += f"<h4 style='color:#9c640c; margin-top:0; margin-bottom:10px; font-size:15px;'>🤖 [제미니 분석 보고서] 스노우볼 오토 파일럿 작전 결과 ({raw_tickers})</h4>"
            yellow_box_html += f"<div style='font-size:12px; color:#7f8c8d; font-weight:bold; margin-bottom:5px;'>📋 적용된 핵심 알고리즘 조건 명세서 및 알파(Alpha) 성과</div>"
            yellow_box_html += f"<ul style='margin:0; padding-left:20px; font-size:12px; color:#34495e; line-height:1.6;'>"
            yellow_box_html += f"<li><b>대상 종목 및 기간:</b> {raw_tickers} / 최근 {years}년</li>"
            yellow_box_html += f"<li><b>지수 대비 초과 수익률(Alpha):</b> 포트폴리오 수익률({portfolio_total_return:+.1f}%)이 동기간 KOSPI({kospi_return:+.1f}%), KOSDAQ({kosdaq_return:+.1f}%) 대비 압도적 초과 달성</li>"
            yellow_box_html += f"<li><b>하락장 방어 및 리스크 제어:</b> MDD {max_drawdown:.2f}% 기록 | 손절 후 쿨다운 {cooldown_days}일 가동 | 코스피 {kospi_crash_threshold}% 급락 락 방파제</li>"
            yellow_box_html += f"<li><b>스노우볼 복리 레벨UP:</b> 순수익 누적 임계치 도달 시 파견 요원 예산 단계적 증액 (현재 레벨업 {total_level_up}회)</li></ul></div>"
            st.markdown(yellow_box_html, unsafe_allow_html=True)

            # 2. 🌟 핑크 박스: 제미니 종목 자동 진단 & [연속 손절 감지] 리포트
            pink_box_html = f"<div style='background-color:#fff0f5; border:1px solid #fadbd8; padding:15px; border-radius:5px; margin-bottom:15px;'>"
            pink_box_html += f"<h4 style='color:#c0392b; margin-top:0; margin-bottom:5px; font-size:14px;'>🚨 [제미니 종목 자동 진단 & 연속 손절 방어 리포트]</h4>"
            pink_box_html += f"<div style='font-size:11px; color:#7f8c8d; margin-bottom:10px;'>최근 연속 손절(2회 이상 발생 시 진입금지 권고), 장기 체류(90일 초과), 수익 기여도를 실시간 스캔하여 시든 나무를 자동 진단합니다.</div>"
            pink_box_html += f"<div style='display:flex; flex-wrap:wrap; gap:10px;'>"
            
            for t_code, res in stock_results.items():
                contrib = (res['net_profit'] / total_net_profit_all * 100) if total_net_profit_all > 0 else 0
                avg_days = np.mean([int(str(t['소요기간']).replace('일 소요','').strip()) for t in all_matched_trades if t['종목코드'] == t_code]) if any(t['종목코드'] == t_code for t in all_matched_trades) else 0
                loss_cnt = res['loss_trades']
                c_loss = res['consecutive_losses']
                
                reasons = []
                
                # 🌟 연속 손절 판정 로직
                if c_loss >= 3:
                    reasons.append(f"🚨 최근 연속 {c_loss}회 손절 (낙하산 칼날 구간)")
                    status_tag = "<span style='background:#fdedec; color:#c0392b; font-size:10px; padding:2px 5px; border-radius:3px; font-weight:bold;'>🔴 진입금지 권고</span>"
                    border_color = "#c0392b"
                elif c_loss == 2:
                    reasons.append(f"⚠️ 최근 연속 2회 손절 (하락 추세 점검)")
                    status_tag = "<span style='background:#fcf3cf; color:#b7950b; font-size:10px; padding:2px 5px; border-radius:3px; font-weight:bold;'>🟡 점검 요망</span>"
                    border_color = "#f1c40f"
                elif res['net_profit'] < 0 or avg_days > 90:
                    if res['net_profit'] < 0: reasons.append("누적 순손실 발생")
                    if avg_days > 90: reasons.append(f"평균 체류기간 {avg_days:.1f}일 초과")
                    status_tag = "<span style='background:#fdedec; color:#c0392b; font-size:10px; padding:2px 5px; border-radius:3px;'>🔴 교체 권고</span>"
                    border_color = "#c0392b"
                elif contrib < 5.0 and total_trades_all > 0:
                    reasons.append(f"수익 기여도 저조 ({contrib:.1f}%)")
                    status_tag = "<span style='background:#fcf3cf; color:#b7950b; font-size:10px; padding:2px 5px; border-radius:3px;'>🟡 주의 관찰</span>"
                    border_color = "#f1c40f"
                else:
                    status_tag = "<span style='background:#e8f8f5; color:#117a65; font-size:10px; padding:2px 5px; border-radius:3px;'>🟢 우수 종목</span>"
                    border_color = "#1abc9c"
                    reasons.append("최근 매매 양호 (추세 유지)")

                reasons_html = "".join([f"<div style='font-size:11px; color:#c0392b; margin-top:2px;'>🔻 {r}</div>" if ('손절' in r or '손실' in r or '초과' in r) else f"<div style='font-size:11px; color:#117a65; margin-top:2px;'>✨ {r}</div>" for r in reasons])
                
                pink_box_html += f"<div style='flex:1 1 180px; background:white; border:1px solid #e5e7e9; border-top:3px solid {border_color}; padding:10px; border-radius:4px; min-width:140px;'>"
                pink_box_html += f"<div style='display:flex; justify-content:space-between; margin-bottom:5px; align-items:center;'><b style='font-size:12px; color:#2c3e50;'>{res['name']}</b> {status_tag}</div>"
                pink_box_html += f"{reasons_html}"
                pink_box_html += f"<div style='font-size:10px; color:#7f8c8d; margin-top:8px; border-top:1px dashed #ecf0f1; padding-top:5px;'>수익기여: {contrib:.1f}% | 총손절: {loss_cnt}회 (최근연속 {c_loss}회)</div></div>"
                
            pink_box_html += "</div></div>"
            st.markdown(pink_box_html, unsafe_allow_html=True)

            # 3. 블루 박스: 운영 설명서 아코디언
            with st.expander("▶ 📖 [클릭하여 펼치기] 박가이버 사령부 공식 운영 설명서 및 작전 원리 가이드"):
                st.markdown("""
                **1. 3단 밸런스 과수원 전략이란?**
                수익 발생 시 60%는 다음 요원 예산으로 복리 재투자, 20%는 현금 비상금(파킹통장), 20%는 평생 보유할 코어 주식(나무)으로 분배하는 안정형 자산 증식 전략입니다.
                
                **2. 🚨 연속 손절 감지 및 쿨다운 시스템**
                최근 2~3회 연속으로 손절이 터진 종목은 '떨어지는 칼날'로 판단하여 리포트에서 **진입금지 권고**를 발령하고, 설정된 쿨다운 일수 동안 신규 파견을 강제 차단합니다.
                
                **3. 무제한 추세추종 (고점 추적 레이더)**
                목표 수익률(예: 15%)에 도달해도 즉시 팔지 않고, 주가가 꺾일 때(고점 대비 설정 하락률)까지 수익을 끝까지 쫓아갑니다.
                """)

            # 4. 12칸 파스텔 대시보드 (20% 비상적립금 완벽 표기)
            dashboard_html = f"<div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 10px; margin-top: 15px;'>"
            dashboard_html += f"<div style='background: #e8f8f5; border-left: 4px solid #1abc9c; padding: 12px; border-radius: 4px;'><div style='font-size: 11px; color: #7f8c8d; font-weight: bold;'>🎯 통합 청산 승률</div><div style='font-size: 18px; font-weight: 900; color: #16a085; margin: 4px 0; white-space: nowrap;'>{overall_win_rate:.1f}%</div><div style='font-size: 10px; color: #1abc9c; white-space: nowrap;'>익절 {win_trades_all} / 손절 {loss_trades_all}</div></div>"
            dashboard_html += f"<div style='background: #ebf5fb; border-left: 4px solid #3498db; padding: 12px; border-radius: 4px;'><div style='font-size: 11px; color: #7f8c8d; font-weight: bold;'>⚔️ 총 투입 요원</div><div style='font-size: 18px; font-weight: 900; color: #2980b9; margin: 4px 0; white-space: nowrap;'>{total_agent_counter}명</div><div style='font-size: 10px; color: #3498db; white-space: nowrap;'>총 {total_cycles_all}회차 / 대기 {total_active_count}명</div></div>"
            dashboard_html += f"<div style='background: #fef5e7; border-left: 4px solid #e67e22; padding: 12px; border-radius: 4px;'><div style='font-size: 11px; color: #7f8c8d; font-weight: bold;'>🔥 최대 요원 풀출력</div><div style='font-size: 18px; font-weight: 900; color: #d35400; margin: 4px 0; white-space: nowrap;'>{full_launch_cycles_all}회 <span style='font-size:11px;'>({full_launch_pct:.1f}%)</span></div><div style='font-size: 10px; color: #e67e22; white-space: nowrap;'>풀가동 비중</div></div>"
            dashboard_html += f"<div style='background: #fadbd8; border-left: 4px solid #e74c3c; padding: 12px; border-radius: 4px;'><div style='font-size: 11px; color: #7f8c8d; font-weight: bold;'>📉 최대 낙폭지수 (MDD)</div><div style='font-size: 18px; font-weight: 900; color: #c0392b; margin: 4px 0; white-space: nowrap;'>{max_drawdown:.2f}%</div><div style='font-size: 10px; color: #e74c3c; white-space: nowrap;'>KS {kospi_mdd:.1f}% | KQ {kosdaq_mdd:.1f}%</div></div>"
            dashboard_html += f"<div style='background: #fef9e7; border-left: 4px solid #f1c40f; padding: 12px; border-radius: 4px;'><div style='font-size: 11px; color: #7f8c8d; font-weight: bold;'>🚀 스노우볼 레벨UP</div><div style='font-size: 18px; font-weight: 900; color: #f39c12; margin: 4px 0; white-space: nowrap;'>{total_level_up}회</div><div style='font-size: 10px; color: #f1c40f; white-space: nowrap;'>복리 예산 스텝 업</div></div>"
            dashboard_html += f"</div>"
            
            if selected_strategy == '3tier':
                cash_card_subtitle = f"<span style='color:#1b4f72; font-weight:bold;'>🛡️ 20%적립: {format_money(total_reserve_cash)}원</span><br><span style='color:#7f8c8d;'>• 대기금: {format_money(operational_cash)}원</span>"
            else:
                cash_card_subtitle = "<span style='color:#3498db;'>안전 예수금 (대기자금)</span>"

            dashboard_html += f"<div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-bottom: 20px;'>"
            dashboard_html += f"<div style='background: #e8f8f5; border-left: 4px solid #1abc9c; padding: 12px; border-radius: 4px;'><div style='font-size: 11px; color: #7f8c8d; font-weight: bold;'>📈 지수 대비 초과수익</div><div style='font-size: 15px; font-weight: 900; color: #166534; margin: 4px 0; white-space: nowrap;'>+{portfolio_total_return - kospi_return:.1f}%p</div><div style='font-size: 10px; color: #1abc9c; white-space: nowrap;'>KS 대비 초과 달성</div></div>"
            dashboard_html += f"<div style='background: #ebf5fb; border-left: 4px solid #3498db; padding: 12px; border-radius: 4px;'><div style='font-size: 11px; color: #7f8c8d; font-weight: bold;'>💵 총 보유 현금금고</div><div style='font-size: 15px; font-weight: 900; color: #1b4f72; margin: 4px 0; white-space: nowrap;'>{format_money(total_cash_all)}원</div><div style='font-size: 9.5px; line-height:1.2; margin-top:3px;'>{cash_card_subtitle}</div></div>"
            dashboard_html += f"<div style='background: #fef5e7; border-left: 4px solid #f39c12; padding: 12px; border-radius: 4px;'><div style='font-size: 11px; color: #7f8c8d; font-weight: bold;'>📊 대기주식 평가금</div><div style='font-size: 15px; font-weight: 900; color: #2c3e50; margin: 4px 0; white-space: nowrap;'>{format_money(total_active_eval)}원</div><div style='font-size: 10px; color: #f39c12; white-space: nowrap;'>대기 요원 평가가</div></div>"
            dashboard_html += f"<div style='background: #ffffff; border-left: 4px solid #e67e22; border-top: 1px solid #eee; border-right: 1px solid #eee; border-bottom: 1px solid #eee; padding: 12px; border-radius: 4px;'><div style='font-size: 11px; color: #7f8c8d; font-weight: bold;'>💰 실현 순수익</div><div style='font-size: 15px; font-weight: 900; color: #d35400; margin: 4px 0; white-space: nowrap;'>{'+' if total_net_profit_all>0 else ''}{format_money(total_net_profit_all)}원</div><div style='font-size: 10px; color: #e67e22; white-space: nowrap;'>매매 실현 순익</div></div>"
            dashboard_html += f"<div style='background: #fadbd8; border-left: 4px solid #c0392b; padding: 12px; border-radius: 4px;'><div style='font-size: 11px; color: #7f8c8d; font-weight: bold;'>💸 수수료·세금</div><div style='font-size: 15px; font-weight: 900; color: #78281f; margin: 4px 0; white-space: nowrap;'>-{format_money(total_fees_paid_all)}원</div><div style='font-size: 10px; color: #e74c3c; white-space: nowrap;'>총 납부 비용</div></div>"
            dashboard_html += f"<div style='background: #ffffff; border-left: 4px solid #c0392b; border-top: 1px solid #eee; border-right: 1px solid #eee; border-bottom: 1px solid #eee; padding: 12px; border-radius: 4px;'><div style='font-size: 11px; color: #7f8c8d; font-weight: bold;'>🏆 총자산</div><div style='font-size: 15px; font-weight: 900; color: #2c3e50; margin: 4px 0; white-space: nowrap;'>{format_money(portfolio_eq.iloc[-1])}원</div><div style='font-size: 10px; color: #7f8c8d; white-space: nowrap;'>현금+주식+코어</div></div>"
            dashboard_html += f"<div style='background: #f4ecf7; border-left: 4px solid #9b59b6; padding: 12px; border-radius: 4px;'><div style='font-size: 11px; color: #7f8c8d; font-weight: bold;'>🍎 코어주식</div><div style='font-size: 15px; font-weight: 900; color: #8e44ad; margin: 4px 0; white-space: nowrap;'>{total_core_shares}주</div><div style='font-size: 10px; color: #9b59b6; white-space: nowrap;'>{format_money(total_core_eval)}원</div></div>"
            dashboard_html += f"</div>"
            st.markdown(dashboard_html, unsafe_allow_html=True)

            # 5. 종목별 종합 성적표 옥석 가리기 판
            rc_html = "<div style='background:#fdfefe; border:1px solid #1abc9c; border-radius:6px; padding:14px; margin-bottom:15px;'>"
            rc_html += "<h4 style='margin:0 0 10px 0; color:#117a65; font-size:14px; font-weight:bold;'>📊 [종목별 종합 성적표] 옥석 가리기 현황판</h4>"
            rc_html += "<div style='overflow-x:auto;'><table style='width:100%; border-collapse:collapse; text-align:center; font-size:12px; min-width:650px;'><thead style='background-color:#e8f8f5; color:#117a65;'><tr><th style='padding:8px; border:1px solid #d5dbdf;'>종목명 (코드)</th><th style='padding:8px; border:1px solid #d5dbdf;'>총 매매 (승/패)</th><th style='padding:8px; border:1px solid #d5dbdf;'>승률</th><th style='padding:8px; border:1px solid #d5dbdf;'>누적 순수익</th><th style='padding:8px; border:1px solid #d5dbdf;'>수익 기여도</th><th style='padding:8px; border:1px solid #d5dbdf;'>평균 체류기간</th><th style='padding:8px; border:1px solid #d5dbdf;'>종합 판정</th></tr></thead><tbody>"
            for t_code, res in stock_results.items():
                contrib = (res['net_profit'] / total_net_profit_all * 100) if total_net_profit_all > 0 else 0
                avg_days = np.mean([int(str(t['소요기간']).replace('일 소요','').strip()) for t in all_matched_trades if t['종목코드'] == t_code]) if any(t['종목코드'] == t_code for t in all_matched_trades) else 0
                
                if res['net_profit'] < 0 or avg_days > 90 or (res['win_rate'] < 50 and res['total_trades'] > 0): 
                    status_tag, row_bg = "<span style='background:#fdedec; color:#c0392b; padding:3px 8px; border-radius:4px; font-weight:bold;'>🔴 교체 권고</span>", "#fdedec"
                elif contrib < 5.0 or avg_days > 60 or res['loss_trades'] >= 2: 
                    status_tag, row_bg = "<span style='background:#fef9e7; color:#d35400; padding:3px 8px; border-radius:4px; font-weight:bold;'>🟡 주의 요망</span>", "#fcf3cf"
                else: 
                    status_tag, row_bg = "<span style='background:#e8f8f5; color:#117a65; padding:3px 8px; border-radius:4px; font-weight:bold;'>🟢 계속 유지</span>", "#ffffff"

                rc_html += f"<tr style='background-color:{row_bg};'><td style='padding:7px; border:1px solid #eaeded; font-weight:bold;'>{res['name']} ({t_code})</td><td style='padding:7px; border:1px solid #eaeded;'>{res['total_trades']}회 ({res['win_trades']}승/{res['loss_trades']}패)</td><td style='padding:7px; border:1px solid #eaeded; font-weight:bold;'>{res['win_rate']:.1f}%</td><td style='padding:7px; border:1px solid #eaeded; color:#c0392b; font-weight:bold;'>{format_money(res['net_profit'])}원</td><td style='padding:7px; border:1px solid #eaeded;'>{contrib:.1f}%</td><td style='padding:7px; border:1px solid #eaeded;'>{avg_days:.1f}일</td><td style='padding:7px; border:1px solid #eaeded;'>{status_tag}</td></tr>"
            rc_html += "</tbody></table></div></div>"
            st.markdown(rc_html, unsafe_allow_html=True)

            # 6. 종목별 코어주식 & 20% 비상적립금 현황판
            core_cards_html = f"<div style='background:#f4ecf7; border:1px solid #9b59b6; border-radius:6px; padding:14px; margin-bottom:15px;'><h4 style='margin:0 0 8px 0; color:#8e44ad; font-size:14px; font-weight:bold;'>🍎 [종목별 코어주식(나무) & 20% 비상적립금 현황판] (총 코어적립: {total_core_shares}주 / 총 비상적립: {format_money(total_reserve_cash)}원)</h4><div style='display:flex; flex-wrap:wrap; gap:8px;'>"
            for t_code, res in stock_results.items():
                core_cards_html += f"<div style='flex:1 1 180px; background:white; border:1px solid #d2b4de; border-top:4px solid #9b59b6; padding:10px; border-radius:6px; min-width:140px;'><b style='font-size:12px; color:#512e5f;'>{res['name']}</b><div style='font-size:11px; color:#2c3e50; margin-top:4px;'>• 적립 코어: <b>{res['core_shares']}주</b> ({format_money(res['core_eval'])}원)<br>• 20% 비상적립: <b style='color:#2980b9;'>{format_money(res['reserve_cash'])}원</b></div></div>"
            core_cards_html += "</div></div>"
            st.markdown(core_cards_html, unsafe_allow_html=True)

            # 7. 장기 체류 요원 TOP 3 경보
            sorted_active = sorted(all_active_positions, key=lambda x: x['holding_days'], reverse=True)
            top3_cards_html = "<div style='background:#fdf2e9; border:1px solid #e67e22; border-radius:6px; padding:14px; margin-bottom:15px;'><h4 style='margin:0 0 8px 0; color:#d35400; font-size:14px; font-weight:bold;'>🚨 [장기 체류 요원 TOP 3 경보 순위표] (청산 검토 대상)</h4><div style='display:flex; flex-wrap:wrap; gap:8px;'>"
            for rank, p in enumerate(sorted_active[:3] if len(sorted_active) >= 3 else sorted_active, 1):
                badge_color, icon = ("#e74c3c", "🚨") if p['holding_days'] >= 90 else ("#e67e22", "🔥") if p['holding_days'] >= 60 else ("#f1c40f", "⚠️") if p['holding_days'] >= 20 else ("#2ecc71", "✅")
                loss_tag = f"<br><span style='color:#e74c3c; font-weight:bold; font-size:11px;'>🚨 손실주의</span>" if p['pnl_pct'] <= -15.0 else ""
                top3_cards_html += f"<div style='flex:1 1 200px; background:white; border:1px solid #fadbd8; border-top:4px solid {badge_color}; padding:10px; border-radius:6px; min-width:140px;'><div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;'><b style='font-size:12px; color:#7d6608;'>🏆 {rank}위 - {p['작전구역']}</b><span style='background:{badge_color}; color:white; padding:1px 6px; border-radius:4px; font-size:10px; font-weight:bold;'>{icon} {p['holding_days']}일 체류</span></div><div style='font-size:11px; color:#2c3e50;'>• 요원명: <b>{p['요원명']}</b><br>• 평가손익: <b style='color:#c0392b;'>{p['평가손익']}</b>{loss_tag}</div></div>"
            top3_cards_html += "</div></div>"
            st.markdown(top3_cards_html, unsafe_allow_html=True)

            # 8. 현재 파견 대기 요원 실시간 현황판
            active_html = f"<div style='background:#fdfefe; border:1px solid #3498db; border-radius:6px; padding:12px; margin-bottom:15px;'><h4 style='margin:0 0 10px 0; color:#2980b9; font-size:13px;'>🕵️ [현재 파견 대기 중인 요원 실시간 현황판] (총 {len(all_active_positions)}명 대기 중)</h4>"
            if len(all_active_positions) > 0:
                active_html += "<div style='overflow-x:auto;'><table style='width:100%; border-collapse:collapse; text-align:center; font-size:11px; min-width:600px;'><thead style='background-color:#ebf5fb; color:#2980b9;'><tr><th style='padding:6px; border:1px solid #d5dbdf;'>No.</th><th style='padding:6px; border:1px solid #d5dbdf;'>상태</th><th style='padding:6px; border:1px solid #d5dbdf;'>작전구역</th><th style='padding:6px; border:1px solid #d5dbdf;'>요원명</th><th style='padding:6px; border:1px solid #d5dbdf;'>파견일</th><th style='padding:6px; border:1px solid #d5dbdf;'>체류일수</th><th style='padding:6px; border:1px solid #d5dbdf;'>진입단가</th><th style='padding:6px; border:1px solid #d5dbdf;'>수량</th><th style='padding:6px; border:1px solid #d5dbdf; background:#f4ecf7; color:#8e44ad;'>🚀 고점추적(최고)</th><th style='padding:6px; border:1px solid #d5dbdf; background:#d4e6f1;'>진입총액</th><th style='padding:6px; border:1px solid #d5dbdf;'>현재평가금액</th><th style='padding:6px; border:1px solid #d5dbdf;'>평가손익</th></tr></thead><tbody>"
                for idx_ap, ap in enumerate(all_active_positions, 1):
                    pnl_color = "#c0392b" if ap['is_plus'] else "#2980b9"
                    row_bg, s_icon = ("#fdedec", "🚨") if ap['holding_days'] >= 90 else ("#fdebd0", "🔥") if ap['holding_days'] >= 60 else ("#fef9e7", "⚠️") if ap['holding_days'] >= 20 else ("#ffffff", "✅")
                    loss_badge = "<br><span style='background:#e74c3c; color:white; padding:2px 4px; border-radius:3px; font-size:10px;'>🚨위험</span>" if ap['pnl_pct'] <= -25.0 else ""
                    active_html += f"<tr style='background-color:{row_bg};'><td style='padding:5px; border:1px solid #eaeded; font-weight:bold; color:#7f8c8d;'>{idx_ap}</td><td style='padding:5px; border:1px solid #eaeded; font-size:14px;'>{s_icon}</td><td style='padding:5px; border:1px solid #eaeded; font-weight:bold;'>{ap['작전구역']}</td><td style='padding:5px; border:1px solid #eaeded; font-weight:bold;'>{ap['요원명']}</td><td style='padding:5px; border:1px solid #eaeded;'>{ap['파견일']}</td><td style='padding:5px; border:1px solid #eaeded; font-weight:bold;'>{ap['holding_days']}일</td><td style='padding:5px; border:1px solid #eaeded;'>{ap['진입단가']}</td><td style='padding:5px; border:1px solid #eaeded;'>{ap['수량']}</td><td style='padding:5px; border:1px solid #eaeded; background:#fdf2e9;'>{ap['고점추적']}</td><td style='padding:5px; border:1px solid #eaeded; font-weight:bold; color:#1e8449;'>{ap['진입금액']}</td><td style='padding:5px; border:1px solid #eaeded;'>{ap['평가금액']}</td><td style='padding:5px; border:1px solid #eaeded; color:{pnl_color}; font-weight:bold;'>{ap['평가손익']}{loss_badge}</td></tr>"
                active_html += "</tbody></table></div>"
            else: active_html += "<div style='font-size:11px; color:#7f8c8d; text-align:center; padding:5px;'>파견 대기 중인 요원이 없습니다.</div>"
            active_html += "</div>"
            st.markdown(active_html, unsafe_allow_html=True)

            # 9. 자산 성장 곡선
            st.subheader("📈 오토파일럿 자산 성장 vs 💵 현금선 추이 비교")
            chart_df = pd.DataFrame(index=portfolio_eq.index)
            chart_df['🚀 오토파일럿 총자산'] = portfolio_eq
            chart_df['💵 현금 잔고 (비상금 + 대기자금)'] = dynamic_cash_line
            if selected_strategy == '3tier':
                chart_df['🍎 누적 코어주식 가치'] = total_core_val
            try: 
                chart_df['📉 KOSPI 지수 (비교용)'] = total_capital * (kospi_df['Close'].reindex(portfolio_eq.index, method='ffill') / kospi_df['Close'].reindex(portfolio_eq.index, method='ffill').iloc[0])
            except: pass
            
            fig_asset = go.Figure()
            fig_asset.add_trace(go.Scatter(x=chart_df.index, y=chart_df['🚀 오토파일럿 총자산'], name='🚀 총자산', line=dict(color='#e74c3c', width=2.5), hovertemplate="%{y:,.0f}원"))
            fig_asset.add_trace(go.Scatter(x=chart_df.index, y=chart_df['💵 현금 잔고 (비상금 + 대기자금)'], name='💵 현금 잔고', line=dict(color='#3498db', width=2), hovertemplate="%{y:,.0f}원"))
            if selected_strategy == '3tier':
                fig_asset.add_trace(go.Scatter(x=chart_df.index, y=chart_df['🍎 누적 코어주식 가치'], name='🍎 코어주식', line=dict(color='#9b59b6', width=2), hovertemplate="%{y:,.0f}원"))
            if '📉 KOSPI 지수 (비교용)' in chart_df.columns:
                fig_asset.add_trace(go.Scatter(x=chart_df.index, y=chart_df['📉 KOSPI 지수 (비교용)'], name='📉 KOSPI(비교용)', line=dict(color='#95a5a6', width=1.5, dash='dot'), hovertemplate="%{y:,.0f}원"))
            
            fig_asset.update_layout(
                height=400, margin=dict(l=20, r=20, t=30, b=20), template='plotly_white', hovermode='x unified',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig_asset.update_yaxes(tickformat=",.0f", ticksuffix="원")
            fig_asset.update_xaxes(tickformat="%Y-%m-%d", hoverformat="%Y년 %m월 %d일")
            st.plotly_chart(fig_asset, use_container_width=True)

            # 10. 연도별 계좌 수익 현황
            st.markdown("<div style='margin-top:25px; margin-bottom:8px; font-size:14px; font-weight:bold; color:#2c3e50;'>📅 연도별 계좌 수익 현황</div>", unsafe_allow_html=True)
            yearly_data = []
            prev_eq = total_capital
            year_groups = portfolio_eq.groupby(portfolio_eq.index.year)
            for year, group in year_groups:
                year_start_eq = prev_eq
                year_end_eq = group.iloc[-1]
                year_profit = year_end_eq - year_start_eq
                year_return = (year_profit / year_start_eq) * 100 if year_start_eq > 0 else 0
                yearly_data.append({'연도': f"{year}년", '기초 자산': year_start_eq, '기말 자산': year_end_eq, '순수익': year_profit, '수익률': year_return})
                prev_eq = year_end_eq
                
            yearly_html = "<div style='overflow-x:auto; border:1px solid #d6dbdf; border-radius:6px; margin-bottom:15px;'><table style='width:100%; border-collapse:collapse; text-align:center; font-size:12px; min-width:600px;'><thead style='background-color:#f8f9f9; color:#2c3e50;'><tr><th style='padding:8px; border:1px solid #d5dbdf;'>연도</th><th style='padding:8px; border:1px solid #d5dbdf;'>기초 자산</th><th style='padding:8px; border:1px solid #d5dbdf;'>기말 자산</th><th style='padding:8px; border:1px solid #d5dbdf;'>당해 연도 순수익</th><th style='padding:8px; border:1px solid #d5dbdf;'>당해 연도 수익률</th></tr></thead><tbody>"
            for yd in yearly_data:
                pnl_color = "#c0392b" if yd['순수익'] >= 0 else "#2980b9"
                yearly_html += f"<tr style='background-color:#ffffff;'><td style='padding:7px; border:1px solid #eaeded; font-weight:bold;'>{yd['연도']}</td><td style='padding:7px; border:1px solid #eaeded;'>{format_money(yd['기초 자산'])}원</td><td style='padding:7px; border:1px solid #eaeded;'>{format_money(yd['기말 자산'])}원</td><td style='padding:7px; border:1px solid #eaeded; color:{pnl_color}; font-weight:bold;'>{'+' if yd['순수익'] >= 0 else ''}{format_money(yd['순수익'])}원</td><td style='padding:7px; border:1px solid #eaeded; color:{pnl_color}; font-weight:bold;'>{yd['수익률']:+.2f}%</td></tr>"
            yearly_html += "</tbody></table></div>"
            st.markdown(yearly_html, unsafe_allow_html=True)

            # 11. 박가이버 사령부 공식 매매 장부
            st.markdown("<div style='margin-top:25px; margin-bottom:8px; font-size:14px; font-weight:bold; color:#2c3e50;'>📜 박가이버 사령부 공식 매매 장부 (최고가 달성 기록 추가)</div>", unsafe_allow_html=True)
            table_html = "<div style='max-height:430px; overflow-y:auto; border:1px solid #d6dbdf; border-radius:6px; margin-bottom:15px;'><table style='width:100%; border-collapse:collapse; text-align:center; font-size:11px; min-width:1000px;'><thead style='position:sticky; top:0; background-color:#f2f4f4; color:#2c3e50; z-index:1;'><tr><th style='padding:6px; border:1px solid #d5dbdf; width:40px;'>No.</th><th style='padding:6px; border:1px solid #d5dbdf;'>요원</th><th style='padding:6px; border:1px solid #d5dbdf;'>작전 구역</th><th style='padding:6px; border:1px solid #d5dbdf;'>출격일</th><th style='padding:6px; border:1px solid #d5dbdf; background:#fdedec;'>청산일</th><th style='padding:6px; border:1px solid #d5dbdf; background:#e8f8f5; color:#117a65;'>진입단가</th><th style='padding:6px; border:1px solid #d5dbdf; background:#f4ecf7; color:#8e44ad;'>🚀 장중 최고가</th><th style='padding:6px; border:1px solid #d5dbdf; background:#fef9e7; color:#b7950b;'>최종 청산가</th><th style='padding:6px; border:1px solid #d5dbdf;'>진입일 등락률</th><th style='padding:6px; border:1px solid #d5dbdf;'>진입금액</th><th style='padding:6px; border:1px solid #d5dbdf;'>매도금액</th><th style='padding:6px; border:1px solid #d5dbdf;'>총 수수료·세금</th><th style='padding:6px; border:1px solid #d5dbdf;'>등락폭</th><th style='padding:6px; border:1px solid #d5dbdf;'>소요기간</th><th style='padding:6px; border:1px solid #d5dbdf;'>순수익률</th><th style='padding:6px; border:1px solid #d5dbdf;'>정산내역</th><th style='padding:6px; border:1px solid #d5dbdf;'>구분 (청산사유)</th><th style='padding:6px; border:1px solid #d5dbdf;'>스노우볼 레벨</th></tr></thead><tbody>"

            for idx_t, t in enumerate(all_matched_trades, 1):
                row_no = len(all_matched_trades) - idx_t + 1
                row_bg, text_color = ("#fdedec", "#c0392b") if t['is_win'] else ("#ebf5fb", "#2980b9")
                table_html += f"<tr style='background-color:{row_bg};'><td style='padding:5px; border:1px solid #eaeded; font-weight:bold; color:#7f8c8d;'>{row_no}</td><td style='padding:5px; border:1px solid #eaeded; font-weight:bold;'>{t['요원']}</td><td style='padding:5px; border:1px solid #eaeded; font-weight:bold; color:#2980b9;'>{t['작전구역']}</td><td style='padding:5px; border:1px solid #eaeded;'>{t['출격일']}</td><td style='padding:5px; border:1px solid #eaeded; font-weight:bold; color:#c0392b;'>{t['복귀일']}</td><td style='padding:5px; border:1px solid #eaeded; font-weight:bold; color:#117a65;'>{t['진입단가']}</td><td style='padding:5px; border:1px solid #eaeded; font-weight:bold; color:#8e44ad; background:#fdf2e9;'>{t.get('최고달성가','-')}</td><td style='padding:5px; border:1px solid #eaeded; font-weight:bold; color:#d35400;'>{t['청산단가']}</td><td style='padding:5px; border:1px solid #eaeded;'>{t['진입일 등락률']}</td><td style='padding:5px; border:1px solid #eaeded;'>{t['진입금액']}</td><td style='padding:5px; border:1px solid #eaeded;'>{t['매도금액']}</td><td style='padding:5px; border:1px solid #eaeded; color:#c0392b;'>{t['총수수료·세금']}</td><td style='padding:5px; border:1px solid #eaeded; color:{text_color}; font-weight:bold;'>{t['등락폭']}</td><td style='padding:5px; border:1px solid #eaeded;'>{t['소요기간']}</td><td style='padding:5px; border:1px solid #eaeded; color:{text_color}; font-weight:bold;'>{t['순수익률']}</td><td style='padding:5px; border:1px solid #eaeded; color:{text_color}; font-weight:bold;'>{t['정산내역']}</td><td style='padding:5px; border:1px solid #eaeded; font-weight:bold;'>{t['구분']}</td><td style='padding:5px; border:1px solid #eaeded; color:#d35400; font-weight:bold;'>{t.get('스노우볼 레벨','-')}</td></tr>"

            table_html += "</tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)

            # 12. 엑셀 CSV 다운로드
            df_export = pd.DataFrame([{k: v for k, v in t.items() if k not in ['is_win', 'raw_profit', 'exit_date', 'raw_entry_dt', 'raw_exit_dt', 'raw_entry_price', 'raw_exit_price']} for t in all_matched_trades])
            csv_buffer = io.StringIO()
            df_export.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
            st.download_button("📜 엑셀(CSV) 다운로드 (V10.56 풀버전)", data=csv_buffer.getvalue().encode('utf-8-sig'), file_name=f"박가이버사령부_V10.56_{selected_strategy}.csv", mime="text/csv")

            # 13. 종목별 캔들차트 아코디언 (최하단 배치)
            st.markdown("<div style='margin-top:35px; margin-bottom:10px; font-size:15px; font-weight:bold; color:#2c3e50;'>📈 [종목별 상세 작전 차트] (클릭하여 펼치기)</div>", unsafe_allow_html=True)
            for t_code, res in stock_results.items():
                s_name = res['name']
                with st.expander(f"📊 {s_name} ({t_code}) - 캔들차트 및 요원 매수/매도 타점 보기"):
                    df_stock = stock_data_dict.get(t_code)
                    if df_stock is not None and not df_stock.empty:
                        fig = go.Figure()
                        
                        fig.add_trace(go.Candlestick(
                            x=df_stock.index, open=df_stock['Open'], high=df_stock['High'],
                            low=df_stock['Low'], close=df_stock['Close'], name='주가',
                            increasing_line_color='#e74c3c', decreasing_line_color='#3498db'
                        ))
                        
                        if 'MA20' in df_stock:
                            fig.add_trace(go.Scatter(x=df_stock.index, y=df_stock['MA20'], line=dict(color='orange', width=1.5), name='20일선(MA20)', hovertemplate="%{y:,.0f}원"))
                        if 'MA60' in df_stock:
                            fig.add_trace(go.Scatter(x=df_stock.index, y=df_stock['MA60'], line=dict(color='green', width=1.5), name='60일선(MA60)', hovertemplate="%{y:,.0f}원"))
                        
                        ticker_trades = [t for t in all_matched_trades if t['종목코드'] == t_code]
                        ticker_actives = [p for p in all_active_positions if p['작전구역'] == s_name]
                        
                        for t in ticker_trades:
                            line_color = 'rgba(231, 76, 60, 0.9)' if t['is_win'] else 'rgba(52, 152, 219, 0.9)'
                            fig.add_trace(go.Scatter(
                                x=[t['raw_entry_dt'], t['raw_exit_dt']], y=[t['raw_entry_price'], t['raw_exit_price']],
                                mode='lines', line=dict(color=line_color, width=2.5, dash='dot'),
                                hovertemplate=f"<b>{t['요원']}</b><br>수익률: {t['순수익률']}<br>정산액: {t['정산내역']}<br>기간: {t['소요기간']}<extra></extra>",
                                showlegend=False
                            ))

                        buy_x = [t['raw_entry_dt'] for t in ticker_trades] + [p['raw_entry_dt'] for p in ticker_actives]
                        buy_y = [t['raw_entry_price'] for t in ticker_trades] + [p['raw_entry_price'] for p in ticker_actives]
                        sell_x = [t['raw_exit_dt'] for t in ticker_trades]
                        sell_y = [t['raw_exit_price'] for t in ticker_trades]
                        
                        if buy_x:
                            fig.add_trace(go.Scatter(x=buy_x, y=buy_y, mode='markers', marker=dict(symbol='triangle-up', size=13, color='magenta', line=dict(width=1, color='black')), name='🎯 매수', hovertemplate="%{y:,.0f}원"))
                        if sell_x:
                            fig.add_trace(go.Scatter(x=sell_x, y=sell_y, mode='markers', marker=dict(symbol='triangle-down', size=13, color='cyan', line=dict(width=1, color='black')), name='💸 매도', hovertemplate="%{y:,.0f}원"))

                        fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', line=dict(color='rgba(231, 76, 60, 0.9)', width=2.5, dash='dot'), name='🔴 익절 궤적'))
                        fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', line=dict(color='rgba(52, 152, 219, 0.9)', width=2.5, dash='dot'), name='🔵 손절 궤적'))

                        fig.update_layout(
                            height=450, margin=dict(l=20, r=20, t=30, b=20), xaxis_rangeslider_visible=False, template='plotly_white', hovermode='x unified',
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                        fig.update_yaxes(tickformat=",.0f", ticksuffix="원")
                        fig.update_xaxes(tickformat="%Y-%m-%d", hoverformat="%Y년 %m월 %d일")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.write("해당 종목의 차트 데이터를 불러올 수 없습니다.")

else:
    st.info("👈 왼쪽 사이드바에서 옵션을 확인하고 [▶️ 작전 개시!] 버튼을 눌러주세요.")
