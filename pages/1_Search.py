import streamlit as st
import pandas as pd

# 🌟 보조 페이지에서는 st.set_page_config를 삭제해야 화면 전환 에러가 나지 않습니다!

st.title("🔎 작전 구역(섹터/종목) 탐색기")
st.caption("관심 있는 테마 및 섹터별 종목을 검색·선택하여 [박가이버 작전 통제실]로 한 번에 보낼 수 있습니다.")
st.markdown("---")

# --- 1. 테마/섹터별 종목 데이터베이스 ---
SECTOR_DATABASE = {
    "반도체 & HBM / 칩렛": {
        "테크윙": "089030.KQ",
        "한미반도체": "042700.KS",
        "HPSP": "403870.KQ",
        "이오테크닉스": "039030.KQ",
        "리노공업": "058470.KQ",
        "ISC": "095340.KQ",
        "주성엔지니어링": "036930.KQ",
        "원익IPS": "240810.KQ",
        "삼성전자": "005930.KS",
        "SK하이닉스": "000660.KS"
    },
    "바이오 & 제약": {
        "알테오젠": "196170.KQ",
        "셀트리온": "068270.KS",
        "삼성바이오로직스": "207940.KS",
        "HLB": "028300.KQ",
        "유한양행": "000100.KS",
        "리가켐바이오": "141080.KQ"
    },
    "2차전지 & 에코": {
        "에코프로비엠": "247540.KQ",
        "에코프로": "086520.KQ",
        "LG에너지솔루션": "373220.KS",
        "POSCO홀딩스": "005490.KS",
        "엘앤에프": "066970.KQ"
    },
    "자동차 & 대표 제조": {
        "현대차": "005380.KS",
        "기아": "000270.KS",
        "현대모비스": "012330.KS"
    },
    "IT & 플랫폼": {
        "NAVER": "035420.KS",
        "카카오": "035720.KS"
    }
}

# 전체 종목 통합 모음
ALL_STOCKS = {}
for sector, stocks in SECTOR_DATABASE.items():
    for name, code in stocks.items():
        ALL_STOCKS[name] = {"code": code, "sector": sector}

# --- 2. 탐색 조종간 ---
st.subheader("🎯 1. 테마/섹터별 둘러보기")

col1, col2 = st.columns([1, 2])

with col1:
    selected_sector = st.selectbox("탐색할 섹터/테마 선택", list(SECTOR_DATABASE.keys()))

with col2:
    sector_stocks = list(SECTOR_DATABASE[selected_sector].keys())
    st.write(f"▼ **[{selected_sector}] 주요 감시 종목 목록**")
    st.info(", ".join(sector_stocks))

st.markdown("---")

st.subheader("🛒 2. 작전 통제실로 전송할 종목 바구니 담기")

default_selections = ["테크윙", "한미반도체", "HPSP", "알테오젠", "에코프로비엠"]

selected_basket = st.multiselect(
    "백테스트 검증을 진행할 종목들을 선택해 주세요 (1개~10개 권장):",
    options=list(ALL_STOCKS.keys()),
    default=default_selections
)

if selected_basket:
    summary_data = []
    for name in selected_basket:
        info = ALL_STOCKS[name]
        summary_data.append({
            "종목명": name,
            "티커 코드": info["code"],
            "소속 테마/섹터": info["sector"]
        })
    
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

    st.markdown("---")
    
    # 전송 버튼 클릭 시 메인 통제실로 데이터 전달
    if st.button("🚀 선택한 종목들을 [작전 통제실]로 즉시 전송!", type="primary"):
        st.session_state["custom_stock_names"] = selected_basket
        st.session_state["custom_stock_dict"] = {name: ALL_STOCKS[name]["code"] for name in selected_basket}
        
        st.success(f"🎉 총 {len(selected_basket)}개 종목이 사령부로 전송되었습니다!")
        st.info("👈 왼쪽 사이드바 메뉴에서 [app]을 누르시면 전송된 종목으로 검증이 시작됩니다!")
else:
    st.warning("⚠️ 최소 1개 이상의 종목을 선택해 주세요.")
