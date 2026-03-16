CryptoPluse Data Gate (MVP)
-------------------------
Tech: Python + FastAPI (MVP) behind a public site, with gated API access via per-seat keys.
Endpoints (MVP):
- GET /api/v1/price_index.json?api_key=KEY
- GET /api/v1/price_index.csv?api_key=KEY
- GET /api/v1/digests/daily.csv?api_key=KEY
- GET /api/v1/digests/weekly.csv?api_key=KEY
Auth: API keys stored in memory for MVP,-ready to migrate to DB.
Rate limits: 1000 requests/day per key; bursts up to 10/min.
Data: seven-coin snapshot (BTC, ETH, SOL, XRP, ADA, BNB, XLM), plus daily/weekly digests.
Onboarding: simple sign-up, API key provisioning, welcome guide.
