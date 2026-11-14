"""Start the Antibiotic Quest server.

    python run.py                    # http://127.0.0.1:5000  (this computer only)
    python run.py --host 0.0.0.0     # also reachable from phones/laptops on the same Wi-Fi
    python run.py --port 8000
"""
import argparse
import socket

from app import create_app
from app.db import connect


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()

    app = create_app()
    con = connect(app.config["DATABASE"])
    approved = con.execute("SELECT COUNT(*) FROM playable_questions").fetchone()[0]
    total = con.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    con.close()

    print("\n  Antibiotic Quest")
    print(f"  Game:   http://localhost:{a.port}/")
    print(f"  Admin:  http://localhost:{a.port}/admin")
    if a.host == "0.0.0.0" and lan_ip():
        print(f"  Other devices on this network: http://{lan_ip()}:{a.port}/")
    print(f"  Questions approved: {approved}/{total}")
    if approved == 0:
        print("  ! No question is approved yet, so levels will not start. Approve questions in /admin,")
        print("    or for a quick local test run:  python db/init_db.py --approve-all-demo")
    if app.config["ADMIN_TOKEN"] == "change-me":
        print("  ! Admin token is the default 'change-me'. Set ADMIN_TOKEN in .env before the pilot.")
    print()
    app.run(host=a.host, port=a.port, debug=a.debug)


if __name__ == "__main__":
    main()
