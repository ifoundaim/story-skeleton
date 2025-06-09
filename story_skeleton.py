def main():
    print("Welcome to the Story Skeleton!")
    print("You are standing at a crossroad. Where do you want to go?")
    print("1. Left towards the dark forest")
    print("2. Right towards the sunny meadow")

    choice = input("Enter 1 or 2: ")

    if choice == "1":
        print("You walk into the dark forest and feel the trees close around you...")
    elif choice == "2":
        print("You head into the sunny meadow, the warm sun on your skin...")
    else:
        print("That's not a valid choice.")

if __name__ == "__main__":
    main()
