import os


def get_working_dir():
    return  os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..')


def read_all_json_files(path):
    return [filename for filename in os.listdir(path)
            if filename.endswith('.json')]
