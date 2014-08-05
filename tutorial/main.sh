#!/bin/bash 

#NEEDED
export HOME=$(pwd)
export PROOFANADIR=$(pwd)
#ROOT STUFF
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
source $ATLAS_LOCAL_ROOT_BASE/user/atlasLocalSetup.sh
localSetupROOT 5.34.18-x86_64-slc6-gcc4.7 --skipConfirm

export PYTHONPATH=$HOME/CondorPythonLocal/lib/python2.7/site-packages:$PYTHONPATH

printf "Start time: "; /bin/date 
printf "Job is running on node: "; /bin/hostname 
printf "Job running as user: "; /usr/bin/id 
printf "Job is running in directory: "; /bin/pwd 

python main.py -p ${1} -f ${2} -s ${3} -n ${4}
