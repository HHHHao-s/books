# Makefile for managing large files using Python split script

# Variables
PYTHON_SCRIPT = compress_large_files.py
SIZE_LIMIT = 100M
SPLIT_INFO_FILE = split_files_info.json

# Check if Python script exists
check-script:
	@if [ ! -f $(PYTHON_SCRIPT) ]; then \
		echo "Error: $(PYTHON_SCRIPT) not found"; \
		exit 1; \
	fi

# Find files larger than 100MB and split them
build: check-script
	@echo "Splitting large files (>$(SIZE_LIMIT))..."
	@python3 $(PYTHON_SCRIPT) build --size-limit $(SIZE_LIMIT) --split-info $(SPLIT_INFO_FILE)

# Merge split files back to original files
all: check-script
	@echo "Merging split files back to original files..."
	@python3 $(PYTHON_SCRIPT) all --split-info $(SPLIT_INFO_FILE)

# Clean up - remove all split files and info file
clean: check-script
	@echo "Cleaning up split files..."
	@python3 $(PYTHON_SCRIPT) clean --split-info $(SPLIT_INFO_FILE)

# Show status of split files
status: check-script
	@echo "Split files status:"
	@if [ -f $(SPLIT_INFO_FILE) ]; then \
		echo "Split info file exists: $(SPLIT_INFO_FILE)"; \
		python3 -c "import json; info=json.load(open('$(SPLIT_INFO_FILE)')); print(f'Number of split files: {len(info)}')"; \
		echo "Original files:"; \
		python3 -c "import json; info=json.load(open('$(SPLIT_INFO_FILE)')); [print(f'  {k} -> {v[\"split_count\"]} parts') for k,v in info.items()]"; \
	else \
		echo "No split info file found"; \
	fi
	@echo "Current split files in directory:"
	@ls -la *_split_* 2>/dev/null || echo "  No split files found"

# Show help
help:
	@echo "Available commands:"
	@echo "  make build   - Find files >$(SIZE_LIMIT) and split them using split command"
	@echo "  make all     - Merge split files back to original files"
	@echo "  make clean   - Remove all split files and split info file"
	@echo "  make status  - Show current split files status"
	@echo "  make help    - Show this help message"
	@echo ""
	@echo "Variables:"
	@echo "  SIZE_LIMIT = $(SIZE_LIMIT)  (can be overridden: make build SIZE_LIMIT=50M)"
	@echo "  SPLIT_INFO_FILE = $(SPLIT_INFO_FILE)"
	@echo ""
	@echo "Examples:"
	@echo "  make build SIZE_LIMIT=50M    # Split files larger than 50MB"
	@echo "  make status                  # Check current split status"

# Force rebuild - clean and build
rebuild: clean build

# Verify integrity of split files
verify: check-script
	@echo "Verifying split files integrity..."
	@if [ -f $(SPLIT_INFO_FILE) ]; then \
		python3 -c " \
import json, os; \
info = json.load(open('$(SPLIT_INFO_FILE)')); \
missing = []; \
for orig, data in info.items(): \
    for split_file in data['split_files']: \
        if not os.path.exists(split_file): \
            missing.append(split_file); \
if missing: \
    print('Missing split files:'); \
    [print(f'  {f}') for f in missing]; \
    exit(1); \
else: \
    print('All split files are present'); \
		"; \
	else \
		echo "No split info file found - nothing to verify"; \
	fi

.PHONY: build all clean help status rebuild verify check-script