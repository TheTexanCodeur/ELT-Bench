import argparse
import datetime
import json
import logging
import os
import random
import sys
import glob

from tqdm import tqdm

from spider_agent.envs.spider_agent import Spider_Agent_Env
from spider_agent.agent.agents import PromptAgent
from create_snowflake_db import create_database
#  Logger Configs {{{ #
logger = logging.getLogger("spider_agent")
logger.setLevel(logging.DEBUG)

datetime_str: str = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")

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

stdout_handler.addFilter(logging.Filter("spider_agent"))
sdebug_handler.addFilter(logging.Filter("spider_agent"))

logger.addHandler(file_handler)
logger.addHandler(debug_handler)
logger.addHandler(stdout_handler)
logger.addHandler(sdebug_handler)
#  }}} Logger Configs # 



def config() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run end-to-end evaluation on the benchmark"
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
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--bq_only", action="store_true")
    parser.add_argument("--local_only", action="store_true")
    parser.add_argument("--dbt_only", action="store_true")
    parser.add_argument("--sf_only", action="store_true")
    parser.add_argument("--ch_only", action="store_true")
    parser.add_argument("--pg_only", action="store_true")
    
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
        
    if args.plan:
        experiment_id = f"{experiment_id}-plan"

    
    agent = PromptAgent(
        model=args.model,
        #max_tokens=args.max_tokens,
        top_p=args.top_p,
        temperature=args.temperature,
        max_memory_length=args.max_memory_length,
        max_steps=args.max_steps,
        use_plan=args.plan
    )
    # databases = [f.name for f in os.scandir('../../elt-bench') if f.is_dir()]
    # databases.sort()
    
    databases = [f.name for f in os.scandir('../../elt-bench') if f.is_dir()]
    databases.sort()
    databases = filter_databases(databases, args.example_index)
    logger.info(f"Processing {len(databases)} databases: {databases}")

    for db in databases:
        #DO NOT DROP THE DATABASE (ALREADY MANUALLY LOADED IN SNOWFLAKE)
        #create_database(db)
        task_config = {}
        task_config["instance_id"] = db
        #task_config["instruction"] = 'You are required to build an ELT pipeline by extracting data from multiple sources, such as custom APIs, Postgres, MongoDB, flat files and cloud service S3. The extracted data will be loaded into a target system, Snowflake, followed by writing transformation queries to construct final tables for downstream use.'
        task_config["instruction"] = 'Data has already been extracted from multiple sources (custom APIs, Postgres, MongoDB, flat files, and S3) and loaded into Snowflake via Airbyte. All source tables are now available in Snowflake. Your task is to focus ONLY on the transformation phase: write DBT transformation queries to construct the final tables for downstream use as defined in data_model.yaml. Do NOT modify Terraform configurations or trigger any Airbyte jobs.'
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



        env_config = {
            "init_args": {
                "name": experiment_id,
                "work_dir": "/workspace"
            }
        }
        task_config['config'] = [{"type": "copy_all_subfiles", "parameters": {"dirs": [os.path.join(args.test_path, db)]}}]


        env_config["init_args"]["name"] = experiment_id +"-"+ db

        env = Spider_Agent_Env(
            env_config=env_config,
            task_config=task_config,
            cache_dir="./cache",
            mnt_dir=output_dir
        )
        agent.set_env_and_task(env)
            
        logger.info('Task input:' + task_config['instruction'])
        done, result_output = agent.run()
        trajectory = agent.get_trajectory()

        os.makedirs(os.path.join(output_dir, "spider"), exist_ok=True)
        result_files = env.post_process()
        spider_result = {"finished": done, "steps": len(trajectory["trajectory"]),
                           "result": result_output,"result_files": result_files, **trajectory}
        with open(os.path.join(output_dir, "spider/result.json"), "w") as f:
            json.dump(spider_result, f, indent=2)
        

        logger.info("Finished %s", instance_id)
        


if __name__ == '__main__':
    args = config()
    test(args)