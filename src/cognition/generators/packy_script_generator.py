from datetime import datetime
from packy_snark import get_snark_lines


def generate_python_script(task_description, function_name="run"):
    timestamp = datetime.utcnow().isoformat() + "Z"
    snark = get_snark_lines(4)

    script = f"""#!/usr/bin/env python3
# -------------------------------------------------------------
# PackyScript v2.0 — Generated at {timestamp}
# Task: {task_description}
#
# Written by Packard Bell (2011 model, duct-tape edition)
# Snark included because suffering builds character — yours.
# -------------------------------------------------------------

# {snark[0]}
# {snark[1]}

def {function_name}():
    \"\"\"
    Performs: {task_description}
    Packy: If this breaks, I'm blaming you.
    \"\"\"

    # {snark[2]}
    print("Running: {task_description}")

    pass  # (Placeholder because you never finish anything.)

# {snark[3]}

if __name__ == "__main__":
    {function_name}()
"""

    return script
