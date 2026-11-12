#!/usr/bin/env python3
"""Reproducible random sample of the tasks scorable locally.
Usage: python3 local/sample.py [--seed 10] [--n 40]   (the paper's batch: seed 10, n 40)"""
import argparse, json, os, random
ap = argparse.ArgumentParser()
ap.add_argument('--seed', '--semilla', dest='semilla', type=int, default=10)
ap.add_argument('--n', type=int, default=40)
a = ap.parse_args()
raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tareas = json.load(open(os.path.join(raiz, 'data/new_bench/scorable_local.json')))['tareas']
print(' '.join(sorted(random.Random(a.semilla).sample(tareas, a.n))))
