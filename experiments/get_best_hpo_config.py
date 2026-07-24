"""
get_best_hpo_config.py — pull the best hyperparameter configuration(s) from a finished (or
running) W&B HPO sweep and save them ready to use.

The E2 sweep (tuning_hyperparameter.py) logs every trial to W&B under projects
  RelationalPKT-<TASK>-<model>     e.g. RelationalPKT-DTI-compgcn, RelationalPKT-DTI-rgcn
but does NOT persist the winning config. This does: it ranks the trials by the composite
metric and writes the best config per model into:
  experiments/hpo_best/<TASK>_<model>_best.json
and prints a block ready to paste into src/models_params.json (optionally injects it with
--write, under config name PKT-<TASK>-best).

Requires:  pip install wandb && wandb login
Usage:
  python experiments/get_best_hpo_config.py --task DTI
  python experiments/get_best_hpo_config.py --task TREATS --metric final_mixed_metric --write
"""
import argparse
import json
import os
from pathlib import Path

# hyperparameter keys that belong in src/models_params.json (per model)
PARAM_KEYS = ["conv_layer_num", "dropout", "layer_0", "layer_1", "layer_2", "mlp_out_layer",
              "learning_rate", "opn", "grad_norm", "num_bases", "regularization",
              "weight_decay", "scheduler_gamma", "model_name"]

DEFAULT_ENTITY = os.environ.get("WANDB_ENTITY", "giovannimaria-defilippis-university-of-naples-federico-ii")
OUT_DIR = Path(__file__).resolve().parent / "hpo_best"
PARAMS_JSON = Path(__file__).resolve().parents[1] / "src" / "models_params.json"


def best_run(api, entity, project, metric):
    """Return (best_value, config, run_name) for the highest `metric` in a project."""
    best = None
    try:
        runs = api.runs(f"{entity}/{project}")
    except Exception as e:
        print(f"  [!] cannot read project {project}: {e}")
        return None
    for r in runs:
        v = r.summary.get(metric)
        if v is None:
            continue
        if best is None or v > best[0]:
            best = (float(v), dict(r.config), r.name)
    return best


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", required=True, help="DTI or TREATS (matches the W&B project prefix)")
    ap.add_argument("--models", nargs="+", default=["compgcn", "rgcn"])
    ap.add_argument("--entity", default=DEFAULT_ENTITY)
    ap.add_argument("--metric", default="val_mixed_metric",
                    help="metric to rank by (default val_mixed_metric; or final_mixed_metric)")
    ap.add_argument("--write", action="store_true",
                    help="also inject the best configs into src/models_params.json as PKT-<TASK>-best")
    args = ap.parse_args()

    import wandb
    api = wandb.Api()
    OUT_DIR.mkdir(exist_ok=True)

    task_config = {}   # {model: best_param_dict}
    for model in args.models:
        project = f"RelationalPKT-{args.task}-{model}"
        print(f"\n[{project}] ranking by '{args.metric}' ...")
        b = best_run(api, args.entity, project, args.metric)
        if b is None:
            print(f"  no runs with metric '{args.metric}' — skipping")
            continue
        value, config, name = b
        params = {k: config[k] for k in PARAM_KEYS if k in config}
        params["model_name"] = model
        task_config[model] = params
        print(f"  best run: {name}  |  {args.metric} = {value:.4f}")
        print(json.dumps(params, indent=2))
        out = OUT_DIR / f"{args.task}_{model}_best.json"
        out.write_text(json.dumps({"metric": args.metric, "value": value,
                                   "run": name, "params": params}, indent=2))
        print(f"  saved -> {out}")

    if args.write and task_config:
        with open(PARAMS_JSON) as f:
            allp = json.load(f)
        key = f"PKT-{args.task}-best"
        allp[key] = task_config
        with open(PARAMS_JSON, "w") as f:
            json.dump(allp, f, indent=4)
        print(f"\n[i] injected into {PARAMS_JSON} as '{key}'.")
        print(f"    Use it in E1:  HP_CONFIG={key} bash experiments/e1_main_training.sh")
    elif task_config:
        print(f"\n[i] To use in E1, add the block above to src/models_params.json under a "
              f"config name (e.g. 'PKT-{args.task}-best'), or re-run with --write.")


if __name__ == "__main__":
    main()
