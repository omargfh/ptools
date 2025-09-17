import json
import os
from pathlib import Path
import subprocess
from typing import Callable
from threading import Thread, Event

from ptools.utils.xml_repr import xmlclass
from ptools.utils.print import FormatUtils

@xmlclass
class NodeProject:
    build: Callable[[bool], None]
    run: Callable[[bool], None]
    start: Callable[[bool], None]
    test: Callable[[bool], None]
    dev: Callable[[bool], None]
    install: Callable[[bool], None]
    
    reserved_names = ['build', 'run', 'start', 'test', 'dev', 'install']
    
    def __init__(self, path: Path, package_manager: str = 'npm'):
        self.name = None
        self.path = path
        self.package_manager = package_manager
        self.scripts = {}
        self.__internals_valid = False

        self.__init__parse_package_json__()
        
    def __init__parse_package_json__(self):
        packageJsonPath = self.path / 'package.json'
        
        if os.path.exists(packageJsonPath):
            with open(packageJsonPath) as f:
                packageJson = json.load(f)
                self.scripts = packageJson.get('scripts', {})
                self.name = packageJson.get('name', self.path.name)
                self.__internals_valid = True
        else:
            self.__internals_valid = False
            
    def __internals_exec_script__(self, name, prefix=True):
        for script in self.scripts:
            cmd = [
                self.package_manager,
                'run',
                script
            ]
            
            is_exact_match = script.lower() == name.lower()
            is_prefix_match = script.lower().startswith(name.lower())
            if (prefix and is_prefix_match) or (is_exact_match):
                subprocess.run(cmd, cwd=self.path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
    def __xml__attrs__(self):
        return {
            'name': self.name,
            'path': self.path.relative_to(Path.cwd()).as_posix(),
            'scriptCount': len(self.scripts),
        }
                
    def is_valid(self) -> bool:
        return self.__internals_valid
          
    def __getattribute__(self, name: str):
        if name in self.reserved_names:
            def method(prefix=True):
                return self.__internals_exec_script__(name, prefix=prefix)
            return method
        return super().__getattribute__(name)

@xmlclass
class NodeProjects(list[NodeProject]):
    def __init__(self, projects: list[NodeProject], package_manager: str = 'npm'):
        self.package_manager = package_manager
        for project in projects:
            project.package_manager = package_manager
            if not project.is_valid():
                projects.remove(project)
        super().__init__(projects)
        
    def __xml__attrs__(self):
        return {
            'children': list(self),
            'count': len(self),
            'package_manager':self.package_manager,
        }

    def __list__(self):
        return [project for project in self]
    
    def each(self, func: Callable[[NodeProject], None], max_workers: int = 4, filter=None):
        """Apply a function to each project in the collection, optionally filtering projects."""
        def worker(project_queue: list[NodeProject], stop_event: Event):
            while not stop_event.is_set():
                try:
                    project = project_queue.pop()
                except IndexError:
                    break
                func(project)
                print(f"{FormatUtils.highlight('✔', 'green')} {project.name}")
        
        project_queue = list(self) 
        if filter:
            project_queue = [p for p in project_queue if filter(p)]
        stop_event = Event()
        threads = []
        
        for _ in range(min(max_workers, len(project_queue))):
            thread = Thread(target=worker, args=(project_queue, stop_event))
            thread.start()
            threads.append(thread)
        
        for thread in threads:
            thread.join()
        stop_event.set()