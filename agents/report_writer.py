import os
import json
import markdown

# weasyprint가 brew 라이브러리를 찾을 수 있도록 경로 설정
if not os.environ.get("DYLD_FALLBACK_LIBRARY_PATH"):
    os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = "/opt/homebrew/lib"

from langchain_openai import ChatOpenAI
from prompts.templates import REPORT_WRITER_PROMPT
from config import LLM_MODEL, OUTPUT_DIR


def report_writer_node(state: dict) -> dict:
    """8장 구조 투자 보고서 생성 (Markdown → HTML → PDF)."""
    profile = state.get("startup_profile", {})
    name = profile.get("company_name", "Unknown")

    print(f"\n[보고서 생성] {name} 투자 보고서 작성 중...")

    tech = state.get("tech_analysis", {})
    market = state.get("market_policy_analysis", {})
    competitor = state.get("competitor_analysis", {})
    criteria_scores = state.get("criteria_scores", {})
    weighted_score = state.get("weighted_score", 0.0)
    verdict = state.get("verdict", "hold")
    memo = state.get("investment_memo", "")
    refs = state.get("references", []) + state.get("sources", [])

    investment_decision = json.dumps(
        {
            "criteria_scores": criteria_scores,
            "weighted_score": weighted_score,
            "verdict": verdict,
            "investment_memo": memo,
        },
        ensure_ascii=False,
        indent=2,
    )

    tech_str = json.dumps(tech, ensure_ascii=False, indent=2) if isinstance(tech, dict) else str(tech)
    market_str = json.dumps(market, ensure_ascii=False, indent=2) if isinstance(market, dict) else str(market)
    competitor_str = json.dumps(competitor, ensure_ascii=False, indent=2) if isinstance(competitor, dict) else str(competitor)
    refs_str = "\n".join(f"- {r}" for r in refs) if refs else "(출처 없음)"

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0.2)
    prompt = REPORT_WRITER_PROMPT.format(
        startup_profile=json.dumps(profile, ensure_ascii=False, indent=2),
        tech_analysis=tech_str,
        market_policy_analysis=market_str,
        competitor_analysis=competitor_str,
        investment_decision=investment_decision,
        references=refs_str,
    )

    response = llm.invoke(prompt)
    report_md = response.content.strip()

    # Markdown 저장
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    md_path = os.path.join(OUTPUT_DIR, f"investment_report_{name}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"[보고서 생성] Markdown 저장: {md_path}")

    # PDF 변환
    pdf_path = os.path.join(OUTPUT_DIR, f"investment_report_{name}.pdf")
    try:
        from weasyprint import HTML

        html_content = markdown.markdown(
            report_md,
            extensions=["tables", "fenced_code"],
        )
        styled_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
            margin: 40px;
            line-height: 1.6;
            font-size: 11pt;
            color: #1a202c;
        }}
        h1 {{
            color: #1a365d;
            border-bottom: 2px solid #1a365d;
            padding-bottom: 8px;
            font-size: 20pt;
            margin-top: 30px;
        }}
        h2 {{
            color: #2d3748;
            font-size: 15pt;
            margin-top: 24px;
        }}
        h3 {{
            color: #4a5568;
            font-size: 13pt;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 16px 0;
        }}
        th, td {{
            border: 1px solid #cbd5e0;
            padding: 8px 12px;
            text-align: left;
        }}
        th {{
            background-color: #edf2f7;
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background-color: #f7fafc;
        }}
        blockquote {{
            border-left: 4px solid #4299e1;
            padding-left: 16px;
            color: #4a5568;
            margin: 16px 0;
        }}
        code {{
            background-color: #edf2f7;
            padding: 2px 6px;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""
        HTML(string=styled_html).write_pdf(pdf_path)
        print(f"[보고서 생성] PDF 저장: {pdf_path}")
    except Exception as e:
        print(f"[보고서 생성] PDF 변환 실패: {e}")
        print(f"[보고서 생성] Markdown 보고서만 저장됨: {md_path}")
        pdf_path = md_path

    return {
        "investment_report": pdf_path,
        "log": [f"보고서 생성 완료: {pdf_path}"],
    }
