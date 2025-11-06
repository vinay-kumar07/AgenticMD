"""
COMPONENTS
1. LAMMPS and NIST RAG
2. Estimate the commands to solve the problem
3. Fetch the relevant information from LAMMPS RAG and appropriate interatomic potential from
4. Prompt LLM to generate the LAMMPS script
"""

import json
import os
from typing import Dict, Any, List
from tools import Tools
import datetime

if __name__ == "__main__":
    for element in ["Al", "Cu", "Fe", "Ni", "SiC"]:
        log_file_name = f'logs/app__{element}_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log'

        with open(log_file_name, 'a') as log_file:
            user_request = f"You are a Molecular Simulation expert trying to perform an NPT " \
                            f"ensemble for {element} using LAMMPS. The following steps will be " \
                            f"taken in the order 1. Read initial configuration of atoms from input.dat file. " \
                            f"2. Choose an appropriate interatomic potential. 3. Perform Energy Minimisation using " \
                            f"an appropriate energy minimiser and bring the atom configuration to a stable equilibrium. " \
                            f"4. Perform NPT ensemble to get a stress-free atom configuration."
            
            tools = Tools()
            # 1. Estimate Commands
            commands = tools.command_estimator(user_request, log_file)

            # 2. Fetch LAMMPS Command Info
            commands_info = tools.command_info_retriever(commands, log_file)

            # 3. Script Generation
            script = tools.script_generator(user_request,commands_info, log_file)
            if not os.path.exists(f'generated_scripts/{element}'):
                os.mkdir(f'generated_scripts/{element}')
            with open(f'generated_scripts/{element}/npt_ensemble_{element}.in', 'w') as script_file:
                script_file.write(script)
