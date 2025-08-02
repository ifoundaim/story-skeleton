"""
Codex Router for Narrative Media Layer v1 (SPR-MEDIA01)

Handles routing and enqueuing of media generation tasks for scenes.
"""

import asyncio
from typing import Dict, List, Optional, TypedDict
from dataclasses import dataclass
from enum import Enum
import json
import os
import queue
import time
import sys

from media.models import MediaAssets, SceneMedia, MediaGenerationRequest
from media.generator import media_generator
from codex.tasks.soulmap_infer import soulmap_infer


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


@dataclass
class SoulmapInferenceTask:
    """Soulmap delta inference task"""
    task_id: str
    player_id: str
    choice_text: str
    scene_text: str
    emotion_state: Dict[str, float]
    trust_levels: Dict[str, float]
    memory_recap: str
    status: TaskStatus
    result: Optional[Dict[str, float]] = None
    error_message: Optional[str] = None


class CodexRouter:
    """Codex router for media generation and soulmap inference tasks"""
    
    def __init__(self):
        self.media_tasks: Dict[str, MediaTask] = {}
        self.soulmap_tasks: Dict[str, SoulmapInferenceTask] = {}
        self.media_queue: List[str] = []
        self.soulmap_queue: List[str] = []
        self.is_processing_media = False
        self.is_processing_soulmap = False
        
    async def enqueue_media_generation(self, scene_tag: str, scene_text: str, 
                                     theme: str, player_id: str,
                                     generate_images: bool = True,
                                     generate_audio: bool = True) -> str:
        """Enqueue a media generation task, or process synchronously if SYNC_MEDIA_GENERATION is set."""
        sync_mode = os.getenv("SYNC_MEDIA_GENERATION", "false").lower() == "true"
        print(f"[DEBUG] enqueue_media_generation called for scene_tag={scene_tag}, player_id={player_id}, sync_mode={sync_mode}")
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
        self.media_tasks[task_id] = task
        if sync_mode:
            try:
                print(f"[DEBUG] Synchronous media generation for {task_id}")
                task.status = TaskStatus.IN_PROGRESS
                request = MediaGenerationRequest(
                    scene_tag=task.scene_tag,
                    scene_text=task.scene_text,
                    theme=task.theme,
                    player_id=task.player_id,
                    generate_images=task.generate_images,
                    generate_audio=task.generate_audio
                )
                result = await media_generator.generate_scene_media(request)
                task.result = result
                task.status = TaskStatus.COMPLETED
                print(f"✅ [codex] Synchronously completed media task {task_id}")
            except Exception as e:
                print(f"❌ [codex] Synchronous media task failed {task_id}: {e}")
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
        else:
            self.media_queue.append(task_id)
            # Start processing if not already running
            if not self.is_processing_media:
                asyncio.create_task(self._process_media_queue())
            print(f"📋 [codex] Enqueued media task {task_id} for scene {scene_tag}")
        return task_id
    
    async def enqueue_soulmap_inference(
        self,
        player_id: str,
        choice_text: str,
        scene_text: str,
        emotion_state: Dict[str, float],
        trust_levels: Dict[str, float],
        memory_recap: str
    ) -> str:
        """Enqueue a soulmap delta inference task"""
        task_id = f"soulmap_{player_id}_{int(asyncio.get_event_loop().time())}"
        task = SoulmapInferenceTask(
            task_id=task_id,
            player_id=player_id,
            choice_text=choice_text,
            scene_text=scene_text,
            emotion_state=emotion_state,
            trust_levels=trust_levels,
            memory_recap=memory_recap,
            status=TaskStatus.PENDING
        )
        self.soulmap_tasks[task_id] = task
        self.soulmap_queue.append(task_id)
        
        # Start processing if not already running
        if not self.is_processing_soulmap:
            asyncio.create_task(self._process_soulmap_queue())
        
        print(f"🧠 [codex] Enqueued soulmap inference task {task_id} for player {player_id}")
        return task_id
    
    async def _process_media_queue(self):
        """Process the media task queue"""
        print("[DEBUG] _process_media_queue started")
        self.is_processing_media = True
        
        while self.media_queue:
            task_id = self.media_queue.pop(0)
            task = self.media_tasks.get(task_id)
            
            if not task:
                print(f"[DEBUG] No media task found for task_id={task_id}")
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
        
        self.is_processing_media = False
        print("[DEBUG] _process_media_queue finished")
    
    async def _process_soulmap_queue(self):
        """Process the soulmap inference task queue"""
        print("[DEBUG] _process_soulmap_queue started")
        self.is_processing_soulmap = True
        
        while self.soulmap_queue:
            task_id = self.soulmap_queue.pop(0)
            task = self.soulmap_tasks.get(task_id)
            
            if not task:
                print(f"[DEBUG] No soulmap task found for task_id={task_id}")
                continue
            
            try:
                print(f"🧠 [codex] Processing soulmap inference task {task_id}")
                task.status = TaskStatus.IN_PROGRESS
                
                # Call the soulmap inference task
                result = await soulmap_infer.infer_soulmap_delta(
                    choice_text=task.choice_text,
                    scene_text=task.scene_text,
                    emotion_state=task.emotion_state,
                    trust_levels=task.trust_levels,
                    memory_recap=task.memory_recap,
                    player_id=task.player_id
                )
                
                task.result = result
                task.status = TaskStatus.COMPLETED
                
                # 🧠 CRITICAL: Automatically apply the inference result to the database
                if result:
                    try:
                        print(f"🧠 [codex] Attempting to apply soulmap delta for player={task.player_id}: {result}")
                        
                        # Import here to avoid circular imports
                        import sys
                        import os
                        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
                        
                        from soulmap.service import apply_delta
                        from db import SessionLocal
                        
                        db = SessionLocal()
                        try:
                            # Apply the delta to the player's soulmap
                            updated_soulmap = apply_delta(db, task.player_id, result)
                            print(f"✅ [codex] Successfully applied soulmap delta for player={task.player_id}")
                            print(f"✅ [codex] Updated soulmap vector length: {len(updated_soulmap.vec)}")
                        except Exception as db_error:
                            print(f"❌ [codex] Database error applying soulmap delta: {db_error}")
                            import traceback
                            print(f"❌ [codex] Database error traceback: {traceback.format_exc()}")
                        finally:
                            db.close()
                    except ImportError as import_error:
                        print(f"❌ [codex] Import error applying soulmap delta: {import_error}")
                    except Exception as e:
                        print(f"❌ [codex] Failed to apply soulmap delta: {e}")
                        import traceback
                        print(f"❌ [codex] Error traceback: {traceback.format_exc()}")
                else:
                    print(f"⚠️ [codex] No soulmap delta result to apply for task {task_id}")
                
                print(f"✅ [codex] Completed soulmap inference task {task_id}: {result}")
                
            except Exception as e:
                print(f"❌ [codex] Failed soulmap inference task {task_id}: {e}")
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
        
        self.is_processing_soulmap = False
        print("[DEBUG] _process_soulmap_queue finished")
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get the status of a task"""
        # Check media tasks first
        task = self.media_tasks.get(task_id)
        if task:
            return task.status
        
        # Check soulmap tasks
        task = self.soulmap_tasks.get(task_id)
        if task:
            return task.status
        
        return None
    
    def get_task_result(self, task_id: str) -> Optional[SceneMedia]:
        """Get the result of a completed media task"""
        task = self.media_tasks.get(task_id)
        return task.result if task and task.status == TaskStatus.COMPLETED else None
    
    def get_soulmap_task_result(self, task_id: str) -> Optional[Dict[str, float]]:
        """Get the result of a completed soulmap inference task"""
        task = self.soulmap_tasks.get(task_id)
        return task.result if task and task.status == TaskStatus.COMPLETED else None
    
    def check_scene_media(self, scene_tag: str, player_id: str) -> Optional[SceneMedia]:
        """Check if media exists for a scene"""
        print(f"[DEBUG] check_scene_media called for scene_tag={scene_tag}, player_id={player_id}")
        # Look for completed tasks for this scene
        for task in self.media_tasks.values():
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

# Task queue and type
TASK_QUEUE = queue.Queue()
class Task(TypedDict):
    type: str
    playerId: str
    sceneTag: str
    payload: dict

# Ensure tasks/ directory exists for imports
TASKS_DIR = os.path.join(os.path.dirname(__file__), 'tasks')
if not os.path.exists(TASKS_DIR):
    os.makedirs(TASKS_DIR)

# CLI entrypoint for running tasks
if __name__ == "__main__":
    if "--run-tasks" in sys.argv:
        from purpose_agents.tasks.registry import run_task
        print("[CODEX] Task processor started. Waiting for tasks...")
        while True:
            try:
                task = TASK_QUEUE.get(timeout=2)
                print(f"[CODEX] Processing task: {task}")
                run_task(task)
            except queue.Empty:
                time.sleep(1) 