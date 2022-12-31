#!/usr/bin/env python
import os
import subprocess
import sys
import re

def main(args):
    if len(args) == 1:
        n_virtuosos_gui = 1
        n_virtuosos_hidden = 0
    elif len(args) == 3:
        n_virtuosos_gui = int(args[1])
        n_virtuosos_hidden = int(args[2])
    else:
        print('Please provide the number of Viruosos to run (with gui and without gui).')
        print('ie. Launch 1 visible virtuoso with a gui and no hidden ones')
        print('\t./launch_virtuosos_and_skillbridge.py 1 0')
        print('Launching with no arguments will launch a single session with a GUI')
        return

    netid = os.getenv('USER')
    virt_path = args[0]

    n_virtuosos = n_virtuosos_gui + n_virtuosos_hidden
    if n_virtuosos < 1 or n_virtuosos > 10:
        print('limit number of instance between 1 and 10')
        return

    sb_path = subprocess.run(['skillbridge', 'path'], capture_output=True)
    sb_path = re.findall('.*load\((.*)\).*', str(sb_path.stdout))[0]

    print(f'Using {sb_path} as skillbridge path\n')
    
    python_path = str(subprocess.run(['which', 'python'], capture_output=True).stdout)[2:-3]
    python_lib_path = python_path[0:python_path.find('/bin')] + '/lib/python3.10/site-packages/'
    print(python_lib_path)
    if 'Virtuosopy/launch_scripts' not in os.path.abspath(os.curdir):
        print('Error: Please launch this script from launch_scripts folder (cd ./launch_scripts)')
        exit()
    
    launch_files_path = os.path.abspath(os.curdir) + '/skill_launch_files'

    
    subprocess.run(['mkdir', launch_files_path, '-p'])
    subprocess.run(['cp', 'CCSinvokeCdfCallbacks.il', f'{virt_path}/CCSinvokeCdfCallbacks.il'])
    

    # exit()
    for tid in range(n_virtuosos):
        with open(f'{launch_files_path}/start{tid}.il', 'w') as f:
            f.write(f'load({sb_path})\n')
            f.write(f'pyStartServer ?id "{netid}_{tid}" ?python "LD_LIBRARY_PATH= {python_path}"\n')
            f.write('load("./CCSinvokeCdfCallbacks.il")\n')

        if n_virtuosos_gui > 0:
            subprocess.run(f'gnome-terminal -- bash -c "cd {virt_path}; source toolsenv; virtuoso -restore {launch_files_path}/start{tid}.il"', shell=True)
            n_virtuosos_gui -= 1
        elif n_virtuosos_hidden > 0:
            subprocess.run(f'gnome-terminal -- bash -c "cd {virt_path}; source toolsenv; virtuoso -restore -nograph {launch_files_path}/start{tid}.il"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            n_virtuosos_hidden -= 1

        print(f'launched virtuoso with skillbridge with a workspace id: {netid}_{tid}')

if __name__ == '__main__':

    args = sys.argv[1:]
    main(args)
    
    