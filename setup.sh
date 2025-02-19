#!/bin/bash
# run.sh
# A shell script to setup Firefox path, activate the virtual environment,
# and run the main Python script.

# Activate the virtual environment
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Error: Virtual environment 'venv' not found."
    exit 1
fi

# Uncomment and modify the line below if you need to pass a profile flag manually
# export FIREFOX_ARGS="-P your_profile_name"

# Run the main Python script
python src/main.py