#!/bin/bash
set -e  # Exit on error

# Script to launch mido_process_train_sai.py in the background using the comfy conda environment

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
# Logging setup
# Define directories for logs
LOG_DIR=$(realpath -m "$PROJECT_ROOT/logs")
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
JOB_LOG_DIR="$LOG_DIR/jobs/$TIMESTAMP"
MAIN_LOG_FILE="$LOG_DIR/mido_process_train_sai_${TIMESTAMP}.log"

# Main script to run
MAIN_SCRIPT="$PROJECT_ROOT/mido_process_train_sai.py"
PID_FILE="/tmp/mido_process_train.pid"

# Create log directories with proper permissions
mkdir -p "$LOG_DIR" "$JOB_LOG_DIR"
chmod 755 "$LOG_DIR" "$JOB_LOG_DIR"

# Verify directories were created successfully
if [[ ! -d "$LOG_DIR" ]] || [[ ! -d "$JOB_LOG_DIR" ]]; then
    echo "Failed to create log directories"
    exit 1
fi

# Export environment variables for Python script
export MAIN_LOG_FILE
export JOB_LOG_DIR
export MAIN_LOGGER_PREFIX="[MAIN]"
export JOB_LOGGER_PREFIX="[JOB]"

export MONITORED_PATH="$PROJECT_ROOT/origin/monitored"
export PROCESSING_PATH="$PROJECT_ROOT/origin/processing"
export PROCESSED_PATH="$PROJECT_ROOT/origin/processed"

# Set default value for DRY_RUN if not set
: "${DRY_RUN:=false}"

# Normalize DRY_RUN to true/false
case "${DRY_RUN,,}" in  # ${DRY_RUN,,} converts to lowercase
    true|t|yes|y|on|1)
        DRY_RUN=true
        ;;
    *)
        DRY_RUN=false
        ;;
esac

# Export normalized value
export DRY_RUN

# Function to log messages with timestamps (console only)
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $MAIN_LOGGER_PREFIX $1"
}

# Check if process is already running
if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
    log "Process already running with PID $(cat "$PID_FILE")"
    exit 1
fi

# Clean up PID file on script exit
trap 'rm -f "$PID_FILE"' EXIT

# Activate conda and the comfy environment
log "Activating conda environment..."
if [ "$DRY_RUN" = true ]; then
    log "DRY RUN: Would activate conda environment '3dgs'"
else
    source ~/miniconda3/etc/profile.d/conda.sh
    conda activate 3dgs
fi

cd $PROJECT_ROOT
log "change current directory to $(pwd)"

# Run the python script in the background
if [ "$DRY_RUN" = true ]; then
    log "DRY RUN: Would start mido_process_train_sai.py"
    log "DRY RUN: Environment variables that would be used:"
    log "  MONITORED_PATH=$MONITORED_PATH"
    log "  PROCESSING_PATH=$PROCESSING_PATH"
    log "  PROCESSED_PATH=$PROCESSED_PATH"
    log "  MAIN_LOG_FILE=$MAIN_LOG_FILE"
    log "  JOB_LOG_DIR=$JOB_LOG_DIR"  
fi

log "Starting mido_process_train_sai.py..."
nohup python "$MAIN_SCRIPT" &> /dev/null &
PID=$!
echo $PID > "$PID_FILE"
log "Process started with PID $PID"

log "Logs will be written to:"
log "Main log: $MAIN_LOG_FILE"
log "Job logs: $JOB_LOG_DIR/*.log"
