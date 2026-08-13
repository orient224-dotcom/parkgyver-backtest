# @title 🎛️ 박가이버 사령부 V10.30 실행 (좌측 실행 버튼을 누른 후, 코드를 숨기려면 여기를 더블클릭 하세요)
import sys
import subprocess
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'yfinance'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

import yfinance as yf
import pandas as pd
import numpy as np
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
import datetime
from dateutil.relativedelta import relativedelta
import base64
import matplotlib.pyplot as plt
import io
import os
import matplotlib.font_manager as fm
from matplotlib.ticker import StrMethodFormatter

# --- 🛠️ 맷플롯립 한글 폰트 세팅 ---
subprocess.run(['apt-get', '-qq', 'install', 'fonts-nanum'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
font_path = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
if os.path.exists(font_path):
    fm.fontManager.addfont(font_path)
    plt.rcParams['font.family'] = 'NanumGothic'
plt.rcParams['axes.unicode_minus'] = False

# --- 💡 소스코드 숨기기 UI 버튼 ---
display(HTML("""
<script>
function toggle_code() {
    var elements = document.querySelectorAll('.input_area, .code_cell .input, .jp-InputArea');
    var btn = document.getElementById("code_toggle_btn");
    var is_hidden = btn.value.includes("보기");
    
    for(var i=0; i<elements.length; i++) { 
        elements[i].style.display = is_hidden ? 'block' : 'none'; 
    }
    btn.value = is_hidden ? "👀 소스코드 숨기기" : "👀 소스코드 보기";
}
</script>
<div style="text-align:right; margin-bottom: 8px;">
    <input type="button" id="code_toggle_btn" value="👀 소스코드 숨기기" onclick="toggle_code()" style="padding: 6px 12px; font-weight: bold; border-radius: 4px; background-color: #2c3e50; color: white; border: none; cursor: pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
</div>
"""))

# --- 통제실 디자인 ---
display(HTML("""
<div style='background-color:#1b4f72; padding:16px; border-radius:10px; max-width:100%; color:white; box-shadow:0 4px 6px rgba(0,0,0,0.1); box-sizing:border-box;'>
    <h2 style='font-weight:900; text-align:center; font-size:18px; margin:0 0 5px 0;'>🎛️ 박가이버 사령부 V10.30 (은퇴 과수원 에디션)</h2>
    <p style='text-align:center; font-size:12px; margin:0; color:#a9cce3;'>하이브리드 예비비 구원/방어 체계 | 1/2군 승강제 도입 | 체류기간 색상 경보 | 통합 차트</p>
</div>
"""))

# --- 입력창 위젯 ---
tickers_1_input = widgets.Text(value='019210.KQ, 005930.KS, 080220.KQ, 089030.KQ, 319660.KQ, 034020.KS, 074600.KQ', description='🎯 1군 코드:', layout=widgets.Layout(width='100%'))
names_1_input = widgets.Text(value='와이지원, 삼성전자, 제주반도체, 테크윙, 피에스케이, 두산인프라코어, 원익QNC', description='📛 1군 이름:', layout=widgets.Layout(width='100%'))

tickers_2_input = widgets.Text(value='005850.KS, 161890.KS, 193250.KS, 188370.KQ, 214150.KQ', description='🏆 2군 후보:', layout=widgets.Layout(width='100%'))
names_2_input = widgets.Text(value='에스엘, 한국콜마, 영원무역, 서진시스템, 클래시스', description='📛 2군 이름:', layout=widgets.Layout(width='100%'))

strategy_select = widgets.Dropdown(
    options=[('🌳 3단 밸런스 과수원 전략 (60%재투자/20%현금/20%코어)', '3tier'),
             ('🚀 풀 현금 복리 재투자 전략 (100% 컴파운딩)', 'full_cash'),
             ('⚖️ 균등 배분 고정 전략 (No Reinvest / Buy&Hold 1/N)', 'equal_alloc')],
    value='3tier', description='📊 작전전략:', layout=widgets.Layout(width='100%')
)

buy_fee_input = widgets.FloatText(value=0.015, description='📉 매수수수료(%):', layout=widgets.Layout(width='50%'))
sell_tax_input = widgets.FloatText(value=0.20, description='📈 매도세금(%):', layout=widgets.Layout(width='50%'))
fee_box = widgets.HBox([buy_fee_input, sell_tax_input])

capital_input = widgets.BoundedIntText(value=16000000, min=1000000, max=1000000000, step=1000000, description='💰 총 씨드(원):', layout=widgets.Layout(width='100%'))
capital_label = widgets.HTML(value="<span style='color:#27ae60; font-weight:bold; font-size:13px;'>➔ 16,000,000 원 (1,600 만원)</span>")
capital_input.observe(lambda change: setattr(capital_label, 'value', f"<span style='color:#27ae60; font-weight:bold; font-size:13px;'>➔ {change['new']:,} 원 ({change['new']//10000:,} 만원)</span>"), names='value')

agents_input = widgets.IntText(value=2, description='⚔️ 종목당요원:', layout=widgets.Layout(width='50%'))
years_input = widgets.IntText(value=3, description='🗓️ 조회기간:', layout=widgets.Layout(width='50%'))
setting_box = widgets.HBox([agents_input, years_input])

run_btn = widgets.Button(description='▶️ 박가이버 사령부 V10.30 작전 및 1/2군 평가 개시!', button_style='danger', layout=widgets.Layout(width='100%', height='45px', margin='10px 0 0 0'))
out = widgets.Output()

def format_money(num):
    return f"{int(round(num)):,}"

def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=130)
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return img_str

def run_simulation(tickers, names, total_capital, max_agents, years, buy_fee_rate, sell_tax_rate, selected_strategy):
    capital_per_stock = total_capital / len(tickers)
    end_date = datetime.datetime.today()
    start_date = end_date - relativedelta(years=years + 1)

    all_matched_trades = []
    stock_results = {}
    combined_equity_df = pd.DataFrame()
    all_active_positions = []
    
    total_cycles_all = 0
    full_launch_cycles_all = 0
    agent_perf_dist = {i: {'wins': 0, 'losses': 0} for i in range(1, max_agents + 2)} # +1 for rescue agent
    total_agent_counter = 0
    stock_total_fees_all = 0.0

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
        level_up_count = 0
        step_progress = 0.0
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

            total_inv = sum(p['shares'] * p['entry_price'] for p in positions) if positions else 0
            total_ev = sum(p['shares'] * close for p in positions) if positions else 0
            comb_ret = (total_ev - total_inv) / total_inv if total_inv > 0 else 0

            has_winner = any(((close - pos['entry_price']) / pos['entry_price']) * 100 >= pos['target_ret'] for pos in positions)
            is_rescue_deployed = any(p['name'] == '🚑 구원투수' for p in positions)
            
            # --- V10.30 하이브리드 청산/구원 로직 ---
            is_stop_loss = is_rescue_deployed and comb_ret <= -0.10
            
            if has_winner or is_stop_loss:
                total_cycles += 1
                total_cycles_all += 1
                batch_size = len([p for p in positions if p['name'] != '🚑 구원투수'])
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
                    stock_total_fees_all += trade_fee_total

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
                    
                    actual_win = profit_krw >= 0
                    if actual_win: win_trades += 1
                    else: loss_trades += 1
                    
                    agent_type = batch_size if pos['name'] != '🚑 구원투수' else max_agents + 1
                    if agent_type in agent_perf_dist:
                        if actual_win: agent_perf_dist[agent_type]['wins'] += 1
                        else: agent_perf_dist[agent_type]['losses'] += 1

                    duration_days = (date - pos['entry_dt']).days if 'entry_dt' in pos else 0
                    exit_reason = "🎯 동반 익절(+)" if has_winner else "🚨 통합 손절(-10%)"

                    current_batch_trades.append({
                        '요원': pos['name'], '작전구역': s_name, '종목코드': ticker,
                        '출격일': pos['entry_date'], '진입단가': pos['entry_price'],
                        '복귀일': date_str, '청산단가': close, '진입금액': buy_amount_net, '매도금액': sell_amount_net,
                        '총수수료·세금': trade_fee_total, '등락폭': close - pos['entry_price'], '소요기간': duration_days,
                        '순수익률': ret, '정산내역': profit_krw, '구분': exit_reason, 'is_win': actual_win, 'exit_date': date
                    })

                event_effect_str = ""
                if selected_strategy != 'equal_alloc':
                    step_progress += batch_reinvest_profit
                    threshold = current_capital * 0.10
                    if step_progress >= threshold:
                        level_up_count += 1; current_capital += threshold; step_progress = 0.0
                        event_effect_str = f"🚀 [레벨업 UP! Lv.{level_up_count}]"

                for t in current_batch_trades:
                    t['스노우볼 레벨'] = f"Lv.{max(1, level_up_count + 1)}" + (f" <br><span style='color:#c0392b; font-size:9px;'>{event_effect_str}</span>" if event_effect_str else "")

                matched_trades.extend(current_batch_trades)
                positions = []

            # 🚑 구원투수 투입 로직 (-15% 하락 시 2배수 예비비 투입)
            elif not is_rescue_deployed and len(positions) == max_agents and comb_ret <= -0.15:
                agent_budget = int((s_capital // max_agents) * (current_capital / s_capital if selected_strategy != 'equal_alloc' else 1.0))
                rescue_budget = agent_budget * 2 # 2배수 물타기
                shares = max(int(rescue_budget // close), 1)
                positions.append({
                    'name': '🚑 구원투수', 'entry_price': close, 'entry_date': date_str, 'entry_dt': date,
                    'shares': shares, 'target_ret': target_ret
                })

            # 일반 요원 투입 로직 (-5% 하락 시)
            elif daily_return <= -5.0 and len(positions) < max_agents and not is_rescue_deployed:
                agent_counter += 1
                total_agent_counter += 1
                agent_budget = int((s_capital // max_agents) * (current_capital / s_capital if selected_strategy != 'equal_alloc' else 1.0))
                shares = max(int(agent_budget // close), 1)
                positions.append({
                    'name': f"{agent_counter}호 요원", 'entry_price': close, 'entry_date': date_str, 'entry_dt': date,
                    'shares': shares, 'target_ret': target_ret
                })

            active_eval = sum(p['shares'] * close for p in positions)
            core_eval = core_shares * close
            realized_pnl = sum([t['정산내역'] for t in matched_trades])
            stock_equity = s_capital + realized_pnl + reserve_cash + core_eval + active_eval - (sum(p['shares']*p['entry_price'] for p in positions))
            daily_log.append({'Date': date, 'Stock_Equity': stock_equity})

        for p in positions:
            cur_eval_p = p['shares'] * float(df['Close'].iloc[-1])
            pnl_p = cur_eval_p - (p['shares'] * p['entry_price'])
            pnl_pct = (pnl_p / (p['shares'] * p['entry_price'])) * 100
            holding_days = (end_date - p['entry_dt']).days 
            all_active_positions.append({
                '작전구역': s_name, '요원명': p['name'], '파견일': p['entry_date'], '체류일수': holding_days, 
                '진입단가': p['entry_price'], '수량': p['shares'], '평가금액': cur_eval_p, '평가손익': pnl_p, '평가손익률': pnl_pct, 'is_plus': pnl_p >= 0
            })

        if daily_log:
            df_stock_eq = pd.DataFrame(daily_log).set_index('Date')
            combined_equity_df[s_name] = df_stock_eq['Stock_Equity']

        stock_results[ticker] = {
            'name': s_name, 'total_trades': total_trades, 'win_trades': win_trades, 'loss_trades': loss_trades,
            'win_rate': (win_trades / total_trades * 100) if total_trades > 0 else 0,
            'net_profit': sum([t['정산내역'] for t in matched_trades]),
            'reserve_cash': reserve_cash, 'core_shares': core_shares,
            'core_eval': core_shares * float(df['Close'].iloc[-1]) if not df.empty else 0,
            'active_eval': sum(p['shares'] * float(df['Close'].iloc[-1]) for p in positions),
            'active_count': len(positions),
            'final_equity': combined_equity_df[s_name].iloc[-1] if not combined_equity_df.empty else s_capital,
            'matched_trades': matched_trades
        }
        all_matched_trades.extend(matched_trades)

    if not combined_equity_df.empty:
        combined_equity_df = combined_equity_df.ffill().bfill().dropna()
        combined_equity_df['Portfolio_Equity'] = combined_equity_df.sum(axis=1)

    return stock_results, combined_equity_df, all_matched_trades, all_active_positions, total_agent_counter, total_cycles_all, full_launch_cycles_all, agent_perf_dist, stock_total_fees_all

def run_v10_30_dashboard(b):
    with out:
        clear_output()
        t1_raw = tickers_1_input.value.strip()
        n1_raw = names_1_input.value.strip()
        t2_raw = tickers_2_input.value.strip()
        n2_raw = names_2_input.value.strip()
        
        tickers_1 = [t.strip().upper() for t in t1_raw.split(',') if t.strip()]
        names_1 = [n.strip() for n in n1_raw.split(',') if n.strip()]
        tickers_2 = [t.strip().upper() for t in t2_raw.split(',') if t.strip()]
        names_2 = [n.strip() for n in n2_raw.split(',') if n.strip()]

        while len(names_1) < len(tickers_1): names_1.append(tickers_1[len(names_1)])
        while len(names_2) < len(tickers_2): names_2.append(tickers_2[len(names_2)])

        if not tickers_1:
            print("❌ 1군 종목 코드를 올바르게 입력해 주세요.")
            return

        total_capital = capital_input.value
        max_agents = agents_input.value
        years = years_input.value
        buy_fee = buy_fee_input.value / 100.0
        sell_tax = sell_tax_input.value / 100.0
        strat = strategy_select.value

        print(f"📡 [V10.30 통제실] 1군({len(tickers_1)}개) 및 2군({len(tickers_2)}개) 백그라운드 연산을 시작합니다...\n")

        try:
            # Run 1군
            res_1, eq_df_1, trades_1, active_1, agents_1, cycles_1, full_1, dist_1, fees_1 = run_simulation(
                tickers_1, names_1, total_capital, max_agents, years, buy_fee, sell_tax, strat)
            
            # Run 2군
            res_2, eq_df_2, trades_2, active_2, agents_2, cycles_2, full_2, dist_2, fees_2 = run_simulation(
                tickers_2, names_2, total_capital, max_agents, years, buy_fee, sell_tax, strat)

            if eq_df_1.empty:
                print("❌ 1군 유효한 종목 데이터가 없습니다.")
                return

            # --- KOSPI / KOSDAQ 벤치마크 ---
            end_date = datetime.datetime.today()
            start_date = end_date - relativedelta(years=years + 1)
            kospi_df = yf.download('^KS11', start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False, auto_adjust=False)
            kosdaq_df = yf.download('^KQ11', start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False, auto_adjust=False)
            
            bench_df = pd.DataFrame(index=eq_df_1.index)
            k_close = kospi_df[('Close', '^KS11')] if isinstance(kospi_df.columns, pd.MultiIndex) else kospi_df['Close']
            kd_close = kosdaq_df[('Close', '^KQ11')] if isinstance(kosdaq_df.columns, pd.MultiIndex) else kosdaq_df['Close']
            bench_df['KOSPI'] = k_close.reindex(bench_df.index, method='ffill')
            bench_df['KOSDAQ'] = kd_close.reindex(bench_df.index, method='ffill')
            bench_df['KOSPI_Norm'] = total_capital * (bench_df['KOSPI'] / bench_df['KOSPI'].iloc[0])
            bench_df['KOSDAQ_Norm'] = total_capital * (bench_df['KOSDAQ'] / bench_df['KOSDAQ'].iloc[0])
            bench_df['All_Cash'] = total_capital

            portfolio_eq = eq_df_1['Portfolio_Equity']
            max_drawdown = ((portfolio_eq - portfolio_eq.cummax()) / portfolio_eq.cummax() * 100).min()
            portfolio_total_return = (portfolio_eq.iloc[-1] - total_capital) / total_capital * 100
            
            k_mdd = ((bench_df['KOSPI'] - bench_df['KOSPI'].cummax()) / bench_df['KOSPI'].cummax() * 100).min()
            kd_mdd = ((bench_df['KOSDAQ'] - bench_df['KOSDAQ'].cummax()) / bench_df['KOSDAQ'].cummax() * 100).min()
            k_ret = ((bench_df['KOSPI'].iloc[-1] - bench_df['KOSPI'].iloc[0]) / bench_df['KOSPI'].iloc[0]) * 100
            kd_ret = ((bench_df['KOSDAQ'].iloc[-1] - bench_df['KOSDAQ'].iloc[0]) / bench_df['KOSDAQ'].iloc[0]) * 100

            # --- 통합 차트 생성 ---
            x_dates = [d.strftime('%Y-%m-%d') for d in eq_df_1.index]
            fig, ax = plt.subplots(figsize=(10, 5.2))
            ax.plot(x_dates, eq_df_1['Portfolio_Equity'], label='1군 오토파일럿 총자산', color='#e74c3c', linewidth=2.5)
            ax.plot(x_dates, bench_df['All_Cash'], label='전액 현금 전략', color='#f1c40f', linewidth=1.5, linestyle=':')
            ax.plot(x_dates, bench_df['KOSPI_Norm'], label='KOSPI 지수', color='#2ecc71', linewidth=1.2, linestyle='-.')
            ax.plot(x_dates, bench_df['KOSDAQ_Norm'], label='KOSDAQ 지수', color='#9b59b6', linewidth=1.2, linestyle='-')
            ax.set_title('[V10.30 전략 및 시장 비교]', fontsize=12, fontweight='bold', pad=10)
            ax.set_ylabel('총 자산 평가액 (원)', fontsize=10, fontweight='bold')
            ax.legend(loc='upper left', fontsize=8, ncol=2)
            ax.grid(True, linestyle=':', alpha=0.6)
            ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
            step_size = max(1, len(x_dates) // 6)
            ax.set_xticks(range(0, len(x_dates), step_size))
            ax.set_xticklabels([x_dates[i] for i in range(0, len(x_dates), step_size)], rotation=15, fontsize=9)
            plt.tight_layout()
            chart_base64 = fig_to_base64(fig)

            # --- 1/2군 고과 평가 리포트 생성 ---
            def get_stats_html(res_dict, trades, is_main=True):
                html = "<div style='display: flex; flex-wrap: wrap; gap: 8px;'>"
                total_net = sum([r['net_profit'] for r in res_dict.values()])
                for t_code, r in res_dict.items():
                    contrib = (r['net_profit'] / total_net * 100) if total_net > 0 else 0
                    s_trades = [t for t in trades if t['종목코드'] == t_code]
                    avg_days = np.mean([t['소요기간'] for t in s_trades]) if s_trades else 0
                    
                    if is_main:
                        warns = []
                        if avg_days > 45: warns.append("⏱️ 회전율 저조(45일 초과)")
                        if contrib < 5.0: warns.append("🍱 기여도 미달(5% 미만)")
                        if r['loss_trades'] >= 2: warns.append("🚨 치명적 실수(통합 손절 2회)")
                        
                        border_color = "#e53e3e" if len(warns) >= 2 else ("#d69e2e" if len(warns) == 1 else "#38a169")
                        tag = "<span style='background:#fed7d7; color:#9b2c2c; padding:2px 6px; border-radius:4px; font-size:10px;'>🔴 강등 주의</span>" if len(warns) >= 2 else ""
                        warn_text = "<br>".join([f"• {w}" for w in warns]) if warns else "• KPI 올패스 (1군 핵심 인재)"
                    else:
                        border_color = "#3498db"
                        tag = "<span style='background:#ebf5fb; color:#2980b9; padding:2px 6px; border-radius:4px; font-size:10px;'>🏆 스카우트 1순위</span>" if contrib > 15.0 and avg_days < 30 else ""
                        warn_text = f"• 가상 수익 기여도: {contrib:.1f}%<br>• 가상 평균 탈출: {avg_days:.1f}일"

                    html += f"""
                    <div style='flex: 1 1 200px; background: white; border: 1px solid #e2e8f0; border-top: 4px solid {border_color}; padding: 10px; border-radius: 6px; min-width: 190px;'>
                        <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;'>
                            <b style='font-size:12px; color:#2d3748;'>{r['name']} ({t_code})</b> {tag}
                        </div>
                        <div style='font-size:11px; color:#4a5568; line-height:1.4;'>
                            {warn_text}<br>
                            <span style='font-size:10px; color:#718096;'>승률: {r['win_rate']:.1f}% | 순수익: {format_money(r['net_profit'])}원</span>
                        </div>
                    </div>
                    """
                return html + "</div>"

            # --- 대기 요원 3단계 색상 경보 ---
            active_html = ""
            for ap in all_active_1:
                days = ap.get('체류일수', 0)
                if days >= 90: row_bg, warn_icon, d_col = "#ffebee", "🚨 ", "#c0392b"
                elif days >= 60: row_bg, warn_icon, d_col = "#fce4ec", "⚠️ ", "#c2185b"
                elif days >= 30: row_bg, warn_icon, d_col = "#fff9c4", "⏳ ", "#d35400"
                else: row_bg, warn_icon, d_col = "#ffffff", "", "#7f8c8d"
                
                pnl_color = "#c0392b" if ap['is_plus'] else "#2980b9"
                active_html += f"<tr style='background-color: {row_bg};'><td style='padding: 5px; border: 1px solid #eaeded; font-weight: bold;'>{ap['작전구역']}</td><td style='padding: 5px; border: 1px solid #eaeded; font-weight: bold;'>{ap['요원명']}</td><td style='padding: 5px; border: 1px solid #eaeded; font-weight: bold; color: {d_col};'>{warn_icon}{days}일</td><td style='padding: 5px; border: 1px solid #eaeded;'>{format_money(ap['진입단가'])}원</td><td style='padding: 5px; border: 1px solid #eaeded;'>{ap['수량']}주</td><td style='padding: 5px; border: 1px solid #eaeded; color: {pnl_color}; font-weight: bold;'>{'+' if ap['is_plus'] else ''}{format_money(ap['평가손익'])}원</td></tr>"

            # --- 전체 대시보드 조립 ---
            html_content = f"""
            <div style='font-family: sans-serif; width: 100%; box-sizing: border-box;'>
                <div style='background: #1b4f72; color: white; padding: 12px 15px; border-radius: 6px; margin-bottom: 15px;'>
                    <h3 style='margin: 0; font-size: 15px;'>🎛️ [박가이버 사령부 V10.30] 하이브리드 통제실 가동</h3>
                </div>

                <!-- 📊 상단 KPI 카드 -->
                <div style='display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 15px;'>
                    <div style='flex: 1 1 135px; background: #f0fdf4; padding: 12px; border-radius: 6px; border-left: 5px solid #16a34a;'><span style='font-size: 11px; color: #15803d; font-weight: bold;'>🚀 1군 초과수익 (Alpha)</span><div style='font-size: 16px; font-weight: 900; color: #166534; margin: 4px 0;'>+{portfolio_total_return - k_ret:.1f}%p</div><span style='font-size: 9.5px; color: #15803d; font-weight: bold;'>KS 대비 알파 창출</span></div>
                    <div style='flex: 1 1 125px; background: #fadbd8; padding: 12px; border-radius: 6px; border-left: 5px solid #c0392b;'><span style='font-size: 11px; color: #7f8c8d; font-weight: bold;'>📉 최대 낙폭지수 (MDD)</span><div style='font-size: 16px; font-weight: 900; color: #78281f; margin: 4px 0;'>{max_drawdown:.2f}%</div><span style='font-size: 9.5px; color: #c0392b; font-weight: bold;'>KOSPI: {k_mdd:.1f}%</span></div>
                    <div style='flex: 1 1 115px; background: #fef5e7; padding: 12px; border-radius: 6px; border-left: 5px solid #d35400;'><span style='font-size: 11px; color: #7f8c8d; font-weight: bold;'>🚀 1군 총자산 ({portfolio_total_return:+.1f}%)</span><div style='font-size: 15px; font-weight: 900; color: #2c3e50; margin: 4px 0;'>{format_money(portfolio_eq.iloc[-1])}원</div><span style='font-size: 10px; color: #7f8c8d;'>현금+주식+코어</span></div>
                </div>

                <!-- 📈 통합 차트 -->
                <div style='text-align: center; background: white; padding: 10px; border-radius: 6px; border: 1px solid #d6dbdf; margin-bottom: 15px;'>
                    <img src="data:image/png;base64,{chart_base64}" style="max-width: 100%; height: auto; border-radius: 4px;">
                </div>

                <!-- 🚨 1군 정기 인사 발령 (KPI 평가) -->
                <div style='background: #fff5f5; border: 1px solid #feb2b2; border-radius: 6px; padding: 14px; margin-bottom: 15px;'>
                    <h4 style='margin: 0 0 8px 0; color: #c53030; font-size: 14px; font-weight: bold;'>🚨 [1군 정기 인사고과 평가] 실전 포트폴리오 생존 진단</h4>
                    <div style='font-size: 11px; color: #4a5568; margin-bottom: 10px;'>객관적인 성과 지표(회전율, 기여도, 손절 이력)를 바탕으로 조직의 신진대사를 관리합니다.</div>
                    {get_stats_html(res_1, trades_1, True)}
                </div>

                <!-- 🏆 2군 스카우팅 리포트 -->
                <div style='background: #f4f6f7; border: 1px solid #d5dbdf; border-radius: 6px; padding: 14px; margin-bottom: 15px;'>
                    <h4 style='margin: 0 0 8px 0; color: #2c3e50; font-size: 14px; font-weight: bold;'>🏆 [2군 스카우팅 리포트] 예비 후보군 가상 훈련 성적표</h4>
                    <div style='font-size: 11px; color: #4a5568; margin-bottom: 10px;'>관심 중형주들이 사령부 로직으로 뛰었을 때의 백그라운드 가상 평가 결과입니다. 1군 강등 요원 발생 시 스왑(Swap) 1순위를 선발합니다.</div>
                    {get_stats_html(res_2, trades_2, False)}
                </div>

                <!-- 🕵️ 대기요원 3단계 색상 경보 -->
                <div style='background: #fdfefe; border: 1px solid #3498db; border-radius: 6px; padding: 12px; margin-bottom: 15px;'>
                    <h4 style='margin: 0 0 10px 0; color: #2980b9; font-size: 13px;'>🕵️ [1군 파견 대기 요원 실시간 현황판] (30일/60일/90일 색상 경고)</h4>
                    <div style='overflow-x: auto;'><table style='width: 100%; border-collapse: collapse; text-align: center; font-size: 11px;'>
                        <thead style='background-color: #ebf5fb; color: #2980b9;'><tr><th style='padding: 6px; border: 1px solid #d5dbdf;'>작전구역</th><th style='padding: 6px; border: 1px solid #d5dbdf;'>요원명</th><th style='padding: 6px; border: 1px solid #d5dbdf;'>체류일수</th><th style='padding: 6px; border: 1px solid #d5dbdf;'>진입단가</th><th style='padding: 6px; border: 1px solid #d5dbdf;'>수량</th><th style='padding: 6px; border: 1px solid #d5dbdf;'>평가손익</th></tr></thead>
                        <tbody>{active_html if active_html else "<tr><td colspan='6' style='padding:10px; color:#7f8c8d;'>대기 중인 요원이 없습니다.</td></tr>"}</tbody>
                    </table></div>
                </div>
            </div>
            """
            display(HTML(html_content))

        except Exception as e:
            print(f"❌ 에러 발생: {e}")

# 변수 연결용 alias
all_active_1 = [] 

def run_wrapper(b):
    global all_active_1
    run_v10_30_dashboard(b)

run_btn.on_click(run_wrapper)

display(widgets.VBox([
    widgets.HBox([tickers_1_input, names_1_input]),
    widgets.HBox([tickers_2_input, names_2_input]),
    strategy_select, fee_box, capital_input, capital_label, setting_box, run_btn
]))
display(out)
