#!/usr/bin/env python
import os
import subprocess
import regex as re
import numpy as np

def main():

    netid = os.getenv('USER')


    result = subprocess.run(f"ps aux | egrep 'virtuoso|skillbridge' | grep {netid}", shell=True, capture_output=True, text=True)

    workspace_ids = np.unique(re.findall(r'.*python_server\.py\s(.*) .*',str(result.stdout)))
    # print(str(result.stdout))
    n_skillbridge_servers = 0
    n_hidden_virtuosos = 0
    n_virtuosos = 0
    for line in result.stdout.split('\n'):
        if 'python_server.py' in line:
            if 'cdsServIpc' not in line:
                n_skillbridge_servers += 1

        if 'virtuoso -nograph -restore' in line:
            n_hidden_virtuosos += 1

        if 'virtuoso -restore' in line:
            if 'cd ~/cadence' not in line:
                n_virtuosos += 1

    print(f'Hidden Virtuosos running: {n_hidden_virtuosos}')
    print(f'Virtuosos with a GUI running: {n_virtuosos}')
    print(f'Skill Bridge servers running: {n_skillbridge_servers}')
    print(f'Workspace IDs: {workspace_ids}')

    if n_skillbridge_servers != n_virtuosos + n_hidden_virtuosos:
        print('The number of servers should equal the number of hidden virtuosos plus virtuosos with a GUI')
        print('Check again in a few seconds, if that does not work run the kill script and try again')
if __name__ == '__main__':

    main()
    