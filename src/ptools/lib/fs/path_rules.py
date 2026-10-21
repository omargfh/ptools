from pathlib import Path
from enum import Enum

class PathAction(Enum):
    READ = 1
    WRITE = 2
    DELETE = 3
    EXECUTE = 4

class ProtectionDepth(Enum):
    SHALLOW = 1
    CHILDREN = 2
    DEEP = 3

class PathRule:
    def __init__(self, path: Path | str, allowed_actions: list[PathAction], protection_depth: ProtectionDepth):
        self.path = Path(path) if isinstance(path, str) else path
        self.allowed_actions = allowed_actions
        self.protection_depth = protection_depth

    def check(
        self,
        path: Path,
        action: PathAction
    ) -> bool:
        if not self.check_path_applicable(path):
            return True
        return self.check_flags(action)

    def check_path_applicable(
        self,
        path: Path
    ) -> bool:
        if self.protection_depth == ProtectionDepth.SHALLOW:
            return self.path == path
        if self.protection_depth == ProtectionDepth.CHILDREN:
            return self.path == path or self.path in path.parents
        if self.protection_depth == ProtectionDepth.DEEP:
            return self.path == path or self.path in path.parents or path in self.path.parents
        return False

    def check_flags(
        self,
        action: PathAction
    ) -> bool:
        return action not in self.allowed_actions

protected_paths = [
    PathRule("/", [PathAction.READ], ProtectionDepth.SHALLOW),
    PathRule("/etc", [PathAction.READ], ProtectionDepth.DEEP),
    PathRule("/bin", [PathAction.READ, PathAction.EXECUTE], ProtectionDepth.DEEP),
    PathRule("/sbin", [PathAction.READ, PathAction.EXECUTE], ProtectionDepth.DEEP),
    PathRule("/usr", [PathAction.READ], ProtectionDepth.SHALLOW),
    PathRule("/var", [PathAction.READ], ProtectionDepth.SHALLOW)
]