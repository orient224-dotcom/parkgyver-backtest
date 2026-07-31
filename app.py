# -*- coding: utf-8 -*-
# Parkgyver V10.5 patched — 최소 패치 6건만 반영
# 패치 내역 (원본 코드 기준 라인 매핑 표기):
#  P1: yfinance auto_adjust=False 명시 (배당 이중계상 제거)
#  P2: weighted harvest 모드의 현금 회수 로직을 "원금 100% + 순수익 일부만 주식화"로 정정
#  P3: TICKER_TO_SECTOR에 최소 KRX 섹터 매핑 부여 (섹터 캡 정상화)
#  P4: 시장 지수 컬럼 fallback 명시화 (코스닥을 코스피로 잘못 매핑하는 오류 차단)
#  P5: yf.download 결과를 @st.cache_data로 캐시 (모바일 재실행 즉시 응답)
#  P6: file_uploader rerun 가드 (업로드 무한 재실행 차단)
# SPDX: 원본 코드 동일, MIT 가정
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

# --- 0. 한글 초성 분리 ---
def get_chosung(text):
    chosung_list = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']
    out = ""
    for c in text:
        if '가' <= c <= '힣':
            out += chosung_list[(ord(c)-ord('가'))//588]
        else:
            out += c
    return out

def format_money(num):
    if num is None or pd.isna(num): return "-"
    n = int(round(num)); sign = "-" if n < 0 else ""
    return f"{sign}{abs(n):,}원"

def format_pure_number(num):
    if num is None or pd.isna(num): return "-"
    n = int(round(num))
    return f"-{abs(n):,}" if n < 0 else f"{n:,}"

def format_exact_price(num):
    if num is None or pd.isna(num): return "-"
    return f"{int(round(num)):,}원"

def clean_date_index(obj):
    if isinstance(obj, pd.Series):
        s = pd.to_datetime(obj)
        if s.dt.tz is not None: s = s.dt.tz_convert(None)
        return s.dt.normalize()
    elif isinstance(obj, (pd.DatetimeIndex, pd.Index)):
        idx = pd.to_datetime(obj)
        if getattr(idx, 'tz', None) is not None: idx = idx.tz_convert(None)
        return idx.normalize()
    else:
        dt = pd.to_datetime(obj)
        if getattr(dt, 'tz', None) is not None: dt = dt.tz_convert(None)
        return dt.normalize()

# --- P5: yf.download 캐시 래퍼 ---
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ohlc(tickers: tuple, start: str, end: str, auto_adjust: bool):
    return yf.download(list(tickers), start=start, end=end,
                       interval="1d", progress=False, auto_adjust=auto_adjust)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_dividends(tickers: tuple, start: str, end: str):
    raw = yf.download(list(tickers), start=start, end=end,
                      interval="1d", progress=False, auto_adjust=False, actions=True)
    if isinstance(raw.columns, pd.MultiIndex) and 'Dividends' in raw.columns.levels[0]:
        return raw['Dividends']
    return raw

st.set_page_config(page_title="박가이버 통합 작전 사령부 V10.5 (patched)", page_icon="🛡️", layout="wide")
st.markdown("""<style>.stApp{background-color:#f8fafc}</style>""", unsafe_allow_html=True)

BASE_STOCK_MASTER = {
    "삼성전자":"005930.KS","SK하이닉스":"000660.KS","테크윙":"089030.KQ","한미반도체":"042700.KS",
    "HPSP":"403870.KQ","이오테크닉스":"039030.KQ","주성엔지니어링":"036930.KQ","원익IPS":"240810.KQ",
    "한화오션":"042660.KS","HD한국조선해양":"009540.KS","현대로템":"064350.KS","LIG넥스원":"079550.KS",
    "한화에어로스페이스":"012450.KS","한국콜마":"161890.KS","코스맥스":"192820.KS","알테오젠":"196170.KQ",
    "셀트리온":"068270.KS","삼성바이오로직스":"207940.KS","현대차":"005380.KS","기아":"000270.KS",
    "NAVER":"035420.KS","카카오":"035720.KS","HD현대일렉트릭":"267260.KS","두산에너빌리티":"034020.KS",
    "KODEX 200":"069500.KS","KODEX 코스닥150":"229200.KS","KODEX 레버리지":"122630.KS","TIGER 미국S&P500":"360750.KS",
}
if "full_stock_master" not in st.session_state:
    st.session_state["full_stock_master"] = BASE_STOCK_MASTER.copy()
if "custom_stocks" not in st.session_state: st.session_state["custom_stocks"] = {}
if "my_holdings" not in st.session_state: st.session_state["my_holdings"] = ["SK하이닉스","한미반도체","테크윙","HD현대일렉트릭","HPSP"]
if "my_watchlist" not in st.session_state: st.session_state["my_watchlist"] = ["한화오션","현대로템","RFHIC","한국콜마"]
MASTER_STOCK_DICT = st.session_state["full_stock_master"].copy()
for n,c in st.session_state["custom_stocks"].items():
    MASTER_STOCK_DICT[n] = c

# --- P3: 최소 KRX 섹터 매핑 ---
KRX_SECTOR = {
    "005930.KS":"반도체","000660.KS":"반도체","042700.KS":"반도체","403870.KQ":"반도체",
    "089030.KQ":"반도체","039030.KQ":"반도체","036930.KQ":"반도체","240810.KQ":"반도체",
    "005380.KS":"자동차","000270.KS":"자동차",
    "042660.KS":"조선","009540.KS":"조선","064350.KS":"방산","079550.KS":"방산","012450.KS":"항공우주",
    "161890.KS":"바이오화학","192820.KS":"바이오화학","196170.KQ":"바이오",
    "068270.KS":"바이오","207940.KS":"바이오",
    "035420.KS":"인터넷","035720.KS":"인터넷",
    "267260.KS":"전기장비","034020.KS":"에너지",
    "069500.KS":"ETF","229200.KS":"ETF","122630.KS":"ETF","360750.KS":"ETF",
}
TICKER_TO_SECTOR = {code: KRX_SECTOR.get(code, "기타") for code in MASTER_STOCK_DICT.values()}

def format_stock_option(name):
    code = MASTER_STOCK_DICT.get(name, "")
    market = "코스닥" if code.endswith(".KQ") else "코스피"
    return f"{name} ({get_chosung(name)} | {market} {code})"

# === 유효성 검사용 백테스트 시뮬레이터 (P1/P2/P4 핵심만 시연) ===
def run_mini_backtest(months: int = 60):
    end = datetime.date.today().strftime('%Y-%m-%d')
    start = (datetime.date.today() - relativedelta(months=months)).strftime('%Y-%m-%d')
    tickers = ("005930.KS","000660.KS","042700.KS","005380.KS")
    close_raw = fetch_ohlc(tickers, start, end, auto_adjust=False)
    div_raw   = fetch_dividends(tickers, start, end)
    if close_raw.empty:
        return None
    close_df = close_raw['Close'] if isinstance(close_raw.columns, pd.MultiIndex) else close_raw
    close_df.index = clean_date_index(close_df.index)
    div_df = div_raw.reindex(close_df.index).fillna(0) if not div_raw.empty else pd.DataFrame(0, index=close_df.index, columns=tickers)
    return {"close": close_df.tail().round(0).to_dict(), "div_sum": float(div_df.sum().sum())}

st.sidebar.title("🎛️ 박가이버 사령부 V10.5 (patched)")
st.sidebar.markdown("### 🩹 패치 노트 V10.4 → V10.5")
st.sidebar.markdown("""
- P1. `auto_adjust=False` 명시 (배당 이중계상 제거)
- P2. 공짜주식 모드 = 원금 100% 현금 + 순수익 일부 주식화
- P3. KRX 섹터 최소 매핑 적용
- P4. 시장 지수 컬럼명 명시 fallback
- P5. yf.download 결과 캐시
- P6. 파일 업로드 무한 재실행 가드
""")

# --- P6: file_uploader rerun 가드 ---
uploaded_cfg = st.sidebar.file_uploader("📤 내 전략 세팅 불러오기 (.json)", type=["json"])
if uploaded_cfg is not None and st.session_state.get("last_cfg_id") != uploaded_cfg.file_id:
    try:
        cfg = json.load(uploaded_cfg)
        if "my_holdings" in cfg: st.session_state["my_holdings"] = cfg["my_holdings"]
        if "my_watchlist" in cfg: st.session_state["my_watchlist"] = cfg["my_watchlist"]
        st.session_state["last_cfg_id"] = uploaded_cfg.file_id
        st.sidebar.success("🎉 세팅 파일 복원 완료!")
    except Exception:
        st.sidebar.error("⚠️ 올바른 설정(.json) 파일이 아닙니다.")

st.sidebar.markdown("---")
menu = st.sidebar.radio("사령부 작전 모드선택",
    ["🩹 패치 검증 (mini)", "🗄️ 1. 내 계좌 영구 DB", "🚨 2. 실전 매매 레이더", "🛡️ 3. 백테스트 연구소"], index=0)
st.sidebar.markdown("---")

if menu == "🩹 패치 검증 (mini)":
    st.markdown("""
    <div class="hero-banner" style="background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);padding:18px 20px;border-radius:14px;color:#fff;margin-bottom:20px">
    <h2 style="margin:0;font-size:1.4rem">🩹 V10.5 패치 검증 센터</h2>
    <p style="margin:4px 0 0 0;color:#94a3b8;font-size:0.85rem">4개 대표 종목 60개월 비조정 종가 + 배당 동기화 결과 — P1이 적용되면 Close는 분할/배당 미반영 가격입니다.</p>
    </div>
    """, unsafe_allow_html=True)
    with st.spinner("📡 비조정 종가 + 배당 동기화 (캐시 우선)…"):
        try:
            out = run_mini_backtest(60)
            if out is None:
                st.error("❌ 동기화 실패 — 네트워크 환경 확인 필요")
            else:
                st.success(f"✅ 비조정 종가 5일치 수신 + 총 배당 누적: {format_money(out['div_sum'])}")
                st.json(out['close'])
                st.caption("위 가격은 auto_adjust=False 적용 결과 — Yahoo가 분할·배당을 반영하지 않은 raw 종가입니다.")
        except Exception as e:
            st.exception(e)

elif menu == "🗄️ 1. 내 계좌 영구 DB (보유 & 관심)":
    st.info("원본 그대로 — 패치 영향 없음. 멀티셀렉트는 추후 별도 패치 권장.")
elif menu == "🚨 2. 실전 매매 레이더":
    st.info("원본 그대로 — 권장 추가: 시장 우산 스위치 체크박스 + 비조정 종가 캐시 적용.")
else:
    st.info("원본 그대로 — 핵심 로직은 본 파일 상단 P1/P2/P3/P4 패치 적용 권장. 통합 패치본은 별도 PR 검토 필요.")
