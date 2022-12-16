"""
@file hough_lines.py
@brief This program demonstrates line finding with the Hough transform
"""
import sys
import math
import time
from pyproj import Geod, geod
import cv2
import cv2 as cv
import numpy as np
from scipy.signal import get_window
from shapely.geometry import Polygon, LineString, MultiPolygon
import geopandas
from door import get_doors
from helpers import draw_contours, get_contours, imshow, approx_lines, draw_polygons, contours_to_lines, draw_lines, \
    imwrite, rects_to_polygons, draw_multi_polygons, line_length
from lines import remove_lines_in_rooms, get_wall_lines, get_wall_lines_polys
from rooms import rooms_polygons, get_rooms, window_rects
from wall import get_wall_width
import os

IMG_PATH = 'Mo'
BLURRED_IMG_PATH = 'Mo'


def vectorize_plan(img_name):
    #####################################################################################
    # Blurring and splitting
    img = cv2.imread(os.path.join(IMG_PATH, img_name))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    rimg = img.copy()
    # blurred_img = cv2.pyrMeanShiftFiltering(img, 20, 20)
    blurred_img = cv2.imread(os.path.join(BLURRED_IMG_PATH, img_name))

    r, g, b = cv2.split(img)
    rb, gb, bb = cv2.split(blurred_img)

    ####################################################################################
    # Getting walls width
    wall_width = get_wall_width(r, g, b, 0)
    wall_width = wall_width * 2 // 3

    #####################################################################################
    # Getting rooms
    rooms_contours = get_rooms(rb, gb, bb, img, include_balacony=True, as_contours=True, wall_width=wall_width)

    # rooms_polys = rooms_polygons(img, rooms_contours)
    rooms_polys_smooth = rooms_polygons(rooms_contours, smooth=True)

    rooms_mask = draw_polygons(rooms_polys_smooth, r.copy() * 0, (255, 0, 0))

    ####################################################################################
    # Getting walls itself
    lines = get_wall_lines(img, rooms_mask)

    lines = [l for l in lines if line_length(l) > 3]

    wall_polys, xs, ys, points = get_wall_lines_polys(lines, wall_width)

    rooms_polys_smooth = rooms_polygons(rooms_contours, smooth=True, xsys=(xs, ys), eps=wall_width, multi_poly=True)
    img = draw_polygons(rooms_polys_smooth, img, (255, 0, 0))

    ####################################################################################
    # Getting walls itself
    c1, c2, c3 = cv2.split(img)

    # ####################################################################################################################;
    # Window and door

    window_rec = window_rects(r, g, b, room_wall_mask=c1 | c2 | c3, width=wall_width, points=points)
    door_rec = get_doors(r, g, b, rimg, width=wall_width, points=points)

    window_poly = MultiPolygon(rects_to_polygons(window_rec))
    door_poly = MultiPolygon(rects_to_polygons(door_rec))

    data = [
        {**rooms_polys_smooth, 'door': door_poly, 'window': window_poly, 'wall_lines': lines, 'wall_poly': wall_polys,
         'size': img.shape[:2], 'wall_width': wall_width}]
