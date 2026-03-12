import json
from langchain_openai import ChatOpenAI
from prompts.templates import DOMAIN_CHECK_PROMPT
from config import LLM_MODEL


def domain_check_node(state: dict) -> dict:
    """스타트업의 Energy 도메인 해당 여부 판별."""
    profile = state.get("startup_profile", {})
    company_name = profile.get("company_name", "Unknown")

    print(f"\n[도메인 확인] {company_name} — Energy 도메인 여부 확인 중...")

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
    prompt = DOMAIN_CHECK_PROMPT.format(
        startup_profile=json.dumps(profile, ensure_ascii=False, indent=2)
    )

    response = llm.invoke(prompt)
    content = response.content.strip()

    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        print("[도메인 확인] JSON 파싱 실패. 도메인 부적합으로 처리.")
        result = {"is_energy_domain": False, "reason": "판별 실패", "sub_domain": "N/A"}

    is_fit = result.get("is_energy_domain", False)
    reason = result.get("reason", "")

    print(f"[도메인 확인] Energy 도메인: {'✓ 적합' if is_fit else '✗ 부적합'}")
    print(f"  사유: {reason}")

    return {
        "domain_fit": is_fit,
        "domain_fit_reason": reason,
        "log": [f"도메인 확인: {'적합' if is_fit else '부적합'} — {reason}"],
    }
