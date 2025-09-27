# Data Processing

The `flow` module provides a powerful, functional programming-inspired data processing pipeline system. It allows you to transform, filter, and manipulate data streams using Python expressions in a Unix-pipe style workflow.

## Core Concepts

### Stream Processing

Flow operates on data streams where each line of input becomes a `StreamValue` object that flows through processing stages:

```
Input → Transform → Filter → Aggregate → Output
```

Each processing stage can:
- **Transform** data (map operations)
- **Filter** data (conditional operations)  
- **Aggregate** data (reduce operations)
- **Generate** data (range, iteration)

### Data Flow Model

```bash
# Basic pattern: input | transform | output
echo "hello world" | ptools flow map "x.upper()" 

# Multi-stage pipeline
cat data.txt | \
  ptools flow map "x.strip()" | \
  ptools flow filter "len(x) > 0" | \
  ptools flow map "x.split()[0]"
```

## Basic Operations

### Map Operations

Transform each input item using a Python expression:

```bash
# Convert to uppercase
echo -e "apple\nbanana\ncherry" | ptools flow map "x.upper()"

# Extract parts of strings
echo -e "name:john\nage:30" | ptools flow map "x.split(':')[1]"

# Mathematical operations
ptools flow range 1 10 | ptools flow map "x * x"

# Complex transformations
echo '{"name": "Alice", "age": 25}' | ptools flow map "eval(x)['name']"
```

### Filter Operations

Keep only items that match a condition:

```bash
# Filter by length
echo -e "a\nbb\nccc\ndddd" | ptools flow filter "len(x) > 2"

# Filter by content
cat log.txt | ptools flow filter "'ERROR' in x"

# Numeric filters
ptools flow range 1 20 | ptools flow filter "x % 2 == 0"

# Regex filters
ls | ptools flow filter "re.match(r'.*\.py$', x)"
```

### Reduce Operations

Aggregate data into a single result:

```bash
# Sum numbers
ptools flow range 1 10 | ptools flow reduce "acc + x" --initial 0

# Concatenate strings
echo -e "hello\nworld" | ptools flow reduce "acc + ' ' + x" --initial ""

# Find maximum
echo -e "3\n7\n1\n9\n2" | ptools flow reduce "max(acc, int(x))" --initial 0

# Complex aggregation
cat numbers.txt | ptools flow reduce "{'sum': acc['sum'] + int(x), 'count': acc['count'] + 1}" \
  --initial "{'sum': 0, 'count': 0}"
```

## Advanced Operations

### Range Generation

Generate sequences of numbers:

```bash
# Basic range
ptools flow range 1 10

# With step
ptools flow range 0 100 10

# Negative numbers
ptools flow range 10 -5 -2

# Process generated ranges
ptools flow range 1 5 | ptools flow map "x ** 2"
```

### Unique Operations

Remove duplicates from streams:

```bash
# Basic deduplication
echo -e "apple\nbanana\napple\ncherry\nbanana" | ptools flow unique

# Case-insensitive unique
cat names.txt | ptools flow map "x.lower()" | ptools flow unique

# Unique by transformation
cat emails.txt | ptools flow unique "x.split('@')[1]"  # Unique domains
```

### Grouping Operations

Group items by a key expression:

```bash
# Group by length
echo -e "cat\ndog\nbird\nelephant" | ptools flow group "len(x)"

# Group by first character
cat words.txt | ptools flow group "x[0].lower()"

# Group by file extension
ls | ptools flow group "x.split('.')[-1] if '.' in x else 'no-ext'"

# Group with complex keys
cat logs.txt | ptools flow group "x.split()[0]"  # Group by first word
```

### Foreach Operations

Generate multiple outputs for each input:

```bash
# Split strings into words
echo "hello world test" | ptools flow foreach "x.split()"

# Generate character sequences
echo "abc" | ptools flow foreach "list(x)"

# Process file lines
echo "file1.txt" | ptools flow foreach "open(x).readlines()"

# Mathematical sequences
echo "5" | ptools flow foreach "range(int(x))"
```

### While Loops

Execute loops with conditions:

```bash
# Simple counting
ptools flow while "x + 1" --initial 0 --condition "x < 10"

# Fibonacci sequence
ptools flow while "[x[1], x[0] + x[1]]" --initial "[0, 1]" \
  --condition "x[1] < 100" --output-all

# Collatz sequence
echo "7" | ptools flow while "x // 2 if x % 2 == 0 else 3 * x + 1" \
  --condition "x != 1" --output-all
```

## Output Formats

### JSON Output

Format output as JSON:

```bash
# Simple JSON array
echo -e "apple\nbanana" | ptools flow map "x" --flavor json

# JSON objects
ptools flow range 1 5 | \
  ptools flow map "{'number': x, 'square': x*x}" --flavor json

# Grouped data as JSON
cat data.txt | ptools flow group "x[0]" --flavor json
```

### Custom Output Formatting

```bash
# Tab-separated values
cat data.txt | ptools flow map "x.replace(',', '\t')"

# CSV-like output
ptools flow range 1 5 | ptools flow map "f'{x},{x*x},{x**3}'"

# Formatted strings
cat names.txt | ptools flow map "f'Hello, {x}!'"
```

## Built-in Functions and Utilities

Flow expressions have access to a rich set of built-in functions:

### String Operations

```bash
# String manipulation
echo "Hello World" | ptools flow map "to_upper(x)"
echo "Hello World" | ptools flow map "to_lower(x)"

# JSON operations
echo '{"key": "value"}' | ptools flow map "from_json(x)['key']"
ptools flow map "to_json({'name': x})"
```

### Mathematical Functions

```bash
# Basic math
ptools flow range 1 10 | ptools flow map "sqrt(x)"
ptools flow range 1 10 | ptools flow map "round_value(x / 3, 2)"

# Statistics
echo -e "1\n2\n3\n4\n5" | ptools flow reduce "mean([acc] + [int(x)])" --initial 0
```

### Regular Expressions

```bash
# Pattern matching
cat file.txt | ptools flow filter "regex_match(r'^\d+', x)"
cat file.txt | ptools flow filter "regex_search(r'error|warning', x)"

# Extract patterns
cat logs.txt | ptools flow map "re.search(r'\d{4}-\d{2}-\d{2}', x).group() if re.search(r'\d{4}-\d{2}-\d{2}', x) else None"
```

### Date and Time

```bash
# Current time
ptools flow map "current_time()"

# Date processing (requires datetime module)
echo "2023-01-01" | ptools flow map "datetime.datetime.fromisoformat(x).strftime('%B %d, %Y')"
```

### System Operations

```bash
# Execute commands
echo "ls -la" | ptools flow map "exec(x)"

# Environment variables
ptools flow map "os.environ.get('HOME')"

# File operations  
ptools flow map "os.path.exists(x)"
```

## Real-World Examples

### Log Analysis

```bash
# Parse Apache access logs
cat access.log | \
  ptools flow filter "'GET' in x" | \
  ptools flow map "x.split()[0]" | \
  ptools flow unique | \
  ptools flow --flavor json

# Error log analysis
cat error.log | \
  ptools flow filter "'ERROR' in x" | \
  ptools flow map "x.split()[0]" | \
  ptools flow group "x" | \
  ptools flow --flavor json
```

### Data Transformation

```bash
# CSV to JSON conversion
cat data.csv | \
  ptools flow map "x.split(',')" | \
  ptools flow map "{'name': x[0], 'age': int(x[1]), 'city': x[2]}" | \
  ptools flow --flavor json

# File listing with metadata
ls -la | tail -n +2 | \
  ptools flow map "x.split()" | \
  ptools flow filter "len(x) >= 9" | \
  ptools flow map "{'name': x[-1], 'size': int(x[4]), 'date': ' '.join(x[5:8])}" | \
  ptools flow --flavor json
```

### Text Processing

```bash
# Word frequency analysis
cat document.txt | \
  ptools flow foreach "x.lower().split()" | \
  ptools flow filter "x.isalpha()" | \
  ptools flow group "x" | \
  ptools flow map "{'word': group_key, 'count': len(group)}" | \
  ptools flow --flavor json

# Extract email addresses
cat text_file.txt | \
  ptools flow filter "regex_search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', x)" | \
  ptools flow map "re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', x).group()"
```

### Mathematical Computations

```bash
# Statistical analysis
ptools flow range 1 100 | \
  ptools flow reduce "{'sum': acc.get('sum', 0) + x, 'count': acc.get('count', 0) + 1, 'squares': acc.get('squares', 0) + x*x}" | \
  ptools flow map "{'mean': x['sum']/x['count'], 'variance': x['squares']/x['count'] - (x['sum']/x['count'])**2}"

# Generate multiplication table
ptools flow range 1 11 | \
  ptools flow foreach "[(i, x, i*x) for i in range(1, 11)]" | \
  ptools flow map "f'{x[0]} x {x[1]} = {x[2]}'"
```

## Integration with Other Modules

### Flow + AI

```bash
# Process AI responses
ptools llm "List 10 programming languages" | \
  ptools flow map "x.strip()" | \
  ptools flow filter "x and not x.startswith('#')" | \
  ptools flow unique

# Generate and process data
ptools llm "Generate 5 JSON objects with name and age" | \
  ptools flow filter "x.startswith('{')" | \
  ptools flow map "from_json(x)"
```

### Flow + File Operations

```bash
# Process file listings
ptools fs walkdir --regex "\.py$" | \
  ptools flow map "x.split('/')[-1]" | \
  ptools flow group "x.split('.')[0]"

# Analyze file sizes
ptools fs walkdir --files | \
  ptools flow map "{'file': x, 'size': os.path.getsize(x)}" | \
  ptools flow filter "x['size'] > 1000000"
```

### Flow + JSON

```bash
# Process JSON data
cat data.json | ptools json format | \
  ptools flow map "from_json(x)" | \
  ptools flow map "x.get('important_field')" | \
  ptools flow filter "x is not None"
```

## Best Practices

### Expression Design

1. **Keep expressions simple**:
   ```bash
   # Good: Simple, readable
   ptools flow map "x.upper()"
   
   # Avoid: Complex nested operations
   ptools flow map "{'result': [y.strip().upper() for y in x.split(',') if len(y.strip()) > 0]}"
   ```

2. **Use intermediate steps**:
   ```bash
   # Better: Break into steps
   cat data.txt | \
     ptools flow map "x.split(',')" | \
     ptools flow foreach "x" | \
     ptools flow map "x.strip()" | \
     ptools flow filter "len(x) > 0" | \
     ptools flow map "x.upper()"
   ```

3. **Handle errors gracefully**:
   ```bash
   # Use conditional expressions for safety
   ptools flow map "int(x) if x.isdigit() else 0"
   ptools flow map "x.get('key', 'default') if isinstance(x, dict) else x"
   ```

### Performance Optimization

1. **Filter early**:
   ```bash
   # Good: Filter first, then process
   cat large_file.txt | \
     ptools flow filter "'ERROR' in x" | \
     ptools flow map "parse_error_line(x)"
   ```

2. **Use appropriate data structures**:
   ```bash
   # For unique operations, filtering is more efficient than grouping
   cat data.txt | ptools flow unique  # vs grouping and extracting keys
   ```

3. **Avoid expensive operations in filters**:
   ```bash
   # Expensive: regex in filter
   ptools flow filter "re.match(r'complex.*pattern', x)"
   
   # Better: simple filter first
   ptools flow filter "'keyword' in x" | ptools flow filter "re.match(r'complex.*pattern', x)"
   ```

### Debugging and Development

1. **Use debug mode**:
   ```bash
   ptools flow map "x.upper()" --debug
   ```

2. **Test expressions incrementally**:
   ```bash
   # Start simple
   echo "test" | ptools flow map "x"
   
   # Add complexity step by step
   echo "test" | ptools flow map "x.upper()"
   echo "test" | ptools flow map "x.upper()[:2]"
   ```

3. **Use intermediate outputs**:
   ```bash
   # Save intermediate results for inspection
   cat data.txt | \
     ptools flow map "x.strip()" > step1.txt
   cat step1.txt | \
     ptools flow filter "len(x) > 0" > step2.txt
   ```

## Troubleshooting

### Common Errors

1. **Syntax Errors**:
   ```bash
   # Error: Invalid Python syntax
   ptools flow map "x.upper("  # Missing closing parenthesis
   
   # Solution: Check expression syntax
   python3 -c "x='test'; print(x.upper())"  # Test outside flow
   ```

2. **Name Errors**:
   ```bash
   # Error: undefined variable
   ptools flow map "y.upper()"  # 'y' not defined, should be 'x'
   
   # Solution: Use 'x' for current item
   ptools flow map "x.upper()"
   ```

3. **Type Errors**:
   ```bash
   # Error: calling method on wrong type  
   ptools flow map "int(x).upper()"  # int has no upper() method
   
   # Solution: Check types and conversions
   ptools flow map "str(int(x)).upper()"
   ```

### Performance Issues

1. **Slow processing**:
   - Use `--debug` to see timing information
   - Profile expensive operations
   - Consider breaking complex expressions into steps

2. **Memory usage**:
   - Flow processes streams, not entire datasets
   - Large intermediate objects can cause issues
   - Use generators where possible in expressions

3. **CPU usage**:
   - Avoid complex regex in tight loops
   - Use built-in functions when available
   - Consider parallelization for independent operations
