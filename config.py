import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

LLM_MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "BAAI/bge-m3"

FAISS_INDEX_PATH = os.path.join(os.path.dirname(__file__), "data", "faiss_index")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
SINGLE_RESULTS_DIR = os.path.join(OUTPUT_DIR, "single_results")
RAGAS_RESULTS_DIR = os.path.join(OUTPUT_DIR, "ragas_results")
ABLATION_RESULTS_DIR = os.path.join(OUTPUT_DIR, "ablation_results")

INVESTMENT_THRESHOLD = 60.0

DOMAIN = "Energy"
DOMAIN_DETAIL = "Energy Transition / Next-Gen Energy Infrastructure (배터리·ESS 중심)"

# 9개 투자 판단 기준 (가중합 = 100%)
EVALUATION_CRITERIA = {
    "sk_synergy": {
        "name": "SK 사업 시너지",
        "weight": 0.15,
        "source": "SK 공식 전략자료 + 과제 목적 반영 커스텀",
        "points": "배터리, LNG, 전력, 에너지솔루션, 소재 밸류체인과의 연결성 / 기존 계열사와 공동사업 가능성 / 기술 내재화 가능성 / 전략적 확장성",
        "evaluation_question": "이 스타트업의 기술/사업이 SK 에너지 밸류체인(배터리·LNG·전력·소재)과 직접 연결되는가?",
        "input_data": ["domain_classification", "technology_analysis", "company_profile"],
        "scoring_rubric": {
            "high": "SK 계열사와 공동사업 즉시 가능, 기술 내재화 용이, 기존 밸류체인 직접 보완",
            "medium": "간접적 연결성 있으나 추가 개발/조정 필요, 잠재적 시너지",
            "low": "SK 에너지 밸류체인과 무관하거나 연결 근거 미약",
        },
    },
    "market_size_growth": {
        "name": "시장 규모·성장성",
        "weight": 0.17,
        "source": "Bessemer + Scorecard Method",
        "points": "TAM/SAM/SOM 규모 / 글로벌 확장 가능성 / 에너지 전환·정책 변화에 따른 성장성 / 대형 사업으로 발전 가능성",
        "evaluation_question": "이 스타트업이 목표하는 시장의 TAM/SAM 규모와 성장 전망은 어떠한가?",
        "input_data": ["market_policy_analysis"],
        "scoring_rubric": {
            "high": "TAM $10B+, CAGR 20%+, 에너지 전환 정책과 직결되는 핵심 시장",
            "medium": "TAM $1-10B, CAGR 10-20%, 성장 동인 존재하나 불확실성 있음",
            "low": "TAM $1B 미만이거나 성장성 제한적, 니치 시장",
        },
    },
    "problem_solving": {
        "name": "문제 해결력 / 고객 가치",
        "weight": 0.10,
        "source": "Bessemer Checklist",
        "points": "고객 pain point의 명확성 / 기존 방식 대비 개선 정도 / 필수성 / 도입 필요성",
        "evaluation_question": "이 스타트업이 해결하는 고객 pain point가 얼마나 명확하고 시급한가?",
        "input_data": ["market_policy_analysis", "technology_analysis"],
        "scoring_rubric": {
            "high": "명확한 pain point, 기존 대비 10배+ 개선, 필수 도입 수준",
            "medium": "pain point 존재하나 개선 폭 제한적이거나 대안 존재",
            "low": "pain point 불명확하거나 nice-to-have 수준",
        },
    },
    "willingness_to_pay": {
        "name": "고객 지불 의사",
        "weight": 0.08,
        "source": "Bessemer Checklist",
        "points": "비용 절감, 효율 향상, 규제 대응, 생산성 향상 등 ROI / 유료 PoC·계약 여부 / 지불 전환 가능성",
        "evaluation_question": "고객이 이 솔루션에 실제로 비용을 지불할 의사가 확인되는가?",
        "input_data": ["market_policy_analysis"],
        "scoring_rubric": {
            "high": "유료 PoC/계약 확보, 명확한 ROI 수치, 규제 의무에 의한 도입",
            "medium": "ROI 존재하나 검증 중, 일부 유료 전환 사례",
            "low": "지불 의사 미검증, ROI 불명확, 무료 시범 단계",
        },
    },
    "tech_differentiation": {
        "name": "기술 차별성·상용화 수준",
        "weight": 0.14,
        "source": "Bessemer + Scorecard Method",
        "points": "성능·효율·안정성·가격 우위 / PoC·파일럿·상용화 단계 / 기술 신뢰성 / 모방 난이도 / 특허·노하우",
        "evaluation_question": "이 스타트업의 기술이 경쟁사 대비 차별적이고 상용화에 근접해 있는가?",
        "input_data": ["technology_analysis", "competition_analysis"],
        "scoring_rubric": {
            "high": "TRL 7+, 핵심 특허 보유, 성능 우위 명확, 모방 난이도 높음",
            "medium": "TRL 5-6, 일부 차별성 있으나 추가 검증 필요",
            "low": "TRL 4 이하, 차별성 불명확, 다수 경쟁자 존재",
        },
    },
    "scalability": {
        "name": "확장성 / 업사이드",
        "weight": 0.10,
        "source": "Bessemer Checklist",
        "points": "지역 확장성 / 산업 확장성 / 플랫폼화 가능성 / 장기 성장 잠재력 / 특정 고객 의존도",
        "evaluation_question": "이 스타트업의 사업이 지역/산업 확장이 가능한 구조인가?",
        "input_data": ["market_policy_analysis", "technology_analysis"],
        "scoring_rubric": {
            "high": "글로벌 확장 가능, 다산업 적용, 플랫폼화 가능 구조",
            "medium": "일부 지역/산업 확장 가능하나 제약 존재",
            "low": "특정 고객/지역 의존, 확장 구조 미비",
        },
    },
    "revenue_model": {
        "name": "수익모델·단위경제성",
        "weight": 0.08,
        "source": "Bessemer + 일반 VC 실사",
        "points": "매출 구조의 명확성 / 반복매출 여부 / 매출총이익률 / 회수기간 / 설치·운영 단위당 채산성",
        "evaluation_question": "수익 구조가 명확하고 단위경제성이 검증되었는가?",
        "input_data": ["market_policy_analysis"],
        "scoring_rubric": {
            "high": "반복매출 구조, 매출총이익률 50%+, 회수기간 명확, 실매출 발생",
            "medium": "매출 구조 있으나 수익성 미검증, 파일럿 매출 단계",
            "low": "매출 구조 불명확, 수익 발생 미시작",
        },
    },
    "risk": {
        "name": "규제·운영·법률 리스크",
        "weight": 0.06,
        "source": "Bessemer Checklist",
        "points": "인허가·인증 필요성 / 안전 규제 / 공급망 리스크 / 운영 복잡도 / 법적 분쟁 가능성 / 대체기술 리스크",
        "evaluation_question": "규제·운영·법률 리스크가 사업 지속에 치명적인가? (높은 점수 = 리스크 낮음)",
        "input_data": ["market_policy_analysis", "technology_analysis"],
        "scoring_rubric": {
            "high": "리스크 최소: 인허가 확보, 공급망 안정, 규제 준수 완료",
            "medium": "관리 가능한 리스크: 인허가 진행 중, 일부 불확실성",
            "low": "리스크 심각: 인허가 불확실, 규제 충돌 가능성, 공급망 취약",
        },
    },
    "founder_team": {
        "name": "창업자·팀의 질 / 장기 몰입도",
        "weight": 0.12,
        "source": "Bessemer + Scorecard Method",
        "points": "산업 전문성 / 기술·사업 균형 / 실행력 / 핵심 인력 구성 / 장기 비전 / 몰입 의지",
        "evaluation_question": "창업자와 팀이 이 사업을 성공시킬 역량과 몰입도를 갖추었는가?",
        "input_data": ["company_profile"],
        "scoring_rubric": {
            "high": "산업 10년+ 전문성, 기술+사업 겸비, 핵심인력 충분, 풀타임 몰입",
            "medium": "관련 경험 있으나 일부 역량 공백, 팀 보강 필요",
            "low": "산업 경험 부족, 핵심 인력 미확보, 몰입 불확실",
        },
    },
}

# Batch mode: 항목별 만점 (weight * 100)
EVALUATION_MAX_SCORES = {key: int(info["weight"] * 100) for key, info in EVALUATION_CRITERIA.items()}

# Batch mode: 도메인 부적합 비율 임계값 (초과 시 쿼리 재작성 + 재탐색)
BATCH_DOMAIN_REJECTION_THRESHOLD = 0.5

# Batch mode: 병렬 실행 동시 실행 수
BATCH_MAX_CONCURRENCY = 3

# Batch mode: 청크 크기 (한 번에 병렬 실행할 스타트업 수)
BATCH_CHUNK_SIZE = 3

# Batch mode: 전체 배치 타임아웃 (초)
BATCH_TOTAL_TIMEOUT = 900  # 15분 (10개 평가 + rate limit 여유)

# Batch mode: 개별 스타트업 타임아웃 (초)
BATCH_PER_STARTUP_TIMEOUT = 60

# Batch mode: 결과 저장 디렉토리
BATCH_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "outputs", "batch_results")

# Batch mode: 고정 평가 개수
BATCH_FIXED_COUNT = 12
