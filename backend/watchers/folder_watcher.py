"""
Watches the data/watch/ folder. When a CSV/Excel file is dropped in, it
auto-ingests it and moves it to data/watch/processed/.
"""
import os
import shutil
import time
import logging
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from ..database import SessionLocal
from ..importers.ingest import ingest_file

logger = logging.getLogger(__name__)


class AutoIngestHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        ext = os.path.splitext(event.src_path)[1].lower()
        if ext not in (".csv", ".xlsx", ".xls"):
            return

        # Wait for the file to be fully written
        filepath = event.src_path
        time.sleep(1)
        _wait_for_stable(filepath)

        logger.info(f"New file detected: {os.path.basename(filepath)}")
        _process_file(filepath)


def _wait_for_stable(filepath: str, timeout: float = 10):
    """Wait until the file size stops changing."""
    prev_size = -1
    elapsed = 0
    while elapsed < timeout:
        try:
            size = os.path.getsize(filepath)
        except OSError:
            return
        if size == prev_size and size > 0:
            return
        prev_size = size
        time.sleep(0.5)
        elapsed += 0.5


def _process_file(filepath: str):
    """Ingest a file and move it to processed/."""
    db = SessionLocal()
    try:
        log = ingest_file(filepath, db)

        # Move to processed folder
        watch_dir = os.path.dirname(filepath)
        processed_dir = os.path.join(watch_dir, "processed")
        os.makedirs(processed_dir, exist_ok=True)

        dest = os.path.join(processed_dir, os.path.basename(filepath))
        # Handle name collisions
        if os.path.exists(dest):
            base, ext = os.path.splitext(os.path.basename(filepath))
            dest = os.path.join(processed_dir, f"{base}_{int(time.time())}{ext}")

        shutil.move(filepath, dest)
        logger.info(f"Moved to {dest} | status={log.status} imported={log.rows_imported} skipped={log.rows_skipped}")

    except Exception as e:
        logger.exception(f"Failed to process {filepath}: {e}")
    finally:
        db.close()


def ingest_existing_files(watch_path: str):
    """Process any files already sitting in the watch folder on startup."""
    if not os.path.isdir(watch_path):
        return
    for filename in sorted(os.listdir(watch_path)):
        ext = os.path.splitext(filename)[1].lower()
        if ext in (".csv", ".xlsx", ".xls"):
            filepath = os.path.join(watch_path, filename)
            if os.path.isfile(filepath):
                logger.info(f"Startup ingest: {filename}")
                _process_file(filepath)


_observer = None


def start_watcher(watch_path: str):
    global _observer
    if _observer:
        return

    os.makedirs(watch_path, exist_ok=True)

    # First, process any files already there
    ingest_existing_files(watch_path)

    # Then watch for new ones
    handler = AutoIngestHandler()
    _observer = Observer()
    _observer.schedule(handler, watch_path, recursive=False)
    _observer.daemon = True
    _observer.start()
    logger.info(f"Watching {watch_path} for new files")


def stop_watcher():
    global _observer
    if _observer:
        _observer.stop()
        _observer.join()
        _observer = None
