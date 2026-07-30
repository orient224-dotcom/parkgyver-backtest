import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta
import base64

# 🌟 에러의 원인이었던 format_money 함수 복구!
def format_money(num):
    return f"{int(round(num)):,}"

def create_download_link(df, filename="작전_최상위_완결장부.csv"):
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    b64 = base64.b64encode(csv.encode()).decode()
    payload = f"data:text/csv;base64,{b64}"
    html = f'''
    <a download="{filename}" href="{payload}" target="_blank"
       style="display:inline-block; padding:12px 24px; background-color:#27ae60; color:white;
              text-decoration:none; border-radius:6px; font-weight:bold; font-size:14px; margin-top:15px; box-shadow:0 2px 5px rgba(0,0,0,0.15);">
       📥 완결판 작전 장부 CSV 다운로드
    </a>
    '''
    return html

# --- ⚙️ 스트림릿 기본 설정 및 CSS ---
st.set_page_config(page_title="박가이버표 통합 작전 사령부 V10.5", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    @keyframes blinker { 50% { opacity: 0.6; } }
    .siren-box {
        background-color: #ffebee; border: 2px solid #e74c3c; border-left: 10px solid #c0392b; 
        border-radius: 8px; padding: 18px 24px; margin-bottom: 25px; animation: blinker 1.5s linear infinite;
    }
    .clear-box {
        background-color: #e8f8f5; border: 1px solid #2ecc71; border-left: 10px solid #27ae60; 
        border-radius: 8px; padding: 18px 24px; margin-bottom: 25px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align: center; color: #1e293b; font-weight: 900;'>🛡️ 박가이버표 작전 통제실 V10.5 (풀버전 대시보드 복원)</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b;'>기존의 강력한 풀버전 대시보드에 기상청 사이렌과 유연한 슬롯 자금 배분(N빵) 엔진을 통합했습니다.</p><hr>", unsafe_allow_html=True)

# --- 📋 사이드바: 작전 통제 제어판 ---
with st.sidebar:
    st.header("⚙️ 작전 통제 제어판")
    
    stock_dict = {
        '📈 069500.KS | KODEX 200 (코스피 대표 지수)': '069500.KS',
        '📈 229200.KS | KODEX 코스닥150 (코스닥 대표 지수)': '229200.KS',
        '089030.KQ | 테크윙 (KOSDAQ 주도주)': '089030.KQ',
        '005930.KS | 삼성전자 (KOSPI 대장주)': '005930.KS',
        '403870.KQ | HPSP (반도체 장비)': '403870.KQ',
        '042700.KS | 한미반도체 (HBM 대장주)': '042700.KS',
        '✏️ 직접 입력': 'CUSTOM'
    }
    selected_option = st.selectbox("🎯 작전 종목 선택", list(stock_dict.keys()), index=2)
    ticker = st.text_input("✏️ 직접 입력 (예: 005930.KS)") if selected_option == '✏️ 직접 입력' else stock_dict[selected_option]
    
    initial_capital = st.number_input("💰 초기 총투자금(원)", min_value=1000000, value=10000000, step=1000000)
    max_agents = st.number_input("⚔️ 최대 출동 요원 수 (슬롯)", min_value=1, value=5, step=1)
    
    entry_drop_str = st.selectbox("📉 출격 기준", [
        '-3.5% 대장주/ETF 맞춤 출격 (추천 🔥)', '-4.0% 대장주 스탠다드 출격', '-5.0% 하락 시 출격', '-7.0% 폭락 시 출격'
    ])
    
    index_filter_str = st.selectbox("🌤️ 지수 경보 시스템", [
        '🌦️ 지수 연동 경보 켜기 (하락장 출격 통제)', '🔓 지수 연동 경보 끄기 (차트만 보고 돌격)'
    ])
    
    bear_filter_str = st.selectbox("🛡️ 종목 방어 필터", [
        '🌧️ 완전역배열 출격 완전 자제 (일시정지)', '🚨 완전역배열 시 -10% 대폭락일에만 파견', '🔓 필터 미적용'
    ])
    
    stop_loss = st.slider("🛑 종가 손절선(%)", -20.0, -3.0, -10.0, 0.5)
    
    target_mode = st.selectbox("📈 목표가 모드", [
        '🔥 하이브리드 추세연장 (목표 달성 시 5일>20일선 추세 홀딩)',
        '기존 고정형 (무조건 +5%)'
    ])
    
    reinvest_rate_str = st.selectbox("🔄 재투자 비율", [
        '🚀 70% 복리재투자 (자산 형성기)', '🌳 50% 복리재투자', '🔥 100% 전액 풀복리', '💰 0% 단리 운용'
    ])
    
    years = st.number_input("🗓️ 백테스트 조회(년)", min_value=1, value=5, step=1)
    run_button = st.button("▶️ 퀀트 시뮬레이션 가동!", use_container_width=True, type="primary")

# --- 🚀 작전 시뮬레이션 알고리즘 ---
if run_button and ticker:
    with st.spinner("📡 구글 슈퍼컴퓨터가 대한민국 증시 날씨와 작전 데이터를 분석 중입니다..."):
        
        # 1. 설정 파싱
        if '-3.5%' in entry_drop_str: entry_drop_threshold = -3.5
        elif '-4.0%' in entry_drop_str: entry_drop_threshold = -4.0
        elif '-5.0%' in entry_drop_str: entry_drop_threshold = -5.0
        else: entry_drop_threshold = -7.0

        if '70%' in reinvest_rate_str: reinvest_rate = 0.70
        elif '50%' in reinvest_rate_str: reinvest_rate = 0.50
        elif '100%' in reinvest_rate_str: reinvest_rate = 1.00
        else: reinvest_rate = 0.00

        use_index_filter = '켜기' in index_filter_str
        
        end_date = datetime.datetime.today()
        user_start_date = end_date - relativedelta(years=years)
        start_date = user_start_date - relativedelta(years=1)
        period_desc = f"최근 {years}년 ({user_start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')})"
        
        # 2. 데이터 다운로드
        df = yf.download(ticker, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)
        df_kospi = yf.download('^KS11', start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)
        df_kosdaq = yf.download('^KQ11', start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)
        
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        if isinstance(df_kospi.columns, pd.MultiIndex): df_kospi.columns = df_kospi.columns.get_level_values(0)
        if isinstance(df_kosdaq.columns, pd.MultiIndex): df_kosdaq.columns = df_kosdaq.columns.get_level_values(0)
        
        df_kospi['Idx_MA20'] = df_kospi['Close'].rolling(window=20).mean()
        df_kosdaq['Idx_MA20'] = df_kosdaq['Close'].rolling(window=20).mean()
        
        target_market = '코스닥' if (ticker.endswith('.KQ') or '229200' in ticker or '233740' in ticker) else '코스피'
        target_idx_df = df_kosdaq if target_market == '코스닥' else df_kospi

        df['Daily_Return'] = df['Close'].pct_change() * 100
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['MA120'] = df['Close'].rolling(window=120).mean()
        df['MA200'] = df['Close'].rolling(window=200).mean()
        
        df = df[(df.index >= user_start_date.strftime('%Y-%m-%d')) & (df.index <= end_date.strftime('%Y-%m-%d'))].copy()

        if df.empty:
            st.error("해당 기간의 데이터를 불러올 수 없습니다.")
            st.stop()

        # 3. 🌟 시스템 변수 초기화
        current_cash_balance = float(initial_capital) # 실제 남은 현금 (예수금)
        baseline_capital = float(initial_capital)     # 레벨업 스노우볼 기준 자산
        step_progress = 0.0
        level_up_count = 0
        step_down_count = 0
        
        positions = []
        matched_trades = []
        agent_counter = 0
        batch_agent_counts = []
        yearly_stats = {}

        total_trades, win_trades, loss_trades = 0, 0, 0
        BUY_FEE_RATE = 0.00015
        SELL_FEE_TAX_RATE = 0.00195

        for date, row in df.iterrows():
            close = float(row['Close'])
            daily_return = float(row['Daily_Return'])
            if pd.isna(daily_return): continue

            ma5, ma20, ma60, ma120, ma200 = row['MA5'], row['MA20'], row['MA60'], row['MA120'], row['MA200']
            year = date.year
            date_str = date.strftime('%Y-%m-%d')
            
            if year not in yearly_stats:
                yearly_stats[year] = {'deployed': 0, 'missions': 0, 'buy_sum': 0, 'sell_sum': 0, 'cash': 0}

            # 지수 기상청 확인
            index_is_bear = False
            if date in target_idx_df.index:
                idx_close = float(target_idx_df.loc[date, 'Close'])
                idx_ma20 = float(target_idx_df.loc[date, 'Idx_MA20']) if not pd.isna(target_idx_df.loc[date, 'Idx_MA20']) else idx_close
                index_is_bear = (idx_close < idx_ma20)

            # --- 🛡️ 0. 개별 포지션 종가 강제 손절 및 타임컷 ---
            updated_positions = []
            for pos in positions:
                curr_ret = ((close - pos['entry_price']) / pos['entry_price']) * 100
                holding_days = (date - pos['entry_dt']).days
                
                is_stop_loss = (holding_days > 0) and (curr_ret <= stop_loss)
                is_time_cut = (holding_days >= 60)
                
                if is_stop_loss or is_time_cut:
                    shares = pos['shares']
                    buy_gross = shares * pos['entry_price']
                    buy_fee = buy_gross * BUY_FEE_RATE
                    buy_amount_net = buy_gross + buy_fee

                    sell_gross = shares * close
                    sell_fee_tax = sell_gross * SELL_FEE_TAX_RATE
                    sell_amount_net = sell_gross - sell_fee_tax

                    profit_krw = sell_amount_net - buy_amount_net
                    ret = (profit_krw / buy_amount_net) * 100

                    # 판 돈 회수!
                    current_cash_balance += sell_amount_net 
                    
                    total_trades += 1
                    loss_trades += 1
                    yearly_stats[year]['missions'] += 1
                    yearly_stats[year]['buy_sum'] += buy_amount_net
                    yearly_stats[year]['sell_sum'] += sell_amount_net
                    yearly_stats[year]['cash'] += profit_krw

                    exit_type = f"🚨 종가 강제손절({stop_loss}%)" if is_stop_loss else "⏳ 타임 컷(60일)"
                    matched_trades.append({
                        'agent_name': pos['name'], 'entry_date': pos['entry_date'], 'exit_date': date_str,
                        'entry_price': pos['entry_price'], 'exit_price': close, 'entry_return': pos.get('entry_return', 0),
                        'market_regime': pos['regime_desc'], 'target_ret': pos['target_ret'], 'shares': shares,
                        'buy_amount': buy_amount_net, 'sell_amount': sell_amount_net, 'profit_krw': profit_krw,
                        'free_shares_gained': 0, 'ret': ret, 'duration': holding_days, 'is_win': False,
                        'snowball_event': exit_type, 'trailing_active': False
                    })
                else:
                    updated_positions.append(pos)
            positions = updated_positions

            # --- 🎯 1. 하이브리드 추세연장 익절 ---
            has_winner = False
            for pos in positions:
                curr_ret = ((close - pos['entry_price']) / pos['entry_price']) * 100
                if curr_ret >= pos['target_ret']:
                    if '하이브리드' in target_mode:
                        if (ma5 > ma20) and (close >= ma5): pos['trailing_active'] = True
                        else: has_winner = True; break
                    else: has_winner = True; break
                elif pos.get('trailing_active', False):
                    if close < ma5 or ma5 < ma20: has_winner = True; break

            if has_winner and len(positions) > 0:
                batch_agent_counts.append(len(positions))
                batch_reinvest_profit = 0.0
                
                for pos in positions:
                    shares = pos['shares']
                    buy_gross = shares * pos['entry_price']
                    buy_fee = buy_gross * BUY_FEE_RATE
                    buy_amount_net = buy_gross + buy_fee

                    sell_gross = shares * close
                    sell_fee_tax = sell_gross * SELL_FEE_TAX_RATE
                    sell_amount_net = sell_gross - sell_fee_tax

                    profit_krw = sell_amount_net - buy_amount_net
                    ret = (profit_krw / buy_amount_net) * 100

                    # 🌟 매도 후 전액 현금 금고로 싹쓸이 회수!
                    current_cash_balance += sell_amount_net
                    
                    if profit_krw > 0: batch_reinvest_profit += profit_krw * reinvest_rate
                    
                    total_trades += 1
                    if profit_krw >= 0: win_trades += 1
                    else: loss_trades += 1

                    yearly_stats[year]['missions'] += 1
                    yearly_stats[year]['buy_sum'] += buy_amount_net
                    yearly_stats[year]['sell_sum'] += sell_amount_net
                    yearly_stats[year]['cash'] += profit_krw

                    matched_trades.append({
                        'agent_name': pos['name'], 'entry_date': pos['entry_date'], 'exit_date': date_str,
                        'entry_price': pos['entry_price'], 'exit_price': close, 'entry_return': pos.get('entry_return', 0),
                        'market_regime': pos['regime_desc'], 'target_ret': pos['target_ret'], 'shares': shares,
                        'buy_amount': buy_amount_net, 'sell_amount': sell_amount_net, 'profit_krw': profit_krw,
                        'free_shares_gained': 0, 'ret': ret, 'duration': (date - pos['entry_dt']).days, 'is_win': profit_krw >= 0,
                        'snowball_event': '', 'trailing_active': pos.get('trailing_active', False)
                    })
                
                # 레벨업 로직
                if reinvest_rate > 0:
                    step_progress += batch_reinvest_profit
                    threshold = baseline_capital * 0.10
                    if step_progress >= threshold:
                        level_up_count += 1
                        baseline_capital += threshold
                        step_progress = 0.0
                        matched_trades[-1]['snowball_event'] = f"🚀 레벨UP #{level_up_count}!"
                    elif step_progress <= -threshold and baseline_capital > initial_capital:
                        step_down_count += 1
                        baseline_capital -= threshold
                        step_progress = 0.0
                        matched_trades[-1]['snowball_event'] = f"🛡️ 스텝다운 #{step_down_count}!"
                
                positions = []

            # --- 🛒 2. 신규 파견 (🌟 N빵 유연 슬롯 엔진) ---
            is_super_bull = (close > ma20) and (ma20 > ma60) and (ma60 > ma120)
            is_mid_bull = (ma20 > ma60) or (close > ma60 > ma120)
            is_super_bear = (close < ma20) and (ma20 < ma60) and (ma60 < ma120)

            should_enter = False
            if use_index_filter and index_is_bear: should_enter = False
            elif is_super_bear:
                if '일시정지' in bear_filter_str: should_enter = False 
                elif '-10%' in bear_filter_str: should_enter = (daily_return <= -10.0) 
                else: should_enter = (daily_return <= entry_drop_threshold) 
            else:
                should_enter = (daily_return <= entry_drop_threshold)

            available_slots = max_agents - len(positions)
            
            # 조건 만족, 빈 슬롯 존재, 주식 1주라도 살 돈이 현금 금고에 있을 때!
            if should_enter and available_slots > 0 and current_cash_balance > close:
                agent_counter += 1
                yearly_stats[year]['deployed'] += 1

                # 🌟 [핵심 마법 로직] 남은 현금을 빈 슬롯 개수로 똑같이 N빵하여 유연하게 채워줍니다!
                agent_budget = int(current_cash_balance // available_slots)
                shares_to_buy = int(agent_budget // (close * (1 + BUY_FEE_RATE)))

                if shares_to_buy > 0:
                    buy_amount_net = shares_to_buy * close * (1 + BUY_FEE_RATE)
                    
                    # 금고에서 실탄(현금) 인출
                    current_cash_balance -= buy_amount_net

                    if '하이브리드' in target_mode:
                        if is_super_bull: target_ret, regime_desc = 10.0, "🔥 완전정배열(+10%)"
                        elif is_mid_bull: target_ret, regime_desc = 10.0, "📈 중기정배열(+10%)"
                        elif is_super_bear: target_ret, regime_desc = 5.0, "🌧️ 완전역배열(+5%)"
                        else: target_ret, regime_desc = 5.0, "🧱 박스권(+5%)"
                    else:
                        target_ret, regime_desc = 5.0, "📌 고정목표(+5%)"

                    positions.append({
                        'name': f"{agent_counter}호 요원", 'entry_price': close, 'entry_date': date_str, 'entry_dt': date,
                        'entry_return': daily_return, 'shares': shares_to_buy, 'regime_desc': regime_desc,
                        'target_ret': target_ret, 'trailing_active': False
                    })

        # --- 📊 정밀 자산 및 회계 집계 ---
        final_price = float(df['Close'].iloc[-1])
        active_positions_eval_sum = sum(p['shares'] * final_price * (1 - SELL_FEE_TAX_RATE) for p in positions)
        sum_trade_net_profit = sum([t['profit_krw'] for t in matched_trades])
        total_portfolio_net_profit = sum_trade_net_profit + (active_positions_eval_sum - sum(p['shares']*p['entry_price']*(1+BUY_FEE_RATE) for p in positions))
        actual_total_equity = current_cash_balance + active_positions_eval_sum
        win_rate_val = (win_trades / total_trades * 100) if total_trades > 0 else 0

        # --- 🚨 [1] 시각화 배너 (태풍 사이렌 vs 맑음) 생성 ---
        latest_idx_close = float(target_idx_df['Close'].dropna().iloc[-1])
        latest_idx_ma20 = float(target_idx_df['Idx_MA20'].dropna().iloc[-1])
        market_is_stormy = (latest_idx_close < latest_idx_ma20)

        if market_is_stormy:
            action_msg = "<span style='color:#c0392b;'><b>🚨 [출격 강제 정지]</b></span> 지수 연동 필터가 작동하여 위험한 바다에 요원을 보내지 않고 현금을 지킵니다!" if use_index_filter else "<span style='color:#2980b9;'>🔓 지수 경보는 꺼져있어 개별 종목 타점만 보고 돌격합니다. (위험 주의)</span>"
            st.markdown(f"""
            <div class="siren-box">
                <h3 style="color: #c0392b; margin: 0 0 5px 0;">🚨 [비상 경보] 대한민국 증시 앞바다 초대형 태풍 발령 중! 🚨</h3>
                <p style="color: #2c3e50; font-size: 15px; margin: 0;">
                    현재 <b>{target_market} 지수({latest_idx_close:,.1f}pt)</b>가 20일선({latest_idx_ma20:,.1f}pt) 아래로 무너져 <b>[철벽 수비 모드]</b> 구간입니다.<br>
                    {action_msg}
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            action_msg = "<span style='color:#27ae60;'><b>✅ [순풍 돛단배 모드]</b></span> 시장이 든든하게 받쳐주고 있습니다. 타점이 오면 요원들이 N빵으로 100% 꽉 채워 기동합니다!"
            st.markdown(f"""
            <div class="clear-box">
                <h3 style="color: #27ae60; margin: 0 0 5px 0;">☀️ [시장 날씨 맑음] 바다가 잔잔하고 순풍이 불고 있습니다! ☀️</h3>
                <p style="color: #2c3e50; font-size: 15px; margin: 0;">
                    현재 <b>{target_market} 지수({latest_idx_close:,.1f}pt)</b>가 20일선({latest_idx_ma20:,.1f}pt) 위에서 안정적으로 상승 중입니다.<br>
                    {action_msg}
                </p>
            </div>
            """, unsafe_allow_html=True)

        # --- 📊 [2] 기존 풀버전 HTML 대시보드 복원 렌더링 ---
        tot_deployed = sum(st['deployed'] for st in yearly_stats.values())
        tot_missions = sum(st['missions'] for st in yearly_stats.values())
        tot_buy_sum = sum(st['buy_sum'] for st in yearly_stats.values())
        tot_sell_sum = sum(st['sell_sum'] for st in yearly_stats.values())
        tot_cash_sum = sum(st['cash'] for st in yearly_stats.values())
        tot_cash_color = "#c0392b" if tot_cash_sum >= 0 else "#2980b9"
        tot_cash_sign = "+" if tot_cash_sum >= 0 else ""

        html_content = f"""
        <div style='font-family: sans-serif;'>
            <!-- 상단 요약 카드 1열 -->
            <div style='display: flex; gap: 8px; margin-bottom: 8px;'>
                <div style='flex: 1; background: #e8f6f3; padding: 12px; border-radius: 8px; border-left: 5px solid #1abc9c;'>
                    <h5 style='margin: 0; color: #16a085;'>🎯 청산 승률</h5>
                    <h3 style='margin: 5px 0 0 0; color: #2c3e50;'>{win_rate_val:.1f}%</h3>
                    <span style='font-size: 11px; color: #7f8c8d;'>익절 {win_trades} / 손절 {loss_trades}</span>
                </div>
                <div style='flex: 1.1; background: #ebf5fb; padding: 12px; border-radius: 8px; border-left: 5px solid #3498db;'>
                    <h5 style='margin: 0; color: #2980b9;'>⚔️ 총 투입 요원</h5>
                    <h3 style='margin: 5px 0 0 0; color: #2c3e50;'>{agent_counter}명</h3>
                    <span style='font-size: 11px; color: #7f8c8d;'>총 누적 투입 요원 수</span>
                </div>
                <div style='flex: 1.2; background: #fffde7; padding: 12px; border-radius: 8px; border-left: 5px solid #f1c40f;'>
                    <h5 style='margin: 0; color: #b7950b;'>🚀 스노우볼 레벨UP</h5>
                    <h3 style='margin: 5px 0 0 0; color: #d35400;'>{level_up_count}회 <span style='font-size:12px; color:#7f8c8d; font-weight:normal;'>(스텝다운 {step_down_count}회)</span></h3>
                    <span style='font-size: 11px; color: #7f8c8d;'>수익 축적에 따른 예산 파이 증액</span>
                </div>
            </div>

            <!-- 상단 요약 카드 2열 -->
            <div style='display: flex; gap: 8px; margin-bottom: 15px;'>
                <div style='flex: 1.3; background: #eaf2f8; padding: 12px; border-radius: 8px; border-left: 5px solid #2980b9;'>
                    <h5 style='margin: 0; color: #1b4f72;'>💵 현재 보유 현금 (예수금)</h5>
                    <h3 style='margin: 5px 0 0 0; color: #1b4f72;'>{format_money(current_cash_balance)}원</h3>
                    <span style='font-size: 11px; color: #5d6d7e;'>즉시 투입 가능한 실탄 현금</span>
                </div>
                <div style='flex: 1.2; background: #fef9e7; padding: 12px; border-radius: 8px; border-left: 5px solid #f39c12;'>
                    <h5 style='margin: 0; color: #b7950b;'>📈 대기주식 평가금</h5>
                    <h3 style='margin: 5px 0 0 0; color: #2c3e50;'>{format_money(active_positions_eval_sum)}원</h3>
                    <span style='font-size: 11px; color: #7f8c8d;'>미귀환 요원 {len(positions)}명 주식 평가가</span>
                </div>
                <div style='flex: 1.2; background: #fdf2e9; padding: 12px; border-radius: 8px; border-left: 5px solid #e67e22;'>
                    <h5 style='margin: 0; color: #d35400;'>💰 누적 실현 순수익</h5>
                    <h3 style='margin: 5px 0 0 0; color: #2c3e50;'>{format_money(sum_trade_net_profit)}원</h3>
                    <span style='font-size: 11px; color: #7f8c8d;'>순수 매매 확정 차익</span>
                </div>
                <div style='flex: 1.3; background: #fef5e7; padding: 12px; border-radius: 8px; border-left: 5px solid #d35400;'>
                    <h5 style='margin: 0; color: #a04000;'>🚀 계좌 총자산</h5>
                    <h3 style='margin: 5px 0 0 0; color: #2c3e50;'>{format_money(actual_total_equity)}원</h3>
                    <span style='font-size: 11px; color: #7f8c8d;'>현금 + 대기주식 총합</span>
                </div>
            </div>

            <!-- 🗓️ 연도별 작전 성과표 -->
            <h3 style='color: #34495e; margin-bottom: 10px;'>🗓️ 연도별 작전 성과표</h3>
            <table style='width: 100%; border-collapse: collapse; text-align: center; margin-bottom: 20px;'>
                <tr style='background-color: #34495e; color: white;'>
                    <th style='padding: 8px; border: 1px solid #bdc3c7;'>연도</th>
                    <th style='padding: 8px; border: 1px solid #bdc3c7;'>파견 횟수</th>
                    <th style='padding: 8px; border: 1px solid #bdc3c7;'>총 청산 건수</th>
                    <th style='padding: 8px; border: 1px solid #bdc3c7;'>총 매수금액</th>
                    <th style='padding: 8px; border: 1px solid #bdc3c7;'>총 매도금액</th>
                    <th style='padding: 8px; border: 1px solid #bdc3c7;'>누적 순손익</th>
                </tr>
        """
        for y in sorted(yearly_stats.keys()):
            st_yr = yearly_stats[y]
            color = "#c0392b" if st_yr['cash'] >= 0 else "#2980b9"
            sign = "+" if st_yr['cash'] >= 0 else ""
            html_content += f"""
                <tr>
                    <td style='padding: 8px; border: 1px solid #bdc3c7; font-weight: bold;'>{y}년</td>
                    <td style='padding: 8px; border: 1px solid #bdc3c7;'>{st_yr['deployed']}명</td>
                    <td style='padding: 8px; border: 1px solid #bdc3c7; font-weight: bold;'>{st_yr['missions']}건</td>
                    <td style='padding: 8px; border: 1px solid #bdc3c7;'>{format_money(st_yr['buy_sum'])}원</td>
                    <td style='padding: 8px; border: 1px solid #bdc3c7;'>{format_money(st_yr['sell_sum'])}원</td>
                    <td style='padding: 8px; border: 1px solid #bdc3c7; color: {color}; font-weight: bold;'>{sign}{format_money(st_yr['cash'])}원</td>
                </tr>
            """
        html_content += f"""
                <tr style='background-color: #eaeded; font-weight: bold; border-top: 2px solid #2c3e50;'>
                    <td style='padding: 10px; border: 1px solid #bdc3c7; color: #2c3e50;'>🏆 누적 합계</td>
                    <td style='padding: 10px; border: 1px solid #bdc3c7; color: #2c3e50;'>{tot_deployed}명</td>
                    <td style='padding: 10px; border: 1px solid #bdc3c7; color: #2c3e50;'>{tot_missions}건</td>
                    <td style='padding: 10px; border: 1px solid #bdc3c7; color: #2c3e50;'>{format_money(tot_buy_sum)}원</td>
                    <td style='padding: 10px; border: 1px solid #bdc3c7; color: #2c3e50;'>{format_money(tot_sell_sum)}원</td>
                    <td style='padding: 10px; border: 1px solid #bdc3c7; color: {tot_cash_color}; font-size: 14px;'>{tot_cash_sign}{format_money(tot_cash_sum)}원</td>
                </tr>
        </table>
        """

        # 🚨 미귀환 요원 상세
        html_content += f"<h3 style='color: #34495e; margin-top: 25px; margin-bottom: 10px;'>🚨 현재 출동 중인 요원 상세 (미귀환 요원: {len(positions)}명)</h3>"
        if len(positions) > 0:
            html_content += """
            <div style='max-height: 400px; overflow-y: auto; border: 1px solid #ddd; margin-bottom: 25px;'>
            <table style='width: 100%; border-collapse: collapse; text-align: center;'>
                <thead style='position: sticky; top: 0; background-color: #2c3e50; color: white; z-index: 1;'>
                    <tr>
                        <th style='padding: 8px; border: 1px solid #bdc3c7;'>요원명</th>
                        <th style='padding: 8px; border: 1px solid #bdc3c7;'>파견 날짜</th>
                        <th style='padding: 8px; border: 1px solid #bdc3c7;'>매수 단가</th>
                        <th style='padding: 8px; border: 1px solid #bdc3c7;'>매수 원금</th>
                        <th style='padding: 8px; border: 1px solid #bdc3c7;'>현재 수익률<br><span style='font-size:11px;'>(주가변동률)</span></th>
                        <th style='padding: 8px; border: 1px solid #bdc3c7; background-color: #d35400;'>상태</th>
                    </tr>
                </thead>
                <tbody>
            """
            for p in positions:
                buy_amt = p['shares'] * p['entry_price'] * (1 + BUY_FEE_RATE)
                curr_amt = p['shares'] * final_price * (1 - SELL_FEE_TAX_RATE)
                ret = ((curr_amt - buy_amt) / buy_amt) * 100
                stock_change_pct = ((final_price - p['entry_price']) / p['entry_price']) * 100
                ret_color = "#c0392b" if ret > 0 else "#2980b9"
                sign = "+" if ret > 0 else ""
                
                status_str = "🔥 추세 홀딩 중" if p.get('trailing_active', False) else "⚔️ 목표가 대기"
                html_content += f"""
                <tr>
                    <td style='padding: 8px; border: 1px solid #bdc3c7; font-weight: bold;'>{p['name']}</td>
                    <td style='padding: 8px; border: 1px solid #bdc3c7;'>{p['entry_date']}</td>
                    <td style='padding: 8px; border: 1px solid #bdc3c7;'>{format_money(p['entry_price'])}원</td>
                    <td style='padding: 8px; border: 1px solid #bdc3c7;'>{format_money(buy_amt)}원</td>
                    <td style='padding: 8px; border: 1px solid #bdc3c7; color: {ret_color}; font-weight: bold;'>
                        {sign}{ret:.2f}%<br><span style='font-size:11px; font-weight:normal;'>({stock_change_pct:+.2f}%)</span>
                    </td>
                    <td style='padding: 8px; border: 1px solid #bdc3c7; font-weight: bold; color: #d35400;'>{status_str}</td>
                </tr>
                """
            html_content += "</tbody></table></div>"
        else:
            html_content += "<div style='padding: 15px; background: #e8f8f5; color: #27ae60; border-radius: 5px; font-weight: bold; text-align: center; margin-bottom: 25px;'>🎉 현재 출동(대기) 중인 요원이 없습니다! 전원 현금화 청산 완료!</div>"

        # 📜 전체 거래 장부
        html_content += f"<h3 style='color: #34495e; margin-top: 25px; margin-bottom: 10px;'>📜 전체 청산 거래 장부 (총 {len(matched_trades)}건)</h3>"
        if len(matched_trades) > 0:
            html_content += """
            <div style='max-height: 550px; overflow-y: auto; border: 1px solid #ddd; margin-bottom: 10px;'>
            <table style='width: 100%; border-collapse: collapse; text-align: center;'>
                <thead style='position: sticky; top: 0; background-color: #34495e; color: white; z-index: 1;'>
                    <tr>
                        <th style='padding: 8px; border: 1px solid #bdc3c7;'>요원명</th>
                        <th style='padding: 8px; border: 1px solid #bdc3c7; background-color: #2c3e50;'>파견일 ➔ 청산일</th>
                        <th style='padding: 8px; border: 1px solid #bdc3c7; background-color: #27ae60;'>매수 ➔ 청산단가<br><span style='font-size:11px;'>(주가변동률)</span></th>
                        <th style='padding: 8px; border: 1px solid #bdc3c7;'>매수총액 ➔ 청산총액</th>
                        <th style='padding: 8px; border: 1px solid #bdc3c7; background-color: #2c3e50;'>💰 순손익금<br><span style='font-size:11px;'>(세후수익률)</span></th>
                        <th style='padding: 8px; border: 1px solid #bdc3c7; background-color: #d4ac0d;'>이벤트 / 청산유형</th>
                        <th style='padding: 8px; border: 1px solid #bdc3c7;'>⏱️ 체류</th>
                    </tr>
                </thead>
                <tbody>
            """
            download_list = []
            for t in reversed(matched_trades):
                color = "#c0392b" if t['is_win'] else "#2980b9"
                sign = "+" if t['profit_krw'] > 0 else ""
                
                price_change_pct = ((t['exit_price'] - t['entry_price']) / t['entry_price']) * 100
                price_change_color = "#c0392b" if price_change_pct > 0 else "#2980b9"
                
                if "손절" in t['snowball_event'] or "타임" in t['snowball_event']: type_str = f"<span style='color:#c0392b; font-weight:bold;'>{t['snowball_event']}</span>"
                elif "레벨" in t['snowball_event'] or "스텝" in t['snowball_event']: type_str = f"<span style='color:#d35400; font-weight:bold;'>{t['snowball_event']}</span>"
                else:
                    if t.get('trailing_active', False) and t['ret'] >= 0: type_str = "🔥 하이브리드 익절"
                    elif t['ret'] >= t['target_ret']: type_str = "🎉 목표달성"
                    else: type_str = "🟢 소폭 익절" if t['ret'] >= 0 else "🚨 동반 손절"

                html_content += f"""
                <tr>
                    <td style='padding: 8px; border: 1px solid #bdc3c7; font-weight: bold;'>{t['agent_name']}</td>
                    <td style='padding: 8px; border: 1px solid #bdc3c7;'>{t['entry_date']} ➔ {t['exit_date']}</td>
                    <td style='padding: 8px; border: 1px solid #bdc3c7; font-weight:bold;'>
                        {format_money(t['entry_price'])}원 ➔ <span style='color:#27ae60;'>{format_money(t['exit_price'])}원</span><br>
                        <span style='font-size:11px; color:{price_change_color};'>({price_change_pct:+.2f}%)</span>
                    </td>
                    <td style='padding: 8px; border: 1px solid #bdc3c7;'>{format_money(t['buy_amount'])}원 ➔ {format_money(t['sell_amount'])}원</td>
                    <td style='padding: 8px; border: 1px solid #bdc3c7; color: {color}; font-weight: bold;'>
                        {sign}{format_money(t['profit_krw'])}원<br>
                        <span style='font-size:11px;'>({sign}{t['ret']:.2f}%)</span>
                    </td>
                    <td style='padding: 8px; border: 1px solid #bdc3c7; font-weight: bold;'>{type_str}</td>
                    <td style='padding: 8px; border: 1px solid #bdc3c7;'>{t['duration']}일</td>
                </tr>
                """
                download_list.append({
                    '요원명': t['agent_name'], '파견일': t['entry_date'], '파견일주가(원)': round(t['entry_price']),
                    '청산일': t['exit_date'], '청산일주가(원)': round(t['exit_price']), '주가변동률(%)': round(price_change_pct, 2),
                    '실현순손익금(원)': round(t['profit_krw']), '세후순수익률(%)': round(t['ret'], 2),
                    '체류기간(일)': t['duration'], '청산유형': t['snowball_event'] if t['snowball_event'] else type_str.replace("🔥 ", "").replace("🎉 ", "").replace("🟢 ", "").replace("🚨 ", "")
                })
            html_content += "</tbody></table></div>"

            df_download = pd.DataFrame(download_list)[::-1] # 원래 순서대로
            html_content += create_download_link(df_download, filename=f"{ticker}_최상위_완결장부_V10.5.csv")

        html_content += "</div>"
        
        # 렌더링!
        st.markdown(html_content, unsafe_allow_html=True)
