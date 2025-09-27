# Workflow Automation

PTools excels at automating repetitive tasks and creating efficient workflows. This section covers advanced automation techniques and patterns.

## File Watching and Automation

The `watch` module provides event-driven automation capabilities.

### Basic File Watching

```bash
# Watch current directory for any changes
ptools watch --command "echo 'Files changed!'"

# Watch specific directory
ptools watch --path /home/user/project --command "make build"

# Watch with custom delay (debouncing)
ptools watch --path ./src --delay 2.0 --command "npm run test"
```

### Advanced Watch Patterns

#### Development Workflow Automation

```bash
# Auto-run tests when Python files change
ptools watch --path src/ --regex "\.py$" --command "python -m pytest tests/ -v"

# Auto-format code on save
ptools watch --path src/ --regex "\.py$" --command "black {filepath} && echo 'Formatted {filepath}'"

# Multi-step build process
ptools watch --path src/ --command "
    echo 'Building project...'
    npm run build && 
    npm run test && 
    echo 'Build successful!' || 
    echo 'Build failed!'
"
```

#### Content Management

```bash
# Auto-generate documentation
ptools watch --path docs/ --regex "\.md$" --command "mkdocs build"

# Process images on upload
ptools watch --path uploads/ --regex "\.(jpg|png)$" --command "
    convert {filepath} -resize 800x600 processed/{filename}
    echo 'Processed {filepath}'
"

# Auto-backup important files
ptools watch --path important/ --command "
    ptools rsync do -avz important/ /backup/$(date +%Y%m%d_%H%M%S)/
"
```

## Rsync Automation

The `rsync` module provides powerful synchronization automation.

### Continuous Synchronization

```bash
# Sync local development to remote server
ptools rsync watch --path ./src -avz ./src/ user@server:/app/src/

# Multi-directory sync with exclusions
ptools rsync watch --path ./ -avz \
    --exclude "node_modules/" \
    --exclude ".git/" \
    --exclude "*.pyc" \
    ./ user@server:/backup/

# Bidirectional sync (use with caution)
ptools rsync watch --path ./ -avz --update ./ user@server:/shared/
```

### Deployment Automation

```bash
# Deploy on successful tests
ptools watch --path src/ --command "
    if python -m pytest; then
        echo 'Tests passed, deploying...'
        ptools rsync do -avz --delete src/ user@production:/app/
        ssh user@production 'systemctl restart myapp'
    else
        echo 'Tests failed, deployment skipped'
    fi
"

# Staged deployment process
ptools watch --path src/ --command "
    # Deploy to staging first
    ptools rsync do -avz src/ user@staging:/app/
    
    # Run integration tests on staging
    if ssh user@staging 'cd /app && npm run test:integration'; then
        echo 'Staging tests passed, deploying to production...'
        ptools rsync do -avz src/ user@production:/app/
    else
        echo 'Staging tests failed, production deployment aborted'
    fi
"
```

## Data Processing Automation

Combine flow processing with automation for powerful data workflows.

### Log Processing

```bash
# Process new log entries
ptools watch --path /var/log/app.log --command "
    tail -n 1 {filepath} | 
    ptools flow filter 'ERROR' | 
    ptools flow map 'extract_error(x)' |
    ptools llm 'Analyze this error and suggest solutions'
"

# Aggregate log statistics
ptools watch --path logs/ --regex "\.log$" --command "
    cat {filepath} |
    ptools flow filter 'contains_timestamp(x)' |
    ptools flow group 'extract_hour(x)' |
    ptools flow map 'format_stats(group_key, len(group))' |
    ptools json format > hourly_stats.json
"
```

### Data Transformation Pipelines

```bash
# Process CSV uploads
ptools watch --path data/incoming/ --regex "\.csv$" --command "
    cat {filepath} |
    ptools flow map 'x.split(\",\")' |
    ptools flow filter 'len(x) >= 3' |
    ptools flow map 'transform_row(x)' |
    ptools json format > data/processed/{filename}.json
"

# ETL Pipeline
ptools watch --path raw_data/ --command "
    # Extract
    cat {filepath} |
    
    # Transform
    ptools flow map 'clean_data(x)' |
    ptools flow filter 'is_valid(x)' |
    ptools flow map 'enrich_data(x)' |
    
    # Load
    ptools json format |
    curl -X POST -H 'Content-Type: application/json' -d @- http://api.example.com/data
"
```

## AI-Powered Automation

Integrate AI into your automation workflows.

### Intelligent Content Processing

```bash
# AI-powered documentation updates
ptools watch --path src/ --regex "\.py$" --command "
    ptools llm 'Generate documentation for this code:' < {filepath} > docs/{filename}.md
"

# Code review automation
ptools watch --path pull_requests/ --command "
    ptools llm 'Review this code change for potential issues:' < {filepath} |
    ptools flow map 'format_review_comment(x)' > reviews/{filename}.md
"

# Automated issue classification
ptools watch --path issues/ --regex "\.txt$" --command "
    CATEGORY=\$(ptools llm 'Classify this issue as bug/feature/question:' < {filepath} | head -1)
    mv {filepath} issues/\$CATEGORY/{filename}
"
```

### Smart Notifications

```bash
# Intelligent error alerting
ptools watch --path logs/error.log --command "
    LAST_ERROR=\$(tail -1 {filepath})
    SEVERITY=\$(echo \"\$LAST_ERROR\" | ptools llm 'Rate severity 1-10:')
    
    if [ \"\$SEVERITY\" -gt 7 ]; then
        echo \"\$LAST_ERROR\" | 
        ptools llm 'Explain this error and suggest immediate actions:' |
        mail -s 'URGENT: High Severity Error' admin@company.com
    fi
"
```

## Complex Workflow Examples

### Full-Stack Development Automation

```bash
#!/bin/bash
# development-automation.sh

# Frontend automation
ptools watch --path frontend/src --command "
    cd frontend &&
    npm run lint &&
    npm run test &&
    npm run build &&
    ptools rsync do -avz build/ user@staging:/var/www/
" &

# Backend automation  
ptools watch --path backend/src --regex "\.py$" --command "
    cd backend &&
    python -m pytest tests/ &&
    python -m pylint src/ &&
    
    # Deploy if tests pass
    if [ \$? -eq 0 ]; then
        ptools rsync do -avz src/ user@staging:/app/
        ssh user@staging 'systemctl restart myapp'
    fi
" &

# Database migration automation
ptools watch --path database/migrations --regex "\.sql$" --command "
    echo 'New migration detected: {filepath}'
    
    # Ask AI to review migration
    ptools llm 'Review this SQL migration for potential issues:' < {filepath} > migration_review.txt
    
    # Apply to staging if review passes
    echo 'Migration reviewed, applying to staging...'
    ssh user@staging 'cd /app && python manage.py migrate'
"
```

### Content Management Workflow

```bash
#!/bin/bash
# content-workflow.sh

# Process markdown articles
ptools watch --path articles/ --regex "\.md$" --command "
    # Generate HTML
    pandoc {filepath} -o html/{filename}.html
    
    # Generate summary using AI
    ptools llm 'Write a 2-sentence summary of this article:' < {filepath} > summaries/{filename}.txt
    
    # Extract keywords
    ptools llm 'List 5 keywords for this article (comma-separated):' < {filepath} |
    ptools flow map 'x.strip()' > keywords/{filename}.txt
    
    # Update search index
    echo 'Updated content for {filename}'
"

# Image processing pipeline
ptools watch --path images/raw --regex "\.(jpg|png)$" --command "
    # Generate thumbnails
    convert {filepath} -resize 150x150^ -gravity center -extent 150x150 thumbnails/{filename}
    
    # Optimize for web
    convert {filepath} -quality 80 -resize 800x600 optimized/{filename}
    
    # Generate alt text using AI
    ptools llm 'Generate descriptive alt text for this image filename:' {filename} > alt_text/{filename}.txt
"
```

### DevOps Automation

```bash
#!/bin/bash
# devops-automation.sh

# Configuration management
ptools watch --path config/ --regex "\.yaml$" --command "
    # Validate configuration
    python -c 'import yaml; yaml.safe_load(open(\"{filepath}\"))'
    
    if [ \$? -eq 0 ]; then
        echo 'Configuration valid, deploying...'
        
        # Deploy to all environments
        for env in staging production; do
            ptools rsync do -avz config/ user@\$env:/etc/myapp/
            ssh user@\$env 'systemctl reload myapp'
        done
        
        # Log deployment
        echo \"\$(date): Deployed {filepath}\" >> deployment.log
    else
        echo 'Configuration invalid, deployment aborted'
        exit 1
    fi
"

# Infrastructure monitoring
ptools watch --path metrics/ --command "
    # Process metrics
    cat {filepath} |
    ptools flow map 'parse_metric(x)' |
    ptools flow filter 'is_anomaly(x)' |
    
    # Alert on anomalies
    while read line; do
        ALERT=\$(echo \"\$line\" | ptools llm 'Should this metric trigger an alert? Yes/No:')
        if [ \"\$ALERT\" = \"Yes\" ]; then
            echo \"\$line\" | mail -s 'Metric Anomaly Detected' ops@company.com
        fi
    done
"
```

## Automation Best Practices

### Design Principles

1. **Idempotent Operations**: Ensure automation can be safely re-run
   ```bash
   # Good: Check before creating
   ptools watch --command "
       if [ ! -f output/{filename} ]; then
           process_file {filepath} > output/{filename}
       fi
   "
   ```

2. **Error Handling**: Always handle failures gracefully
   ```bash
   ptools watch --command "
       if process_file {filepath}; then
           echo 'Success: {filepath}'
       else
           echo 'Error processing {filepath}' >> error.log
           exit 0  # Don't stop watching
       fi
   "
   ```

3. **Logging and Monitoring**: Keep track of automation activities
   ```bash
   ptools watch --command "
       echo \"\$(date): Processing {filepath}\" >> automation.log
       process_file {filepath}
       echo \"\$(date): Completed {filepath}\" >> automation.log
   "
   ```

### Performance Considerations

1. **Debouncing**: Use appropriate delays to avoid excessive triggering
   ```bash
   ptools watch --delay 5.0 --command "expensive_operation"
   ```

2. **Resource Management**: Be mindful of system resources
   ```bash
   # Limit concurrent operations
   ptools watch --command "
       if [ \$(jobs -r | wc -l) -lt 3 ]; then
           expensive_task &
       else
           echo 'Too many jobs running, skipping'
       fi
   "
   ```

3. **Batch Processing**: Group related operations
   ```bash
   # Collect changes and process in batches
   ptools watch --delay 10.0 --command "
       find . -newer .last_processed -name '*.py' |
       xargs python process_batch.py
       touch .last_processed
   "
   ```

### Security Considerations

1. **Validate Inputs**: Always validate file contents and paths
   ```bash
   ptools watch --command "
       if [ -f {filepath} ] && [ \"\$(file -b {filepath})\" = 'ASCII text' ]; then
           safe_process {filepath}
       else
           echo 'Skipping potentially unsafe file: {filepath}'
       fi
   "
   ```

2. **Limit Scope**: Use specific paths and patterns
   ```bash
   # Good: Specific pattern
   ptools watch --path trusted/directory --regex "\.txt$"
   
   # Avoid: Too broad
   ptools watch --path /
   ```

3. **User Permissions**: Run with minimal required permissions
   ```bash
   # Create dedicated user for automation
   sudo useradd -r automation-user
   sudo -u automation-user ptools watch --command "safe_command"
   ```

## Troubleshooting Automation

### Common Issues

1. **Watch Not Triggering**:
   ```bash
   # Test file system events
   ptools watch --command "echo 'Event detected: {event_type} on {filepath}'"
   
   # Check file system permissions
   ls -la /path/being/watched
   ```

2. **Commands Failing Silently**:
   ```bash
   # Add explicit error handling
   ptools watch --command "
       command_that_might_fail || {
           echo 'Command failed for {filepath}' >&2
           exit 1
       }
   "
   ```

3. **Resource Exhaustion**:
   ```bash
   # Monitor resource usage
   ptools watch --command "
       echo 'CPU: \$(top -bn1 | grep 'Cpu(s)' | cut -d' ' -f2)'
       echo 'Memory: \$(free -h | grep Mem | awk '{print \$3}')'
       actual_command
   "
   ```

### Debugging Automation

1. **Enable Debug Mode**:
   ```bash
   export PTOOLS_DEBUG=1
   ptools watch --command "debug_command"
   ```

2. **Add Verbose Logging**:
   ```bash
   ptools watch --command "
       echo '\$(date): Starting {filepath}' >> debug.log
       set -x  # Enable bash debugging
       your_command
       set +x  # Disable bash debugging
       echo '\$(date): Finished {filepath}' >> debug.log
   "
   ```

3. **Test Commands Separately**:
   ```bash
   # Test command outside of watch
   filepath="/test/file.txt"
   your_command_here
   
   # Then add to watch
   ptools watch --command "your_command_here"
   ```

Workflow automation with PTools enables you to create sophisticated, intelligent automation systems that can handle complex development, deployment, and data processing tasks with minimal manual intervention.
