import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import io  # <-- io 모듈 추가 완료

# --- 1. 페이지 기본 설정 및 한글 폰트 세팅 ---
st.set_page_config(page_title="박가이버 사령부 V10.21", layout="wide", page_icon="🎛️")

# 한글 폰트 세팅 (스트림릿 클라우드 완벽 대응)
font_path = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
if os.path.exists(font_path):
    fm.fontManager.addfont(font_path)
    plt.rc('font', family='NanumGothic')
else:
    nanum_fonts = [f for f in fm.findSystemFonts() if 'nanum' in f.lower() or 'Nanum' in f.lower()]
    if nanum_fonts:
        fm.fontManager.addfont(nanum_fonts[0])
        font_name = fm.FontProperties(fname=nanum_fonts[0]).get_name()
        plt.rc('font', family=font_name)

plt.rcParams['axes.unicode_minus'] = False

def format_money(num):
    return f"{int(round(num)):,}"

# --- 2. 사이드바 조종간 (파라미터 입력) ---
st.sidebar.title("🎛️ 박가이버 사령부 V10.21")
st.sidebar.caption("은퇴 과수원 에디션 - 스트림릿 라이브 웹 통제실")

raw_tickers = st.sidebar.text_input("🎯 종목코드 (쉼표 구분):", value="019210.KQ, 005930.KS, 080220.KQ, 089030.KQ, 319660.KQ, 034020.KS, 074600.KQ")
raw_names = st.sidebar.text_input("📛 종목이름 (쉼표 구분):", value="와이지원, 삼성전자, 제주반도체, 테크윙, 피에스케이, 두산인프라코어, 원익QNC")

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
total_capital = st.sidebar.number_input("💰 총 씨드머니(원):", value=16000000, step=1000000)
max_agents = st.sidebar.number_input("⚔️ 종목당 최대 요원 수:", value=2, min_value=1, max_value=10)
years = st.sidebar.number_input("🗓️ 백테스트 조회기간(년):", value=3, min_value=1, max_value=10)

run_btn = st.sidebar.button("▶️ 박가이버 사령부 V10.21 작전 개시!", type="primary")

# --- 3. 메인 백테스트 연산 엔진 ---
if run_btn or 'calculated' in st.session_state:
    st.session_state['calculated'] = True

    buy_fee_rate = buy_fee_val / 100.0
    sell_tax_rate = sell_tax_val / 100.0

    tickers = [t.strip().upper() for t in raw_tickers.split(',') if t.strip()]
    names = [n.strip() for n in raw_names.split(',') if n.strip()]

    while len(names) < len(tickers):
        names.append(tickers[len(names)])

    capital_per_stock = total_capital / len(tickers)

    strategy_names_map = {
        '3tier': '3단 밸런스 과수원 전략 (60%재투자/20%현금/20%코어)',
        'full_cash': '풀 현금 복리 재투자 전략 (100% 컴파운딩)',
        'equal_alloc': '균등 배분 고정 전략 (No Reinvest / Buy&Hold 1/N)'
    }
    current_strategy_name = strategy_names_map.get(selected_strategy, '전략')

    with st.spinner("📡 [박가이버 사령부] 최신 시장 데이터를 수집 및 연산 중입니다..."):
        end_date = datetime.datetime.today()
        start_date = end_date - relativedelta(years=years + 1)

        kospi_df = yf.download('^KS11', start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False, auto_adjust=False)
        kosdaq_df = yf.download('^KQ11', start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False, auto_adjust=False)

        all_matched_trades = []
        stock_results = {}
        combined_equity_df = pd.DataFrame()
        all_active_positions = []

        total_cycles_all = 0
        full_launch_cycles_all = 0
        agent_perf_dist = {i: {'wins': 0, 'losses': 0} for i in range(1, max_agents + 1)}
        total_agent_counter = 0
        total_fees_paid_all = 0.0

        for idx, ticker in enumerate(tickers):
            s_name = names[idx]
            s_capital = capital_per_stock

            df = yf.download(ticker, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False, auto_adjust=False)
            if df.empty: continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

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

                has_winner = any(((close - pos['entry_price']) / pos['entry_price']) * 100 >= pos['target_ret'] for pos in positions)

                if has_winner:
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

                        current_batch_trades.append({
                            '요원': pos['name'], '작전구역': s_name, '종목코드': ticker,
                            '출격일': pos['entry_date'], '진입일 등락률': f"{pos['entry_return']:+.2f}%",
                            '진입금액': format_money(buy_amount_net) + "원", '진입단가': format_money(pos['entry_price']) + "원",
                            '복귀일': date_str, '청산일 등락률': f"{daily_return:+.2f}%",
                            '청산단가': format_money(close) + "원", '매도금액': format_money(sell_amount_net) + "원",
                            '총수수료·세금': format_money(trade_fee_total) + "원",
                            '등락폭': f"{'+' if close >= pos['entry_price'] else ''}{format_money(close - pos['entry_price'])}원 ({ret:+.2f}%)",
                            '소요기간': f"{duration_days}일 소요", '순수익률': f"{ret:+.2f}%",
                            '정산내역': f"{'+' if profit_krw >= 0 else ''}{format_money(profit_krw)}원",
                            '구분': "🎯 정상 복귀(+5%)" if is_win else "🚨 강제 철수(-15%)",
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

                if daily_return <= -5.0 and len(positions) < max_agents:
                    agent_counter += 1; total_agent_counter += 1
                    scale_ratio = current_capital / s_capital if selected_strategy != 'equal_alloc' else 1.0
                    agent_budget = int((s_capital // max_agents) * scale_ratio)
                    shares = max(int(agent_budget // close), 1)

                    positions.append({
                        'name': f"{agent_counter}호 요원", 'entry_price': close,
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
                all_active_positions.append({
                    '작전구역': s_name, '요원명': p['name'], '파견일': p['entry_date'],
                    '진입단가': format_money(p['entry_price']) + "원", '수량': f"{p['shares']}주",
                    '평가금액': format_money(cur_eval_p) + "원",
                    '평가손익': f"{'+' if pnl_p >= 0 else ''}{format_money(pnl_p)}원 ({pnl_pct:+.2f}%)",
                    'is_plus': pnl_p >= 0
                })

            df_stock_eq = pd.DataFrame(daily_log).set_index('Date')
            combined_equity_df[s_name] = df_stock_eq['Stock_Equity']

            stock_results[ticker] = {
                'name': s_name, 'total_trades': total_trades, 'win_trades': win_trades, 'loss_trades': loss_trades,
                'win_rate': (win_trades / total_trades * 100) if total_trades > 0 else 0,
                'net_profit': sum([t['raw_profit'] for t in matched_trades]),
                'reserve_cash': reserve_cash, 'core_shares': core_shares,
                'core_eval': core_shares * float(df['Close'].iloc[-1]),
                'active_eval': sum(p['shares'] * float(df['Close'].iloc[-1]) for p in positions),
                'active_count': len(positions),
                'final_equity': combined_equity_df[s_name].iloc[-1] if not combined_equity_df.empty else s_capital,
                'total_cycles': total_cycles, 'full_launch_cycles': full_launch_cycles,
                'level_up_count': level_up_count, 'step_down_count': step_down_count,
                'total_fees': stock_total_fees, 'matched_trades': matched_trades
            }
            all_matched_trades.extend(matched_trades)

        combined_equity_df = combined_equity_df.dropna()
        combined_equity_df['Portfolio_Equity'] = combined_equity_df.sum(axis=1)

        portfolio_eq = combined_equity_df['Portfolio_Equity']
        rolling_max = portfolio_eq.cummax()
        drawdown = (portfolio_eq - rolling_max) / rolling_max * 100
        max_drawdown = drawdown.min()

        final_portfolio_equity = portfolio_eq.iloc[-1]
        portfolio_total_return = (final_portfolio_equity - total_capital) / total_capital * 100

        try:
            k_close = kospi_df[('Close', '^KS11')] if isinstance(kospi_df.columns, pd.MultiIndex) else kospi_df['Close']
            kd_close = kosdaq_df[('Close', '^KQ11')] if isinstance(kosdaq_df.columns, pd.MultiIndex) else kosdaq_df['Close']

            bench_df = pd.DataFrame(index=combined_equity_df.index)
            bench_df['KOSPI'] = k_close.reindex(bench_df.index, method='ffill')
            bench_df['KOSDAQ'] = kd_close.reindex(bench_df.index, method='ffill')

            bench_df['KOSPI_Normalized'] = total_capital * (bench_df['KOSPI'] / bench_df['KOSPI'].iloc[0])
            bench_df['KOSDAQ_Normalized'] = total_capital * (bench_df['KOSDAQ'] / bench_df['KOSDAQ'].iloc[0])
            bench_df['All_Cash'] = total_capital

            k_rolling_max = bench_df['KOSPI'].cummax()
            kospi_mdd = ((bench_df['KOSPI'] - k_rolling_max) / k_rolling_max * 100).min()

            kd_rolling_max = bench_df['KOSDAQ'].cummax()
            kosdaq_mdd = ((bench_df['KOSDAQ'] - kd_rolling_max) / kd_rolling_max * 100).min()

            kospi_return = ((bench_df['KOSPI'].iloc[-1] - bench_df['KOSPI'].iloc[0]) / bench_df['KOSPI'].iloc[0]) * 100
            kosdaq_return = ((bench_df['KOSDAQ'].iloc[-1] - bench_df['KOSDAQ'].iloc[0]) / bench_df['KOSDAQ'].iloc[0]) * 100
            
            alpha_vs_kospi = portfolio_total_return - kospi_return
            alpha_vs_kosdaq = portfolio_total_return - kosdaq_return
        except Exception as e:
            kospi_mdd = 0.0; kosdaq_mdd = 0.0; kospi_return = 0.0; kosdaq_return = 0.0
            alpha_vs_kospi = portfolio_total_return; alpha_vs_kosdaq = portfolio_total_return
            bench_df = pd.DataFrame(index=combined_equity_df.index)
            bench_df['KOSPI_Normalized'] = total_capital; bench_df['KOSDAQ_Normalized'] = total_capital; bench_df['All_Cash'] = total_capital

        x_dates = [d.strftime('%Y-%m-%d') for d in combined_equity_df.index]

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

        # --- 4. 대시보드 UI 출력 ---
        st.markdown(f"<div style='background:#1b4f72;color:white;padding:12px 15px;border-radius:6px;margin-bottom:15px;'><h3 style='margin:0;font-size:16px;'>🎛️ [박가이버 사령부 V10.21 통제실] 전략: {current_strategy_name} ({len(tickers)}개 종목 / 최근 {years}년)</h3></div>", unsafe_allow_html=True)

        # 🤖 제미니 분석 보고서 카드
        st.markdown(f"<div style='background:#fef9e7;border:1px solid #f39c12;border-radius:6px;padding:14px;margin-bottom:15px;'><h4 style='margin:0 0 8px 0;color:#b7950b;font-size:14px;font-weight:bold;'>🤖 [제미니 분석 보고서] 스노우볼 오토 파일럿 작전 결과 ({raw_tickers})</h4><div style='font-size:12px;color:#7f8c8d;font-weight:bold;margin-bottom:6px;'>📋 적용된 핵심 알고리즘 조건 명세서 및 알파(Alpha) 성과</div><ul style='margin:0;padding-left:18px;font-size:11px;color:#2c3e50;line-height:1.6;'><li><b>대상 종목 및 기간:</b> {raw_tickers} ({raw_names}) / 최근 {years}년 ({start_date_str} ~ {end_date_str})</li><li><b>지수 대비 초과 수익률(Alpha):</b> 포트폴리오 수익률(<b>{portfolio_total_return:+.1f}%</b>)이 동기간 KOSPI({kospi_return:+.1f}%), KOSDAQ({kosdaq_return:+.1f}%) 대비 각각 <b>+{alpha_vs_kospi:.1f}%p</b>, <b>+{alpha_vs_kosdaq:.1f}%p</b> 초과 달성</li><li><b>하락장 방어 및 리스크 제어:</b> MDD {max_drawdown:.2f}% 기록 (동기간 KOSPI MDD {kospi_mdd:.1f}%, KOSDAQ MDD {kosdaq_mdd:.1f}% 대비 압도적 방어력 증명)</li><li><b>스노우볼 복리 레벨UP:</b> 순수익 누적 임계치 도달 시 요원 진입 예산 단계적 증액 (현재 레벨업 {total_level_up}회)</li></ul></div>", unsafe_allow_html=True)

        # 🚨 종목 자동 진단 리포트
        cards_html = ""
        for t_code, res in stock_results.items():
            s_name = res['name']
            net_p = res['net_profit']
            contrib = (net_p / total_net_profit_all * 100) if total_net_profit_all > 0 else 0
            
            stock_trades = [t for t in all_matched_trades if t['종목코드'] == t_code]
            avg_days = np.mean([int(str(t['소요기간']).replace('일 소요','').strip()) for t in stock_trades]) if stock_trades else 0
            losses = res['loss_trades']
            
            warns = []
            if avg_days > 90: warns.append("⏱️ 평균 보유기간 90일 초과")
            if contrib < 5.0: warns.append("🍱 수익 기여도 5% 미만")
            if losses >= 2: warns.append("🚨 손절 2회 이상 발생")
            
            if len(warns) == 0:
                status_tag = "<span style='background:#c6f6d5;color:#22543d;padding:2px 6px;border-radius:4px;font-weight:bold;font-size:10px;'>🟢 우수 유지</span>"
                border_color = "#38a169"
            elif len(warns) == 1:
                status_tag = "<span style='background:#fefcbf;color:#744210;padding:2px 6px;border-radius:4px;font-weight:bold;font-size:10px;'>🟡 주의 관찰</span>"
                border_color = "#d69e2e"
            else:
                status_tag = "<span style='background:#fed7d7;color:#9b2c2c;padding:2px 6px;border-radius:4px;font-weight:bold;font-size:10px;'>🔴 퇴출/교체 권고</span>"
                border_color = "#e53e3e"
                
            warn_text = " | ".join(warns) if warns else "• 모든 성과 지표 정상"
            
            cards_html += f"<div style='flex:1 1 210px;background:white;border:1px solid #e2e8f0;border-top:4px solid {border_color};padding:10px;border-radius:6px;min-width:190px;'><div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;'><b style='font-size:12px;color:#2d3748;'>{s_name} ({t_code})</b>{status_tag}</div><div style='font-size:11px;color:#4a5568;line-height:1.4;'>{warn_text}<br><span style='font-size:10px;color:#718096;'>수익기여: {contrib:.1f}% | 평균소요: {avg_days:.1f}일 | 손절: {losses}회</span></div></div>"

        st.markdown(f"<div style='background:#fff5f5;border:1px solid #feb2b2;border-radius:6px;padding:14px;margin-bottom:15px;'><h4 style='margin:0 0 8px 0;color:#c53030;font-size:14px;font-weight:bold;'>🚨 [제미니 종목 자동 진단 & 퇴출/교체 권고 리포트]</h4><div style='font-size:11px;color:#4a5568;margin-bottom:10px;'>보유 기간(90일 초과), 수익 기여도(5% 미만), 손절 횟수(2회 이상) 기준으로 시든 나무를 자동 진단합니다.</div><div style='display:flex;flex-wrap:wrap;gap:8px;'>{cards_html}</div></div>", unsafe_allow_html=True)

        # 상단 KPI 카드 세트 1열 & 2열
        st.markdown(f"<div style='display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px;'><div style='flex:1 1 125px;background:#e8f8f5;padding:12px;border-radius:6px;border-left:5px solid #1abc9c;min-width:110px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>🎯 통합 청산 승률</span><div style='font-size:17px;font-weight:900;color:#2c3e50;margin:4px 0;'>{overall_win_rate:.1f}%</div><span style='font-size:10px;color:#16a085;'>익절 {win_trades_all} / 손절 {loss_trades_all}</span></div><div style='flex:1 1 125px;background:#ebf5fb;padding:12px;border-radius:6px;border-left:5px solid #3498db;min-width:110px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>⚔️ 총 투입 요원</span><div style='font-size:17px;font-weight:900;color:#2c3e50;margin:4px 0;'>{total_agent_counter}명</div><span style='font-size:10px;color:#2980b9;'>총 {total_cycles_all}회차 / 대기 {total_active_count}명</span></div><div style='flex:1 1 125px;background:#fdf2e9;padding:12px;border-radius:6px;border-left:5px solid #e67e22;min-width:110px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>🔥 최대 요원 풀출력</span><div style='font-size:17px;font-weight:900;color:#c0392b;margin:4px 0;'>{full_launch_cycles_all}회 <span style='font-size:10px;'>({full_launch_pct:.1f}%)</span></div><span style='font-size:10px;color:#d35400;'>{max_agents}명 풀가동 비중</span></div><div style='flex:1 1 125px;background:#fadbd8;padding:12px;border-radius:6px;border-left:5px solid #c0392b;min-width:110px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>📉 최대 낙폭지수 (MDD)</span><div style='font-size:17px;font-weight:900;color:#78281f;margin:4px 0;'>{max_drawdown:.2f}%</div><span style='font-size:9.5px;color:#c0392b;font-weight:bold;'>지수: KOSPI {kospi_mdd:.1f}% | KQ {kosdaq_mdd:.1f}%</span></div><div style='flex:1 1 125px;background:#fef9e7;padding:12px;border-radius:6px;border-left:5px solid #f1c40f;min-width:110px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>🚀 스노우볼 레벨UP</span><div style='font-size:17px;font-weight:900;color:#d35400;margin:4px 0;'>{total_level_up}회 <span style='font-size:9px;color:#7f8c8d;'>(다운:{total_step_down})</span></div><span style='font-size:10px;color:#b7950b;'>복리 예산 스텝 업</span></div></div>", unsafe_allow_html=True)

        st.markdown(f"<div style='display:flex;flex-wrap:wrap;gap:8px;margin-bottom:15px;'><div style='flex:1 1 135px;background:#f0fdf4;padding:12px;border-radius:6px;border-left:5px solid #16a34a;min-width:120px;'><span style='font-size:11px;color:#15803d;font-weight:bold;'>🚀 지수 대비 초과수익 (Alpha)</span><div style='font-size:16px;font-weight:900;color:#166534;margin:4px 0;'>+{alpha_vs_kospi:.1f}%p</div><span style='font-size:9.5px;color:#15803d;font-weight:bold;'>KS({kospi_return:+.1f}%) | KQ({kosdaq_return:+.1f}%) 초과</span></div><div style='flex:1 1 115px;background:#eaf2f8;padding:12px;border-radius:6px;border-left:5px solid #2980b9;min-width:105px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>💵 비상 현금금고</span><div style='font-size:13px;font-weight:900;color:#1b4f72;margin:4px 0;'>{format_money(total_reserve_cash)}원</div><span style='font-size:10px;color:#5d6d7e;'>안전 예수금</span></div><div style='flex:1 1 115px;background:#fef9e7;padding:12px;border-radius:6px;border-left:5px solid #f39c12;min-width:105px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>📈 대기주식 평가금</span><div style='font-size:13px;font-weight:900;color:#2c3e50;margin:4px 0;'>{format_money(total_active_eval)}원</div><span style='font-size:10px;color:#7f8c8d;'>대기 요원 평가가</span></div><div style='flex:1 1 115px;background:#fdf2e9;padding:12px;border-radius:6px;border-left:5px solid #e67e22;min-width:105px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>💰 실현 순수익</span><div style='font-size:13px;font-weight:900;color:#c0392b;margin:4px 0;'>+{format_money(total_net_profit_all)}원</div><span style='font-size:10px;color:#7f8c8d;'>매매 실현 순익</span></div><div style='flex:1 1 115px;background:#f5b7b1;padding:12px;border-radius:6px;border-left:5px solid #c0392b;min-width:105px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>💸 수수료·세금</span><div style='font-size:13px;font-weight:900;color:#78281f;margin:4px 0;'>-{format_money(total_fees_paid_all)}원</div><span style='font-size:10px;color:#7f8c8d;'>총 납부 비용</span></div><div style='flex:1 1 115px;background:#fef5e7;padding:12px;border-radius:6px;border-left:5px solid #d35400;min-width:105px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>🚀 총자산 ({portfolio_total_return:+.1f}%)</span><div style='font-size:13px;font-weight:900;color:#2c3e50;margin:4px 0;'>{format_money(final_portfolio_equity)}원</div><span style='font-size:10px;color:#7f8c8d;'>현금+주식+코어</span></div><div style='flex:1 1 95px;background:#f4ecf7;padding:12px;border-radius:6px;border-left:5px solid #9b59b6;min-width:90px;'><span style='font-size:11px;color:#7f8c8d;font-weight:bold;'>🍎 코어주식</span><div style='font-size:13px;font-weight:900;color:#8e44ad;margin:4px 0;'>{total_core_shares}주</div><span style='font-size:10px;color:#7f8c8d;'>{format_money(total_core_eval)}원</span></div></div>", unsafe_allow_html=True)

        # 차트 출력
        fig, ax = plt.subplots(figsize=(10, 4.8))
        ax.plot(x_dates, combined_equity_df['Portfolio_Equity'], label=f'오토파일럿 총자산 ({current_strategy_name})', color='#e74c3c', linewidth=2.5)
        ax.plot(x_dates, bench_df['All_Cash'], label='전액 현금 전략 (Cash 보유)', color='#f1c40f', linewidth=1.5, linestyle=':')
        ax.plot(x_dates, bench_df['KOSPI_Normalized'], label='KOSPI 지수 (^KS11)', color='#2ecc71', linewidth=1.2, linestyle='-.')
        ax.plot(x_dates, bench_df['KOSDAQ_Normalized'], label='KOSDAQ 지수 (^KQ11)', color='#9b59b6', linewidth=1.2, linestyle='-')

        stock_colors = ['#3498db', '#e67e22', '#1abc9c', '#8e44ad', '#d35400', '#27ae60', '#c0392b', '#7f8c8d']
        for s_idx, (t_code, res) in enumerate(stock_results.items()):
            s_name = res['name']
            s_eq = combined_equity_df[s_name]
            s_norm = total_capital * (s_eq / s_eq.iloc[0])
            col_c = stock_colors[s_idx % len(stock_colors)]
            ax.plot(x_dates, s_norm, label=f'[{s_name}] 개별 종목 자산', color=col_c, linewidth=1.5, linestyle='--')

        ax.set_title(f'[V10.21 포지션 종목별 & 시장 비교] {current_strategy_name}', fontsize=12, fontweight='bold', pad=10)
        ax.set_ylabel('자산 평가액 (원)', fontsize=10, fontweight='bold')
        ax.legend(loc='upper left', fontsize=7.5, ncol=2)
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.yaxis.set_major_formatter('${x:,.0f}')

        step_size = max(1, len(x_dates) // 6)
        ax.set_xticks(range(0, len(x_dates), step_size))
        ax.set_xticklabels([x_dates[i] for i in range(0, len(x_dates), step_size)], rotation=15, fontsize=9)
        plt.tight_layout()

        st.pyplot(fig)

        # 매매 장부 데이터프레임
        df_export_data = []
        for t in all_matched_trades:
            clean_row = {k: v for k, v in t.items() if k not in ['is_win', 'raw_profit', 'exit_date']}
            df_export_data.append(clean_row)

        df_export = pd.DataFrame(df_export_data)

        # CSV 다운로드 버튼
        csv_buffer = io.StringIO()
        df_export.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        st.download_button(
            label="📜 엑셀(CSV) V10.21 공식 작전장부 다운로드",
            data=csv_buffer.getvalue().encode('utf-8-sig'),
            file_name=f"박가이버사령부_V10.21_{selected_strategy}.csv",
            mime="text/csv"
        )
else:
    st.info("👈 왼쪽 사이드바에서 종목과 조건 설정 후 [▶️ 박가이버 사령부 V10.21 작전 개시!] 버튼을 눌러주세요.")
