import os
from pathlib import Path
from enum import Enum
from glob import glob
from collections import defaultdict

from ptools.utils import flatten
from ptools.utils.xml_repr import  xmlclass
from .project import NodeProject, NodeProjects

class WorkspaceType(Enum):
    Turbo = 'turbo'
    Default = 'default'
    
    
DirsGlob = defaultdict(lambda: ['packages/*', 'apps/*'], {
    WorkspaceType.Turbo: ['packages/*', 'apps/*'],
})

@xmlclass
class NodeWorkspace:
    def __init__(self, path: Path, type: WorkspaceType = None, package_manager: str = None):
        self.path = path
        self.type = type
        if self.type is None:
            self.__init__detect_type__()
        self.package_manager = package_manager
        if self.package_manager is None:
            self.__init__detect_package_manager__()
        self.projects = NodeProjects([], package_manager=self.package_manager)
        self.__init__read_projects__()

    def __init__detect_type__(self):
        turboPaths = [
            self.path / 'turbo.json',
            self.path / 'turbo.config.json',
            self.path / 'turbo.config.js',
        ]
        if any(os.path.exists(p) for p in turboPaths):
            self.type = WorkspaceType.Turbo
        else:
            self.type = WorkspaceType.Default
            
    def __init__detect_package_manager__(self):
        if os.path.exists(self.path / 'yarn.lock'):
            self.package_manager = 'yarn'
        elif os.path.exists(self.path / 'pnpm-lock.yaml'):
            self.package_manager = 'pnpm'
        else:
            self.package_manager = 'npm'

    def __init__read_projects__(self):
        pattern = DirsGlob.get(self.type)
        projectDirs = flatten([self.path.glob(p) for p in pattern])
        self.projects = NodeProjects(
            [NodeProject(Path(dir)) for dir in projectDirs],
            package_manager=self.package_manager
        )
    
    def __xml__attrs__(self):
        return {
            'children': self.projects,
            'path': self.path,
            'type': self.type.value,
        }

    def __iter__(self):
        for project in self.projects:
            yield project
            
    def each(self, *args, **kwargs):
        self.projects.each(*args, **kwargs)