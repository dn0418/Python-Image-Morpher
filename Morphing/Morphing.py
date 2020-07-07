#######################################################
#   Author:     David Dowd
#   email:      ddowd@purdue.edu
#   ID:         ee364e06
#   Date:       04/05/19
#######################################################

import os
import imageio
import time
from scipy.spatial import Delaunay
from scipy.interpolate import RectBivariateSpline
from matplotlib.path import Path
import numpy as np
from PIL import Image
import itertools
import concurrent.futures
import multiprocessing
import threading

from profilehooks import profile
from pycallgraph import PyCallGraph
from pycallgraph.output import GraphvizOutput

# Module  level  Variables
#######################################################
# DataPath = os.path.expanduser('/Users/xzomb/PycharmProjects/Personal/')
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


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
    #rightTri.vertices = rightList
    rightTri.vertices = rightArray

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
        minX = int(self.vertices[:, 0].min())
        maxX = int(self.vertices[:, 0].max())
        minY = int(self.vertices[:, 1].min())
        maxY = int(self.vertices[:, 1].max())

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

        # TODO: New! Crude and quickly thrown together. Reminder to clean this function up later.
        coordArray = np.transpose(coordArray)
        temp = np.ones(coordArray.shape[1])
        coordArray = np.vstack((coordArray, temp))

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
        self.leftInterpolation = RectBivariateSpline(np.arange(0, self.leftImage.shape[0], 1), np.arange(0, self.leftImage.shape[1], 1), self.leftImage)
        self.rightInterpolation = RectBivariateSpline(np.arange(0, self.leftImage.shape[0], 1), np.arange(0, self.leftImage.shape[1], 1), self.rightImage)
        self.lock = threading.Lock()

    #@profile
    def getImageAtAlpha(self, alpha, mode):
        '''
        for leftTriangle, rightTriangle in zip(self.leftTriangles, self.rightTriangles):
            t = threading.Thread(target=self.interpolatePoints, args=(leftTriangle, rightTriangle, alpha))
            t.start()
        main_thread = threading.currentThread()
        for t in threading.enumerate():
            if t is not main_thread:
                t.join()
        '''

        #with concurrent.futures.ThreadPoolExecutor() as executor:
        #    results = [executor.submit(self.interpolatePoints, leftTriangle, rightTriangle, alpha) for leftTriangle, rightTriangle in zip(self.leftTriangles, self.rightTriangles)]

        '''
        with concurrent.futures.ProcessPoolExecutor() as executor:
            results = [executor.submit(self.interpolatePoints, leftTriangle, rightTriangle, alpha) for leftTriangle, rightTriangle in zip(self.leftTriangles, self.rightTriangles)]
        '''

        for leftTriangle, rightTriangle in zip(self.leftTriangles, self.rightTriangles):
            self.interpolatePoints(leftTriangle, rightTriangle, alpha)

        blendARR = ((1 - alpha) * self.leftImage + alpha * self.rightImage)
        blendARR = blendARR.astype(np.uint8)
        return blendARR

    def interpolatePoints(self, leftTriangle, rightTriangle, alpha):
        targetTriangle = Triangle(leftTriangle.vertices + (rightTriangle.vertices - leftTriangle.vertices) * alpha)
        targetVertices = targetTriangle.vertices.reshape(6, 1)
        tempLeftMatrix = np.array([[leftTriangle.vertices[0][0], leftTriangle.vertices[0][1], 1, 0, 0, 0],
                                   [0, 0, 0, leftTriangle.vertices[0][0], leftTriangle.vertices[0][1], 1],
                                   [leftTriangle.vertices[1][0], leftTriangle.vertices[1][1], 1, 0, 0, 0],
                                   [0, 0, 0, leftTriangle.vertices[1][0], leftTriangle.vertices[1][1], 1],
                                   [leftTriangle.vertices[2][0], leftTriangle.vertices[2][1], 1, 0, 0, 0],
                                   [0, 0, 0, leftTriangle.vertices[2][0], leftTriangle.vertices[2][1], 1]])
        tempRightMatrix = np.array([[rightTriangle.vertices[0][0], rightTriangle.vertices[0][1], 1, 0, 0, 0],
                                    [0, 0, 0, rightTriangle.vertices[0][0], rightTriangle.vertices[0][1], 1],
                                    [rightTriangle.vertices[1][0], rightTriangle.vertices[1][1], 1, 0, 0, 0],
                                    [0, 0, 0, rightTriangle.vertices[1][0], rightTriangle.vertices[1][1], 1],
                                    [rightTriangle.vertices[2][0], rightTriangle.vertices[2][1], 1, 0, 0, 0],
                                    [0, 0, 0, rightTriangle.vertices[2][0], rightTriangle.vertices[2][1], 1]])
        lefth = np.linalg.solve(tempLeftMatrix, targetVertices)
        righth = np.linalg.solve(tempRightMatrix, targetVertices)
        leftH = np.array([[lefth[0][0], lefth[1][0], lefth[2][0]], [lefth[3][0], lefth[4][0], lefth[5][0]], [0, 0, 1]])
        rightH = np.array(
            [[righth[0][0], righth[1][0], righth[2][0]], [righth[3][0], righth[4][0], righth[5][0]], [0, 0, 1]])
        # can add .round(decimals=x) to the end of left and right invH to reduce precision
        leftinvH = np.linalg.inv(leftH)
        rightinvH = np.linalg.inv(rightH)
        targetPoints = targetTriangle.getPoints()

        # np.delete(array, 2, 1)
        leftSourcePoints = np.transpose(np.matmul(leftinvH, targetPoints))
        rightSourcePoints = np.transpose(np.matmul(rightinvH, targetPoints))
        targetPoints = np.transpose(targetPoints)
        #return zip(targetPoints, leftSourcePoints, rightSourcePoints)
        self.lock.acquire()
        for x, y, z in zip(targetPoints, leftSourcePoints, rightSourcePoints):
            self.leftImage[int(x[1])][int(x[0])] = self.leftInterpolation(y[1], y[0])
            self.rightImage[int(x[1])][int(x[0])] = self.rightInterpolation(z[1], z[0])
        self.lock.release()



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
