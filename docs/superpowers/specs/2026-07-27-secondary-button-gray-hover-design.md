# Secondary Button Gray Hover Design

## Goal

Change every student-side `InteractiveHoverButton` with `type="secondary"` so its animated hover and keyboard-focus fill is neutral gray instead of orange.

## Scope

- Keep the existing circular reveal animation.
- Use a light neutral gray fill with dark gray text and arrow.
- Do not change primary, disabled, loading, active, sizing, or layout behavior.
- Apply the behavior through the shared component so all student-side secondary buttons stay consistent.

## Verification

- Add a browser test that checks the secondary fill and revealed content colors.
- Verify the primary button keeps its existing white reveal behavior.
- Run the focused student-side browser tests and production build.
- Deploy only the student frontend and verify the new assets online.
