# End-to-end tests

`make e2e` builds the SPA, then Playwright:

1. `global-setup.ts` resets the **test** database (`TEST_DATABASE_URL`), migrates it,
   imports every pack under `content/packs/`, and creates the owner `e2e-owner`.
2. `playwright.config.ts` starts the API on `127.0.0.1:8001` serving `backend/static`
   against that database.
3. The specs log in, complete a five-question session, review a card, and read Progress —
   at desktop, phone and ultrawide sizes. Screenshots land in `test-results/screenshots/`.

Nothing here touches the development database.
