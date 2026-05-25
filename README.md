# Excel Cleaner Engine `v0.1.0`

A local, open-source automation pipeline that takes messy Excel and CSV files — the kind every business produces daily — and turns them into clean, structured reports with AI analysis, anomaly detection and automated email delivery.

```
python pipeline.py
```

---

## What it does

Drop any `.xlsx` or `.csv` file into the pipeline and get back:

- A **clean Excel file** with normalized data, consistent formatting and professional styling
- **Summaries** grouped by client, seller, product and status
- An **anomaly report** flagging suspicious values, empty critical fields and similar names
- A **column-level validation report** catching structural data issues
- An **AI-generated executive summary** via Gemini 2.5 Flash
- An **automated email** with all outputs attached

---

## Modules

| Script | Responsibility | Input → Output |
|---|---|---|
| `loader.py` | Reads the source file | path → state with df_raw |
| `cleaner.py` | Normalizes and cleans data | df_raw → df_clean |
| `analyzer.py` | Generates grouped summaries | df_clean → analysis |
| `anomaly_detector.py` | Flags row-level anomalies | df_clean → anomalies |
| `validator.py` | Applies column-level business rules | df_clean → warnings |
| `insights.py` | Calls Gemini API | state → AI text |
| `notifier.py` | Sends email with attachments | state + paths → email |

### Outputs

| Script | Responsibility |
|---|---|
| `outputs/excel.py` | Writes formatted `.xlsx` + insights `.txt` |

### Orchestrators

| Script | Mode |
|---|---|
| `pipeline.py` | Manual — single file or batch folder |
| `watcher.py` | Automatic — detects new files in `inbox/` |

---

## What gets cleaned

- Headers with inconsistent casing, spaces or special characters → normalized to snake_case
- Fully empty rows → removed
- Hardcoded total rows mixed with data → detected and removed
- Duplicate rows → removed
- Dates in multiple formats (`15/03/2024`, `2024-03-16`, `17-03-2024`) → normalized to `YYYY-MM-DD`
- Numbers with `$`, thousand separators, decimal commas, attached text (`"2 u"`, `"N/A"`) → converted or marked as NaN
- Inconsistent text casing (`ACME CORP`, `acme corp`) → normalized to Title Case

## What gets detected

**Row-level anomalies**
- Statistical outliers (values beyond 3 standard deviations)
- Negative values in columns that shouldn't have them
- Totals that don't match price × quantity
- Empty values in critical columns (client, date, total)
- Values appearing only once — possible typos
- Similar names that may refer to the same entity

**Column-level warnings**
- Columns with ≥30% empty values
- Columns where all rows have the same value
- Numeric columns that sum to zero
- Percentage columns with values outside 0–100
- Date columns with future or pre-2000 dates

---

## Pipeline output

```
output/
└── ventas_marzo/
    ├── ventas_marzo_clean_20260525_1430.xlsx
    └── ventas_marzo_clean_20260525_1430_insights.txt
```

---

## Project structure

```
Excel Automation/
├── pipeline.py          ← manual orchestrator
├── watcher.py           ← automatic orchestrator
├── modules/
│   ├── loader.py
│   ├── cleaner.py
│   ├── analyzer.py
│   ├── anomaly_detector.py
│   ├── validator.py
│   ├── insights.py
│   └── notifier.py
├── outputs/
│   └── excel.py
├── inbox/               ← drop files here (watcher mode)
├── output/              ← processed reports land here
├── .env
└── requirements.txt
```

---

## Stack

- **[pandas](https://pandas.pydata.org/)** — data processing and transformation
- **[openpyxl](https://openpyxl.readthedocs.io/)** — Excel file generation with formatting
- **[watchdog](https://python-watchdog.readthedocs.io/)** — file system watcher
- **[Gemini 2.5 Flash](https://ai.google.dev/)** — AI insights (free tier)
- **[python-dotenv](https://github.com/theskumar/python-dotenv)** — environment variable management
- **smtplib** — Gmail SMTP email delivery

---

## Requirements

- Python 3.10+

```bash
pip install -r requirements.txt
```

---

## Setup

1. Clone the repo
2. Install dependencies
3. Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_key_here
GMAIL_USER=your@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com).
For Gmail, generate an App Password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).

---

## Usage

**Single file:**
```bash
python pipeline.py
```

**Batch — process an entire folder, one email at the end:**
```bash
python pipeline.py --batch inbox/
```

**Automatic watcher — processes any file dropped in `inbox/`:**
```bash
python watcher.py recipient@email.com
```

---

## Roadmap

- `outputs/sql.py` — insert clean data directly into a database
- Historical comparison — track changes between monthly files
- Charts sheet — native Excel charts generated automatically
- Airflow / Prefect integration — production-grade scheduling

---

## License

Apache 2.0 — free to use, modify, and distribute.
