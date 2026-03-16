CryptoPluse MVP Go-Live Bundle (ZIP) - Production-Ready

Contents:
- gate/ (FastAPI MVP: main.py, requirements.txt, and initial DB setup)
- cryptopluse-site/ (landing.html, signup.html, success.html, styles.css)
- memory/ (price_index.csv/.json, signals.log, volume_history.json, daily/weekly digests)
- ONE_PAGE_DATSHEET.md
- README_SALES.md
- memory/godaddy_guide.md
- memory/api_gate_plan.md
- onboarding emails (text + HTML templates)
- a simple sign-up form HTML file (signup.html)

How to publish:
1) Create a public GitHub repo and push all contents
2) Bind www.cryptopluse.io via Porkbun (CNAME) and apex via A-records
3) Set GitHub Pages source to main root and domain to www.cryptopluse.io
4) Test reachability and TLS

Runbook snippets (for quick copy-paste):
- npm install inside lossless-claw directory if needed
- npx openclaw plugins install --link .
- npx openclaw gateway restart
- curl -I https://www.cryptopluse.io/
