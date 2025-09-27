# File Operations

The file operations module (`fs`) provides enhanced file system navigation, manipulation, and monitoring capabilities that extend beyond standard Unix tools.

## Core File System Commands

### File and Directory Information

Get detailed information about files and directories:

```bash
# Basic file information
ptools fs info /path/to/file

# Directory information with size calculations
ptools fs info /path/to/directory

# Multiple files at once
ptools fs info file1.txt file2.txt directory/
```

The `info` command provides:
- File type and permissions
- Size (human-readable format)
- Creation and modification times
- Owner and group information
- For directories: total size and file count

### Directory Walking and Search

Navigate directory trees with powerful filtering:

```bash
# Basic directory walking
ptools fs walkdir

# Limit search depth
ptools fs walkdir --max-depth 3

# Show only files (no directories)
ptools fs walkdir --files --no-dirs

# Show only directories (no files)
ptools fs walkdir --dirs --no-files

# Include symbolic links
ptools fs walkdir --symlinks

# Filter by regex pattern
ptools fs walkdir --regex "\.py$"
ptools fs walkdir --regex "config.*\.(json|yaml)$"

# Search specific path
ptools fs walkdir --path /home/user/projects
```

### Search Examples

Find specific file types:

```bash
# Find all Python files
ptools fs walkdir --regex "\.py$"

# Find configuration files
ptools fs walkdir --regex "(config|settings)\.(json|yaml|ini)$"

# Find large directories (combine with other tools)
ptools fs walkdir --dirs | xargs -I {} ptools fs info "{}"

# Find recently modified files
ptools fs walkdir --regex "\.(py|js|md)$" | head -20
```

## Advanced File Operations

### Working with File Metadata

Extract and work with file metadata:

```bash
# Get file sizes in different formats
ptools fs info *.log | grep "Size:"

# Find files larger than specific size
ptools fs walkdir | xargs ls -la | awk '$5 > 1000000'

# Sort files by modification time
ptools fs walkdir --files | xargs ls -lt
```

### Integration with Data Processing

Combine file operations with flow processing:

```bash
# Process file names
ptools fs walkdir --regex "\.py$" | \
  ptools flow map "x.split('/')[-1]" | \
  ptools flow filter "len(x) < 20"

# Analyze file extensions
ptools fs walkdir --files | \
  ptools flow map "x.split('.')[-1] if '.' in x else 'no-extension'" | \
  ptools flow group "x" | \
  ptools json format

# Find duplicate filenames
ptools fs walkdir --files | \
  ptools flow map "x.split('/')[-1]" | \
  ptools flow group "x" | \
  ptools flow filter "len(group) > 1"
```

## Rsync Integration

The `rsync` module provides enhanced rsync operations with monitoring capabilities.

### Basic Rsync Operations

Execute rsync with any arguments:

```bash
# Basic sync
ptools rsync do -avz source/ destination/

# Dry run to see what would be copied
ptools rsync do -avzn source/ destination/

# Sync with progress
ptools rsync do -avz --progress source/ destination/

# Exclude patterns
ptools rsync do -avz --exclude="*.pyc" --exclude="__pycache__/" source/ destination/
```

### Watched Rsync

Automatically sync when files change:

```bash
# Watch current directory and sync changes
ptools rsync watch -avz ./ user@server:/backup/

# Watch specific directory with custom delay
ptools rsync watch --path ./src --delay 2.0 -avz ./src/ user@server:/backup/src/

# Watch with exclusions
ptools rsync watch --path ./project -avz --exclude="node_modules/" ./project/ user@server:/backup/
```

The watched rsync:
- Monitors file system events
- Uses debouncing to avoid excessive syncing
- Runs rsync with your specified arguments
- Provides feedback on sync operations

### Rsync Best Practices

1. **Always test with dry run first**:
   ```bash
   ptools rsync do -avzn source/ dest/  # Note the 'n' flag
   ```

2. **Use appropriate exclusions**:
   ```bash
   # Common exclusions for development projects
   ptools rsync do -avz \
     --exclude="node_modules/" \
     --exclude="__pycache__/" \
     --exclude=".git/" \
     --exclude="*.pyc" \
     source/ dest/
   ```

3. **Monitor watched operations**:
   ```bash
   # Use verbose mode to see what's happening
   ptools rsync watch -avz --progress source/ dest/
   ```

## File Watching and Monitoring

The `watch` module provides general-purpose file monitoring capabilities.

### Basic File Watching

Monitor files and directories for changes:

```bash
# Watch current directory
ptools watch --command "echo 'Files changed!'"

# Watch specific path
ptools watch --path /home/user/project --command "make build"

# Custom debounce delay
ptools watch --path ./src --delay 1.0 --command "python test.py"
```

### Watch Command Patterns

The command can use placeholders for event information:

```bash
# Access file path in command
ptools watch --command "echo 'Changed: {filepath}'"

# More complex command with file info
ptools watch --command "echo 'File {filepath} was {event_type} at {timestamp}'"

# Run tests when Python files change
ptools watch --path ./tests --command "python -m pytest {filepath}"
```

### Integration Examples

Combine watching with other PTools modules:

```bash
# Watch and process with AI
ptools watch --path ./docs \
  --command "ptools llm 'Summarize changes in {filepath}' >> changes.log"

# Watch and update data processing
ptools watch --path ./data \
  --command "cat {filepath} | ptools flow map 'process(x)' > processed.json"

# Development workflow
ptools watch --path ./src \
  --command "ptools dev install && ptools test run"
```

## Clipboard Integration

The `clip` module provides clipboard integration for seamless data transfer.

### Basic Clipboard Operations

```bash
# Copy to clipboard
echo "Hello World" | ptools clip copy

# Paste from clipboard
ptools clip paste

# Copy file contents
ptools clip copy < file.txt

# Paste to file
ptools clip paste > output.txt
```

### Integration with Other Modules

Use clipboard in data processing workflows:

```bash
# Process clipboard content
ptools clip paste | ptools flow map "x.upper()" | ptools clip copy

# Copy file list to clipboard
ptools fs walkdir --regex "\.py$" | ptools clip copy

# Process AI response to clipboard
ptools llm "Generate 10 project names" | \
  ptools flow map "x.strip()" | \
  ptools flow filter "len(x) > 0" | \
  ptools clip copy
```

## Best Practices

### File System Navigation

1. **Use regex patterns effectively**:
   ```bash
   # Match multiple extensions
   ptools fs walkdir --regex "\.(py|js|ts)$"
   
   # Match patterns in path
   ptools fs walkdir --regex "test.*\.py$"
   
   # Case-insensitive matching
   ptools fs walkdir --regex "(?i)readme\.(md|txt)$"
   ```

2. **Combine with standard tools**:
   ```bash
   # Find and process
   ptools fs walkdir --regex "\.log$" | xargs tail -f
   
   # Find and analyze
   ptools fs walkdir --files | xargs wc -l | sort -n
   ```

3. **Be mindful of large directories**:
   ```bash
   # Use depth limits
   ptools fs walkdir --max-depth 2
   
   # Focus searches
   ptools fs walkdir --path specific/subdir
   ```

### Rsync Operations

1. **Security considerations**:
   ```bash
   # Use SSH keys for remote sync
   ptools rsync do -avz -e "ssh -i ~/.ssh/id_rsa" source/ user@server:dest/
   ```

2. **Bandwidth optimization**:
   ```bash
   # Compress during transfer
   ptools rsync do -avz --compress-level=9 source/ dest/
   
   # Limit bandwidth
   ptools rsync do -avz --bwlimit=1000 source/ dest/
   ```

3. **Monitoring large syncs**:
   ```bash
   # Show progress for large transfers
   ptools rsync do -avz --progress --stats source/ dest/
   ```

### File Watching

1. **Efficient command execution**:
   ```bash
   # Use specific file extensions to reduce events
   ptools watch --regex "\.py$" --command "pylint {filepath}"
   ```

2. **Avoid recursive operations**:
   ```bash
   # Don't watch the output directory if command writes there
   ptools watch --path src/ --command "build output/"  # Good
   ptools watch --path ./ --command "build ./"         # Bad (recursive)
   ```

3. **Debug watch operations**:
   ```bash
   # Use echo to see what events trigger
   ptools watch --command "echo 'Event: {event_type} on {filepath}'"
   ```

## Troubleshooting

### Common Issues

1. **Permission Errors**:
   ```bash
   # Check file permissions
   ptools fs info /path/to/file
   
   # Use appropriate user permissions
   sudo ptools fs walkdir /restricted/path
   ```

2. **Rsync Failures**:
   ```bash
   # Test connectivity first
   ssh user@server "echo 'Connection OK'"
   
   # Use dry run to check
   ptools rsync do -avzn source/ dest/
   ```

3. **Watch Not Triggering**:
   ```bash
   # Check if path exists
   ptools fs info /watch/path
   
   # Use broader pattern
   ptools watch --path ./ --command "echo 'Any change'"
   ```

### Performance Considerations

1. **Large Directory Trees**:
   - Use `--max-depth` to limit recursion
   - Filter early with specific regex patterns
   - Consider processing in chunks

2. **Network Operations**:
   - Test with small files first
   - Use appropriate compression settings
   - Monitor bandwidth usage

3. **File Watching**:
   - Use specific paths rather than watching entire file systems
   - Implement appropriate debouncing delays
   - Be careful with commands that modify watched directories
