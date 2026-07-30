import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
from dateutil.relativedelta import relativedelta
import base64

# --- ⚙️ 스트림릿 기본 설정 및 CSS ---
st.set_page_config(page_title="박가이버표 통합 작전 사령부 V10.4", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    @keyframes blinker { 50% { opacity: 0.6; } }
    .siren-box {
        background-color: #ffebee; border: 2px solid #e74c3c; border-left: 10px solid #c0392b; 
        border-radius: 8px; padding: 20px; margin-bottom: 20px; animation: blinker 1.5s linear infinite;
    }
    .clear-box {
        background-color: #e8f8f5; border: 1px solid #2ecc71; border-left: 10px solid #27ae60; 
        border-radius: 8px; padding: 20px; margin-bottom: 20px;
    }
    .metric-card {
        background: white; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center;
    }
    .metric-title { font-size: 0.9rem; color: #64748b; font-weight: bold; margin-bottom: 5px; }
    .metric-value { font-size: 1.5rem; color: #0f172a; font-weight: 900; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align: center; color: #1e293b; font-weight: 900;'>🛡️ 박가이버표 작전 통제실 V10.4 (태풍 경보 & 유연 슬롯 장착)</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b;'>시장의 날씨를 직관적으로 감지하고, 남은 현금을 빈 슬롯에 100% 꽉 채워 출동시킵니다!</p><hr>", unsafe_allow_html=True)

# --- 📋 사이드바: 작전 통제 설정 ---
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
    selected_option = st.selectbox("🎯 작전 종목 선택", list(stock_dict.keys()))
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
    
    reinvest_rate = st.selectbox("🔄 재투자 비율", ['70% 복리재투자 (자산 형성기)', '50% 복리재투자', '100% 전액 풀복리', '0% 단리 운용'])
    
    years = st.number_input("🗓️ 백테스트 조회(년)", min_value=1, value=5, step=1)
    run_button = st.button("▶️ 퀀트 시뮬레이션 가동!", use_container_width=True, type="primary")

# --- 🚀 작전 시뮬레이션 알고리즘 ---
if run_button and ticker:
    with st.spinner("📡 구글 슈퍼컴퓨터가 대한민국 증시 날씨와 작전 데이터를 분석 중입니다..."):
        
        # 1. 설정 파싱
        entry_drop_threshold = float(entry_drop_str.split('%')[0])
        re_rate = float(reinvest_rate.split('%')[0]) / 100.0 if '%' in reinvest_rate else 0.0
        use_index_filter = '켜기' in index_filter_str
        
        end_date = datetime.datetime.today()
        start_date = end_date - relativedelta(years=years + 1)
        user_start_date = end_date - relativedelta(years=years)
        
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

        # 3. 🌟 유연한 자금 관리 엔진 변수
        current_cash_balance = float(initial_capital) # 금고에 있는 실제 현금
        baseline_capital = float(initial_capital)     # 레벨업 기준 자산
        step_progress = 0.0
        level_up_count = 0
        
        positions = []
        matched_trades = []
        agent_counter = 0

        BUY_FEE_RATE = 0.00015
        SELL_FEE_TAX_RATE = 0.00195

        for date, row in df.iterrows():
            close = float(row['Close'])
            daily_return = float(row['Daily_Return'])
            if pd.isna(daily_return): continue

            ma5, ma20, ma60, ma120, ma200 = row['MA5'], row['MA20'], row['MA60'], row['MA120'], row['MA200']
            
            # 지수 기상청 확인
            index_is_bear = False
            if date in target_idx_df.index:
                idx_close = float(target_idx_df.loc[date, 'Close'])
                idx_ma20 = float(target_idx_df.loc[date, 'Idx_MA20']) if not pd.isna(target_idx_df.loc[date, 'Idx_MA20']) else idx_close
                index_is_bear = (idx_close < idx_ma20)

            # --- [1단계] 매도 (손절 및 타임컷) ---
            updated_positions = []
            for pos in positions:
                curr_ret = ((close - pos['entry_price']) / pos['entry_price']) * 100
                holding_days = (date - pos['entry_dt']).days
                
                if (curr_ret <= stop_loss and holding_days > 0) or holding_days >= 60:
                    shares = pos['shares']
                    sell_amount_net = (shares * close) * (1 - SELL_FEE_TAX_RATE)
                    buy_amount_net = (shares * pos['entry_price']) * (1 + BUY_FEE_RATE)
                    profit_krw = sell_amount_net - buy_amount_net
                    
                    # 🌟 판 돈은 다시 현금 금고로 회수!
                    current_cash_balance += sell_amount_net 
                    
                    matched_trades.append({
                        'agent_name': pos['name'], 'entry_date': pos['entry_date'], 'exit_date': date.strftime('%Y-%m-%d'),
                        'entry_price': pos['entry_price'], 'exit_price': close, 'ret': (profit_krw/buy_amount_net)*100,
                        'profit': profit_krw, 'type': f"🚨 강제손절/타임컷 ({curr_ret:.1f}%)"
                    })
                else:
                    updated_positions.append(pos)
            positions = updated_positions

            # --- [2단계] 매도 (하이브리드 익절) ---
            has_winner = False
            for pos in positions:
                curr_ret = ((close - pos['entry_price']) / pos['entry_price']) * 100
                if curr_ret >= 10.0:
                    if (ma5 > ma20) and (close >= ma5): pos['trailing'] = True
                    else: has_winner = True; break
                elif pos.get('trailing', False) and (close < ma5 or ma5 < ma20):
                    has_winner = True; break

            if has_winner and len(positions) > 0:
                batch_profit = 0.0
                for pos in positions:
                    shares = pos['shares']
                    sell_amount_net = (shares * close) * (1 - SELL_FEE_TAX_RATE)
                    buy_amount_net = (shares * pos['entry_price']) * (1 + BUY_FEE_RATE)
                    profit_krw = sell_amount_net - buy_amount_net
                    
                    # 🌟 전원 매도 후 현금 금고로 싹쓸이 회수!
                    current_cash_balance += sell_amount_net
                    
                    if profit_krw > 0: batch_profit += profit_krw * re_rate
                    
                    matched_trades.append({
                        'agent_name': pos['name'], 'entry_date': pos['entry_date'], 'exit_date': date.strftime('%Y-%m-%d'),
                        'entry_price': pos['entry_price'], 'exit_price': close, 'ret': (profit_krw/buy_amount_net)*100,
                        'profit': profit_krw, 'type': "🔥 하이브리드 익절" if pos.get('trailing', False) else "🎉 목표달성"
                    })
                positions = []
                
                # 레벨업 스노우볼 로직
                if re_rate > 0:
                    step_progress += batch_profit
                    if step_progress >= baseline_capital * 0.10:
                        level_up_count += 1
                        baseline_capital += baseline_capital * 0.10
                        step_progress = 0.0
                        matched_trades[-1]['type'] = f"🚀 레벨UP #{level_up_count}!"

            # --- [3단계] 신규 파견 (🌟 유연한 슬롯 자금 분배 엔진) ---
            is_super_bear = (close < ma20) and (ma20 < ma60) and (ma60 < ma120)
            should_enter = False
            
            if use_index_filter and index_is_bear:
                should_enter = False
            elif is_super_bear and '자제' in bear_filter_str:
                should_enter = False
            else:
                should_enter = (daily_return <= entry_drop_threshold)

            available_slots = max_agents - len(positions)
            
            # 조건 만족하고, 빈 슬롯이 있으며, 금고에 현금이 주식 1주 살 돈 이상 있을 때 출격!
            if should_enter and available_slots > 0 and current_cash_balance > close:
                agent_counter += 1
                
                # 🌟 [혁신 로직] 남은 현금을 빈 슬롯 개수로 정확히 N빵하여 유연하게 꽉 채워줍니다!
                agent_budget = int(current_cash_balance // available_slots)
                
                shares_to_buy = int(agent_budget // (close * (1 + BUY_FEE_RATE)))
                if shares_to_buy > 0:
                    buy_amount_net = shares_to_buy * close * (1 + BUY_FEE_RATE)
                    
                    # 금고에서 실탄(현금) 인출
                    current_cash_balance -= buy_amount_net
                    
                    positions.append({
                        'name': f"{agent_counter}호 요원", 'entry_price': close, 
                        'entry_date': date.strftime('%Y-%m-%d'), 'entry_dt': date, 
                        'shares': shares_to_buy, 'trailing': False
                    })

        # --- 📊 결과 화면 렌더링 ---
        # 1. 🚨 기상청 시각화 배너 (스트림릿 전용)
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
            action_msg = "<span style='color:#27ae60;'><b>✅ [순풍 돛단배 모드]</b></span> 시장이 든든하게 받쳐주고 있습니다. 급락 타점이 오면 요원들이 100% 꽉 채워 기동합니다!"
            st.markdown(f"""
            <div class="clear-box">
                <h3 style="color: #27ae60; margin: 0 0 5px 0;">☀️ [시장 날씨 맑음] 바다가 잔잔하고 순풍이 불고 있습니다! ☀️</h3>
                <p style="color: #2c3e50; font-size: 15px; margin: 0;">
                    현재 <b>{target_market} 지수({latest_idx_close:,.1f}pt)</b>가 20일선({latest_idx_ma20:,.1f}pt) 위에서 안정적으로 상승 중입니다.<br>
                    {action_msg}
                </p>
            </div>
            """, unsafe_allow_html=True)

        # 2. 요약 지표 카드
        final_price = float(df['Close'].iloc[-1])
        active_eval = sum([p['shares'] * final_price * (1 - SELL_FEE_TAX_RATE) for p in positions])
        total_profit = sum([t['profit'] for t in matched_trades])
        total_equity = current_cash_balance + active_eval
        win_count = len([t for t in matched_trades if t['profit'] > 0])
        win_rate = (win_count / len(matched_trades) * 100) if matched_trades else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='metric-card'><div class='metric-title'>🎯 청산 승률</div><div class='metric-value'>{win_rate:.1f}%</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'><div class='metric-title'>💰 누적 실현 순수익</div><div class='metric-value' style='color:#e74c3c;'>{format_money(total_profit)}원</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-card'><div class='metric-title'>🛡️ 현재 금고 현금(예수금)</div><div class='metric-value' style='color:#2980b9;'>{format_money(current_cash_balance)}원</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='metric-card'><div class='metric-title'>🚀 계좌 총자산</div><div class='metric-value'>{format_money(total_equity)}원</div></div>", unsafe_allow_html=True)

        st.write("---")
        st.subheader(f"📜 전체 청산 거래 장부 (총 {len(matched_trades)}건)")
        
        if matched_trades:
            df_trades = pd.DataFrame(matched_trades)
            df_trades.columns = ['요원명', '파견일', '청산일', '매수단가', '청산단가', '순수익률(%)', '순손익금(원)', '작전유형']
            
            # 순수익률 포맷팅
            df_trades['순수익률(%)'] = df_trades['순수익률(%)'].apply(lambda x: f"{x:+.2f}%")
            df_trades['순손익금(원)'] = df_trades['순손익금(원)'].apply(lambda x: f"{int(x):,}원")
            df_trades['매수단가'] = df_trades['매수단가'].apply(lambda x: f"{int(x):,}원")
            df_trades['청산단가'] = df_trades['청산단가'].apply(lambda x: f"{int(x):,}원")
            
            st.dataframe(df_trades[::-1], use_container_width=True, hide_index=True)
        else:
            st.info("아직 청산 완료된 작전이 없습니다.")
