# Frontend Accessibility Verification

This is the repeatable cross-cutting verification phase for Atlas Prime's user-facing flows. It complements feature tests; it does not replace manual assistive-technology testing before a production release.

## Current Audit

Scope: the shared shell and public search flow, including live API results.

Hallmark review scores: Philosophy 4/5, Hierarchy 4/5, Execution 4/5, Specificity 4/5, Restraint 5/5, Variety 4/5.

Delivered checks:

- Shared navigation, a labelled search landmark, and a keyboard-visible skip link are present in the application shell.
- Controls use visible focus indicators and 44px minimum button targets.
- Search loading and result-count changes use polite status announcements; failures use alerts.
- Motion is reduced when the user requests `prefers-reduced-motion`.
- The desktop header uses an intentional two-row layout rather than wrapping navigation among search and account controls.
- The live search route was reviewed at 1440, 768, 414, 375, and 320px widths without clipped text or horizontal layout overflow.

## Repeatable Validation

```sh
make lint
make test
make smoke
docker compose up -d --build web
google-chrome --headless --no-sandbox --disable-gpu --virtual-time-budget=5000 \
  --window-size=375,900 --screenshot=/tmp/atlas-search-mobile.png \
  'http://127.0.0.1:3001/search?q=smoke'
```

Review the screenshot at 320, 375, 414, 768, and 1440px after UI changes. Test keyboard navigation and a screen reader manually for any new dialog, custom control, or authenticated workflow.

## Remaining Release Checks

- Review signed-in Studio, Admin, and upload flows with a real Clerk session before public launch.
- Run a manual screen-reader pass for media player controls and Clerk-managed dialogs after their production branding/configuration is final.
