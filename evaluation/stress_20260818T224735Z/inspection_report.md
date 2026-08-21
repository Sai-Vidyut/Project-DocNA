# DocNA Stress Test Inspection Report

Generated: 2026-08-18T22:47:36.939076+00:00
Fixtures: 18

## Summary

- Passed (no errors): 13
- Failed or issues: 5

## Fixture Results

### budget_forecast_cells.docx

- Provider: mock
- Status: completed
- Detected tasks: 4
- Answerable: 4
- Answers generated: 4
- Placement strategies: {'fill_cell': 3, 'insert_below': 1}
- Structure: tables 1->1, blocks 16->17
- Notes: headers_footers_skipped

### clinical_intake_merged.docx

- Provider: mock
- Status: completed
- Detected tasks: 3
- Answerable: 3
- Answers generated: 3
- Placement strategies: {'fill_cell': 3}
- Structure: tables 1->1, blocks 16->16
- Notes: headers_footers_skipped

### construction_rfp_tables.docx

- Provider: mock
- Status: completed
- Detected tasks: 4
- Answerable: 4
- Answers generated: 4
- Placement strategies: {'fill_existing': 1, 'insert_below': 1, 'fill_cell': 2}
- Structure: tables 1->1, blocks 18->19
- Notes: headers_footers_skipped

### course_syllabus_breaks.docx

- Provider: mock
- Status: completed
- Detected tasks: 5
- Answerable: 5
- Answers generated: 5
- Placement strategies: {'fill_existing': 4, 'insert_below': 1}
- Structure: tables 0->0, blocks 13->14
- Notes: headers_footers_skipped

### debate_worksheet.docx

- Provider: mock
- Status: completed
- Detected tasks: 3
- Answerable: 3
- Answers generated: 3
- Placement strategies: {'fill_existing': 3}
- Structure: tables 0->0, blocks 10->10
- Notes: headers_footers_skipped

### grant_proposal_messy.docx

- Provider: mock
- Status: completed
- Detected tasks: 6
- Answerable: 6
- Answers generated: 6
- Placement strategies: {'fill_existing': 3, 'insert_below': 3}
- Structure: tables 0->0, blocks 13->16
- Notes: headers_footers_skipped

### hr_onboarding_underlines.docx

- Provider: mock
- Status: completed
- Detected tasks: 4
- Answerable: 3
- Answers generated: 3
- Placement strategies: {'insert_below': 3, 'skip': 1}
- Structure: tables 0->0, blocks 11->14
- Notes: headers_footers_skipped

### internship_multibreak.docx

- Provider: mock
- Status: completed
- Detected tasks: 1
- Answerable: 1
- Answers generated: 1
- Placement strategies: {'insert_below': 1}
- Structure: tables 0->0, blocks 11->12
- Notes: headers_footers_skipped

### interview_no_blanks.docx

- Provider: mock
- Status: failed
- Detected tasks: 0
- Answerable: 0
- Answers generated: 0
- Placement strategies: {}
- Structure: tables 0->0, blocks 8->8
- Errors:
  - [B] Expected prompt containing 'complex project you led' was not detected
  - [B] Expected prompt containing 'prioritize conflicting deadlines' was not detected
  - [B] Expected prompt containing 'failure and what you learned' was not detected
  - [B] Only 0 answerable tasks detected; expected at least 4
- Notes: headers_footers_skipped

### it_security_audit_form.docx

- Provider: mock
- Status: completed
- Detected tasks: 4
- Answerable: 4
- Answers generated: 4
- Placement strategies: {'fill_existing': 1, 'insert_below': 1, 'fill_cell': 2}
- Structure: tables 1->1, blocks 15->16
- Notes: headers_footers_skipped

### legal_deposition_long.docx

- Provider: mock
- Status: completed
- Detected tasks: 1
- Answerable: 1
- Answers generated: 1
- Placement strategies: {'insert_below': 1}
- Structure: tables 0->0, blocks 10->11
- Notes: headers_footers_skipped

### medical_history_shaded.docx

- Provider: mock
- Status: completed
- Detected tasks: 2
- Answerable: 2
- Answers generated: 2
- Placement strategies: {'fill_cell': 2}
- Structure: tables 1->1, blocks 17->17
- Notes: headers_footers_skipped

### memo_unstructured.docx

- Provider: mock
- Status: failed
- Detected tasks: 2
- Answerable: 2
- Answers generated: 2
- Placement strategies: {'insert_below': 2}
- Structure: tables 0->0, blocks 8->10
- Errors:
  - [B] False positive containing 'For discussion only': For discussion only: Should we change vendors?
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
- Status: failed
- Detected tasks: 0
- Answerable: 0
- Answers generated: 0
- Placement strategies: {}
- Structure: tables 0->0, blocks 7->7
- Errors:
  - [B] Expected prompt containing 'revenue target' was not detected
  - [B] Expected prompt containing 'leadership initiatives' was not detected
  - [B] Expected prompt containing 'measurable' was not detected
  - [B] Only 0 answerable tasks detected; expected at least 3
- Notes: headers_footers_skipped

### policy_partial_answers.docx

- Provider: mock
- Status: failed
- Detected tasks: 1
- Answerable: 1
- Answers generated: 1
- Placement strategies: {'insert_below': 1}
- Structure: tables 0->0, blocks 11->12
- Errors:
  - [B] Only 1 answerable tasks detected; expected at least 2
- Notes: headers_footers_skipped

### research_survey_dense.docx

- Provider: mock
- Status: failed
- Detected tasks: 0
- Answerable: 0
- Answers generated: 0
- Placement strategies: {}
- Structure: tables 0->0, blocks 8->8
- Errors:
  - [B] Expected prompt containing 'age range' was not detected
  - [B] Expected prompt containing 'statistical software' was not detected
  - [B] Expected prompt containing 'recruiting diverse' was not detected
  - [B] Only 0 answerable tasks detected; expected at least 3
- Notes: headers_footers_skipped

### volunteer_mixed_completion.docx

- Provider: mock
- Status: completed
- Detected tasks: 4
- Answerable: 4
- Answers generated: 4
- Placement strategies: {'insert_below': 3, 'fill_existing': 1}
- Structure: tables 0->0, blocks 11->14
- Notes: headers_footers_skipped
