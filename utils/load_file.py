def load_prompt(filepath):
    with open(filepath, "r", encoding="utf-8") as file:
        return file.read()
