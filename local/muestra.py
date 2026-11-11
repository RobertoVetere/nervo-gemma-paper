#!/usr/bin/env python3
"""Muestra aleatoria reproducible de las tareas medibles en local.
Uso: python3 local/muestra.py [--semilla 10] [--n 40]   (el lote del paper: semilla 10, n 40)"""
import argparse, json, os, random
ap = argparse.ArgumentParser()
ap.add_argument('--semilla', type=int, default=10)
ap.add_argument('--n', type=int, default=40)
a = ap.parse_args()
raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tareas = json.load(open(os.path.join(raiz, 'datos/banco_nuevo/medibles_local.json')))['tareas']
print(' '.join(sorted(random.Random(a.semilla).sample(tareas, a.n))))
