import json
import os

# ---------- file names ----------
STORY_FILE = "story.json"
STATE_FILE = "player_state.json"

# ---------- helpers ----------
def load_json(path: str, fallback: dict) -> dict:
    """
    Return the JSON data in *path* if the file exists,
    otherwise return the supplied *fallback* dict.
    """
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return fallback


def save_json(path: str, data: dict) -> None:
    """Write *data* to *path* in pretty-printed JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------- core gameplay ----------
def play_scene(story: dict, player: dict, current_scene: str) -> None:
    """
    Recursively present *current_scene*,
    handle user input, and persist *player* after every step.
    """
    scene = story[current_scene]
    print("\n" + scene["text"])                   # show scene text

    if "choices" in scene:                        # branching scene
        for key, next_tag in scene["choices"].items():
            print(f"{key}. {next_tag.replace('_', ' ').title()}")

        choice = input("Enter your choice: ")
        if choice in scene["choices"]:
            next_tag = scene["choices"][choice]
            play_scene(story, player, next_tag)   # recurse to next scene
        else:
            print("Invalid choice. Try again.")
            play_scene(story, player, current_scene)
    else:                                         # leaf node
        print("The End.")

    # ---------- persist after every scene ----------
    save_json(STATE_FILE, player)


# ---------- main entry ----------
def main() -> None:
    story  = load_json(STORY_FILE, {})
    player = load_json(STATE_FILE, {"courage": 0, "visited": []})
    play_scene(story, player, "start")


if __name__ == "__main__":
    main()
