import json

def load_story(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def play_scene(story, current_scene):
    scene = story[current_scene]
    print(scene["text"])

    if "choices" in scene:
        for key, next_scene in scene["choices"].items():
            print(f"{key}. {next_scene.replace('_', ' ').title()}")

        choice = input("Enter your choice: ")
        if choice in scene["choices"]:
            play_scene(story, scene["choices"][choice])
        else:
            print("Invalid choice. Try again.")
            play_scene(story, current_scene)
    else:
        print("The End.")

def main():
    story = load_story("story.json")
    play_scene(story, "start")

if __name__ == "__main__":
    main()
