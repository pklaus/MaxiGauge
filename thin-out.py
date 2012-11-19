#!/usr/bin/env python2

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

i = 0
for row in log:
    if len(row) != len(fieldnames): continue
    if i % args.n == 0:
        print ','.join(row)
    i += 1
