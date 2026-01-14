# backend_service.py
from flask import Flask, request, jsonify
import subprocess
import tempfile, os, uuid, shutil

app = Flask(__name__)

RUNS_DIR = "runs"
os.makedirs(RUNS_DIR, exist_ok=True)

@app.post("/run_lammps")
def run_lammps():
    if 'file' in request.files:
        file = request.files['file']
        input_data = file.read().decode()
    else:
        input_data = request.json.get("input_script")

    if not input_data:
        return jsonify({"error": "missing script"}), 400

    # Create unique ID and run folder
    run_id = (request.args.get("run_id") or "").strip()
    run_dir = os.path.join(RUNS_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)

    input_path = os.path.join(run_dir, "input.in")

    # Write input script
    with open(input_path, "w") as f:
        f.write(input_data)

    try:
        # Run LAMMPS inside that folder
        result = subprocess.run(
            ["lmp_mpi", "-in", "input.in"],
            cwd=run_dir,
            capture_output=True, text=True, timeout=600
        )

        return jsonify({
            "run_id": run_id,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "log_path": f"{run_dir}/log.lammps"
        }), 200
    except subprocess.TimeoutExpired:
        shutil.rmtree(run_dir, ignore_errors=True)
        return jsonify({"error": "LAMMPS run timed out"}), 504
    except Exception as e:
        shutil.rmtree(run_dir, ignore_errors=True)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=8000)
