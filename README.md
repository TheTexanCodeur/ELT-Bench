# ELT-Bench
The first comprehensive, end-to-end benchmark designed to evaluate AI agents in automating ELT pipelines.
![ELT](https://anonymous.4open.science/r/ELT-Bench-B51C/materials/elt.svg)

## Table of Contents
- [Project Structure](#project-structure)
  - [Initial Structure (Before Setup)](#initial-structure-before-setup)
  - [Structure After Setup](#structure-after-setup-elt_setupsh)
  - [Key Directory Roles](#key-directory-roles)
- [Workflow Overview](#workflow-overview)
- [Environment Setup](#environment-setup)
- [Running Agents](#running-agents)
- [Evaluation](#evaluation)
- [Common Issues and Solutions](#common-issues-and-solutions)
- [Project Maintenance](#project-maintenance)

## Project Structure

### Initial Structure (Before Setup)
```
ELT-Bench/
├── README.md                           # This file
├── elt-bench/                          # 100 benchmark problems (source definitions)
│   ├── address/
│   │   ├── config.yaml                # Problem configuration
│   │   ├── data_model.yaml            # Data model definition
│   │   └── schemas/                   # Source schemas
│   ├── airline/
│   └── ... (98 more problems)
├── setup/                              # Setup scripts and credentials
│   ├── elt_setup.sh                   # Main setup script
│   ├── data_setup.sh                  # Database setup script
│   ├── write_config.py                # Config generator for workspace
│   ├── airbyte/                       # Airbyte credentials
│   ├── destination/                   # Snowflake credentials
│   ├── sources/                       # Source database setup scripts
│   └── *.zip                          # Downloaded data archives
├── elt-docker/                         # Docker compose for data sources
│   └── docker-compose.yml
├── agents/                             # Agent implementations
│   ├── spider-agent/
│   └── SWE-agent/
├── evaluation/                         # Evaluation scripts
│   ├── eva.py                         # Main evaluation script
│   ├── eva_stage1.py                  # Stage 1 evaluator
│   ├── eva_stage2.py                  # Stage 2 evaluator
│   ├── address/                       # Expected SQL queries per problem
│   └── ...
├── data/                               # (Created during setup - all generated content)
├── example/                            # Example usage
├── dev/                                # Development utilities
├── documentation/                      # API documentation
└── materials/                          # Project materials

```

### Structure After Setup (`elt_setup.sh`)

Running the setup script performs the following transformations:

1. **Downloads and extracts data to `data/` directory**:
   - `data_api.zip` → `data/source/api/` (API source data)
   - `data_db.zip` → `data/source/db/` (Database source data)
   - `gt.zip` → `data/ground_truth/` (ground truth for evaluation)

2. **Creates `data/inputs/` directory**:
   - Copies all 100 problems from `elt-bench/` to `data/inputs/`
   - Each problem folder in `data/inputs/` contains:
     - `config.yaml` (updated with Snowflake/Airbyte credentials)
     - `data_model.yaml`
     - `schemas/`
     - `snowflake_credential.json` (created)
     - `documentation/` (copied from root)
     - `check_job_status.py` (copied)
     - `elt/` (created with `main.tf`)

3. **All generated content organized under `data/`**:
   - Source data for problems in `data/source/`
   - Working copies for agents in `data/inputs/`
   - Ground truth for validation in `data/ground_truth/`
   - Evaluation results in `data/results/` (created when running evaluations)

**Final structure**:
```
ELT-Bench/
├── elt-bench/                          # Original benchmark definitions (unchanged)
├── data/                               # All generated content (gitignored)
│   ├── inputs/                         # Working copies with credentials
│   │   ├── address/
│   │   │   ├── config.yaml            # Updated with credentials
│   │   │   ├── data_model.yaml
│   │   │   ├── schemas/
│   │   │   ├── snowflake_credential.json
│   │   │   ├── documentation/
│   │   │   ├── check_job_status.py
│   │   │   └── elt/
│   │   └── ... (99 more)
│   ├── ground_truth/                   # Ground truth validation data
│   │   ├── address/
│   │   │   └── *.csv
│   │   └── ... (99 more)
│   ├── source/                         # Source data for problems
│   │   ├── api/                       # API data files
│   │   └── db/                        # Database data files
│   └── results/                        # Evaluation results
│       └── run_20241021_143052/
├── evaluation/                         # Evaluation scripts + SQL queries
│   ├── eva.py, eva_stage1.py, eva_stage2.py
│   ├── address/                       # Expected SQL queries
│   │   └── states.sql
│   └── ... (99 more)
├── elt-docker/                         # Docker configs (data moved to data/source/api/)
│   └── docker-compose.yml
├── setup/                              # Setup scripts (data moved to data/source/db/)
│   ├── elt_setup.sh
│   └── write_config.py
└── ... (other directories)
│   ├── address/
│   │   └── *.csv                      # Expected output data
│   ├── airline/
│   └── ... (98 more)
├── inputs/                             # Created: Working copies with credentials
│   ├── address/
│   │   ├── config.yaml                # Updated with credentials
│   │   ├── data_model.yaml
│   │   ├── schemas/
│   │   ├── snowflake_credential.json  # Created
│   │   ├── documentation/             # Copied
│   │   ├── check_job_status.py        # Copied
│   │   └── elt/                       # Created (contains main.tf)
│   └── ... (99 more)
├── evaluation/
│   ├── eva.py, eva_stage1.py, eva_stage2.py
│   ├── address/                       # Created: Expected query results per problem
│   │   └── states.sql
│   ├── airline/
│   └── ... (98 more)
├── results/                           # Created when running evaluation
│   └── <folder_name>/                 # Your evaluation results
├── elt-docker/
│   └── rest_api/                      # Created: API source data
├── setup/
│   └── data/                          # Created: Database source data
└── ... (other directories)
```

### Key Directory Roles

- **`elt-bench/`**: Read-only benchmark problem definitions (committed to Git, never modified)
- **`data/`**: All generated content (gitignored, can be regenerated)
  - **`data/inputs/`**: Working copies for agents with injected credentials
  - **`data/ground_truth/`**: Ground truth CSV data for validation
  - **`data/source/`**: Source data files (API and database data)
  - **`data/results/`**: Agent evaluation outputs (timestamped folders)
- **`evaluation/`**: Evaluation scripts and expected SQL queries per problem
- **`setup/`**: Setup scripts and credential templates
- **`elt-docker/`**: Docker compose configurations

## Workflow Overview

The typical workflow for using ELT-Bench:

```
1. Setup Phase
   ├── Run elt_setup.sh
   ├── Creates data/inputs/ from elt-bench/
   ├── Downloads and extracts all data to data/
   └── Starts Docker containers for data sources

2. Agent Phase
   ├── Agent reads problem from data/inputs/<problem>/
   ├── Agent generates ELT pipeline code
   └── Agent executes pipeline

3. Evaluation Phase
   ├── Run eva.py (auto-timestamped)
   ├── Compares agent output vs ground truth
   └── Results saved to data/results/<timestamped_folder>/
```

**Directory Flow:**
```
elt-bench/             →  data/inputs/         →  data/results/
(benchmark defs)          (working copies)        (evaluation outputs)
                          ↓
                      agents work here
                          ↓
data/ground_truth/     →  comparison  ←  agent outputs
(ground truth)
evaluation/<problem>/
(expected queries)
```
                    agents work here
                       ↓
ground_truth/       →  comparison  ←  agent outputs
(ground truth)
evaluation/<problem>/
(expected queries)
```

## Environment Setup

### Install Docker and Conda 
- Ensure your machine has the [Docker environment](https://docs.docker.com/get-docker/) and the [Conda environment](https://docs.conda.io/projects/conda/en/stable/user-guide/install/index.html) installed.

### Install Airbyte (not required if transform step only)
- You can deploy Airbyte Open Source by following the [official documentation](https://docs.airbyte.com/using-airbyte/getting-started/oss-quickstart).  
*Note:* You may need to add `sudo` before `abctl` commands.

### Setup Airbyte (not required if transform step only)

- Navigate to [http://localhost:8000/](http://localhost:8000/) in your web browser. Set your username. To retrieve your password, execute:
  ```bash
  (sudo) abctl local credentials
  ```

- In the Airbyte UI, go to Builder > Import a YAML. 
Upload the YAML file located at ./setup/elt_bench.yaml.
Click on the Publish button, type ignore warnings, and publish it to your workspace.

- In the Airbyte UI, go to **Sources > Custom > ELT Bench**. Retrieve the Workspace ID and Definition ID from the URL:
  ```
  http://localhost:8012/workspaces/<workspace_id>/source/new-source/<api_definition_id>
  ```
  Update the file `./setup/airbyte/airbyte_credentials.json` by filling in the following information: username, password, workspace ID, and API definition ID.


### Install psql (not required if transform step only)
- To insert data into PostgreSQL without installing the complete PostgreSQL database server, you can use the `psql` command-line tool. 
Please refer to the [installation instructions](https://www.timescale.com/blog/how-to-install-psql-on-mac-ubuntu-debian-windows) to install `psql` on your machine.
After successful installation, you can confirm the installation by running:

  ```bash
  psql --version
  ```

### Set up data destination - Snowflake
- Refer to the example in `./setup/destination/setup.sql`. Copy all the contents into a Snowflake worksheet and execute "Run all" to create the necessary credentials.
NOTE: No need to do this if the setup has already been done.

- Fill in the required values in `./setup/destination/snowflake_credential` to ensure Airbyte can successfully connect to Snowflake.
NOTE: use role "AIRBYTE_ROLE" and not "SYSADMIN"

### Run ELT setup
- Execute the script to create Docker containers for various sources, download both source data and ground truth results for evaluation, and insert the data.
  ```bash
  cd ./setup
  bash elt_setup.sh
  ```
- The conda env commands need to be executed directly in the terminal. Not all the commands need to be executed if you only focus on the transform stage. Read the script for more details.

### Upload tables to Snowflake
- Run the following script from the root of the project to load the data into Snowflake: 
  ```bash
  python3 dev/snowflake-connector/upload_tables.py --example_index 0-4
  ```
NOTE: the range includes both ends, so 0-4 means examples 0, 1, 2, 3, and 4. To upload all the tables, use 0-99.

## Running Agents

To evaluate AI agents on ELT-Bench, follow the instructions in the `agents/` folder. This folder contains detailed steps for running each agent (Spider-Agent and SWE-agent).

**Agent Workflow:**
1. Agents work within the `data/inputs/<problem_name>/` directory
2. Agents receive problem configuration and credentials from `config.yaml`
3. Agents generate ELT pipeline code (Terraform, SQL, etc.)
4. Agents can use `check_job_status.py` to monitor pipeline execution

## Evaluation

### Running Evaluation

Evaluate an agent's performance using the evaluation script:

```bash
cd evaluation
python eva.py --folder <folder_name> --example_index 0-4
```

**Parameters:**
- `--folder`: Name for this evaluation run (creates `results/<folder_name>/`)
- `--example_index`: Problem indices to evaluate
  - `0-4`: Problems 0 through 4 (inclusive)
  - `2,3`: Only problems 2 and 3
  - `all`: All 100 problems

**Example:**
```bash
python eva.py --folder my_agent_run_1 --example_index 0-99
```

### Evaluation Output Structure

Results are saved to `data/results/<folder_name>/`:
```
data/results/
└── <folder_name>/           # Your evaluation run (auto-timestamped)
    ├── eval_address/        # Per-problem results
    │   ├── stage1.log       # Stage 1 evaluation logs
    │   └── stage2.log       # Stage 2 evaluation logs
    ├── eval_airline/
    └── ...
```

### Understanding Evaluation

- **Stage 1**: Validates data extraction and loading (EL stage)
- **Stage 2**: Validates data transformation results (T stage)
- Results are compared against ground truth in `data/ground_truth/` and `evaluation/<problem>/`

**Important Notes:**
- Each evaluation run automatically gets a **unique timestamped folder** to avoid overwriting previous results
- Ground truth data in `data/ground_truth/` and `evaluation/<problem>/` must exist before running evaluation
- These are created by the setup script (`elt_setup.sh`)

## Common Issues and Solutions

### Missing `data/inputs/` directory
**Problem:** Agents can't find problem definitions  
**Solution:** Run `setup/elt_setup.sh` to generate `data/inputs/` from `elt-bench/`

### Missing ground truth for evaluation
**Problem:** Evaluation fails with "ground truth not found"  
**Solution:** Ensure `setup/elt_setup.sh` was run to extract `gt.zip` to `data/ground_truth/`

### Evaluation results overwritten
**Problem:** Previous evaluation results were lost  
**Solution:** As of the latest version, evaluation runs are automatically timestamped. You can also specify a custom folder:
```bash
python eva.py --folder my_custom_run --example_index 0-99
```

### Credentials not found
**Problem:** Agents can't connect to Snowflake/Airbyte  
**Solution:** 
1. Fill in `setup/destination/snowflake_credential.json`
2. Fill in `setup/airbyte/airbyte_credential.json`
3. Re-run `setup/write_config.py` to update `data/inputs/` folders

### Confusion between `elt-bench/` and `data/inputs/`
- **`elt-bench/`**: Original benchmark (read-only, never modify)
- **`data/inputs/`**: Working copies for agents (generated, can be regenerated)
- To reset: Delete `data/inputs/` and re-run `setup/write_config.py`

## Project Maintenance

### Re-generating `data/inputs/` directory
If you need to regenerate the `data/inputs/` directory with updated credentials:

```bash
cd setup
python3 write_config.py
```

This will:
1. Delete and recreate `data/inputs/` from `elt-bench/`
2. Inject current credentials from `setup/destination/` and `setup/airbyte/`
3. Copy documentation and helper scripts

### Clean Evaluation Results
To start fresh with evaluations while keeping ground truth:

```bash
rm -rf data/results/*  # Keeps results/ directory structure
```

### Reset All Generated Data
To completely reset and start fresh:

```bash
rm -rf data/  # Removes all generated content
cd setup
./elt_setup.sh  # Re-download and extract everything
```