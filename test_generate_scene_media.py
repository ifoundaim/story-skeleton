import asyncio
import os
from backend.media.generator import media_generator
from backend.media.models import MediaGenerationRequest

# Set your environment variables here if needed
os.environ["USE_CPU_STUBS"] = "false"  # Set to "true" for placeholder
os.environ["OPENAI_API_KEY"] = "sk-..."  # Your real OpenAI key
os.environ["S3_ENDPOINT_URL"] = "http://localhost:9000"
os.environ["AWS_ACCESS_KEY_ID"] = "minioadmin"
os.environ["AWS_SECRET_ACCESS_KEY"] = "minioadmin"
os.environ["S3_BUCKET_NAME"] = "story-skeleton-media"

async def main():
    req = MediaGenerationRequest(
        scene_tag="test_scene",
        scene_text="A hero stands in a mystical forest at sunset.",
        theme="Hero's Journey",
        player_id="test_player",
        generate_images=True,
        generate_audio=False
    )
    result = await media_generator.generate_scene_media(req)
    print("Success:", result.success)
    print("Images:", result.media.images)
    print("Audio:", result.media.audio)
    if result.error_message:
        print("Error:", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
