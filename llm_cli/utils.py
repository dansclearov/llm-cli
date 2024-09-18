import re
import importlib.resources as pkg_resources


def read_system_message_from_file(file_name):
    file_path = pkg_resources.files("llm_cli.prompts").joinpath(file_name)
    with file_path.open("r") as file:
        return file.read()


def get_prompts():
    prompts = []
    pattern = r'prompt_(.+)\.txt'
    for file in pkg_resources.files("llm_cli.prompts").iterdir():
        if match := re.match(pattern, file.name):
            prompts.append(match.group(1))
    return prompts
