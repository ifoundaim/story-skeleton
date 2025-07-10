from .media import handle_generate_image, handle_generate_voice

TASK_HANDLERS = {
    "generate_image": handle_generate_image,
    "generate_voice": handle_generate_voice,
}

def run_task(task):
    handler = TASK_HANDLERS.get(task["type"])
    if handler:
        return handler(task)
    else:
        print(f"[CODEX] No handler for task type: {task['type']}") 