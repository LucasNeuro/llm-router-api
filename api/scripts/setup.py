import os
import sys
from pathlib import Path

def setup_environment():
    """Setup the Python environment for the project"""
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    
    # Add the project root to PYTHONPATH
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))
        print(f"Added {project_root} to PYTHONPATH")
    
    # Set environment variables
    os.environ["PYTHONPATH"] = str(project_root)
    
    print("Environment setup complete!")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")
    print(f"Python path: {sys.path}")

if __name__ == "__main__":
    setup_environment() 