# ELT-Bench
The first comprehensive, end-to-end benchmark designed to evaluate AI agents in automating ELT pipelines.
![ELT](https://anonymous.4open.science/r/ELT-Bench-B51C/materials/elt.svg)

## Table of Contents
- [Overview](#overview)
- [Project Structure](#project-structure)
  - [Directory Layout (Before Setup)](#directory-layout-before-setup)
  - [How Setup Transforms the Structure](#how-setup-transforms-the-structure)
  - [Directory Roles and Responsibilities](#directory-roles-and-responsibilities)
- [Workflow Overview](#workflow-overview)
- [Environment Setup](#environment-setup)
- [Running Agents](#running-agents)
- [Evaluation](#evaluation)
- [Common Issues and Solutions](#common-issues-and-solutions)
- [Project Maintenance](#project-maintenance)

## Overview

ELT-Bench is a benchmark suite containing **100 ELT pipeline problems** that test AI agents' ability to:
1. **Extract** data from various sources (PostgreSQL, MongoDB, S3, APIs, files)
2. **Load** data into Snowflake
3. **Transform** data according to specified requirements

The project uses a **two-tier structure**:
- **`elt-bench/`**: Read-only benchmark definitions (committed to Git)
- **`data/`**: Generated working environment (gitignored, recreated by setup)

## Project Structure

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
│   ├── data_setup.sh                  # Database initialization script
│   ├── check_job_status.py            # Job monitoring helper (copied to inputs)
│   ├── main.tf                        # Terraform template (copied to inputs)
│   ├── mongo.py                       # MongoDB data loader
│   ├── requirements.txt               # Python dependencies
│   ├── elt_bench.yaml                 # Airbyte connector definition
│   │
│   ├── airbyte/                       # Airbyte credentials (user-filled)
│   │   └── airbyte_credential.json    # {username, password, workspace_id, api_definition_id}
│   │
│   ├── destination/                   # Snowflake credentials (user-filled)
│   │   ├── snowflake_credential.json  # {account, user, password}
│   │   └── setup.sql                  # Snowflake setup SQL
│   │
│   └── sources/                       # Source database setup scripts
│       ├── postgres_setup.sql         # PostgreSQL schema & data
│       └── ...
│
├── elt-docker/                         # 🐳 DOCKER INFRASTRUCTURE
│   ├── docker-compose.yml             # Defines: PostgreSQL, MongoDB, S3 (LocalStack), APIs
│   └── rest_api/                      # (Created by setup) API source data
│
├── evaluation/                         # ✅ EVALUATION FRAMEWORK
│   ├── eva.py                         # Main evaluation orchestrator
│   ├── eva_stage1.py                  # Stage 1: Data extraction/loading validator
│   ├── eva_stage2.py                  # Stage 2: Data transformation validator
│   ├── table.json                     # Table metadata for validation
│   │
│   └── address/, airline/, ... (100)  # Expected SQL queries per problem
│       └── *.sql                      # Query definitions for comparison
│
├── agents/                             # 🤖 AGENT IMPLEMENTATIONS
│   ├── spider-agent/                  # Spider Agent implementation
│   └── SWE-agent/                     # SWE Agent implementation
│
├── documentation/                      # 📚 API/PROVIDER DOCUMENTATION
│   ├── connection.md                  # Connection guidelines
│   ├── source_postgres.md             # PostgreSQL source docs
│   ├── source_mongodb_v2.md           # MongoDB source docs
│   ├── source_s3.md                   # S3 source docs
│   ├── source_file.md                 # File source docs
│   ├── source_custom_api.md           # Custom API source docs
│   ├── destination_snowflake.md       # Snowflake destination docs
│   ├── airbyte_Provider.md            # Airbyte provider docs
│   └── trigger_job.md                 # Job triggering docs
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

#### Step 3: Start Docker Infrastructure
```bash
cd ../elt-docker
docker compose up -d
```
Launches containers:
- PostgreSQL (port 5432)
- MongoDB (port 27017)
- LocalStack S3 (port 4566)
- REST API servers (various ports)

#### Step 4: Generate Working Directories (`write_config.py`)
For each of the 100 problems in `elt-bench/`, creates a working copy in `data/inputs/` with:

**Original files (copied from `elt-bench/<problem>/`):**
- `config.yaml` (modified - see below)
- `data_model.yaml`
- `schemas/` directory

**Injected credentials:**
- Updates `config.yaml` with Snowflake account from `setup/destination/snowflake_credential.json`
- Updates `config.yaml` with Airbyte credentials from `setup/airbyte/airbyte_credential.json`
- Creates `snowflake_credential.json` with connection details

**Added resources:**
- `documentation/` (entire directory copied from root)
- `check_job_status.py` (copied from `setup/`)
- `elt/main.tf` (Terraform template copied from `setup/`)

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
│   │   │   ├── config.yaml            # ✏️ Modified with credentials
│   │   │   ├── data_model.yaml        # Copied from elt-bench/
│   │   │   ├── schemas/               # Copied from elt-bench/
│   │   │   ├── snowflake_credential.json  # ✨ Created (Snowflake auth)
│   │   │   ├── documentation/         # 📚 Copied from root
│   │   │   ├── check_job_status.py    # 🔍 Monitoring helper
│   │   │   └── elt/                   # 🏗️ Created directory
│   │   │       └── main.tf            # Terraform template
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
│           │   ├── stage1.log         # Extraction/loading validation
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
    └── rest_api/                       # 🌐 (symlinked/copied from data/source/api/)
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
| **`elt-docker/`** | Docker infrastructure | ❌ Infrastructure | ✅ Yes |
| **`agents/`** | Agent implementations | 👤 User develops | ✅ Yes |
| **`documentation/`** | API/provider guides | ❌ Reference material | ✅ Yes |
| **`dev/`** | Development utilities | 👤 Helper tools | ✅ Yes |

**Key Principles:**
- **`elt-bench/`** is the source of truth (never modify directly)
- **`data/`** is ephemeral (can be deleted and regenerated)
- **Agents only work in `data/inputs/`** (isolated from originals)
- **Credentials never committed** (stored in `setup/`, injected into `data/inputs/`)

**File Flow Summary:**
```
elt-bench/<problem>/          →  (write_config.py)  →  data/inputs/<problem>/
├── config.yaml (template)                            ├── config.yaml (+ credentials)
├── data_model.yaml                                   ├── data_model.yaml
└── schemas/                                          ├── schemas/
                                                      ├── snowflake_credential.json (new)
documentation/ (root)         →  (copied)         →  ├── documentation/
setup/check_job_status.py     →  (copied)         →  ├── check_job_status.py
setup/main.tf                 →  (copied)         →  └── elt/main.tf

setup/data_*.zip              →  (extracted)      →  data/source/{api,db}/
setup/gt.zip                  →  (extracted)      →  data/ground_truth/
```
## Workflow Overview

The complete ELT-Bench workflow consists of three phases:

### Phase 1: Setup (One-time)
```
┌─────────────────────────────────────────────────────────────┐
│ 1. User fills credentials                                   │
│    ├── setup/airbyte/airbyte_credential.json               │
│    └── setup/destination/snowflake_credential.json         │
├─────────────────────────────────────────────────────────────┤
│ 2. Run setup/elt_setup.sh                                   │
│    ├── Downloads ZIPs (data_api, data_db, gt)              │
│    ├── Extracts to data/ directory                         │
│    ├── Starts Docker containers                            │
│    └── Runs write_config.py                                │
├─────────────────────────────────────────────────────────────┤
│ 3. write_config.py generates data/inputs/                   │
│    ├── Copies elt-bench/ → data/inputs/                    │
│    ├── Injects credentials into config.yaml                │
│    ├── Creates snowflake_credential.json                   │
│    └── Adds documentation, helpers, templates              │
└─────────────────────────────────────────────────────────────┘
                           ↓
          data/inputs/ ready for agents
          data/source/ populated with source data
          data/ground_truth/ populated with expected outputs
```

### Phase 2: Agent Execution (Iterative)
```
┌─────────────────────────────────────────────────────────────┐
│ Agent operates in: data/inputs/<problem>/                   │
│                                                             │
│ 1. Reads problem requirements                               │
│    ├── config.yaml (sources, credentials)                  │
│    ├── data_model.yaml (target schema)                     │
│    └── documentation/ (API guides)                         │
├─────────────────────────────────────────────────────────────┤
│ 2. Generates ELT pipeline code                              │
│    ├── Extract: Airbyte connectors, Python scripts         │
│    ├── Load: Snowflake SQL, Terraform                      │
│    └── Transform: dbt, SQL, Python                         │
├─────────────────────────────────────────────────────────────┤
│ 3. Executes pipeline                                        │
│    ├── Triggers data extraction                            │
│    ├── Loads to Snowflake                                  │
│    ├── Runs transformations                                │
│    └── Uses check_job_status.py to monitor                 │
└─────────────────────────────────────────────────────────────┘
                           ↓
            Data loaded into Snowflake
```

### Phase 3: Evaluation (Validation)
```
┌─────────────────────────────────────────────────────────────┐
│ Run: python evaluation/eva.py --folder <name> --example_index 0-99 │
│                                                             │
│ 1. Stage 1: Extraction/Loading Validation                  │
│    ├── Connects to Snowflake                               │
│    ├── Queries raw tables                                  │
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
data/inputs/        (agent workspace - credentials injected)
    ↓ agent reads
  Agent             (generates code, executes pipeline)
    ↓ writes to
Snowflake           (destination database)
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
| **Docker** | Runs PostgreSQL, MongoDB, S3, API sources | [Install Docker](https://docs.docker.com/get-docker/) |
| **Conda** | Python environment management | [Install Conda](https://docs.conda.io/projects/conda/en/stable/user-guide/install/index.html) |
| **Airbyte** | Data integration platform (optional*) | [Airbyte OSS Quickstart](https://docs.airbyte.com/using-airbyte/getting-started/oss-quickstart) |
| **psql** | PostgreSQL CLI (optional*) | [Install psql](https://www.timescale.com/blog/how-to-install-psql-on-mac-ubuntu-debian-windows) |

**Note:** *Optional components only needed for full Extract-Load workflow. Transform-only workflows can skip Airbyte and psql.

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

#### 3. Configure Airbyte (Optional - for EL stages)

**3.1. Deploy Airbyte**

```bash
# May require sudo depending on your setup
abctl local install

# Retrieve credentials
abctl local credentials
```

**3.2. Import Custom Connector**

1. Navigate to [http://localhost:8000/](http://localhost:8000/)
2. Login with credentials from step 3.1
3. Go to **Builder > Import a YAML**
4. Upload `setup/elt_bench.yaml`
5. Click **Publish** → type "ignore warnings" → Publish to workspace

**3.3. Get Workspace & Definition IDs**

1. Go to **Sources > Custom > ELT Bench**
2. Extract IDs from URL:
   ```
   http://localhost:8012/workspaces/<workspace_id>/source/new-source/<api_definition_id>
   ```

**3.4. Fill Airbyte Credentials**

Edit `setup/airbyte/airbyte_credential.json`:

```json
{
  "username": "your-username",
  "password": "your-password",
  "workspace_id": "your-workspace-id",
  "api_definition_id": "your-api-definition-id"
}
```

#### 4. Run Main Setup Script

Execute the setup script to:
- Download source data and ground truth (via `gdown`)
- Extract to `data/` directory
- Start Docker containers
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
3. Starts Docker containers (PostgreSQL, MongoDB, LocalStack S3, APIs)
4. Runs `write_config.py` to generate `data/inputs/` with injected credentials

**Expected output structure:**
```
data/
├── inputs/           # 100 problem folders with credentials
├── source/
│   ├── api/         # API data files
│   └── db/          # Database dumps
└── ground_truth/    # Expected outputs (100 folders)
```

#### 5. Load Data to Snowflake

Upload benchmark data to Snowflake:

```bash
# From project root
python3 dev/snowflake-connector/upload_tables.py --example_index 0-99
```

**Parameters:**
- `--example_index 0-99`: Uploads all 100 problems (inclusive range)
- `--example_index 0-4`: Uploads only problems 0-4
- `--example_index 2,5,7`: Uploads specific problems

**Verification:**
After upload, check Snowflake for tables in `AIRBYTE_DATABASE.AIRBYTE_SCHEMA`.

### Optional: Database-Specific Setup (for EL stages)

If working with Extract-Load stages, you may need to populate source databases:

```bash
cd setup

# Initialize PostgreSQL tables
bash data_setup.sh $(pwd)

# Load MongoDB data
python3 mongo.py --path $(pwd)
```

### Troubleshooting Setup

| Issue | Solution |
|-------|----------|
| `gdown` fails to download | Check internet connection, Google Drive quota |
| Docker containers fail to start | Check port availability (5432, 27017, 4566) |
| Snowflake connection fails | Verify credentials in `setup/destination/snowflake_credential.json` |
| `data/inputs/` empty after setup | Run `python3 setup/write_config.py` manually |
| Airbyte UI not accessible | Ensure Airbyte is running: `abctl local status` |

## Running Agents

Agents work within the `data/inputs/<problem>/` directory structure. Each problem folder contains everything an agent needs to build and execute an ELT pipeline.

### Agent Input Structure

For each problem in `data/inputs/<problem>/`:

```
data/inputs/address/
├── config.yaml                 # Data source configurations (with credentials)
├── data_model.yaml             # Required output schema definition
├── schemas/                    # Source data schemas
│   ├── postgres_schema.json
│   ├── mongodb_schema.json
│   └── ...
├── snowflake_credential.json   # Snowflake connection details
├── documentation/              # API/provider documentation
│   ├── source_postgres.md
│   ├── source_mongodb_v2.md
│   ├── destination_snowflake.md
│   └── ...
├── check_job_status.py         # Helper to monitor pipeline execution
└── elt/                        # Agent's working directory
    └── main.tf                 # Terraform template (if needed)
```

### Agent Workflow

1. **Read Problem Requirements**
   - `config.yaml`: Identifies data sources (PostgreSQL, MongoDB, S3, APIs, files)
   - `data_model.yaml`: Defines target schema and transformations
   - `schemas/`: Provides source data structures

2. **Generate Pipeline Code**
   - **Extract**: Create Airbyte connections, API calls, or file readers
   - **Load**: Write Snowflake DDL, configure destinations
   - **Transform**: Generate SQL transformations, dbt models, or Python scripts

3. **Execute Pipeline**
   - Deploy infrastructure (Terraform, Airbyte connectors)
   - Trigger data extraction and loading
   - Run transformations
   - Use `check_job_status.py` to monitor progress

4. **Output to Snowflake**
   - Tables loaded to: `AIRBYTE_DATABASE.AIRBYTE_SCHEMA.<table_name>`
   - Agent should ensure data matches `data_model.yaml` specifications

### Agent Implementations

See the `agents/` directory for example implementations:

- **`agents/spider-agent/`**: Spider-based agent implementation
- **`agents/SWE-agent/`**: SWE-agent implementation

Each agent directory contains:
- Setup instructions
- Configuration files
- Execution scripts
- Documentation

### Development Utilities

Agents can use the following utilities:

| Utility | Location | Purpose |
|---------|----------|---------|
| `check_job_status.py` | Each `data/inputs/<problem>/` | Monitor Airbyte job status |
| `upload_tables.py` | `dev/snowflake-connector/` | Upload data to Snowflake |
| `csv_checker.py` | `dev/` | Validate CSV outputs |

### Agent Best Practices

1. **Never modify `elt-bench/`** - Always work in `data/inputs/`
2. **Use provided credentials** - Read from `config.yaml` and `snowflake_credential.json`
3. **Follow schema specifications** - Match output to `data_model.yaml`
4. **Log progress** - Use `check_job_status.py` for monitoring
5. **Handle errors gracefully** - Implement retry logic for transient failures

## Evaluation

The evaluation framework validates agent performance across two stages:
- **Stage 1**: Data extraction and loading (EL) - verifies raw data in Snowflake
- **Stage 2**: Data transformation (T) - validates transformed output against expected results

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
# Evaluate all 100 problems
python eva.py --folder full_evaluation --example_index 0-99

# Evaluate first 5 problems for testing
python eva.py --folder quick_test --example_index 0-4

# Evaluate specific problems
python eva.py --folder targeted_test --example_index 10,25,50,75
```

### Evaluation Process

```
┌──────────────────────────────────────────────────────────────┐
│ Stage 1: Extraction & Loading Validation (eva_stage1.py)    │
├──────────────────────────────────────────────────────────────┤
│ 1. Connects to Snowflake                                     │
│ 2. Queries raw tables in AIRBYTE_DATABASE.AIRBYTE_SCHEMA    │
│ 3. Compares against: data/ground_truth/<problem>/*.csv      │
│ 4. Validates:                                                │
│    ├── Row counts match                                      │
│    ├── Column names match                                    │
│    ├── Data types correct                                    │
│    └── Values match expected data                           │
│ 5. Logs results to: data/results/<folder>/eval_<problem>/stage1.log │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│ Stage 2: Transformation Validation (eva_stage2.py)          │
├──────────────────────────────────────────────────────────────┤
│ 1. Reads SQL queries from: evaluation/<problem>/*.sql       │
│ 2. Executes queries against Snowflake                       │
│ 3. Compares results against ground truth                    │
│ 4. Validates:                                                │
│    ├── Transformation logic correct                         │
│    ├── Aggregations accurate                                │
│    ├── Joins produce expected results                       │
│    └── Final schema matches data_model.yaml                 │
│ 5. Logs results to: data/results/<folder>/eval_<problem>/stage2.log │
└──────────────────────────────────────────────────────────────┘
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

**Log Format:**

Each log contains:
- **Timestamp**: When evaluation ran
- **Problem Name**: Which problem was evaluated
- **Stage**: Stage 1 or Stage 2
- **Status**: PASS/FAIL
- **Details**: 
  - Row count comparisons
  - Schema validations
  - Data mismatches (if any)
  - Error messages (if failed)

### Evaluation Requirements

Before running evaluation, ensure:

1. **Ground truth exists**: `data/ground_truth/` populated by `setup/elt_setup.sh`
2. **SQL queries exist**: `evaluation/<problem>/*.sql` present
3. **Snowflake has data**: Agent successfully loaded data
4. **Credentials configured**: Snowflake connection works

### Understanding Results

**Stage 1 Pass Criteria:**
- All expected tables exist in Snowflake
- Row counts match ground truth
- Column names and types match
- Data values match ground truth CSVs

**Stage 2 Pass Criteria:**
- Transformation queries execute successfully
- Results match expected output
- Data model requirements satisfied
- All business logic correctly implemented

**Common Failure Reasons:**

| Failure | Cause | Solution |
|---------|-------|----------|
| Stage 1: Table not found | Agent didn't load data | Check agent logs, verify pipeline ran |
| Stage 1: Row count mismatch | Incomplete extraction | Verify source data availability |
| Stage 1: Schema mismatch | Wrong column types | Check `schemas/` and fix data types |
| Stage 2: Query error | Transformation logic wrong | Review `data_model.yaml`, fix SQL |
| Stage 2: Result mismatch | Incorrect aggregation | Debug transformation code |

### Automated Timestamping

**Note:** Evaluation runs are automatically timestamped to prevent overwriting previous results. You can specify a custom folder name with `--folder` for organization.

## Common Issues and Solutions

### Setup Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **Missing `data/inputs/`** | Agent can't find problem folders | Run `cd setup && bash elt_setup.sh` |
| **Empty `data/inputs/`** | Folders exist but no files | Run `cd setup && python3 write_config.py` |
| **Missing ground truth** | Evaluation fails: "ground truth not found" | Re-run `elt_setup.sh` to extract `gt.zip` |
| **Download fails** | `gdown` errors | Check internet, Google Drive quota, retry |
| **Docker containers fail** | Can't connect to PostgreSQL/MongoDB | Check ports 5432, 27017, 4566 not in use |

### Credential Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **Snowflake connection fails** | "Authentication failed" | Verify `setup/destination/snowflake_credential.json` |
| **Wrong Snowflake role** | Permission denied errors | Use `AIRBYTE_ROLE`, not `SYSADMIN` |
| **Airbyte auth fails** | Can't connect to Airbyte API | Verify `setup/airbyte/airbyte_credential.json` |
| **Credentials not in `data/inputs/`** | Agents can't connect | Re-run `python3 setup/write_config.py` |

### Data Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **Tables not in Snowflake** | Evaluation fails: "table not found" | Run `python3 dev/snowflake-connector/upload_tables.py --example_index 0-99` |
| **Partial data in Snowflake** | Row count mismatches | Check source data in `data/source/`, re-upload |
| **Source database empty** | No data to extract | Run `cd setup && bash data_setup.sh $(pwd)` |
| **MongoDB data missing** | MongoDB queries return no results | Run `cd setup && python3 mongo.py --path $(pwd)` |

### Evaluation Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **"Ground truth not found"** | Can't find CSV files | Ensure `data/ground_truth/` populated by setup |
| **SQL query files missing** | Stage 2 fails | Check `evaluation/<problem>/*.sql` exists |
| **Stage 1 passes, Stage 2 fails** | Data loaded but transformations wrong | Review agent's transformation logic |
| **Results overwritten** | Previous results lost | Use unique `--folder` names or rely on auto-timestamping |

### Directory Confusion

**Problem:** Unclear whether to work in `elt-bench/` or `data/inputs/`

**Solution:**
- **`elt-bench/`**: Source of truth, **never modify** directly
- **`data/inputs/`**: Working copies for agents, **safe to modify**
- To reset: Delete `data/inputs/` and re-run `setup/write_config.py`

### Reset Workflows

**Reset generated data (keep credentials):**
```bash
rm -rf data/inputs/
cd setup
python3 write_config.py
```

**Reset evaluation results:**
```bash
rm -rf data/results/*
```

**Complete reset (re-download everything):**
```bash
rm -rf data/
cd setup
bash elt_setup.sh
```

**Reset Snowflake data:**
```sql
-- In Snowflake worksheet
USE DATABASE AIRBYTE_DATABASE;
USE SCHEMA AIRBYTE_SCHEMA;
DROP SCHEMA AIRBYTE_SCHEMA CASCADE;
CREATE SCHEMA AIRBYTE_SCHEMA;
```

Then re-upload:
```bash
python3 dev/snowflake-connector/upload_tables.py --example_index 0-99
```

## Project Maintenance

### Regenerating `data/inputs/` Directory

If credentials change or you need fresh working copies:

```bash
cd setup
python3 write_config.py
```

**What happens:**
1. Deletes existing `data/inputs/` (if present)
2. Copies all 100 problems from `elt-bench/` → `data/inputs/`
3. Injects current credentials from:
   - `setup/destination/snowflake_credential.json`
   - `setup/airbyte/airbyte_credential.json`
4. Creates `snowflake_credential.json` in each problem folder
5. Copies `documentation/`, `check_job_status.py`, `elt/main.tf`

**Use cases:**
- Updated Snowflake credentials
- Updated Airbyte workspace/definition IDs
- Corrupted `data/inputs/` needs reset
- Want to test with fresh environment

### Updating Credentials

**Step 1: Update credential files**

```bash
# Edit Snowflake credentials
vim setup/destination/snowflake_credential.json

# Edit Airbyte credentials
vim setup/airbyte/airbyte_credential.json
```

**Step 2: Propagate to working directories**

```bash
cd setup
python3 write_config.py
```

All 100 problem folders in `data/inputs/` will receive updated credentials.

### Cleaning Evaluation Results

**Remove all evaluation runs:**
```bash
rm -rf data/results/*
```

**Remove specific run:**
```bash
rm -rf data/results/my_old_run/
```

**Archive before cleaning:**
```bash
# Create archive
tar -czf evaluation_archive_$(date +%Y%m%d).tar.gz data/results/

# Then clean
rm -rf data/results/*
```

### Resetting to Fresh State

**Option 1: Full reset (everything)**
```bash
# Remove all generated data
rm -rf data/

# Re-run complete setup
cd setup
bash elt_setup.sh

# Re-upload to Snowflake
cd ..
python3 dev/snowflake-connector/upload_tables.py --example_index 0-99
```

**Option 2: Partial reset (keep downloaded data)**
```bash
# Remove only working directories and results
rm -rf data/inputs/ data/results/

# Regenerate working directories
cd setup
python3 write_config.py
```

**Option 3: Reset only evaluation**
```bash
rm -rf data/results/*
```

### Version Control Best Practices

**What to commit:**
- ✅ `elt-bench/` (benchmark definitions)
- ✅ `setup/*.py`, `setup/*.sh` (setup scripts)
- ✅ `evaluation/` (evaluation framework)
- ✅ `agents/` (agent implementations)
- ✅ `documentation/` (API docs)
- ✅ `dev/` (development utilities)

**What to ignore (already in `.gitignore`):**
- ❌ `data/` (all generated content)
- ❌ `setup/*.zip` (downloaded archives)
- ❌ `setup/*_credential.json` (credentials)
- ❌ `__pycache__/` (Python cache)
- ❌ `*.pyc` (compiled Python)

### Maintaining Data Integrity

**Verify ground truth integrity:**
```bash
# Check if ground truth exists for all problems
for i in {0..99}; do
  problem=$(ls -d elt-bench/* | sed -n "$((i+1))p" | xargs basename)
  if [ ! -d "data/ground_truth/$problem" ]; then
    echo "Missing: $problem"
  fi
done
```

**Verify `data/inputs/` completeness:**
```bash
# Should show 100 directories
ls -d data/inputs/*/ | wc -l

# Check each has required files
for dir in data/inputs/*/; do
  if [ ! -f "$dir/config.yaml" ] || [ ! -f "$dir/snowflake_credential.json" ]; then
    echo "Incomplete: $dir"
  fi
done
```

**Verify Snowflake tables:**
```sql
-- In Snowflake worksheet
USE DATABASE AIRBYTE_DATABASE;
USE SCHEMA AIRBYTE_SCHEMA;

-- Count tables (should have tables for loaded problems)
SHOW TABLES;

-- Check specific table
SELECT COUNT(*) FROM address_table;
```

### Adding New Problems

To add a new benchmark problem:

1. **Create problem folder in `elt-bench/`:**
   ```bash
   mkdir elt-bench/new_problem
   ```

2. **Add required files:**
   ```
   elt-bench/new_problem/
   ├── config.yaml          # Source configurations
   ├── data_model.yaml      # Target schema
   └── schemas/             # Source schemas
   ```

3. **Create evaluation queries:**
   ```bash
   mkdir evaluation/new_problem
   # Add *.sql files with expected queries
   ```

4. **Add ground truth:**
   ```bash
   mkdir data/ground_truth/new_problem
   # Add expected output CSVs
   ```

5. **Regenerate working directory:**
   ```bash
   cd setup
   python3 write_config.py
   ```

### Monitoring Disk Usage

The `data/` directory can grow large:

```bash
# Check total size
du -sh data/

# Check breakdown
du -sh data/*/

# Largest problem folders
du -sh data/inputs/* | sort -h | tail -20
```

**Space-saving tips:**
- Delete `data/results/` after archiving
- Keep only recent evaluation runs
- Compress old archives: `tar -czf old_results.tar.gz data/results/old_run/`

---

## Quick Reference

### Essential Commands

**Initial Setup:**
```bash
# 1. Create conda environment
conda create -y -n elt && conda activate elt && conda install -y python=3.11

# 2. Install dependencies
cd setup && pip install -r requirements.txt

# 3. Fill credentials (edit these files)
vim setup/destination/snowflake_credential.json
vim setup/airbyte/airbyte_credential.json

# 4. Run setup
bash elt_setup.sh

# 5. Upload to Snowflake
cd .. && python3 dev/snowflake-connector/upload_tables.py --example_index 0-99
```

**Run Evaluation:**
```bash
cd evaluation
python eva.py --folder <run_name> --example_index 0-99
```

**Regenerate Working Directories:**
```bash
cd setup
python3 write_config.py
```

### Key File Locations

| What You Need | Where to Find It |
|---------------|------------------|
| **Problem definitions** | `elt-bench/<problem>/` |
| **Agent workspace** | `data/inputs/<problem>/` |
| **Source data** | `data/source/api/` and `data/source/db/` |
| **Ground truth** | `data/ground_truth/<problem>/` |
| **Evaluation results** | `data/results/<folder>/` |
| **Snowflake credentials** | `setup/destination/snowflake_credential.json` |
| **Airbyte credentials** | `setup/airbyte/airbyte_credential.json` |
| **SQL validation queries** | `evaluation/<problem>/*.sql` |

### Directory Quick Guide

```
elt-bench/          ← Original problems (DON'T MODIFY)
data/inputs/        ← Agent workspace (AGENTS WORK HERE)
data/ground_truth/  ← Expected outputs (FOR VALIDATION)
data/results/       ← Evaluation logs (GENERATED)
setup/              ← Setup scripts + credentials (USER FILLS)
evaluation/         ← Validation framework (RUNS EVALUATION)
```

### Common Workflows

**Test agent on one problem:**
```bash
# Run agent on data/inputs/address/
<your_agent_command>

# Evaluate
cd evaluation
python eva.py --folder test_run --example_index 0
```

**Full benchmark run:**
```bash
# Run agent on all 100 problems
<your_agent_loop_command>

# Evaluate all
cd evaluation
python eva.py --folder full_run --example_index 0-99
```

**Reset everything:**
```bash
rm -rf data/
cd setup && bash elt_setup.sh
cd .. && python3 dev/snowflake-connector/upload_tables.py --example_index 0-99
```

### Support & Documentation

- **API Documentation**: See `documentation/` folder
- **Agent Examples**: See `agents/` folder  
- **Setup Issues**: See [Common Issues](#common-issues-and-solutions) section
- **Evaluation Details**: See [Evaluation](#evaluation) section

---

**Built with ❤️ for AI agent ELT pipeline benchmarking**