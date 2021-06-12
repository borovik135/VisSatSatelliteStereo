#!/usr/bin/env python
'''2021 (C) Eugene.Borovikov@Kwiver.com: dump PLY point cloud to a text file'''
from lib.ply_np_converter import ply2np, np2ply
import csv
FN = '/data/Danesfield/CORE3D/Jacksonville/VisSatStereo/aggregate_3d.ply'
outFN = '/data/Danesfield/CORE3D/Jacksonville/VisSatStereo/aggregate_3d.tsv'
points, color, comments = ply2np(FN)
with open(outFN, 'w') as f:
    CVW = csv.writer(f, delimiter=' ')
    CVW.writerows(points)
