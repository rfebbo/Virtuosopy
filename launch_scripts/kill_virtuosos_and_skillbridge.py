#!/usr/bin/env python
import os
import subprocess
import sys

def main():

    netid = os.getenv('USER')
    subprocess.run(f"kill $(ps aux | egrep '(virtuoso -nograph -restore)|(skillbridge/server/python_server.py)|(virtuoso -restore)|(virtuoso -nographE -restore)' | grep {netid} | awk '{{print $2}}')", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(f"rm -rf /tmp/skill-server-{netid}*", shell=True)
    subprocess.run(f"rm -rf /tmp/crashReport*{netid}*", shell=True) # :/

if __name__ == '__main__':

    main()
    