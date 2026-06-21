# Token Analytics Dashboard

**Live Demo:** [token-analytics-dashboard.onrender.com](https://token-analytics-dashboard.onrender.com)

A multipage interactive dashboard built with Plotly Dash to analyze token revenue from live streaming sessions. Data is ingested in real time via a separate ETL pipeline and stored in a PostgreSQL database on Supabase.

---

## Project Context

Tokens are the primary monetization mechanism on the platform — viewers send tokens ("tips") to the streamer during live sessions. This dashboard transforms raw transaction logs into actionable business intelligence, helping answer questions like: *when should I stream? who are my most valuable users? how concentrated is my revenue?*

> **Note:** Date gaps in the charts reflect days when no live streaming sessions were held — not missing data.

---

## Key Findings

- **187 unique users** have contributed tokens across all recorded sessions.
- The **top 5 users account for 56.6%** of all tokens — high revenue concentration.
- **Thursday and Saturday** are the highest-earning days of the week.
- Peak token activity occurs between **21:00 and 22:30 (Colombia time)**.

---

## Dashboard Pages

### Historical View
- **Average Tokens by Day of the Week** — fortnightly view with sample size annotations; low-confidence days flagged in gray.
- **Average Tokens by Time Slot** — 30-minute resolution bar chart for the selected fortnight.
- **All-Time Heatmap** — weekday × time slot heatmap with average tokens and observation count per cell; cells with fewer than 3 observations are marked with a dashed border.

### Users & Distribution
- **Total Global Audience** — unique user count across all sessions.
- **Top 15 All-Time Users** — ranked by total token contribution.
- **Concentration Analysis (Pareto)** — percentage of total tokens held by top 5, 8, 10, and 15 users.
- **Weekly Token Distribution** — stacked bar chart by user for the selected week.
- **User Peak Activity Table** — identifies the two 30-minute blocks where each top user appears most frequently in the selected fortnight.

---

## Date Picker Logic

The sidebar date picker controls two analysis windows simultaneously:
- **Fortnight** — the payroll period (1st–15th or 16th–end of month) containing the selected date.
- **Week** — the Monday-to-Sunday week containing the selected date.

---

## Tech Stack

| Layer | Tools |
|---|---|
| Dashboard | Plotly Dash, Dash Bootstrap Components |
| Data visualization | Plotly Express, Plotly Graph Objects |
| Data processing | Pandas, NumPy |
| Database | PostgreSQL (Supabase) |
| Deployment | Render |

---

## Related Repository

The ETL pipeline that feeds this dashboard lives in a separate repo:
[token-analytics-pipeline](https://github.com/kj-data/token-analytics-pipeline)

---

## Running Locally

**1. Clone the repo:**
```bash
git clone https://github.com/kj-data/token-analytics-dashboard.git
cd token-analytics-dashboard
```

**2. Install dependencies:**
```bash
pip install -r requirements.txt
```

**3. Create a `.env` file** with your Supabase credentials:
```
DB_HOST=your_host
DB_PORT=5432
DB_NAME=postgres
DB_USER=your_user
DB_PASSWORD=your_password
```

**4. Run the app:**
```bash
python app_en.py
```

Open `http://localhost:8050` in your browser.
