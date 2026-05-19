def build_startup_summary(project_root: str, interval_seconds: int) -> str:
    return f"PM Scheduler watching {project_root} every {interval_seconds}s"


def main() -> None:
    import os
    import time

    project_root = os.getenv("CCCAGENTS_PROJECT_ROOT", "/home/ubuntu/cccagents/projects")
    interval_seconds = int(os.getenv("CCCAGENTS_SCHEDULER_INTERVAL_SECONDS", "60"))
    print(build_startup_summary(project_root, interval_seconds), flush=True)
    while True:
        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
