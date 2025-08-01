#!/usr/bin/env python3
"""
Script to index the React repository from GitHub
"""

import sys
import os
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from backend.repository_indexer import indexer

def main():
    """Index the React repository"""
    print("🚀 Starting React repository indexing...")
    
    # React repository URL
    react_url = "https://github.com/facebook/react"
    
    try:
        # Index the repository
        result = indexer.index_repository(react_url, branch="main")
        
        print("\n✅ Indexing completed successfully!")
        print(f"Repository: {result['repository']}")
        print(f"Total files found: {result['total_files']}")
        print(f"Files indexed: {result['indexed_files']}")
        print(f"Indexed at: {result['indexed_at']}")
        
        # Show some statistics
        print("\n📊 Repository Statistics:")
        stats = indexer.get_repository_stats(result['repository'])
        if 'error' not in stats:
            print(f"Total size: {stats['total_size']:,} characters")
            print(f"File types:")
            for file_type, count in sorted(stats['file_types'].items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {file_type}: {count} files")
        
        # Test search functionality
        print("\n🔍 Testing search functionality...")
        search_results = indexer.search_files(result['repository'], "useState", ".js")
        print(f"Found {len(search_results)} files containing 'useState' in .js files")
        
        if search_results:
            print("Sample results:")
            for i, result in enumerate(search_results[:3]):
                print(f"  {i+1}. {result['file_path']} ({result['file_type']})")
        
        print("\n🎉 React repository indexing is complete!")
        
    except Exception as e:
        print(f"❌ Error indexing React repository: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 