"""
Repository Indexer for GitHub repositories

Handles cloning, parsing, and indexing of GitHub repositories for code analysis.
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
import re

from sqlalchemy import Column, String, Text, DateTime, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class IndexedFile(Base):
    """Database model for indexed files"""
    __tablename__ = 'indexed_files'
    
    id = Column(Integer, primary_key=True)
    repository = Column(String, nullable=False, index=True)
    file_path = Column(String, nullable=False)
    file_hash = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    file_type = Column(String, nullable=False, index=True)
    size = Column(Integer, nullable=False)
    indexed_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<IndexedFile(repository='{self.repository}', file_path='{self.file_path}')>"


class RepositoryIndexer:
    """Indexes GitHub repositories for code analysis"""
    
    def __init__(self, db_url: str = "sqlite:///repository_index.db"):
        self.db_url = db_url
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
    def clone_repository(self, repo_url: str, branch: str = "main") -> str:
        """Clone a GitHub repository to a temporary directory"""
        temp_dir = tempfile.mkdtemp(prefix="repo_index_")
        
        try:
            # Clone the repository
            subprocess.run([
                "git", "clone", 
                "--depth", "1",  # Shallow clone for speed
                "--branch", branch,
                repo_url, 
                temp_dir
            ], check=True, capture_output=True)
            
            print(f"✅ Cloned {repo_url} to {temp_dir}")
            return temp_dir
            
        except subprocess.CalledProcessError as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise Exception(f"Failed to clone repository: {e.stderr.decode()}")
    
    def get_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def should_index_file(self, file_path: str) -> bool:
        """Determine if a file should be indexed based on its type and location"""
        # Skip common non-code files and directories
        skip_patterns = [
            r'\.git/',
            r'node_modules/',
            r'\.DS_Store$',
            r'\.log$',
            r'\.lock$',
            r'\.min\.(js|css)$',
            r'dist/',
            r'build/',
            r'coverage/',
            r'\.env',
            r'\.cache/',
            r'\.vscode/',
            r'\.idea/',
        ]
        
        for pattern in skip_patterns:
            if re.search(pattern, file_path):
                return False
        
        # Only index code files
        code_extensions = {
            '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h', 
            '.hpp', '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', 
            '.scala', '.clj', '.hs', '.ml', '.fs', '.v', '.nim', '.zig',
            '.html', '.css', '.scss', '.sass', '.less', '.vue', '.svelte',
            '.md', '.txt', '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg',
            '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd',
            '.dockerfile', '.dockerignore', '.gitignore', '.gitattributes',
            '.editorconfig', '.eslintrc', '.prettierrc', '.babelrc',
            'package.json', 'requirements.txt', 'setup.py', 'pyproject.toml',
            'Cargo.toml', 'go.mod', 'composer.json', 'Gemfile', 'pom.xml',
            'build.gradle', 'CMakeLists.txt', 'Makefile', 'Dockerfile'
        }
        
        file_ext = Path(file_path).suffix.lower()
        file_name = Path(file_path).name.lower()
        
        return file_ext in code_extensions or file_name in code_extensions
    
    def index_repository(self, repo_url: str, branch: str = "main") -> Dict[str, Any]:
        """Index a GitHub repository"""
        print(f"🔍 Starting to index {repo_url}")
        
        # Clone the repository
        temp_dir = self.clone_repository(repo_url, branch)
        
        try:
            session = self.Session()
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            
            indexed_files = []
            total_files = 0
            indexed_count = 0
            
            # Walk through all files in the repository
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, temp_dir)
                    total_files += 1
                    
                    if not self.should_index_file(relative_path):
                        continue
                    
                    try:
                        # Read file content
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        # Calculate file hash
                        file_hash = self.get_file_hash(file_path)
                        
                        # Check if file already exists in database
                        existing = session.query(IndexedFile).filter_by(
                            repository=repo_name,
                            file_path=relative_path,
                            file_hash=file_hash
                        ).first()
                        
                        if existing:
                            print(f"⏭️  Skipping {relative_path} (already indexed)")
                            continue
                        
                        # Create new indexed file record
                        indexed_file = IndexedFile(
                            repository=repo_name,
                            file_path=relative_path,
                            file_hash=file_hash,
                            content=content,
                            file_type=Path(relative_path).suffix.lower(),
                            size=len(content)
                        )
                        
                        session.add(indexed_file)
                        indexed_files.append(relative_path)
                        indexed_count += 1
                        
                        if indexed_count % 100 == 0:
                            print(f"📁 Indexed {indexed_count} files...")
                            
                    except Exception as e:
                        print(f"⚠️  Error indexing {relative_path}: {e}")
                        continue
            
            # Commit all changes
            session.commit()
            
            result = {
                "repository": repo_name,
                "total_files": total_files,
                "indexed_files": indexed_count,
                "indexed_file_paths": indexed_files,
                "indexed_at": datetime.utcnow().isoformat()
            }
            
            print(f"✅ Successfully indexed {repo_name}")
            print(f"   Total files: {total_files}")
            print(f"   Indexed files: {indexed_count}")
            
            return result
            
        except Exception as e:
            session.rollback()
            raise Exception(f"Failed to index repository: {e}")
        finally:
            session.close()
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def search_files(self, repository: str, query: str, file_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search indexed files by content"""
        session = self.Session()
        
        try:
            query_filter = IndexedFile.repository == repository
            if file_type:
                query_filter = query_filter & (IndexedFile.file_type == file_type)
            
            files = session.query(IndexedFile).filter(query_filter).all()
            
            results = []
            for file in files:
                if query.lower() in file.content.lower():
                    results.append({
                        "file_path": file.file_path,
                        "file_type": file.file_type,
                        "size": file.size,
                        "indexed_at": file.indexed_at.isoformat(),
                        "content_preview": file.content[:500] + "..." if len(file.content) > 500 else file.content
                    })
            
            return results
            
        finally:
            session.close()
    
    def get_repository_stats(self, repository: str) -> Dict[str, Any]:
        """Get statistics about an indexed repository"""
        session = self.Session()
        
        try:
            files = session.query(IndexedFile).filter_by(repository=repository).all()
            
            if not files:
                return {"error": "Repository not found"}
            
            # Calculate statistics
            total_files = len(files)  # type: ignore
            total_size = sum(file.size for file in files)  # type: ignore
            file_types: Dict[str, int] = {}
            
            for file in files:
                file_type = file.file_type or "unknown"  # type: ignore
                file_types[file_type] = file_types.get(file_type, 0) + 1  # type: ignore
            
            # Get the most recent indexed_at timestamp
            latest_indexed = max(file.indexed_at for file in files) if files else datetime.utcnow()  # type: ignore
            
            return {
                "repository": repository,
                "total_files": total_files,
                "total_size": total_size,
                "file_types": file_types,
                "last_indexed": latest_indexed.isoformat()
            }
            
        finally:
            session.close()


# Global indexer instance
indexer = RepositoryIndexer() 