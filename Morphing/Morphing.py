#######################################################
#   Author:     David Dowd
#   email:      ddowd@purdue.edu
#   ID:         ee364e06
#   Date:       04/05/19
#######################################################

import multiprocessing
import os
import sys
import imageio
import scipy
import time
import matplotlib.pyplot as plt
from scipy.spatial import Delaunay
from scipy import ndimage
from scipy.interpolate import RectBivariateSpline
from matplotlib.path import Path
import numpy as np
from PIL import Image
from pycallgraph import PyCallGraph
from pycallgraph.output import GraphvizOutput
import itertools
import math

...

# Module  level  Variables
#######################################################
DataPath = os.path.expanduser('/Users/xzomb/PycharmProjects/Personal/')


# np.uint8 [image value assignment], np.float64 [matrix algebra], np.round() [before assigning a float to an int]
# scipy.interpolate.RectBivariateSpline(), scipy.interpolate.interp2d(), scipy.ndimage.map_coordinates()
# "Point-in-Polygon" Technique (ImageDraw().polygon)
# h = np.linalg.solve(A, b)
# 0 Alpha -> Image 1. 100 Alpha -> Image 2. X Alpha -> (1 - Alpha)Image1 + (Alpha)Image2

def loadTriangles(leftPointFilePath: str, rightPointFilePath: str) -> tuple:
    leftList = []
    rightList = []

    with open(leftPointFilePath, "r") as leftFile:
        for j in leftFile:
            leftList.append(j.split())
    with open(rightPointFilePath, "r") as rightFile:
        for k in rightFile:
            rightList.append(k.split())

    leftArray = np.array(leftList, np.float64)
    rightArray = np.array(rightList, np.float64)
    leftTri = Delaunay(leftArray)
    rightTri = leftTri
    rightTri.vertices = rightList

    leftNP = np.array(leftArray[leftTri.simplices], np.float64)
    rightNP = np.array(rightArray[rightTri.simplices], np.float64)

    leftTriList = []
    rightTriList = []

    for x in leftNP:
        leftTriList.append(Triangle(x))
    for y in rightNP:
        rightTriList.append(Triangle(y))

    triangleTuple = (leftTriList, rightTriList)
    return triangleTuple


class Triangle:
    def __init__(self, vertices):
        if isinstance(vertices, np.ndarray) == 0:
            raise ValueError("Input argument is not of type np.array.")
        if vertices.shape != (3, 2):
            raise ValueError("Input argument does not have the expected dimensions.")
        if vertices.dtype != np.float64:
            raise ValueError("Input argument is not of type float64.")
        self.vertices = vertices

    def getPoints(self):
        minX = int(min(self.vertices[0][0], self.vertices[1][0], self.vertices[2][0]))
        maxX = int(max(self.vertices[0][0], self.vertices[1][0], self.vertices[2][0]))
        minY = int(min(self.vertices[0][1], self.vertices[1][1], self.vertices[2][1]))
        maxY = int(max(self.vertices[0][1], self.vertices[1][1], self.vertices[2][1]))

        xList = range(minX, maxX + 1)
        yList = range(minY, maxY + 1)
        a = [xList, yList]
        emptyList = list(itertools.product(*a))

        points = np.array(emptyList, np.float64)
        p = Path(self.vertices)
        grid = p.contains_points(points)
        mask = grid.reshape(maxX - minX + 1, maxY - minY + 1)

        trueArray = np.where(np.array(mask) == True)
        leftArray = (trueArray[0] + minX).reshape(np.shape(trueArray[0])[0], 1)
        rightArray = (trueArray[1] + minY).reshape(np.shape(trueArray[1])[0], 1)
        coordArray = np.hstack((leftArray, rightArray))

        return coordArray


class Morpher:
    def __init__(self, leftImage, leftTriangles, rightImage, rightTriangles):
        if type(leftImage) != np.ndarray:
            raise TypeError('Input leftImage is not an np.ndarray')
        if leftImage.dtype != np.uint8:
            raise TypeError('Input leftImage is not of type np.uint8')
        if type(rightImage) != np.ndarray:
            raise TypeError('Input rightImage is not an np.ndarray')
        if rightImage.dtype != np.uint8:
            raise TypeError('Input rightImage is not of type np.uint8')
        if type(leftTriangles) != list:
            raise TypeError('Input leftTriangles is not of type List')
        for j in leftTriangles:
            if isinstance(j, Triangle) == 0:
                raise TypeError('Element of input leftTriangles is not of Class Triangle')
        if type(rightTriangles) != list:
            raise TypeError('Input leftTriangles is not of type List')
        for k in rightTriangles:
            if isinstance(k, Triangle) == 0:
                raise TypeError('Element of input rightTriangles is not of Class Triangle')
        self.leftImage = leftImage
        self.leftTriangles = leftTriangles  # Not of type np.uint8
        self.rightImage = rightImage
        self.rightTriangles = rightTriangles  # Not of type np.uint8

    def getImageAtAlpha(self, alpha, mode):
        xRange = np.arange(0, self.leftImage.shape[1], 1)
        yRange = np.arange(0, self.leftImage.shape[0], 1)
        leftInterpolation = RectBivariateSpline(yRange, xRange, self.leftImage)
        rightInterpolation = RectBivariateSpline(yRange, xRange, self.rightImage)
        # newTargetTriangleList = [Triangle((leftTriangle.vertices + (rightTriangle.vertices - leftTriangle.vertices) * alpha)) for leftTriangle, rightTriangle in zip(self.leftTriangles, self.rightTriangles)]
        for leftTriangle, rightTriangle in zip(self.leftTriangles, self.rightTriangles):
            targetTriangle = Triangle((leftTriangle.vertices + (rightTriangle.vertices - leftTriangle.vertices) * alpha))
            tempLeftMatrix = np.array([leftTriangle.vertices[0][0], leftTriangle.vertices[0][1], 1, 0, 0, 0, 0, 0, 0,
                                       leftTriangle.vertices[0][0], leftTriangle.vertices[0][1], 1,
                                       leftTriangle.vertices[1][0], leftTriangle.vertices[1][1], 1, 0, 0, 0, 0, 0, 0,
                                       leftTriangle.vertices[1][0], leftTriangle.vertices[1][1], 1,
                                       leftTriangle.vertices[2][0], leftTriangle.vertices[2][1], 1, 0, 0, 0, 0, 0, 0,
                                       leftTriangle.vertices[2][0], leftTriangle.vertices[2][1], 1])
            tempLeftMatrix = tempLeftMatrix.reshape(6, 6)
            tempRightMatrix = np.array([rightTriangle.vertices[0][0], rightTriangle.vertices[0][1], 1, 0, 0, 0, 0, 0, 0,
                                        rightTriangle.vertices[0][0], rightTriangle.vertices[0][1], 1,
                                        rightTriangle.vertices[1][0], rightTriangle.vertices[1][1], 1, 0, 0, 0, 0, 0, 0,
                                        rightTriangle.vertices[1][0], rightTriangle.vertices[1][1], 1,
                                        rightTriangle.vertices[2][0], rightTriangle.vertices[2][1], 1, 0, 0, 0, 0, 0, 0,
                                        rightTriangle.vertices[2][0], rightTriangle.vertices[2][1], 1])
            tempRightMatrix = tempRightMatrix.reshape(6, 6)
            targetVertices = targetTriangle.vertices.reshape(6, 1)
            lefth = np.linalg.solve(tempLeftMatrix, targetVertices)
            righth = np.linalg.solve(tempRightMatrix, targetVertices)
            leftH = np.array([lefth[0][0], lefth[1][0], lefth[2][0], lefth[3][0], lefth[4][0], lefth[5][0], 0, 0, 1])
            leftH = leftH.reshape(3, 3)
            rightH = np.array([righth[0][0], righth[1][0], righth[2][0], righth[3][0], righth[4][0], righth[5][0], 0, 0, 1])
            rightH = rightH.reshape(3, 3)
            # can add .round(decimals=5) to the end of left and right invH to reduce precision, seems to have no negative visual effects
            leftinvH = np.linalg.inv(leftH)
            rightinvH = np.linalg.inv(rightH)
            targetPoints = targetTriangle.getPoints()
            for x in targetPoints:  # TODO: HUGE Bottleneck (~90% of Program Runtime!) ... Unsure of how to optimize.
                x = np.array([x[0], x[1], 1]).reshape(3, 1)
                leftSourcePoint = np.matmul(leftinvH, x)  # TODO: Roughly 21% of Bottleneck
                rightSourcePoint = np.matmul(rightinvH, x)  # TODO: Roughly 21% of Bottleneck
                self.leftImage[int(x[1])][int(x[0])] = leftInterpolation(leftSourcePoint[1], leftSourcePoint[0])  # TODO: Roughly 29% of Bottleneck
                self.rightImage[int(x[1])][int(x[0])] = rightInterpolation(rightSourcePoint[1], rightSourcePoint[0])  # TODO: Roughly 29% of Bottleneck
        blendARR = ((1 - alpha) * self.leftImage + alpha * self.rightImage)
        blendARR = blendARR.astype(np.uint8)
        return blendARR

# EXPERIMENTAL MANUAL INTERPOLATION METHOD.. TAKES 2-3X AS LONG, IMAGE INCORRECT.. COULD BE FIXED...
'''
z = float(leftSourcePoint[0])
z1 = math.floor(z)
z2 = math.ceil(z)
y = float(leftSourcePoint[1])
y1 = math.floor(y)
y2 = math.ceil(y)
if z1 == z2:
    z1 = max(0, z1 - 1)
    z2 = min(self.leftImage.shape[1], z2 + 1)
    # left_fx_y1 = self.leftImage([y1][z1])
    # left_fx_y2 = self.leftImage([y2][z1])
left_fx_y1 = ((z2 - float(z)) / (z2 - z1)) * self.leftImage[y1][z1] + ((z - z1) / (z2 - z1)) * self.leftImage[y1][z2]
left_fx_y2 = ((z2 - z) / (z2 - z1)) * self.leftImage[y2][z1] + ((z - z1) / (z2 - z1)) * self.leftImage[y2][z2]

if y1 == y2:
    y1 = max(0, y1 - 1)
    y2 = min(self.leftImage.shape[0], y2 + 1)
self.leftImage[int(x[1])][int(x[0])] = ((y2 - y) / (y2 - y1)) * left_fx_y1 + ((y - y1) / (y2 - y1)) * left_fx_y2

z = float(rightSourcePoint[0])
z1 = math.floor(z)
z2 = math.ceil(z)
y = float(rightSourcePoint[1])
y1 = math.floor(y)
y2 = math.ceil(y)
if z1 == z2:
    z1 = max(0, z1 - 1)
    z2 = min(self.rightImage.shape[1], z2 + 1)
    # left_fx_y1 = self.leftImage([y1][z1])
    # left_fx_y2 = self.leftImage([y2][z1])
right_fx_y1 = ((z2 - float(z)) / (z2 - z1)) * self.rightImage[y1][z1] + ((z - z1) / (z2 - z1)) * self.rightImage[y1][z2]
right_fx_y2 = ((z2 - z) / (z2 - z1)) * self.rightImage[y2][z1] + ((z - z1) / (z2 - z1)) * self.rightImage[y2][z2]

if y1 == y2:
    y1 = max(0, y1 - 1)
    y2 = min(self.rightImage.shape[0], y2 + 1)
self.rightImage[int(x[1])][int(x[0])] = ((y2 - y) / (y2 - y1)) * right_fx_y1 + ((y - y1) / (y2 - y1)) * right_fx_y2
'''


if __name__ == "__main__":
    #with PyCallGraph(output=GraphvizOutput()):
        begin = time.time()
        leftPointFilePath = 'C:/Users/xzomb/PycharmProjects/Personal/Morphing/Images_Points/StartGray1.txt'
        rightPointFilePath = 'C:/Users/xzomb/PycharmProjects/Personal/Morphing/Images_Points/EndGray1.txt'
        testTuple = loadTriangles(leftPointFilePath, rightPointFilePath)
        left = imageio.imread('C:/Users/xzomb/PycharmProjects/Personal/Morphing/Images_Points/StartGray1.jpg')
        right = imageio.imread('C:/Users/xzomb/PycharmProjects/Personal/Morphing/Images_Points/EndGray1.jpg')
        leftARR = np.asarray(left)
        rightARR = np.asarray(right)
        testMorph = Morpher(leftARR, testTuple[0], rightARR, testTuple[1])
        blendARR = testMorph.getImageAtAlpha(0.5, 0)
        im = Image.fromarray(blendARR)
        im.save("blah.jpg")
        print("Took a total of " + str(time.time() - begin) + " seconds.\n")
