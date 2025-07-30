"""
Repository Indexing Router

Provides API endpoints for indexing and searching GitHub repositories.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio

from repository_indexer import indexer

router = APIRouter(prefix="/repository", tags=["repository"])


class IndexRequest(BaseModel):
    repo_url: str
    branch: str = "main"


class SearchRequest(BaseModel):
    repository: str
    query: str
    file_type: Optional[str] = None


class IndexResponse(BaseModel):
    repository: str
    total_files: int
    indexed_files: int
    indexed_file_paths: List[str]
    indexed_at: str


class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_results: int


class StatsResponse(BaseModel):
    repository: str
    total_files: int
    total_size: int
    file_types: Dict[str, int]
    last_indexed: str


@router.post("/index", response_model=IndexResponse)
async def index_repository(request: IndexRequest, background_tasks: BackgroundTasks):
    """Index a GitHub repository"""
    try:
        # Run indexing in background to avoid blocking
        def run_indexing():
            return indexer.index_repository(request.repo_url, request.branch)
        
        # For now, run synchronously. In production, you'd want to use a proper task queue
        result = run_indexing()
        
        return IndexResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index repository: {str(e)}")


@router.get("/stats/{repository}", response_model=StatsResponse)
async def get_repository_stats(repository: str):
    """Get statistics about an indexed repository"""
    try:
        stats = indexer.get_repository_stats(repository)
        
        if "error" in stats:
            raise HTTPException(status_code=404, detail=stats["error"])
        
        return StatsResponse(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get repository stats: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search_repository(request: SearchRequest):
    """Search indexed files in a repository"""
    try:
        results = indexer.search_files(request.repository, request.query, request.file_type)
        
        return SearchResponse(
            results=results,
            total_results=len(results)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search repository: {str(e)}")


@router.get("/list")
async def list_indexed_repositories():
    """List all indexed repositories"""
    try:
        # This would require adding a method to get unique repositories
        # For now, return a simple response
        return {"message": "List repositories endpoint - to be implemented"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list repositories: {str(e)}") 