#!/usr/bin/env python2

import argparse

import sys

parser = argparse.ArgumentParser(description='Thin out data files')
parser.add_argument("-n", help="aggregate data and print every nth line", type=int, default=30)
parser.add_argument("filename", help="File to thin out")

args = parser.parse_args()

try:
    f = open(args.filename)
except:
    sys.exit(1)

print f.readline().strip()
i = 0
for line in f:
    if i % args.n == 0:
        print line.strip()
    i += 1
