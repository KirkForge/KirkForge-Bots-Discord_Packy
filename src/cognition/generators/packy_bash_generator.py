from packy_snark_engine import get_snark_lines
from datetime import datetime

def generate_bash_script(task_description):
    timestamp = datetime.utcnow().isoformat() + "Z"
    snark = get_snark_lines(3)

    return f"""#!/bin/bash
# -------------------------------------------------------------
# PackyScript (Bash Edition) — {timestamp}
# Task: {task_description}
#
# {snark[0]}
# {snark[1]}
# -------------------------------------------------------------

echo "Running task: {task_description}"
# {snark[2]}

# (Insert your poorly written commands below)
"""

