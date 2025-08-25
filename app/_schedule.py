from apscheduler.schedulers.blocking import BlockingScheduler
from app.collect import run_collect_once
from app.reddit_collect import run as run_reddit

def main():
    sched = BlockingScheduler(timezone="UTC")
    sched.add_job(run_collect_once, "interval", minutes=3, id="rss_html", max_instances=1, coalesce=True)
    sched.add_job(run_reddit, "interval", minutes=2, id="reddit", max_instances=1, coalesce=True)
    print("Scheduler started. Jobs:", sched.get_jobs())
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler stopped.")

if __name__ == "__main__":
    main()
