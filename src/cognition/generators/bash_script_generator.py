from packy_snark import get_snark_lines
from datetime import datetime


def generate_bash_script(task_description):
    timestamp = datetime.utcnow().isoformat() + "Z"
    snark = get_snark_lines(2)

    return f"""#!/bin/bash
# PackyScript (Bash Edition) — {timestamp}
# Task: {task_description}
# {snark[0]}

echo "Running task: {task_description}"
# {snark[1]}

"""  # auto-closed by repair script
