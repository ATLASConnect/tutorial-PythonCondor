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

