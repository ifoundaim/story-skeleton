import json, os

# ---------- file names ----------
STORY_FILE = "story.json"
STATE_FILE = "player_state.json"

# ---------- helpers ----------
def load_json(path: str, fallback: dict) -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return fallback


def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------- branching helper ----------
def choose_next_node(player: dict) -> str | None:
    """
    Called when a scene has no choices.
    If courage >= 2 and secret_cave not yet visited, unlock it.
    Otherwise return None so the game ends.
    """
    if player["courage"] >= 2 and "secret_cave" not in player["visited"]:
        return "secret_cave"
    return None


# ---------- core gameplay ----------
def play_scene(story: dict, player: dict, current: str) -> None:
    scene = story[current]
    print("\n" + scene["text"])

    # ---------- demo bravery rule ----------
    brave_tags = {"investigate_noise", "go_to_river"}
    if current in brave_tags:
        player["courage"] += 1

    # ---------- mark scene visited ----------
    if current not in player["visited"]:
        player["visited"].append(current)

    if "choices" in scene:                       # branching node
        for key, tag in scene["choices"].items():
            print(f"{key}. {tag.replace('_', ' ').title()}")

        choice = input("Enter your choice: ")
        if choice in scene["choices"]:
            next_tag = scene["choices"][choice]
            play_scene(story, player, next_tag)
        else:
            print("Invalid choice. Try again.")
            play_scene(story, player, current)
    else:                                        # leaf node
        next_tag = choose_next_node(player)
        if next_tag:
            play_scene(story, player, next_tag)
        else:
            print("The End.")

    # ---------- persist state every turn ----------
    save_json(STATE_FILE, player)


# ---------- main ----------
def main() -> None:
    story  = load_json(STORY_FILE, {})
    player = load_json(STATE_FILE, {"courage": 0, "visited": []})
    play_scene(story, player, "start")


if __name__ == "__main__":
    main()
