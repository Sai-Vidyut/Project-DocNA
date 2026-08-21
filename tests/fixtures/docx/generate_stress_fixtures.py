"""Generate Phase 12 real-world stress-test DOCX fixtures.

These documents are intentionally harder than the curated realworld corpus.
They combine multiple structural and formatting characteristics found in
documents users might upload without designing them for DocNA.
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_BREAK, WD_UNDERLINE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

FIXTURE_DIR = Path(__file__).resolve().parent / "stress"


def _blank(doc: Document) -> None:
    doc.add_paragraph("")


def _underline_blank(doc: Document, label: str = "", width: int = 30) -> None:
    p = doc.add_paragraph()
    if label:
        p.add_run(f"{label} ")
    run = p.add_run("_" * width)
    run.underline = True


def _add_header_footer(doc: Document, header_text: str, footer_text: str) -> None:
    section = doc.sections[0]
    section.header.paragraphs[0].text = header_text
    section.footer.paragraphs[0].text = footer_text


def _shade_cell(cell, fill: str = "D9E2F3") -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def build_grant_proposal_messy(path: Path) -> None:
    doc = Document()
    doc.add_heading("Community Arts Grant Proposal", level=1)
    doc.add_paragraph(
        "Instructions: Complete every numbered item. Use black ink. "
        "Do not attach supplementary materials unless requested."
    )
    doc.add_heading("Project Overview", level=2)
    doc.add_paragraph("1. Summarize the project in one sentence.", style="List Number")
    _blank(doc)
    doc.add_paragraph("2. Describe target beneficiaries.", style="List Number")
    doc.add_paragraph("a) Primary audience", style="List Number 2")
    _blank(doc)
    doc.add_paragraph("b) Secondary audience", style="List Number 2")
    _underline_blank(doc, "Estimated reach:")
    p = doc.add_paragraph()
    run = p.add_run("3. Why is this project urgent?")
    run.bold = True
    run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
    _blank(doc)
    _blank(doc)
    doc.save(path)


def build_hr_onboarding_underlines(path: Path) -> None:
    doc = Document()
    doc.add_heading("Employee Onboarding Packet", level=1)
    doc.add_paragraph("Complete all fields on your first day.")
    p1 = doc.add_paragraph()
    p1.add_run("Legal name: ")
    r1 = p1.add_run("______________________________")
    r1.underline = True
    doc.add_paragraph("State your preferred pronouns")
    _underline_blank(doc)
    doc.add_paragraph("Answer:")
    _underline_blank(doc, width=40)
    doc.add_paragraph("List emergency contact name and phone")
    _blank(doc)
    p2 = doc.add_paragraph()
    r2 = p2.add_run("Describe any workplace accommodations needed")
    r2.italic = True
    _blank(doc)
    doc.save(path)


def build_clinical_intake_merged(path: Path) -> None:
    doc = Document()
    doc.add_heading("Patient Intake Form", level=1)
    doc.add_paragraph("Complete shaded cells only. Leave N/A where appropriate.")
    table = doc.add_table(rows=4, cols=3)
    table.style = "Table Grid"
    table.rows[0].cells[0].merge(table.rows[0].cells[2])
    table.rows[0].cells[0].text = "Demographics — fill all fields below"
    _shade_cell(table.rows[0].cells[0])
    labels = ["Date of visit", "Primary complaint", "Current medications"]
    for idx, label in enumerate(labels, start=1):
        table.rows[idx].cells[0].text = label
        _shade_cell(table.rows[idx].cells[1])
        table.rows[idx].cells[2].text = "Notes"
    doc.add_paragraph("Describe symptom onset and duration")
    _blank(doc)
    doc.save(path)


def build_legal_deposition_long(path: Path) -> None:
    doc = Document()
    doc.add_heading("Deposition Worksheet", level=1)
    doc.add_paragraph(
        "Provide detailed responses. If a question does not apply, write N/A."
    )
    doc.add_paragraph(
        "Explain in full detail the sequence of events on the date in question, "
        "including all persons present, communications exchanged, and documents reviewed."
    )
    _blank(doc)
    doc.add_paragraph("State whether you reviewed Exhibit A prior to signing")
    _blank(doc)
    doc.add_paragraph("Identify all individuals with knowledge of the contract terms")
    doc.add_paragraph("Describe any amendments discussed after execution")
    doc.add_paragraph("List every email thread referenced in paragraph 12")
    _blank(doc)
    doc.save(path)


def build_course_syllabus_breaks(path: Path) -> None:
    doc = Document()
    doc.add_heading("Midterm Study Guide", level=1)
    doc.add_paragraph("Answer each item before the review session.")
    doc.add_paragraph("1. Define polymorphism.", style="List Number")
    _blank(doc)
    doc.add_paragraph("2. Compare stack vs heap allocation.", style="List Number")
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    doc.add_heading("Part II — Systems", level=2)
    doc.add_paragraph("3. Explain cache locality.", style="List Number")
    doc.add_paragraph("a) Temporal locality", style="List Number 2")
    _blank(doc)
    doc.add_paragraph("Note: Part II examples will not be collected.")
    doc.add_paragraph("4. When should you prefer mmap over read()", style="List Number")
    _blank(doc)
    doc.save(path)


def build_research_survey_dense(path: Path) -> None:
    doc = Document()
    doc.add_heading("Research Participant Survey", level=1)
    doc.add_paragraph(
        "What is your age range and how many years have you worked in research "
        "administration — please answer both parts."
    )
    _blank(doc)
    doc.add_paragraph("Example response format: 35-44; 8 years.")
    doc.add_paragraph("How often do you use statistical software")
    doc.add_paragraph("Which tools have you used in the last 12 months")
    doc.add_paragraph("Describe challenges recruiting diverse participants")
    _blank(doc)
    doc.save(path)


def build_it_security_audit_form(path: Path) -> None:
    doc = Document()
    doc.add_heading("Quarterly Security Audit", level=1)
    doc.add_paragraph("Document controls for each domain.")
    doc.add_paragraph("Access control", style="List Number")
    doc.add_paragraph("List all privileged accounts", style="List Number 2")
    _blank(doc)
    doc.add_paragraph("Patch management", style="List Number")
    doc.add_paragraph("State mean time to patch critical CVEs", style="List Number 2")
    table = doc.add_table(rows=3, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "Control"
    table.rows[0].cells[1].text = "Evidence"
    table.rows[1].cells[0].text = "MFA enrollment rate"
    table.rows[1].cells[1].text = ""
    _shade_cell(table.rows[1].cells[1], "FFF2CC")
    table.rows[2].cells[0].text = "Last penetration test date"
    table.rows[2].cells[1].text = ""
    p = doc.add_paragraph()
    r = p.add_run("Summarize outstanding critical findings")
    r.bold = True
    r.font.size = Pt(14)
    _blank(doc)
    doc.save(path)


def build_volunteer_mixed_completion(path: Path) -> None:
    doc = Document()
    doc.add_heading("Volunteer Registration", level=1)
    doc.add_paragraph("Update any blank fields.")
    doc.add_paragraph("Volunteer ID?")
    doc.add_paragraph("Answer: VOL-22017")
    doc.add_paragraph("Primary phone number?")
    doc.add_paragraph("Answer:")
    _blank(doc)
    doc.add_paragraph("Preferred volunteer shift?")
    _blank(doc)
    doc.add_paragraph("Background check completed?")
    doc.add_paragraph("Answer: Yes — 2025-11-02")
    doc.save(path)


def build_performance_review_runs(path: Path) -> None:
    doc = Document()
    doc.add_heading("Annual Performance Review", level=1)
    p1 = doc.add_paragraph()
    r1 = p1.add_run("Goal 1: ")
    r1.bold = True
    p1.add_run("Describe progress on the revenue target.")
    _blank(doc)
    p2 = doc.add_paragraph()
    r2 = p2.add_run("Goal 2: ")
    r2.bold = True
    r2.font.italic = True
    p2.add_run("Summarize leadership initiatives.")
    _blank(doc)
    p3 = doc.add_paragraph()
    p3.add_run("List ")
    r3 = p3.add_run("three measurable")
    r3.bold = True
    p3.add_run(" outcomes from Q3.")
    _blank(doc)
    doc.save(path)


def build_construction_rfp_tables(path: Path) -> None:
    doc = Document()
    doc.add_heading("Construction RFP Response", level=1)
    doc.add_paragraph("Provide pricing and methodology.")
    doc.add_paragraph("Site preparation", style="List Number")
    doc.add_paragraph("a) Mobilization plan", style="List Number 2")
    _blank(doc)
    doc.add_paragraph("b) Disposal requirements", style="List Number 2")
    table = doc.add_table(rows=3, cols=3)
    table.style = "Table Grid"
    for col, header in enumerate(["Line item", "Unit cost", "Notes"]):
        table.rows[0].cells[col].text = header
    table.rows[1].cells[0].text = "Concrete pour"
    table.rows[2].cells[0].text = "Steel erection"
    doc.add_paragraph("Describe your safety record for the last five years in detail.")
    _blank(doc)
    _blank(doc)
    doc.save(path)


def build_newsletter_with_header(path: Path) -> None:
    doc = Document()
    _add_header_footer(doc, "INTERNAL NEWSLETTER — DO NOT DISTRIBUTE", "Page footer text")
    doc.add_heading("Reader Feedback Form", level=1)
    doc.add_paragraph("What topic should we cover next month")
    doc.add_paragraph("Which section was most useful")
    doc.add_paragraph("Rate overall readability from 1-5")
    _underline_blank(doc, "Comments:")
    doc.save(path)


def build_medical_history_shaded(path: Path) -> None:
    doc = Document()
    doc.add_heading("Medical History Update", level=1)
    table = doc.add_table(rows=3, cols=4)
    table.style = "Table Grid"
    table.rows[0].cells[0].merge(table.rows[0].cells[1])
    table.rows[0].cells[0].text = "Condition history"
    table.rows[0].cells[2].text = "Year diagnosed"
    table.rows[0].cells[3].text = "Treating physician"
    table.rows[1].cells[0].text = "Hypertension"
    table.rows[1].cells[1].text = ""
    table.rows[2].cells[0].text = "Asthma"
    table.rows[2].cells[1].text = ""
    for row in table.rows[1:]:
        _shade_cell(row.cells[1], "E2EFDA")
    doc.add_paragraph("List current allergies and reactions")
    _blank(doc)
    doc.add_paragraph("Describe family history of cardiac disease")
    _blank(doc)
    doc.save(path)


def build_internship_multibreak(path: Path) -> None:
    doc = Document()
    doc.add_heading("Internship Application", level=1)
    doc.add_paragraph("Complete both sections.")
    doc.add_paragraph("Section A — Background")
    p = doc.add_paragraph()
    p.add_run("University: ")
    p.add_run("________________")
    doc.add_paragraph("Expected graduation term")
    _blank(doc)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    doc.add_heading("Section B — Experience", level=2)
    doc.add_paragraph("Describe your most relevant internship or project")
    _blank(doc)
    _blank(doc)
    doc.save(path)


def build_debate_worksheet(path: Path) -> None:
    doc = Document()
    doc.add_heading("Debate Preparation Worksheet", level=1)
    doc.add_paragraph("Complete arguments for your assigned side only.")
    doc.add_paragraph("1. State your thesis.", style="List Number")
    _blank(doc)
    doc.add_paragraph("Example thesis: Renewable energy lowers long-term costs.")
    doc.add_paragraph("2. Provide two supporting points.", style="List Number")
    _blank(doc)
    doc.add_paragraph("3. Anticipate one counterargument.", style="List Number")
    _blank(doc)
    doc.add_paragraph("Do not copy the example thesis into your answer.")
    doc.save(path)


def build_budget_forecast_cells(path: Path) -> None:
    doc = Document()
    doc.add_heading("Budget Forecast Worksheet", level=1)
    doc.add_paragraph("Enter figures in yellow cells.")
    table = doc.add_table(rows=4, cols=3)
    table.style = "Table Grid"
    headers = ["Category", "Q1", "Q2"]
    for col, header in enumerate(headers):
        table.rows[0].cells[col].text = header
    rows = [("Personnel", "", ""), ("Software", "", ""), ("Travel", "", "")]
    for row_index, (label, q1, q2) in enumerate(rows, start=1):
        table.rows[row_index].cells[0].text = label
        table.rows[row_index].cells[1].text = q1
        table.rows[row_index].cells[2].text = q2
        _shade_cell(table.rows[row_index].cells[1], "FFF2CC")
        _shade_cell(table.rows[row_index].cells[2], "FFF2CC")
    doc.add_paragraph("Explain major variances from prior quarter")
    _blank(doc)
    doc.save(path)


def build_interview_no_blanks(path: Path) -> None:
    doc = Document()
    doc.add_heading("Panel Interview Notes", level=1)
    doc.add_paragraph("Candidate responses:")
    doc.add_paragraph("Describe a complex project you led")
    doc.add_paragraph("How do you prioritize conflicting deadlines")
    doc.add_paragraph("Tell us about a failure and what you learned")
    doc.add_paragraph("Why this organization")
    doc.add_paragraph("Questions for the panel")
    _blank(doc)
    doc.save(path)


def build_policy_partial_answers(path: Path) -> None:
    doc = Document()
    doc.add_heading("Policy Acknowledgment", level=1)
    doc.add_paragraph("Confirm each statement.")
    doc.add_paragraph("Have you read the code of conduct?")
    doc.add_paragraph("Answer: Yes")
    doc.add_paragraph("List any conflicts of interest")
    doc.add_paragraph("Answer:")
    _blank(doc)
    doc.add_paragraph("Date acknowledged")
    doc.add_paragraph("Answer: 2026-01-15")
    doc.add_paragraph("Supervisor name if applicable")
    _blank(doc)
    doc.save(path)


def build_memo_unstructured(path: Path) -> None:
    doc = Document()
    doc.add_heading("Operations Memo — Action Items", level=1)
    doc.add_paragraph(
        "Several items require written follow-up. Discussion-only topics are marked."
    )
    doc.add_paragraph("Document the root cause of last week's outage")
    _blank(doc)
    doc.add_paragraph("For discussion only: Should we change vendors?")
    doc.add_paragraph("Provide revised timeline for Phase 2")
    _blank(doc)
    p = doc.add_paragraph()
    p.add_run("Budget owner: ")
    p.add_run("____________")
    doc.save(path)


BUILDERS = {
    "grant_proposal_messy.docx": build_grant_proposal_messy,
    "hr_onboarding_underlines.docx": build_hr_onboarding_underlines,
    "clinical_intake_merged.docx": build_clinical_intake_merged,
    "legal_deposition_long.docx": build_legal_deposition_long,
    "course_syllabus_breaks.docx": build_course_syllabus_breaks,
    "research_survey_dense.docx": build_research_survey_dense,
    "it_security_audit_form.docx": build_it_security_audit_form,
    "volunteer_mixed_completion.docx": build_volunteer_mixed_completion,
    "performance_review_runs.docx": build_performance_review_runs,
    "construction_rfp_tables.docx": build_construction_rfp_tables,
    "newsletter_with_header.docx": build_newsletter_with_header,
    "medical_history_shaded.docx": build_medical_history_shaded,
    "internship_multibreak.docx": build_internship_multibreak,
    "debate_worksheet.docx": build_debate_worksheet,
    "budget_forecast_cells.docx": build_budget_forecast_cells,
    "interview_no_blanks.docx": build_interview_no_blanks,
    "policy_partial_answers.docx": build_policy_partial_answers,
    "memo_unstructured.docx": build_memo_unstructured,
}


def main() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    for filename, builder in BUILDERS.items():
        builder(FIXTURE_DIR / filename)
        print(f"Wrote {filename}")


if __name__ == "__main__":
    main()
