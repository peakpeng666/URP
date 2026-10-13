import os

FOLDER = 'RESULTS_without_robots'

if __name__ == '__main__':
    for filename in os.listdir(os.path.join('.', FOLDER)):
        if not filename.endswith('.json'):
            os.rename(os.path.join('.', FOLDER, filename), os.path.join('.', FOLDER, f'{filename}.json'))
