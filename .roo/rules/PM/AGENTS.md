# Project Manager Mode Rules (Non-Obvious Only)

- Backend runs in `.venv`, not global Python environment
- iflow commands hang without `-y` flag (operation confirmation trap)
- iflow commands hang without `-p` flag (interactive mode trap)
- Frontend API config saves only model_name/base_url, not apiKey (security)
- Tests run with `npm run test` in frontend, not standard vitest paths
- iflow command format must include --timeout 5000 for safety
- Project moved from Streamlit to separate frontend/backend architecture