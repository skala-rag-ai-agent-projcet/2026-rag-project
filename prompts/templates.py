STARTUP_SEARCH_PROMPT = """당신은 Energy 도메인 전문 스타트업 리서치 애널리스트입니다.

사용자가 입력한 스타트업 **{startup_name}**에 대해 아래 항목을 포함하는 기업 프로필을 JSON으로 작성하세요.

## 수집 항목
- "company_name": 회사 정식 명칭
- "founded_year": 설립 연도
- "ceo": 대표자명
- "headquarters": 본사 소재지
- "core_technology": 핵심 기술 (1-2문장)
- "product_service": 주요 제품/서비스
- "funding_stage": 투자 단계 (Seed / Series A / B / etc.)
- "total_funding": 누적 투자금액 (알 수 있는 경우)
- "key_investors": 주요 투자자
- "domain_classification": 도메인 분류 (e.g., "배터리", "ESS", "수소", "태양광" 등)
- "description": 회사 개요 (3-5문장)

## 검색 결과
{search_results}

## 부정적/리스크 검색 결과
{negative_search_results}

JSON만 반환하세요. 다른 텍스트는 포함하지 마세요.
"""

DOMAIN_CHECK_PROMPT = """당신은 Energy 도메인 투자 심사역입니다.

아래 스타트업이 **Energy 도메인**에 해당하는지 판별하세요.

Energy 도메인이란: 배터리, ESS(에너지저장시스템), 에너지전환, 수소, 태양광, 풍력, 전력 인프라, 에너지 효율, 스마트그리드, 차세대 에너지 기술 등을 포함합니다.

## 스타트업 정보
{startup_profile}

## 판별 기준
1. 핵심 기술/제품이 에너지 관련인가?
2. 주요 매출/사업이 에너지 산업과 직접 연관되는가?
3. 에너지 밸류체인 내에 위치하는가?

아래 JSON 형식으로만 답변하세요:
{{
    "is_energy_domain": true/false,
    "reason": "판별 근거 (2-3문장)",
    "sub_domain": "세부 도메인 (e.g., 배터리, ESS, 수소 등)"
}}
"""

TECH_ANALYSIS_PROMPT = """당신은 에너지 기술 전문 애널리스트입니다.

**{startup_name}**의 기술을 심층 분석하세요.

## 기업 정보
{startup_profile}

## RAG 참고 자료
{rag_context}

## 웹 검색 결과
{search_results}

## 부정적/리스크 검색 결과
{negative_search_results}

## 분석 항목
1. **핵심 기술 개요**: 기술의 원리, 구조, 독창성
2. **에너지 특화 지표**:
   - 에너지밀도 / 효율 / 수명 (해당 시)
   - 충·방전 특성, 안전성 (배터리의 경우)
3. **기술성숙도(TRL)**: 1-9 단계 평가 + 근거
4. **지식재산(IP)**: 특허, 논문, 핵심 노하우
5. **상용화 수준**: PoC / 파일럿 / 양산 단계
6. **기술적 한계 및 리스크**: 확장성, 내구성, 원가 등

구체적인 수치와 근거를 포함하여 분석하세요. 정보가 부족한 경우 명확히 표시하세요.

분석 결과를 아래 JSON 형식으로 반환하세요:
{{
    "core_technology": "핵심 기술 개요",
    "energy_metrics": "에너지 특화 지표 분석",
    "trl_level": <1-9>,
    "trl_justification": "TRL 판단 근거",
    "ip_status": "지식재산 현황",
    "commercialization_stage": "PoC / 파일럿 / 양산",
    "limitations": "기술적 한계 및 리스크",
    "summary": "기술 분석 종합 요약 (3-5문장)"
}}
"""

MARKET_POLICY_PROMPT = """당신은 에너지 산업 시장 분석 전문가입니다.

**{startup_name}**의 시장 기회와 정책 환경을 분석하세요.

## 기업 정보
{startup_profile}

## RAG 참고 자료
{rag_context}

## 웹 검색 결과
{search_results}

## 부정적/리스크 검색 결과
{negative_search_results}

## 분석 항목
1. **시장 규모 (TAM/SAM/SOM)**: 글로벌 및 국내 시장 규모 추정
2. **시장 성장성**: CAGR, 성장 동인, 에너지 전환 트렌드
3. **고객 및 수요**: 타깃 고객군, 수요 동인, pain point
4. **지불 의사 및 ROI**: 고객의 비용절감/효율향상 기대치
5. **수익모델**: 매출 구조, 반복매출 가능성, 마진
6. **정책 수혜**: IRA, RE100, 탄소중립 정책 등 에너지 정책의 영향
7. **규제 리스크**: 인허가, 안전 규제, 환경 규제 등
8. **한계점**: 시장 진입 장벽, 시장 불확실성

구체적인 수치와 근거를 포함하세요.

## 정책 위반 판별
위 분석을 바탕으로, 이 스타트업이 현행 에너지 정책·규제와 **심각하게 충돌**하는지 판별하세요.
- 인허가 불가능, 수출통제 대상, 환경규제 위반, 안전인증 불가 등
- 단순 리스크가 아닌 **사업 자체를 불가능하게 하는 수준**인지 여부

분석 결과를 아래 JSON 형식으로 반환하세요:
{{
    "tam": "TAM 규모 및 근거",
    "sam": "SAM 규모 및 근거",
    "som": "SOM 규모 및 근거",
    "growth_rate": "시장 성장률 및 근거",
    "target_customers": "타깃 고객군",
    "willingness_to_pay": "지불 의사 분석",
    "revenue_model": "수익모델 분석",
    "policy_benefits": "정책 수혜 분석",
    "regulatory_risks": "규제 리스크",
    "limitations": "시장 한계점",
    "summary": "시장/정책 분석 종합 요약 (3-5문장)",
    "policy_violation": false,
    "policy_violation_reason": "정책 위반 사유 (위반 시 상세 기술, 미위반 시 '해당 없음')"
}}
"""

COMPETITOR_ANALYSIS_PROMPT = """당신은 에너지 산업 경쟁 분석 전문가입니다.

**{startup_name}**의 경쟁 환경을 분석하세요.

## 기업 정보
{startup_profile}

## 기술 분석 결과
{tech_analysis}

## 시장/정책 분석 결과
{market_policy_analysis}

## 웹 검색 결과 (경쟁사 비교)
{search_results}

## 부정적/리스크 검색 결과
{negative_search_results}

## 분석 항목
1. **경쟁사 맵**: 직접 경쟁사 3-5개 + 간접 경쟁사/대체기술
2. **비교 분석**: 기술력, 시장점유율, 투자규모, 팀, 상용화 단계 비교
3. **대체기술 위협**: 해당 기술을 대체할 수 있는 기술/솔루션
4. **진입장벽**: 특허, 네트워크 효과, 전환비용, 데이터 해자
5. **포지셔닝**: {startup_name}의 경쟁 우위와 약점
6. **경쟁 전략 시사점**: 차별화 전략, 시장 선점 가능성
7. **경쟁력 점수**: 전체 경쟁 환경 속 {startup_name}의 종합 경쟁력을 0-10점으로 평가

분석 결과를 아래 JSON 형식으로 반환하세요:
{{
    "direct_competitors": [
        {{"name": "경쟁사명", "description": "설명", "comparison": "비교 포인트"}}
    ],
    "substitute_technologies": "대체기술 위협 분석",
    "entry_barriers": "진입장벽 분석",
    "competitive_advantages": "{startup_name}의 경쟁 우위",
    "competitive_weaknesses": "{startup_name}의 약점",
    "positioning": "시장 포지셔닝 평가",
    "competitiveness_score": <0-10>,
    "summary": "경쟁 분석 종합 요약 (3-5문장)"
}}
"""

INVESTMENT_DECISION_PROMPT = """당신은 에너지 분야 전문 벤처캐피탈 투자심사역입니다.

**{startup_name}**에 대한 투자 판단을 수행하세요.

## 기업 프로필
{startup_profile}

## 기술 분석
{tech_analysis}

## 시장/정책 분석
{market_policy_analysis}

## 경쟁사 분석
{competitor_analysis}

## 내부 평가 기준 참고자료
{rag_context}

---

## SK 그룹 시너지 컨텍스트
SK그룹은 배터리(SK온), LNG·전력(SK E&S), 에너지솔루션(SK이노베이션), 소재(SK아이이테크놀로지) 등
에너지 밸류체인 전반에 걸쳐 사업을 영위하고 있습니다.
투자 대상 스타트업과 SK 계열사 간의 시너지 가능성을 함께 평가하세요:
- SK 계열사와의 공동사업/기술 내재화 가능성
- SK 에너지 밸류체인 내 확장성
- SK의 전략적 투자 방향과의 정합성

---

## 9개 평가 항목 (가중합 100%)
아래 각 항목에 대해 0-100점으로 평가하고, 점수의 근거를 제시하세요.
각 항목의 평가 질문에 답하고, 점수 기준(High/Medium/Low)을 참고하여 적절한 범위에서 점수를 부여하세요.

{criteria_description}

---

## 점수 캘리브레이션 가이드 (반드시 준수 — 매우 중요)

### 점수 분포 원칙
- **가중합 60+ (invest)**: 12개 스타트업 중 **최대 2-3개**만 해당. 우수한 경우만.
- **대부분의 스타트업은 가중합 35-55점 범위**에 위치해야 정상.
- 가중합 55-64: 아쉽지만 기각. 한두 가지가 특출나도 전체적으로 미달.
- 가중합 55 이하: 명확한 기각.

### 채점 규칙
1. **약점 먼저 나열**: 각 항목 채점 전에 해당 항목의 **약점 2개를 반드시 식별**한 뒤 점수를 매기세요.
2. 정보가 부족한 항목 = **보수적으로 채점** (30-40점 수준). "정보 부족이니 중간" 금지.
3. 에너지 스타트업이라는 이유만으로 시장성·확장성에 고점을 주지 마세요. 구체적 TAM/SAM 수치 없이 High 금지.
4. **SK 시너지**: MOU, 계약, 공식 파트너십 등 구체적 근거가 없으면 **Low (0-44점)**. "잠재적 시너지"만으로 Medium 이상 금지.
5. 각 항목은 **독립적으로** 평가하세요. 한 항목이 높다고 다른 항목도 높아지지 않음.
6. **근거 없이 높은 점수를 주지 마세요.** 구체적 사실/데이터가 없으면 Low.

### Few-shot 저점수 예시 (참고)
- SK시너지: SK와 공식 관계 없는 배터리 소재 스타트업 → 25점 (Low)
- 시장규모: 니치 시장, TAM 수치 미확인 → 30점 (Low)
- 문제해결: pain point 불명확, 기존 대안 다수 → 25점 (Low)
- 기술차별: TRL 4 이하, 특허 미확보, 경쟁사 다수 → 30점 (Low)
- 수익모델: 매출 미발생, 수익 구조 불명확 → 20점 (Low)
- 창업자·팀: 산업 경험 부족, 핵심인력 미확보 → 25점 (Low)

## 판정 기준
- **가중합 점수 ≥ {threshold}점**: invest (투자)
- **가중합 점수 < {threshold}점**: reject (기각)
- hold(보류)는 사용하지 않습니다. invest 아니면 reject입니다.

아래 JSON 형식으로만 반환하세요:
{{
    "weakness_analysis": {{
        "sk_synergy": ["약점1", "약점2"],
        "market_size_growth": ["약점1", "약점2"],
        "problem_solving": ["약점1", "약점2"],
        "willingness_to_pay": ["약점1", "약점2"],
        "tech_differentiation": ["약점1", "약점2"],
        "scalability": ["약점1", "약점2"],
        "revenue_model": ["약점1", "약점2"],
        "risk": ["약점1", "약점2"],
        "founder_team": ["약점1", "약점2"]
    }},
    "criteria_scores": {{
        "sk_synergy": {{"score": <0-100>, "justification": "근거"}},
        "market_size_growth": {{"score": <0-100>, "justification": "근거"}},
        "problem_solving": {{"score": <0-100>, "justification": "근거"}},
        "willingness_to_pay": {{"score": <0-100>, "justification": "근거"}},
        "tech_differentiation": {{"score": <0-100>, "justification": "근거"}},
        "scalability": {{"score": <0-100>, "justification": "근거"}},
        "revenue_model": {{"score": <0-100>, "justification": "근거"}},
        "risk": {{"score": <0-100>, "justification": "근거"}},
        "founder_team": {{"score": <0-100>, "justification": "근거"}}
    }},
    "weighted_score": <가중합 점수>,
    "verdict": "invest 또는 reject",
    "investment_memo": "투자 판단 요약 (3-5문장, 핵심 투자포인트와 리스크 포함)"
}}
"""

REPORT_WRITER_PROMPT = """당신은 벤처캐피탈의 투자 보고서 작성 전문가입니다.

아래 분석 결과를 바탕으로 **투자 평가 보고서**를 한국어로 작성하세요.

## 기업 프로필
{startup_profile}

## 기술 분석
{tech_analysis}

## 시장/정책 분석
{market_policy_analysis}

## 경쟁사 분석
{competitor_analysis}

## 투자 판단 결과
{investment_decision}

## 출처 목록
{references}

---

## 보고서 목차 (반드시 이 구조를 따르세요)

# 1. SUMMARY
- 투자 대상 한 줄 정의
- 핵심 투자포인트 2~3개
- 핵심 리스크 2~3개
- 투자/기각 판단 및 근거 요약
(분량: 1/2~1페이지)

# 2. COMPANY & BUSINESS
- 기업 개요 (설립, 대표, 소재지, 투자현황)
- 사업 아이디어 / 핵심 컨셉
- 비즈니스 모델

# 3. TECHNOLOGY & PRODUCT
- 핵심 기술 상세
- 기술 차별성
- 실증/상용화 수준 (TRL)
- 기술적 한계점

# 4. MARKET & COMMERCIALIZATION
- 시장 규모·성장성 (TAM/SAM/SOM)
- 고객·수요
- 지불 의사 / ROI
- 수익모델
- 한계점

# 5. TEAM & EXECUTION
- 창업자·팀 역량
- 기술 역량
- 실행력
- 한계점

# 6. RISKS & LIMITATIONS
- 시장 리스크
- 기술 리스크
- 규제 리스크
- 경쟁 리스크
- 종합 한계점

# 7. INVESTMENT DECISION
- 종합 평가
- 투자/기각 판단
- 9개 항목 점수표 (표 형식)
  | 항목 | 비중 | 점수 | 근거 |
- 가중합 점수
- SK 시너지 평가

# 8. REFERENCE
출처를 아래 형식으로 정리:
- 기관 보고서: 발행기관(YYYY). *보고서명*. URL
- 학술 논문: 저자(YYYY). 논문제목. *학술지명*, 권(호), 페이지.
- 웹페이지: 기관명 또는 작성자(YYYY-MM-DD). *제목*. 사이트명, URL

---

Markdown 형식으로 작성하세요. 구체적인 데이터 포인트를 포함하세요.
한국어로 작성하세요.
"""

EVALUATION_CHECK_PROMPT = """당신은 투자 평가 품질 관리 전문가입니다.

아래 투자 판단 결과가 9개 평가 항목 모두에 대해 적절한 점수와 충분한 근거를 포함하고 있는지 검증하세요.

## 투자 판단 결과
{investment_decision}

## 검증 기준
1. 9개 항목 모두 점수가 매겨져 있는가? (sk_synergy, market_size_growth, problem_solving, willingness_to_pay, tech_differentiation, scalability, revenue_model, risk, founder_team)
2. 각 항목의 점수가 0-100 범위 내인가?
3. 각 항목에 대한 근거(justification)가 2문장 이상인가?
4. 가중합 점수가 정확히 계산되었는가?
5. 투자 판단(invest/reject)이 가중합 점수와 일치하는가?

아래 JSON 형식으로만 반환하세요:
{{
    "evaluation_complete": true/false,
    "missing_criteria": ["누락된 항목 목록"],
    "insufficient_justification": ["근거가 부족한 항목 목록"],
    "score_calculation_correct": true/false,
    "verdict_consistent": true/false,
    "feedback": "보완이 필요한 경우 구체적 피드백"
}}
"""

# ── Batch mode prompts ───────────────────────────────────────────────

BATCH_COMPARISON_REPORT_PROMPT = """당신은 에너지 분야 벤처캐피탈 포트폴리오 매니저입니다.

아래 {count}개 스타트업의 개별 투자 평가 결과를 바탕으로 **종합 비교 보고서**를 한국어로 작성하세요.

## 개별 평가 결과
{results_json}

---

## 보고서 구성 (Markdown)

# 종합 비교 보고서

## 1. Executive Summary
- 평가 대상 {count}개 스타트업 한 줄 소개
- 최종 투자 추천 순위
- 핵심 인사이트 (2-3문장)

## 2. 비교 분석표
| 항목 | {header_row} |
|------|{separator_row}|
| 도메인 | ... |
| 핵심 기술 | ... |
| TRL | ... |
| 가중합 점수 | ... |
| 판정 | ... |
| 경쟁력 점수 | ... |
| SK 시너지 | ... |

## 3. 9개 항목별 비교
각 평가 항목에 대해 스타트업 간 점수를 비교하고, 우위/열위를 분석하세요.

## 4. 투자 포트폴리오 제안
- 단독 투자 추천 대상과 근거
- 조합 투자(포트폴리오) 관점에서의 시너지 가능성
- 리스크 분산 관점

## 5. 종합 의견
전체 평가를 종합한 투자 추천 의견 (3-5문장)

---

구체적인 수치와 데이터 포인트를 포함하세요. Markdown으로 작성하세요.
"""

BATCH_HOLD_REPORT_PROMPT = """당신은 에너지 분야 벤처캐피탈 포트폴리오 매니저입니다.

{count}개 스타트업을 평가했으나 **모든 대상이 보류(hold) 판정**을 받았습니다.
아래 결과를 바탕으로 **보류 사유 종합 보고서**를 한국어로 작성하세요.

## 개별 평가 결과
{results_json}

---

## 보고서 구성 (Markdown)

# 보류 사유 종합 보고서

## 1. Executive Summary
- 평가 대상 {count}개 스타트업 및 보류 판정 요약
- 공통적 보류 사유

## 2. 개별 보류 사유
각 스타트업별로:
- 가중합 점수 및 기준 미달 항목
- 핵심 리스크
- 개선 시 재검토 가능 여부

## 3. 보류 사유 비교표
| 스타트업 | 점수 | 주요 부족 항목 | 핵심 리스크 | 재검토 가능성 |
|----------|------|--------------|------------|-------------|

## 4. 시장 전체 평가
- 에너지 도메인 스타트업 전반의 투자 적합성 평가
- 향후 모니터링 대상 선정 기준

## 5. 종합 의견
보류 판정에 대한 종합 소견 (3-5문장)

---

구체적인 수치와 데이터 포인트를 포함하세요. Markdown으로 작성하세요.
"""

BATCH_DISCOVER_PROMPT = """당신은 Energy 도메인 전문 스타트업 리서치 애널리스트입니다.

아래 웹 검색 결과를 바탕으로, 투자 검토 대상이 될 수 있는 **한국 에너지 도메인 스타트업 {count}개**를 선별하세요.

## 선별 기준
- Energy 도메인: 배터리, ESS, 수소, 태양광, 풍력, 전력 인프라, 에너지 효율, 스마트그리드 등
- 투자 단계: Seed ~ Series C (초기~성장기)
- 기술 기반 스타트업 우선
- 서로 다른 세부 도메인/기술 영역에서 선별하여 다양성 확보

## 웹 검색 결과
{search_results}

정확히 {count}개 스타트업의 **회사명만** JSON 배열로 반환하세요:
["회사명1", "회사명2", ...]

JSON 배열만 반환하세요. 다른 텍스트는 포함하지 마세요.
"""
