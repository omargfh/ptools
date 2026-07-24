from pydantic import BaseModel

def on_close() -> None:
  from ptools.lib.app.log_file import HistoryEntry, get_log_file
  from ptools.settings import MAX_HISTORY_ENTRIES
  import datetime
  import sys

  log = get_log_file()

  history_entry = HistoryEntry(
      executable=sys.executable,
      command=sys.argv[1:],
      timestamp=datetime.datetime.now().isoformat()
  )

  max_len = int(getattr(MAX_HISTORY_ENTRIES, "default", 1000))

  log.set("history", [
      *log.typed.history[-max_len:], history_entry
  ])
