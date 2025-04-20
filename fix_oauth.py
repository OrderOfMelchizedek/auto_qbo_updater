#!/usr/bin/env python
"""
Script to fix OAuth library installation in fom_qbo environment.
"""
import os
import sys
import subprocess
import shutil

def fix_oauth_library():
    """
    Fix the OAuth library installation by removing problematic files
    and reinstalling properly.
    """
    print("Fixing OAuth library installation...")
    
    # Check if we're in the correct virtual environment
    if 'fom_qbo' not in sys.prefix:
        print("WARNING: This script should be run in the fom_qbo virtual environment.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Aborting.")
            return
    
    # 1. Find problematic files
    site_packages = os.path.join(sys.prefix, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages')
    pth_file = os.path.join(site_packages, 'intuit_oauth-1.2.6-nspkg.pth')
    dist_info = os.path.join(site_packages, 'intuit_oauth-1.2.6.dist-info')
    
    # 2. Remove problematic files
    if os.path.exists(pth_file):
        print(f"Removing {pth_file}...")
        os.remove(pth_file)
    
    if os.path.exists(dist_info):
        print(f"Removing {dist_info}...")
        shutil.rmtree(dist_info)
    
    # 3. Uninstall any existing OAuth library with pip
    print("Uninstalling any existing OAuth library...")
    subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', 'intuit-oauth'])
    
    # 4. Update the setup.py file in vendor directory
    setup_py_path = os.path.join(os.getcwd(), 'vendor', 'oauth-pythonclient-master', 'setup.py')
    if os.path.exists(setup_py_path):
        print(f"Updating {setup_py_path}...")
        with open(setup_py_path, 'r') as f:
            setup_py_content = f.read()
        
        # Comment out namespace_packages if it exists
        if 'namespace_packages=(' in setup_py_content:
            setup_py_content = setup_py_content.replace(
                'namespace_packages=(\'intuitlib\',)', 
                '# Comment out namespace_packages to avoid Python 3.13 warnings\n    # namespace_packages=(\'intuitlib\',)'
            )
            
            with open(setup_py_path, 'w') as f:
                f.write(setup_py_content)
    
    # 5. Install the OAuth library from vendor directory
    oauth_lib_path = os.path.join(os.getcwd(), 'vendor', 'oauth-pythonclient-master')
    if os.path.exists(oauth_lib_path):
        print(f"Installing OAuth library from {oauth_lib_path}...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', oauth_lib_path])
    else:
        print(f"Error: OAuth library not found at {oauth_lib_path}")
        return
    
    print("OAuth library installation fixed successfully!")

if __name__ == '__main__':
    fix_oauth_library()