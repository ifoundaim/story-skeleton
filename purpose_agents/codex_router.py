"""
Codex Router for Narrative Media Layer v1 (SPR-MEDIA01)

Handles routing and enqueuing of media generation tasks for scenes.
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import json
import os

from backend.media.models import MediaAssets, SceneMedia, MediaGenerationRequest
from backend.media.generator import media_generator


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class MediaTask:
    """Media generation task"""
    task_id: str
    scene_tag: str
    player_id: str
    scene_text: str
    theme: str
    generate_images: bool
    generate_audio: bool
    status: TaskStatus
    result: Optional[SceneMedia] = None
    error_message: Optional[str] = None


class CodexRouter:
    """Codex router for media generation tasks"""
    
    def __init__(self):
        self.tasks: Dict[str, MediaTask] = {}
        self.task_queue: List[str] = []
        self.is_processing = False
        
    async def enqueue_media_generation(self, scene_tag: str, scene_text: str, 
                                     theme: str, player_id: str,
                                     generate_images: bool = True,
                                     generate_audio: bool = True) -> str:
        """Enqueue a media generation task"""
        print(f"[DEBUG] enqueue_media_generation called for scene_tag={scene_tag}, player_id={player_id}")
        task_id = f"{player_id}_{scene_tag}_{int(asyncio.get_event_loop().time())}"
        
        task = MediaTask(
            task_id=task_id,
            scene_tag=scene_tag,
            player_id=player_id,
            scene_text=scene_text,
            theme=theme,
            generate_images=generate_images,
            generate_audio=generate_audio,
            status=TaskStatus.PENDING
        )
        
        self.tasks[task_id] = task
        self.task_queue.append(task_id)
        
        # Start processing if not already running
        if not self.is_processing:
            asyncio.create_task(self._process_queue())
        
        print(f"📋 [codex] Enqueued media task {task_id} for scene {scene_tag}")
        return task_id
    
    async def _process_queue(self):
        """Process the task queue"""
        print("[DEBUG] _process_queue started")
        self.is_processing = True
        
        while self.task_queue:
            print(f"[DEBUG] Task queue: {self.task_queue}")
            task_id = self.task_queue.pop(0)
            task = self.tasks.get(task_id)
            
            if not task:
                print(f"[DEBUG] No task found for task_id={task_id}")
                continue
            
            try:
                print(f"🔄 [codex] Processing media task {task_id}")
                task.status = TaskStatus.IN_PROGRESS
                
                print(f"[DEBUG] Creating MediaGenerationRequest with generate_images={task.generate_images}, generate_audio={task.generate_audio}")
                # Create media generation request
                request = MediaGenerationRequest(
                    scene_tag=task.scene_tag,
                    scene_text=task.scene_text,
                    theme=task.theme,
                    player_id=task.player_id,
                    generate_images=task.generate_images,
                    generate_audio=task.generate_audio
                )
                
                print(f"[DEBUG] Calling media_generator.generate_scene_media for scene_tag={task.scene_tag}, player_id={task.player_id}")
                # Generate media
                result = await media_generator.generate_scene_media(request)
                task.result = result
                task.status = TaskStatus.COMPLETED
                
                print(f"✅ [codex] Completed media task {task_id}")
                
            except Exception as e:
                print(f"❌ [codex] Failed media task {task_id}: {e}")
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
        
        self.is_processing = False
        print("[DEBUG] _process_queue finished")
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get the status of a task"""
        task = self.tasks.get(task_id)
        return task.status if task else None
    
    def get_task_result(self, task_id: str) -> Optional[SceneMedia]:
        """Get the result of a completed task"""
        task = self.tasks.get(task_id)
        return task.result if task and task.status == TaskStatus.COMPLETED else None
    
    def check_scene_media(self, scene_tag: str, player_id: str) -> Optional[SceneMedia]:
        """Check if media exists for a scene"""
        print(f"[DEBUG] check_scene_media called for scene_tag={scene_tag}, player_id={player_id}")
        # Look for completed tasks for this scene
        for task in self.tasks.values():
            if (task.scene_tag == scene_tag and 
                task.player_id == player_id and 
                task.status == TaskStatus.COMPLETED):
                print(f"[DEBUG] Found completed task {task.task_id} for scene {scene_tag}")
                return task.result
        print(f"[DEBUG] No completed media found for scene {scene_tag}")
        return None
    
    def should_generate_media(self, scene_media: Optional[MediaAssets]) -> tuple[bool, bool]:
        """Determine if media should be generated for a scene"""
        if not scene_media:
            return True, True  # Generate both images and audio
        
        # Check if images are missing
        generate_images = not scene_media.images
        
        # Check if audio is missing
        generate_audio = not scene_media.audio
        
        return generate_images, generate_audio


# Global codex router instance
codex_router = CodexRouter() 