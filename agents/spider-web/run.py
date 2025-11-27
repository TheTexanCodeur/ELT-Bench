import argparse
import datetime
import json
import logging
import os
import sys

from tqdm import tqdm
from spiders.agents import PromptAgent
from spiders.utils import PostProcessor

#  Logger Configs {{{ #
logger = logging.getLogger("spider_web")
logger.setLevel(logging.DEBUG)

datetime_str: str = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")

# Ensure logs directory exists before creating FileHandlers to avoid FileNotFoundError
os.makedirs("logs", exist_ok=True)

file_handler = logging.FileHandler(os.path.join("logs", "normal-{:}.log".format(datetime_str)), encoding="utf-8")
debug_handler = logging.FileHandler(os.path.join("logs", "debug-{:}.log".format(datetime_str)), encoding="utf-8")
stdout_handler = logging.StreamHandler(sys.stdout)
sdebug_handler = logging.FileHandler(os.path.join("logs", "sdebug-{:}.log".format(datetime_str)), encoding="utf-8")

file_handler.setLevel(logging.INFO)
debug_handler.setLevel(logging.DEBUG)
stdout_handler.setLevel(logging.INFO)
sdebug_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    fmt="\x1b[1;33m[%(asctime)s \x1b[31m%(levelname)s \x1b[32m%(module)s/%(lineno)d-%(processName)s\x1b[1;33m] \x1b[0m%(message)s")
file_handler.setFormatter(formatter)
debug_handler.setFormatter(formatter)
stdout_handler.setFormatter(formatter)
sdebug_handler.setFormatter(formatter)

stdout_handler.addFilter(logging.Filter("spider_web"))
sdebug_handler.addFilter(logging.Filter("spider_web"))

logger.addHandler(file_handler)
logger.addHandler(debug_handler)
logger.addHandler(stdout_handler)
logger.addHandler(sdebug_handler)
#  }}} Logger Configs # 


def config() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run evaluations on the benchmark"
    )
    
    parser.add_argument("--max_steps", type=int, default=100)
    
    parser.add_argument("--max_memory_length", type=int, default=25)
    parser.add_argument("--suffix", '-s', type=str, default="gpt-4-try1")
    
    parser.add_argument("--model", type=str, default="gpt-4o")
    #parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--temperature", type=float, default=1)
    parser.add_argument("--top_p", type=float, default=0.9)
    # parser.add_argument("--max_tokens", type=int, default=2500)

    parser.add_argument("--stop_token", type=str, default=None)
    
    # example config
    parser.add_argument("--test_path","-t", type=str, default="../../data/inputs/")
    parser.add_argument("--example_index", "-i", type=str, default="all", help="index range of the examples to run, e.g., '0-10', '2,3', 'all'")
    parser.add_argument("--example_name", "-n", type=str, default="", help="name of the example to run")
    parser.add_argument("--overwriting", action="store_true", default=False)
    parser.add_argument("--retry_failed", action="store_true", default=False)

    # output related
    parser.add_argument("--output_dir", type=str, default="output")
    parser.add_argument("--bq_only", action="store_true")
    parser.add_argument("--local_only", action="store_true")
    parser.add_argument("--dbt_only", action="store_true")
    parser.add_argument("--sf_only", action="store_true")
    parser.add_argument("--ch_only", action="store_true")
    parser.add_argument("--pg_only", action="store_true")
    # retry behavior
    parser.add_argument("--max_retries", type=int, default=5, help="Maximum number of retry attempts for dbt run on failure")
    
    args = parser.parse_args()

    return args

def filter_databases(databases, example_index):
    """Filter databases based on example_index parameter"""
    if example_index == "all":
        return databases
    
    if "," in example_index:
        # Handle comma-separated indices like "2,3,5"
        indices = [int(i.strip()) for i in example_index.split(",")]
        return [databases[i] for i in indices if 0 <= i < len(databases)]
    
    if "-" in example_index:
        # Handle range like "0-10"
        start, end = map(int, example_index.split("-"))
        return databases[start:end+1]
    
    # Handle single index
    try:
        index = int(example_index)
        return [databases[index]] if 0 <= index < len(databases) else []
    except ValueError:
        logger.warning(f"Invalid example_index format: {example_index}")
        return databases
    
def run_spider(agent, post_processor, output_dir):
    post_processor.set_files_hash()
    done, result_output = agent.run()
    trajectory = agent.get_trajectory()
    
    os.makedirs(f"trajectories/{agent.name}", exist_ok=True)
    result_files = post_processor.post_process()
    spider_result = {"finished": done, "steps": len(trajectory["trajectory"]),
                        "result": result_output,"result_files": result_files, **trajectory}
    
    with open(f"trajectories/{agent.name}/result.json", "w") as f:
        json.dump(spider_result, f, indent=2)
    

def test(
    args: argparse.Namespace,
    test_all_meta: dict = None
) -> None:
    scores = []
    
    # log args
    logger.info("Args: %s", args)

    if args.suffix == "":
        logger.warning("No suffix is provided, the experiment id will be the model name.")
        experiment_id = args.model.split("/")[-1]
    else:
        experiment_id = args.model.split("/")[-1] + "-" + args.suffix

        
    databases = [f.name for f in os.scandir('../../elt-bench') if f.is_dir()]
    databases.sort()
    databases = filter_databases(databases, args.example_index)
    logger.info(f"Processing {len(databases)} databases: {databases}")

    for db in databases:
        
        ### INITIALIZATION STEPS ###
        
        instance_id = experiment_id +"/"+ db
        output_dir = os.path.join(args.output_dir, instance_id)
        result_json_path =os.path.join(output_dir, "elt/result.json")

        if not args.overwriting and os.path.exists(result_json_path):
            logger.info("Skipping %s", instance_id)
            continue
        elif os.path.exists(result_json_path):
            logger.info("Overwriting %s", instance_id)
        else:
            logger.info("Running %s", instance_id)
        if args.retry_failed and os.path.exists(result_json_path):
            with open(result_json_path, "r") as f:
                result = json.load(f)
                if result["finished"] and (not "FAIL" in result["result"]) and (not "error" in result["result"].lower()):
                    logger.info("Skipping %s", instance_id)
                    continue
            logger.info("Retrying %s", instance_id)
            
        if os.path.exists(output_dir):
            os.system(f"rm -rf {output_dir}")
            logger.info("Removed existing %s", output_dir)

        os.makedirs(output_dir, exist_ok=True)
        
        # Copy all the input files to output dir
        os.system(f"cp -r {os.path.join(args.test_path, db)}/* {output_dir}/")
        
        # Change working directory to output dir
        os.chdir(output_dir)
        
        #Initialize PostProcessor
        post_processor = PostProcessor(wrk_dir=output_dir)
        
        ### AGENT ORCHESTRATION STEPS ###

        ##############################################################
        #                  Query Plan Spider Agent                  #
        ##############################################################
        
        
        query_plan_spider_instruction = "Your task is to focus ONLY on creating the transformation query plan: analyze the data model requirements and source schemas to create a comprehensive query plan that will guide subsequent SQL development. Create a detailed .txt file outlining how source tables should be transformed into the final data models defined in data_model.yaml. Do NOT write actual SQL queries - focus on the high-level transformation logic, data flow, and dependencies."
        logger.info('Task input for query plan spider:' + query_plan_spider_instruction)
        
        query_plan_spider_agent = PromptAgent(
          name="query_plan_spider",
          instruction=query_plan_spider_instruction,
          model=args.model,
          top_p=args.top_p,
          temperature=args.temperature,
          max_memory_length=args.max_memory_length,
          max_steps=15,
        )
        
        # Generate Query Plan
        logger.info("Starting query plan spider for %s", instance_id)
        run_spider(query_plan_spider_agent, post_processor, output_dir)
        logger.info("Query plan spider finished for %s", instance_id)

        ##############################################################
        #                      SQL Spider Agent                      #
        ##############################################################
        
        sql_spider_instruction = "Your task is to generate the SQL queries based on the provided query plan. Carefully read the query_plan.txt file created by the previous agent, and translate each step of the plan into executable SQL statements that will transform the source data into the desired data models as specified in data_model.yaml. Ensure that the SQL queries are efficient, accurate, and adhere to best practices for database operations."
        logger.info('Task input for sql spider:' + sql_spider_instruction)
        
        sql_spider_agent = PromptAgent(
          name="sql_spider",
          instruction=sql_spider_instruction,
          model=args.model,
          top_p=args.top_p,
          temperature=args.temperature,
          max_memory_length=args.max_memory_length,
          max_steps=15,
        )
        
        # Generate SQL Queries
        logger.info("Starting SQL spider for %s", instance_id)
        run_spider(sql_spider_agent, post_processor, output_dir)
        logger.info("SQL spider finished for %s", instance_id)
        
        logger.info("Finished %s", instance_id)


        ##################################################
        #                   DBT agent                    #
        ##################################################

        # dbt is the agent that creates dbt_project.yml and profiles.yml
        dbt_spider_instruction = """Your task is to create the DBT configuration files (dbt_project.yml and profiles.yml)
          required to run the SQL models generated by the SQL Spider.

          You MUST:
          - Read config.yaml for Snowflake connection and SCHEMA settings.
          - Read all SQL models in ./sql/.
          - Use exactly the schema from config.yaml (uppercase).
          - Never invent a schema.
          - Never modify SQL.
          - Never create extra files.
          - Produce valid DBT YAML only.

          Follow the system prompt rules strictly.
        """

        logger.info('Task input for dbt agent:' + dbt_spider_instruction)
        dbt_spider = PromptAgent(
          name="dbt_spider",
          instruction=dbt_spider_instruction,
          model=args.model,
          top_p=args.top_p,
          temperature=args.temperature,
          max_memory_length=args.max_memory_length,
          max_steps=15,
        )

        # Generate DBT configuration files
        logger.info("Starting DBT agent for %s", instance_id)
        run_spider(dbt_spider, post_processor, output_dir)
        logger.info("DBT agent finished for %s", instance_id) 

        ##################################################
        #         ELT Execution + Correction Loop        #
        ##################################################
        max_attempts = max(1, int(args.max_retries))  
        attempt = 1
        while attempt <= max_attempts:
            logger.info("Starting ELT execution (attempt %d) for %s", attempt, instance_id)
            exit_code = os.system("dbt run")
            # On POSIX, os.system returns the exit status; 0 means success
            success = (exit_code == 0)
            if success:
                logger.info("ELT execution succeeded on attempt %d for %s", attempt, instance_id)
                break
            logger.info("ELT execution failed on attempt %d for %s (exit_code=%d)", attempt, instance_id, exit_code)

            if attempt == max_attempts:
                logger.info("Reached max attempts (%d), stopping", max_attempts)
                break

            logger.info("Retries remaining: %d. Starting correction loop for %s", max_attempts - attempt, instance_id)

            # correction plan spider function is to create a correction plan based on dbt run logs
            correction_plan_spider_instruction = """Your task is to create or update exactly one file: correction_plan.txt.
            You must analyze dbt run logs in ./logs/dbt.log, SQL models in ./sql/, and
            dbt configuration files, then identify the root cause of the failure.

            You must write a deterministic, step-by-step correction plan:
            - NO SQL execution
            - NO speculative fixes
            - EXACT file paths
            - EXACT line ranges or anchor text
            - EXACT replace/insert/delete operations
            - MINIMAL changes only
            - Never create new schemas, tables, directories, or filenames

            Follow the system prompt rules strictly.
            """

            logger.info('Task input for correction plan spider:' + correction_plan_spider_instruction)
            correction_plan_spider_agent = PromptAgent(
              name="correction_plan_spider",
              instruction=correction_plan_spider_instruction,
              model=args.model,
              top_p=args.top_p,
              temperature=args.temperature,
              max_memory_length=args.max_memory_length,
              max_steps=15,
            )

            # Generate Correction Plan
            logger.info("Starting correction plan spider for %s", instance_id)
            run_spider(correction_plan_spider_agent, post_processor, output_dir)
            logger.info("Correction plan spider finished for %s", instance_id)


            # correction spider function is to implement the corrections based on the correction plan
            correction_spider_instruction = """
            Your task is to APPLY the corrections described in correction_plan.txt. 
            Do not analyze the errors yourself and do not invent new fixes. 
            Read correction_plan.txt completely using ReadFile, then update only the files 
            explicitly referenced in the plan. Apply each fix exactly as written, using the 
            specified file paths, line anchors, and replace/insert/delete instructions.

            You MUST:
            - Modify only the files listed in the correction plan.
            - Perform only the actions described in the plan.
            - Use EditFile for all modifications.
            - Make minimal, surgical edits exactly matching the plan’s content.
            - Never rewrite entire files unless the plan explicitly requires it.
            - Never change any SQL or YAML that is not part of the plan.
            - Never create new files, rename files, or invent schemas or fields.

            Follow the system prompt strictly.
            """

            correction_spider_agent = PromptAgent(
              name="correction_spider",
              instruction=correction_spider_instruction,
              model=args.model,  
              top_p=args.top_p,
              temperature=args.temperature,
              max_memory_length=args.max_memory_length,
              max_steps=15,
            )

            # Generate Corrected SQL Queries
            logger.info("Starting correction SQL spider for %s", instance_id)
            run_spider(correction_spider_agent, post_processor, output_dir)
            logger.info("Correction SQL spider finished for %s", instance_id)

            attempt += 1
        logger.info("Finished %s", instance_id)



if __name__ == '__main__':
    args = config()
    test(args)