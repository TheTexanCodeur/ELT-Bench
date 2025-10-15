# ELT-Bench
The first comprehensive, end-to-end benchmark designed to evaluate AI agents in automating ELT pipelines.
![ELT](https://anonymous.4open.science/r/ELT-Bench-B51C/materials/elt.svg)
## Environment Setup

### Install Docker (not required if transform step only) and Conda 
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

### Load tables to Snowflake
- Run the following script from the root of the project to load the data into Snowflake: 
  ```bash
  python3 dev/snowflake-connector/upload_tables.py --example_index 0-4
  ```
NOTE: the range includes both ends, so 0-4 means examples 0, 1, 2, 3, and 4.

## Running agents
- To evaluate the Spider-Agent and SWE-agent on ELT-Bench, follow the instructions in the `agents` folder. This folder contains detailed steps for running each agent.

## Evaluation

- To evaluate the performance of an agent, use the following commands:

  ```bash
  cd evaluation
  python eva.py --folder folder_name --example_index 0-4
  ```
  
  Replace folder_name with your desired name for the evaluation results. The newly created folder with the results will be located at `./evaluation/agent_results`.