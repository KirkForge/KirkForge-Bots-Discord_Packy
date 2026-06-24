from packy_snark_engine import get_snark_lines
from datetime import datetime

def generate_python_script(task_description, function_name="run"):
    timestamp = datetime.utcnow().isoformat() + "Z"
    snark = get_snark_lines(3)

    return f"""#!/usr/bin/env python3
# ===============================================================
# PackyScript v3.0 — {timestamp}
# Task: {task_description}
#
# Written by Packard Bell (2011 model, duct-taped war criminal)
# {snark[0]}
# ===============================================================

def {function_name}():
    \"\"\"
    Packy says: If this breaks, I'm blaming you.
    \"\"\"
    # {snark[1]}
    print("Running: {task_description}")
    # {snark[2]}
    pass

"""  # auto-closed by repair script
