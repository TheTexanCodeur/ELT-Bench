# ELT-Bench (Transform Stage Only)

A benchmark suite for evaluating AI agents on **data transformation tasks** using Snowflake and SQL/DBT.

**Based on:** [uiuc-kang-lab/ELT-Bench](https://github.com/uiuc-kang-lab/ELT-Bench)  
**Modification:** This fork focuses **exclusively on the Transform (T)** stage. All Extract (E) and Load (L) operations are pre-completed.

## 🎯 What is ELT-Bench?

ELT-Bench contains **100 data transformation problems** where AI agents must:
1. Read source tables from Snowflake (`AIRBYTE_SCHEMA`)
2. Generate SQL/DBT transformations based on requirements
3. Create target tables in the same schema

**Important:** This benchmark evaluates **only the Transform (T)** stage. Source data is pre-loaded into Snowflake before agents start working. Unlike the original ELT-Bench, agents do **not** need to configure or run Airbyte for data extraction and loading.

---

## 🚀 Quick Start

### 1. Install Prerequisites

- **Docker** - For running agent containers
- **Conda** - For Python environment management
- **Snowflake Account** - For data storage and transformations

### 2. Setup Environment

```bash
# Clone repository
git clone <repo-url>
cd ELT-Bench

# Create conda environment
conda create -y -n elt python=3.11
conda activate elt

# Install dependencies
cd setup
pip install -r requirements.txt
```

### 3. Configure Snowflake

**A. Run the setup SQL in your Snowflake account:**

Copy and execute `setup/destination/setup.sql` in Snowflake. This creates:
- Database: `AIRBYTE_DATABASE`
- Schema: `AIRBYTE_SCHEMA`
- User: `AIRBYTE_USER` (password: `Snowflake@123`)
- Role: `AIRBYTE_ROLE`
- Warehouse: `AIRBYTE_WAREHOUSE`

**B. Add your Snowflake credentials:**

Edit `setup/destination/snowflake_credential.json`:
```json
{
  "account": "your-account.region.snowflakecomputing.com",
  "user": "AIRBYTE_USER",
  "password": "Snowflake@123"
}
```

⚠️ **Important:** Use role `AIRBYTE_ROLE`, not `SYSADMIN`

### 4. Download and Setup Data

```bash
# From setup/ directory
bash elt_setup.sh
```

This will:
- Download source data, ground truth, and schemas (via Google Drive)
- Extract files to `data/` directory
- Generate agent workspaces in `data/inputs/` with credentials

### 5. Load Source Data to Snowflake

```bash
# From project root
python3 dev/snowflake-connector/upload_tables.py --example_index 0-99
```

This uploads all 100 problems' source tables to `AIRBYTE_SCHEMA`. You can also upload specific problems:
- `--example_index 0-4` - Upload first 5 problems
- `--example_index 0,5,10` - Upload specific problems

**Verify:** Check Snowflake for tables in `AIRBYTE_DATABASE.AIRBYTE_SCHEMA`

---

## 🤖 Running Agents

### Agent Workspace Structure

Each problem has a workspace in `data/inputs/<problem>/`:

```
data/inputs/address/
├── config.yaml                 # Source table information
├── data_model.yaml             # Target schema requirements
├── schemas/                    # Source data schemas
│   └── *.json
└── snowflake_credential.json   # Snowflake connection info
```

### Agent Requirements

Your agent should:

1. **Read requirements** from the workspace files
2. **Generate transformation code** (SQL, DBT, Python)
3. **Execute transformations** that:
   - Read from `AIRBYTE_SCHEMA` (source tables)
   - Write to `AIRBYTE_SCHEMA` (target tables)
   - Match the schema defined in `data_model.yaml`

### Example Agent Implementations

See these for reference:
- `agents/spider-agent/` - Spider-based agent
---

## ✅ Evaluation

### Run Evaluation

```bash
cd evaluation
python eva.py --folder <run_name> --example_index <range>
```

**Examples:**
```bash
# Evaluate all 100 problems
python eva.py --folder my_run --example_index 0-99

# Evaluate first 5 problems (for testing)
python eva.py --folder test --example_index 0-4

# Evaluate specific problems
python eva.py --folder targeted --example_index 10,25,50
```

### Evaluation Stages

**Stage 1: Source Table Validation**
- Verifies source tables exist in `AIRBYTE_SCHEMA`
- Compares against ground truth data
- Validates row counts, schemas, and data values

**Stage 2: Transformation Validation**
- Executes SQL queries from `evaluation/<problem>/*.sql`
- Compares transformation results against expected output
- Validates business logic and data model compliance

### Results

Results are saved to `data/results/<run_name>/`:

```
data/results/my_run/
├── eval_address/
│   ├── stage1.log    # Source validation logs
│   └── stage2.log    # Transformation validation logs
├── eval_airline/
│   ├── stage1.log
│   └── stage2.log
└── ...
```

---

## 📁 Project Structure

### Directory Layout (Before Setup)

```
ELT-Bench/
├── README.md                           # Project documentation
│
├── elt-bench/                          # 📦 BENCHMARK DEFINITIONS (100 problems)
│   ├── address/                       # Problem 1: Address data
│   │   ├── config.yaml                # Data source configurations
│   │   ├── data_model.yaml            # Required output schema
│   │   └── schemas/                   # Source data schemas
│   ├── airline/                       # Problem 2: Airline data
│   └── ... (98 more problems)         # Problems 3-100
│
├── setup/                              # 🔧 SETUP SCRIPTS & CREDENTIALS
│   ├── elt_setup.sh                   # Main setup orchestrator
│   ├── write_config.py                # Generates data/inputs/ from elt-bench/
│   ├── requirements.txt               # Python dependencies
│   │
│   └── destination/                   # Snowflake credentials (user-filled)
│       ├── snowflake_credential.json  # {account, user, password}
│       └── setup.sql                  # Snowflake setup SQL
│
├── elt-docker/                         # 🐳 DOCKER INFRASTRUCTURE (for agent containers)
│   └── docker-compose.yml             # Defines agent environment images
│
├── evaluation/                         # ✅ EVALUATION FRAMEWORK
│   ├── eva.py                         # Main evaluation orchestrator
│   ├── eva_stage1.py                  # Stage 1: Source table validation
│   ├── eva_stage2.py                  # Stage 2: Transformation validation
│   ├── table.json                     # Table metadata for validation
│   │
│   └── address/, airline/, ... (100)  # Expected SQL queries per problem
│       └── *.sql                      # Query definitions for comparison
│
├── agents/                             # 🤖 AGENT IMPLEMENTATIONS
│   ├── spider-agent/                  # Spider Agent implementation
│   └── SWE-agent/                     # SWE Agent implementation
│
├── dev/                                # 🛠️ DEVELOPMENT UTILITIES
│   ├── csv_checker.py                 # CSV validation tool
│   └── snowflake-connector/           # Snowflake data upload utilities
│       └── upload_tables.py           # Bulk table uploader
│
├── example/                            # 📖 USAGE EXAMPLES
│   └── ...
│
├── materials/                          # 📊 PROJECT MATERIALS
│   └── elt.svg                        # Diagram assets
│
└── data/                               # (Not present initially - created by setup)
```

### How Setup Transforms the Structure

The `setup/elt_setup.sh` script performs the following transformations:

#### Step 1: Download Data Archives (via `gdown`)
Downloads three ZIP files to `setup/`:
- `data_api.zip` (~XXX MB) - API source data files
- `data_db.zip` (~XXX MB) - Database source data files  
- `gt.zip` (~XXX MB) - Ground truth validation data

#### Step 2: Extract Archives to `data/`
```bash
unzip data_api.zip -d ../data/source/api     # → data/source/api/
unzip data_db.zip -d ../data/source/db       # → data/source/db/
unzip gt.zip -d ../data/ground_truth         # → data/ground_truth/
```

#### Step 3: Generate Working Directories (`write_config.py`)
For each of the 100 problems in `elt-bench/`, creates a working copy in `data/inputs/` with:

**Original files (copied from `elt-bench/<problem>/`):**
- `config.yaml`
- `data_model.yaml`
- `schemas/` directory

**Injected credentials:**
- Creates `snowflake_credential.json` with connection details from `setup/destination/snowflake_credential.json`

**Resulting structure after setup:**

```
ELT-Bench/
├── elt-bench/                          # 📦 ORIGINAL (unchanged, Git-tracked)
│   ├── address/
│   │   ├── config.yaml                # Template configs (no credentials)
│   │   ├── data_model.yaml
│   │   └── schemas/
│   └── ... (99 more)
│
├── data/                               # 🎯 GENERATED (gitignored, recreatable)
│   │
│   ├── inputs/                         # 💼 WORKING COPIES (agents work here)
│   │   ├── address/
│   │   │   ├── config.yaml            # Copied from elt-bench/
│   │   │   ├── data_model.yaml        # Copied from elt-bench/
│   │   │   ├── schemas/               # Copied from elt-bench/
│   │   │   └── snowflake_credential.json  # ✨ Created (Snowflake auth)
│   │   └── ... (99 more problems)
│   │
│   ├── source/                         # 📥 SOURCE DATA (extracted from ZIPs)
│   │   ├── api/                       # API endpoint data files
│   │   │   ├── address/
│   │   │   │   └── *.json, *.csv
│   │   │   └── ... (problems with API sources)
│   │   └── db/                        # Database dump files
│   │       ├── postgres/
│   │       │   ├── address/
│   │       │   │   └── *.sql, *.csv
│   │       │   └── ...
│   │       └── mongodb/
│   │           └── ...
│   │
│   ├── ground_truth/                   # ✅ VALIDATION DATA (extracted from gt.zip)
│   │   ├── address/
│   │   │   └── *.csv                  # Expected output tables
│   │   └── ... (99 more)
│   │
│   └── results/                        # 📊 EVALUATION OUTPUTS (created on eval run)
│       └── run_YYYYMMDD_HHMMSS/       # Timestamped evaluation run
│           ├── eval_address/
│           │   ├── stage1.log         # Source table validation
│           │   └── stage2.log         # Transformation validation
│           └── ... (evaluated problems)
│
├── setup/                              # 🔧 (artifacts added after download)
│   ├── data_api.zip                   # ⬇️ Downloaded archive
│   ├── data_db.zip                    # ⬇️ Downloaded archive
│   ├── gt.zip                         # ⬇️ Downloaded archive
│   └── ... (scripts unchanged)
│
└── elt-docker/
    └── (agent docker images)
```

### Directory Roles and Responsibilities

| Directory | Role | Mutability | Git Tracked |
|-----------|------|------------|-------------|
| **`elt-bench/`** | Benchmark definitions (100 problems) | ❌ Read-only | ✅ Yes |
| **`data/inputs/`** | Agent working environment | ✅ Agents modify | ❌ No (gitignored) |
| **`data/source/`** | Source data files (extracted from ZIPs) | ❌ Read-only | ❌ No (gitignored) |
| **`data/ground_truth/`** | Expected outputs for validation | ❌ Read-only | ❌ No (gitignored) |
| **`data/results/`** | Evaluation outputs | ✅ Written by `eva.py` | ❌ No (gitignored) |
| **`setup/`** | Setup scripts & credential templates | 👤 User fills credentials | ✅ Yes (except ZIPs) |
| **`evaluation/`** | Evaluation scripts & SQL queries | ❌ Framework code | ✅ Yes |
| **`elt-docker/`** | Agent container images | ❌ Infrastructure | ✅ Yes |
| **`agents/`** | Agent implementations | 👤 User develops | ✅ Yes |
| **`dev/`** | Development utilities | 👤 Helper tools | ✅ Yes |

**Key Principles:**
- **`elt-bench/`** is the source of truth (never modify directly)
- **`data/`** is ephemeral (can be deleted and regenerated)
- **Agents only work in `data/inputs/`** (isolated from originals)
- **Credentials never committed** (stored in `setup/`, injected into `data/inputs/`)

**File Flow Summary:**
```
elt-bench/<problem>/          →  (write_config.py)  →  data/inputs/<problem>/
├── config.yaml                                       ├── config.yaml
├── data_model.yaml                                   ├── data_model.yaml
└── schemas/                                          ├── schemas/
                                                      └── snowflake_credential.json (new)

setup/data_*.zip              →  (extracted)      →  data/source/{api,db}/
setup/gt.zip                  →  (extracted)      →  data/ground_truth/
```
## Workflow Overview

The complete ELT-Bench workflow consists of three phases:

### Phase 1: Setup (One-time)
```
┌─────────────────────────────────────────────────────────────┐
│ 1. User fills Snowflake credentials                         │
│    └── setup/destination/snowflake_credential.json         │
├─────────────────────────────────────────────────────────────┤
│ 2. Run setup/elt_setup.sh                                   │
│    ├── Downloads ZIPs (data_api, data_db, gt)              │
│    ├── Extracts to data/ directory                         │
│    └── Runs write_config.py                                │
├─────────────────────────────────────────────────────────────┤
│ 3. write_config.py generates data/inputs/                   │
│    ├── Copies elt-bench/ → data/inputs/                    │
│    └── Creates snowflake_credential.json                   │
├─────────────────────────────────────────────────────────────┤
│ 4. Upload source data to Snowflake                          │
│    └── python dev/snowflake-connector/upload_tables.py     │
└─────────────────────────────────────────────────────────────┘
                           ↓
          data/inputs/ ready for agents
          AIRBYTE_SCHEMA populated with source tables
          data/ground_truth/ populated with expected outputs
```

### Phase 2: Agent Execution (Iterative)
```
┌─────────────────────────────────────────────────────────────┐
│ Agent operates in: data/inputs/<problem>/                   │
│                                                             │
│ 1. Reads problem requirements                               │
│    ├── config.yaml (source table info)                     │
│    ├── data_model.yaml (target schema)                     │
│    ├── schemas/ (source schemas)                           │
│    └── snowflake_credential.json (connection)              │
├─────────────────────────────────────────────────────────────┤
│ 2. Generates transformation code                            │
│    └── Transform: dbt, SQL queries                         │
├─────────────────────────────────────────────────────────────┤
│ 3. Executes transformations                                 │
│    ├── Reads from AIRBYTE_SCHEMA (source tables)           │
│    └── Writes to AIRBYTE_SCHEMA (target tables)            │
└─────────────────────────────────────────────────────────────┘
                           ↓
            Transformed data in AIRBYTE_SCHEMA
```

### Phase 3: Evaluation (Validation)
```
┌─────────────────────────────────────────────────────────────┐
│ Run: python evaluation/eva.py --folder <name> --example_index 0-99 │
│                                                             │
│ 1. Stage 1: Source Table Validation                        │
│    ├── Connects to Snowflake                               │
│    ├── Queries source tables in AIRBYTE_SCHEMA             │
│    ├── Compares vs data/ground_truth/<problem>/*.csv       │
│    └── Logs to data/results/<folder>/eval_<problem>/stage1.log │
├─────────────────────────────────────────────────────────────┤
│ 2. Stage 2: Transformation Validation                       │
│    ├── Runs SQL queries from evaluation/<problem>/*.sql    │
│    ├── Compares results vs ground truth                    │
│    └── Logs to data/results/<folder>/eval_<problem>/stage2.log │
└─────────────────────────────────────────────────────────────┘
                           ↓
        Results saved to data/results/<folder>/
```

### Directory Interaction Map
```
elt-bench/          (read-only templates)
    ↓ copied by write_config.py
data/inputs/        (agent workspace)
    ↓ agent reads
  Agent             (generates transformation code, executes SQL/DBT)
    ↓ writes to
Snowflake           (AIRBYTE_SCHEMA - reads source, writes target)
    ↓ queried by
evaluation/         (validation scripts + SQL queries)
    ↓ compares against
data/ground_truth/  (expected outputs)
    ↓ results written to
data/results/       (evaluation logs & scores)
```

## Environment Setup

### Prerequisites

Before starting, ensure you have installed:

| Tool | Purpose | Installation Guide |
|------|---------|-------------------|
| **Docker** | Runs agent containers | [Install Docker](https://docs.docker.com/get-docker/) |
| **Conda** | Python environment management | [Install Conda](https://docs.conda.io/projects/conda/en/stable/user-guide/install/index.html) |

### Setup Steps

#### 1. Install Conda Environment

```bash
# Create and activate conda environment
conda create -y -n elt
conda activate elt
conda install -y python=3.11

# Install Python dependencies
cd setup
pip install -r requirements.txt
```

#### 2. Configure Snowflake (Data Destination)

**2.1. Create Snowflake Resources**

Execute the SQL script in your Snowflake account:

```bash
# Copy contents of setup/destination/setup.sql
# Paste into Snowflake worksheet and run "Run All"
```

This creates:
- Database: `AIRBYTE_DATABASE`
- Warehouse: `AIRBYTE_WAREHOUSE`
- Role: `AIRBYTE_ROLE`
- User: `AIRBYTE_USER` (password: `Snowflake@123`)
- Schema: `AIRBYTE_SCHEMA`

**2.2. Fill Snowflake Credentials**

Edit `setup/destination/snowflake_credential.json`:

```json
{
  "account": "your-account.region.snowflakecomputing.com",
  "user": "AIRBYTE_USER",
  "password": "Snowflake@123"
}
```

**Important:** Use role `AIRBYTE_ROLE`, **not** `SYSADMIN`.

#### 3. Run Main Setup Script

Execute the setup script to:
- Download source data and ground truth (via `gdown`)
- Extract to `data/` directory
- Generate `data/inputs/` with credentials

```bash
cd setup
bash elt_setup.sh
```

**What this does:**
1. Downloads three ZIP files:
   - `data_api.zip` - API source data
   - `data_db.zip` - Database source data
   - `gt.zip` - Ground truth validation data
2. Extracts archives to `data/source/` and `data/ground_truth/`
3. Runs `write_config.py` to generate `data/inputs/` with Snowflake credentials

**Expected output structure:**
```
data/
├── inputs/           # 100 problem folders with credentials
├── source/
│   ├── api/         # API data files
│   └── db/          # Database dumps
└── ground_truth/    # Expected outputs (100 folders)
```

#### 4. Load Source Data to Snowflake

Upload source data to Snowflake's `AIRBYTE_SCHEMA`:

```bash
# From project root
python3 dev/snowflake-connector/upload_tables.py --example_index 0-99
```

**Parameters:**
- `--example_index 0-99`: Uploads all 100 problems (inclusive range)
- `--example_index 0-4`: Uploads only problems 0-4
- `--example_index 2,5,7`: Uploads specific problems

**Verification:**
After upload, check Snowflake for source tables in `AIRBYTE_DATABASE.AIRBYTE_SCHEMA`.

### Troubleshooting Setup

| Issue | Solution |
|-------|----------|
| `gdown` fails to download | Check internet connection, Google Drive quota |
| Snowflake connection fails | Verify credentials in `setup/destination/snowflake_credential.json` |
| `data/inputs/` empty after setup | Run `python3 setup/write_config.py` manually |

## Running Agents

See the `agents/` directory for instructions and examples:
- **`agents/spider-agent/`**: Spider-based agent implementation



## Evaluation

The evaluation framework validates agent performance across two stages:
- **Stage 1**: Source table validation - verifies source data is present in Snowflake's AIRBYTE_SCHEMA
- **Stage 2**: Transformation validation - validates transformed output against expected results

### Running Evaluation

```bash
cd evaluation
python eva.py --folder <folder_name> --example_index <range>
```

**Parameters:**

| Parameter | Description | Examples |
|-----------|-------------|----------|
| `--folder` | Name for this evaluation run | `spider_run_1`, `my_agent_test` |
| `--example_index` | Problems to evaluate | `0-99` (all), `0-4` (range), `2,5,7` (specific) |

**Examples:**

```bash
# Evaluate first 5 problems for testing
python eva.py --folder quick_test --example_index 0-4
```

```bash
# Evaluate specific problems
python eva.py --folder targeted_test --example_index 10,25,50,75
```

### Evaluation Output

Results are saved to `data/results/<folder>/`:

```
data/results/
└── <folder_name>/              # Your evaluation run
    ├── eval_address/           # Results for "address" problem
    │   ├── stage1.log          # EL validation logs
    │   └── stage2.log          # Transform validation logs
    ├── eval_airline/           # Results for "airline" problem
    │   ├── stage1.log
    │   └── stage2.log
    └── ... (for each evaluated problem)
```

### Automated Timestamping

**Note:** Evaluation runs are automatically timestamped to prevent overwriting previous results. You can specify a custom folder name with `--folder` for organization.
