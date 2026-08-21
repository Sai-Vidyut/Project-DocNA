"""Generate DOCX fixtures for placement and apply tests."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.shared import Pt

FIXTURE_DIR = Path(__file__).resolve().parent


def build_blank_run(path: Path) -> None:
    doc = Document()
    p = doc.add_paragraph()
    p.add_run("Full name: ")
    p.add_run("____________________")
    doc.save(path)


def build_empty_paragraph(path: Path) -> None:
    doc = Document()
    doc.add_paragraph("Describe your experience.")
    doc.add_paragraph("")
    doc.save(path)


def build_table_answer(path: Path) -> None:
    doc = Document()
    table = doc.add_table(rows=2, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "Question"
    table.rows[0].cells[1].text = "Answer"
    table.rows[1].cells[0].text = "Name?"
    table.rows[1].cells[1].text = ""
    doc.save(path)


def build_numbered_question(path: Path) -> None:
    doc = Document()
    doc.add_paragraph("Question A?", style="List Number")
    doc.add_paragraph("Question B?", style="List Number")
    doc.add_paragraph("Question C?", style="List Number")
    doc.save(path)


def build_nested_questions(path: Path) -> None:
    doc = Document()
    doc.add_paragraph("Explain OOP.")
    doc.add_paragraph("a) Explain inheritance.")
    doc.add_paragraph("b) Explain polymorphism.")
    doc.save(path)


def build_already_answered(path: Path) -> None:
    doc = Document()
    doc.add_paragraph("What is your role?")
    doc.add_paragraph("Answer: Manager")
    doc.save(path)


def build_overflow_answer(path: Path) -> None:
    doc = Document()
    p = doc.add_paragraph()
    p.add_run("Short blank: ")
    p.add_run("____")
    doc.save(path)


def build_multiple_answers(path: Path) -> None:
    doc = Document()
    doc.add_paragraph("Provide a detailed summary.")
    doc.add_paragraph("")
    doc.save(path)


def build_formatting_preservation(path: Path) -> None:
    doc = Document()
    p = doc.add_paragraph("Bold question?")
    for run in p.runs:
        run.bold = True
        run.font.size = Pt(14)
    doc.add_paragraph("")
    doc.save(path)


def build_multi_segment_shared_space(path: Path) -> None:
    doc = Document()
    doc.add_paragraph(
        "Describe your role. Explain your responsibilities. List your main achievements."
    )
    doc.add_paragraph("")
    doc.save(path)


def build_placement_integration(path: Path) -> None:
    doc = Document()
    doc.add_heading("Placement Integration", level=1)
    doc.add_paragraph("Complete all fields.")

    p1 = doc.add_paragraph()
    p1.add_run("1. What is your name? ")
    p1.add_run("________")

    doc.add_paragraph("2. Describe your organization.")
    doc.add_paragraph("")

    doc.add_paragraph("3. What is your role?")
    doc.add_paragraph("Answer: Manager")

    doc.add_paragraph("4. Do not complete section D.")

    doc.add_paragraph("a) What is inheritance?")
    doc.add_paragraph("b) What is polymorphism?")

    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Country"
    table.rows[0].cells[1].text = "Capital"
    table.rows[1].cells[0].text = "France"
    table.rows[1].cells[1].text = ""

    doc.add_paragraph("5. Explain encapsulation with no blank below.", style="List Number")
    doc.save(path)


def main() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    builders = {
        "blank_run.docx": build_blank_run,
        "empty_paragraph.docx": build_empty_paragraph,
        "table_answer.docx": build_table_answer,
        "numbered_question.docx": build_numbered_question,
        "nested_questions.docx": build_nested_questions,
        "already_answered.docx": build_already_answered,
        "overflow_answer.docx": build_overflow_answer,
        "multiple_answers.docx": build_multiple_answers,
        "formatting_preservation.docx": build_formatting_preservation,
        "multi_segment_shared_space.docx": build_multi_segment_shared_space,
        "placement_integration.docx": build_placement_integration,
    }
    for filename, builder in builders.items():
        builder(FIXTURE_DIR / filename)
        print(f"Wrote {filename}")


if __name__ == "__main__":
    main()
