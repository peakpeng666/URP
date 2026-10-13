#!/bin/bash
#
# Copyright (c) 2025
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


source .env

#####################################################################################
#################                      Config                       #################
#####################################################################################

# At which population the ideas are integrated
IDEAS_ITERATION_START=1
# At which population of old experiment will be started
CONTINUE_TARGET_POP=10

# Folder with CEoH Experiments, already done
# Adding the Ideas to the process, starting with the
# Target Population
GOAL_FOLDER="$PWD/idea_selection"

if [ ! -d "$GOAL_FOLDER" ]; then
  echo "GOAL Folder for LitCEoH created..."
  echo "Please insert your ceoh experiment, to reevaluate with literature ideas!"
  echo "Please place the experiment folder into $GOAL_FOLDER"
  mkdir $GOAL_FOLDER
  exit 0
fi

if [ -z "$( ls -A $GOAL_FOLDER )" ]; then
  echo "GOAL Folder for LitCEoH empty..."
  echo "Please place the experiment folder into $GOAL_FOLDER"
  exit 0
fi

#####################################################################################
#####################################################################################
#####################################################################################

echo "Data path:"
echo $INSTANCES_PATH
echo $BASE_PATH

if [ -z "${INSTANCES_PATH}" ]; then
    echo "INSTANCES_PATH for funsearch and eoh not set."
    echo "Please create a .env file and add this variable"
    echo "For more information, please look into the readme"
    sleep 10
    exit 1
fi


if [ -z "${BASE_PATH}" ]; then
    echo "BASE_PATH for evaluation not set."
    echo "Please create a .env file and add this variable"
    echo "For more information, please look into the readme"
    sleep 10
    exit 1
fi

#####################################################################################
#################                 General Settings                  #################
#####################################################################################

export PYTHONUNBUFFERED=False
export TIMEOUT=120 # [s] timout for every request thread
export LOGGING=False
export DETAILED_OUTPUT=False # Show all code and explanations

#####################################################################################
#################              Build Process and Execute            #################
#####################################################################################

pip install . -q

echo ""

# Define the target folder
IDEAS_FOLDER="$PWD/ideas"

if [ ! -d "$IDEAS_FOLDER" ]; then
  mkdir $IDEAS_FOLDER
fi

OUTPUT_PATH="$IDEAS_FOLDER/new_heuristics_with_ideas"

if [ ! -d "$OUTPUT_PATH" ]; then
  mkdir $OUTPUT_PATH
fi

# Iterate over each subdirectory in GOAL_FOLDER
for folder in "$GOAL_FOLDER"/*/; do
    if [ -d "$folder" ]; then
        echo "Processing folder: $folder"
        ceoh run "$EOH_PROBLEM" --model_name "$MODEL_NAME" --ideas_iteration_start $IDEAS_ITERATION_START --continue_target_folder $folder --continue_target_pop $CONTINUE_TARGET_POP
    fi
done
