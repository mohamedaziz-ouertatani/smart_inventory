import os
import subprocess
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime

def job_runner(job_cmd):
    print(f"[{datetime.utcnow().isoformat()}] Running: {job_cmd}", flush=True)
    result = subprocess.run(job_cmd, shell=True)
    print(f"[{datetime.utcnow().isoformat()}] Finished: {job_cmd} (Exit: {result.returncode})", flush=True)

def main():
    jobs_sequence = [
        "python -m jobs.ingest --skus 1000 --locations 3 --weeks 156",
        "python -m jobs.preprocess",
        "python -m jobs.train_ml --horizon 4",
        "python -m jobs.compute_policy"
    ]
    scheduler = BlockingScheduler(timezone='UTC')
    def pipeline():
        for jc in jobs_sequence:
            job_runner(f"docker compose -f docker-compose.yml -f docker-compose.jobs.override.yml run --rm jobs {jc}")
    scheduler.add_job(pipeline, 'cron', day_of_week='sun', hour=4, minute=0, id="weekly_pipeline", timezone='UTC')
    print("[Scheduler] Job scheduled. Press Ctrl+C to exit.")
    scheduler.start()

if __name__ == "__main__":
    main()