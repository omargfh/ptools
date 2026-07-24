from pydantic import BaseModel
from ptools.utils.config import LazyConfigFile

class HistoryEntry(BaseModel):
    executable: str
    command: list[str]
    timestamp: str | float

class LogFile(BaseModel):
    history: list[HistoryEntry] = []


def get_log_file() -> "LazyConfigFile[LogFile]":
    return LazyConfigFile("log", model=LogFile, quiet=True)
