# ==============================================================================
# 🛡️ 박가이버표 특수 요원 매매 알고리즘 핵심 엔진 (Core Engine)
# ==============================================================================

# 1. 증권사 수수료 및 거래세 설정
BUY_FEE_RATE = 0.00015       # 매수 수수료 (0.015%)
SELL_FEE_TAX_RATE = 0.00195  # 매도 수수료 + 증권거래세 (0.195%)

# 2. 일별 시세 데이터 순회 (Daily Backtest Loop)
for date, row in df.iterrows():
    close = float(row['Close'])            # 당일 종가
    daily_return = float(row['Daily_Return']) # 당일 등락률(%)
    
    # 이동평균선 지표 추출 (20, 60, 120, 200일선)
    ma20, ma60, ma120, ma200 = row['MA20'], row['MA60'], row['MA120'], row['MA200']

    # --------------------------------------------------------------------------
    # 🎯 STEP 1. 목표가 달성 및 동반 탈출 (연쇄 청산) 체크
    # --------------------------------------------------------------------------
    # 현장에 파견된 요원 중 '단 1명이라도' 목표 수익률을 터치했는지 확인
    has_winner = any(((close - pos['entry_price']) / pos['entry_price']) * 100 >= pos['target_ret'] for pos in positions)

    if has_winner:
        batch_reinvest_profit = 0.0

        # 현장에 파견되어 있던 모든 요원 전원 동반 청산! (회전율 극대화)
        for pos in positions:
            shares = pos['shares']
            
            # 세금/수수료 정밀 공제 순손익 계산
            buy_amount_net = (shares * pos['entry_price']) * (1 + BUY_FEE_RATE)
            sell_amount_net = (shares * close) * (1 - SELL_FEE_TAX_RATE)
            profit_krw = sell_amount_net - buy_amount_net 

            # 익절 발생 시: 복리 재투자 & 전리품 수확 분기
            if profit_krw > 0:
                reinvest_amt = profit_krw * reinvest_rate       # 예: 70% 복리 재투자
                harvest_amt = profit_krw * (1.0 - reinvest_rate) # 예: 30% 수확
                
                if harvest_type == 'SHARES':
                    buyable = int(harvest_amt // close)          # 공짜 주식 매수
                    cost = buyable * close
                    leftover = harvest_amt - cost
                else: # CASH (100% 현금 수확)
                    buyable = 0
                    leftover = harvest_amt
            else:
                reinvest_amt = profit_krw  # 손실 발생 시 손실금 전액 반영
                harvest_amt, buyable, leftover = 0.0, 0, 0.0

            batch_reinvest_profit += reinvest_amt
            free_shares += buyable
            cash_harvested += leftover

        # 🚀 스노우볼 레벨UP & 스텝다운 (계단식 예산 증액/감액)
        if reinvest_rate > 0:
            step_progress += batch_reinvest_profit
            threshold = current_capital * 0.10  # 현재 자산의 +10% 채워질 때
            
            if step_progress >= threshold:      # 🚀 레벨UP! 요원 1인당 예산 10% 증액
                level_up_count += 1
                current_capital += threshold
                step_progress = 0.0
            elif step_progress <= -threshold and current_capital > initial_capital: # 🛡️ 원금 방어 스텝다운
                current_capital -= threshold
                step_progress = 0.0

        positions = []  # 부대 전원 복귀 (대기열 초기화)

    # --------------------------------------------------------------------------
    # 🛒 STEP 2. 급락 타점 시 요원 파견 (스마트 출격)
    # --------------------------------------------------------------------------
    # 당일 등락률이 설정치(-7.0% 또는 -5.0%) 이하로 폭락하고, 최대 요원(5명) 미만일 때 출격!
    if daily_return <= entry_drop_threshold and len(positions) < max_agents:
        agent_counter += 1
        
        # 💵 요원 1인당 파견 예산 산출 (직접 입력 vs 자동 계산)
        if custom_entry_amt > 0:
            scale_ratio = current_capital / initial_capital
            agent_budget = int(custom_entry_amt * scale_ratio) # 스케일업 비례 증액
        else:
            agent_budget = int(current_capital // max_agents)  # 총예산 ÷ 최대요원(5명)

        shares = int(agent_budget // close) # 종가 기준 매수 주식 수 산출
        if shares < 1: shares = 1

        # 📊 3단계 이동평균선 정배열/역배열 판정 & 상투방지 캡 적용
        is_super_bull = (close > ma20) and (ma20 > ma60) and (ma60 > ma120)
        is_mid_bull = (ma20 > ma60) or (close > ma60 > ma120)
        is_super_bear = (close < ma20) and (ma20 < ma60) and (ma60 < ma120)

        if '완전정배열 +10%' in target_mode:
            if is_super_bull or is_mid_bull:
                target_ret = 10.0 # 🔥 완전/중기 정배열 상관없이 목표가 +10% 캡(Cap)으로 고점 탈출!
                regime_desc = "🔥 완전정배열(+10%)" if is_super_bull else "📈 중기정배열(+10%)"
            elif is_super_bear:
                target_ret = 5.0  # 🌧️ 하락 추세 시 +5% 단기 스캘핑 탈출
                regime_desc = "🌧️ 완전역배열(+5%)"
            else:
                target_ret = 5.0  # 🧱 박스권/혼조 시 +5% 빠른 탈출
                regime_desc = "🧱 박스권/혼조(+5%)"

        # 현장 요원 파견 등록
        positions.append({
            'name': f"{agent_counter}호 요원",
            'entry_price': close,
            'shares': shares,
            'target_ret': target_ret,
            'regime_desc': regime_desc,
            'used_cap_at_entry': current_capital
        })
