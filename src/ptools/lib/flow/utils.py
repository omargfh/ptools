from .values import StreamValue

def stream():
    """Stream one line at a time from stdin, process it, and yield StreamValue objects."""
    import sys
    for line in sys.stdin:
        if line.strip():
            yield StreamValue(line.strip())
        else:
            yield
        
def read_stream():
    """Read all lines from stdin, process them, and return a list of StreamValue objects.
       Skip if stream is empty."""
    import sys
    if sys.stdin.isatty():
        return None
    lines = [line.strip() for line in sys.stdin if line.strip()]
    if not lines:
        return None
    return [StreamValue(line) for line in lines]
    
def yield_scope(stream_value):
    """Create a scope dictionary for evaluating expressions."""
    value = stream_value.value if isinstance(stream_value, StreamValue) else stream_value
        
    if isinstance(value, dict):
        for k, v in value.items():
            yield {'k': k, 'v': v, 'x': v, 'obj': value}
    elif isinstance(value, tuple):
        for i, v in enumerate(value):
            yield {'x': v, 'i': i, 'arr': value}
    elif isinstance(value, set):
        for i, v in enumerate(value):
            yield {'x': v, 'i': i, 'arr': list(value)}
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield {'x': v, 'i': i, 'arr': value}
    else:
        yield {'x': value, 'i': 0, 'arr': [value]}
        
def create_global_scope():
    """Create a global scope with utility functions."""
    import json
    import math
    import statistics
    import re
    import datetime
    import random
    import string
    import subprocess
    import os
    import sys
    import glob
    
    def to_json(value):
        return json.dumps(value)
    
    def from_json(value):
        return json.loads(value)
    
    def to_upper(value):
        return str(value).upper()
    
    def to_lower(value):
        return str(value).lower()
    
    def round_value(value, ndigits=0):
        return round(float(value), ndigits)
    
    def sqrt(value):
        return math.sqrt(float(value))
    
    def mean(values):
        return statistics.mean(values)
    
    def median(values):
        return statistics.median(values)
    
    def regex_match(pattern, string):
        return re.match(pattern, string) is not None
    
    def regex_search(pattern, string):
        return re.search(pattern, string) is not None
    
    def current_time():
        return datetime.datetime.now().isoformat()
    
    def random_choice(seq):
        return random.choice(seq)
    
    def random_string(length=8):
        letters = string.ascii_letters + string.digits
        return ''.join(random.choice(letters) for _ in range(length))
    
    def exec(command):
        result = subprocess.run(command, shell=True, capture_output=True, text=True, env=os.environ)
        return result.stdout.strip()
    
    global_scope = {
        # JSON
        'to_json': to_json,
        'from_json': from_json,
        'json': json,
        # String manipulations
        'to_upper': to_upper,
        'to_lower': to_lower,
        
        # Math and statistics
        'round': round_value,
        'sqrt': sqrt,
        'mean': mean,
        'median': median,
        
        # Regex
        'regex_match': regex_match,
        'regex_search': regex_search,
        
        # Date and time
        'current_time': current_time,
        
        # Random 
        'random_choice': random_choice,
        'random_string': random_string,
        
        # Modules
        'math': math,
        'statistics': statistics,
        're': re,
        'datetime': datetime,
        'random': random,
        'string': string,
        
        # System
        'exec': exec,
        'os': os,
        'sys': sys,
        'glob': glob
    }
    
    class Globals:
        @staticmethod
        def dir():
            return list(global_scope.keys())
        
    global_scope['Globals'] = Globals
    
    return global_scope