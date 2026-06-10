# Dashboard Revamp Guide

This guide defines the dashboard design system and implementation rules for Aptitude Kenya.

## Layout Principles

- Dashboards are operational tools, not landing pages.
- Keep information dense but readable.
- Show metrics first, then tables, then secondary details.
- Forms belong in modals or dedicated edit pages, not embedded on the main dashboard.
- Use registration/admission numbers whenever students are listed or reported.
- Use POST-only forms for mutations and keep CSRF protection on every action.

## Shared CSS Primitives

The base template provides these classes:

- `dashboard-shell`
- `dashboard-topbar`
- `dashboard-eyebrow`
- `dashboard-title`
- `dashboard-subtitle`
- `dashboard-actions`
- `dashboard-grid`
- `dashboard-panel`
- `dashboard-panel-header`
- `metric-tile`
- `data-table`
- `student-identity`
- `status-pill`
- `empty-state`

Use these before adding page-specific styles.

## Modal Pattern

Use Bootstrap modals for create/import actions:

- Create classroom
- Create student
- Add existing student to classroom
- Bulk import students
- Add question section
- Add question
- Import questions
- Add todo
- Admin plan/pricing forms where practical

Modal buttons should live in `dashboard-actions` or a panel header. The modal form should submit to the existing route unless a new route is required.

## Student Identity Pattern

Every student table row should include:

- Full name
- Registration/admission number
- Email
- School or classroom context where relevant

Preferred visual pattern:

```html
<span class="student-identity">
    <strong>Student Name</strong>
    <span>REG-001</span>
    <span>student@example.com</span>
</span>
```

## Classroom Membership Rules

- A tutor owns student accounts through `StudentProfile`.
- A classroom contains students through membership only.
- Adding a student to a class by registration number should not create a duplicate user.
- If the student is already in the class, show a clear message.
- Removing a student from a class must not delete the user or student profile.
- Tutors must not add students owned by another tutor.

## Report Rules

- Include registration/admission number in all student result tables and exports.
- Include classroom and assessment context.
- Separate score performance from integrity events.
- Printable reports should use professional headings, clean tables, and restrained styling.

## GitHub Documentation Expectations

For every dashboard revamp pull request, update:

- `docs/DASHBOARD_AUDIT.md` if findings change.
- `docs/DASHBOARD_REVAMP.md` if patterns change.
- `README.md` when user-facing routes or workflows change.
- `DEVELOPMENT_PROCESS.md` when checklist status changes.

## Next Implementation Order

1. Tutor dashboard.
2. Classroom dashboard and membership workflow.
3. Reports and exports.
4. Student dashboard.
5. Admin console.
6. Assessment builder.
