#!/usr/bin/env bash
# run_dgx_ablation.sh — Run the remaining base conditions (general_only, tom_only,
# full_kg) for the immigration topic on Rossetti's DGX box against a vLLM endpoint.
#
# The no_kg baseline (140 agents, 10 days, seed 42) already completed locally on
# Ollama — this script only runs the three remaining conditions.
#
# Designed to be launched unattended, e.g.:
#   nohup bash scripts/run_dgx_ablation.sh > /dev/null 2>&1 &
#   tmux new -d -s dgx_ablation 'bash scripts/run_dgx_ablation.sh'
#
# It is safe to re-launch after a crash/disconnect: each condition resumes from
# its checkpoint.json (built into src/simulation.py) rather than starting over,
# and a lock file prevents two copies from running concurrently.
#
# Sequential by design (see the for-loop below) since the DGX may be shared with
# other jobs. To run conditions concurrently instead, replace the `for COND in
# ...; do ... done` loop with one `... & ` per condition followed by `wait` —
# not done here on purpose, to keep resource usage predictable on a shared box.

set -uo pipefail
# NOTE: intentionally not `-e` — failures are caught explicitly below so the
# retry loop can act on them instead of the script dying.

# ── vLLM / concurrency configuration (override before running) ───────────────
LLM_BASE_URL="${LLM_BASE_URL:-http://REPLACE_ME:8000/v1}"
LLM_MODEL="${LLM_MODEL:-REPLACE_ME_MODEL}"
LLM_MAX_CONCURRENCY="${LLM_MAX_CONCURRENCY:-16}"
PARALLEL_EXCHANGE_JOBS="${PARALLEL_EXCHANGE_JOBS:-4}"

# ── Fixed run parameters ───────────────────────────────────────────────────────
TOPIC="immigration"
N_AGENTS=140
N_ITERATIONS=10      # 10 days
MIN_TURNS="${MIN_TURNS:-2}"
MAX_TURNS="${MAX_TURNS:-5}"
RANDOM_SEED=42
LLM_PROVIDER="vllm"
CLOCK_ADVANCE_HOURS="${CLOCK_ADVANCE_HOURS:-24}"
CONDITIONS=("general_only" "tom_only" "full_kg")

MAX_RETRIES="${MAX_RETRIES:-5}"
BACKOFF_SECONDS="${BACKOFF_SECONDS:-30}"

PYTHON=".venv/bin/python"

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR" || { echo "Cannot cd to project root $SCRIPT_DIR" >&2; exit 1; }

LOG_DIR="logs"
mkdir -p "$LOG_DIR"
ORCHESTRATION_LOG="${LOG_DIR}/dgx_ablation_orchestration.log"
LOCK_FILE="${LOG_DIR}/dgx_ablation.lock"
PID_FILE="${LOG_DIR}/dgx_ablation.pid"

# ── Fail fast if the placeholder endpoint/model is still present ──────────────
if [[ "$LLM_BASE_URL" == *"REPLACE_ME"* ]]; then
    echo "ERROR: LLM_BASE_URL is still set to the placeholder ('$LLM_BASE_URL')." >&2
    echo "       Set LLM_BASE_URL to the real DGX vLLM endpoint before running this script." >&2
    exit 1
fi

if [[ "$LLM_MODEL" == *"REPLACE_ME"* ]]; then
    echo "ERROR: LLM_MODEL is still set to the placeholder ('$LLM_MODEL')." >&2
    echo "       Set LLM_MODEL to the model name served by vLLM before running this script." >&2
    exit 1
fi

# ── Single-instance lock ───────────────────────────────────────────────────────
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    echo "ERROR: another run_dgx_ablation.sh appears to be running (lock held on $LOCK_FILE)." >&2
    if [ -f "$PID_FILE" ]; then
        echo "       PID file says: $(cat "$PID_FILE")" >&2
    fi
    exit 1
fi
echo $$ > "$PID_FILE"
trap 'rm -f "$PID_FILE"' EXIT

log_orchestration() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$ORCHESTRATION_LOG"
}

log_orchestration "=========================================================="
log_orchestration "Starting DGX ablation run (PID $$)"
log_orchestration "Topic=$TOPIC  N_AGENTS=$N_AGENTS  N_ITERATIONS=$N_ITERATIONS  SEED=$RANDOM_SEED"
log_orchestration "LLM_PROVIDER=$LLM_PROVIDER  LLM_MODEL=$LLM_MODEL  LLM_BASE_URL=$LLM_BASE_URL"
log_orchestration "LLM_MAX_CONCURRENCY=$LLM_MAX_CONCURRENCY  PARALLEL_EXCHANGE_JOBS=$PARALLEL_EXCHANGE_JOBS"
log_orchestration "Conditions: ${CONDITIONS[*]}"
log_orchestration "=========================================================="

# ── Result tracking for the final summary table ───────────────────────────────
declare -A STATUS
declare -A RETRIES

# ── Run conditions sequentially (DGX may be shared with other jobs) ───────────
# To parallelize instead: launch each `run_one_condition "$COND" &` in the loop
# below and `wait` after it — not done by default here.
for COND in "${CONDITIONS[@]}"; do
    OUT_DIR="data/${TOPIC}/${COND}"
    DB_PATH="${OUT_DIR}/simulation.db"
    COND_LOG="${LOG_DIR}/dgx_run_${COND}.log"
    mkdir -p "$OUT_DIR"

    log_orchestration "Starting condition '$COND' -> $OUT_DIR (log: $COND_LOG)"

    attempt=0
    success=0
    while [ "$attempt" -lt "$MAX_RETRIES" ]; do
        attempt=$((attempt + 1))
        if [ "$attempt" -gt 1 ]; then
            log_orchestration "Retrying condition '$COND' (attempt $attempt/$MAX_RETRIES) — resuming from checkpoint if present"
        fi

        {
            echo "===== $(date '+%Y-%m-%d %H:%M:%S') — attempt $attempt/$MAX_RETRIES for $COND ====="
        } >> "$COND_LOG"

        PYTHONDONTWRITEBYTECODE=1 \
        TOPIC="$TOPIC" \
        MEMORY_CONDITION="$COND" \
        OUTPUT_DIR="$OUT_DIR" \
        DB_PATH="$DB_PATH" \
        N_AGENTS="$N_AGENTS" \
        N_ITERATIONS="$N_ITERATIONS" \
        MIN_TURNS="$MIN_TURNS" \
        MAX_TURNS="$MAX_TURNS" \
        RANDOM_SEED="$RANDOM_SEED" \
        LLM_PROVIDER="$LLM_PROVIDER" \
        LLM_MODEL="$LLM_MODEL" \
        LLM_BASE_URL="$LLM_BASE_URL" \
        LLM_MAX_CONCURRENCY="$LLM_MAX_CONCURRENCY" \
        PARALLEL_EXCHANGE_JOBS="$PARALLEL_EXCHANGE_JOBS" \
        CLOCK_ADVANCE_HOURS="$CLOCK_ADVANCE_HOURS" \
        $PYTHON src/simulation.py >> "$COND_LOG" 2>&1

        rc=$?

        if [ "$rc" -eq 0 ]; then
            success=1
            break
        fi

        log_orchestration "Condition '$COND' failed on attempt $attempt/$MAX_RETRIES (exit code $rc). See $COND_LOG"

        if [ "$attempt" -lt "$MAX_RETRIES" ]; then
            sleep "$BACKOFF_SECONDS"
        fi
    done

    RETRIES["$COND"]=$attempt

    if [ "$success" -eq 1 ]; then
        STATUS["$COND"]="SUCCESS"
        log_orchestration "Condition '$COND' finished successfully after $attempt attempt(s)"
    else
        STATUS["$COND"]="FAILED"
        log_orchestration "Condition '$COND' exhausted all $MAX_RETRIES attempts — giving up and moving to the next condition"
    fi
done

log_orchestration "All conditions processed. Run complete."

# ── Summary table ──────────────────────────────────────────────────────────────
echo ""
echo "=========================================================="
echo " DGX Ablation Run Summary"
echo "=========================================================="
printf "%-16s %-10s %s\n" "CONDITION" "STATUS" "ATTEMPTS"
printf "%-16s %-10s %s\n" "----------------" "----------" "--------"
for COND in "${CONDITIONS[@]}"; do
    printf "%-16s %-10s %s\n" "$COND" "${STATUS[$COND]:-UNKNOWN}" "${RETRIES[$COND]:-0}"
done
echo "=========================================================="
echo "Per-condition logs: ${LOG_DIR}/dgx_run_<condition>.log"
echo "Orchestration log : $ORCHESTRATION_LOG"
