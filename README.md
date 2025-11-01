## Available commands:
```bash
make build   # Find files >100M and split them using split command
make all     # Merge split files back to original files
make clean   # Remove all split files and split info file
make status  # Show current split files status
make help    # Show this help message
```
## Variables:
```bash
SIZE_LIMIT = 100M  #(can be overridden: make build SIZE_LIMIT=50M)
SPLIT_INFO_FILE = split_files_info.json
```
## Examples:
```bash
make build SIZE_LIMIT=50M    # Split files larger than 50MB
make status                  # Check current split status
```
