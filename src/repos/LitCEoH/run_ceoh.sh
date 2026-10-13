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


./setup.sh

source .env

echo "Data path:"
echo $INSTANCES_PATH
echo $OUTPUT_PATH
echo $BASE_PATH

if [ -z "${INSTANCES_PATH}" ]; then
    echo "INSTANCES_PATH for ceoh and eoh not set."
    echo "Please create a .env file and add this variable"
    echo "For more information, please look into the readme"
    sleep 10
    exit 1
fi

if [ -z "${OUTPUT_PATH}" ]; then
    echo "OUTPUT_PATH for eoh not set."
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


# If empty set standard value.
# Please only change in .env file
if [ -z "${EOH_PROBLEM}" ]
then
  echo "--- NO PROBLEM IS SET - Standard: gemma2:27b"
  echo ""
  # ['tsp_construct','bp_online', 'multibay_reshuffle', 'multibay_reshuffle_pick_drop']
  EOH_PROBLEM="bp_online"
fi

# If empty set standard value.
# Please only change in .env file
if [ -z "${MODEL_NAME}" ]
then
  # ['llama3.1:70b', 'gemma2:27b', 'nemotron:latest' ]
  echo "--- NO MODEL IS SET - Standard: gemma2:27b"
  echo ""
  MODEL_NAME="gpt-4o" # ['llama3.1:70b', 'gemma2:27b', 'nemotron:latest' ]
fi

# If empty set standard value.
# Please only change in .env file
if [ -z "${IDEA_MODEL_NAME}" ]
then
  # ['llama3.1:70b', 'gemma2:27b', 'nemotron:latest' ]
  echo "--- NO IDEA_MODEL_NAME IS SET - Standard: as ceoh model"
  MODEL_NAME=$MODEL_NAME # ['llama3.1:70b', 'gemma2:27b', 'nemotron:latest' ]
fi

# If empty set standard value.
# Please only change in .env file
if [ -z "${DETAILED_OUTPUT}" ]
then
  export DETAILED_OUTPUT=False # Show all code and explanations
fi


#####################################################################################
#################                 General Settings                  #################
#####################################################################################

export PYTHONUNBUFFERED=False
export TIMEOUT=120 # [s] timout for every request thread
export LOGGING=False


#####################################################################################
#################              Build Process and Execute            #################
#####################################################################################

pip install . -q

echo "########################## LLM MODELS AVAILABLE ##########################"
llm models | grep -- "gemma\|llama"

echo ""
echo "-----------------------------------------"
echo "--- EOH Problem: $EOH_PROBLEM"

ceoh run $EOH_PROBLEM --model_name $MODEL_NAME --ideas_iteration_start -1

sleep 1000