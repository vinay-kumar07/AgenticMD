from langchain_core.messages import HumanMessage, SystemMessage

COMMAND_ESTIMATION_PROMPT = "You are an expert in LAMMPS molecular dynamics simulations. You will be provided with a problem description, and your " \
            "task is to identify and list the essential LAMMPS commands required to address the problem effectively. " \
            "Focus on selecting commands that are directly relevant to the tasks outlined in the problem description. " \
            "Provide your response as a concise list of command names without additional explanations or context. " \
            "Input: {problem_description} " \
            "Output: A list of LAMMPS command names." \
            "Example Output: read_data, pair_style, pair_coeff, minimize, fix npt, run" \
            "Problem: Perform an NPT ensemble simulation on a system of Argon atoms at 300K and 1 atm pressure for 100 ps." \
            "Thoughts: To perform an NPT ensemble simulation on Argon atoms, I will need to read the data file containing the initial configuration of the Argon atoms. First thing will be to " \
            "bring the configuration to a minimum energy state. Then, I will set the pair style and coefficients for Argon interactions. Then I will set the velocities to match the starting temperature. Next, I will apply a fix for the NPT ensemble to control temperature and pressure. Finally, I will" \
            "run the simulation for the specified duration." \
            "Commands: ['read_data', 'units', 'atom_style', 'pair_style', 'pair_coeff', 'min_style', 'minimize', 'velocity', 'timestep', 'fix npt', 'run']"


SCRIPT_GENERATION_PROMPT = "You are an expert in LAMMPS molecular dynamics simulations. You will be provided with the problem statement and necessary LAMMPS commands guidelines in form of a json having" \
            "keys command and restriction. Use these guidelines to generate a complete LAMMPS script " \
            "problem description: {problem_description} " \
            "guidelines: {commands_info}" \
            "Output: A LAMMPS script"