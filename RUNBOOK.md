# SageScan — Production Runbook

> Step-by-step guide to validate two real-world public datasets.  
> Run every command from the **project root**: `/Users/abhishekkaushik/Downloads/SageScan-main`

---

## Part 0 — One-time Setup

```bash
cd /Users/abhishekkaushik/Downloads/SageScan-main

# 1. Create the Python virtual environment and install all dependencies
make setup-python

# 2. Build the Go CLI binary
make build

# Verify both worked
./sagescan --version
engine/.venv/bin/python engine/main.py --help

# 3. Create the data folder
mkdir -p examples/data
```

---

## Dataset 1 — Titanic Passenger Manifest

### What it is
The complete passenger list for the RMS Titanic (1912).  
- **891 rows**, 12 columns  
- Real nulls: ~20% of `Age` is missing, 2 rows missing `Embarked`, ~77% missing `Cabin`  
- Real outliers: a few very high fares (first-class suites)  
- Perfect for: `not_null`, `unique`, `allowed_values`, `range`, `null_percentage`, `z_score`, `mean_check`

### Step 1 — Download

```bash
curl -L -o examples/data/titanic.csv \
  "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv"

# Verify
wc -l examples/data/titanic.csv        # expect: 892 (header + 891 rows)
head -3 examples/data/titanic.csv
```

Expected header:
```
PassengerId,Survived,Pclass,Name,Sex,Age,SibSp,Parch,Ticket,Fare,Cabin,Embarked
```

### Step 2 — Run Validation (text output)

```bash
./sagescan validate examples/rules/titanic_rules.yaml
```

### Step 3 — Run Validation (JSON output — for CI or piping)

```bash
./sagescan validate examples/rules/titanic_rules.yaml --output json
```

### Step 4 — Run with context label (simulates a CI pipeline run)

```bash
./sagescan validate examples/rules/titanic_rules.yaml \
  --context production \
  --output json | python3 -m json.tool
```

### Step 5 — Run Python tests on the engine directly

```bash
cd engine
../.venv/bin/python main.py << 'EOF'
{
  "command": "validate",
  "config": {
    "version": "1.0",
    "source": {"type": "csv", "path": "../examples/data/titanic.csv"},
    "rules": [
      {"column": "PassengerId", "checks": [{"type": "not_null"}, {"type": "unique"}]},
      {"column": "Age",         "checks": [{"type": "null_percentage", "value": 25.0}]},
      {"column": "Survived",    "checks": [{"type": "allowed_values",  "values": [0, 1]}]}
    ]
  }
}
EOF
cd ..
```

### Expected Failures & Why They Matter

| Column | Check | Will it FAIL? | Why it matters in production |
|--------|-------|--------------|------------------------------|
| `PassengerId` | `unique` | **PASS** | IDs are all distinct — good primary key |
| `Age` | `null_percentage ≤ 25%` | **PASS** | ~20% missing — within the 25% threshold |
| `Age` | `range 0.1–100` | **PASS** | All ages are plausible |
| `Age` | `z_score ≤ 3.5` | **PASS** | No extreme outliers |
| `Fare` | `z_score ≤ 3.5` | **FAIL ⚠️** | A handful of first-class passengers paid £512. In any billing system, these would trigger fraud alerts |
| `Survived` | `allowed_values [0,1]` | **PASS** | Clean binary flag |
| `Embarked` | `allowed_values [C,Q,S]` | **FAIL ⚠️** | 2 rows have NULL — any downstream `GROUP BY Embarked` will silently drop them |
| `Cabin` | *(not in rules)* | N/A | ~77% missing — if you add `null_percentage: 80` it would barely pass, showing how a "dirty" column can be documented |

**Key insight:** The `Fare` z-score failure and `Embarked` null are exactly the kinds of silent bugs that corrupt downstream aggregations in real data pipelines.

---

## Dataset 2 — Airbnb NYC Listings

### What it is
All active Airbnb listings in New York City.  
- **~22,000 rows**, 16+ columns  
- Real issues: `$0` prices (inactive listings), `price` outliers (penthouses), new listings with no reviews  
- Perfect for: `range`, `allowed_values`, `z_score`, `null_percentage`, `mean_check`, coordinate validation

### Step 1 — Download

```bash
curl -L -o examples/data/airbnb_listings.csv \
  "https://data.insideairbnb.com/united-states/ny/new-york-city/2024-09-04/visualisations/listings.csv"

# Verify
wc -l examples/data/airbnb_listings.csv      # expect: ~22,000 rows
head -3 examples/data/airbnb_listings.csv
```

Expected header:
```
id,name,host_id,host_name,neighbourhood_group,neighbourhood,latitude,longitude,
room_type,price,minimum_nights,number_of_reviews,last_review,reviews_per_month,
calculated_host_listings_count,availability_365
```

### Step 2 — Run Validation (text output)

```bash
./sagescan validate examples/rules/airbnb_rules.yaml
```

### Step 3 — Run Validation (JSON, save to file)

```bash
./sagescan validate examples/rules/airbnb_rules.yaml \
  --output json > airbnb_validation_report.json

# Count failures
python3 -c "
import json
r = json.load(open('airbnb_validation_report.json'))
print(f\"Status: {r['status']}\")
print(f\"Pass rate: {r['summary']['pass_rate']:.1f}%\")
failed = [x for x in r['results'] if not x['passed']]
for f in failed:
    print(f\"  FAIL  {f['column']:30s}  {f['check_type']:20s}  {f['message']}\")
"
```

### Step 4 — Profile the dataset first (understand it before validating)

```bash
./sagescan profile examples/rules/airbnb_rules.yaml
```

### Step 5 — Run with strict CI mode (non-zero exit code on any failure)

```bash
./sagescan validate examples/rules/airbnb_rules.yaml --fail-fast
echo "Exit code: $?"    # 0 = all pass, 1 = at least one failure
```

### Step 6 — Validate only the price column (quick sanity check)

Create a quick inline config:
```bash
cat > /tmp/quick_price_check.yaml << 'EOF'
version: "1.0"
source:
  type: csv
  path: examples/data/airbnb_listings.csv
rules:
  - column: price
    checks:
      - type: not_null
      - type: min_value
        value: 1
      - type: z_score
        value: 4.0
EOF

./sagescan validate /tmp/quick_price_check.yaml
```

### Expected Failures & Why They Matter

| Column | Check | Will it FAIL? | Why it matters in production |
|--------|-------|--------------|------------------------------|
| `id` | `unique` | **PASS** | Listing IDs are unique |
| `neighbourhood_group` | `allowed_values` | **FAIL ⚠️** | Any scraping artifact or new borough name will break BI dashboards that do `GROUP BY neighbourhood_group` |
| `price` | `min_value ≥ 1` | **FAIL ⚠️** | Some listings are priced at $0. Any revenue calculation that sums price will be understated. In production this means incorrect host payouts |
| `price` | `z_score ≤ 4.0` | **FAIL ⚠️** | Luxury penthouses exist at $10,000+/night. Normalisation pipelines that compute per-night averages will be skewed by these outliers |
| `price` | `mean_check 50–500` | **PASS** | NYC average is ~$180 — within expected band |
| `latitude` | `range 40.47–40.92` | **FAIL ⚠️** | Any listing geocoded outside NYC means the map pin is wrong. Customers book the wrong location |
| `reviews_per_month` | `null_percentage ≤ 40%` | **PASS** | New listings have no reviews; ~35–38% null is expected |
| `minimum_nights` | `max_value ≤ 365` | **FAIL ⚠️** | Some hosts set 1125 minimum nights — this is a data entry error that makes a listing unbookable. It inflates "available inventory" metrics |
| `availability_365` | `range 0–365` | **PASS** | Properly bounded |

**Key insight:** The `$0 price` and `minimum_nights > 365` failures are **real data quality bugs** that exist in the actual Airbnb dataset and directly corrupt revenue and inventory reports.

---

---

## Part 3 — AI / LLM Features

> **Prerequisite:** You need an OpenAI API key.  
> All LLM features are **optional** — validation always works without them.

---

### Step 0 — Set your API key (do this once per session)

```bash
export OPENAI_API_KEY=sk-...your-key-here...

# Verify it is set
echo $OPENAI_API_KEY | cut -c1-10   # should print "sk-..." prefix only
```

---

### Feature 1 — Generate Rules Automatically from a Dataset

SageScan analyses the dataset's column types and statistics, builds a prompt
(no raw data values are sent), and asks the LLM to write a `rules.yaml` for you.

#### Generate rules for Titanic

```bash
./sagescan generate-rules \
  --input   examples/data/titanic.csv \
  --output  examples/rules/titanic_llm_rules.yaml \
  --context "RMS Titanic 1912 passenger manifest. Used for survival analysis." \
  --llm-model gpt-4o \
  --timeout 3m
```

What happens internally:
```
CSV → column stats (min/max/mean/null%) → deterministic prompt → OpenAI API → YAML rules
                   ↑
          No raw passenger data is sent to the LLM — only statistics
```

Check the generated file:
```bash
cat examples/rules/titanic_llm_rules.yaml
```

Now validate using the LLM-generated rules:
```bash
./sagescan validate examples/rules/titanic_llm_rules.yaml --output json | python3 -m json.tool
```

---

#### Generate rules for Airbnb NYC

```bash
./sagescan generate-rules \
  --input   examples/data/airbnb_listings.csv \
  --output  examples/rules/airbnb_llm_rules.yaml \
  --context "Airbnb NYC active listings. Used for pricing and availability analytics." \
  --llm-model gpt-4o \
  --timeout 5m
```

Validate with generated rules:
```bash
./sagescan validate examples/rules/airbnb_llm_rules.yaml
```

---

### Feature 2 — AI Explanations for Validation Failures

When `llm_api_key` is present in the config, the engine automatically calls
the LLM to explain **why** each failed check matters and what to do about it.

#### Add API key to Titanic rules and get explanations

```bash
cat > /tmp/titanic_with_llm.yaml << EOF
version: "1.0"
source:
  type: csv
  path: examples/data/titanic.csv

llm_api_key: "${OPENAI_API_KEY}"
llm_model: "gpt-4o"
llm_max_tokens: 500

rules:
  - column: Fare
    checks:
      - type: z_score
        value: 3.5

  - column: Embarked
    checks:
      - type: allowed_values
        values: [C, Q, S]
      - type: null_percentage
        value: 1.0
EOF

./sagescan validate /tmp/titanic_with_llm.yaml --output json | python3 -m json.tool
```

The JSON output will include an `llm_explanations` block like:
```json
{
  "status": "FAIL",
  "llm_explanations": {
    "Fare_z_score": "The fare column contains statistical outliers — 3 first-class passengers paid over £512, which is 6+ standard deviations above the mean of £32. In a billing pipeline this would trigger fraud detection or cause mean-normalisation to produce incorrect results for all other passengers.",
    "Embarked_allowed_values": "2 rows have a NULL value for Embarked. Any GROUP BY Embarked query will silently drop these passengers, understating totals by 0.2%. In survival rate analysis by embarkation port, these rows will be excluded from every cohort."
  }
}
```

---

#### Add API key to Airbnb rules and get explanations

```bash
cat > /tmp/airbnb_with_llm.yaml << EOF
version: "1.0"
source:
  type: csv
  path: examples/data/airbnb_listings.csv

llm_api_key: "${OPENAI_API_KEY}"
llm_model: "gpt-4o"
llm_max_tokens: 500

rules:
  - column: price
    checks:
      - type: min_value
        value: 1
      - type: z_score
        value: 4.0

  - column: minimum_nights
    checks:
      - type: max_value
        value: 365
EOF

./sagescan validate /tmp/airbnb_with_llm.yaml --output json | python3 -m json.tool
```

---

### Feature 3 — Test LLM connectivity without running validation

SageScan has a built-in `check-llm` command. No dataset, no config file needed — just your API key.

```bash
# Uses OPENAI_API_KEY environment variable
./sagescan check-llm

# Test a specific model
./sagescan check-llm --llm-model gpt-3.5-turbo

# Pass the key directly (useful for one-off tests)
./sagescan check-llm --llm-api-key sk-...

# Test against gpt-4o with JSON output (for scripting)
./sagescan check-llm --llm-model gpt-4o --output json
```

Expected text output:
```
🔍 SageScan LLM Connectivity Check
──────────────────────────────────────────────────
  Model   : gpt-4o
  API Key : sk-proj-**************************
──────────────────────────────────────────────────

✅  LLM check PASSED
    Response : SageScan LLM OK
    Model    : gpt-4o
    Tokens   : 14
    Latency  : 312ms
```

Expected JSON output (`--output json`):
```json
{
  "status": "PASS",
  "summary": {
    "message": "SageScan LLM OK",
    "model": "gpt-4o",
    "tokens_used": 14,
    "latency_ms": 312
  },
  "results": []
}
```

**Failure cases the command handles:**

| Scenario | Output |
|----------|--------|
| `OPENAI_API_KEY` not set | `❌  no API key found` — clear message |
| Wrong/expired key | `❌  AuthenticationError` from OpenAI |
| Model does not exist | `❌  model 'gpt-4' not found` — try `--llm-model gpt-4o` |
| Network unreachable | `❌  APIConnectionError` |
| `openai` not installed | `❌  openai package is not installed` + install command |
| Rate limited | `❌  RateLimitError` — wait and retry |

---

### Feature 4 — Compare hand-written vs LLM-generated rules

After running both generate-rules commands above, diff the outputs:

```bash
# Titanic: hand-written vs LLM
diff examples/rules/titanic_rules.yaml examples/rules/titanic_llm_rules.yaml

# Airbnb: hand-written vs LLM
diff examples/rules/airbnb_rules.yaml  examples/rules/airbnb_llm_rules.yaml
```

Then validate with BOTH and compare pass rates:
```bash
# Hand-written rules
./sagescan validate examples/rules/titanic_rules.yaml --output json \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print('Hand-written pass rate:', r['summary']['pass_rate'])"

# LLM-generated rules
./sagescan validate examples/rules/titanic_llm_rules.yaml --output json \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print('LLM-generated pass rate:', r['summary']['pass_rate'])"
```

---

### LLM Cost Estimate

| Operation | Dataset | Approx tokens | Approx cost (gpt-4o) |
|-----------|---------|--------------|----------------------|
| `generate-rules` | Titanic (12 cols) | ~2,000 | ~$0.01 |
| `generate-rules` | Airbnb (16 cols) | ~2,500 | ~$0.01 |
| `explain` failures | 3 failed checks | ~1,500 | ~$0.01 |
| LLM connectivity test | — | ~20 | < $0.001 |

> **Note:** No raw CSV data is ever sent to the LLM — only column names, dtypes, and aggregate statistics (min/max/mean/std/null%). PII column values (email, name, ssn, phone, password) are automatically redacted from the prompt.

---

### LLM Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `LLM API key is required` | `OPENAI_API_KEY` not set | `export OPENAI_API_KEY=sk-...` |
| `AuthenticationError` | Wrong or expired key | Check key at platform.openai.com |
| `RateLimitError` | Too many requests | SageScan auto-retries 3× with backoff; wait 60s |
| `LLM returned unparseable YAML` | Model hallucinated bad YAML | Retry; or switch to `--llm-model gpt-4o` |
| `LLM response contained zero rules` | Model returned explanation text, not YAML | Retry; model is non-deterministic |
| `No module named 'openai'` | LLM deps not installed | `engine/.venv/bin/pip install openai litellm` |
| `model: gpt-4 does not exist` | Model name wrong or no access | Use `--llm-model gpt-4o` or `gpt-3.5-turbo` |
| Explanation block missing in output | `llm_api_key` not in config | Add `llm_api_key` to YAML or use inline config as shown above |

---

## Full Command Reference Card

```bash
# ── LLM setup ──────────────────────────────────────────────────────────────
export OPENAI_API_KEY=sk-...            # required for all LLM features

# ── LLM connectivity test (built-in CLI command) ───────────────────────────
./sagescan check-llm                                   # uses OPENAI_API_KEY env var
./sagescan check-llm --llm-model gpt-3.5-turbo        # test a specific model
./sagescan check-llm --llm-api-key sk-...             # pass key directly

# ── Generate rules with LLM ────────────────────────────────────────────────
./sagescan generate-rules \
  -i examples/data/titanic.csv \
  -o examples/rules/titanic_llm_rules.yaml \
  --context "Titanic passenger manifest" \
  --llm-model gpt-4o

./sagescan generate-rules \
  -i examples/data/airbnb_listings.csv \
  -o examples/rules/airbnb_llm_rules.yaml \
  --context "Airbnb NYC listings for pricing analytics" \
  --llm-model gpt-4o \
  --timeout 5m

# ── Validate with LLM-generated rules ─────────────────────────────────────
./sagescan validate examples/rules/titanic_llm_rules.yaml
./sagescan validate examples/rules/airbnb_llm_rules.yaml

# ── Validate with AI explanations (add llm_api_key to config) ─────────────
./sagescan validate /tmp/titanic_with_llm.yaml  --output json
./sagescan validate /tmp/airbnb_with_llm.yaml   --output json
# ── Build ──────────────────────────────────────────────────────────────────
make build                              # compile ./sagescan binary

# ── Setup ──────────────────────────────────────────────────────────────────
make setup-python                       # create venv + install deps
mkdir -p examples/data                  # create data folder

# ── Download datasets ──────────────────────────────────────────────────────
curl -L -o examples/data/titanic.csv \
  "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv"

curl -L -o examples/data/airbnb_listings.csv \
  "https://data.insideairbnb.com/united-states/ny/new-york-city/2024-09-04/visualisations/listings.csv"

# ── Validate ───────────────────────────────────────────────────────────────
./sagescan validate examples/rules/titanic_rules.yaml
./sagescan validate examples/rules/airbnb_rules.yaml

# ── JSON output ────────────────────────────────────────────────────────────
./sagescan validate examples/rules/titanic_rules.yaml --output json
./sagescan validate examples/rules/airbnb_rules.yaml  --output json

# ── Save report to file ────────────────────────────────────────────────────
./sagescan validate examples/rules/titanic_rules.yaml \
  --output json > titanic_report.json

./sagescan validate examples/rules/airbnb_rules.yaml \
  --output json > airbnb_report.json

# ── Profile (inspect dataset before writing rules) ─────────────────────────
./sagescan profile examples/rules/titanic_rules.yaml
./sagescan profile examples/rules/airbnb_rules.yaml

# ── CI mode (non-zero exit on failure) ────────────────────────────────────
./sagescan validate examples/rules/titanic_rules.yaml --fail-fast
./sagescan validate examples/rules/airbnb_rules.yaml  --fail-fast

# ── Debug mode (see Python engine logs) ───────────────────────────────────
SAGESCAN_VERBOSE=true ./sagescan validate examples/rules/titanic_rules.yaml
SAGESCAN_LOG_LEVEL=DEBUG ./sagescan validate examples/rules/airbnb_rules.yaml

# ── Run Python tests ───────────────────────────────────────────────────────
make test-python

# ── Run Go tests ───────────────────────────────────────────────────────────
make test-go
```

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `python: command not found` | Python not on PATH | Use `python3` or set `SAGESCAN_ENGINE_PATH` and run `./sagescan` after setting `PATH` |
| `engine not found` | Binary run from wrong dir | Set `SAGESCAN_ENGINE_PATH=/path/to/SageScan-main/engine/main.py` |
| `No module named 'pandas'` | venv not active | Run `make setup-python` first; the binary auto-uses system `python` — ensure venv python is on PATH or set `SAGESCAN_ENGINE_PATH` to venv python |
| `Configuration validation failed` | YAML uses wrong check type | See validator table in README; common mistake: `pattern` needs `regex` key |
| `CSV file not found` | Relative path wrong | Run `./sagescan` from the project root, or use absolute paths in the YAML |
| `Fare z_score FAIL` on Titanic | Expected — real outliers | This is correct behaviour. Adjust `value: 4.5` to suppress if needed |
| `price min_value FAIL` on Airbnb | Expected — $0 listings exist | This is a real data quality bug in the source data |
| Timeout on large Airbnb file | Default 5m may be tight | Add `--timeout 15m` flag |

---

## What "Production-Grade" Means Here

In a real pipeline you would:

```bash
# In your Airflow / GitHub Actions / dbt step:

./sagescan validate config/prod_rules.yaml \
  --context production              \
  --output json                     \
  --fail-fast                       \
  > reports/$(date +%Y%m%d)_report.json

# The non-zero exit code stops the pipeline before bad data reaches the warehouse
```

The exact same binary, the exact same YAML, runs locally and in CI — no environment differences.

