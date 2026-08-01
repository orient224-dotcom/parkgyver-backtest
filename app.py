import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import json
from dateutil.relativedelta import relativedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 0. 한글 초성 분리 및 모바일 검색용 포맷팅 엔진 ---
def get_chosung(text):
    chosung_list = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    result = ""
    for char in text:
        if '가' <= char <= '힣':
            idx = (ord(char) - ord('가')) // 588
            result += chosung_list[idx]
        else:
            result += char
    return result

def format_stock_option(stock_name):
    code = MASTER_STOCK_DICT.get(stock_name, "")
    chosung = get_chosung(stock_name)
    market = "코스닥" if code.endswith(".KQ") else "코스피"
    return f"{stock_name} ({chosung} | {market} {code})"

def clean_date_index(obj):
    if isinstance(obj, pd.Series):
        s = pd.to_datetime(obj)
        if s.dt.tz is not None:
            s = s.dt.tz_convert(None)
        return s.dt.normalize()
    elif isinstance(obj, (pd.DatetimeIndex, pd.Index)):
        idx = pd.to_datetime(obj)
        if getattr(idx, 'tz', None) is not None:
            idx = idx.tz_convert(None)
        return idx.normalize()
    else:
        dt = pd.to_datetime(obj)
        if getattr(dt, 'tz', None) is not None:
            dt = dt.tz_convert(None)
        return dt.normalize()

# 🌟 [업그레이드] 스노우볼 레벨업 상태가 반영된 스마트 컬러 음영 스타일러 함수
def style_trade_df(df):
    def apply_row_style(row):
        ret_val = str(row.get('순수익률', ''))
        reason = str(row.get('구분', ''))
        snow_level = str(row.get('스노우볼 레벨', ''))
        
        if '레벨UP' in snow_level:
            return ['background-color: #fef08a; color: #854d0e; font-weight: bold;'] * len(row) # 골드 옐로우 (스노우볼 레벨업 순간!)
        elif '특별 보너스' in reason:
            return ['background-color: #eff6ff; color: #1d4ed8; font-weight: bold;'] * len(row) # 연파랑 (배당금)
        elif '강제 철수' in reason or '-' in ret_val:
            return ['background-color: #fee2e2; color: #991b1b; font-weight: bold;'] * len(row) # 연분홍/빨강 (손절)
        elif '타임 컷' in reason:
            return ['background-color: #fff7ed; color: #c2410c; font-weight: bold;'] * len(row) # 연주황 (타임컷)
        elif '+' in ret_val or '정상 복귀' in reason or '추세연장' in reason:
            return ['background-color: #dcfce7; color: #166534; font-weight: bold;'] * len(row) # 연초록 (익절)
        else:
            return [''] * len(row)
            
    return df.style.apply(apply_row_style, axis=1)

# --- 1. 페이지 웹 디자인 세팅 ---
st.set_page_config(page_title="박가이버 통합 작전 사령부 V10.10", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    
    .algo-spec-container {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }
    .algo-spec-header {
        font-size: 1.1rem;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .algo-grid {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
    }
    .algo-card {
        flex: 1;
        min-width: 280px;
        background-color: #f8fafc;
        border-radius: 10px;
        padding: 14px 16px;
        border: 1px solid #e2e8f0;
    }
    .algo-card.card-1 { border-left: 6px solid #ef4444; }
    .algo-card.card-2 { border-left: 6px solid #f59e0b; }
    .algo-card.card-3 { border-left: 6px solid #10b981; }
    .algo-card.card-4 { border-left: 6px solid #2563eb; }
    
    .algo-card-title { font-size: 0.95rem; font-weight: 800; margin-bottom: 6px; }
    .algo-card-title.t-1 { color: #dc2626; }
    .algo-card-title.t-2 { color: #d97706; }
    .algo-card-title.t-3 { color: #059669; }
    .algo-card-title.t-4 { color: #2563eb; }
    .algo-card-desc { font-size: 0.85rem; color: #475569; line-height: 1.45; font-weight: 500; }

    .weather-card {
        background-color: #fffef2;
        border: 2px solid #f59e0b;
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(245, 158, 11, 0.08);
    }
    .weather-title { font-size: 1.1rem; font-weight: 800; color: #92400e; margin-bottom: 12px; display: flex; align-items: center; gap: 6px; }
    .weather-box-container { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
    .weather-pill { background-color: #ffffff; border: 1px solid #fcd34d; border-radius: 8px; padding: 8px 14px; font-size: 0.9rem; font-weight: 700; color: #78350f; flex: 1; min-width: 260px; }
    .weather-divider { border-top: 1px dashed #f59e0b; margin: 12px 0; }
    .weather-status-text { font-size: 0.88rem; color: #451a03; font-weight: 600; }

    .metric-card {
        background-color: #ffffff; border-radius: 10px; padding: 14px 16px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); border: 1px solid #e2e8f0; margin-bottom: 12px;
        height: 100%; display: flex; flex-direction: column; justify-content: space-between;
    }
    .metric-card.card-green { border-left: 6px solid #10b981; }
    .metric-card.card-blue { border-left: 6px solid #2563eb; }
    .metric-card.card-red { border-left: 6px solid #ef4444; }
    .metric-card.card-yellow { border-left: 6px solid #f59e0b; background-color: #fffbeb; }
    .metric-card.card-orange { border-left: 6px solid #d97706; }
    .metric-card.card-purple { border-left: 6px solid #a855f7; background-color: #faf5ff; border-top: 1px solid #f3e8ff; border-right: 1px solid #f3e8ff; border-bottom: 1px solid #f3e8ff; }

    .metric-label { font-size: 0.85rem; font-weight: 800; color: #475569; margin-bottom: 4px; display: flex; align-items: center; gap: 5px; }
    .metric-value { font-size: 1.35rem; font-weight: 900; color: #0f172a; margin-bottom: 4px; }
    .metric-sub { font-size: 0.78rem; color: #64748b; font-weight: 600; }

    .hero-banner { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 18px 20px; border-radius: 14px; color: #ffffff; border-left: 6px solid #38bdf8; box-shadow: 0 8px 20px -4px rgba(15, 23, 42, 0.2); margin-bottom: 20px; }
    .hero-title { font-size: 1.45rem; font-weight: 900; margin: 0; color: #f8fafc; }
    .hero-subtitle { font-size: 0.88rem; color: #94a3b8; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# --- 2. 기본 종목 마스터 사전 ---
BASE_STOCK_MASTER = {
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "테크윙": "089030.KQ", "한미반도체": "042700.KS",
    "HPSP": "403870.KQ", "이오테크닉스": "039030.KQ", "주성엔지니어링": "036930.KQ", "원익IPS": "240810.KQ",
    "한화오션": "042660.KS", "HD한국조선해양": "009540.KS", "현대로템": "064350.KS", "LIG넥스원": "079550.KS",
    "한화에어로스페이스": "012450.KS", "한국콜마": "161890.KS", "코스맥스": "192820.KS", "알테오젠": "196170.KQ",
    "셀트리온": "068270.KS", "삼성바이오로직스": "207940.KS", "현대차": "005380.KS", "기아": "000270.KS",
    "NAVER": "035420.KS", "카카오": "035720.KS", "HD현대일렉트릭": "267260.KS", "두산에너빌리티": "034020.KS",
    "KODEX 200": "069500.KS", "KODEX 코스닥150": "229200.KS", "KODEX 레버리지": "122630.KS", "TIGER 미국S&P500": "360750.KS"
}

if "full_stock_master" not in st.session_state:
    st.session_state["full_stock_master"] = BASE_STOCK_MASTER.copy()

if "custom_stocks" not in st.session_state: st.session_state["custom_stocks"] = {}
if "my_holdings" not in st.session_state: st.session_state["my_holdings"] = ["SK하이닉스", "한미반도체", "테크윙", "HD현대일렉트릭", "HPSP"]
if "my_watchlist" not in st.session_state: st.session_state["my_watchlist"] = ["한화오션", "현대로템", "RFHIC", "한국콜마"]

MASTER_STOCK_DICT = st.session_state["full_stock_master"]
for name, code in st.session_state["custom_stocks"].items():
    MASTER_STOCK_DICT[name] = code

TICKER_TO_SECTOR = {code: "우량주" for code in MASTER_STOCK_DICT.values()}

if "selected_stocks" not in st.session_state: st.session_state["selected_stocks"] = st.session_state["my_holdings"]

def format_money(num):
    if num is None or pd.isna(num): return "-"
    num_int = int(round(num))
    sign = "-" if num_int < 0 else ""
    return f"{sign}{abs(num_int):,}원"

def format_pure_number(num):
    if num is None or pd.isna(num): return "-"
    return f"{int(round(num)):,}"

def format_exact_price(num):
    if num is None or pd.isna(num): return "-"
    return f"{int(round(num)):,}원"

# --- 3. 사이드바 조종간 ---
st.sidebar.title("🎛️ 박가이버 사령부 V10.10")

st.sidebar.subheader("💾 나만의 작전 세팅 (휴대폰 관리)")
uploaded_cfg = st.sidebar.file_uploader("📤 내 전략 세팅 불러오기 (.json)", type=["json"], help="내 계좌 보유 종목 및 세팅 파일을 올립니다.")

if uploaded_cfg is not None:
    try:
        cfg_data = json.load(uploaded_cfg)
        if "my_holdings" in cfg_data: st.session_state["my_holdings"] = cfg_data["my_holdings"]
        if "my_watchlist" in cfg_data: st.session_state["my_watchlist"] = cfg_data["my_watchlist"]
        if "custom_stocks" in cfg_data: 
            st.session_state["custom_stocks"] = cfg_data["custom_stocks"]
            for name, code in cfg_data["custom_stocks"].items():
                MASTER_STOCK_DICT[name] = code
        st.session_state["selected_stocks"] = st.session_state["my_holdings"]
        st.sidebar.success("🎉 세팅 파일 복원 완료!")
        st.rerun()
    except Exception:
        st.sidebar.error("⚠️ 올바른 설정(.json) 파일이 아닙니다.")

st.sidebar.markdown("---")

menu_choice = st.sidebar.radio(
    "사령부 작전 모드선택",
    [
        "🗄️ 1. 내 계좌 영구 DB (보유 & 관심)", 
        "🚨 2. 오늘의 실전 매매 레이더", 
        "🛡️ 3. 과거 5년 백테스트 연구소"
    ],
    index=2
)
st.sidebar.markdown("---")

# =====================================================================
# 🗄️ 메뉴 1: 내 계좌 영구 DB (마이 포트폴리오 세팅 본부)
# =====================================================================
if menu_choice == "🗄️ 1. 내 계좌 영구 DB (보유 & 관심)":
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🗄️ 나만의 투자 영구 DB (스마트폰 연동)</div>
        <div class="hero-subtitle">스마트폰 전 종목 DB 연동으로 대한민국 2,600개 상장 종목을 초성 키보드로 1초 만에 검색하세요!</div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📲 🏛️ 대한민국 2,600개 전 종목 DB 스마트폰 연동 센터", expanded=True):
        col_db1, col_db2 = st.columns(2)
        
        with col_db1:
            st.markdown("##### 1️⃣ 스마트폰에 전 종목 DB 탑재하기")
            uploaded_db = st.file_uploader("📂 스마트폰의 krx_stock_db.json 업로드", type=["json"])
            if uploaded_db is not None:
                try:
                    loaded_db = json.load(uploaded_db)
                    st.session_state["full_stock_master"].update(loaded_db)
                    st.success(f"🎉 성공! 총 {len(st.session_state['full_stock_master']):,}개 전 종목 DB 탑재 완료!")
                    st.rerun()
                except Exception:
                    st.error("❌ 올바른 전 종목 DB 파일이 아닙니다.")
                    
        with col_db2:
            st.markdown("##### 2️⃣ 전 종목 DB 다운로드")
            st.caption("현재 통제실 DB 종목 수: **" + f"{len(MASTER_STOCK_DICT):,}개**")
            
            json_db_data = json.dumps(MASTER_STOCK_DICT, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 krx_stock_db.json 스마트폰에 저장",
                data=json_db_data,
                file_name="krx_stock_db.json",
                mime="application/json",
                use_container_width=True
            )

    st.markdown("---")

    db_tab1, db_tab2 = st.tabs(["💼 내 실전 보유 종목 (주력)", "⭐ 눈여겨보는 관심 종목"])

    with db_tab1:
        st.markdown("### 💼 1. 실전 보유 종목 DB 세팅")
        valid_holdings = [s for s in st.session_state["my_holdings"] if s in MASTER_STOCK_DICT]
        
        new_holdings = st.multiselect(
            "실전 보유 종목 편집 (초성 검색: 예: ㅅㅅㅈㅈ, ㅎㅁㅂㄷㅊ, ㅌㅋㅇ):",
            options=list(MASTER_STOCK_DICT.keys()),
            default=valid_holdings,
            format_func=format_stock_option,
            key="holding_multiselect"
        )
        if st.button("💾 실전 보유 종목 DB 저장", type="primary", use_container_width=True):
            st.session_state["my_holdings"] = new_holdings
            st.session_state["selected_stocks"] = new_holdings
            st.success("🎉 실전 보유 종목이 안전하게 저장되었습니다!")
            st.rerun()

    with db_tab2:
        st.markdown("### ⭐ 2. 관심 종목 DB 세팅")
        valid_watchlist = [s for s in st.session_state["my_watchlist"] if s in MASTER_STOCK_DICT]
        new_watchlist = st.multiselect(
            "관심 종목 편집 (초성 검색 지원):",
            options=list(MASTER_STOCK_DICT.keys()),
            default=valid_watchlist,
            format_func=format_stock_option,
            key="watchlist_multiselect"
        )
        if st.button("💾 관심 종목 DB 저장", type="secondary", use_container_width=True):
            st.session_state["my_watchlist"] = new_watchlist
            st.success("🎉 관심 종목이 안전하게 저장되었습니다!")
            st.rerun()

    st.markdown("---")
    
    with st.expander("➕ 목록에 없는 특수 종목 개별 등록", expanded=False):
        c_col1, c_col2 = st.columns(2)
        with c_col1: new_s_name = st.text_input("📝 종목명 (예: 신한지주)")
        with c_col2: new_s_code = st.text_input("🔢 종목코드 (예: 055550.KS)", help="코스피는 .KS / 코스닥은 .KQ")
        
        if st.button("✅ 내 DB에 종목 개별 추가", use_container_width=True):
            if new_s_name and new_s_code:
                st.session_state["custom_stocks"][new_s_name] = new_s_code.upper().strip()
                st.session_state["full_stock_master"][new_s_name] = new_s_code.upper().strip()
                st.success(f"🎉 **{new_s_name}** 종목이 새로 등록되었습니다!")
                st.rerun()

    st.markdown("---")
    st.markdown("### 💾 나만의 세팅 휴대폰 파일로 백업하기")
    cfg_to_save = {
        "my_holdings": st.session_state.get("my_holdings", []),
        "my_watchlist": st.session_state.get("my_watchlist", []),
        "custom_stocks": st.session_state.get("custom_stocks", {})
    }
    json_cfg_str = json.dumps(cfg_to_save, ensure_ascii=False, indent=2)
    st.download_button(
        label="📥 내 작전 세팅 휴대폰에 다운로드 (.json)",
        data=json_cfg_str,
        file_name="parkgyver_my_strategy_V10.json",
        mime="application/json",
        use_container_width=True
    )

# =====================================================================
# 🚨 메뉴 2: 오늘의 실전 매매 레이더 (출격 명령서 전용)
# =====================================================================
elif menu_choice == "🚨 2. 오늘의 실전 매매 레이더":
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🚨 오늘의 실전 매매 레이더 (출격 명령서)</div>
        <div class="hero-subtitle">매일 오후 3시 20분 종가 기준 | 내 계좌 DB 주력 종목의 매수 타점을 감시합니다.</div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.subheader("⚙️ 실전 매매 조건 설정")
    buy_cond_input = st.sidebar.slider("🛒 진입 기준 (-% 하락 시)", 1, 20, 5, 1, key="live_buy_cond")
    
    valid_watch_stocks = [s for s in st.session_state["my_holdings"] if s in MASTER_STOCK_DICT]
    PORTFOLIO_UNIVERSE = {s_name: MASTER_STOCK_DICT[s_name] for s_name in valid_watch_stocks if s_name in MASTER_STOCK_DICT}

    st.markdown(f"🎯 **[실전 감시 전광판] 현재 감시 종목 ({len(valid_watch_stocks)}개):** {', '.join(valid_watch_stocks)}")
    st.markdown("---")

    with st.spinner("📡 대한민국 증시 기상청 및 실시간 시세를 동기화 중입니다..."):
        last_ks_c, last_ks_ma, last_kq_c, last_kq_ma = None, None, None, None
        try:
            live_bench = yf.download(["^KS11", "^KQ11"], period="2mo", interval="1d", progress=False)
            bench_close = live_bench['Close'] if isinstance(live_bench.columns, pd.MultiIndex) and 'Close' in live_bench.columns.levels[0] else live_bench
            
            ks_key = '^KS11' if '^KS11' in bench_close.columns else bench_close.columns[0]
            kq_key = '^KQ11' if '^KQ11' in bench_close.columns else (bench_close.columns[1] if len(bench_close.columns) > 1 else ks_key)

            ks_series = bench_close[ks_key].ffill()
            kq_series = bench_close[kq_key].ffill()
            ks_ma20 = ks_series.rolling(window=20).mean()
            kq_ma20 = kq_series.rolling(window=20).mean()

            last_ks_c = float(ks_series.dropna().iloc[-1])
            last_ks_ma = float(ks_ma20.dropna().iloc[-1])
            last_kq_c = float(kq_series.dropna().iloc[-1])
            last_kq_ma = float(kq_ma20.dropna().iloc[-1])

            ks_weather = "🌧️ 먹구름 하락장" if last_ks_c < last_ks_ma else "☀️ 맑은 상승장"
            kq_weather = "🌧️ 먹구름 하락장" if last_kq_c < last_kq_ma else "☀️ 맑은 상승장"
            
            siren_html = f"""
            <div class="weather-card">
                <div class="weather-title">⛅ 대한민국 증시 기상청 실시간 현황</div>
                <div class="weather-box-container">
                    <div class="weather-pill">
                        [코스피 지수] {ks_weather} ({last_ks_c:,.1f}pt < 20일선 {last_ks_ma:,.1f}pt)
                    </div>
                    <div class="weather-pill">
                        [코스닥 지수] {kq_weather} ({last_kq_c:,.1f}pt < 20일선 {last_kq_ma:,.1f}pt)
                    </div>
                </div>
                <div class="weather-divider"></div>
                <div class="weather-status-text">
                    🔒 현재 통제실 상태: <b>{'🚨 하락장 경보 발령 (출격 보류 권장)' if (last_ks_c < last_ks_ma or last_kq_c < last_kq_ma) else '✅ 상승장 순풍 (정상 출격 가능)'}</b>
                </div>
            </div>
            """
            st.markdown(siren_html, unsafe_allow_html=True)
        except Exception:
            pass

        st.markdown("### 📡 실시간 출격 시그널 검사 결과")
        if len(PORTFOLIO_UNIVERSE) > 0:
            try:
                live_tickers = list(PORTFOLIO_UNIVERSE.values())
                live_raw = yf.download(live_tickers, period="5d", interval="1d", progress=False)
                live_data = live_raw['Close'] if isinstance(live_raw.columns, pd.MultiIndex) and 'Close' in live_raw.columns.levels[0] else (live_raw['Close'] if 'Close' in live_raw.columns else live_raw)
                
                buy_signals = []
                for name, code in PORTFOLIO_UNIVERSE.items():
                    s_data = live_data[code].dropna() if isinstance(live_data, pd.DataFrame) and code in live_data.columns else (live_data.dropna() if isinstance(live_data, pd.Series) else pd.Series())
                    if len(s_data) >= 2:
                        today_p = float(s_data.iloc[-1])
                        yester_p = float(s_data.iloc[-2])
                        change_pct = ((today_p - yester_p) / yester_p) * 100
                        
                        if change_pct <= -float(buy_cond_input):
                            is_kq = code.endswith('.KQ')
                            is_stormy = False
                            if is_kq and last_kq_c is not None and last_kq_ma is not None:
                                is_stormy = last_kq_c < last_kq_ma
                            elif not is_kq and last_ks_c is not None and last_ks_ma is not None:
                                is_stormy = last_ks_c < last_ks_ma
                                
                            warning_tag = "<span style='color:#e74c3c; font-weight:bold;'>(⚠️태풍 경보! 출격 보류)</span>" if is_stormy else "<span style='color:#27ae60; font-weight:bold;'>(✅순풍! 출격 가능)</span>"
                            buy_signals.append(f"🛒 **[{name}]** 변동률: **{change_pct:.2f}%** ➔ 오늘 3시 20분 타점! {warning_tag}")
                
                if buy_signals:
                    st.markdown("<div style='padding:15px; border-radius:8px; border:2px solid #e74c3c; background-color:#fef9e7;'>⚡ <b>오늘 실전 진입 타점에 포착된 종목이 있습니다!</b><br><br>" + "<br><br>".join(buy_signals) + "</div>", unsafe_allow_html=True)
                else:
                    st.success("✅ **현재 감시 종목 중 당일 급락 종목이 없습니다.** 요원들은 출격 대기 상태를 유지합니다.")
            except Exception:
                st.info("💡 실시간 시세를 동기화하는 중입니다.")
        else:
            st.warning("⚠️ 감시 종목이 없습니다. 메뉴 [🗄️ 1. 내 계좌 영구 DB]에서 주력 종목을 먼저 세팅해 주세요!")

    with st.expander("📖 [당귀다TV] 실전 출격 명령서 1분 가이드 (순수 종가 매매법)", expanded=True):
        st.markdown("""
        ### 🛡️ 직장인을 위한 '하루 1분 순수 종가(동시호가) 매매법' 핵심 수칙
        1. **👔 장중 감시 금지:** 장중 주가창을 보며 조바심을 내지 마세요. 본업에 온전히 집중합니다!
        2. **🕒 오후 3시 20분 접속:** 장 마감 직전 본 앱의 이 화면을 켜서 상단의 **`🚨 오늘의 실전 출격 명령서`**를 확인합니다.
        3. **🛒 원클릭 종가 매수:** 포착된 종목이 있다면 증권사 앱에서 **'종가(동시호가)'**로 매수 주문을 넣습니다.
        4. **🕒 오후 3시 20분 종가 청산(관리):** 매수한 다음 날부터 매일 오후 3시 20분, 계좌를 확인하여 목표가(+5%)나 손절가(-15%)에 도달했다면 **'종가(동시호가)'**로 깔끔하게 매도하여 수익을 수확합니다!
        """)

# =====================================================================
# 🛡️ 메뉴 3: 과거 5년 백테스트 연구소 (성과 검증 전용)
# =====================================================================
else:
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🛡️ 과거 백테스트 연구소 (스노우볼 레벨UP V10.10)</div>
        <div class="hero-subtitle">실전 검증 | 스노우볼 레벨업(자산 증액 구간) 추적과 스마트 컬러 음영 매매장부를 확인하세요.</div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("💡 🛡️ 박가이버표 매매 알고리즘 4대 동작 원리 명세서", expanded=True):
        spec_html = f"""
        <div class="algo-spec-container">
            <div class="algo-spec-header">💡 박가이버표 매매 알고리즘 핵심 동작 원리</div>
            <div class="algo-grid">
                <div class="algo-card card-1">
                    <div class="algo-card-title t-1">1. 🛡️ [대세 하락장] 자동 우산 방어 필터</div>
                    <div class="algo-card-desc">증시 기상청(지수 20일선) 태풍 또는 대세 하락 추세 구간에서는 <b>요원 출격을 일시 정지(Pause)</b>하여 원금 손실 위험을 사전에 완벽히 방어합니다.</div>
                </div>
                <div class="algo-card card-2">
                    <div class="algo-card-title t-2">2. 🛒 스마트 출격 타점 (-5% 이하 급락)</div>
                    <div class="algo-card-desc">선택하신 출격 기준(-5.0% 또는 -7.0% 이하 급락일)에만 대기 중인 요원이 설정된 1회 진입 금액만큼 <b>그날 종가로 기계적으로 파견</b>됩니다.</div>
                </div>
                <div class="algo-card card-3">
                    <div class="algo-card-title t-3">3. 🔥 하이브리드 추세연장 익절 스위치</div>
                    <div class="algo-card-desc">목표가(+5%) 달성 시 5일 이동평균선이 살아있으면 팔지 않고 <b>추세가 꺾일 때까지(+30%~+60%) 끝까지 수익을 극대화</b>합니다.</div>
                </div>
                <div class="algo-card card-4">
                    <div class="algo-card-title t-4">4. ⏱️ 철저한 타임컷 & 리스크 관리</div>
                    <div class="algo-card-desc">보유 기간 30일 초과 또는 -15% 손절선 도달 시 <b>그날 종가로 기계적 청산</b>하여 계좌 회전율과 현금 안전성을 비약적으로 높입니다.</div>
                </div>
            </div>
        </div>
        """
        st.markdown(spec_html, unsafe_allow_html=True)

    valid_watch_stocks = [s for s in st.session_state["my_holdings"] if s in MASTER_STOCK_DICT]
    PORTFOLIO_UNIVERSE = {s_name: MASTER_STOCK_DICT[s_name] for s_name in valid_watch_stocks if s_name in MASTER_STOCK_DICT}

    if valid_watch_stocks:
        st.success(f"🎯 **[백테스트 연구소 전광판] 내 계좌 DB 연동 종목 ({len(valid_watch_stocks)}개):** {', '.join(valid_watch_stocks)}")
    else:
        st.error("⚠️ **[감시 종목 경보]** 장전된 종목이 없습니다! 메뉴 **[🗄️ 1. 내 계좌 영구 DB]**에서 종목을 골라주세요.")

    st.sidebar.subheader("⚙️ 백테스트 전략 조건 설정")
    use_market_filter = st.sidebar.checkbox("🌤️ 대세 하락장 자동 우산 스위치", value=True)
    ma_period_choice = st.sidebar.radio("📏 하락장 우산 기준선 선택", [120, 240], index=1, horizontal=True)
    use_strict_ma_filter = st.sidebar.checkbox("📈 장기 이평선 위에서만 출격 (추세 필터)", value=False)
    use_sector_limit = st.sidebar.checkbox("🤹‍♂️ 동일 섹터 몰빵 방지 캡", value=True)
    use_time_cut = st.sidebar.checkbox("⏱️ 타임 컷 (최대 보유일 제한)", value=True)
    max_hold_days_input = st.sidebar.slider("⏳ 최대 보유 제한일 (일)", 5, 60, 30, 5) if use_time_cut else 9999
    
    st.sidebar.markdown("---")
    use_hybrid_trailing = st.sidebar.checkbox("🔥 하이브리드 추세연장 (목표가 달성 시 추세 홀딩)", value=True)
    use_weighted_entry = st.sidebar.checkbox("📉 하락폭 가중 매수 (폭락장에서 예산 가중 투입)", value=True)

    st.sidebar.markdown("---")
    total_capital_input = st.sidebar.number_input("🏦 총 작전 예산(원)", value=10000000, step=1000000, key="bt_capital")
    rec_default_invest = total_capital_input // 5
    invest_amount_input = st.sidebar.number_input("💰 회당 초기 진입금액(원)", value=int(rec_default_invest), step=500000, key="bt_invest")
    max_active_slots = max(1, int(total_capital_input // invest_amount_input))
    max_sector_slots = max(1, max_active_slots // 2)

    use_compounding = st.sidebar.checkbox("🚀 복리 스케일업 모드", value=True, key="bt_compound")
    time_unit = st.sidebar.radio("🗓️ 기간 단위", ["월 단위 (개월)", "년 단위 (년)"], horizontal=True, key="bt_tunit")

    if time_unit == "월 단위 (개월)":
        months_input = st.sidebar.slider("백테스트 기간(개월)", 1, 120, 60, 1, key="bt_m")
        period_label = f"{months_input}개월"
    else:
        years_val = st.sidebar.slider("백테스트 기간(년)", 1, 10, 5, 1, key="bt_y")
        months_input = years_val * 12
        period_label = f"{years_val}년"

    buy_cond_input = st.sidebar.slider("🛒 진입 기준 (-% 하락 시)", 1, 20, 5, 1, key="bt_buy")
    sell_target_input = st.sidebar.slider("🎯 익절 목표 (+%)", 1, 30, 5, 1, key="bt_sell")
    stop_loss_input = st.sidebar.slider("🚨 손절 기준 (-%)", 0, 50, 15, 1, key="bt_stop")

    st.sidebar.subheader("💸 거래비용 적용")
    use_fee = st.sidebar.checkbox("수수료/거래세 반영", value=True, key="bt_fee")
    broker_fee_pct = (st.sidebar.number_input("위탁수수료 (%)", value=0.015, format="%.3f") / 100) if use_fee else 0.0
    tax_pct = (st.sidebar.number_input("매도 거래세 (%)", value=0.18, format="%.2f") / 100) if use_fee else 0.0
    slippage_pct = (st.sidebar.number_input("체결 오차 (슬리피지) (%)", value=0.10, format="%.2f") / 100) if use_fee else 0.0

    reward_type = st.sidebar.selectbox("🎁 전리품 수령 방식", [
        "전액 현금으로 챙기기", 
        "🌟 현금 50% + 열매 50% (하이브리드)", 
        "🌟 현금 40% + 열매 60% (하이브리드 강화)", 
        "열매로 결실 모으기"
    ], index=0)

    st.sidebar.markdown("---")
    run_btn = st.sidebar.button("🚀 백테스트 타임머신 가동!", type="primary", use_container_width=True)

    if run_btn:
        if len(PORTFOLIO_UNIVERSE) == 0:
            st.error("❌ 감시 종목이 없습니다. 메뉴 [🗄️ 1. 내 계좌 영구 DB]에서 주력 종목을 먼저 세팅해 주세요!")
        else:
            with st.spinner("📡 슈퍼컴퓨터가 스노우볼 레벨업 및 백테스트 데이터를 안전하게 가동 중입니다..."):
                try:
                    end_date_str = datetime.datetime.today().strftime('%Y-%m-%d')
                    start_date_str = (datetime.datetime.today() - relativedelta(months=months_input)).strftime('%Y-%m-%d')
                    tickers = list(PORTFOLIO_UNIVERSE.values())
                    
                    raw_close = yf.download(tickers, start=start_date_str, end=end_date_str, interval="1d", progress=False)
                    if isinstance(raw_close.columns, pd.MultiIndex):
                        close_df = raw_close['Close'] if 'Close' in raw_close.columns.levels[0] else raw_close
                    elif 'Close' in raw_close.columns:
                        close_df = raw_close['Close'].to_frame() if len(tickers) == 1 else raw_close
                    else:
                        close_df = raw_close

                    if isinstance(close_df, pd.Series): close_df = close_df.to_frame(name=tickers[0])
                    close_df = close_df.dropna(how='all')

                    if close_df.empty:
                        st.error("❌ 야후 파이낸스에서 주가 데이터를 가져오지 못했습니다. 기간을 조정해 주세요.")
                        st.stop()

                    close_df.index = clean_date_index(close_df.index)

                    try:
                        raw_actions = yf.download(tickers, start=start_date_str, end=end_date_str, interval="1d", actions=True, progress=False)
                        div_df = raw_actions['Dividends'] if isinstance(raw_actions.columns, pd.MultiIndex) and 'Dividends' in raw_actions.columns.levels[0] else pd.DataFrame(0, index=close_df.index, columns=tickers)
                    except Exception:
                        div_df = pd.DataFrame(0, index=close_df.index, columns=tickers)
                    
                    div_df.index = clean_date_index(div_df.index)
                    div_df = div_df.reindex(close_df.index).fillna(0)

                    bench_df = pd.DataFrame()
                    bench_ma20 = pd.DataFrame()
                    try:
                        bench_raw = yf.download(["^KS11", "^KQ11"], start=start_date_str, end=end_date_str, interval="1d", progress=False)
                        bench_df = bench_raw['Close'] if isinstance(bench_raw.columns, pd.MultiIndex) and 'Close' in bench_raw.columns.levels[0] else bench_raw
                        if not bench_df.empty:
                            bench_df.index = clean_date_index(bench_df.index)
                            bench_ma20 = bench_df.rolling(window=20).mean()
                    except Exception:
                        pass

                    return_df = close_df.pct_change() * 100
                    sma_df = close_df.rolling(window=int(ma_period_choice)).mean()
                    ma5_df = close_df.rolling(window=5).mean()
                    ma20_df = close_df.rolling(window=20).mean()

                    buy_cond = -float(buy_cond_input)
                    sell_target = float(sell_target_input)
                    stop_loss_limit = -float(stop_loss_input) if stop_loss_input > 0 else None

                    current_cash = float(total_capital_input)
                    active_positions, trade_logs, daily_returns_history, asset_history = [], [], [], []
                    agent_counter = 0

                    yearly_stats = {}
                    free_shares_dict = {s_name: 0 for s_name in PORTFOLIO_UNIVERSE.keys()}
                    stock_win_stats = {s_name: {'success': 0, 'stop': 0, 'profit_gain': 0, 'loss_cost': 0} for s_name in PORTFOLIO_UNIVERSE.keys()}

                    total_success, total_stop_loss, total_cash_profit = 0, 0, 0
                    global_max_deployed = 0
                    daily_deployment_snapshots = []
                    missed_opportunities = []
                    total_dividend_profit = 0

                    peak_asset_value = float(total_capital_input)
                    max_drawdown_pct = 0.0

                    # 🌟 스노우볼 레벨업 추적 변수 (수익 +10% 축적 시마다 레벨UP)
                    current_snow_level = 1
                    last_level_threshold_asset = float(total_capital_input)
                    level_up_events_count = 0

                    for date, row in close_df.iterrows():
                        date_str = date.strftime('%Y-%m-%d')
                        year = date.year
                        if year not in yearly_stats:
                            yearly_stats[year] = {'success': 0, 'stop': 0, 'shares': 0, 'cash': 0, 'share_val': 0.0, 'stock_fruits': {}}
                        
                        daily_dividend_sum = 0
                        if date in div_df.index:
                            for s_name, count in free_shares_dict.items():
                                if count > 0:
                                    t_code = PORTFOLIO_UNIVERSE[s_name]
                                    if t_code in div_df.columns:
                                        d_val = div_df.loc[date, t_code]
                                        if pd.notna(d_val) and d_val > 0:
                                            daily_dividend_sum += count * d_val
                            for pos in active_positions:
                                t_code = pos['ticker']
                                if t_code in div_df.columns:
                                    d_val = div_df.loc[date, t_code]
                                    if pd.notna(d_val) and d_val > 0:
                                        pos_shares = pos['invest_amount'] / pos['entry_price']
                                        daily_dividend_sum += pos_shares * d_val
                        
                        if daily_dividend_sum > 0:
                            current_cash += daily_dividend_sum
                            total_dividend_profit += daily_dividend_sum
                            trade_logs.append({
                                '요원': '시스템', '작전 구역': '배당금(꿀) 수금', '출격일': date_str,
                                '진입일 등락률': '-', '진입금액': '-', '진입단가': '-', '복귀일': date_str,
                                '청산일 등락률': '-', '청산단가': '-', '매도금액': '-',
                                '등락폭': '-', '소요기간': '-', '순수익률': '-',
                                '정산내역': f"🍯 꿀 수입: +{format_pure_number(daily_dividend_sum)}원", '구분': '🌟 특별 보너스',
                                '스노우볼 레벨': f"Lv.{current_snow_level}"
                            })
                        
                        survived_positions = []
                        for pos in active_positions:
                            t_code = pos['ticker']
                            if t_code in row and not pd.isna(row[t_code]):
                                curr_price = float(row[t_code])
                                gross_ret = ((curr_price - pos['entry_price']) / pos['entry_price']) * 100
                                is_exit, exit_reason = False, ""

                                entry_dt = pd.to_datetime(pos['entry_date'])
                                exit_dt = pd.to_datetime(date_str)
                                days_taken = (exit_dt - entry_dt).days

                                ma5_val = ma5_df.loc[date, t_code] if t_code in ma5_df.columns and date in ma5_df.index else None
                                ma20_val = ma20_df.loc[date, t_code] if t_code in ma20_df.columns and date in ma20_df.index else None

                                if use_hybrid_trailing:
                                    if pos.get('trailing', False):
                                        if pd.notna(ma5_val) and pd.notna(ma20_val) and (curr_price < ma5_val or ma5_val < ma20_val):
                                            is_exit, exit_reason = True, "🔥 하이브리드 추세연장 익절"
                                    else:
                                        if gross_ret >= sell_target:
                                            if pd.notna(ma5_val) and pd.notna(ma20_val) and (ma5_val > ma20_val) and (curr_price >= ma5_val):
                                                pos['trailing'] = True
                                            else:
                                                is_exit, exit_reason = True, f"🎯 정상 복귀(+{sell_target_input}%)"
                                        elif stop_loss_limit is not None and gross_ret <= stop_loss_limit:
                                            is_exit, exit_reason = True, f"🚨 강제 철수(-{stop_loss_input}%)"
                                        elif use_time_cut and days_taken >= max_hold_days_input:
                                            is_exit, exit_reason = True, f"⏳ 타임 컷 ({max_hold_days_input}일 초과)"
                                else:
                                    if gross_ret >= sell_target:
                                        is_exit, exit_reason = True, f"🎯 정상 복귀(+{sell_target_input}%)"
                                    elif stop_loss_limit is not None and gross_ret <= stop_loss_limit:
                                        is_exit, exit_reason = True, f"🚨 강제 철수(-{stop_loss_input}%)"
                                    elif use_time_cut and days_taken >= max_hold_days_input:
                                        is_exit, exit_reason = True, f"⏳ 타임 컷 ({max_hold_days_input}일 초과)"

                                if is_exit:
                                    sell_gross_val = pos['invest_amount'] * (curr_price / pos['entry_price'])
                                    buy_fee = pos['invest_amount'] * broker_fee_pct
                                    sell_fee = sell_gross_val * broker_fee_pct
                                    sell_tax = sell_gross_val * tax_pct
                                    slippage_cost = (pos['invest_amount'] * slippage_pct) + (sell_gross_val * slippage_pct)
                                    total_trade_cost = buy_fee + sell_fee + sell_tax + slippage_cost

                                    net_profit = (sell_gross_val - pos['invest_amount']) - total_trade_cost
                                    net_ret = (net_profit / pos['invest_amount']) * 100
                                    s_name = pos['stock_name']
                                    
                                    price_diff = curr_price - pos['entry_price']
                                    diff_sign = "+" if price_diff >= 0 else ""
                                    price_change_str = f"{diff_sign}{format_pure_number(price_diff)}원 ({gross_ret:+.2f}%)"

                                    if gross_ret >= sell_target or net_profit > 0:
                                        total_success += 1
                                        yearly_stats[year]['success'] += 1
                                        stock_win_stats[s_name]['success'] += 1
                                        stock_win_stats[s_name]['profit_gain'] += net_profit
                                        
                                        if '전액 현금' in reward_type:
                                            buyable = 0
                                            leftover = net_profit
                                        elif '열매로 결실' in reward_type:
                                            buyable = int(max(0, net_profit) // curr_price)
                                            leftover = net_profit - (buyable * curr_price)
                                        elif '50%' in reward_type:
                                            share_budget = max(0, net_profit) * 0.5
                                            buyable = int(share_budget // curr_price)
                                            leftover = net_profit - (buyable * curr_price)
                                        elif '60%' in reward_type:
                                            share_budget = max(0, net_profit) * 0.6
                                            buyable = int(share_budget // curr_price)
                                            leftover = net_profit - (buyable * curr_price)
                                        else:
                                            buyable = 0
                                            leftover = net_profit
                                    else:
                                        total_stop_loss += 1
                                        yearly_stats[year]['stop'] += 1
                                        stock_win_stats[s_name]['stop'] += 1
                                        stock_win_stats[s_name]['loss_cost'] += net_profit
                                        buyable, leftover = 0, net_profit

                                    free_shares_dict[s_name] += buyable
                                    total_cash_profit += leftover
                                    current_cash += (pos['invest_amount'] + leftover)

                                    yearly_stats[year]['shares'] += buyable
                                    yearly_stats[year]['cash'] += leftover
                                    yearly_stats[year]['share_val'] += (buyable * curr_price)
                                    
                                    if buyable > 0:
                                        if s_name not in yearly_stats[year]['stock_fruits']:
                                            yearly_stats[year]['stock_fruits'][s_name] = {'shares': 0, 'value': 0}
                                        yearly_stats[year]['stock_fruits'][s_name]['shares'] += buyable
                                        yearly_stats[year]['stock_fruits'][s_name]['value'] += (buyable * curr_price)

                                    daily_returns_history.append(net_ret)

                                    log_reward = f"열매 {buyable}개 + 잔돈 {format_pure_number(leftover)}원" if buyable > 0 else f"{format_pure_number(leftover)}원"
                                    
                                    entry_day_ret = pos.get('entry_day_ret', 0)
                                    exit_day_ret = float(return_df.loc[date, t_code]) if date in return_df.index and t_code in return_df.columns and not pd.isna(return_df.loc[date, t_code]) else 0.0

                                    # 🌟 자산 증가에 따른 스노우볼 레벨업 체크 (+10% 축적 시)
                                    current_total_eval_check = current_cash + sum([p['invest_amount'] * (float(row[p['ticker']]) / p['entry_price']) for p in active_positions if p['ticker'] in row and not pd.isna(row[p['ticker']])])
                                    is_level_up = False
                                    if use_compounding and current_total_eval_check >= last_level_threshold_asset * 1.10:
                                        current_snow_level += 1
                                        level_up_events_count += 1
                                        last_level_threshold_asset = current_total_eval_check
                                        is_level_up = True

                                    level_display_str = f"🚀 Lv.{current_snow_level} (레벨UP!)" if is_level_up else f"Lv.{current_snow_level}"

                                    trade_logs.append({
                                        '요원': pos['name'], '작전 구역': pos['stock_name'], '출격일': pos['entry_date'],
                                        '진입일 등락률': f"{entry_day_ret:+.2f}%", '진입금액': f"{format_pure_number(pos['invest_amount'])}원",
                                        '진입단가': format_exact_price(pos['entry_price']), '복귀일': date_str,
                                        '청산일 등락률': f"{exit_day_ret:+.2f}%", '청산단가': format_exact_price(curr_price),
                                        '매도금액': f"{format_pure_number(sell_gross_val)}원", '등락폭': price_change_str,
                                        '소요기간': f"{days_taken}일 소요", '순수익률': f"{net_ret:+.2f}%",
                                        '정산내역': log_reward, '구분': exit_reason,
                                        '스노우볼 레벨': level_display_str
                                    })
                                else:
                                    survived_positions.append(pos)
                            else:
                                survived_positions.append(pos)
                        
                        active_positions = survived_positions
                        remaining_slots = max_active_slots - len(active_positions)
                        dynamic_invest_amount = max(float(invest_amount_input), current_cash / remaining_slots) if (use_compounding and remaining_slots > 0) else float(invest_amount_input)

                        day_returns = return_df.loc[date] if date in return_df.index else None
                        if day_returns is not None:
                            candidates = []
                            for s_name, t_code in PORTFOLIO_UNIVERSE.items():
                                if not any(p['ticker'] == t_code for p in active_positions) and t_code in day_returns and not pd.isna(day_returns[t_code]):
                                    ret_val = float(day_returns[t_code])
                                    target_buy_cond = buy_cond
                                    
                                    if t_code in sma_df.columns and date in sma_df.index:
                                        sma_val = sma_df.loc[date, t_code]
                                        curr_p = row[t_code]
                                        if pd.notna(sma_val) and pd.notna(curr_p):
                                            if use_strict_ma_filter and curr_p < sma_val:
                                                continue
                                            if use_market_filter and curr_p < sma_val:
                                                target_buy_cond = buy_cond * 1.4

                                    if ret_val <= target_buy_cond:
                                        candidates.append((s_name, t_code, ret_val, float(row[t_code])))
                            candidates.sort(key=lambda x: x[2])

                            for cand in candidates:
                                c_price = cand[3]
                                ret_val = cand[2]
                                t_code = cand[1]
                                s_name = cand[0]

                                if use_weighted_entry:
                                    weight = max(1.0, abs(ret_val) / abs(buy_cond_input))
                                    actual_invest = min(dynamic_invest_amount * weight, current_cash)
                                else:
                                    actual_invest = min(dynamic_invest_amount, current_cash)
                                
                                if use_sector_limit:
                                    c_sector = TICKER_TO_SECTOR.get(t_code, "기타")
                                    current_sector_count = sum(1 for p in active_positions if TICKER_TO_SECTOR.get(p['ticker'], "기타") == c_sector)
                                    if current_sector_count >= max_sector_slots:
                                        missed_opportunities.append({
                                            "발생 일자": date_str, "미출격 종목": s_name, "당일 하락률": f"{ret_val:.2f}%",
                                            "불가 사유": f"특정 섹터({c_sector}) 쏠림 방지 캡 도달"
                                        })
                                        continue

                                if c_price > actual_invest:
                                    missed_opportunities.append({
                                        "발생 일자": date_str, "미출격 종목": s_name, "당일 하락률": f"{ret_val:.2f}%",
                                        "불가 사유": f"1주 가격 초과"
                                    })
                                elif len(active_positions) >= max_active_slots:
                                    missed_opportunities.append({
                                        "발생 일자": date_str, "미출격 종목": s_name, "당일 하락률": f"{ret_val:.2f}%",
                                        "불가 사유": f"요원 슬롯 풀가동"
                                    })
                                elif actual_invest < 500000 or current_cash < 500000:
                                    missed_opportunities.append({
                                        "발생 일자": date_str, "미출격 종목": s_name, "당일 하락률": f"{ret_val:.2f}%",
                                        "불가 사유": f"가용 현금 부족"
                                    })
                                else:
                                    agent_counter += 1
                                    current_cash -= actual_invest
                                    active_positions.append({
                                        'name': f"{agent_counter}호 요원", 'stock_name': s_name, 'ticker': t_code,
                                        'entry_price': c_price, 'entry_date': date_str, 'invest_amount': actual_invest, 'entry_day_ret': ret_val,
                                        'trailing': False
                                    })

                        curr_count = len(active_positions)
                        if curr_count > global_max_deployed: global_max_deployed = curr_count
                        if curr_count > 0:
                            daily_deployment_snapshots.append({
                                "발생 일자": date_str, "동시 출격 수": curr_count,
                                "출격 종목 리스트": ", ".join([p['stock_name'] for p in active_positions])
                            })

                        eval_pos = sum([p['invest_amount'] * (float(row[p['ticker']]) / p['entry_price']) for p in active_positions if p['ticker'] in row and not pd.isna(row[p['ticker']])])
                        today_total_asset = current_cash + eval_pos
                        
                        if today_total_asset > peak_asset_value:
                            peak_asset_value = today_total_asset
                        current_drawdown = ((today_total_asset - peak_asset_value) / peak_asset_value) * 100
                        if current_drawdown < max_drawdown_pct:
                            max_drawdown_pct = current_drawdown
                        
                        asset_history.append({
                            "Date": date_str, 
                            "Total_Asset": today_total_asset, 
                            "Drawdown": current_drawdown,
                            "Invest_Scale": dynamic_invest_amount
                        })

                    asset_df = pd.DataFrame(asset_history)
                    kospi_ret_pct, kosdaq_ret_pct = 0.0, 0.0
                    bench_synced = False

                    if not bench_df.empty:
                        try:
                            bench_df_clean = bench_df.copy()
                            bench_df_clean.index = [d.strftime('%Y-%m-%d') for d in bench_df_clean.index]
                            ks_key = '^KS11' if '^KS11' in bench_df_clean.columns else bench_df_clean.columns[0]
                            kq_key = '^KQ11' if '^KQ11' in bench_df_clean.columns else (bench_df_clean.columns[1] if len(bench_df_clean.columns) > 1 else ks_key)
                            bench_aligned = bench_df_clean.reindex(asset_df['Date']).ffill().bfill()
                            
                            ks_start = float(bench_aligned[ks_key].dropna().iloc[0])
                            ks_end = float(bench_aligned[ks_key].dropna().iloc[-1])
                            kq_start = float(bench_aligned[kq_key].dropna().iloc[0])
                            kq_end = float(bench_aligned[kq_key].dropna().iloc[-1])

                            kospi_ret_pct = ((ks_end - ks_start) / ks_start) * 100 if ks_start > 0 else 0.0
                            kosdaq_ret_pct = ((kq_end - kq_start) / kq_start) * 100 if kq_start > 0 else 0.0

                            asset_df['KOSPI (지수)'] = (bench_aligned[ks_key].values / ks_start) * total_capital_input
                            asset_df['KOSDAQ (지수)'] = (bench_aligned[kq_key].values / kq_start) * total_capital_input
                            bench_synced = True
                        except Exception:
                            pass

                    asset_df['내 총자산'] = asset_df['Total_Asset']

                    last_row = close_df.iloc[-1]
                    active_eval_value = sum([p['invest_amount'] * (float(last_row[p['ticker']]) / p['entry_price']) for p in active_positions if p['ticker'] in last_row and not pd.isna(last_row[p['ticker']])])
                    total_free_shares_count = sum(free_shares_dict.values())
                    total_free_shares_value = sum([count * float(last_row[PORTFOLIO_UNIVERSE[s_name]]) for s_name, count in free_shares_dict.items() if count > 0 and PORTFOLIO_UNIVERSE[s_name] in last_row and not pd.isna(last_row[PORTFOLIO_UNIVERSE[s_name]])])

                    final_total_asset = current_cash + active_eval_value + total_free_shares_value
                    total_net_profit = final_total_asset - total_capital_input
                    total_return_pct = (total_net_profit / total_capital_input) * 100
                    total_trades = total_success + total_stop_loss
                    win_rate = (total_success / total_trades * 100) if total_trades > 0 else 0

                    current_query_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    backtest_period_str = f"{start_date_str} ~ {end_date_str} ({period_label})"
                    
                    initial_scale = float(invest_amount_input)
                    final_scale = float(asset_df['Invest_Scale'].iloc[-1]) if not asset_df.empty else initial_scale
                    scale_growth_pct = ((final_scale - initial_scale) / initial_scale) * 100 if initial_scale > 0 else 0

                    st.markdown(f"""
                    <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 15px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; flex-wrap: wrap; gap: 10px;">
                        <div>
                            <h2 style="margin: 0; font-size: 1.4rem; color: #0f172a; font-weight: 800;">🏆 백테스트 최종 성과 대시보드</h2>
                            <p style="margin: 4px 0 0 0; font-size: 0.85rem; color: #475569; font-weight: 700;">
                                📅 검증 기간: <b style="color: #2563eb;">{backtest_period_str}</b> | 📏 기준선: <b style="color: #2563eb;">{ma_period_choice}일선 적용</b>
                            </p>
                        </div>
                        <span style="font-size: 0.85rem; color: #64748b; font-weight: 600; background: #f1f5f9; padding: 4px 10px; border-radius: 6px; border: 1px solid #cbd5e1;">
                            🕒 조회: <b style="color: #0284c7;">{current_query_time}</b>
                        </span>
                    </div>
                    """, unsafe_allow_html=True)

                    last_ks_c, last_ks_ma, last_kq_c, last_kq_ma = None, None, None, None
                    if not bench_df.empty and not bench_ma20.empty:
                        ks_key = '^KS11' if '^KS11' in bench_df.columns else bench_df.columns[0]
                        kq_key = '^KQ11' if '^KQ11' in bench_df.columns else (bench_df.columns[1] if len(bench_df.columns) > 1 else ks_key)
                        
                        last_ks_c = float(bench_df[ks_key].dropna().iloc[-1]) if ks_key in bench_df else None
                        last_ks_ma = float(bench_ma20[ks_key].dropna().iloc[-1]) if ks_key in bench_ma20 else None
                        last_kq_c = float(bench_df[kq_key].dropna().iloc[-1]) if kq_key in bench_df else None
                        last_kq_ma = float(bench_ma20[kq_key].dropna().iloc[-1]) if kq_key in bench_ma20 else None

                        if last_ks_c is not None and last_ks_ma is not None and last_kq_c is not None and last_kq_ma is not None:
                            ks_weather = "🌧️ 먹구름 하락장" if last_ks_c < last_ks_ma else "☀️ 맑은 상승장"
                            kq_weather = "🌧️ 먹구름 하락장" if last_kq_c < last_kq_ma else "☀️ 맑은 상승장"
                            siren_html = f"""
                            <div class="weather-card">
                                <div class="weather-title">⛅ 대한민국 증시 기상청 실시간 현황</div>
                                <div class="weather-box-container">
                                    <div class="weather-pill">
                                        [코스피 지수] {ks_weather} ({last_ks_c:,.1f}pt < 20일선 {last_ks_ma:,.1f}pt)
                                    </div>
                                    <div class="weather-pill">
                                        [코스닥 지수] {kq_weather} ({last_kq_c:,.1f}pt < 20일선 {last_kq_ma:,.1f}pt)
                                    </div>
                                </div>
                                <div class="weather-divider"></div>
                                <div class="weather-status-text">
                                    🔒 백테스트 기준 상태: <b>{'🚨 하락장 우산 스위치 작동 중' if (last_ks_c < last_ks_ma or last_kq_c < last_kq_ma) else '✅ 상승장 순풍'}</b>
                                </div>
                            </div>
                            """
                            st.markdown(siren_html, unsafe_allow_html=True)

                    row1_col1, row1_col2, row1_col3, row1_col4 = st.columns(4)
                    with row1_col1:
                        st.markdown(f"""
                        <div class="metric-card card-green">
                            <div class="metric-label">🎯 청산 승률</div>
                            <div class="metric-value">{win_rate:.1f}%</div>
                            <div class="metric-sub">익절 {total_success} / 손절 {total_stop_loss}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with row1_col2:
                        st.markdown(f"""
                        <div class="metric-card card-blue">
                            <div class="metric-label">⚔️ 총 투입 요원</div>
                            <div class="metric-value">{agent_counter}명</div>
                            <div class="metric-sub">교전 대기중 요원: {len(active_positions)}명</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with row1_col3:
                        st.markdown(f"""
                        <div class="metric-card card-red">
                            <div class="metric-label">🏰 최대 동시 출격 요원</div>
                            <div class="metric-value">{global_max_deployed}명</div>
                            <div class="metric-sub">전체 슬롯: 총 {max_active_slots}개</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with row1_col4:
                        # 🌟 [스노우볼 레벨UP 카드 반영]
                        st.markdown(f"""
                        <div class="metric-card card-yellow">
                            <div class="metric-label">🚀 스노우볼 레벨UP</div>
                            <div class="metric-value">Lv.{current_snow_level} (레벨UP {level_up_events_count}회)</div>
                            <div class="metric-sub">수익 +10% 축적 시마다 예산 증액</div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.write("")

                    row2_col1, row2_col2, row2_col3, row2_col4, row2_col5 = st.columns(5)
                    with row2_col1:
                        st.markdown(f"""
                        <div class="metric-card card-blue">
                            <div class="metric-label">💵 현재 보유 현금(예수금)</div>
                            <div class="metric-value">{format_pure_number(current_cash)}원</div>
                            <div class="metric-sub">출금 / 재투입 가능 실탄 현금</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with row2_col2:
                        st.markdown(f"""
                        <div class="metric-card card-yellow">
                            <div class="metric-label">📈 대기주식 평가금</div>
                            <div class="metric-value">{format_pure_number(active_eval_value)}원</div>
                            <div class="metric-sub">대기 요원 {len(active_positions)}명 주식 평가가</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with row2_col3:
                        profit_sign = "+" if total_net_profit >= 0 else ""
                        st.markdown(f"""
                        <div class="metric-card card-orange">
                            <div class="metric-label">💰 누적 실현 순수익</div>
                            <div class="metric-value">{profit_sign}{format_pure_number(total_net_profit)}원</div>
                            <div class="metric-sub">매매순익 + 주식평가손익</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with row2_col4:
                        st.markdown(f"""
                        <div class="metric-card card-orange">
                            <div class="metric-label">🚀 계좌 총자산</div>
                            <div class="metric-value">{format_pure_number(final_total_asset)}원</div>
                            <div class="metric-sub">현금 + 대기주식 + 공짜주식</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with row2_col5:
                        st.markdown(f"""
                        <div class="metric-card card-purple">
                            <div class="metric-label">📦 확보 공짜주식</div>
                            <div class="metric-value">{total_free_shares_count}주</div>
                            <div class="metric-sub">평가 가치: {format_money(total_free_shares_value)}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("---")
                    st.markdown("### 📊 벤치마크 시장 지수 대비 수익률 초과 달성 리포트")
                    b_col1, b_col2, b_col3 = st.columns(3)
                    b_col1.metric("🛡️ 내 박가이버 작전 수익률", f"{total_return_pct:+.2f}%")
                    if bench_synced:
                        b_col2.metric("📉 KOSPI 지수", f"{kospi_ret_pct:+.2f}%", delta=f"지수 대비 {(total_return_pct - kospi_ret_pct):+.2f}%p 초과")
                        b_col3.metric("📉 KOSDAQ 지수", f"{kosdaq_ret_pct:+.2f}%", delta=f"지수 대비 {(total_return_pct - kosdaq_ret_pct):+.2f}%p 초과")
                    else:
                        b_col2.metric("📉 KOSPI 지수", "동기화 대기중")
                        b_col3.metric("📉 KOSDAQ 지수", "동기화 대기중")

                    if total_free_shares_count > 0:
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); padding: 16px 20px; border-radius: 12px; border-left: 6px solid #22c55e; margin-top: 15px; margin-bottom: 20px;">
                            <h4 style="margin-top: 0; color: #166534; font-size: 1.1rem; margin-bottom: 8px;">📦 내 공짜 주식(무위험 자산) 금고 상세 현황</h4>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        fruit_list = []
                        for s_name, count in free_shares_dict.items():
                            if count > 0:
                                t_code = PORTFOLIO_UNIVERSE[s_name]
                                c_price = float(last_row[t_code]) if t_code in last_row and not pd.isna(last_row[t_code]) else 0
                                eval_val = count * c_price
                                fruit_list.append({
                                    "작전 구역 (종목명)": s_name,
                                    "공짜주식 보유 수량": f"{count}주",
                                    "현재 1주 단가": format_exact_price(c_price),
                                    "현재 공짜주식 평가액": format_money(eval_val)
                                })
                        st.dataframe(pd.DataFrame(fruit_list), use_container_width=True, hide_index=True)

                    tab1, tab2, tab3, tab4 = st.tabs([
                        "📊 1. 자산 성장 & 복리 스케일업 차트", 
                        "🔍 2. 자금 회전율 & 동시 투입 분포", 
                        "📈 3. 종목/연도별 손익분석", 
                        "📜 4. 현장 투입요원 & 매매장부"
                    ])

                    with tab1:
                        fig = make_subplots(
                            rows=3, cols=1, 
                            shared_xaxes=True, 
                            vertical_spacing=0.08, 
                            row_heights=[0.5, 0.25, 0.25],
                            subplot_titles=("🏆 1. 총자산 증식 추이", "🚀 2. 1회 출격 예산(복리 스케일업) 증식 추이", "🌊 3. 계좌 최대 낙폭 (MDD)")
                        )
                        
                        fig.add_trace(go.Scatter(x=asset_df['Date'], y=asset_df['Total_Asset'], mode='lines', name='내 총자산', line=dict(color='#2563eb', width=3), fill='tozeroy', fillcolor='rgba(37, 99, 235, 0.08)'), row=1, col=1)
                        if bench_synced:
                            fig.add_trace(go.Scatter(x=asset_df['Date'], y=asset_df['KOSPI (지수)'], mode='lines', name='KOSPI 지수', line=dict(color='#94a3b8', width=1.5, dash='dash')), row=1, col=1)
                            fig.add_trace(go.Scatter(x=asset_df['Date'], y=asset_df['KOSDAQ (지수)'], mode='lines', name='KOSDAQ 지수', line=dict(color='#cbd5e1', width=1.5, dash='dot')), row=1, col=1)
                        fig.add_hline(y=total_capital_input, line_dash="solid", line_color="#ef4444", annotation_text="초기 원금", row=1, col=1)
                        
                        fig.add_trace(go.Scatter(x=asset_df['Date'], y=asset_df['Invest_Scale'], mode='lines', name='1회 출격 예산(스케일)', line=dict(color='#16a34a', width=2.5), fill='tozeroy', fillcolor='rgba(22, 163, 74, 0.08)'), row=2, col=1)
                        fig.add_hline(y=invest_amount_input, line_dash="dash", line_color="#16a34a", annotation_text="초기 1회 예산", row=2, col=1)
                        
                        fig.add_trace(go.Scatter(x=asset_df['Date'], y=asset_df['Drawdown'], mode='lines', name='낙폭(MDD)', line=dict(color='#dc2626', width=1.5), fill='tozeroy', fillcolor='rgba(220, 38, 38, 0.15)'), row=3, col=1)
                        
                        fig.update_layout(height=800, template="plotly_white", margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                        st.plotly_chart(fig, use_container_width=True)

                    with tab2:
                        st.write("### 🔍 자금 회전율 & 요원 동시 투입 분포 리포트")
                        
                        if daily_deployment_snapshots:
                            snap_df = pd.DataFrame(daily_deployment_snapshots)
                            total_deploy_sessions = len(snap_df)
                            c1_cnt = int((snap_df['동시 출격 수'] == 1).sum())
                            c2_cnt = int((snap_df['동시 출격 수'] == 2).sum())
                            c3_cnt = int((snap_df['동시 출격 수'] == 3).sum())
                            c4_cnt = int((snap_df['동시 출격 수'] == 4).sum())
                            cf_cnt = int((snap_df['동시 출격 수'] >= max_active_slots).sum())

                            c1_pct = (c1_cnt / total_deploy_sessions * 100) if total_deploy_sessions > 0 else 0.0
                            c2_pct = (c2_cnt / total_deploy_sessions * 100) if total_deploy_sessions > 0 else 0.0
                            c3_pct = (c3_cnt / total_deploy_sessions * 100) if total_deploy_sessions > 0 else 0.0
                            c4_pct = (c4_cnt / total_deploy_sessions * 100) if total_deploy_sessions > 0 else 0.0
                            cf_pct = (cf_cnt / total_deploy_sessions * 100) if total_deploy_sessions > 0 else 0.0
                        else:
                            total_deploy_sessions = 0
                            c1_cnt, c2_cnt, c3_cnt, c4_cnt, cf_cnt = 0, 0, 0, 0, 0
                            c1_pct, c2_pct, c3_pct, c4_pct, cf_pct = 0.0, 0.0, 0.0, 0.0, 0.0

                        dist_html = f"""
                        <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px 20px; margin-top: 10px; margin-bottom: 25px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);">
                            <div style="font-size: 1.05rem; font-weight: 800; color: #1e293b; margin-bottom: 14px; display: flex; align-items: center; gap: 6px;">
                                📊 작전 회차별 요원 동시 투입 분포 현황 (총 {total_deploy_sessions}개 작전 회차)
                            </div>
                            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                                <div style="flex: 1; min-width: 130px; background-color: #f0fdf4; border-left: 5px solid #10b981; border-radius: 8px; padding: 10px 14px; border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0;">
                                    <div style="font-size: 0.82rem; font-weight: 700; color: #166534;">1명 투입</div>
                                    <div style="font-size: 1.2rem; font-weight: 900; color: #0f172a; margin-top: 2px;">
                                        {c1_cnt}회 <span style="font-size: 0.82rem; font-weight: 600; color: #475569;">({c1_pct:.1f}%)</span>
                                    </div>
                                </div>
                                <div style="flex: 1; min-width: 130px; background-color: #f0fdf4; border-left: 5px solid #10b981; border-radius: 8px; padding: 10px 14px; border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0;">
                                    <div style="font-size: 0.82rem; font-weight: 700; color: #166534;">2명 투입</div>
                                    <div style="font-size: 1.2rem; font-weight: 900; color: #0f172a; margin-top: 2px;">
                                        {c2_cnt}회 <span style="font-size: 0.82rem; font-weight: 600; color: #475569;">({c2_pct:.1f}%)</span>
                                    </div>
                                </div>
                                <div style="flex: 1; min-width: 130px; background-color: #fefce8; border-left: 5px solid #eab308; border-radius: 8px; padding: 10px 14px; border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0;">
                                    <div style="font-size: 0.82rem; font-weight: 700; color: #854d0e;">3명 투입</div>
                                    <div style="font-size: 1.2rem; font-weight: 900; color: #0f172a; margin-top: 2px;">
                                        {c3_cnt}회 <span style="font-size: 0.82rem; font-weight: 600; color: #475569;">({c3_pct:.1f}%)</span>
                                    </div>
                                </div>
                                <div style="flex: 1; min-width: 130px; background-color: #fefce8; border-left: 5px solid #eab308; border-radius: 8px; padding: 10px 14px; border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0;">
                                    <div style="font-size: 0.82rem; font-weight: 700; color: #854d0e;">4명 투입</div>
                                    <div style="font-size: 1.2rem; font-weight: 900; color: #0f172a; margin-top: 2px;">
                                        {c4_cnt}회 <span style="font-size: 0.82rem; font-weight: 600; color: #475569;">({c4_pct:.1f}%)</span>
                                    </div>
                                </div>
                                <div style="flex: 1; min-width: 130px; background-color: #fef2f2; border-left: 5px solid #ef4444; border-radius: 8px; padding: 10px 14px; border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0;">
                                    <div style="font-size: 0.82rem; font-weight: 700; color: #991b1b;">🔥 최대 풀출격</div>
                                    <div style="font-size: 1.15rem; font-weight: 900; color: #0f172a; margin-top: 2px;">
                                        {cf_cnt}회 <span style="font-size: 0.82rem; font-weight: 600; color: #475569;">({cf_pct:.1f}%)</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        """
                        st.markdown(dist_html, unsafe_allow_html=True)

                        st.warning(f"📊 기간 중 최대 동시 출격 수: **총 {global_max_deployed}개 종목** (전체 슬롯: {max_active_slots}개)")
                        if daily_deployment_snapshots:
                            snap_df = pd.DataFrame(daily_deployment_snapshots)
                            peak_df = snap_df[snap_df['동시 출격 수'] == global_max_deployed].drop_duplicates(subset=['발생 일자'])
                            st.write("▼ **역대 최고 자금 몰림(피크) 발생 일자 및 출격 목록:**")
                            st.dataframe(peak_df, use_container_width=True, hide_index=True)

                        st.markdown("---")
                        st.write("### 🚫 현금/슬롯/섹터 제한으로 놓쳐버린 출격 타점 추적기")
                        if missed_opportunities:
                            st.error(f"🚨 하락 타점이 맞았으나 제한으로 놓친 기회: 총 {len(missed_opportunities)}회")
                            st.dataframe(pd.DataFrame(missed_opportunities), use_container_width=True, hide_index=True)
                        else:
                            st.success("🎉 단 한 번도 현금이나 슬롯이 부족해서 출격 기회를 놓친 적이 없습니다!")

                    with tab3:
                        st.write("### 📊 종목 및 연도별 정밀 성적표")
                        c_col1, c_col2 = st.columns([1.2, 1])
                        with c_col1:
                            st.write("#### 🗓️ 연도별 익절 vs 손절 건수 그래프")
                            yearly_chart_data = []
                            for y, val in yearly_stats.items():
                                yearly_chart_data.append({"연도": str(y), "구분": "🎯 익절", "건수": val['success']})
                                yearly_chart_data.append({"연도": str(y), "구분": "🚨 손절", "건수": val['stop']})
                            fig_bar = px.bar(pd.DataFrame(yearly_chart_data), x="연도", y="건수", color="구분", barmode="group", color_discrete_map={"🎯 익절": "#22c55e", "🚨 손절": "#ef4444"})
                            st.plotly_chart(fig_bar, use_container_width=True)
                        with c_col2:
                            st.write("#### 🗓️ 연도별 정산 종합표")
                            yearly_summary_list = []
                            for y, val in sorted(yearly_stats.items()):
                                yearly_summary_list.append({"연도": str(y), "🎯 익절": f"{val['success']}회", "🚨 손절": f"{val['stop']}회", "📦 획득 공짜주식": f"{int(val['shares'])}주", "💵 현금수익": format_money(val['cash'])})
                            st.dataframe(pd.DataFrame(yearly_summary_list), use_container_width=True, hide_index=True)

                        st.markdown("---")
                        st.write("#### 📦 종목별 누적 공짜주식 수확 총합계 리포트")
                        total_stock_fruit_summary = []
                        for s_name in PORTFOLIO_UNIVERSE.keys():
                            total_shares = free_shares_dict.get(s_name, 0)
                            t_code = PORTFOLIO_UNIVERSE[s_name]
                            c_price = float(last_row[t_code]) if t_code in last_row and not pd.isna(last_row[t_code]) else 0
                            eval_val = total_shares * c_price
                            total_stock_fruit_summary.append({
                                "작전 구역 (종목명)": s_name,
                                "총 수확한 공짜주식 수": f"{total_shares}주",
                                "현재 1주 단가": format_exact_price(c_price),
                                "현재 공짜주식 총 평가액": format_money(eval_val)
                            })
                        st.dataframe(pd.DataFrame(total_stock_fruit_summary), use_container_width=True, hide_index=True)

                    with tab4:
                        st.write("### ⚔️ 현재 현장 투입 요원 현황")
                        if len(active_positions) > 0:
                            active_table = []
                            tot_inv, tot_eval, tot_prof = 0, 0, 0
                            for p in active_positions:
                                t_code = p['ticker']
                                curr_price = float(last_row[t_code]) if t_code in last_row and not pd.isna(last_row[t_code]) else p['entry_price']
                                eval_val = p['invest_amount'] * (curr_price / p['entry_price'])
                                eval_profit = eval_val - p['invest_amount']
                                ret = ((curr_price - p['entry_price']) / p['entry_price']) * 100
                                tot_inv += p['invest_amount']
                                tot_eval += eval_val
                                tot_prof += eval_profit
                                
                                status_str = "🔥 추세 홀딩 중" if p.get('trailing', False) else "⚔️ 대기중"

                                active_table.append({
                                    '요원': p['name'], '구역명': p['stock_name'], '출격일': p['entry_date'],
                                    '출격 당시 주가': format_exact_price(p['entry_price']),
                                    '진입금액': f"{format_pure_number(p['invest_amount'])}원",
                                    '현재 평가금액': f"{format_pure_number(eval_val)}원",
                                    '평가 손익': f"{format_pure_number(eval_profit)}원",
                                    '현재수익률': f"{ret:.2f}%",
                                    '상태': status_str
                                })

                            st.success(f"⚔️ **현재 현장 교전(투입) 중인 요원: 총 {len(active_positions)}명**")
                            ac1, ac2, ac3 = st.columns(3)
                            ac1.metric("💰 투입 원금 합계", f"{format_pure_number(tot_inv)}원")
                            ac2.metric("📊 현재 평가금액 합계", f"{format_pure_number(tot_eval)}원")
                            ac3.metric("📈 평가 손익 합계", f"{format_pure_number(tot_prof)}원")
                            st.dataframe(pd.DataFrame(active_table), use_container_width=True, hide_index=True)
                        else:
                            st.success("🎉 현재 현장에 대기 중인 요원이 없습니다! (100% 현금 회수 완료 상태)")

                        st.markdown("---")
                        st.write("### 📜 전체 매매 장부 (스노우볼 레벨UP & 스마트 컬러 음영 적용)")
                        if trade_logs:
                            logs_df = pd.DataFrame(list(reversed(trade_logs)))
                            
                            # 🌟 [스노우볼 레벨업 음영 스타일러 적용]
                            styled_logs_df = style_trade_df(logs_df)
                            st.dataframe(styled_logs_df, use_container_width=True)
                            
                            metadata_header = f"""# ===================================================
# 🛡️ 박가이버 통합 작전 사령부 백테스트 설정 조건
# ===================================================
# 🕒 생성 일시: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 📅 백테스트 기간: {period_label} ({start_date_str} ~ {end_date_str})
# 🛒 진입 기준: -{buy_cond_input}% 이하 하락 시
# 🎯 익절 목표: +{sell_target_input}%
# 🚨 손절 기준: -{stop_loss_input}%
# ⏱️ 타임 컷: {f'{max_hold_days_input}일' if use_time_cut else '미사용'}
# 🚀 복리 스케일업 모드: {'ON (적용)' if use_compounding else 'OFF (미적용)'}
# 📉 하락폭 가중 매수: {'ON (적용)' if use_weighted_entry else 'OFF (미적용)'}
# 🔥 하이브리드 추세연장: {'ON (적용)' if use_hybrid_trailing else 'OFF (미적용)'}
# 🎁 전리품 수령 방식: {reward_type}
# ===================================================

"""
                            csv_body = logs_df.to_csv(index=False)
                            full_csv_content = metadata_header + csv_body
                            
                            st.download_button(
                                label="📥 엑셀(CSV) 매매장부 다운로드 (설정 조건 메타데이터 포함)",
                                data=full_csv_content.encode('utf-8-sig'),
                                file_name=f"당귀다TV_매매장부_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/css",
                            )

                except Exception as e:
                    st.error(f"❌ 분석 중 에러가 발생했습니다: {e}")
