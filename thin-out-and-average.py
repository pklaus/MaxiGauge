#!/usr/bin/env python2.7

import argparse
parser = argparse.ArgumentParser(description='Thin out data files')
parser.add_argument("-n", help="aggregate data and print every nth line", type=int, default=30)
parser.add_argument("filename", help="File to thin out")
args = parser.parse_args()

try:
    f = open(args.filename)
except:
    import sys
    sys.exit(1)

import csv
log = csv.reader(f)

# Get the 1st line, assuming it contains the column titles
fieldnames = log.next()
print ','.join(fieldnames)

import operator
import math
last_time = 0L
store = []
for row in log:
    if len(row) != len(fieldnames): continue
    this_time = long(row[0])
    if this_time > last_time + 1 or this_time <= last_time:
        store = []
    store.append([this_time] + [float(val) if not val.strip() == '' else float('nan') for val in row[1:]])
    if len(store) % args.n == 0:
        tstore = zip(*store) # transpose store
        tstore = tstore[1:] # remove first element
        avgs = [(sum(vals)/args.n) for vals in tstore]
        print "%d, " % store[args.n/2][0], ', '.join('%.3E' % avg if not math.isnan(avg) else '' for avg in avgs)
        store = []
    last_time = this_time
