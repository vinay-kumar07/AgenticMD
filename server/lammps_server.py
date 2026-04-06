from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)


@app.post("/run_lammps")
def run_lammps():
    body = request.get_json()
    if not body:
        return jsonify({"error": "JSON body required"}), 400

    work_dir = body.get("work_dir", "").strip()
    script   = body.get("script", "").strip()   # filename only, e.g. "script_attempt1.in"

    if not work_dir or not script:
        return jsonify({"error": "work_dir and script are required"}), 400
    if not os.path.isdir(work_dir):
        return jsonify({"error": f"work_dir does not exist: {work_dir}"}), 400
    if not os.path.isfile(os.path.join(work_dir, script)):
        return jsonify({"error": f"script not found in work_dir: {script}"}), 400

    try:
        result = subprocess.run(
            ["lmp_mpi", "-in", script],
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=420,
        )
        return jsonify({
            "work_dir":   work_dir,
            "stdout":     result.stdout,
            "stderr":     result.stderr,
            "returncode": result.returncode,
        }), 200
    except subprocess.TimeoutExpired:
        return jsonify({"error": "LAMMPS run timed out"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(port=8000)
