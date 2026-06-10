# Dashboard Audit

This audit starts the dashboard revamp track. It records the current issues before implementation so future GitHub work has a clear source of truth.

## System-Wide Findings

- Dashboard pages currently mix metrics, forms, tables, and navigation in one surface.
- Long forms are embedded directly on dashboards and classroom pages, making pages crowded on mobile.
- Most pages use repeated `bk-border` cards without a consistent dashboard hierarchy.
- Action buttons are inconsistent across pages; some are primary actions, some are navigation, and some mutate data.
- Student identity is not consistently displayed with registration/admission number.
- Reports are functional but not yet school-report quality.
- Admin console pages are useful but need a tighter operations layout and consistent filters.
- Empty states, status labels, table headers, and action groups need one shared design language.

## Tutor Dashboard

- Create classroom and create student forms should move to modals.
- Student table should show full name, registration number, email, school, and class membership summary.
- Dashboard should emphasize core metrics and recent activity before management tables.
- Reset credential action is present but should be visually separated from class membership actions.
- Current implementation creates students directly; next step must support adding existing tutor-owned students to classes by admission number.

## Classroom Dashboard

- Create student and bulk import forms should move to modals.
- Needs add-existing-student-by-registration workflow.
- Needs remove-from-class action without deleting the student account.
- Must prevent duplicate class membership and show clear errors.
- Student list must prioritize registration number because names can repeat.

## Student Dashboard

- Todo form should move to a modal.
- Active work, calendar, todos, reminders, notifications, and results need clearer hierarchy.
- Result history should include classroom and assessment context.
- Student identity header already includes registration number and should remain prominent.

## Admin Dashboard And Console

- Admin dashboard now links to operations pages, but the design should become a consistent console.
- User, billing, plans, support, announcements, audit logs, and jobs should share one layout pattern.
- Filters should be compact and table-first.
- Destructive or sensitive actions should stay POST-only and should eventually use confirmation modals.

## Assessment Builder

- Add section, add question, import questions, and add-from-bank forms should move to modals.
- Builder should show assessment readiness, payment/publish state, and question list more clearly.
- Question rows should be easier to scan by type, marks, section, and order.

## Reports

- All student rows must include registration/admission number.
- Assessment reports should include registration number in submissions and exports.
- Classroom reports should include registration number and school.
- Printable reports should look formal and not like dashboard management screens.
- Violation reports should show student identity, registration number, event type, count, and disqualification status.

## Immediate Correction Priorities

1. Build shared dashboard layout primitives.
2. Refactor tutor dashboard with modal forms.
3. Refactor classroom dashboard with add/remove-by-registration workflow.
4. Refactor reports to include registration numbers everywhere.
5. Refactor student and admin dashboards to use the same layout system.
6. Add tests for duplicate prevention, class removal, and registration-number reporting.
