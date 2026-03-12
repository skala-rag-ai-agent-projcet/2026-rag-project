"""Generate Energy Storage Benchmark RAG PDF from markdown content."""
import re
from fpdf import FPDF


class BenchmarkPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("gothic", "", "/tmp/NanumGothic-Regular.ttf")
        self.add_font("gothic", "B", "/tmp/NanumGothic-Bold.ttf")
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if self.page_no() > 1:
            self.set_font("gothic", "", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 6, "[2026 Energy Storage Technical Benchmark & RAG Reference Guide] - CONFIDENTIAL", align="R")
            self.ln(3)
            self.set_draw_color(200, 200, 200)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("gothic", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Technical Analyst Reference | Page {self.page_no()}", align="C")

    def chapter_title(self, title, level=1):
        if level == 1:
            if self.get_y() > 40:
                self.add_page()
            self.set_font("gothic", "B", 16)
            self.set_text_color(41, 128, 185)
            self.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(41, 128, 185)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(6)
        elif level == 2:
            self.ln(4)
            self.set_font("gothic", "B", 13)
            self.set_text_color(44, 62, 80)
            self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(189, 195, 199)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(4)
        elif level == 3:
            self.ln(3)
            self.set_font("gothic", "B", 11)
            self.set_text_color(52, 73, 94)
            self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

    def body_text(self, text):
        self.set_font("gothic", "", 10)
        self.set_text_color(30, 30, 30)
        text = text.replace("**", "")
        self.multi_cell(0, 6, text)
        self.ln(2)

    def bullet_item(self, text, indent=0):
        self.set_font("gothic", "", 10)
        self.set_text_color(30, 30, 30)
        x = 15 + indent * 5
        self.set_x(x)
        text = text.replace("**", "")
        self.cell(5, 6, "•")
        self.multi_cell(0, 6, text)
        self.ln(1)

    def numbered_item(self, num, text, indent=0):
        self.set_font("gothic", "", 10)
        self.set_text_color(30, 30, 30)
        x = 15 + indent * 5
        self.set_x(x)
        text = text.replace("**", "")
        self.cell(8, 6, f"{num}.")
        self.multi_cell(0, 6, text)
        self.ln(1)

    def blockquote(self, text):
        self.set_fill_color(240, 240, 240)
        self.set_draw_color(41, 128, 185)
        y = self.get_y()
        self.set_font("gothic", "", 9)
        self.set_text_color(100, 100, 100)
        self.set_x(15)
        self.rect(12, y, 1.5, 20, "F")
        self.set_x(17)
        text = text.replace("**", "")
        self.multi_cell(175, 5, text)
        self.ln(3)

    def tech_block(self, text):
        """Render [기술군: ...] blocks with special styling."""
        self.set_fill_color(236, 240, 241)
        self.set_font("gothic", "B", 10)
        self.set_text_color(41, 128, 185)
        self.set_x(12)
        self.cell(186, 8, text, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)


def generate_benchmark_pdf():
    with open("data/energy_storage_benchmark_2026.md", "r") as f:
        content = f.read()

    pdf = BenchmarkPDF()

    # Cover page
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font("gothic", "B", 24)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 15, "2026 에너지 저장 기술 심사 및", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 15, "RAG 데이터 벤치마크 가이드북", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_font("gothic", "", 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, "[RAG 최적화 버전: 텍스트 위주 구성]", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, "(Energy Transition / Next-Gen Infrastructure)", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(15)
    pdf.set_font("gothic", "", 10)
    pdf.cell(0, 7, "본 문서는 스타트업 기술력 평가 시 '홈페이지, 논문, 특허' 데이터와 대조하기 위한", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, "글로벌 및 국내 표준 기술 지표를 텍스트 구조로 제공합니다.", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, "VectorDB 저장을 고려하여 표 형식을 배제하고 섹션 단위로 구성되었습니다.", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)
    pdf.set_draw_color(41, 128, 185)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(10)
    pdf.set_font("gothic", "", 10)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 7, "발행일: 2026년 03월 12일", align="C", new_x="LMARGIN", new_y="NEXT")

    # Parse and render content
    lines = content.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Skip the title and initial blockquote (already on cover)
        if i < 12 and (line.startswith("# 2026 에너지") or line.startswith("> ")):
            i += 1
            continue

        # Headers
        if line.startswith("## ") and not line.startswith("### "):
            pdf.chapter_title(line[3:].strip(), level=2)
            i += 1
            continue

        if line.startswith("### "):
            pdf.chapter_title(line[4:].strip(), level=3)
            i += 1
            continue

        # Tech block headers [기술군: ...]
        if line.strip().startswith("[기술군:") or line.strip().startswith("[미국 시장") or line.strip().startswith("[유럽 시장") or line.strip().startswith("[한국 시장"):
            pdf.tech_block(line.strip())
            i += 1
            continue

        # Horizontal rule
        if line.strip() == "---":
            pdf.ln(3)
            pdf.set_draw_color(220, 220, 220)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(3)
            i += 1
            continue

        # Numbered list
        num_match = re.match(r"^(\d+)\.\s+(.*)", line.strip())
        if num_match:
            pdf.numbered_item(num_match.group(1), num_match.group(2))
            i += 1
            continue

        # Bullet
        if line.strip().startswith("- "):
            text = line.strip()[2:]
            indent = (len(line) - len(line.lstrip())) // 2
            pdf.bullet_item(text, indent)
            i += 1
            continue

        # Body text
        if line.strip():
            if line.strip().startswith("※"):
                pdf.set_font("gothic", "", 9)
                pdf.set_text_color(150, 100, 100)
                pdf.multi_cell(0, 5, line.strip())
                pdf.ln(2)
                pdf.set_text_color(30, 30, 30)
            else:
                pdf.body_text(line.strip())

        i += 1

    output_path = "data/energy_storage_benchmark_2026.pdf"
    pdf.output(output_path)
    print(f"PDF generated: {output_path}")
    print(f"Total pages: {pdf.page_no()}")


if __name__ == "__main__":
    generate_benchmark_pdf()
