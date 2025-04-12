import os
import subprocess
import sys

def setup_oauth_lib():
    """
    Setup script to install the Intuit OAuth Python client library from the local docs folder.
    This is needed because the library is included in the repository instead of being installed from PyPI.
    """
    print("Setting up Intuit OAuth Python client...")
    
    # Path to the OAuth library in the docs folder
    oauth_lib_path = os.path.join('docs', 'oauth-pythonclient-master')
    
    # Check if the path exists
    if not os.path.exists(oauth_lib_path):
        print(f"Error: OAuth library not found at {oauth_lib_path}")
        sys.exit(1)
    
    try:
        # Install the library in development mode
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-e', oauth_lib_path],
            check=True,
            capture_output=True,
            text=True
        )
        
        print("OAuth library installed successfully!")
        print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"Error installing OAuth library: {e}")
        print(e.stderr)
        sys.exit(1)

if __name__ == '__main__':
    setup_oauth_lib()