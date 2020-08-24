#######################################################
#   Author:     David Dowd
#   Email:      ddowd97@gmail.com
#######################################################

import os
import copy
from scipy.ndimage import median_filter
from scipy.spatial import Delaunay                  # pip install scipy
from scipy.interpolate import RectBivariateSpline   # pip install scipy
from matplotlib.path import Path                    # pip install matplotlib
import numpy as np                                  # pip install numpy
import itertools

# Module  level  Variables
#######################################################
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def loadTriangles(leftPointFilePath: str, rightPointFilePath: str) -> tuple:
    leftList = []
    rightList = []
    leftTriList = []
    rightTriList = []

    with open(leftPointFilePath, "r") as leftFile:
        for j in leftFile:
            leftList.append(j.split())
    with open(rightPointFilePath, "r") as rightFile:
        for k in rightFile:
            rightList.append(k.split())

    leftArray = np.array(leftList, np.float64)
    rightArray = np.array(rightList, np.float64)
    delaunayTri = Delaunay(leftArray)

    leftNP = leftArray[delaunayTri.simplices]
    rightNP = rightArray[delaunayTri.simplices]

    for x, y in zip(leftNP, rightNP):
        leftTriList.append(Triangle(x))
        rightTriList.append(Triangle(y))

    return leftTriList, rightTriList


class Triangle:
    def __init__(self, vertices):
        if isinstance(vertices, np.ndarray) == 0:
            raise ValueError("Input argument is not of type np.array.")
        if vertices.shape != (3, 2):
            raise ValueError("Input argument does not have the expected dimensions.")
        if vertices.dtype != np.float64:
            raise ValueError("Input argument is not of type float64.")
        self.vertices = vertices
        self.minX = int(self.vertices[:, 0].min())
        self.maxX = int(self.vertices[:, 0].max())
        self.minY = int(self.vertices[:, 1].min())
        self.maxY = int(self.vertices[:, 1].max())

    def getPoints(self):
        xList = range(self.minX, self.maxX + 1)
        yList = range(self.minY, self.maxY + 1)
        a = [xList, yList]
        emptyList = list(itertools.product(*a))

        points = np.array(emptyList, np.float64)
        p = Path(self.vertices)
        grid = p.contains_points(points)
        mask = grid.reshape(self.maxX - self.minX + 1, self.maxY - self.minY + 1)

        trueArray = np.where(np.array(mask) == True)
        coordArray = np.vstack((trueArray[0] + self.minX, trueArray[1] + self.minY, np.ones(trueArray[0].shape[0])))

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
        self.leftImage = copy.deepcopy(leftImage)
        self.leftTriangles = leftTriangles  # Not of type np.uint8
        self.rightImage = copy.deepcopy(rightImage)
        self.rightTriangles = rightTriangles  # Not of type np.uint8
        self.leftInterpolation = RectBivariateSpline(np.arange(self.leftImage.shape[0]), np.arange(self.leftImage.shape[1]), self.leftImage)
        self.rightInterpolation = RectBivariateSpline(np.arange(self.rightImage.shape[0]), np.arange(self.rightImage.shape[1]), self.rightImage)


    def getImageAtAlpha(self, alpha, smoothMode):
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
        rightH = np.array([[righth[0][0], righth[1][0], righth[2][0]], [righth[3][0], righth[4][0], righth[5][0]], [0, 0, 1]])
        leftinvH = np.linalg.inv(leftH)
        rightinvH = np.linalg.inv(rightH)
        targetPoints = targetTriangle.getPoints()  # TODO: ~ 17-18% of runtime

        leftSourcePoints = np.transpose(np.matmul(leftinvH, targetPoints))
        rightSourcePoints = np.transpose(np.matmul(rightinvH, targetPoints))
        targetPoints = np.transpose(targetPoints)

        for x, y, z in zip(targetPoints, leftSourcePoints, rightSourcePoints):  # TODO: ~ 53% of runtime
            self.leftImage[int(x[1])][int(x[0])] = self.leftInterpolation(y[1], y[0])
            self.rightImage[int(x[1])][int(x[0])] = self.rightInterpolation(z[1], z[0])

def smoothBlend(blendImage):
    return median_filter(blendImage, size=2)
