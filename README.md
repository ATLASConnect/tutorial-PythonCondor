tutorial-PythonCondor
=====================

A tutorial focused on running a python job on Condor using NumPy, SciPy, Matplotlib, and a custom user package.

# Running Python on Condor

## Introduction
For the purposes of the setup, we will be using

 * `python-2.7`
 * `5.34.18-x86_64-slc6-gcc4.7`
 
These are the last known good installations that work together. One might be able to use `asetup 17.8.0,here` but the current issue is that the header points to A-FS, which doesn't exist!, instead of CVM-FS!

We will also be working from `connect.usatlas.org` and the machines involved should be **SLC6** (Scientific Linux CERN-variant, version 6). It may be possible to run on SLC5, but we're moving forward and this won't cover any issues arising with different versions.

The other assumption is that you don't have `easy_install` or `pip` so we shall document obtaining it and setting it up correctly. I will use a package manager to install a few packages:

 * [numpy](http://www.numpy.org/numpy)
 * [root\_numpy](http://rootpy.github.io/root_numpy/root_numpy)

to play around with ROOT files. I picked these two because they are a good example of packages that depend on compilers for the machine you're on as well as a package that requires PyROOT bindings.

### Brief Outline
 * set up your environment on `connect`
 * grab and setup a python package manager (e.g. `easy_install` or `pip` )
    * This is a one time thing, once you have this set up, you can always refer back to this tutorial on how to set up a new Condor job skipping the `pip` and `easy_install` portions
 * install python packages you want
 * setup a Condor job:
    * using a `main.sh` shell script to wrap around your python script(s)
    * turning on input file transfers (your python script(s) and your packages)
    * running multiple jobs and passing in arguments
    * automatically transferring output
 * wrapping up the tutorial by plotting the results in a final image

## Setting up the Environment
Set up ROOT
```bash
localSetupROOT 5.34.18-x86_64-slc6-gcc4.7
```

Verify that ROOT and Python are setup with correct versions:
```bash
connect $: which root
    /cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase/x86_64/root/5.34.18-x86_64-slc6-gcc4.7/bin/root
  
connect $: python --version
    Python 2.7.3
```

## Setting up `easy_install` and `pip`
Next, you would probably always want to have `easy_install` available for future projects so this will install it locally in persistence.
```bash
connect $: wget https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py -O - | python - --user
```

You should only download the code securely (via SSL). The second half executes the setup script and installs it in `$HOME/.local/`. Verify this by
```bash
connect $: ls -la $HOME/.local
    total 4
    drwxr-xr-x  4 kratsg users   &nbsp;&nbsp;&nbsp;38 Mar 28 15:17 .
    drwxr-xr-x 11 kratsg users 4096 Mar 28 17:26 ..
    drwxr-xr-x  2 kratsg users   &nbsp;&nbsp;&nbsp;75 Mar 28 15:25 bin
    drwxr-xr-x  3 kratsg users   &nbsp;&nbsp;&nbsp;30 Mar 28 15:28 lib
```

### Update environment paths
I use my `.bash_profile` here: 
```bash
echo 'export PATH=$HOME/.local/bin:$HOME/.local:$PATH' >> $HOME/.bash_profile
```

You can manually add the following line to the file instead
```bash
export PATH=$HOME/.local/bin:$HOME/.local:$PATH
```

After that, source the file so that your environments are updated
```bash
source ~/.bash_profile
```

Verify this worked correctly by checking to see where `easy_install` is located
```bash
connect $: which easy_install
  ~/.local/bin/easy_install
```

### Update `easy_install` to point to correct python binary
This will do it for us: 
```bash
perl -pi -e 's/\#\!.*/\#\!\/usr\/bin\/env python/g if $. == 1' `which easy_install`
```

What this does is takes the file (looks something like this)

```shell
#!/afs/cern.ch/sw/lcg/external/Python/2.7.3/x86_64-slc6-gcc47-opt/bin/python
# EASY-INSTALL-ENTRY-SCRIPT: 'setuptools==3.3','console_scripts','easy_install'
__requires__ = 'setuptools==3.3'
import sys
from pkg_resources import load_entry_point

if __name__ == '__main__':
    sys.exit(
        load_entry_point('setuptools==3.3', 'console_scripts', 'easy_install')()
```

and changes the first line to
```shell
#!/usr/bin/env python
# EASY-INSTALL-ENTRY-SCRIPT: 'setuptools==3.3','console_scripts','easy_install'
__requires__ = 'setuptools==3.3'
import sys
from pkg_resources import load_entry_point

if __name__ == '__main__':
    sys.exit(
        load_entry_point('setuptools==3.3', 'console_scripts', 'easy_install')()
```

Now, test that `easy_install` is working - simply run

```bash
connect $: easy_install
    error: No urls, filenames, or requirements specified (see --help)
```

If you're seeing this (and not an `ImportError` that means it was able to execute initial python code without any issues!

### Install `pip` locally
This is a quick two-liner.

1. Install `pip`: `easy_install --prefix=$HOME/.local/ pip`
1. Update `pip`'s headers to point to the right python: 
    ```bash
    perl -pi -e 's/\#\!.*/\#\!\/usr\/bin\/env python/g if $. == 1' `which pip`
    ```

You can verify that this works by running `pip` and seeing the usage menu display.

## Installing Python packages to transfer to Condor (for a job)
At this point, you've set up your environment so that `easy_install` is local for `python-2.7`. Now, we can install our packages elsewhere locally, as long as Python knows where to find them. You can choose to use `easy_install` or `pip` at this point. I'll demonstrate code that uses either one to install python packages to a local directory that you create specifically for a condor job.

Let's call the folder `CondorPythonLocal` for which we place all relevant python packages.

1. Build the base directory structure for installing packages. 
    ```bash
    mkdir -p $HOME/CondorPythonLocal/lib/python2.7/site-packages
    ```
    The `-p` flag will recursively make parent directories as needed (http://explainshell.com/explain?cmd=mkdir+-p).

1. Update `$PYTHONPATH` so python can find your files via 
    ```bash
    export PYTHONPATH=$HOME/CondorPythonLocal/lib/python2.7/site-packages:$PYTHONPATH
    ```
    This is only for the current shell.
 
1. Export some variables, [see scipy docs](http://docs.scipy.org/doc/numpy/user/install.html#disabling-atlas-and-other-accelerated-libraries) (this is numpy specific!) so that you're not compiling using external libraries that may not be on the Condor nodes you are flocking to. 
    ```bash
    export BLAS=None LAPACK=None ATLAS=None
    ```
 
1. Install the packages (`numpy`, then `root_numpy`) using

    1. `easy_install`
        * `easy_install --prefix=$HOME/CondorPythonLocal numpy`
        * `easy_install --prefix=$HOME/CondorPythonLocal root_numpy`
    1. `pip`
        * `pip install --install-option="--prefix=~/CondorPythonLocal" --ignore-installed numpy`
        * `pip install --install-option="--prefix=~/CondorPythonLocal" --ignore-installed root_numpy`
     
    Note that you need to specify an absolute path for `--install-option` here. See the [pip](http://pip.readthedocs.org/en/latest/reference/pip_install.html?highlight=install%20option#cmdoption--install-option) docs for more information. In my case: `$HOME = /home/kratsg`.

We can use the PEP350 recommendations to specify the `prefix` on where to install python packages by `prefix=$HOME/folder/for/python/packages`. Unlike `pip`, `easy_install` has no `--ignore-installed` flag which allows you to ignore any python packages that may already be installed locally or globally (locally inside `$HOME/.local` for example). This is a particular reason why I would recommend `pip`.

**Warning**: please make sure that these packages don't already exist inside `$HOME/.local` because otherwise, python will import those over some other local package directory you set up.

You can check these installations after by locally importing to make sure things are fine:

```bash
connect $: python
  Python 2.7.3 (default, Oct 25 2012, 12:19:07)
  [GCC 4.7.2] on linux2
  Type "help", "copyright", "credits" or "license" for more information.
  >>> import numpy
  >>> numpy.__file__
  '/home/kratsg/CondorPythonLocal/lib/python2.7/site-packages/numpy/__init__.pyc'
  >>> import root_numpy
  >>> root_numpy.__file__
  '/home/kratsg/CondorPythonLocal/lib/python2.7/site-packages/root_numpy/__init__.pyc'
```

and you're good to go. Notice that the paths refer to your `CondorPythonLocal` prefix that you've installed the packages to. At this point, you should be able to see that we can copy the `CondorPythonLocal` library over to a node, set up the environment, and set up our `$PYTHONPATH` variable to point to the libraries. This is the basic idea. Future condor jobs can take advantage of the fact that you can set up new folders with similar directory structure and install other packages you might want to use!

# Actually running a Condor job (use case)
In order to make this as painless as possible, I'll document a use case that I needed to use Condor for -- I describe this below. The file we're looking at has 10,000 events which I've placed on faxbox [here](http://faxbox.usatlas.org/user/kratsg/CondorPythonTest/). We can access this by `root://faxbox.usatlas.org//user/kratsg/CondorPythonTest/PileupSkim_TTbar_14TeV_MU80.root`

I'll have python process it event-by-event up to 1000 events, starting from the nth event. After that I write the results to an output file on that node which then gets transferred back to my machine when the job is finished. In order to make sure filenames don't conflict, I use the process number which will be unique. This use case involves `numpy` and `root_numpy` which I've compiled locally using the above instructions.

## The Files

### The Condor `config` file
The Condor manual is [here](http://research.cs.wisc.edu/htcondor/manual/v8.0/condor-V8_0_6-Manual.pdf). 

Code for `$HOME/tutorial/config.sh`:

```bash
# The UNIVERSE defines an execution environment. You will almost always use VANILLA. 
Universe = vanilla
# EXECUTABLE is the program your job will run It's often useful
# to create a shell script to "wrap" your actual work.
Executable = main.sh

# requirements
Requirements = OpSysAndVer =?= "SL6"

# ERROR and OUTPUT are the error and output channels from your job
# that HTCondor returns from the remote host.
Error = error/job.$(Process)
Output = out/job.$(Process)

# The LOG file is where HTCondor places information about your
# job's status, success, and resource consumption.
Log = log/job.$(Process)

# +ProjectName is the name of the project reported to the OSG accounting system
+ProjectName="atlas-org-uchicago"

should_transfer_files = YES
when_to_transfer_output = ON_Exit
transfer_output         = True
transfer_input_files    = home/kratsg/CondorPythonLocal, main.py
# transfer_output_files   = hist_jet_AntiKt10LCTopo_E_$(Process).pkl

# QUEUE is the "start button" - it launches any jobs that have been 
# specified thus far.

Arguments = $(Process) root://faxbox.usatlas.org//user/kratsg/CondorPythonTest/PileupSkim_TTbar_14TeV_MU80.root 0 1000
Queue 1

Arguments = $(Process) root://faxbox.usatlas.org//user/kratsg/CondorPythonTest/PileupSkim_TTbar_14TeV_MU80.root 1000 1000
Queue 1

Arguments = $(Process) root://faxbox.usatlas.org//user/kratsg/CondorPythonTest/PileupSkim_TTbar_14TeV_MU80.root 2000 1000
Queue 1

Arguments = $(Process) root://faxbox.usatlas.org//user/kratsg/CondorPythonTest/PileupSkim_TTbar_14TeV_MU80.root 3000 1000
Queue 1

Arguments = $(Process) root://faxbox.usatlas.org//user/kratsg/CondorPythonTest/PileupSkim_TTbar_14TeV_MU80.root 4000 1000
Queue 1

Arguments = $(Process) root://faxbox.usatlas.org//user/kratsg/CondorPythonTest/PileupSkim_TTbar_14TeV_MU80.root 5000 1000
Queue 1

Arguments = $(Process) root://faxbox.usatlas.org//user/kratsg/CondorPythonTest/PileupSkim_TTbar_14TeV_MU80.root 6000 1000
Queue 1

Arguments = $(Process) root://faxbox.usatlas.org//user/kratsg/CondorPythonTest/PileupSkim_TTbar_14TeV_MU80.root 7000 1000
Queue 1

Arguments = $(Process) root://faxbox.usatlas.org//user/kratsg/CondorPythonTest/PileupSkim_TTbar_14TeV_MU80.root 8000 1000
Queue 1

Arguments = $(Process) root://faxbox.usatlas.org//user/kratsg/CondorPythonTest/PileupSkim_TTbar_14TeV_MU80.root 9000 1000
Queue 1
```

Notice that I have 10 processes, one for every 1000 events in the file. The arguments I use here are specified in my Python file below (file, starting event, number of events to process). Some key features about what I've placed above:

   * `should_transfer_files` is what turns on Condor's file mechanisms.
   * `transfer_out` lets Condor know that you want to transfer output files back to the submitting machine (e.g. Connect). It can do this automatically.
   * `transfer_input_files` we tell Condor which input files we want to transfer -- in this case, the local Python packages `CondorPythonLocal` and `main.py` (see below for this file)
   * `transfer_output_files` should not necessarily be needed. In some cases, according to Condor's manual, you submit GRID jobs - Condor will not automatically look for new files you've created to transfer over, so you should most likely specify this if you aren't sure or if the file isn't being found automatically. I've commented out an example of how you might transfer files generated with a variable `$(Process)` in the filename.

And again, I'll repeat, the Condor manual is [here](http://research.cs.wisc.edu/htcondor/manual/v8.0/condor-V8_0_6-Manual.pdf).  

### The main script file
This is the script file that gets executed by the Condor `config` file.

Code for `$HOME/tutorial/main.sh`:
```bash
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
```

Screw code highlighting. Let's just explain some of what's going on here.

* We export some variables `HOME` and `PROOFANADIR` which is just for organization and consistency.
    ```bash
    #NEEDED
    export HOME=$(pwd)
    export PROOFANADIR=$(pwd)
    ```

* We export **ALRB** (ATLAS Local ROOT Base) and locally set up the version of ROOT we want (see [introduction](#introduction)).
    ```bash
    #ROOT STUFF
    export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
    source $ATLAS_LOCAL_ROOT_BASE/user/atlasLocalSetup.sh
    localSetupROOT 5.34.18-x86_64-slc6-gcc4.7 --skipConfirm
    ```

* We add the python package folder we transferred over using the `config` file into our python path. **You must always do this after you set up ROOT so that it searches your local package first!**
    ```bash
    export PYTHONPATH=$HOME/CondorPythonLocal/lib/python2.7/site-packages:$PYTHONPATH
    ```

* We just print some information about when the job starts, runs, the directory, to make it easier for tracking issues later... and then we pass along the arguments into the python file. 
    ```bash
    printf "Start time: "; /bin/date
    printf "Job is running on node: "; /bin/hostname
    printf "Job running as user: "; /usr/bin/id
    printf "Job is running in directory: "; /bin/pwd
    #
    python main.py -p ${1} -f ${2} -s ${3} -n ${4}
    ```

    * `${1}` is the process
    * `${2}` is the filename
    * `${3}` is the start event
    * `${4}` is the number of events to read


See `config` above for more information about how the arguments were passed.

### The python code
This is the main piece of the script that will use the `numpy` and `root_numpy` packages we installed to generate histograms of the data [this is a super simple example - obviously, you can do more than this and even use multiple files!]


Code for `$HOME/tutorial/main.py`:
```python
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
parser.add_argument('-f', '--file',  type=str, required=True, dest='filename',    help='a filename to read in')
parser.add_argument('-s', '--start', type=int, required=True, dest='event_start', help='start index of event')
parser.add_argument('-n', '--num',   type=int, required=True, dest='num_events',  help='number of events to process')
parser.add_argument('-t', '--step',    type=int, required=False, dest='step_size',   help='chunking of events', default=10)

# parse the arguments, throw errors if missing any
args = parser.parse_args()

# define the TDirectory to look in [f->ls() shows this]
directory = 'TTbar_14TeV_MU80'
#      and the tree
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
```

There are a lot of things I'm doing in the Python file. Particularly - I set up argument parameters so I can call my python file like
```bash
python main.py -f FILENAME -s START_EVENT -n NUM_EVENTS -p PROCESS
```
and parse those arguments. Afterwards, I set up a loop to loop over each event, one at a time, from `START_EVENT` to `START_EVENT+NUM_EVENTS` to create a histogram of the `AntiKt10LCTopo` jet energies. After I've processed and built up the histogram data, I store it in a file using [pickle](https://wiki.python.org/moin/UsingPickle). That's it.

Yes, I could do more features such as placing in `matplotlib` as well, and having my script build up plots -- but it's much better to process your ROOT files and get it into a format you want, such as running clustering algorithms, specialized filters, etcetera... and then dump this data so you can make displays from it, or apply additional trivial cuts. Most of the time, a large portion of the ROOT file is ignored when we process these things - so you can think of trying to cut down the data and make it smaller and much easier to work with... especially in the cases where you have 500k events and you want to process and make jet clusters, you can often cut your data size from ~80 gigs to ~1 gig processed (an order of magnitude smaller).

I could also have dumped the data into a new ROOT file because [root_numpy](http://rootpy.github.io/root_numpy/) does have this functionality. You can also fill in histograms as well without a problem and merge them (as this is available with ROOT I think). See [root_numpy](http://rootpy.github.io/root_numpy/) for more information and even [rootpy](http://www.rootpy.org/) for more features!

## Flocking the job

Finally, we're all set. Since I have separate directories for my `log`, `output`, and `error` files; you'd probably want to make these first by `mkdir error log out`. Then all that's left to do is submit the job `condor_submit config` which should transfer the python and shell script over.

Some notes: for this particular code -- I find that it is I/O bound. Particularly, there are numerous calls to read the file out (in chunks). A way to speed up is to load up multiple events per loop and add additional processing like that... or just make more jobs! I do have the functionality to add in another argument ==-t== for step size if I want to change from the default of 10. This still works and should be fast enough for most small jobs ( < 1mm events). When I ran it myself with this script - all files took about 100 seconds (approximately 1 minute). It may be slower or faster, etc. But it runs!

## Plotting the results

When I run the above code - I get 10 files returned, each contains pickled data of the histogram entries and the bins. I'll use `matplotlib` to make a plot quite easily. It's always suggested to make plots locally and use Condor to crunch and return data you want to plot, not just making it process and plot. But it's your preference. To do this, I'm going to want to install `matplotlib` locally on Connect to use it, as well as dependencies. I can do this pretty much in one line (install to `$HOME/.local/` ).

```bash
pip install --install-option="--prefix=~/.local" --ignore-installed --no-use-wheel matplotlib
```

or the short-hand `--user` option (PEP350)

```bash
pip install --user --ignore-installed --no-use-wheel matplotlib
```

Strangely, one of the dependencies for `matplotlib` is [six.py](http://pythonhosted.org/six/) which comes in both an `egg` and [wheel](http://wheel.readthedocs.org/en/latest/) format. I have no idea why the `wheel` archive screws this up, but it does. See more `pip install` options [here](http://pip.readthedocs.org/en/latest/reference/pip_install.html#options).

Now, here is the script to plot the results of the Condor job.

Code for `$HOME/tutorial/make_plot.py`:
```python
#don't use an X-Server to render images
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as pl

#helper libraries for the files
import pickle
import glob

#I use this for a map(add) but you could use numpy arrays
from operator import add

files = glob.glob("*.pkl")

bins = []
vals = []

for filename in files:
  with open(filename, "rb") as f:
    data = pickle.load(f)

    #check if vals initialized, otherwise initialize
    if vals:
      vals = map(add, vals, data['hist'])
    else:
      vals = data['hist']
    bins = data['bins']

#computes the width of each bin (this is my magic)
widths = [x - bins[i-1] for i,x in enumerate(bins)][1:]

#set sizes for labels, titles, and figure size (inches and points)
figsize = (16, 12)
labelsize = 28
titlesize = 36

pl.figure(figsize=figsize)
pl.xlabel('offline $E^{\mathrm{jet}}$ [GeV]', fontsize=labelsize)
pl.ylabel('number of offline jets', fontsize=labelsize)
pl.title('Anti-Kt R=1.0 Topo Jet Energy Distribution', fontsize=titlesize)
pl.bar(bins[:-1], vals, width=widths)
pl.grid(True)
pl.savefig('hist_jet_AntiKt10LCTopo_E.png')
pl.close()
```

And simply run `python merge.py` when you're done to generate a png plot from the data. The code merges the output and then makes your plot. You can then simply copy it over to faxbox and view it online `cp hist_jet_AntiKt10LCTopo_E.png $HOME/faxbox/.` at http://faxbox.usatlas.org/user/kratsg/ and you're done (obviously replacing `kratsg` with your username). Here's a plot of the image that results:

![](http://faxbox.usatlas.org/user/kratsg/CondorPythonTest/hist_jet_AntiKt10LCTopo_E.png)

# All Files in the Tutorial

All of the files used in the tutorial can be found [here](http://faxbox.usatlas.org/user/kratsg/CondorPythonTest/). This github contains most of the files, but the larger files are in the faxbox.

# FAQs

## Errors with nested vectors for root_numpy?

That's not a problem. The current release of `root_numpy` at 3.3.0 does have support for nested vectors. Make sure your version is right by something like

```python
>>> import root_numpy
>>> root_numpy.__version__
'3.3.0'
````

If there are other issues with it, please let me know as I implemented that feature.

## Condor job stderror output?

This isn't an issue. You usually get an error output like the following:

```
which: no python in ((null))
```

this seems to be associated with Condor when you execute python. I don't know why it comes up, but it doesn't seem to affect the actual processing of a job.
