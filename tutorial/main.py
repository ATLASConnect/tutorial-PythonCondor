import argparse
import os
import time

from ROOT import TFile
import pickle
import numpy as np
import root_numpy as rnp
from operator import add

parser = argparse.ArgumentParser(description='Process TTbar events for Level 1 Trigger.')
parser.add_argument('-p', '--process', type=int, required=False, dest='process_num', help='a process number for tagging files', default=0)
parser.add_argument('-f', '--file',    type=str, required=True,  dest='filename',    help='a filename to read in')
parser.add_argument('-s', '--start',   type=int, required=True,  dest='event_start', help='start index of event')
parser.add_argument('-n', '--num',     type=int, required=True,  dest='num_events',  help='number of events to process')
parser.add_argument('-t', '--step',    type=int, required=False, dest='step_size',   help='chunking of events', default=10)

# parse the arguments, throw errors if missing any
args = parser.parse_args()

# define the TDirectory to look in [f->ls() shows this]
directory = 'TTbar_14TeV_MU80'
#   and the tree
tree = 'mytree'

# getting 5 branches, but we're only going to make a histogram of the E
branches = ['jet_AntiKt10LCTopo_%s' % col for col in ['E', 'pt', 'm', 'eta', 'phi']]

# set up bins for the histogram (10 GeV bins)
bins = np.arange(0.,2010.,10.)
# initialize to zero, since we're going to accumulate when we loop over
hist_data = np.zeros(len(bins)-1).astype(float)

# open up the file and grab the tree
f = TFile.Open(args.filename)
t = f.Get('%s/%s' % (directory,tree))

startTime_wall      = time.time()
startTime_processor = time.clock()

for event_num in xrange(args.event_start, args.event_start+args.num_events, args.step_size):
  data = rnp.tree2rec(t, branches=branches, start=(event_num), stop=(event_num+args.step_size))
  # grab 0th element since there's only one event
  for energies in data['jet_AntiKt10LCTopo_E']/1000.:
    # accumulate, np.histogram's first argument is the histogram data
    hist_data = map(add, hist_data, np.histogram(energies, bins=bins)[0] )

endTime_wall      = time.time()
endTime_processor = time.clock()
print "Finished job %d in:\n\t Wall time: %0.2f s \n\t Clock Time: %0.2f s" % (args.process_num, (endTime_wall - startTime_wall), (endTime_processor - startTime_processor))

# dump results into file uniquely named by the process number of Condor job
pickle.dump({'hist': hist_data, 'bins': bins}, file('hist_jet_AntiKt10LCTopo_E_%d.pkl' % args.process_num, 'w+') )
