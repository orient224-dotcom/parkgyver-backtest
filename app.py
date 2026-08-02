import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
from dateutil.relativedelta import relativedelta
import io
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 페이지 기본 설정 ---
st.set_page_config(page_title="박가이버 사령부 V10.28 (구글 시트 연동 에디션)", layout="wide", page_icon="🎛️")

def format_money(num):
    try:
        return f"{int(round(float(num))):,}"
    except:
        return str(num)

# --- 2. 구글 시트 연결 함수 ---
@st.cache_resource
def init_gsheet():
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        if "gcp_service_account" in st.secrets:
            creds_info = st.secrets["gcp_service_account"]
            creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
            client = gspread.authorize(creds)
            sheet_id = st.secrets["spreadsheet"]["id"]
            sh = client.open_by_key(sheet_id)
            return sh
        else:
            return None
    except Exception as e:
        st.error(f"⚠️ 구글 시트 연동 실패: {e}")
        return None

sh = init_gsheet()

# --- 구글 시트 데이터 로드/저장 헬퍼 ---
def load_sheet_data(worksheet_name, default_df):
    if sh is None:
        return default_df
    try:
        try:
            ws = sh.worksheet(worksheet_name)
        except:
            ws = sh.add_worksheet(title=worksheet_name, rows="100", cols="20")
            ws.update([default_df.columns.values.tolist()] + default_df.values.tolist())
            return default_df
        
        data = ws.get_all_records()
        if not data:
            return default_df
        return pd.DataFrame(data)
    except Exception as e:
        return default_df

def save_sheet_data(worksheet_name, df):
    if sh is None:
        return
    try:
        try:
            ws = sh.worksheet(worksheet_name)
        except:
            ws = sh.add_worksheet(title=worksheet_name, rows="100", cols="20")
        ws.clear()
        ws.update([df.columns.values.tolist()] + df.astype(str).values.tolist())
    except Exception as e:
        st.error(f"⚠️ 시트 저장 중 오류: {e}")

# --- 3. 기본 데이터베이스 초기화 ---
default_acc = pd.DataFrame([{"총씨드머니": 16000000, "예수금": 16000000}])
default_agents = pd.DataFrame(columns=['stock', 'code', 'name', 'entry_date', 'entry_price', 'shares', 'target_ret'])

df_acc = load_sheet_data("계좌현황", default_acc)
df_agents = load_sheet_data("보유요원", default_agents)

if 'real_capital' not in st.session_state:
    st.session_state['real_capital'] = float(df_acc.iloc[0]['총씨드머니']) if not df_acc.empty else 16000000.0
if 'real_cash' not in st.session_state:
    st.session_state['real_cash'] = float(df_acc.iloc[0]['예수금']) if not df_acc.empty else 16000000.0
if 'active_agents' not in st.session_state:
    st.session_state['active_agents'] = df_agents.to_dict('records') if not df_agents.empty else []

# --- 4. 사이드바 조종간 ---
st.sidebar.title("🎛️ 박가이버 사령부 V10.28")
st.sidebar.caption("은퇴 과수원 에디션 - 구글 시트 동기화 통제실")

stock_database = {
    "테크윙 (089030.KQ)": "089030.KQ",
    "피에스케이 (319660.KQ)": "319660.KQ",
    "제주반도체 (080220.KQ)": "080220.KQ",
    "삼성전자 (005930.KS)": "005930.KS",
    "와이지원 (019210.KQ)": "019210.KQ",
    "두산인프라코어/밥캣등 (034020.KS)": "034020.KS",
    "원익QNC (074600.KQ)": "074600.KQ",
    "한미반도체 (042700.KQ)": "042700.KQ",
    "주성엔지니어링 (036930.KQ)": "036930.KQ",
    "SK하이닉스 (000660.KS)": "000660.KS",
    "LG에너지솔루션 (373220.KS)": "373220.KS",
    "셀트리온 (068270.KS)": "068270.KS"
}

st.sidebar.markdown("---")
default_selected = ["와이지원 (019210.KQ)", "삼성전자 (005930.KS)", "제주반도체 (080220.KQ)", "테크윙 (089030.KQ)", "피에스케이 (319660.KQ)", "두산인프라코어/밥캣등 (034020.KS)", "원익QNC (074600.KQ)"]
selected_stocks = st.sidebar.multiselect("관찰/매매 종목 선택:", options=list(stock_database.keys()), default=default_selected)

tickers_list = [stock_database[s] for s in selected_stocks]
names_list = [s.split(" (")[0] for s in selected_stocks]

total_capital = st.sidebar.number_input("💰 실전 총 씨드머니(원):", value=int(st.session_state['real_capital']), step=1000000)
st.session_state['real_capital'] = float(total_capital)
max_agents = st.sidebar.number_input("⚔️ 종목당 최대 요원 수:", value=2, min_value=1, max_value=10)

# --- 📗 구글 시트 실시간 관제 현황판 ---
st.markdown("<div style='background:#1b4f72;color:white;padding:12px;border-radius:6px;margin-bottom:12px;'><h3 style='margin:0;font-size:16px;'>📗 [박가이버 사령부] 구글 시트 연동 계좌 관제탑</h3></div>", unsafe_allow_html=True)

if sh:
    st.success("✅ 구글 스프레드시트가 정상적으로 연결되었습니다. PC/스마트폰 데이터가 실시간 동기화됩니다.")
else:
    st.warning("⚠️ 구글 시트 미연동 상태입니다. (Secrets 설정을 완료하시면 자동 저장됩니다.)")

acc_col1, acc_col2, acc_col3 = st.columns(3)
with acc_col1:
    st.metric("💰 총 설정 씨드머니", f"{format_money(st.session_state['real_capital'])} 원")
with acc_col2:
    st.metric("💵 현재 사용 가능 예수금", f"{format_money(st.session_state['real_cash'])} 원")
with acc_col3:
    st.metric("🕵️ 현장 파견 보유 요원 수", f"{len(st.session_state['active_agents'])} 명")

st.markdown("---")

# --- 🚨 3:20 PM 실전 작전 지시서 ---
st.markdown("<div style='background:#154360;color:white;padding:12px;border-radius:6px;margin-bottom:12px;'><h3 style='margin:0;font-size:16px;'>🚨 [오후 3:20 PM 실전 작전 지시서] 실시간 신호등 관제탑</h3></div>", unsafe_allow_html=True)

scan_col1, scan_col2 = st.columns([1, 3])
with scan_col1:
    scan_live_btn = st.button("📡 [3시 20분] 실시간 시장 스캔 및 수량 계산", type="primary", use_container_width=True)
with scan_col2:
    st.caption("구글 시트 장부에 기록된 예수금 잔액 및 요원 현황을 기반으로 매수/매도 수량을 정밀 산출합니다.")

if scan_live_btn:
    with st.spinner("🔍 실시간 시세 스캔 및 실전 수량 연산 중..."):
        buy_orders, sell_orders = [], []

        for idx, t_code in enumerate(tickers_list):
            s_name = names_list[idx]
            try:
                ticker_obj = yf.Ticker(t_code)
                hist = ticker_obj.history(period="5d")
                
                if len(hist) >= 2:
                    prev_close = float(hist['Close'].iloc[-2])
                    curr_price = float(hist['Close'].iloc[-1])
                    daily_ret = ((curr_price - prev_close) / prev_close) * 100

                    current_stock_agents = [a for a in st.session_state['active_agents'] if a.get('code') == t_code]

                    for ag in current_stock_agents:
                        profit_pct = ((curr_price - float(ag['entry_price'])) / float(ag['entry_price'])) * 100
                        if profit_pct >= float(ag['target_ret']):
                            sell_orders.append({
                                '작전구역': s_name, '요원명': ag['name'], '코드': t_code,
                                '진입단가': ag['entry_price'], '현재가': curr_price,
                                '수량': ag['shares'], '수익률': f"{profit_pct:+.2f}%"
                            })

                    if daily_ret <= -5.0 and len(current_stock_agents) < max_agents:
                        agent_budget = (st.session_state['real_capital'] / len(tickers_list)) / max_agents
                        buyable_shares = max(int(agent_budget // curr_price), 1)
                        total_cost = buyable_shares * curr_price

                        if st.session_state['real_cash'] >= total_cost:
                            next_agent_num = len(current_stock_agents) + 1
                            buy_orders.append({
                                '작전구역': s_name, '코드': t_code, '요원명': f"{next_agent_num}호 요원",
                                '현재가': curr_price, '당일등락률': f"{daily_ret:+.2f}%",
                                '추천수량': buyable_shares, '필요금액': total_cost
                            })
            except Exception as e:
                st.error(f"⚠️ {s_name}({t_code}) 스캔 중 오류: {e}")

        st.markdown("---")
        if sell_orders:
            st.markdown("<h4 style='color:#2980b9;margin-bottom:8px;'>🔵 [오늘 시장가 매도(익절) 청산 지시]</h4>", unsafe_allow_html=True)
            for s in sell_orders:
                st.info(f"🎉 **{s['작전구역']} ({s['요원명']})** | 현재가: **{format_money(s['현재가'])}원** ({s['수익률']}) ➔ **전량 매도!** (주문 수량: **{s['수량']}주**)")

        if buy_orders:
            st.markdown("<h4 style='color:#c0392b;margin-bottom:8px;'>🔴 [오늘 시장가 매수 투입 지시]</h4>", unsafe_allow_html=True)
            for b in buy_orders:
                st.error(f"🎯 **{b['작전구역']} ({b['코드']})** | 당일 등락률: **{b['당일등락률']}** ➔ **{b['요원명']} 투입!** (주문 수량: **{b['추천수량']}주** / 필요 금액: {format_money(b['필요금액'])}원)")

        if not sell_orders and not buy_orders:
            st.success("🟢 **[오늘 작전 없음]** 조건을 충족한 종목이 없습니다.")

# --- 📥 체결 결과 정산 및 구글 시트 저장 ---
with st.expander("📥 [장 마감 후] 실제 체결 결과 정산 및 구글 시트 동기화"):
    trade_type = st.radio("매매 구분:", ["매수 체결 정산", "매도 체결 정산"], horizontal=True)
    
    if trade_type == "매수 체결 정산":
        col_b1, col_b2, col_b3, col_b4 = st.columns(4)
        with col_b1: b_stock = st.selectbox("종목 선택:", options=selected_stocks)
        with col_b2: b_price = st.number_input("실제 체결 단가(원):", value=10000, step=100)
        with col_b3: b_shares = st.number_input("실제 체결 수량(주):", value=10, step=1)
        with col_b4: b_agent_name = st.text_input("요원명:", value="1호 요원")
            
        if st.button("📥 매수 체결 확정 및 구글 시트 동기화"):
            t_code = stock_database[b_stock]
            s_name = b_stock.split(" (")[0]
            cost = b_price * b_shares
            
            st.session_state['active_agents'].append({
                'stock': s_name, 'code': t_code, 'name': b_agent_name,
                'entry_date': datetime.datetime.today().strftime('%Y-%m-%d'),
                'entry_price': b_price, 'shares': b_shares, 'target_ret': 10.0
            })
            st.session_state['real_cash'] -= cost
            
            # 구글 시트 즉시 업로드
            save_sheet_data("계좌현황", pd.DataFrame([{"총씨드머니": st.session_state['real_capital'], "예수금": st.session_state['real_cash']}]))
            save_sheet_data("보유요원", pd.DataFrame(st.session_state['active_agents']))
            st.success("✅ 매수 체결 내역이 구글 시트에 실시간으로 기록되었습니다!")
            st.rerun()

    else:
        if not st.session_state['active_agents']:
            st.info("현재 파견된 요원이 없습니다.")
        else:
            agent_options = [f"{a['stock']} - {a['name']} ({a['shares']}주 / 진입가: {format_money(a['entry_price'])}원)" for a in st.session_state['active_agents']]
            selected_ag_idx = st.selectbox("청산할 요원 선택:", options=range(len(agent_options)), format_func=lambda x: agent_options[x])
            s_price = st.number_input("실제 매도 체결 단가(원):", value=11000, step=100)
            
            if st.button("📤 매도 체결 확정 및 구글 시트 동기화"):
                target_ag = st.session_state['active_agents'].pop(selected_ag_idx)
                sell_amt = s_price * float(target_ag['shares'])
                st.session_state['real_cash'] += sell_amt
                
                # 구글 시트 즉시 업로드
                save_sheet_data("계좌현황", pd.DataFrame([{"총씨드머니": st.session_state['real_capital'], "예수금": st.session_state['real_cash']}]))
                save_sheet_data("보유요원", pd.DataFrame(st.session_state['active_agents']))
                st.success("🎉 매도 체결 및 실현 손익 정산이 구글 시트에 즉시 동기화되었습니다!")
                st.rerun()

st.markdown("#### 📋 [현재 보유 요원 실시간 명단]")
if st.session_state['active_agents']:
    st.table(pd.DataFrame(st.session_state['active_agents'])[['stock', 'name', 'entry_date', 'entry_price', 'shares', 'target_ret']])
