#!/bin/bash

# Slurm environment variables available in EpilogSlurmctld
JOB_ID=$SLURM_JOB_ID
USER=$SLURM_JOB_USER
JOB_NAME=$SLURM_JOB_NAME
EXIT_CODE=$SLURM_JOB_EXIT_CODE
EXIT_CODE2=$SLURM_JOB_EXIT_CODE2

# Determine basic status
STATUS="COMPLETED"
if [ "$EXIT_CODE" -ne 0 ]; then
    STATUS="FAILED"
fi

# Optional: detect cancel/kill via signal field in EXIT_CODE2
SIG_VAL=$(echo "$EXIT_CODE2" | cut -d: -f2)
if [ "$SIG_VAL" -eq 15 ]; then
    STATUS="CANCELLED"
elif [ "$SIG_VAL" -eq 9 ]; then
    STATUS="KILLED"
fi



# Write the curl command results to SlurmCTLD log file
LOGFILE="/var/log/slurm/slurmctld.log"


# Send JSON payload to your HTTP server
if curl -s -X POST http://localhost:8060/webhooks/job_event \
       -H "Content-Type: application/json" \
       -d "{\"job_id\": \"$JOB_ID\",
            \"username\": \"$USER\",
            \"job_name\": \"$JOB_NAME\",
            \"status\": \"$STATUS\",
            \"exit_code\": \"$EXIT_CODE\"}" \
       --max-time 2; then
    # Log success to slurmctld log
    ts=$(date '+[%Y-%m-%dT%H:%M:%S.%3N]')
    echo "$ts EpilogSlurmctld: Job $JOB_ID webhook SUCCESS (status=$STATUS, exit_code=$EXIT_CODE)" >> "$LOGFILE"
else
    # Log failure to slurmctld log
    ts=$(date '+[%Y-%m-%dT%H:%M:%S.%3N]')
    echo "$ts EpilogSlurmctld: Job $JOB_ID webhook FAILED (status=$STATUS, exit_code=$EXIT_CODE)" >> "$LOGFILE"
fi

# Always exit successfully to avoid blocking Slurm finalization
exit 0
