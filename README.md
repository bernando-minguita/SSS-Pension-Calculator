# SSS Pension & Retirement Calculator

A single-page web app that estimates your monthly SSS retirement pension and the
contributions needed to reach it — powered by the **official SSS
`calculate-planner` API**, the same backend used by the MySSS Retirement Planner
portal. Every peso shown is computed live by the SSS server; there is no local
or approximate math in this app.

## Features

- **Two calculator modes**
  - **Target Monthly Pension** — enter the pension you want (₱5,000 – ₱100,000);
    the app tells you the Pension Booster contribution required to reach it.
  - **Voluntary Booster** — enter a monthly Pension Booster contribution
    (₱500 – ₱50,000) and see the pension it produces.
- **Flexible inputs** — current age 15–59 (slider + −/+ buttons), monthly income
  ₱5,000 – ₱35,000 with one-click presets (₱10k / ₱15k / ₱20k / ₱25k / ₱35k).
- **Live dual result cards**
  - *Monthly pension from age 60*: Regular SSS pension, Mandatory Provident Fund
    (WISP), Pension Booster, and TOTAL.
  - *Monthly contribution starting today*: Regular SSS, Mandatory Provident
    Fund, Pension Booster, and TOTAL.
- **Summary information card** — Total Pension (15-year guaranteed period),
  Total Contribution, No. of Pension Years (15, Pension Booster), and No. of
  Contribution Years (credited years of service = 60 − current age).
- **ⓘ Basis of computation modal** — explains the assumptions behind the
  numbers (15% contribution rate, fixed contributions until age 60, ₱1,000/month
  allowance + 13th month, Pension Booster ROI 6% p.a., etc.).
- **Auto-recalculation** — results refresh as you type or drag the slider
  (350 ms debounce), plus an explicit **Calculate Planner** button.
- **Transparent API status line** — shows whether the current numbers came from
  a direct call, the serverless relay, or whether the SSS server is unreachable.

## How it works

```
Browser (index.html)
   │  POST application/x-www-form-urlencoded
   │  fields: age, monthlyIncome, desiredPension, volPenBoostContri
   │
   ├─ on *.sss.gov.ph host ──► direct POST to member.sss.gov.ph
   │                            /member/pbl/pencalc/calculate-planner
   │
   └─ anywhere else ─────────► POST /api/proxy  (Vercel serverless relay)
                                  │
                                  └─ server-to-server POST to the same
                                     official SSS endpoint; official JSON
                                     returned verbatim to the browser
```

**Why the relay exists:** `member.sss.gov.ph` sends no
`Access-Control-Allow-Origin` header, so a browser on any other host (e.g.
`*.vercel.app`) can never read a direct API response. A server-to-server call
from a Vercel function is not subject to browser CORS, so `api/proxy.py`
forwards the exact official payload and passes the official response straight
through.

**No fallback engine:** if the SSS server cannot be reached, the status line
turns red (`* Unable to reach the official SSS server - please try again`) and
the page never substitutes locally-computed figures.

## Project structure

```
SSS/
├── index.html        # the entire frontend (HTML + Tailwind CDN + vanilla JS)
├── api/
│   └── proxy.py      # Vercel Python serverless relay for the SSS API
└── bak/              # local backups only — exclude from deployment
```

## Tech stack

- **Frontend:** single static `index.html` — Tailwind CSS (CDN), FontAwesome 6,
  Google Fonts (Inter), vanilla JavaScript. No build step, no dependencies.
- **Backend:** `api/proxy.py` — Vercel Python function using only the standard
  library (`urllib`, `json`, `http.server`). No `requirements.txt` needed.

## API contract

`POST` to the official endpoint (or `/api/proxy`) with
`application/x-www-form-urlencoded` body. Only the active mode field is sent;
the other stays empty — identical to the official portal:

| Field | Mode | Valid range | Sent when |
|---|---|---|---|
| `age` | both | 15 – 59 | always |
| `monthlyIncome` | both | 5,000 – 35,000 (500 steps) | always |
| `desiredPension` | Target Monthly Pension | 5,000 – 100,000 | target mode only |
| `volPenBoostContri` | Voluntary Booster | 500 – 50,000 | booster mode only |

The response's `calculateRes` object populates every result field:
`ssmonthlypen`, `mpb_monthpen`, `vpb_monthpen`, `totalmonthpn`, `ss_contri`,
`mpb_contri`, `vpb_contri2`, `totalmoncont`, `totalamtcont`, `cys`,
`totalpen15` (shown only when `errorNum === 0`).

## Running locally

- **Quick look:** open `index.html` directly in a browser. The UI works, but
  `/api/proxy` does not exist on `file://`, so the status line will show the
  red "unable to reach" message — expected.
- **Full local stack:** use the [Vercel CLI](https://vercel.com/docs/cli) in
  the project folder:
  ```
  npm i -g vercel
  vercel dev
  ```
  This serves `index.html` and executes `api/proxy.py` locally, producing the
  same green *(serverless relay)* status as production.

## Deploying to Vercel

1. Create a Vercel project from this folder (framework preset: **Other**).
2. Deploy — Vercel auto-detects `api/proxy.py` as a Python function and serves
   `index.html` as the static root. No configuration file required.
3. Exclude the `bak/` folder from the deployment (add it to `.vercelignore`
   if deploying from this directory).
4. Verify on the live URL: the status line under the inputs should read
   green — `* Computed live via the official SSS API (serverless relay)`.
5. **If the relay reports the SSS server unreachable from Vercel**, the SSS
   endpoint may be blocking datacenter IPs. Pin the function to the region
   closest to the SSS servers by adding a `vercel.json`:
   ```json
   { "regions": ["sin1"] }
   ```

## Privacy & disclaimers

- The relay forwards only the four planner fields, logs only the HTTP status
  and `errorNum`, and never logs income or pension values.
- Computations are for **illustration purposes only** and are subject to change
  based on your actual SSS records. Official SSS statements always govern.
- This is an unofficial tool and is not affiliated with, endorsed by, or
  operated by the Social Security System (Philippines). SSS names and marks
  belong to their respective owners.

## Browser support

Any modern evergreen browser (Chrome, Edge, Firefox, Safari) with support for
`fetch`, `Intl.NumberFormat`, and ES5+ JavaScript.

