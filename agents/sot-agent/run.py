import argparse
import datetime
import json
import logging
import os
from typing import List, Optional

from sot_agent.agent import sot_pipeline

# ---------- logging ----------
logger = logging.getLogger("sot_agent")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("[%(asctime)s %(levelname)s] %(message)s"))
logger.addHandler(_handler)


def list_folders(root: str) -> List[str]:
    if not os.path.isdir(root):
        return []
    names = [f.name for f in os.scandir(root) if f.is_dir()]
    names.sort()
    return names


def filter_databases(databases: List[str], example_index: str) -> List[str]:
    if example_index == "all":
        return databases
    if "," in example_index:
        indices = []
        for tok in example_index.split(","):
            tok = tok.strip()
            if tok.isdigit():
                indices.append(int(tok))
        return [databases[i] for i in indices if 0 <= i < len(databases)]
    if "-" in example_index:
        start, end = example_index.split("-")
        start, end = int(start), int(end)
        return databases[start : end + 1]
    try:
        idx = int(example_index)
        return [databases[idx]] if 0 <= idx < len(databases) else []
    except ValueError:
        return databases


def config() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SoT agent on ELT-Bench (transform-only).")
    parser.add_argument("--suffix", "-s", type=str, default="gpt-4o-try1")
    parser.add_argument("--model", type=str, default="gpt-4o")
    parser.add_argument("--temperature", type=float, default=0.0)

    # paths & selection
    parser.add_argument("--test_path", "-t", type=str, default="../../elt-bench")
    parser.add_argument("--example_index", "-i", type=str, default="all")  # "0-10", "2,3", "all"
    parser.add_argument("--output_dir", type=str, default="output")

    # optional overrides
    parser.add_argument("--question", type=str, default=None)
    parser.add_argument("--schema", type=str, default=None, help="Optional schema override (e.g., AIRBYTE_SCHEMA)")

    return parser.parse_args()


def _get_schema_hint_from_config(cfg_path: str) -> Optional[str]:
    try:
        import yaml  # local import to keep deps optional
        if os.path.exists(cfg_path):
            with open(cfg_path, "r") as f:
                cfg = yaml.safe_load(f) or {}
            return (
                cfg.get("destination", {}).get("snowflake", {}).get("schema")
                or cfg.get("snowflake", {}).get("schema")
                or cfg.get("schema")
            )
    except Exception:
        pass
    return None


def main():
    args = config()
    logger.info("Args: %s", vars(args))

    # experiment id similar to spider-agent (model-suffix)
    mname = args.model.split("/")[-1]
    experiment_id = f"{mname}-{args.suffix}" if args.suffix else mname

    # enumerate databases from ../../elt-bench
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    elt_bench_root = os.path.abspath(os.path.join(repo_root, "elt-bench"))
    all_dbs = list_folders(elt_bench_root)
    dbs = filter_databases(all_dbs, args.example_index)
    logger.info("Databases selected (%d): %s", len(dbs), dbs)

    # inputs root for creds/configs
    inputs_root = os.path.join(repo_root, "data", "inputs")

    for db in dbs:
        creds_path = os.path.join(inputs_root, db, "snowflake_credential.json")
        cfg_path = os.path.join(inputs_root, db, "config.yaml")

        # schema hint precedence: CLI --schema > config.yaml > None (auto-discover)
        schema_hint = args.schema or _get_schema_hint_from_config(cfg_path)

        # question heuristic
        question = (
            args.question
            or "Data is already loaded in Snowflake. Focus ONLY on the transform stage and "
               "generate the final tables defined in data_model.yaml using the loaded source tables."
        )

        ok, result, debug = sot_pipeline(
            question=question,
            creds_path=creds_path,
            db_name=db,             # behave like spider-agent: database = folder name
            schema_name=schema_hint,  # may be None; agent will auto-discover if needed
            model=args.model,
            temperature=args.temperature,
            retry=2,
        )

        # write artifacts for this db
        out_dir = os.path.join(args.output_dir, f"{experiment_id}/{db}/sot")
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "result.json"), "w") as f:
            json.dump(
                {
                    "finished": ok,
                    "result": "OK" if ok else "FAIL",
                    "details": result,
                    "model": args.model,
                    "suffix": args.suffix,
                    "timestamp": datetime.datetime.now().isoformat(),
                },
                f,
                indent=2,
            )
        # also dump debugging info (schema list, plan, sql, last error)
        with open(os.path.join(out_dir, "sot_agent.log"), "w") as f:
            f.write(debug)

        logger.info("[%s] %s", db, "OK" if ok else "FAIL")


if __name__ == "__main__":
    main()
