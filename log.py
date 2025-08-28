from flask import Flask, render_template, request
import yaml
import os
import sys

# Determine base directory (for config/logs) and template_folder (for flask)
if getattr(sys, 'frozen', False):
    # Running as a bundle.
    # base_dir is the directory of the executable, used for config/logs
    base_dir = os.path.dirname(sys.executable)
    # template_folder is in the temporary _MEIPASS directory where bundled files are
    template_folder = os.path.join(sys._MEIPASS, 'templates')
else:
    # Running as a .py script.
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_folder = os.path.join(base_dir, 'templates')

app = Flask(__name__, template_folder=template_folder)

def get_log_colors():
    return {
        'INFO': 'lightgray',
        'WARNING': 'orange',
        'ERROR': 'red',
        'DEBUG': 'lightblue',
        'CRITICAL': 'magenta'
    }

@app.route('/')
def index():
    config_path = os.path.join(base_dir, 'config.yaml')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        if not config:
            config = {}
    except (IOError, yaml.YAMLError):
        config = {}

    log_directory = config.get('paths', {}).get('log_file', base_dir)
    # Get the directory part from the log_file path
    if log_directory != base_dir:
        log_directory = os.path.dirname(log_directory)

    # If the configured directory is a relative path, make it absolute based on the base_dir
    if not os.path.isabs(log_directory):
        log_directory = os.path.join(base_dir, log_directory)

    log_files = []
    if os.path.isdir(log_directory):
        log_files = [f for f in os.listdir(log_directory) if f.endswith('.log')]

    selected_file = request.args.get('file')
    logs = []
    if selected_file and selected_file in log_files:
        log_file_path = os.path.join(log_directory, selected_file)
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                logs = f.readlines()
        except Exception as e:
            logs = [f"Error reading file: {e}"]

    log_colors = get_log_colors()
    
    return render_template('index.html', logs=logs, log_colors=log_colors, log_files=log_files, selected_file=selected_file)

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)
