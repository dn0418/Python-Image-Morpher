#######################################################
#            Author:     David Dowd
#            Email:      ddowd97@gmail.com
#######################################################

import os
import copy
from PIL import Image, ImageDraw
from scipy.spatial import Delaunay                  # pip install scipy
from scipy.interpolate import RectBivariateSpline   # pip install scipy
import numpy as np                                  # pip install numpy

# Module  level  Variables
#######################################################
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def loadTriangles(leftPointFilePath: str, rightPointFilePath: str) -> tuple:
    leftTriList = []
    rightTriList = []

    leftArray = np.loadtxt(leftPointFilePath).astype(np.float64)
    rightArray = np.loadtxt(rightPointFilePath).astype(np.float64)

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

    # Credit to https://github.com/zhifeichen097/Image-Morphing for the following approach (which is a bit more efficient than my own)!
    def getPoints(self):
        width = round(max(self.vertices[:, 0]) + 2)
        height = round(max(self.vertices[:, 1]) + 2)
        mask = Image.new('P', (width, height), 0)
        ImageDraw.Draw(mask).polygon(tuple(map(tuple, self.vertices)), outline=255, fill=255)
        coordArray = np.transpose(np.nonzero(mask))

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
        self.newLeftImage = copy.deepcopy(leftImage)
        self.leftTriangles = leftTriangles  # Not of type np.uint8
        self.rightImage = copy.deepcopy(rightImage)
        self.newRightImage = copy.deepcopy(rightImage)
        self.rightTriangles = rightTriangles  # Not of type np.uint8

    def getImageAtAlpha(self, alpha):
        for leftTriangle, rightTriangle in zip(self.leftTriangles, self.rightTriangles):
            self.interpolatePoints(leftTriangle, rightTriangle, alpha)
        return ((1 - alpha) * self.newLeftImage + alpha * self.newRightImage).astype(np.uint8)

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
        try:
            lefth = np.linalg.solve(tempLeftMatrix, targetVertices)
            righth = np.linalg.solve(tempRightMatrix, targetVertices)
            leftH = np.array([[lefth[0][0], lefth[1][0], lefth[2][0]], [lefth[3][0], lefth[4][0], lefth[5][0]], [0, 0, 1]])
            rightH = np.array([[righth[0][0], righth[1][0], righth[2][0]], [righth[3][0], righth[4][0], righth[5][0]], [0, 0, 1]])
            leftinvH = np.linalg.inv(leftH)
            rightinvH = np.linalg.inv(rightH)
            targetPoints = targetTriangle.getPoints()

            # Credit to https://github.com/zhifeichen097/Image-Morphing for the following code block that I've adapted. Exceptional work on discovering
            # RectBivariateSpline's .ev() method! I noticed the method but didn't think much of it at the time due to the website's poor documentation..
            xp, yp = np.transpose(targetPoints)
            leftXValues = leftinvH[1, 1] * xp + leftinvH[1, 0] * yp + leftinvH[1, 2]
            leftYValues = leftinvH[0, 1] * xp + leftinvH[0, 0] * yp + leftinvH[0, 2]
            leftXParam = np.arange(np.amin(leftTriangle.vertices[:, 1]), np.amax(leftTriangle.vertices[:, 1]), 1)
            leftYParam = np.arange(np.amin(leftTriangle.vertices[:, 0]), np.amax(leftTriangle.vertices[:, 0]), 1)
            leftImageValues = self.leftImage[int(leftXParam[0]):int(leftXParam[-1] + 1), int(leftYParam[0]):int(leftYParam[-1] + 1)]

            rightXValues = rightinvH[1, 1] * xp + rightinvH[1, 0] * yp + rightinvH[1, 2]
            rightYValues = rightinvH[0, 1] * xp + rightinvH[0, 0] * yp + rightinvH[0, 2]
            rightXParam = np.arange(np.amin(rightTriangle.vertices[:, 1]), np.amax(rightTriangle.vertices[:, 1]), 1)
            rightYParam = np.arange(np.amin(rightTriangle.vertices[:, 0]), np.amax(rightTriangle.vertices[:, 0]), 1)
            rightImageValues = self.rightImage[int(rightXParam[0]):int(rightXParam[-1] + 1), int(rightYParam[0]):int(rightYParam[-1] + 1)]

            self.newLeftImage[xp, yp] = RectBivariateSpline(leftXParam, leftYParam, leftImageValues, kx=1, ky=1).ev(leftXValues, leftYValues)
            self.newRightImage[xp, yp] = RectBivariateSpline(rightXParam, rightYParam, rightImageValues, kx=1, ky=1).ev(rightXValues, rightYValues)
        except:
            return
