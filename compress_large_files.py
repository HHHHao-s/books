#!/usr/bin/env python3
import os
import sys
import json
import argparse
from pathlib import Path

class LargeFileManager:
    def __init__(self, size_limit="100M", split_info_file="split_files_info.json"):
        self.size_limit_bytes = self._parse_size(size_limit)
        self.split_info_file = split_info_file
        self.gitignore_path = Path(".gitignore")
    
    def _parse_size(self, size_str):
        """Convert size string like '100M' to bytes"""
        if size_str.endswith('M'):
            return int(size_str[:-1]) * 1024 * 1024
        elif size_str.endswith('G'):
            return int(size_str[:-1]) * 1024 * 1024 * 1024
        elif size_str.endswith('K'):
            return int(size_str[:-1]) * 1024
        else:
            return int(size_str)
    
    def find_large_files(self):
        """Find files larger than size limit, excluding files in directories starting with ."""
        large_files = []
        for root, dirs, files in os.walk('.'):
            # Remove directories starting with '.' from dirs list to prevent os.walk from entering them
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                file_path = Path(root) / file
                try:
                    if file_path.stat().st_size > self.size_limit_bytes:
                        large_files.append(file_path)
                except (OSError, FileNotFoundError):
                    continue
        return large_files
    
    def _generate_split_prefix(self, file_path):
        """Generate split file prefix based on original file path"""
        # Replace path separators with underscores and remove extension
        file_str = str(file_path).replace('/', '_').replace('\\', '_')
        if file_str.startswith('./'):
            file_str = file_str[2:]
        if file_str.startswith('_'):
            file_str = file_str[1:]
        
        # Remove extension and add split suffix
        stem = Path(file_str).stem
        return f"{stem}_split_"
    
    def check_already_split(self, file_path):
        """Check if a file has already been split and split files exist"""
        split_info = self.load_split_info()
        file_str = str(file_path)
        
        if file_str not in split_info:
            return False, None
        
        file_info = split_info[file_str]
        split_files = file_info.get('split_files', [])
        
        # Check if all split files exist
        all_exist = all(Path(sf).exists() for sf in split_files)
        
        if all_exist:
            # Verify original file size hasn't changed
            current_size = file_path.stat().st_size
            recorded_size = file_info.get('original_size', 0)
            
            if current_size == recorded_size:
                return True, file_info
            else:
                print(f"Warning: {file_path} size changed since last split (was {recorded_size}, now {current_size})")
                # Clean up outdated split files
                self._cleanup_outdated_split_files(split_files)
                return False, None
        else:
            missing_files = [sf for sf in split_files if not Path(sf).exists()]
            print(f"Warning: Some split files missing for {file_path}: {missing_files}")
            return False, None
    
    def _cleanup_outdated_split_files(self, split_files):
        """Remove outdated split files"""
        for split_file in split_files:
            if Path(split_file).exists():
                Path(split_file).unlink()
                print(f"Removed outdated split file: {split_file}")
    
    def split_file_python(self, file_path):
        """Split file using Python file operations"""
        print(f"Splitting {file_path}...")
        
        # Generate split file prefix
        split_prefix = self._generate_split_prefix(file_path)
        
        # Calculate chunk size (slightly smaller than limit)
        chunk_size = self.size_limit_bytes - (1024 * 1024)  # Leave 1MB buffer
        
        split_files = []
        part_number = 0
        
        try:
            with open(file_path, 'rb') as input_file:
                while True:
                    # Read chunk
                    chunk = input_file.read(chunk_size)
                    if not chunk:
                        break
                    
                    # Generate split file name
                    split_filename = f"{split_prefix}{part_number:03d}"
                    split_files.append(split_filename)
                    
                    # Write chunk to split file
                    with open(split_filename, 'wb') as output_file:
                        output_file.write(chunk)
                    
                    size_mb = len(chunk) / (1024 * 1024)
                    print(f"  Created {split_filename}: {size_mb:.1f}MB")
                    
                    part_number += 1
            
            # Prepare split info
            split_info = {
                'original_file': str(file_path),
                'original_size': file_path.stat().st_size,
                'split_prefix': split_prefix,
                'split_files': split_files,
                'split_count': len(split_files)
            }
            
            print(f"Split {file_path} into {len(split_files)} parts")
            return split_info
            
        except Exception as e:
            print(f"Error splitting {file_path}: {e}")
            # Clean up any created split files on error
            for split_file in split_files:
                if Path(split_file).exists():
                    Path(split_file).unlink()
            return None
    
    def load_split_info(self):
        """Load split information from JSON file"""
        if not Path(self.split_info_file).exists():
            return {}
        
        try:
            with open(self.split_info_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading split info: {e}")
            return {}
    
    def append_to_split_info(self, new_split_info):
        """Append new split information to existing JSON file"""
        # Load existing data
        existing_info = self.load_split_info()
        
        # Merge with new data
        existing_info.update(new_split_info)
        
        # Save back to file
        with open(self.split_info_file, 'w') as f:
            json.dump(existing_info, f, indent=2)
        
        print(f"Updated split information in {self.split_info_file}")
    
    def merge_split_files_python(self, file_info):
        """Merge split files back to original file using Python file operations"""
        original_file = file_info['original_file']
        split_files = file_info['split_files']
        expected_size = file_info['original_size']
        
        print(f"Merging {original_file}...")
        
        # Check if all split files exist
        missing_files = [f for f in split_files if not Path(f).exists()]
        if missing_files:
            print(f"Missing split files for {original_file}: {missing_files}")
            return False
        
        # Check if original file already exists
        if Path(original_file).exists():
            current_size = Path(original_file).stat().st_size
            if current_size == expected_size:
                print(f"Original file {original_file} already exists with correct size, skipping merge")
                # Still remove split files
                for split_file in split_files:
                    Path(split_file).unlink()
                    print(f"Removed {split_file}")
                return True
            else:
                print(f"Original file {original_file} exists but size mismatch: expected {expected_size}, got {current_size}")
                print("Will recreate the file from split files")
        
        try:
            # Merge files using Python
            with open(original_file, 'wb') as output_file:
                for split_file in split_files:
                    with open(split_file, 'rb') as input_file:
                        while True:
                            chunk = input_file.read(1024 * 1024)  # Read 1MB at a time
                            if not chunk:
                                break
                            output_file.write(chunk)
            
            # Verify file size
            merged_size = Path(original_file).stat().st_size
            
            if merged_size == expected_size:
                print(f"Successfully merged {original_file} ({merged_size / (1024*1024):.1f}MB)")
                
                # Remove split files
                for split_file in split_files:
                    Path(split_file).unlink()
                    print(f"Removed {split_file}")
                
                return True
            else:
                print(f"Size mismatch for {original_file}: expected {expected_size}, got {merged_size}")
                # Remove the incorrectly merged file
                Path(original_file).unlink()
                return False
                
        except Exception as e:
            print(f"Error merging {original_file}: {e}")
            return False
    
    def add_to_gitignore(self, file_paths):
        """Add file paths to .gitignore"""
        if not file_paths:
            return
        
        existing_entries = set()
        if self.gitignore_path.exists():
            with open(self.gitignore_path, 'r') as f:
                existing_entries = set(line.strip() for line in f if line.strip())
        
        new_entries = set()
        for file_path in file_paths:
            # Convert to relative path and remove leading ./
            if isinstance(file_path, Path):
                rel_path = str(file_path.relative_to('.'))
            else:
                rel_path = str(Path(file_path).relative_to('.'))
            new_entries.add(rel_path)
        
        all_entries = existing_entries | new_entries
        with open(self.gitignore_path, 'w') as f:
            for entry in sorted(all_entries):
                f.write(f"{entry}\n")
        
        print(f"Added {len(new_entries)} files to .gitignore")
    
    def find_split_files(self):
        """Find all split files based on JSON info"""
        split_info = self.load_split_info()
        all_split_files = []
        
        for info in split_info.values():
            all_split_files.extend(info.get('split_files', []))
        
        return [f for f in all_split_files if Path(f).exists()]
    
    def build(self):
        """Find large files, split them, and add to .gitignore (keep original files)"""
        print(f"Finding files larger than {self.size_limit_bytes // (1024*1024)}MB...")
        
        large_files = self.find_large_files()
        if not large_files:
            print("No files larger than size limit found")
            return
        
        print(f"Found {len(large_files)} large files")
        
        # Check which files need to be split
        files_to_split = []
        already_split_count = 0
        
        for file_path in large_files:
            is_split, split_info = self.check_already_split(file_path)
            if is_split:
                print(f"File {file_path} already split into {split_info['split_count']} parts, skipping")
                already_split_count += 1
            else:
                files_to_split.append(file_path)
        
        if already_split_count > 0:
            print(f"Skipped {already_split_count} files that are already split")
        
        if not files_to_split:
            print("No new files need to be split")
            return
        
        print(f"Processing {len(files_to_split)} new files for splitting")
        
        # Split large files and collect split info
        new_split_info = {}
        files_for_gitignore = []
        
        for file_path in files_to_split:
            split_info = self.split_file_python(file_path)
            if split_info:
                new_split_info[str(file_path)] = split_info
                files_for_gitignore.append(file_path)
        
        if not new_split_info:
            print("No files were split")
            return
        
        # Append to existing split information
        self.append_to_split_info(new_split_info)
        
        # Add original files to .gitignore
        self.add_to_gitignore(files_for_gitignore)
        
        print(f"Build completed successfully. Split {len(new_split_info)} new files, {len(files_for_gitignore)} files added to .gitignore")
    
    def extract_all(self):
        """Merge split files back to original files (no gitignore or JSON modification)"""
        split_info = self.load_split_info()
        
        if not split_info:
            print("No split file information found")
            return
        
        print(f"Found split information for {len(split_info)} files")
        
        # Merge split files
        merged_count = 0
        for original_file, file_info in split_info.items():
            if self.merge_split_files_python(file_info):
                merged_count += 1
        
        if merged_count > 0:
            print(f"Successfully merged {merged_count} files")
            print("Note: .gitignore and split info JSON were not modified")
        else:
            print("No files were merged")
    
    def clean(self):
        """Remove all split files and split info file"""
        split_files = self.find_split_files()
        
        if split_files:
            for split_file in split_files:
                Path(split_file).unlink()
                print(f"Removed split file: {split_file}")
            print(f"Cleaned {len(split_files)} split files")
        else:
            print("No split files to clean")
        
        # Remove split info file
        if Path(self.split_info_file).exists():
            Path(self.split_info_file).unlink()
            print(f"Removed {self.split_info_file}")

def main():
    parser = argparse.ArgumentParser(description="Manage large files by splitting them using Python")
    parser.add_argument('command', choices=['build', 'all', 'clean', 'help'],
                       help='Command to execute')
    parser.add_argument('--size-limit', default='100M',
                       help='Size limit for large files (default: 100M)')
    parser.add_argument('--split-info', default='split_files_info.json',
                       help='Split information file (default: split_files_info.json)')
    
    args = parser.parse_args()
    
    if args.command == 'help':
        print("Available commands:")
        print("  build  - Find files >100MB, split them using Python, add to .gitignore (keep originals)")
        print("  all    - Merge split files back to original files (no gitignore/JSON modification)")
        print("  clean  - Remove all split files and split info file")
        print("  help   - Show this help message")
        print("")
        print("Note: Original files are preserved during build process")
        print("Note: 'build' skips files that are already split")
        print("Note: 'all' command reconstructs files but leaves .gitignore and JSON unchanged")
        return
    
    manager = LargeFileManager(args.size_limit, args.split_info)
    
    try:
        if args.command == 'build':
            manager.build()
        elif args.command == 'all':
            manager.extract_all()
        elif args.command == 'clean':
            manager.clean()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()