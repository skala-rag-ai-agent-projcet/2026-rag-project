# VSco — AI Startup Investment Evaluation Agent

본 프로젝트는 **에너지 전환(Energy Transition)** 도메인의 스타트업에 대한 투자 가능성을 자동으로 평가하는 **Multi-Agent 시스템**을 설계하고 구현한 프로젝트입니다.

## Overview

| | |
|---|---|
| **Objective** | 에너지(배터리·ESS) 스타트업의 기술력, 시장성, 리스크 등 9개 기준으로 투자 적합성 자동 분석 |
| **Method** | Multi-Agent Workflow + Corrective RAG + Web Search |
| **Domain** | Energy Transition / Next-Gen Energy Infrastructure (배터리·ESS 중심) |
| **Threshold** | 100점 만점 중 60점 이상 시 Invest 판정 |

## Features

- **Corrective RAG 기반 근거 수집** — 4개 도메인 PDF(산업 개관, 기술 벤치마크, 정책·규제, SK 전략) → FAISS 벡터 검색 → LLM 관련성 평가 → 쿼리 리라이트/웹 검색 폴백
- **9개 투자 기준 정량 평가** — SK 시너지, 시장 규모, 기술 차별성, 팀 역량 등 가중합 100점 체계
- **배치 모드** — 웹 검색 기반 스타트업 자동 발굴 → 도메인 필터링 → 병렬 평가 → A4 요약 리포트
- **8페이지 투자 보고서 자동 생성** — Markdown → HTML → PDF 변환
- **점수 인플레이션 방지** — 역방향 웹 검색(리스크·약점 탐색) + 서버사이드 균일 점수 감점 로직

## Tech Stack

| Category | Details |
|----------|---------|
| **Orchestration** | LangGraph (StateGraph, 조건부 라우팅, 병렬 브랜치) |
| **LLM** | GPT-4o-mini via OpenAI API |
| **RAG** | FAISS + Corrective RAG (관련성 평가 → 쿼리 리라이트 → 웹 폴백) |
| **Embedding** | BAAI/bge-m3 (multilingual, 8192 토큰) |
| **Web Search** | Tavily Search API |
| **PDF Generation** | WeasyPrint (HTML → PDF) |
| **UI** | Streamlit |
| **Language** | Python 3.12 |

---

## Design Decisions

### 왜 Supervisor를 쓰지 않았는가

초기 설계 시 Supervisor 패턴을 검토했으나, 최종적으로 채택하지 않았습니다.

- 투자 평가 파이프라인은 **순서가 명확**합니다 — 탐색 → 도메인 확인 → 분석 → 판단 → 보고서. Supervisor가 동적으로 에이전트를 선택할 필요가 없음
- Supervisor를 두면 **서브 에이전트가 다른 서브 에이전트를 직접 호출하는 구조**가 생기기 쉬운데, 이는 디버깅과 상태 추적을 어렵게 만듦
- 대신 **LangGraph의 조건부 라우팅**으로 분기를 처리 — 도메인 부적합 시 즉시 기각, 평가 지표 누락 시 재평가(최대 1회) 등
- 기술 분석 / 시장·정책 분석처럼 독립적인 에이전트는 **Fan-out 병렬 실행**으로 처리하여 효율성 확보

### 왜 VC가 아닌 CVC 관점을 추가했는가

일반 VC의 투자 판단 기준(Bessemer's Checklist, Scorecard Method)만으로는 **CVC(Corporate Venture Capital)의 관점**이 빠집니다. CVC는 단순 수익률이 아니라 모회사 사업과의 시너지를 봅니다. 과제 목적이 SK 에너지 밸류체인과의 연결성을 평가하는 것이므로, **SK 사업 시너지(15%)**를 커스텀 항목으로 추가하여 **VC + CVC 복합 관점**의 평가 체계를 구성했습니다.

| 출처 | 반영 항목 |
|------|---------|
| **SK 전략자료 (CVC 커스텀)** | SK 사업 시너지 (15%) |
| **Bessemer + Scorecard 기반** | 시장 규모·성장성, 기술 차별성·상용화, 창업자·팀 역량 |
| **Bessemer 체크리스트 + VC 실사 보완** | 문제 해결력, 확장성, 고객 지불 의사, 수익모델·단위경제성, 규제·리스크 |

### 왜 bge-m3을 선택했는가

도메인 문서가 **한영 혼합**(기술 용어·논문은 영어, 정책·시장 자료는 한국어)이라 두 임베딩 모델을 15개 도메인 질문으로 정량 비교했습니다.

| 모델 | 특징 |
|------|------|
| **BAAI/bge-m3** | 다국어 범용, 8192 토큰, Matryoshka 표현 |
| **upskyy/bge-m3-korean** | bge-m3의 한국어 파인튜닝 버전 |

**비교 결과:**

- **코사인 유사도**: bge-m3이 15개 쿼리 중 12개에서 우위
- **LLM Judge 관련성 평가**: 대부분 동등하거나 bge-m3이 소폭 우위
- **Top-5 Jaccard 겹침**: 평균 0.50 — 두 모델이 절반은 같은 문서를 가져오지만, 나머지 절반에서 bge-m3이 더 관련성 높은 문서를 검색
- **결론**: 한국어 파인튜닝 모델이 반드시 유리하지 않음. 도메인 문서가 한영 혼합이라 다국어 범용 모델이 더 적합 → **BAAI/bge-m3 채택**

<!-- 📸 사진: 임베딩 비교 종합 테이블 -->
<!-- 경로: outputs/embedding_comparison/summary_table.png -->

<!-- 📸 사진: 유사도 바 차트 (쿼리별 평균 코사인 유사도 비교) -->
<!-- 경로: outputs/embedding_comparison/similarity_bar_chart.png -->

<!-- 📸 사진: 유사도 박스플롯 (모델별 분포) -->
<!-- 경로: outputs/embedding_comparison/similarity_box_plot.png -->

<!-- 📸 사진: LLM Judge 관련성 히트맵 (쿼리×모델 관련성 0-2점) -->
<!-- 경로: outputs/embedding_comparison/relevance_heatmap.png -->

<!-- 📸 사진: 카테고리별 레이더 차트 (tech/market/competitor) -->
<!-- 경로: outputs/embedding_comparison/radar_chart.png -->

<!-- 📸 사진: Top-5 Jaccard 겹침도 -->
<!-- 경로: outputs/embedding_comparison/overlap_bar_chart.png -->

---

## Agents

본 시스템은 7개의 전문 에이전트가 파이프라인으로 연결됩니다.

| Agent | 역할 | RAG | 주요 입출력 |
|-------|------|-----|------------|
| **Startup Search** | 웹 검색으로 기업 프로필 수집 | - | → 기업명, 핵심기술, 펀딩 단계, 설립연도 |
| **Domain Check** | 에너지 도메인 적합성 판별 (최대 2회 재시도) | - | → is_energy_domain, sub_domain |
| **Tech Analysis** | 기술 경쟁력·TRL·차별성 심층 분석 | Corrective RAG | → TRL, 벤치마크 비교, 기술 리스크 |
| **Market & Policy** | 시장 규모(TAM/SAM)·정책·규제 분석 | Corrective RAG | → TAM, CAGR, 정책 수혜/리스크 |
| **Competitor Analysis** | 경쟁 환경 매핑 | - | → 경쟁사, 포지셔닝, 위협 수준 |
| **Investment Decision** | 9개 기준 가중 평가 + 투자 판정 | - | → 항목별 점수, 총점, invest/reject |
| **Report Writer** | 8페이지 투자 보고서 생성 | - | → Markdown + PDF 보고서 |

### 파이프라인 흐름

```
[Batch Startup Processing]
         ↓
[스타트업 탐색 에이전트] ←------ no: 쿼리 재작성 후 재탐색 (max 1)
         ↓
    ◇ 도메인 확인 ◇
    │           │
   yes         no → target domain 기업만 전달
    ↓
┌───────────────────┐
│ [기술 분석]  [시장 및 정책 분석] │  ← 병렬 실행 + Corrective RAG
└─────────┬─────────┘
          ↓
  결과 형식 통합 로직
          ↓
  [경쟁사 분석 에이전트] ←------ 검증 실패시 재시도 (max 1)
          ↓
  ┌─────────────────────────────────┐
  │     투자 판단 입력 검증            │
  │  기술/시장/경쟁사 분석 완료 여부     │
  │  필수 필드 누락 여부 확인           │
  └──────────┬──────────────────────┘
             ↓
  [투자 판단 에이전트]
          ↓          ←------ no: 평가 지표 미반영 시 재평가
  ◇ 투자 평가 지표 반영 여부 확인 ◇
          ↓ yes
    [최종 결과 집계]
          ↓
  [보고서 생성 에이전트]
```

## Architecture

<!-- 📸 사진: 아키텍처 그래프 다이어그램 -->
<!-- 경로: GitHub 업로드 이미지 (기존 Graph 제출용) -->

<img width="2448" height="3764" alt="Graph 제출용" src="https://github.com/user-attachments/assets/47f5768d-fad6-4ae4-83aa-d42b2462adcd" />

---

## Evaluation Criteria

9개 투자 평가 기준 (가중합 = 100점). Scorecard Method 비중 + Bessemer's Checklist 관점 + SK CVC 전략 커스텀으로 구성했습니다.

| # | 기준 | 배점 | 출처 | 핵심 질문 | 평가 포인트 |
|---|------|------|------|----------|------------|
| 1 | **SK 사업 시너지** | **15점** | **SK 전략자료 + CVC 커스텀** | SK 에너지 밸류체인과 직접 연결되는가? | 배터리·LNG·전력·에너지솔루션·소재 밸류체인 연결성, 기존 계열사 공동사업 가능성, 기술 내재화 가능성 |
| 2 | 시장 규모·성장성 | 17점 | Bessemer + Scorecard | TAM/SAM 규모와 성장 전망은? | TAM/SAM/SOM 규모, 글로벌 확장 가능성, 에너지 전환·정책 변화에 따른 성장성 |
| 3 | 기술 차별성·상용화 | 14점 | Bessemer + Scorecard | 경쟁사 대비 차별적이고 상용화에 근접? | 성능·효율·안정성·가격 우위, PoC·파일럿·상용화 단계, 기술 신뢰성, 특허·노하우 |
| 4 | 창업자·팀 역량 | 12점 | Bessemer + Scorecard | 성공시킬 역량과 몰입도를 갖추었는가? | 산업 전문성, 기술·사업 균형, 실행력, 핵심 인력 구성, 장기 비전·몰입 의지 |
| 5 | 문제 해결력 | 10점 | Bessemer Checklist | 고객 pain point가 명확하고 시급한가? | 고객 pain point 명확성, 기존 방식 대비 개선 정도, 필수성·도입 필요성 |
| 6 | 확장성 | 10점 | Bessemer Checklist | 지역/산업 확장이 가능한 구조인가? | 지역·산업 확장성, 플랫폼화 가능성, 장기 성장 잠재력 |
| 7 | 고객 지불 의사 | 8점 | Bessemer Checklist | 실제 비용 지불 의사가 확인되는가? | 비용 절감·효율 향상·규제 대응, ROI·유료 PoC·계약 여부·지불 전환 가능성 |
| 8 | 수익모델·단위경제성 | 8점 | Bessemer + VC 실사 | 수익 구조가 명확하고 검증되었는가? | 매출 구조 명확성, 반복매출 여부, 매출총이익률, 회수기간, 운영 단위당 채산성 |
| 9 | 규제·운영 리스크 | 6점 | Bessemer Checklist | 규제·운영 리스크가 치명적인가? | 인허가·인증 필요성, 안전 규제, 공급망 리스크, 운영 복잡도, 법적 분쟁·대체기술 리스크 |

---

## RAG Pipeline

### Corrective RAG 구조

에이전트가 "감"이 아닌 "근거"로 판단하도록, 4개 도메인 PDF를 FAISS 벡터스토어에 인덱싱하고 Corrective RAG로 검색합니다. 에너지 산업은 정책 의존도가 높아 최신 법령·가이드라인·정부 자료 grounding이 핵심입니다.

```
질의 → FAISS Top-5 검색 (bge-m3)
        → LLM 관련성 평가 (binary yes/no)
        → 관련 문서 50%+ → 컨텍스트 사용
        → 관련 문서 50%- → 쿼리 리라이트 → 재검색
        → 여전히 부족    → 웹 검색 폴백 (Tavily)
```

<img width="2804" height="1704" alt="CRAG 파이프라인" src="https://github.com/user-attachments/assets/4f576313-2b62-4057-9900-21f2dfb607f9" />


### RAG 문서 (4개 PDF → 174 청크)

| 문서 | 내용 |
|------|------|
| 배터리·에너지저장 산업 개관 | 시장 규모, 밸류체인, 수요처 구조, 중국 편중 리스크 |
| 에너지 저장 기술 벤치마크 | Li-ion/VRFB/NaS 등 기술별 TRL, RTE, 사이클 수명, LCOS 비교 |
| 한국 배터리·에너지 정책·규제 | K-배터리 정책, NDC, 배출권거래제, ESS 안전기준 |
| SK 전략 적합도 | SK 에너지 밸류체인, 시너지 평가 프레임워크 |

---

## Two Modes — Single & Batch

시스템은 두 가지 실행 모드를 제공하며, 각 모드가 보여주는 것이 다릅니다.

| | Single Mode | Batch Mode |
|---|---|---|
| **목적** | 특정 기업에 대한 심층 투자 분석 | 다수 기업을 자동 탐색·비교·선별 |
| **입력** | 기업명 1개 | 도메인 키워드 (예: "에너지 배터리 ESS") |
| **프로세스** | 7개 에이전트 순차+병렬 파이프라인 | 스타트업 자동 발굴 → 도메인 필터 → 7개 에이전트 파이프라인 × N개 기업 |
| **출력** | 8섹션 투자 보고서 (PDF) | 전체 비교표 + 기업별 상세 + 횡단 분석 (PDF) |
| **보여주는 것** | **"이 기업이 왜 투자할 만한가"** — 개별 기업의 투자 근거와 리스크 상세 분석 | **"여러 기업 중 어떤 기업이 투자 가치가 있는가"** — 스크리닝과 비교 선별 |

---

## Results — Single Mode

개별 스타트업에 대한 심층 투자 보고서를 생성합니다. 보고서는 8개 섹션(Summary → Company & Business → Technology & Product → Market & Commercialization → Team & Execution → Risks & Limitations → Investment Decision → Reference)으로 구성됩니다.

### 스탠다드에너지 — 투자 판정 (가중합 81.35/100)

| 항목 | 비중 | 점수 | 근거 |
|------|------|------|------|
| SK 시너지 | 10% | 85 | SK 배터리·전력 솔루션과 직접 연결 가능한 VIB 기술 보유 |
| 시장 규모·성장성 | 15% | 90 | 글로벌 ESS 시장 연평균 21.7% 성장 예상 |
| 문제 해결 | 15% | 80 | 고객의 전력 공급 안정성과 비용 절감 문제 해결 |
| 지불 의사 | 10% | 75 | 전기요금 절감과 피크 수요 관리 필요성으로 지불 의사 높음 |
| 기술 차별성 | 15% | 85 | 바나듐 이온 배터리 안전성, 수명 20년+, 에너지 효율 97%+ |
| 확장성 | 10% | 80 | 재생에너지 발전소, 전기차 충전소, 산업체 등 다양한 적용 가능 |
| 수익 모델 | 10% | 70 | 매출 구조 명확하나 수익성 검증 필요 |
| 리스크 | 10% | 70 | 공급망 안정성에 대한 리스크 관리 가능 |
| 창업자 팀 | 5% | 80 | KAIST·MIT 출신 연구진, 300+ 특허 |

**투자 판정 근거:** 바나듐 이온 배터리(VIB) 기술 기반 ESS 기업. TRL 7 수준의 상용화 직전 기술력, Series C 1,225억 원 유치, 대전 구암역 실증 사례 보유. 기술적 차별성과 시장 성장 가능성이 높아 투자 가치가 있으나, 원자재 공급과 생산 비용의 변동성은 리스크 요소. **결론: 투자.**

<!-- 📸 사진: 싱글 투자 보고서 PDF 캡처 (Summary + Investment Decision 페이지) -->
<!-- 경로: outputs/single_results/investment_report_스탠다드에너지.pdf -->

---

## Results — Batch Mode

12개 스타트업을 자동 탐색·평가한 결과입니다. **투자 추천 1개 | 기각 11개.**

### 전체 비교표

| 스타트업 | 도메인 | 총점 | 판정 | SK시너지 | 시장성 | 문제해결 | 지불의사 | 기술차별 | 확장성 | 수익모델 | 리스크 | 팀 |
|---------|--------|------|------|---------|--------|---------|---------|---------|--------|---------|--------|-----|
| **스탠다드에너지** | ESS, 배터리 | **61** | **invest** | 6 | 12 | 6 | 5 | 10 | 6 | 4 | 5 | 7 |
| 휴네이트 | ESS, 배터리 관리 | 55 | reject | 6 | 12 | 5 | 5 | 8 | 5 | 4 | 4 | 6 |
| 이온어스 | 에너지 저장 | 54 | reject | 5 | 10 | 6 | 5 | 8 | 6 | 4 | 4 | 6 |
| 터빈크루 | 재생에너지 | 53 | reject | 5 | 10 | 6 | 4 | 8 | 6 | 3 | 3 | 7 |
| Hydro-Québec | 수력, 배터리 | 53 | reject | 5 | 10 | 6 | 4 | 9 | 5 | 3 | 4 | 7 |
| 플렉셀스페이스 | 태양광 | 52 | reject | 5 | 10 | 6 | 4 | 8 | 6 | 4 | 3 | 6 |
| 기가에떼 | 열에너지 저장 | 52 | reject | 5 | 10 | 6 | 4 | 8 | 5 | 4 | 4 | 6 |
| 에이에스이티 | 배터리 | 51 | reject | 6 | 10 | 5 | 4 | 8 | 5 | 4 | 3 | 6 |
| 에이티비랩 | 배터리 | 51 | reject | 5 | 10 | 6 | 4 | 8 | 5 | 4 | 3 | 6 |
| 액트이온배터리테크놀로지스 | 배터리 | 50 | reject | 5 | 10 | 5 | 4 | 8 | 5 | 4 | 3 | 6 |
| 라이온볼트 | 배터리 | 42 | reject | 5 | 8 | 5 | 4 | 5 | 5 | 3 | 3 | 4 |
| 메텍홀딩스 | 온실가스 측정 | 0 | reject | - | - | - | - | - | - | - | - | - |

### 결과 해석

**invest가 1개인 이유:**
- 실제 VC 투자 심사에서도 스크리닝 단계 통과율은 극히 낮으며, 대부분 기각되는 것이 현실
- PoC 단계에서 12개라는 제한된 표본으로 검증. 대규모 배치 시 invest 비율은 달라질 수 있음
- 점수 인플레이션 방지 로직(역방향 웹 검색 + 균일 감점)이 보수적으로 작동 → 시스템이 "다 투자하라"고 하는 것보다 신뢰도가 높음

**스탠다드에너지만 통과한 근거:**
- 기술차별성 10점(최고점) — RAG 문서의 기술 벤치마크와 대조 시 VIB 기술(TRL 7, 에너지 효율 97%+, 수명 20년+)의 우위가 입증됨
- 시장성 12점(최고점) — 글로벌 ESS 시장 CAGR 8.51% + 대규모 실증 사례
- 나머지 기업은 50~55점 구간에 밀집 → SK 시너지 부족(평균 5.1), 수익모델 미검증(평균 4.0)이 공통 감점 요인

**메텍홀딩스 0점 — 도메인 필터 정상 작동:**
- 도메인이 "온실가스 측정"으로 환경/탄소 모니터링 영역. 에너지를 생산·저장·전환하는 기업이 아님
- 도메인 체크 에이전트가 에너지 밸류체인 외의 기업을 정확히 걸러냄 → 도메인 필터가 정상 작동하고 있음을 보여주는 사례

### 항목별 횡단 분석

| 항목 | 배점 | 평균 | 득점율 | 비고 |
|------|------|------|--------|------|
| 시장 규모·성장성 | 17점 | 10.2 | 60% | 가장 높은 득점율 — 에너지 시장 자체의 성장성이 반영 |
| 기술 차별성 | 14점 | 8.0 | 57% | 기술력 있는 스타트업이 많으나, 상용화 수준에서 차이 발생 |
| 규제·리스크 | 6점 | 3.5 | 59% | 에너지 분야 특성상 규제 환경이 우호적 |
| 수익모델 | 8점 | 3.8 | 48% | **가장 낮은 득점율** — 초기 스타트업의 공통 약점 |
| SK 시너지 | 15점 | 5.3 | 35% | **배점 대비 가장 낮음** — SK 파트너십 부재가 주요 감점 요인 |

- **강한 항목 패턴**: 기술차별(7.2점) — 에너지 스타트업들이 기술적 차별성은 갖추고 있음
- **약한 항목 패턴**: SK 시너지(5.1점) — SK와의 협력 관계 부족이 전반적 감점 요인
- **에너지 스타트업 공통 시사점**: 기술적 차별성이 있지만, SK와의 시너지 부족과 시장성 불확실성이 주요 리스크

<!-- 📸 사진: 점수 분포 차트 -->
<!-- 경로: outputs/evidence_20260312_205109/score_distribution.png -->

<!-- 📸 사진: 레이더 차트 (기업별 9개 항목 비교) -->
<!-- 경로: outputs/evidence_20260312_205109/radar_chart.png -->

<!-- 📸 사진: 항목별 박스플롯 (9개 항목 분포) -->
<!-- 경로: outputs/evidence_20260312_205109/criteria_boxplot.png -->

<!-- 📸 사진: 배치 투자 보고서 PDF 캡처 (전체 비교표 + Invest 상세 + Reject 상세 + 횡단 분석 페이지) -->
<!-- 경로: outputs/batch_results/batch_summary_report_20260312_202212.pdf -->

---

## Evaluation & Validation

RAG 파이프라인의 품질과 에이전트 의사결정의 유효성을 검증했습니다.

### 1. RAGAS 프레임워크 평가 — RAG 파이프라인 품질

15개 도메인 질문(시장/정책 7개, 기술 분석 8개)에 대해 [RAGAS](https://docs.ragas.io/) 4대 메트릭을 측정했습니다.

| Metric | Score | 의미 |
|--------|-------|------|
| **Faithfulness** (충실도) | **0.9611** | 응답이 검색 문서에 근거하는 정도 (환각 최소) |
| **Response Relevancy** (응답 관련성) | **0.8371** | 응답이 질문에 적절한 정도 |
| **Context Precision** (컨텍스트 정밀도) | **0.9869** | 검색된 문서 중 실제 관련 문서 비율 |
| **Context Recall** (컨텍스트 재현율) | **1.0000** | 정답에 필요한 정보를 검색이 커버하는 정도 |

- Context Recall 1.0 — 필요한 정보를 빠짐없이 검색
- Faithfulness 0.96 — LLM이 검색된 문서에 충실하게 답변 (환각 최소화)
- Context Precision 0.99 — 검색 결과 대부분이 실제로 관련 있는 문서

<img width="921" height="430" alt="스크린샷 2026-03-13 오전 9 06 02" src="https://github.com/user-attachments/assets/950e06ce-e0bb-4803-915d-a4832aba50cd" />

<img width="873" height="234" alt="스크린샷 2026-03-13 오전 9 05 13" src="https://github.com/user-attachments/assets/3d985963-a6e0-4f64-8779-b4bc5969f58e" />


### 2. Ablation Study — RAG가 에이전트 판단에 미치는 영향

동일한 10개 스타트업을 RAG ON/OFF 조건에서 평가하여 비교했습니다.

| | RAG ON | RAG OFF |
|---|---|---|
| **평균 점수** | 52.2점 | 53.9점 |
| **점수 범위** | 42 ~ 61점 | 49 ~ 58점 |
| **Invest 판정** | **1개** (스탠다드에너지) | 0개 |
| **점수 표준편차** | 높음 (변별력 ↑) | 낮음 (균일, 변별력 ↓) |

**핵심 발견:**
- **RAG OFF**는 모든 스타트업에 비슷한 점수(49~58)를 부여 → 변별력 없음
- **RAG ON**은 도메인 벤치마크 대비 검증이 가능하여 점수 범위가 넓어짐(42~61)
- 스탠다드에너지(VRFB, TRL 6-8)만 유일하게 invest 판정 → RAG 문서의 기술 벤치마크가 정당한 가점의 근거로 작용
- RAG = "점수를 높이는 도구"가 아니라 **"변별력을 만드는 도구"**

<img width="2798" height="2337" alt="ablation_comparison_detailed" src="https://github.com/user-attachments/assets/60556d34-d8b8-4939-b834-336e3bb5154b" />


### 3. 시스템 일관성 검증

세 가지 평가 모드에서 동일한 결론이 도출되었습니다.

| 평가 모드 | 스탠다드에너지 결과 | 나머지 기업 |
|----------|-------------------|----------|
| Single Mode | **invest** (81.35점) | - |
| Batch Mode (12개) | **invest** (61점) | 전원 reject |
| Ablation RAG ON (10개) | **invest** (61점) | 전원 reject |
| Ablation RAG OFF (10개) | reject | 전원 reject |

- 스탠다드에너지만 3개 모드에서 일관되게 invest → 시스템이 특정 기업을 무작위로 올려주는 것이 아님
- RAG가 꺼지면 어떤 기업도 통과하지 못함 → RAG 근거에 기반한 **재현 가능한 판단**
- 싱글(81.35점)과 배치(61점)의 점수 차이는 배치 모드의 점수 인플레이션 방지 로직이 더 보수적으로 작동하기 때문

---

## Directory Structure

```
ai-startup-investment-agent/
├── app.py                       # CLI 엔트리포인트 (Single / Batch)
├── config.py                    # 설정 (모델, 평가기준 9개, 배치 파라미터)
├── streamlit_app.py             # Streamlit Web UI
├── agents/                      # 에이전트 모듈 (7+4 batch)
│   ├── startup_search.py        #   스타트업 프로필 수집
│   ├── domain_check.py          #   에너지 도메인 판별
│   ├── tech_analysis.py         #   기술 분석 (CRAG)
│   ├── market_policy.py         #   시장·정책 분석 (CRAG)
│   ├── competitor_analysis.py   #   경쟁사 분석
│   ├── investment_decision.py   #   9개 기준 투자 판단
│   ├── evaluation_check.py      #   평가 검증
│   ├── report_writer.py         #   8페이지 보고서 생성
│   └── batch_*.py               #   배치 전용 에이전트 (4개)
├── graph/                       # LangGraph 워크플로우
│   ├── state.py                 #   GraphState 정의
│   ├── workflow.py              #   단일 모드 그래프
│   └── batch_workflow.py        #   배치 모드 그래프
├── rag/                         # RAG 파이프라인
│   ├── retriever.py             #   FAISS 벡터스토어 빌더
│   └── corrective_rag.py        #   Corrective RAG 구현
├── prompts/                     # 프롬프트 템플릿
│   ├── templates.py             #   단일 모드 프롬프트 (495줄)
│   └── batch_templates.py       #   배치 모드 프롬프트
├── tools/
│   └── search.py                # Tavily 웹 검색 래퍼
├── scripts/
│   └── compare_embeddings.py    # 임베딩 모델 비교 스크립트
├── data/                        # RAG 문서 + FAISS 인덱스
│   ├── faiss_index/             #   사전 빌드된 벡터 인덱스
│   └── *.pdf                    #   도메인 문서 4개
├── evaluation/                  # 평가 스크립트
│   ├── ragas_eval.py            #   RAGAS 4대 메트릭 평가
│   ├── test_dataset.json        #   15개 테스트 질문
│   ├── ablation_rag_off.py      #   Ablation Study 실행
│   └── ablation_visualize.py    #   Ablation 시각화
├── docs/                        # 설계 문서 + 다이어그램
├── outputs/                     # 전체 결과 디렉토리
│   ├── single_results/          #   개별 스타트업 투자 보고서 (MD+PDF)
│   ├── batch_results/           #   배치 세션 결과 + 서머리 리포트
│   ├── embedding_comparison/    #   임베딩 모델 비교 차트 + CSV
│   ├── ragas_results/           #   RAGAS 평가 결과
│   ├── ablation_results/        #   Ablation Study 차트
│   └── evidence_*/              #   증빙자료 (차트 + 리포트)
└── requirements.txt
```

---

## Contributors

| 양정우 (PM) <br> [@mrangjw](https://github.com/mrangjw) | 박지현 <br> [@pjhyun0225](https://github.com/pjhyun0225) | 정재환 <br> [@hwnnn](https://github.com/hwnnn) | 이채연 <br> [@coduslee](https://github.com/coduslee) |
|:---:|:---:|:---:|:---:|
| <img width="150" src="https://avatars.githubusercontent.com/u/157506327?v=4"/> | <img width="150" src="https://avatars.githubusercontent.com/u/82721608?v=4"/> | <img width="150" src="https://avatars.githubusercontent.com/u/169510824?v=4"/> | <img width="150" src="https://avatars.githubusercontent.com/u/260080132?v=4"/> |
| 스타트업 탐색 에이전트<br>투자 판단 에이전트<br>Corrective RAG 파이프라인<br>평가 검증 (RAGAS + Ablation) | 기술 분석 에이전트<br>투자 보고서 생성 에이전트 | 시장·정책 분석 에이전트<br>도메인 체크 에이전트<br>프롬프트 엔지니어링 | 경쟁사 분석 에이전트<br>도메인 데이터 큐레이션 (PDF 4종)<br>Streamlit UI |
