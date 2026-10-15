# Bonsai GUI

This is the frontend of the Bonsai application.

## Sample table checks

From this directory, install dependencies with `npm ci`, then run:

```sh
npm run typecheck
npm run test:table
npx playwright install chromium --only-shell
npm run test:table:browser
```

The browser tests use Chromium and the real DataTables modules with local
fixture responses. They need no running Bonsai services. They cover selection
and QC updates across unvisited pages, filtered bulk selection, exports, the
existing Jinja table path, and retrying failed overview loads.
