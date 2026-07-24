import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
from dateutil.relativedelta import relativedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 페이지 웹 디자인 세팅 (최고급 프리미엄 UX/UI CSS) ---
st.set_page_config(page_title="박가이버 통합 작전 사령부 V8 Ultra Pro", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .stApp {
        background-color: #f8fafc;
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%) !important;
        padding: 16px 20px !important;
        border-radius: 14px !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
        transition: transform 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08) !important;
    }
    div[data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] * {
        color: #475569 !important;
        font-size: 0.88rem !important;
        font-weight: 800 !important;
    }
    div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] * {
        color: #0f172a !important;
        font-size: 1.4rem !important;
        font-weight: 900 !important;
    }
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 24px 28px;
        border-radius: 16px;
        color: #ffffff;
        border-left: 8px solid #38bdf8;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25);
        margin-bottom: 25px;
    }
    .hero-title {
        font-size: 1.8rem;
        font-weight: 900;
        margin: 0;
        color: #f8fafc;
    }
    .hero-subtitle {
        font-size: 0.95rem;
        color: #94a3b8;
        margin-top: 6px;
    }
    .ai-advice-card {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
        color: #ffffff;
        padding: 22px 26px;
        border-radius: 16px;
        box-shadow: 0 8px 20px rgba(2, 132, 199, 0.25);
        margin-bottom: 25px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 동적 데이터베이스 및 종목 마스터 세션 초기화 ---
if "sector_db" not in st.session_state:
    st.session_state["sector_db"] = {
        "⚡ 반도체 & HBM / 칩렛": {
            "테크윙": "089030.KQ", "한미반도체": "042700.KS", "HPSP": "403870.KQ",
            "이오테크닉스": "039030.KQ", "리노공업": "058470.KQ", "ISC": "095340.KQ",
            "주성엔지니어링": "036930.KQ", "원익IPS": "240810.KQ", "삼성전자": "005930.KS", "SK하이닉스": "000660.KS"
        },
        "🧬 바이오 & 제약 / 화장품": {
            "한국콜마": "161890.KS", "코스맥스": "192820.KS", "알테오젠": "196170.KQ", 
            "셀트리온": "068270.KS", "삼성바이오로직스": "207940.KS", "HLB": "028300.KQ", 
            "유한양행": "000100.KS", "리가켐바이오": "141080.KQ"
        },
        "📡 통신 & 방산 & 조선": {
            "RFHIC": "218410.KQ", "한화시스템": "272210.KS", "현대로템": "064350.KS",
            "LIG넥스원": "079550.KS", "한화오션": "042660.KS", "HD한국조선해양": "009540.KS"
        },
        "🔋 2차전지 & 에코": {
            "에코프로비엠": "247540.KQ", "에코프로": "086520.KQ", "LG에너지솔루션": "373220.KS",
            "POSCO홀딩스": "005490.KS", "엘앤에프": "066970.KQ"
        },
        "🚗 자동차 & 대표 제조": {
            "현대차": "005380.KS", "기아": "000270.KS", "현대모비스": "012330.KS"
        },
        "💻 IT & 플랫폼": {
            "NAVER": "035420.KS", "카카오": "035720.KS"
        }
    }

if "custom_stocks" not in st.session_state:
    st.session_state["custom_stocks"] = {}

KOREAN_STOCK_MASTER = {
    "한국콜마": "161890.KS", "RFHIC": "218410.KQ", "코스맥스": "192820.KS",
    "현대힘스": "460930.KQ", "한화오션": "042660.KS", "HD한국조선해양": "009540.KS",
    "에스피지": "058610.KQ", "SPG": "058610.KQ", "레인보우로보틱스": "277810.KQ",
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "테크윙": "089030.KQ", 
    "한미반도체": "042700.KS", "기가비스": "420770.KQ", "케이씨텍": "281820.KS",
    "이수화학": "005950.KS", "이수스페셜티케미컬": "457190.KS", "마녀공장": "439090.KQ",
    "뉴파워프라즈마": "144960.KQ", "두산에너빌리티": "034020.KS", "하나마이크론": "084370.KQ",
    "동진쎄미켐": "033640.KQ", "솔브레인": "357780.KQ", "가온칩스": "399500.KQ",
    "두산로보틱스": "454910.KS", "한화에어로스페이스": "012450.KS", "LIG넥스원": "079550.KS",
    "HD현대일렉트릭": "267260.KS", "LS일렉트릭": "010120.KS", "포스코퓨처엠": "003670.KS"
}

MASTER_STOCK_DICT = {}
for sector, stocks in st.session_state["sector_db"].items():
    for name, code in stocks.items():
        MASTER_STOCK_DICT[name] = code
for name, code in KOREAN_STOCK_MASTER.items():
    if name not in MASTER_STOCK_DICT:
        MASTER_STOCK_DICT[name] = code
for name, code in st.session_state["custom_stocks"].items():
    MASTER_STOCK_DICT[name] = code

if "selected_stocks" not in st.session_state:
    st.session_state["selected_stocks"] = ["한국콜마", "RFHIC", "테크윙", "한미반도체", "HPSP"]

def format_money(num):
    if num is None or pd.isna(num):
        return "-"
    num = round(num)
    abs_num = abs(num)
    sign = "-" if num < 0 else ""
    
    if abs_num >= 100000000:
        eok = abs_num // 100000000
        man = (abs_num % 100000000) // 10000
        if man > 0:
            return f"{sign}{eok:,}억 {man:,}만 원"
        return f"{sign}{eok:,}억 원"
    elif abs_num >= 10000:
        man = abs_num / 10000
        if man >= 100:
            if man == int(man):
                return f"{sign}{int(man):,}만 원"
            return f"{sign}{man:,.1f}만 원"
        else:
            if man == int(man):
                return f"{sign}{int(man):,}만 원"
            return f"{sign}{man:,.1f}만 원"
    else:
        return f"{sign}{abs_num:,}원"

@st.cache_data(ttl=3600)
def analyze_stock_suitability(stock_dict, invest_amount=2000000):
    results = []
    tickers = list(stock_dict.values())
    if not tickers:
        return pd.DataFrame()

    try:
        data = yf.download(tickers, period="1y", progress=False)['Close']
        for name, code in stock_dict.items():
            if code in data.columns and len(data[code].dropna()) > 10:
                s_data = data[code].dropna()
                curr_price = float(s_data.iloc[-1])
                
                if curr_price > invest_amount:
                    total_score = 0
                    fit_grade = "🚫 출격 불가 (단가 초과)"
                    reason = f"1주 가격({format_money(curr_price)})이 진입 예산({format_money(invest_amount)})보다 비쌉니다!"
                    buyable_qty = 0
                else:
                    buyable_qty = int(invest_amount // curr_price)
                    daily_change = s_data.pct_change().abs() * 100
                    avg_volatility = daily_change.mean()
                    
                    sma200 = s_data.rolling(min(200, len(s_data))).mean().iloc[-1]
                    trend_score = 35 if curr_price >= sma200 else 20
                    
                    if 1.5 <= avg_volatility <= 4.0:
                        vol_score = 45
                    elif avg_volatility > 4.0:
                        vol_score = 30
                    else:
                        vol_score = 15
                        
                    total_score = vol_score + trend_score + 20
                    
                    if buyable_qty < 3:
                        total_score = max(30, total_score - 20)
                        fit_grade = "⚠️ 주의 (단가 부담)"
                        reason = f"1주 가격({format_money(curr_price)})이 높아 진입 시 {buyable_qty}주밖에 못 사 자금 효율이 낮습니다."
                    elif total_score >= 80:
                        fit_grade = "🥇 최적합 (강력 추천)"
                        reason = f"파동(±{avg_volatility:.1f}%)이 훌륭하며, 1회 진입 시 약 {buyable_qty}주씩 분할 매수 가능합니다."
                    elif total_score >= 65:
                        fit_grade = "🥈 적합 (무난)"
                        reason = f"스노우볼 작전에 무난하게 적합합니다. (진입 시 약 {buyable_qty}주 매수 가능)"
                    else:
                        fit_grade = "⚠️ 주의 (파동 부족/하락세)"
                        reason = f"변동폭이 너무 적거나 하락세가 지속되어 진입 타점이 더디게 올 수 있습니다."

                results.append({
                    "종목명": name,
                    "티커": code,
                    "현재가(1주)": format_money(curr_price),
                    "1회 진입 가능 수량": f"{buyable_qty}주",
                    "적합도 점수": f"{total_score}점",
                    "적합도 판정": fit_grade,
                    "사령관 정밀 진단 소견": reason
                })
    except Exception:
        pass

    return pd.DataFrame(results)

# --- 3. 사이드바 조종간 ---
st.sidebar.title("🎛️ 박가이버 사령부 V8 Pro")
menu_choice = st.sidebar.radio(
    "모드 선택",
    ["🔎 1. 작전 구역(섹터) 탐색기", "🛡️ 2. 실전 작전 통제실 (백테스트)"],
    index=1
)
st.sidebar.markdown("---")

# =====================================================================
# 🔎 모드 1: 작전 구역(섹터) 탐색기
# =====================================================================
if menu_choice == "🔎 1. 작전 구역(섹터) 탐색기":
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🔎 작전 구역 및 영구 종목 탐색기</div>
        <div class="hero-subtitle">종목 이름(예: 한국콜마, RFHIC) 또는 6자리 종목코드를 입력하시면 바구니에 100% 영구 등록됩니다.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🔍 1. 대한민국 전종목 스마트 등록 (이름 & 코드 겸용)")
    st.info("💡 종목명(예: **한국콜마**, **RFHIC**, **뉴파워프라즈마**)을 입력하시거나 6자리 숫자 코드를 입력해 바구니에 담으세요!")

    search_tab1, search_tab2 = st.tabs(["⚡ 스마트 종목/코드 직접 등록 (영구 저장)", "🔎 내장 장부에서 바로 고르기"])

    with search_tab1:
        c_col1, c_col2, c_col3, c_col4 = st.columns([2, 1.5, 1, 1])
        input_name = c_col1.text_input("종목명 입력", placeholder="예: 한국콜마, RFHIC", key="custom_name_input")
        input_code = c_col2.text_input("6자리 코드 (선택)", placeholder="예: 161890, 218410", key="custom_code_input")
        input_market = c_col3.selectbox("소속 시장", ["코스피 (.KS)", "코스닥 (.KQ)"], key="custom_market_select")
        
        if c_col4.button("➕ 바구니에 담기", type="primary", key="btn_add_custom_stock"):
            name_q = input_name.strip()
            code_q = input_code.strip()
            
            resolved_name = None
            resolved_code = None

            if name_q in MASTER_STOCK_DICT:
                resolved_name = name_q
                resolved_code = MASTER_STOCK_DICT[name_q]
            elif name_q in KOREAN_STOCK_MASTER:
                resolved_name = name_q
                resolved_code = KOREAN_STOCK_MASTER[name_q]
            elif len(code_q) == 6 and code_q.isdigit():
                suffix = ".KS" if "코스피" in input_market else ".KQ"
                resolved_code = f"{code_q}{suffix}"
                resolved_name = name_q if name_q else f"신규작전주({code_q})"
            elif len(name_q) == 6 and name_q.isdigit():
                suffix = ".KS" if "코스피" in input_market else ".KQ"
                resolved_code = f"{name_q}{suffix}"
                resolved_name = f"신규작전주({name_q})"

            if resolved_name and resolved_code:
                st.session_state["custom_stocks"][resolved_name] = resolved_code
                MASTER_STOCK_DICT[resolved_name] = resolved_code
                
                if resolved_name not in st.session_state["selected_stocks"]:
                    st.session_state["selected_stocks"].append(resolved_name)
                st.success(f"🎉 [{resolved_name} ({resolved_code})] 종목이 바구니에 완벽하게 추가되었습니다!")
                st.rerun()
            else:
                st.error("⚠️ 사전에서 종목명을 찾지 못했습니다. 종목명과 함께 **'6자리 숫자 코드(예: 161890)'**를 정확히 작성해 주세요!")

    with search_tab2:
        all_stock_names = sorted(list(MASTER_STOCK_DICT.keys()))
        selected_from_dropdown = st.selectbox(
            "사령부에 내장된 종목 이름 중에서 고르세요:",
            options=[""] + all_stock_names,
            key="dropdown_stock_select_final"
        )
        if st.button("🛒 선택 종목 [백테스트 바구니] 추가", type="secondary", key="btn_dropdown_add_final"):
            if selected_from_dropdown and selected_from_dropdown in MASTER_STOCK_DICT:
                code = MASTER_STOCK_DICT[selected_from_dropdown]
                if selected_from_dropdown not in st.session_state["selected_stocks"]:
                    st.session_state["selected_stocks"].append(selected_from_dropdown)
                    st.success(f"🎉 [{selected_from_dropdown} ({code})] 종목이 바구니에 성공적으로 담겼습니다!")
                    st.rerun()
                else:
                    st.info(f"💡 '{selected_from_dropdown}' 종목은 이미 바구니에 담겨 있습니다.")

    st.markdown("---")

    st.markdown("### 🎯 2. 테마/섹터별 둘러보기")
    col_sec1, col_sec2 = st.columns([1, 2])
    with col_sec1:
        selected_sector = st.selectbox("📂 탐색할 섹터 선택", list(st.session_state["sector_db"].keys()))
    
    sector_stocks_dict = st.session_state["sector_db"][selected_sector]
    
    with col_sec2:
        st.write(f"▼ **[{selected_sector}] 주요 감시 종목 목록**")
        sector_target_list = st.multiselect(
            "바구니로 전송할 종목 선택:",
            options=list(sector_stocks_dict.keys()),
            default=list(sector_stocks_dict.keys()),
            key=f"sec_select_{selected_sector}"
        )
        
        if st.button(f"🛒 선택 종목 [백테스트 바구니] 추가", type="secondary"):
            added_count = 0
            for s_name in sector_target_list:
                if s_name not in st.session_state["selected_stocks"]:
                    st.session_state["selected_stocks"].append(s_name)
                    added_count += 1
            st.toast(f"🎉 {added_count}개 종목이 바구니에 담겼습니다!")

    st.markdown("---")

    st.markdown("### 🛒 3. 작전 통제실로 전송할 종목 바구니 담기")

    valid_selected_stocks = [s for s in st.session_state["selected_stocks"] if s in MASTER_STOCK_DICT]
    
    st.session_state["selected_stocks"] = st.multiselect(
        "백테스트 검증을 진행할 종목들을 선택해 주세요 (1개~10개 권장):",
        options=list(MASTER_STOCK_DICT.keys()),
        default=valid_selected_stocks
    )

    if st.session_state["selected_stocks"]:
        st.markdown("---")
        st.markdown("#### 💡 자금별 1회 진입금액 최적 추천 가이드")
        
        total_budget_input = st.number_input("🏦 내 총 작전 예산(원)을 입력하세요", value=10000000, step=1000000, key="rec_total_budget")
        
        rec_std = total_budget_input // 5      # 표준 (5슬롯)
        rec_aggr = total_budget_input // 3     # 공격 (3슬롯)
        rec_def = total_budget_input // 8      # 방어 (8슬롯)

        r_col1, r_col2, r_col3 = st.columns(3)
        r_col1.metric("🎯 표준 권장 (5슬롯 균형)", format_money(rec_std), delta="총 예산의 20%")
        r_col2.metric("⚡ 적극 공격 (3슬롯 회전)", format_money(rec_aggr), delta="총 예산의 33%")
        r_col3.metric("🛡️ 철벽 방어 (8슬롯 연금)", format_money(rec_def), delta="총 예산의 12.5%")

        st.markdown("---")
        st.markdown("#### 🎯 바구니 종목 작전 적합도 & 단가 검진 리포트")
        
        diag_invest_amount = rec_std

        basket_dict = {name: MASTER_STOCK_DICT[name] for name in st.session_state["selected_stocks"] if name in MASTER_STOCK_DICT}
        
        with st.spinner("📡 종목별 1주 단가, 자금 비율 및 파동 적합도를 검진 중..."):
            suitability_df = analyze_stock_suitability(basket_dict, diag_invest_amount)
            
        if not suitability_df.empty:
            st.dataframe(suitability_df, use_container_width=True, hide_index=True)
        else:
            st.info("💡 종목 정보를 불러오는 중입니다.")

        st.markdown("---")
        if st.button("🚀 선택한 종목들을 [작전 통제실]로 즉시 전송!", type="primary"):
            st.success(f"🎉 총 {len(st.session_state['selected_stocks'])}개 종목 설정 완료!")
            st.info("👈 왼쪽 사이드바 메뉴에서 [🛡️ 2. 실전 작전 통제실]을 누르세요!")

# =====================================================================
# 🛡️ 모드 2: 실전 작전 통제실 (백테스트 대시보드 V8 Ultra Pro)
# =====================================================================
else:
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🛡️ 박가이버표 실전 작전 통제실 V8 Ultra</div>
        <div class="hero-subtitle">월가 퀀트 스타일의 2단 연동 차트, 폭락장 우산 알고리즘, MDD 멘탈 분석 및 AI 실시간 장세 자금 조언 가이드입니다.</div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.subheader("⚙️ 빠른 전략 프리셋")
    preset_col1, preset_col2 = st.sidebar.columns(2)
    buy_preset, sell_preset = 5, 5
    if preset_col1.button("⚡ 적극 공격형"):
        buy_preset, sell_preset = 3, 7
        st.sidebar.info("적극 공격형 (-3% 진입 / +7% 익절) 설정 완료!")
    if preset_col2.button("🛡️ 안정 스노우볼"):
        buy_preset, sell_preset = 5, 5
        st.sidebar.info("안정 스노우볼 (-5% 진입 / +5% 익절) 설정 완료!")

    st.sidebar.subheader("🛡️ 스마트 방어 스위치")
    use_market_filter = st.sidebar.checkbox("🌤️ 대세 하락장 자동 우산 스위치", value=True, help="주가가 200일 이평선 아래인 하락장에서는 진입 기준을 1.4배 깊게 잡아 손절을 줄입니다.")

    st.sidebar.subheader("🎯 감시 작전 구역 선택")
    valid_watch_stocks = [s for s in st.session_state["selected_stocks"] if s in MASTER_STOCK_DICT]
    
    selected_stock_names = st.sidebar.multiselect(
        "감시 종목 리스트",
        options=list(MASTER_STOCK_DICT.keys()),
        default=valid_watch_stocks
    )

    PORTFOLIO_UNIVERSE = {s_name: MASTER_STOCK_DICT[s_name] for s_name in selected_stock_names if s_name in MASTER_STOCK_DICT}

    st.sidebar.markdown("---")
    total_capital_input = st.sidebar.number_input("🏦 총 작전 예산(원)", value=10000000, step=1000000)
    
    rec_default_invest = total_capital_input // 5
    st.sidebar.caption(f"💡 권장 1회 진입금 (5슬롯 표준): **{format_money(rec_default_invest)}**")
    invest_amount_input = st.sidebar.number_input("💰 회당 초기 진입금액(원)", value=int(rec_default_invest), step=500000)
    
    max_active_slots = max(1, int(total_capital_input // invest_amount_input))
    st.sidebar.info(f"💡 동원 가능 요원 슬롯: **{max_active_slots}개**")

    use_compounding = st.sidebar.checkbox("🚀 복리 스케일업 모드", value=True)
    time_unit = st.sidebar.radio("🗓️ 기간 단위", ["월 단위 (개월)", "년 단위 (년)"], horizontal=True)

    if time_unit == "월 단위 (개월)":
        months_input = st.sidebar.slider("백테스트 기간(개월)", 1, 120, 60, 1)
        period_label = f"{months_input}개월"
    else:
        years_val = st.sidebar.slider("백테스트 기간(년)", 1, 10, 5, 1)
        months_input = years_val * 12
        period_label = f"{years_val}년"

    buy_cond_input = st.sidebar.slider("🛒 진입 기준 (-% 하락 시)", 1, 20, buy_preset, 1)
    sell_target_input = st.sidebar.slider("🎯 익절 목표 (+%)", 1, 30, sell_preset, 1)
    stop_loss_input = st.sidebar.slider("🚨 손절 기준 (-%)", 0, 50, 15, 5)

    st.sidebar.subheader("💸 거래비용 적용")
    use_fee = st.sidebar.checkbox("수수료/거래세 반영", value=True)
    broker_fee_pct = (st.sidebar.number_input("위탁수수료 (%)", value=0.015, format="%.3f") / 100) if use_fee else 0.0
    tax_pct = (st.sidebar.number_input("매도 거래세 (%)", value=0.18, format="%.2f") / 100) if use_fee else 0.0

    reward_type = st.sidebar.selectbox(
        "🎁 전리품 수령 방식", 
        ["전액 현금으로 챙기기", "열매로 결실 모으기", "🌟 현금 50% + 열매 50% (하이브리드)"]
    )
    
    run_btn = st.sidebar.button("🚀 1,000만 원 작전 검증 개시!", type="primary")

    # 🚨 실시간 터미널 시그널 알림판
    st.markdown("### 🚨 오늘의 실전 출격 명령서 (실시간 레이더 터미널)")
    if len(PORTFOLIO_UNIVERSE) > 0:
        try:
            live_tickers = list(PORTFOLIO_UNIVERSE.values())
            live_data = yf.download(live_tickers, period="5d", progress=False)['Close']
            
            buy_signals = []
            for name, code in PORTFOLIO_UNIVERSE.items():
                if code in live_data.columns and len(live_data[code].dropna()) >= 2:
                    prices = live_data[code].dropna()
                    today_p = float(prices.iloc[-1])
                    yester_p = float(prices.iloc[-2])
                    change_pct = ((today_p - yester_p) / yester_p) * 100
                    
                    if change_pct <= -float(buy_cond_input):
                        buy_signals.append(f"🛒 **[{name}]** 당일 변동률: **{change_pct:.2f}%** (진입 타점 포착! 내일 아침 실전 출격 시그널)")
            
            if buy_signals:
                st.error("⚡ **오늘 실전 진입 타점에 포착된 종목이 있습니다!**\n\n" + "\n\n".join(buy_signals))
            else:
                st.success("✅ **현재 감시 구역 내 당일 급락 종목이 없습니다.** 사령부 요원들은 출격 대기 상태를 유지합니다.")
        except Exception:
            st.info("💡 실시간 시세를 동기화하는 중입니다.")

    st.markdown("---")
    st.write(f"### 🛡️ 감시 구역 요약 ({len(PORTFOLIO_UNIVERSE)}개 종목)")
    universe_list = []
    for name, code in PORTFOLIO_UNIVERSE.items():
        market_type = "코스닥" if ".KQ" in code else ("코스피" if ".KS" in code else "기타")
        universe_list.append({"구역명": name, "티커": code.split('.')[0], "시장": market_type, "상태": "실시간 감시 중"})
    st.dataframe(pd.DataFrame(universe_list), use_container_width=True, hide_index=True)
    st.markdown("---")

    if run_btn:
        if len(PORTFOLIO_UNIVERSE) == 0:
            st.error("❌ 선택된 종목이 없습니다. 1개 이상 선택해 주세요.")
        else:
            with st.spinner("📡 슈퍼컴퓨터가 과거 파동, 배당금 및 MDD 데이터를 퀀트 분석 중입니다..."):
                try:
                    end_date = datetime.datetime.today()
                    start_date = end_date - relativedelta(months=months_input)
                    tickers = list(PORTFOLIO_UNIVERSE.values())
                    
                    raw_df = yf.download(tickers, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), actions=True, progress=False)

                    if isinstance(raw_df.columns, pd.MultiIndex):
                        close_df = raw_df['Close']
                        div_df = raw_df['Dividends'] if 'Dividends' in raw_df.columns.levels[0] else pd.DataFrame(index=raw_df.index, columns=tickers).fillna(0)
                    else:
                        close_df = pd.DataFrame({tickers[0]: raw_df['Close']})
                        div_df = pd.DataFrame({tickers[0]: raw_df['Dividends']}) if 'Dividends' in raw_df.columns else pd.DataFrame({tickers[0]: 0}, index=raw_df.index)

                    return_df = close_df.pct_change() * 100
                    sma200_df = close_df.rolling(window=200).mean()

                    buy_cond = -float(buy_cond_input)
                    sell_target = float(sell_target_input)
                    stop_loss_limit = -float(stop_loss_input) if stop_loss_input > 0 else None

                    current_cash = float(total_capital_input)
                    active_positions, trade_logs, daily_returns_history, asset_history = [], [], [], []
                    agent_counter = 0

                    yearly_stats = {}
                    free_shares_dict = {s_name: 0 for s_name in PORTFOLIO_UNIVERSE.keys()}
                    stock_win_stats = {s_name: {'success': 0, 'stop': 0, 'profit_gain': 0, 'loss_cost': 0} for s_name in PORTFOLIO_UNIVERSE.keys()}

                    total_success, total_stop_loss, total_cash_profit, total_fee_tax_paid = 0, 0, 0, 0
                    global_max_deployed = 0
                    daily_deployment_snapshots = []
                    missed_opportunities = []
                    total_dividend_profit = 0

                    peak_asset_value = float(total_capital_input)
                    max_drawdown_pct = 0.0

                    for date, row in close_df.iterrows():
                        date_str = date.strftime('%Y-%m-%d')
                        year = date.year
                        if year not in yearly_stats:
                            yearly_stats[year] = {'success': 0, 'stop': 0, 'shares': 0, 'cash': 0, 'share_val': 0.0}
                        
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
                                '진입금액': '-', '매도금액': '-', '진입단가': '-', '복귀일': date_str,
                                '청산단가': '-', '순수익률': '-',
                                '정산내역': f"🍯 꿀 수입: +{format_money(daily_dividend_sum)}", '구분': '🌟 특별 보너스'
                            })
                        
                        survived_positions = []
                        for pos in active_positions:
                            t_code = pos['ticker']
                            if t_code in row and not pd.isna(row[t_code]):
                                curr_price = float(row[t_code])
                                gross_ret = ((curr_price - pos['entry_price']) / pos['entry_price']) * 100
                                is_exit, exit_reason = False, ""

                                if gross_ret >= sell_target:
                                    is_exit, exit_reason = True, f"🎯 정상 복귀(+{sell_target_input}%)"
                                elif stop_loss_limit is not None and gross_ret <= stop_loss_limit:
                                    is_exit, exit_reason = True, f"🚨 강제 철수(-{stop_loss_input}%)"

                                if is_exit:
                                    sell_gross_val = pos['invest_amount'] * (curr_price / pos['entry_price'])
                                    buy_fee = pos['invest_amount'] * broker_fee_pct
                                    sell_fee = sell_gross_val * broker_fee_pct
                                    sell_tax = sell_gross_val * tax_pct
                                    total_trade_cost = buy_fee + sell_fee + sell_tax
                                    total_fee_tax_paid += total_trade_cost

                                    net_profit = (sell_gross_val - pos['invest_amount']) - total_trade_cost
                                    net_ret = (net_profit / pos['invest_amount']) * 100
                                    s_name = pos['stock_name']
                                    
                                    if gross_ret >= sell_target:
                                        total_success += 1
                                        yearly_stats[year]['success'] += 1
                                        stock_win_stats[s_name]['success'] += 1
                                        stock_win_stats[s_name]['profit_gain'] += net_profit
                                        
                                        if reward_type == '열매로 결실 모으기':
                                            buyable = int(max(0, net_profit) // curr_price)
                                            leftover = net_profit - (buyable * curr_price)
                                        elif reward_type == '🌟 현금 50% + 열매 50% (하이브리드)':
                                            share_budget = max(0, net_profit) / 2
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
                                    daily_returns_history.append(net_ret)

                                    log_reward = f"열매 {buyable}개 + 잔돈 {format_money(leftover)}" if buyable > 0 else format_money(leftover)
                                    trade_logs.append({
                                        '요원': pos['name'], '작전 구역': pos['stock_name'], '출격일': pos['entry_date'],
                                        '진입금액': format_money(pos['invest_amount']),
                                        '매도금액': format_money(sell_gross_val),
                                        '진입단가': format_money(pos['entry_price']), '복귀일': date_str,
                                        '청산단가': format_money(curr_price), '순수익률': f"{net_ret:.2f}%",
                                        '정산내역': log_reward, '구분': exit_reason
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
                                    if use_market_filter and (t_code in sma200_df.columns) and date in sma200_df.index:
                                        sma_val = sma200_df.loc[date, t_code]
                                        curr_p = row[t_code]
                                        if pd.notna(sma_val) and pd.notna(curr_p) and curr_p < sma_val:
                                            target_buy_cond = buy_cond * 1.4

                                    if ret_val <= target_buy_cond:
                                        candidates.append((s_name, t_code, ret_val, float(row[t_code])))
                            candidates.sort(key=lambda x: x[2])

                            for cand in candidates:
                                actual_invest = min(dynamic_invest_amount, current_cash)
                                c_price = cand[3]
                                
                                if c_price > actual_invest:
                                    missed_opportunities.append({
                                        "발생 일자": date_str, "미출격 종목": cand[0], "당일 하락률": f"{cand[2]:.2f}%",
                                        "불가 사유": f"1주 가격({format_money(c_price)})이 진입 예산({format_money(actual_invest)})을 초과함"
                                    })
                                elif len(active_positions) >= max_active_slots:
                                    missed_opportunities.append({
                                        "발생 일자": date_str, "미출격 종목": cand[0], "당일 하락률": f"{cand[2]:.2f}%",
                                        "불가 사유": f"요원 슬롯 풀가동 ({max_active_slots}/{max_active_slots}개)"
                                    })
                                elif actual_invest < 500000 or current_cash < 500000:
                                    missed_opportunities.append({
                                        "발생 일자": date_str, "미출격 종목": cand[0], "당일 하락률": f"{cand[2]:.2f}%",
                                        "불가 사유": f"가용 현금 부족 ({format_money(current_cash)})"
                                    })
                                else:
                                    agent_counter += 1
                                    s_name, t_code, ret_val, c_price = cand
                                    current_cash -= actual_invest
                                    active_positions.append({
                                        'name': f"{agent_counter}호 요원", 'stock_name': s_name, 'ticker': t_code,
                                        'entry_price': c_price, 'entry_date': date_str, 'invest_amount': actual_invest
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

                        asset_history.append({"Date": date, "Total_Asset": today_total_asset, "Drawdown": current_drawdown})

                    last_row = close_df.iloc[-1]
                    active_eval_value = sum([p['invest_amount'] * (float(last_row[p['ticker']]) / p['entry_price']) for p in active_positions if p['ticker'] in last_row and not pd.isna(last_row[p['ticker']])])
                    total_free_shares_count = sum(free_shares_dict.values())
                    total_free_shares_value = sum([count * float(last_row[PORTFOLIO_UNIVERSE[s_name]]) for s_name, count in free_shares_dict.items() if count > 0 and PORTFOLIO_UNIVERSE[s_name] in last_row and not pd.isna(last_row[PORTFOLIO_UNIVERSE[s_name]])])

                    final_total_asset = current_cash + active_eval_value + total_free_shares_value
                    total_net_profit = final_total_asset - total_capital_input
                    total_return_pct = (total_net_profit / total_capital_input) * 100
                    total_trades = total_success + total_stop_loss
                    win_rate = (total_success / total_trades * 100) if total_trades > 0 else 0

                    # 🌟 [신규] 최근 20일 실시간 시장 변동성 및 추세 계산
                    recent_20d_df = close_df.iloc[-20:] if len(close_df) >= 20 else close_df
                    recent_volatility = recent_20d_df.pct_change().abs().mean().mean() * 100
                    
                    # 과거 백테스트 전체 변동성
                    hist_volatility = return_df.abs().mean().mean()

                    # 🤖 [제미니 AI 분석 엔진] 진입금 조언 메시지 생성
                    if recent_volatility > hist_volatility * 1.3:
                        ai_market_status = "🚨 최근 시장 변동성이 과거 평균 대비 급격히 확대된 '초고변동성/불안정 구간'입니다."
                        ai_action_advice = f"**[진입금 30% 축소 권고]** 기존 회당 진입금 **{format_money(invest_amount_input)}**에서 **{format_money(invest_amount_input * 0.7)}** 수준으로 낮추어 방어 현금을 대폭 확보하세요!"
                        ai_bg_color = "#dc2626" # Red
                    elif recent_volatility < hist_volatility * 0.8:
                        ai_market_status = "☀️ 최근 시장 변동성이 수평을 이루는 '잔잔한 박스권/안정 국면'입니다."
                        ai_action_advice = f"**[표준 진입금 유지]** 현재 진입금 **{format_money(invest_amount_input)}** (전체 자금의 {int(invest_amount_input/total_capital_input*100)}%) 수준으로 정상적인 복리 스노우볼 작전을 펼치기 최적입니다."
                        ai_bg_color = "#0284c7" # Blue
                    else:
                        ai_market_status = "🌤️ 최근 변동성이 과거 데이터 패턴과 평형을 유지하고 있습니다."
                        ai_action_advice = f"**[정상 전략 유지]** 지정하신 회당 진입금 **{format_money(invest_amount_input)}**을 유지하되, 하락장 우산 스위치를 켜두어 우발적 폭락을 방지하세요."
                        ai_bg_color = "#16a34a" # Green

                    st.markdown(f"""
                    <div style="background-color: {ai_bg_color}; color: #ffffff; padding: 22px 26px; border-radius: 16px; margin-bottom: 25px; box-shadow: 0 8px 20px rgba(0,0,0,0.15);">
                        <h3 style="margin-top:0; font-size: 1.35rem; color: #ffffff; display: flex; align-items: center; gap: 8px;">🤖 제미니 AI 참모의 실시간 장세 진단 & 실전 진입금 처방전</h3>
                        <p style="font-size: 1.05rem; margin-bottom: 8px; opacity: 0.95;"><b>1. 현재 장세 진단:</b> {ai_market_status}</p>
                        <p style="font-size: 1.1rem; margin-bottom: 0; background: rgba(0,0,0,0.2); padding: 12px 16px; border-radius: 10px;"><b>2. 실전 자금 조치 지침:</b> {ai_action_advice}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    st.subheader("🏆 백테스트 최종 성과 대시보드")

                    m1, m2, m3 = st.columns(3)
                    m1.metric("🏁 원금 예산", format_money(total_capital_input))
                    m2.metric(f"✨ {period_label} 후 총자산", format_money(final_total_asset))
                    m3.metric("📈 총 순수익금", format_money(total_net_profit), delta=f"{total_return_pct:.2f}%")
                    
                    st.write("") 
                    
                    m4, m5, m6 = st.columns(3)
                    m4.metric("🎯 작전 승률", f"{win_rate:.1f}%", delta=f"{total_trades}전 {total_success}승")
                    m5.metric("🌊 멘탈 방어 지수 (MDD)", f"{max_drawdown_pct:.1f}%", delta="최대 파도 높이")
                    m6.metric("🍯 누적 배당금 (보너스)", format_money(total_dividend_profit), delta="달콤한 배당 꿀")

                    monthly_pension = (final_total_asset * 0.04) / 12
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%); padding: 22px; border-radius: 14px; border-left: 6px solid #f59e0b; margin-top: 18px; margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.04);">
                        <h4 style="margin-top: 0; color: #b45309; font-size: 1.25rem;">🐣 은퇴자를 위한 '제2의 연금통장' 변환기</h4>
                        <p style="font-size: 1.05rem; color: #451a03; margin-bottom: 0; line-height: 1.6;">
                            달성한 총자산 <b>{format_money(final_total_asset)}</b>을 연 4% 배당 ETF에 재투자 시,<br>
                            원금 손실 없이 매월 <b>💰 {format_money(monthly_pension)}의 제2의 월급(연금)</b>을 평생 수령할 수 있습니다!
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

                    # 🎥 당귀다TV 전용 요약 카드뉴스
                    with st.expander("📸 [당귀다TV 전용] 럭셔리 방송용 요약 카드뉴스 (캡처/썸네일용)"):
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #ffffff; padding: 28px; border-radius: 18px; border: 2px solid #f59e0b; box-shadow: 0 12px 30px rgba(0,0,0,0.3);">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h3 style="color: #f59e0b; margin: 0; font-size: 1.5rem;">🎥 당귀다TV X 박가이버 사령부 V8</h3>
                                <span style="background: #2563eb; color: #fff; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: bold;">VERIFIED QUANT</span>
                            </div>
                            <p style="font-size: 1.05rem; color: #94a3b8; margin-top: 8px;"><b>주요 감시 종목:</b> {', '.join(list(PORTFOLIO_UNIVERSE.keys())[:5])} 등</p>
                            <hr style="border-color: #334155; margin: 15px 0;">
                            <div style="display: flex; justify-content: space-between; font-size: 1.1rem; line-height: 2.0;">
                                <div>
                                    • 초기 종잣돈: <b>{format_money(total_capital_input)}</b><br>
                                    • 최종 총자산: <b><span style="color: #4ade80; font-size: 1.3rem;">{format_money(final_total_asset)}</span></b><br>
                                    • 총 순수익률: <b><span style="color: #facc15; font-size: 1.2rem;">+{total_return_pct:.2f}%</span></b>
                                </div>
                                <div style="text-align: right;">
                                    • 작전 승률: <b>{win_rate:.1f}%</b> ({total_success}승 / {total_stop_loss}패)<br>
                                    • 최대 낙폭(MDD): <b>{max_drawdown_pct:.1f}%</b><br>
                                    • 예상 월 연금: <b><span style="color: #38bdf8;">💰 {format_money(monthly_pension)}/월</span></b>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("---")

                    tab1, tab2, tab3, tab4 = st.tabs([
                        "📊 1. 2단 연동 퀀트 차트 (자산 & MDD)", 
                        "🔍 2. 자금 회전율 & 미출격 진단", 
                        "📈 3. 종목/연도별 손익분석", 
                        "📜 4. 현장 대기요원 & 매매장부"
                    ])

                    with tab1:
                        st.write("### 📈 백테스트 기간 자산 성장 & MDD 파도 차트")
                        asset_df = pd.DataFrame(asset_history)
                        
                        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.7, 0.3], subplot_titles=(f"총자산 증식 추이 ({period_label})", "계좌 최대 낙폭 (MDD Underwater)"))

                        fig.add_trace(go.Scatter(x=asset_df['Date'], y=asset_df['Total_Asset'], mode='lines', name='총자산', line=dict(color='#2563eb', width=2.5), fill='tozeroy', fillcolor='rgba(37, 99, 235, 0.08)'), row=1, col=1)
                        fig.add_hline(y=total_capital_input, line_dash="dash", line_color="#ef4444", annotation_text="원금", row=1, col=1)

                        fig.add_trace(go.Scatter(x=asset_df['Date'], y=asset_df['Drawdown'], mode='lines', name='낙폭(MDD)', line=dict(color='#dc2626', width=1.5), fill='tozeroy', fillcolor='rgba(220, 38, 38, 0.15)'), row=2, col=1)

                        fig.update_layout(height=580, template="plotly_white", margin=dict(l=20, r=20, t=40, b=20), hovermode="x unified")
                        st.plotly_chart(fig, use_container_width=True)

                    with tab2:
                        st.write("### 🔍 회전율 & 미출격 타점 분석 리포트")
                        st.warning(f"📊 {period_label} 기간 중 역사적 절대 최고 동시 출격 수: **총 {global_max_deployed}개 종목** (전체 슬롯: {max_active_slots}개)")
                        
                        if daily_deployment_snapshots:
                            snap_df = pd.DataFrame(daily_deployment_snapshots)
                            peak_df = snap_df[snap_df['동시 출격 수'] == global_max_deployed].drop_duplicates(subset=['발생 일자'])
                            st.write("▼ **역대 최고 자금 몰림(피크) 발생 일자 및 출격 목록:**")
                            st.dataframe(peak_df, use_container_width=True, hide_index=True)

                        st.markdown("---")
                        st.write("### 🚫 현금/슬롯 부족 또는 단가 초과로 놓쳐버린 출격 타점 추적기")
                        if missed_opportunities:
                            st.error(f"🚨 지난 {period_label} 동안 하락 타점이 맞았으나, **현금/슬롯 부족 또는 단가 초과로 놓친 기회가 총 {len(missed_opportunities)}회** 발생했습니다!")
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
                                yearly_summary_list.append({
                                    "연도": str(y),
                                    "🎯 익절": f"{val['success']}회",
                                    "🚨 손절": f"{val['stop']}회",
                                    "📦 열매": f"{int(val['shares'])}주",
                                    "💎 열매 가치": format_money(val['share_val']),
                                    "💵 현금수익": format_money(val['cash'])
                                })
                            st.dataframe(pd.DataFrame(yearly_summary_list), use_container_width=True, hide_index=True)

                        st.markdown("---")
                        st.write("#### 🏆 종목별 작전 성과 순위표 (1위~최하위)")
                        
                        stock_temp_list = []
                        for s_name, stats in stock_win_stats.items():
                            s_total = stats['success'] + stats['stop']
                            s_win_rate = (stats['success'] / s_total * 100) if s_total > 0 else 0
                            
                            gained_shares = free_shares_dict.get(s_name, 0)
                            share_val = 0
                            if gained_shares > 0 and PORTFOLIO_UNIVERSE[s_name] in last_row and not pd.isna(last_row[PORTFOLIO_UNIVERSE[s_name]]):
                                share_val = gained_shares * float(last_row[PORTFOLIO_UNIVERSE[s_name]])

                            net_profit_sum = stats['profit_gain'] + stats['loss_cost']
                            total_value_created = net_profit_sum + share_val

                            stock_temp_list.append({
                                "name": s_name,
                                "total_trades": s_total,
                                "win_rate": s_win_rate,
                                "profit_gain": stats['profit_gain'],
                                "loss_cost": stats['loss_cost'],
                                "net_profit": net_profit_sum,
                                "gained_shares": gained_shares,
                                "share_val": share_val,
                                "total_value_created": total_value_created,
                                "success_cnt": stats['success'],
                                "stop_cnt": stats['stop']
                            })

                        stock_temp_list.sort(key=lambda x: x['total_value_created'], reverse=True)

                        stock_summary = []
                        underperformers = []

                        for idx, item in enumerate(stock_temp_list):
                            rank_num = idx + 1
                            if rank_num == 1: rank_badge = "🥇 1위"
                            elif rank_num == 2: rank_badge = "🥈 2위"
                            elif rank_num == 3: rank_badge = "🥉 3위"
                            else: rank_badge = f"🏅 {rank_num}위"

                            stock_summary.append({
                                "순위": rank_badge,
                                "작전 구역": item['name'],
                                "총작전": f"{item['total_trades']}회",
                                "승률": f"{item['win_rate']:.1f}%",
                                "🎯 익절금": format_money(item['profit_gain']),
                                "🚨 손절금": format_money(item['loss_cost']),
                                "✨ 순손익": format_money(item['net_profit']),
                                "📦 획득 열매": f"{item['gained_shares']}주",
                                "💎 열매 가치": format_money(item['share_val'])
                            })

                            if item['net_profit'] < 0 or item['win_rate'] < 55:
                                underperformers.append(item)

                        st.dataframe(pd.DataFrame(stock_summary), use_container_width=True, hide_index=True)

                        if underperformers:
                            st.markdown("---")
                            st.write("#### 📉 성적 저조 종목 정밀 원인 분석 및 사령관 처방전")

                            for u in underperformers:
                                name = u['name']
                                w_rate = u['win_rate']
                                net_p = u['net_profit']
                                stops = u['stop_cnt']
                                succs = u['success_cnt']

                                if w_rate < 50:
                                    cause = f"하향 하락 추세가 장기화되어 진입 후 목표가(+{sell_target_input}%) 도달 전 손절선(-{stop_loss_input}%)에 지속 저촉되었습니다."
                                    solution = f"진입 기준 하락폭(-%)을 현재(-{buy_cond_input}%)보다 더 깊게(-7%~-10%) 잡거나, 폭락장 우산 스위치를 켜두시는 것을 추천합니다."
                                elif net_p < 0:
                                    cause = f"익절 건수({succs}회) 대비 손절 발생 시({stops}회) 깎여나간 손실폭이 상대적으로 컸습니다."
                                    solution = f"익절 목표(+{sell_target_input}%)를 상향 조정하거나 손절폭(-{stop_loss_input}%)을 단단하게 죄어 손실을 줄이세요."
                                else:
                                    cause = f"전체 자산 성장에 대한 기여도가 다소 낮고 승률({w_rate:.1f}%)이 기대에 미치지 못했습니다."
                                    solution = f"해당 종목의 1회 진입금 비중을 낮추거나 주도주 섹터의 신규 종목으로 교체해 보세요."

                                st.error(f"""
                                ⚠️ **[{name}] 진단 리포트 (순손익: {format_money(net_p)} / 승률: {w_rate:.1f}% / 손절 {stops}회 발생)**
                                * **🔍 원인 분석:** {cause}
                                * **💡 사령관 처방:** {solution}
                                """)
                        else:
                            st.success("🎉 감시 종목 전체가 마이너스 없이 훌륭한 승률과 손익비를 기록했습니다!")

                    with tab4:
                        st.write("### ⚔️ 현재 현장 대기 요원 (평가 현황)")
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

                                active_table.append({
                                    '요원': p['name'], 
                                    '구역명': p['stock_name'], 
                                    '출격일': p['entry_date'],
                                    '출격 당시 주가': format_money(p['entry_price']),
                                    '진입금액': format_money(p['invest_amount']),
                                    '현재 평가금액': format_money(eval_val),
                                    '평가 손익': format_money(eval_profit),
                                    '현재수익률': f"{ret:.2f}%"
                                })

                            tot_ret_pct = (tot_prof / tot_inv * 100) if tot_inv > 0 else 0
                            ac1, ac2, ac3 = st.columns(3)
                            ac1.metric("💰 현장 투입 원금 합계", format_money(tot_inv))
                            ac2.metric("📊 현재 총 평가금액 합계", format_money(tot_eval), delta=f"{tot_ret_pct:.2f}%")
                            ac3.metric("📈 총 평가 손익 합계", format_money(tot_prof))

                            st.write("")
                            st.dataframe(pd.DataFrame(active_table), use_container_width=True, hide_index=True)
                        else:
                            st.success("🎉 현재 현장에 대기 중인 요원이 없습니다! (100% 현금 회수 완료)")

                        st.markdown("---")
                        st.write("### 📜 전체 매매 장부 (최근 순)")
                        if trade_logs:
                            logs_df = pd.DataFrame(list(reversed(trade_logs)))
                            st.dataframe(logs_df, use_container_width=True)

                    perf_score = min(100, max(50, int(70 + (total_return_pct / 15) + (win_rate - 50))))
                    grade_title = "🏆 S급 (마스터 최우수 작전)" if perf_score >= 90 else ("🔥 A급 (우수 성장 작전)" if perf_score >= 75 else "🛡️ B급 (안정 방어 작전)")
                    
                    missed_cnt = len(missed_opportunities)
                    pros_text = f"총자산이 초기 대비 **{total_return_pct:.1f}%** 폭발적으로 성장했으며, 작전 승률 **{win_rate:.1f}%**, 최대 낙폭(MDD) **{max_drawdown_pct:.1f}%**로 매우 우수합니다."
                    cons_text = f"백테스트 기간 중 총 **{missed_cnt}회**의 미출격 타점(현금/슬롯 부족 또는 단가 초과)이 발생했습니다." if missed_cnt > 0 else "현금 관리와 슬롯 회전율이 100% 완벽했습니다."
                    advice_text = "복리 스케일업 모드와 폭락장 우산 스위치, 그리고 제미니 AI 참모의 실시간 진입금 처방전을 함께 활용해 리스크를 철저히 방어하세요."

                    st.markdown("---")
                    st.markdown("### 🎖️ 박가이버 사령관의 종합 진단 및 실전 리포트")
                    
                    col_sc1, col_sc2 = st.columns(2)
                    col_sc1.metric("작전 종합 점수", f"{perf_score}점 / 100점")
                    col_sc2.metric("종합 평가 등급", grade_title)

                    st.success(f"**✨ 1. 잘된 점 (강점):** {pros_text}")
                    if missed_cnt > 0:
                        st.warning(f"**⚠️ 2. 아쉬운 점 (한계):** {cons_text}")
                    else:
                        st.info(f"**⚠️ 2. 아쉬운 점 (한계):** {cons_text}")
                    st.info(f"**🛠️ 3. 향후 개선할 점:** AI 참모의 지침에 따라 초고변동성 장세에서는 진입금액 비율을 적절히 축소하여 현금을 높게 유지하세요.")
                    st.error(f"**💡 종합 실전 어드바이스:** {advice_text}")

                except Exception as e:
                    st.error(f"❌ 분석 중 에러가 발생했습니다: {e}")
