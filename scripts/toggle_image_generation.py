#!/usr/bin/env python3
"""
Toggle image generation blocking for testing.

This script provides an easy way to enable/disable image generation
to save API costs during testing.

Usage:
    python scripts/toggle_image_generation.py block    # Block image generation
    python scripts/toggle_image_generation.py enable   # Enable image generation
    python scripts/toggle_image_generation.py status   # Show current status
"""

import os
import sys
from pathlib import Path


def get_env_file_path():
    """Get the path to the .env file."""
    # Look for .env file in project root
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"
    return env_file


def get_backend_env_file_path():
    """Get the path to the backend .env file."""
    project_root = Path(__file__).parent.parent
    backend_env_file = project_root / "backend" / ".env"
    return backend_env_file


def read_env_file():
    """Read the current .env file."""
    env_file = get_env_file_path()
    return read_env_file_from_path(env_file)


def write_env_file(env_vars):
    """Write variables to .env file."""
    env_file = get_env_file_path()
    backend_env_file = get_backend_env_file_path()
    
    # Create backup for main .env
    if env_file.exists():
        backup_file = env_file.with_suffix('.env.backup')
        env_file.rename(backup_file)
        print(f"📋 Created backup: {backup_file}")
    
    # Write new main .env file
    with open(env_file, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    print(f"✅ Updated {env_file}")
    
    # Also update backend .env file if it exists
    if backend_env_file.exists():
        backend_env_vars = read_env_file_from_path(backend_env_file)
        backend_env_vars['BLOCK_IMAGE_GENERATION'] = env_vars.get('BLOCK_IMAGE_GENERATION', 'false')
        
        with open(backend_env_file, 'w') as f:
            for key, value in backend_env_vars.items():
                f.write(f"{key}={value}\n")
        
        print(f"✅ Updated {backend_env_file}")


def read_env_file_from_path(env_file_path):
    """Read the .env file from a specific path."""
    if not env_file_path.exists():
        return {}
    
    env_vars = {}
    with open(env_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
    return env_vars


def block_image_generation():
    """Block image generation by setting BLOCK_IMAGE_GENERATION=true."""
    env_vars = read_env_file()
    env_vars['BLOCK_IMAGE_GENERATION'] = 'true'
    write_env_file(env_vars)
    print("🛑 Image generation blocked!")
    print("   Set BLOCK_IMAGE_GENERATION=false to re-enable")


def enable_image_generation():
    """Enable image generation by setting BLOCK_IMAGE_GENERATION=false."""
    env_vars = read_env_file()
    env_vars['BLOCK_IMAGE_GENERATION'] = 'false'
    write_env_file(env_vars)
    print("✅ Image generation enabled!")
    print("   Set BLOCK_IMAGE_GENERATION=true to block again")


def show_status():
    """Show current image generation status."""
    env_vars = read_env_file()
    
    block_image = env_vars.get('BLOCK_IMAGE_GENERATION', 'false').lower() == 'true'
    use_cpu_stubs = env_vars.get('USE_CPU_STUBS', 'false').lower() == 'true'
    openai_key = bool(env_vars.get('OPENAI_API_KEY', ''))
    
    print("📋 Current Image Generation Status:")
    print(f"  • BLOCK_IMAGE_GENERATION: {'🛑 BLOCKED' if block_image else '✅ ENABLED'}")
    print(f"  • USE_CPU_STUBS: {'🛑 BLOCKED' if use_cpu_stubs else '✅ ENABLED'}")
    print(f"  • OpenAI API Key: {'✅ CONFIGURED' if openai_key else '❌ MISSING'}")
    
    if block_image or use_cpu_stubs:
        print("\n🛑 Image generation is currently BLOCKED")
        if block_image:
            print("   Run: python scripts/toggle_image_generation.py enable")
        if use_cpu_stubs:
            print("   Also set USE_CPU_STUBS=false in .env file")
    else:
        print("\n✅ Image generation is currently ENABLED")
        print("   Run: python scripts/toggle_image_generation.py block")


def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage:")
        print("  python scripts/toggle_image_generation.py block    # Block image generation")
        print("  python scripts/toggle_image_generation.py enable   # Enable image generation")
        print("  python scripts/toggle_image_generation.py status   # Show current status")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'block':
        block_image_generation()
    elif command == 'enable':
        enable_image_generation()
    elif command == 'status':
        show_status()
    else:
        print(f"❌ Unknown command: {command}")
        print("Valid commands: block, enable, status")
        sys.exit(1)


if __name__ == "__main__":
    main() 