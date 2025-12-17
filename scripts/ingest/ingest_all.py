import subprocess
import sys

SCRIPTS = [
    "/scripts/ingest/ingest_faq.py",
    "/scripts/ingest/ingest_contacts.py",
    "/scripts/ingest/ingest_procedures.py",
]

def run(path: str):
    print(f"\n=== Running {path} ===")
    subprocess.check_call([sys.executable, path])

def main():
    for s in SCRIPTS:
        run(s)
    print("\n[OK] All ingestions done.")

if __name__ == "__main__":
    main()
