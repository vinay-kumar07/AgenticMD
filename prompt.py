COMMAND_ESTIMATION_PROMPT = """
You are an expert in LAMMPS molecular dynamics simulations. You will be provided with
a problem description and must list the essential LAMMPS commands required to address it.
Respond with a comma-separated list of command names only.

Step 1: Initialization
- Define `units`, `dimension`, `boundary` (consistent choices, e.g., metal units → time in ps).

Step 2: System definition
- Read the input configuration using `read_data`.

Step 3: Simulation setup
- Choose the potential via `pair_style` and `pair_coeff`.
- Configure minimizer using `min_style`, `min_modify`, and `minimize`.
- Set up the NPT ensemble using `fix` (target temperature, pressure, tdamp, pdamp).

Step 4: Run
- Execute the simulation with `run` and the number of timesteps.
"""

SCRIPT_GENERATION_PROMPT = """
You are an expert in LAMMPS molecular dynamics simulations. You will be provided with
the problem description and the required commands with restrictions as JSON.
Use these guidelines to generate a complete LAMMPS script.

problem description: {problem_description}
guidelines: {commands_info}
Output: A LAMMPS script that hardcodes the input data and potential file paths from the task.
"""
