"""Entry: python ppt_worker.py  — DB-queue PPT generation worker."""

from app.services.ppt.agent.backend.worker.loop import main

if __name__ == "__main__":
    main()
