# DGX Ablation Runbook

## What it does

`scripts/run_dgx_ablation.sh` runs three memory-condition ablations for the immigration topic in sequence: `general_only`, `tom_only`, `full_kg`. Each is a full 140-agent, 10-day simulation writing to its own `data/immigration/{condition}/` directory. It calls `src/simulation.py` once per condition with `MEMORY_CONDITION` set accordingly, the same pattern `run_ablation.sh` uses for all four conditions. The `no_kg` baseline is already done and is not part of this run.

## Prerequisites

1. A vLLM server reachable from the DGX node, serving an OpenAI-compatible endpoint:
   ```
   python -m vllm.entrypoints.openai.api_server \
     --model meta-llama/Llama-3.1-8B-Instruct \
     --port 8000
   ```
2. Confirm it responds before launching the ablation:
   ```
   curl -s http://127.0.0.1:8000/v1/models
   ```
3. Set these before running the script (either export them or prefix the command):
   ```
   LLM_BASE_URL=http://127.0.0.1:8000/v1
   LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct
   LLM_MAX_CONCURRENCY=16
   PARALLEL_EXCHANGE_JOBS=4
   ```
   `LLM_BASE_URL` must point at the vLLM server's `/v1` path, not the bare host. If vLLM runs on a different port or a remote address, adjust the host and port accordingly. The script refuses to run if `LLM_BASE_URL` or `LLM_MODEL` are left at their placeholder values, so a typo here fails immediately instead of quietly hitting a fake host.

## Launching it

Run it under `nohup` so it survives a disconnect:

```bash
cd /path/to/Agentic-Stance
LLM_BASE_URL=http://127.0.0.1:8000/v1 \
LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct \
nohup bash scripts/run_dgx_ablation.sh > /dev/null 2>&1 &
disown
```

Or inside tmux:

```bash
tmux new -d -s dgx_ablation 'LLM_BASE_URL=http://127.0.0.1:8000/v1 LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct bash scripts/run_dgx_ablation.sh'
```

Check it's alive:

```bash
ps aux | grep simulation.py
tail -f logs/dgx_ablation_orchestration.log
```

The orchestration log records when each condition starts, retries, finishes, or fails permanently. Each condition also writes its own log at `logs/dgx_run_{condition}.log`, plus the usual simulation output under `data/immigration/{condition}/`: `results.csv`, `exchanges.jsonl`, `checkpoint.json`, and `simulation_iter_N.db.bak` snapshots.

A lock file at `logs/dgx_ablation.lock` stops a second copy from launching while one is already running. If you try to start it twice, the second call exits immediately and tells you the PID of the one already running.

## Checking progress mid-run

```bash
wc -l data/immigration/general_only/results.csv
tail -20 data/immigration/general_only/results.csv
cat data/immigration/general_only/checkpoint.json
```

Normal: `checkpoint.json`'s `last_completed_iteration` increases roughly once per day of simulated time, and `results.csv` row count grows by up to 140 rows per completed day.

Stuck: `checkpoint.json` unchanged and no new lines in `results.csv` for well past one day's expected duration, with the process still present in `ps`. That usually means a hung LLM call. Check the vLLM server logs and `curl` the endpoint again to confirm it's still serving.

## Crash and restart behavior

The script retries a failed condition automatically, up to 5 attempts with a 30 second pause between them, by re-running the identical command. Re-running the exact same command is also what you'd do by hand if the whole script died: on startup, `simulation.py` reads `checkpoint.json`. If it exists, it restores `simulation_iter_{last_completed}.db.bak` over the live SQLite file, which rolls the GhostKG state back to the end of the last fully completed day, then rebuilds `current_stances` in memory by replaying every row of `results.csv` in order. It resumes the day loop at `last_completed_iteration + 1`.

One real gotcha: the checkpoint is written once per day, after every agent has exchanged, not after each row. If the process is killed mid-day, `results.csv` can already contain some rows for that day even though `checkpoint.json` still says the previous day. On resume, that day reruns from scratch and appends a second set of rows for the same day number. If exact row counts matter for analysis, check for duplicate `iteration` values in `results.csv` and drop the earlier partial set for any day with more than 140 rows.

If a condition's directory has no `checkpoint.json`, that condition starts fresh regardless of what else is on disk.

If a condition exhausts all 5 retry attempts, the script logs it as FAILED and moves on to the next condition rather than stopping the whole run. Check the summary table printed at the end, or the orchestration log, to see which conditions need a manual re-run.

## Stopping it safely

```bash
pkill -f "src/simulation.py"
```

Because checkpoints only land at day boundaries, killing it mid-day loses that day's in-progress work on restart, but never corrupts `results.csv` or the SQLite file. There's nothing to clean up by hand. Re-running the script picks up from the last completed day for whichever condition was in progress, and continues to the next condition after that.

## What done looks like

Each of the three conditions should end with:

- `results.csv`: 1400 rows (140 agents x 10 days), plus header
- `checkpoint.json`: `"last_completed_iteration": 10`
- `exchanges.jsonl`: 1400 lines
- No `simulation_iter_*.db.bak` newer than the final day (harmless to leave in place)

The script prints a summary table at the end showing SUCCESS or FAILED and the attempt count for each condition. If any condition shows FAILED, its `checkpoint.json` will show which day it stopped on, and re-running the script picks that condition back up from there.
