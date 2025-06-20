from . import UnifiedSyntheticMind


def main():
    usm = UnifiedSyntheticMind()
    print("Unified Synthetic Mind initialized. Type 'exit' to quit.")
    while True:
        try:
            user_input = input('> ')
        except EOFError:
            break
        if user_input.strip().lower() in {'exit', 'quit'}:
            break
        response = usm.get_response(user_input)
        print(response)


if __name__ == '__main__':
    main()
