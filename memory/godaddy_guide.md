GoDaddy Go-Live guide for CryptoPluse (www.cryptopluse.io apex setup)

Overview
- Goal: publish CryptoPluse landing site on GitHub Pages behind the apex or www subdomain, using GoDaddy DNS.
- Assumptions: You already have a GitHub repo (r3shaver3141/cryptopluse) with the site live at https://<github-username>.github.io/cryptopluse/ and a domain you control in GoDaddy (not purchased yet).

1) Prerequisites
- Domain: cryptopluse.io (GoDaddy account)
- GitHub repo with CryptoPluse site (index.html at repo root, cryptopluse-site moved as needed)
- Access to GoDaddy DNS management for cryptopluse.io
- GitHub account linked to the repo and Pages configured

2) Step-by-step: apex domain cryptopluse.io (A records) if you later decide to buy and use apex
- Go to GoDaddy > My Products > Domains > cryptopluse.io > DNS
- Records:
  - A: Host @ -> 185.199.108.153
  - A: Host @ -> 185.199.109.153
  - A: Host @ -> 185.199.110.153
  - A: Host @ -> 185.199.111.153
- In GitHub:
  - Settings > Pages > Custom domain: enter cryptopluse.io
  - Save; a CNAME will be created in your repo
- TLS will be provisioned automatically by GitHub (Let’s Encrypt) after DNS propagates

3) Step-by-step: www subdomain setup (recommended)
- GoDaddy DNS: add CNAME for www -> your GitHub Pages domain
  - Name: www
  - Value: <your-username>.github.io (e.g., r3shaver3141.github.io)
  - TTL: default (1 hour)
- GitHub: Settings > Pages > Custom domain: enter www.cryptopluse.io
- Add a CNAME file in repo root containing:
  www.cryptopluse.io
- TLS is auto-managed by GitHub

4) Testing and validation
- DNS propagation can take minutes to up to 48h; after propagation, visit:
  - https://www.cryptopluse.io/
  - The base apex (cryptopluse.io) will work as a fallback if configured
- Ensure the signup mailto: still works (mailto: sales@cryptopluse.com or your configured address)

5) Rollout checklist (a quick go-live sheet)
- [ ] Domain registered and DNS updated for www (CNAME) and optional apex (A records)
- [ ] GitHub Pages configured to use www.cryptopluse.io
- [ ] CNAME file present with www.cryptopluse.io
- [ ] TLS/SSL provisioning completed
- [ ] Live URL tested in multiple browsers
- [ ] Sign-up form verified (mailto configuration or backend form)

6) Rollback plan
- If there’s a problem, revert DNS changes or switch Pages source to a different branch/folder; keep the old site in a separate branch or backup before applying changes.

Notes
- I can tailor this guide to your exact registrar if you share the registrar details, but this GoDaddy-focused version should cover the typical flow.
