# DocNA Stress Test Inspection Report

Generated: 2026-08-18T22:58:35.759406+00:00
Fixtures: 18

## Summary

- Passed (no errors): 15
- Failed or issues: 3

## Fixture Results

### budget_forecast_cells.docx

- Provider: mock
- Status: completed
- Detected tasks: 4
- Answerable: 4
- Answers generated: 4
- Placement strategies: {'insert_below': 1, 'fill_cell': 3}
- Structure: tables 1->1, blocks 16->17
- Edit checks: single=True, multi=True, ai_preserved=True
- Notes: headers_footers_skipped

### clinical_intake_merged.docx

- Provider: mock
- Status: completed
- Detected tasks: 5
- Answerable: 5
- Answers generated: 5
- Placement strategies: {'insert_below': 2, 'fill_cell': 3}
- Structure: tables 1->1, blocks 16->18
- Edit checks: single=True, multi=True, ai_preserved=True
- Notes: headers_footers_skipped

### construction_rfp_tables.docx

- Provider: mock
- Status: completed
- Detected tasks: 6
- Answerable: 6
- Answers generated: 6
- Placement strategies: {'insert_below': 3, 'fill_existing': 1, 'fill_cell': 2}
- Structure: tables 1->1, blocks 18->21
- Edit checks: single=True, multi=True, ai_preserved=True
- Notes: headers_footers_skipped

### course_syllabus_breaks.docx

- Provider: mock
- Status: completed
- Detected tasks: 5
- Answerable: 5
- Answers generated: 5
- Placement strategies: {'fill_existing': 4, 'insert_below': 1}
- Structure: tables 0->0, blocks 13->14
- Edit checks: single=True, multi=True, ai_preserved=True
- Notes: headers_footers_skipped

### debate_worksheet.docx

- Provider: mock
- Status: completed
- Detected tasks: 4
- Answerable: 4
- Answers generated: 4
- Placement strategies: {'insert_below': 1, 'fill_existing': 3}
- Structure: tables 0->0, blocks 10->11
- Edit checks: single=True, multi=True, ai_preserved=True
- Notes: headers_footers_skipped

### grant_proposal_messy.docx

- Provider: mock
- Status: completed
- Detected tasks: 6
- Answerable: 6
- Answers generated: 6
- Placement strategies: {'fill_existing': 3, 'insert_below': 3}
- Structure: tables 0->0, blocks 13->16
- Edit checks: single=True, multi=True, ai_preserved=True
- Notes: headers_footers_skipped

### hr_onboarding_underlines.docx

- Provider: mock
- Status: completed
- Detected tasks: 7
- Answerable: 6
- Answers generated: 6
- Placement strategies: {'insert_below': 4, 'fill_existing': 2, 'skip': 1}
- Structure: tables 0->0, blocks 11->15
- Edit checks: single=True, multi=True, ai_preserved=True
- Notes: headers_footers_skipped

### internship_multibreak.docx

- Provider: mock
- Status: completed
- Detected tasks: 3
- Answerable: 3
- Answers generated: 3
- Placement strategies: {'insert_below': 2, 'fill_existing': 1}
- Structure: tables 0->0, blocks 11->13
- Edit checks: single=True, multi=True, ai_preserved=True
- Notes: headers_footers_skipped

### interview_no_blanks.docx

- Provider: mock
- Status: failed
- Detected tasks: 3
- Answerable: 3
- Answers generated: 3
- Placement strategies: {'insert_below': 3}
- Structure: tables 0->0, blocks 8->11
- Edit checks: single=True, multi=True, ai_preserved=True
- Errors:
  - [B] Only 3 answerable tasks detected; expected at least 4
- Notes: headers_footers_skipped

### it_security_audit_form.docx

- Provider: mock
- Status: completed
- Detected tasks: 6
- Answerable: 6
- Answers generated: 6
- Placement strategies: {'insert_below': 3, 'fill_existing': 1, 'fill_cell': 2}
- Structure: tables 1->1, blocks 15->18
- Edit checks: single=True, multi=True, ai_preserved=True
- Notes: headers_footers_skipped

### legal_deposition_long.docx

- Provider: mock
- Status: completed
- Detected tasks: 6
- Answerable: 6
- Answers generated: 6
- Placement strategies: {'insert_below': 3, 'fill_existing': 3}
- Structure: tables 0->0, blocks 10->13
- Edit checks: single=True, multi=True, ai_preserved=True
- Notes: headers_footers_skipped

### medical_history_shaded.docx

- Provider: mock
- Status: completed
- Detected tasks: 4
- Answerable: 4
- Answers generated: 4
- Placement strategies: {'insert_below': 2, 'fill_cell': 2}
- Structure: tables 1->1, blocks 17->19
- Edit checks: single=True, multi=True, ai_preserved=True
- Notes: headers_footers_skipped

### memo_unstructured.docx

- Provider: mock
- Status: failed
- Detected tasks: 3
- Answerable: 3
- Answers generated: 3
- Placement strategies: {'fill_existing': 2, 'insert_below': 1}
- Structure: tables 0->0, blocks 8->9
- Edit checks: single=True, multi=True, ai_preserved=True
- Errors:
  - [B] Expected prompt containing 'For discussion only: Should we change vendors?' was not detected
- Notes: headers_footers_skipped

### newsletter_with_header.docx

- Provider: mock
- Status: completed
- Detected tasks: 1
- Answerable: 1
- Answers generated: 1
- Placement strategies: {'insert_below': 1}
- Structure: tables 0->0, blocks 5->6
- Notes: headers_footers_skipped

### performance_review_runs.docx

- Provider: mock
- Status: completed
- Detected tasks: 3
- Answerable: 3
- Answers generated: 3
- Placement strategies: {'fill_existing': 3}
- Structure: tables 0->0, blocks 7->7
- Edit checks: single=True, multi=True, ai_preserved=True
- Notes: headers_footers_skipped

### policy_partial_answers.docx

- Provider: mock
- Status: completed
- Detected tasks: 5
- Answerable: 3
- Answers generated: 5
- Placement strategies: {'insert_below': 2, 'skip': 2, 'fill_existing': 1}
- Structure: tables 0->0, blocks 11->13
- Edit checks: single=True, multi=True, ai_preserved=True
- Notes: headers_footers_skipped

### research_survey_dense.docx

- Provider: mock
- Status: failed
- Detected tasks: 2
- Answerable: 2
- Answers generated: 2
- Placement strategies: {'fill_existing': 2}
- Structure: tables 0->0, blocks 8->8
- Edit checks: single=True, multi=True, ai_preserved=True
- Errors:
  - [B] Expected prompt containing 'statistical software' was not detected
  - [B] Only 2 answerable tasks detected; expected at least 3
- Notes: headers_footers_skipped

### volunteer_mixed_completion.docx

- Provider: mock
- Status: completed
- Detected tasks: 4
- Answerable: 2
- Answers generated: 4
- Placement strategies: {'skip': 2, 'insert_below': 1, 'fill_existing': 1}
- Structure: tables 0->0, blocks 11->12
- Edit checks: single=True, multi=True, ai_preserved=True
- Notes: headers_footers_skipped
