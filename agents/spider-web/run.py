import argparse
import datetime
import json
import logging
import os
import sys
import yaml

from tqdm import tqdm
from spiders.agents import PromptAgent
from spiders.utils import PostProcessor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTRUCTIONS_PATH = os.path.join(BASE_DIR, "spiders", "instructions.yml")

with open(INSTRUCTIONS_PATH) as f:
    INSTRUCTIONS = yaml.safe_load(f)


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
    
def make_agent(name: str, model: str, args, **extra_kwargs):
    
        
    return PromptAgent(
        name=name,
        instruction=INSTRUCTIONS[name]["instruction"],
        model=model,
        top_p=args.top_p,
        temperature=args.temperature,
        max_memory_length=args.max_memory_length,
        max_steps=INSTRUCTIONS[name].get("max_steps", 15),
        **extra_kwargs,
    )

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
    

def dbt_correction_loop(args, post_processor, output_dir, max_retries, instance_id):
    """
    Execute dbt with automatic correction loop on failure.
    
    Args:
        args: Command line arguments containing model configuration
        post_processor: PostProcessor instance for handling file operations
        output_dir: Directory where dbt project is located
        max_retries: Maximum number of retry attempts
        instance_id: Unique identifier for this instance (for logging)
    
    Returns:
        bool: True if dbt execution succeeded, False otherwise
    """
    max_attempts = max(1, int(max_retries))  
    attempt = 1
    success = False

    while attempt <= max_attempts:
        logger.info("Starting ELT execution (attempt %d) for %s", attempt, instance_id)
        exit_code = os.system("dbt run")
        success = (exit_code == 0)

        if success:
            logger.info("ELT execution succeeded on attempt %d for %s", attempt, instance_id)
            break

        logger.info("ELT execution failed on attempt %d for %s (exit_code=%d)", 
                    attempt, instance_id, exit_code)

        if attempt == max_attempts:
            logger.info("Reached max attempts (%d), stopping execution phase.", max_attempts)
            break

        logger.info("Retries remaining: %d. Starting execution correction loop for %s",
                    max_attempts - attempt, instance_id)

        ### EXECUTION CORRECTION PLAN SPIDER
        # Generate Correction Plan
        logger.info("Starting correction plan spider for %s", instance_id)
        correction_plan_spider_agent = make_agent("correction_plan_spider", args.model, args)
        run_spider(correction_plan_spider_agent, post_processor, output_dir)
        logger.info("Correction plan spider finished for %s", instance_id)

        # correction spider function is to implement the corrections based on the correction plan
        # Apply corrections based on the correction plan
        logger.info("Starting correction spider for %s", instance_id)
        correction_spider_agent = make_agent("correction_spider", args.model, args)
        run_spider(correction_spider_agent, post_processor, output_dir)
        logger.info("Correction spider finished for %s", instance_id)

        attempt += 1

    logger.info("Execution correction phase completed for %s", instance_id)
    return success


def semantic_verification_loop(args, post_processor, output_dir, max_retries, instance_id):
    """
    Run semantic verification and correction loop on successful dbt execution.
    
    Args:
        args: Command line arguments containing model configuration
        post_processor: PostProcessor instance for handling file operations
        output_dir: Directory where dbt project is located
        max_retries: Maximum number of verification/correction iterations
        instance_id: Unique identifier for this instance (for logging)
    
    Returns:
        bool: True if verification passed, False otherwise
    """
    logger.info("Starting semantic verification phase for %s", instance_id)

    for sem_iter in range(1, max_retries + 1):

        ### VERIFICATION SPIDER
        verification_spider_agent = make_agent("verification_spider", args.model, args)
        run_spider(verification_spider_agent, post_processor, output_dir)

        # read verification report
        report_path = "verification_report.txt"
        if not os.path.exists(report_path):
            logger.warning("verification_report.txt missing; assuming PASS.")
            return True

        with open(report_path) as f:
            report = f.read()

        if "overall_status: PASS" in report:
            logger.info("Semantic verification PASSED for %s", instance_id)
            return True

        logger.info("Semantic verification FAILED (iteration %d).", sem_iter)

        ### SEMANTIC CORRECTION PLAN SPIDER
        sem_plan_agent = make_agent("sem_correction_plan_spider", args.model, args)
        run_spider(sem_plan_agent, post_processor, output_dir)

        ### CORRECTION SPIDER (semantic)
        correction_spider_agent = make_agent("correction_spider", args.model, args)
        run_spider(correction_spider_agent, post_processor, output_dir)

        ### Re-run dbt
        logger.info("Re-running dbt after semantic corrections.")
        exit_code = os.system("dbt run")
        if exit_code != 0:
            logger.info("dbt failed after semantic corrections; stopping semantic loop.")
            return False

    logger.info("Semantic verification phase completed for %s", instance_id)
    return False

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
        
        # Generate Query Plan
        logger.info("Starting query plan spider for %s", instance_id)
        query_plan_spider_agent = make_agent("query_plan_spider", args.model, args)
        run_spider(query_plan_spider_agent, post_processor, output_dir)
        logger.info("Query plan spider finished for %s", instance_id)

        ##############################################################
        #                      SQL Spider Agent                      #
        ##############################################################
        
        # Generate SQL Queries
        logger.info("Starting SQL spider for %s", instance_id)
        sql_spider_agent = make_agent("sql_spider", args.model, args)
        run_spider(sql_spider_agent, post_processor, output_dir)
        logger.info("SQL spider finished for %s", instance_id)
        
        logger.info("Finished %s", instance_id)


        ##################################################
        #                   DBT agent                    #
        ##################################################

        # Generate DBT configuration files
        logger.info("Starting DBT agent for %s", instance_id)
        dbt_spider = make_agent("dbt_spider", args.model, args)
        run_spider(dbt_spider, post_processor, output_dir)
        logger.info("DBT agent finished for %s", instance_id) 

        ##################################################
        #         ELT Execution Correction Loop          #
        ##################################################
        success = dbt_correction_loop(args, post_processor, output_dir, args.max_retries, instance_id)


        ##################################################
        #          SEMANTIC VERIFICATION LOOP            #
        ##################################################
        if success:
            semantic_verification_loop(args, post_processor, output_dir, args.max_retries, instance_id)

        logger.info("Finished %s", instance_id)



if __name__ == '__main__':
    args = config()
    test(args)