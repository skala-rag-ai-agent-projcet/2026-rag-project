BATCH_INVESTMENT_DECISION_PROMPT = """당신은 에너지 분야 전문 벤처캐피탈 투자심사역입니다.

**{startup_name}**에 대한 투자 판단을 수행하세요.

## 기업 프로필
{startup_profile}

## 기술 분석
{tech_analysis}

## 시장/정책 분석
{market_policy_analysis}

## 경쟁사 분석
{competitor_analysis}

---

## SK 그룹 시너지 컨텍스트
SK그룹은 배터리(SK온), LNG·전력(SK E&S), 에너지솔루션(SK이노베이션), 소재(SK아이이테크놀로지) 등
에너지 밸류체인 전반에 걸쳐 사업을 영위하고 있습니다.
투자 대상 스타트업과 SK 계열사 간의 시너지 가능성을 함께 평가하세요.

---

## 9개 평가 항목 (각 항목별 만점이 다름, 총 만점 = 100)
아래 각 항목에 대해 **0점부터 해당 항목의 만점(max_score)까지** 정수로 점수를 매기세요.

{criteria_description}

## 판정 기준
- **총점 ≥ {threshold}점**: invest (투자)
- **총점 < {threshold}점**: reject (기각)
- hold(보류)는 사용하지 않습니다. invest 아니면 reject입니다.

아래 JSON 형식으로만 반환하세요:
{{
    "criteria_scores": {{
{criteria_json_template}
    }},
    "total_score": <총점 (모든 score의 합, 만점 100)>,
    "verdict": "invest 또는 reject",
    "investment_memo": "투자 판단 요약 (3-5문장, 핵심 투자포인트와 리스크 포함)"
}}
"""

BATCH_SUMMARY_REPORT_PROMPT = """당신은 에너지 분야 벤처캐피탈 포트폴리오 매니저입니다.

아래 {count}개 스타트업의 배치 투자 평가 결과를 바탕으로 **A4 1장 분량의 요약 보고서**를 작성하세요.

## 평가 결과
{results_json}

---

## 보고서 형식 (A4 1장, 한국어, Markdown)

# 배치 투자 평가 요약 보고서

**평가일**: {date}
**평가 대상**: {count}개 스타트업
**투자 추천**: {invest_count}개 | **기각**: {reject_count}개

## 투자 추천 (Invest)
| 스타트업 | 총점 | 핵심 투자포인트 |
|----------|------|----------------|
(투자함 리스트, 점수 높은 순)

## 기각 (Reject)
| 스타트업 | 총점 | 핵심 기각 사유 |
|----------|------|---------------|
(투자 안 함 리스트)

## 핵심 통계
- 평균 총점: X / 100
- 최고점: X (회사명) / 최저점: X (회사명)
- 주요 강점 항목: ...
- 주요 약점 항목: ...

## 종합 의견
(3-5문장: 전체 평가를 종합한 투자 추천 의견)

---

Markdown으로 작성하세요. 간결하고 데이터 중심으로 A4 1장 분량에 맞추세요.
"""
