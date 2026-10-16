from pydantic import BaseModel
from ptools.utils.config import LazyConfigFile
import datetime

class HistoryEntry(BaseModel):
    executable: str
    command: list[str]
    timestamp: str | float

class LogFile(BaseModel):
    history: list[HistoryEntry] = []


def get_log_file() -> "LazyConfigFile[LogFile]":
    today = datetime.date.today().isoformat()
    path = f"logs/log_{today}"
    return LazyConfigFile(path, model=LogFile, quiet=True)
