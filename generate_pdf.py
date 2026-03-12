"""Generate SK Strategic Fit RAG PDF from markdown content."""
import re
from fpdf import FPDF


class SKReportPDF(FPDF):
    def __init__(self):
        super().__init__()
        font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
        self.add_font("gothic", "", font_path)
        self.add_font("gothic", "B", font_path)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if self.page_no() > 1:
            self.set_font("gothic", "", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 6, "SK 배터리·에너지 시너지 기준 정리본 — 전략 적합성 RAG", align="R")
            self.ln(3)
            self.set_draw_color(200, 200, 200)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("gothic", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"{self.page_no()}", align="C")

    def chapter_title(self, title, level=1):
        if level == 1:
            if self.get_y() > 40:
                self.add_page()
            self.set_font("gothic", "B", 16)
            self.set_text_color(192, 57, 43)
            self.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(192, 57, 43)
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

    def add_table(self, headers, rows):
        self.ln(2)
        col_count = len(headers)
        available = 190
        col_w = available / col_count

        # Header
        self.set_font("gothic", "B", 9)
        self.set_fill_color(44, 62, 80)
        self.set_text_color(255, 255, 255)
        for h in headers:
            self.cell(col_w, 8, h.strip(), border=1, fill=True, align="C")
        self.ln()

        # Rows
        self.set_font("gothic", "", 9)
        self.set_text_color(30, 30, 30)
        for i, row in enumerate(rows):
            if self.get_y() > 265:
                self.add_page()
            if i % 2 == 0:
                self.set_fill_color(248, 249, 250)
            else:
                self.set_fill_color(255, 255, 255)
            max_h = 8
            # Calculate needed height
            for cell in row:
                lines = len(cell.strip()) * 0.9 / (col_w - 2)
                needed = max(8, int(lines + 1) * 5)
                max_h = max(max_h, needed)
            for cell in row:
                self.cell(col_w, max_h, cell.strip().replace("**", ""), border=1, fill=True)
            self.ln()
        self.ln(3)

    def blockquote(self, text):
        self.set_fill_color(240, 240, 240)
        self.set_draw_color(192, 57, 43)
        x = self.get_x()
        y = self.get_y()
        self.set_font("gothic", "", 9)
        self.set_text_color(100, 100, 100)
        self.set_x(15)
        # Draw left border
        self.rect(12, y, 1.5, 20, "F")
        self.set_x(17)
        text = text.replace("**", "")
        self.multi_cell(175, 5, text)
        self.ln(3)

    def code_block(self, text):
        self.set_fill_color(44, 62, 80)
        self.set_font("gothic", "", 8)
        self.set_text_color(236, 240, 241)
        y_start = self.get_y()
        self.set_x(12)
        lines = text.split("\n")
        h = len(lines) * 5 + 8
        if self.get_y() + h > 270:
            self.add_page()
        self.rect(12, self.get_y(), 186, h, "F")
        self.set_xy(15, self.get_y() + 4)
        for line in lines:
            self.cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")
            self.set_x(15)
        self.ln(6)
        self.set_text_color(30, 30, 30)


def parse_table(lines, start_idx):
    """Parse markdown table starting at start_idx, return (headers, rows, end_idx)."""
    headers = [c.strip() for c in lines[start_idx].strip().split("|") if c.strip()]
    # Skip separator line
    data_start = start_idx + 2
    rows = []
    idx = data_start
    while idx < len(lines) and "|" in lines[idx] and lines[idx].strip().startswith("|"):
        cells = [c.strip() for c in lines[idx].strip().split("|") if c.strip()]
        # Pad cells if needed
        while len(cells) < len(headers):
            cells.append("")
        rows.append(cells[:len(headers)])
        idx += 1
    return headers, rows, idx


def generate_pdf():
    with open("data/sk_strategic_fit_rag.md", "r") as f:
        content = f.read()

    pdf = SKReportPDF()

    # Cover page
    pdf.add_page()
    pdf.ln(50)
    pdf.set_font("gothic", "B", 28)
    pdf.set_text_color(192, 57, 43)
    pdf.cell(0, 15, "SK 배터리·에너지 시너지", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 15, "기준 정리본", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("gothic", "", 14)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, "전략 적합성 RAG", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_font("gothic", "", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, "SK와의 시너지 및 전략적 적합성 판단 기준 제공", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, "배터리 · 전력 · LNG · 에너지솔루션 밸류체인", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)
    pdf.set_draw_color(192, 57, 43)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(10)
    pdf.set_font("gothic", "", 10)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 7, "SK 공식 발표 및 회사 소개 자료 기반", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, "공식 웹페이지 / 보도자료 / IR 자료 정리", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, "2026년 3월 기준", align="C", new_x="LMARGIN", new_y="NEXT")

    # Parse and render content
    lines = content.split("\n")
    i = 0
    in_code_block = False
    code_lines = []

    while i < len(lines):
        line = lines[i]

        # Skip the title and initial blockquote (already on cover)
        if i < 10 and (line.startswith("# SK 배터리") or line.startswith("## 전략 적합성")):
            i += 1
            continue
        if i < 10 and line.startswith(">"):
            i += 1
            continue

        # Code block
        if line.strip().startswith("```"):
            if in_code_block:
                pdf.code_block("\n".join(code_lines))
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # Headers
        if line.startswith("# ") and not line.startswith("## "):
            title = line[2:].strip()
            if title not in ["SK 배터리·에너지 시너지 기준 정리본"]:
                pdf.chapter_title(title, level=1)
            i += 1
            continue

        if line.startswith("## "):
            pdf.chapter_title(line[3:].strip(), level=2)
            i += 1
            continue

        if line.startswith("### "):
            pdf.chapter_title(line[4:].strip(), level=3)
            i += 1
            continue

        # Table
        if "|" in line and i + 1 < len(lines) and "---" in lines[i + 1]:
            headers, rows, end_idx = parse_table(lines, i)
            pdf.add_table(headers, rows)
            i = end_idx
            continue

        # Blockquote
        if line.startswith(">"):
            bq_text = line[1:].strip()
            while i + 1 < len(lines) and lines[i + 1].startswith(">"):
                i += 1
                bq_text += "\n" + lines[i][1:].strip()
            pdf.blockquote(bq_text)
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

        # Horizontal rule
        if line.strip() == "---":
            pdf.ln(3)
            pdf.set_draw_color(220, 220, 220)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(3)
            i += 1
            continue

        # Body text
        if line.strip():
            # Check for special "※" note
            if line.strip().startswith("※"):
                pdf.set_font("gothic", "", 9)
                pdf.set_text_color(150, 100, 100)
                pdf.multi_cell(0, 5, line.strip())
                pdf.ln(2)
                pdf.set_text_color(30, 30, 30)
            else:
                pdf.body_text(line.strip())

        i += 1

    output_path = "data/sk_strategic_fit_rag.pdf"
    pdf.output(output_path)
    print(f"PDF generated: {output_path}")
    print(f"Total pages: {pdf.page_no()}")


if __name__ == "__main__":
    generate_pdf()
