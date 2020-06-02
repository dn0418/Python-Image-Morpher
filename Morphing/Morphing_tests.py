import unittest
import os
from uuid import uuid4
from time import perf_counter
import numpy as np
from imageio import imread as libread

from MorphingUtility import *
from Morphing import *

TestFolder = "TestData"

# Modify this settings to increase acceptable difference.
maxDiff = 10

def imread(filePath):
    startImage = libread(filePath)
    return np.array(startImage)


class MorphingTestSuite(unittest.TestCase, ImageAssertion):

    def test_loadTriangle(self):

        leftPath = os.path.join(TestFolder, "points.left.txt")
        rightPath = os.path.join(TestFolder, "points.right.txt")
        loaded = loadTriangles(leftPath, rightPath)

        with self.subTest(key="Returned Type"):             # 1.5 Points

            self.assertIsInstance(loaded, tuple)

        first, second = loaded

        with self.subTest(key="Triangles present"):         # 1.5 Points

            isValid1 = all(isinstance(e, Triangle) for e in first)
            isValid2 = all(isinstance(e, Triangle) for e in second)
            self.assertTrue(isValid1 and isValid2)

    def test_Triangle(self):

        with self.subTest(key="Normal Initializer"):        # 1.5 Points

            t = Triangle(self.support.vertices)
            self.assertIsInstance(t, Triangle)

        with self.subTest(key="Incorrect Dimensions"):      # 1.5 Points

            self.assertRaises(ValueError, Triangle, self.support.smallVertices)

        with self.subTest(key="Incorrect DataType"):        # 1.5 Points

            self.assertRaises(ValueError, Triangle, self.support.otherVertices)

        with self.subTest(key="Incorrect Types"):           # 1.5 Points

            self.assertRaises(ValueError, Triangle, [[ 786.6,  864. ], [ 844.2,  898.2], [ 709.2,  1079.]])

        with self.subTest(key="Point Content"):             # 11 Points
            tri = Triangle(self.support.pointVertices)
            actualValue = sorted([(int(x), int(y)) for x, y in tri.getPoints().tolist()])
            expectedValue = sorted([(int(x), int(y)) for x, y in self.support.samplePoints.tolist()])

            actualPoints = set(actualValue)
            expectedPoints = set(expectedValue)
            common = actualPoints & expectedPoints
            difference = (actualPoints - expectedPoints) | (expectedPoints - actualPoints)

            if difference:
                print(f" ==> Common Points = {len(common)}, Different Points = {len(difference)}")
                print(f" =====> List of different points = {difference}\n")

            self.assertLessEqual(len(difference), 33)

    def test_Morpher(self):                                 # 5 Points

        leftPointFilePath = os.path.join(TestFolder, "points.left.txt")
        rightPointFilePath = os.path.join(TestFolder, "points.right.txt")
        leftTriangles, rightTriangles = loadTriangles(leftPointFilePath, rightPointFilePath)

        leftImagePath = os.path.join(TestFolder, 'LeftGray.png')
        rightImagePath = os.path.join(TestFolder, 'RightGray.png')

        leftImage = imread(leftImagePath)
        rightImage = imread(rightImagePath)

        morpher = Morpher(leftImage, leftTriangles, rightImage, rightTriangles)

        with self.subTest(key="Normal Initializer"):

            self.assertIsInstance(morpher, Morpher)

        with self.subTest(key="Attribute Check"):

            attributes = ["leftImage", "leftTriangles", "rightImage", "rightTriangles"]
            actualValue = all(hasattr(morpher, a) for a in attributes)
            self.assertTrue(actualValue)

        with self.subTest(key="Incorrect Initializer"):

            arr = self.support.pointVertices
            self.assertRaises(TypeError, Morpher, leftImage, arr, rightImage, arr)

    def test_MorpherAlpha25(self):                          # 25 Points

        leftPointFilePath = os.path.join(TestFolder, "points.left.txt")
        rightPointFilePath = os.path.join(TestFolder, "points.right.txt")
        leftImagePath = os.path.join(TestFolder, 'LeftGray.png')
        rightImagePath = os.path.join(TestFolder, 'RightGray.png')
        expectedPath = os.path.join(TestFolder, 'Alpha25Gray.png')
        comparisonImagePath = os.path.join(TestFolder, str(uuid4()).upper() + '-GrayAlpha25Comparison.png')

        leftImage = imread(leftImagePath)
        rightImage = imread(rightImagePath)
        leftTriangles, rightTriangles = loadTriangles(leftPointFilePath, rightPointFilePath)
        expectedImage = imread(expectedPath)

        morpher = Morpher(leftImage, leftTriangles, rightImage, rightTriangles)
        actualImage = morpher.getImageAtAlpha(0.25)

        self.assertArrayAlmostEqual(expectedImage, actualImage, maxDiff, comparisonImagePath)

    def test_MorpherAlpha50(self):                          # 25 Points

        leftPointFilePath = os.path.join(TestFolder, "points.left.txt")
        rightPointFilePath = os.path.join(TestFolder, "points.right.txt")
        leftImagePath = os.path.join(TestFolder, 'LeftGray.png')
        rightImagePath = os.path.join(TestFolder, 'RightGray.png')
        expectedPath = os.path.join(TestFolder, 'Alpha50Gray.png')
        comparisonImagePath = os.path.join(TestFolder, str(uuid4()).upper() + '-GrayAlpha50Comparison.png')

        leftImage = imread(leftImagePath)
        rightImage = imread(rightImagePath)
        leftTriangles, rightTriangles = loadTriangles(leftPointFilePath, rightPointFilePath)
        expectedImage = imread(expectedPath)

        morpher = Morpher(leftImage, leftTriangles, rightImage, rightTriangles)
        actualImage = morpher.getImageAtAlpha(0.50)

        self.assertArrayAlmostEqual(expectedImage, actualImage, maxDiff, comparisonImagePath)

    def test_MorpherAlpha75(self):                          # 25 Points
        leftPointFilePath = os.path.join(TestFolder, "points.left.txt")
        rightPointFilePath = os.path.join(TestFolder, "points.right.txt")
        leftImagePath = os.path.join(TestFolder, 'LeftGray.png')
        rightImagePath = os.path.join(TestFolder, 'RightGray.png')
        expectedPath = os.path.join(TestFolder, 'Alpha75Gray.png')
        comparisonImagePath = os.path.join(TestFolder, str(uuid4()).upper() + '-GrayAlpha75Comparison.png')

        leftImage = imread(leftImagePath)
        rightImage = imread(rightImagePath)
        leftTriangles, rightTriangles = loadTriangles(leftPointFilePath, rightPointFilePath)
        expectedImage = imread(expectedPath)

        morpher = Morpher(leftImage, leftTriangles, rightImage, rightTriangles)
        actualImage = morpher.getImageAtAlpha(0.75)

        self.assertArrayAlmostEqual(expectedImage, actualImage, maxDiff, comparisonImagePath)

    @classmethod
    def setUpClass(cls):
        cls.support = Support()


class ColorMorphingTestSuite(unittest.TestCase, ImageAssertion): # 5 Points

    def test_ColorMorpherAlpha25(self):

        leftPointFilePath = os.path.join(TestFolder, "points.left.txt")
        rightPointFilePath = os.path.join(TestFolder, "points.right.txt")
        leftImagePath = os.path.join(TestFolder, 'LeftColor.png')
        rightImagePath = os.path.join(TestFolder, 'RightColor.png')
        expectedPath = os.path.join(TestFolder, 'Alpha25Color.png')
        comparisonImagePath = os.path.join(TestFolder, str(uuid4()).upper() + '-ColorAlpha25Comparison.png')

        leftImage = imread(leftImagePath)
        rightImage = imread(rightImagePath)
        leftTriangles, rightTriangles = loadTriangles(leftPointFilePath, rightPointFilePath)
        expectedImage = imread(expectedPath)

        morpher = ColorMorpher(leftImage, leftTriangles, rightImage, rightTriangles)
        actualImage = morpher.getImageAtAlpha(0.25)

        self.assertArrayAlmostEqual(expectedImage, actualImage, maxDiff, comparisonImagePath)

    def test_ColorMorpherAlpha50(self):

        leftPointFilePath = os.path.join(TestFolder, "points.left.txt")
        rightPointFilePath = os.path.join(TestFolder, "points.right.txt")
        leftImagePath = os.path.join(TestFolder, 'LeftColor.png')
        rightImagePath = os.path.join(TestFolder, 'RightColor.png')
        expectedPath = os.path.join(TestFolder, 'Alpha50Color.png')
        comparisonImagePath = os.path.join(TestFolder, str(uuid4()).upper() + '-ColorAlpha50Comparison.png')

        leftImage = imread(leftImagePath)
        rightImage = imread(rightImagePath)
        leftTriangles, rightTriangles = loadTriangles(leftPointFilePath, rightPointFilePath)
        expectedImage = imread(expectedPath)

        morpher = ColorMorpher(leftImage, leftTriangles, rightImage, rightTriangles)
        actualImage = morpher.getImageAtAlpha(0.50)

        self.assertArrayAlmostEqual(expectedImage, actualImage, maxDiff, comparisonImagePath)

    def test_ColorMorpherAlpha75(self):

        leftPointFilePath = os.path.join(TestFolder, "points.left.txt")
        rightPointFilePath = os.path.join(TestFolder, "points.right.txt")
        leftImagePath = os.path.join(TestFolder, 'LeftColor.png')
        rightImagePath = os.path.join(TestFolder, 'RightColor.png')
        expectedPath = os.path.join(TestFolder, 'Alpha75Color.png')
        comparisonImagePath = os.path.join(TestFolder, str(uuid4()).upper() + '-ColorAlpha75Comparison.png')

        leftImage = imread(leftImagePath)
        rightImage = imread(rightImagePath)
        leftTriangles, rightTriangles = loadTriangles(leftPointFilePath, rightPointFilePath)
        expectedImage = imread(expectedPath)

        morpher = ColorMorpher(leftImage, leftTriangles, rightImage, rightTriangles)
        actualImage = morpher.getImageAtAlpha(0.75)

        self.assertArrayAlmostEqual(expectedImage, actualImage, maxDiff, comparisonImagePath)

    @classmethod
    def setUpClass(cls):
        cls.support = Support()


class MorphingVideoTestSuite(unittest.TestCase, ImageAssertion): # 5 Points

    def test_generateGrayVideo(self):

        leftPointFilePath = os.path.join(TestFolder, "points.left.txt")
        rightPointFilePath = os.path.join(TestFolder, "points.right.txt")
        leftImagePath = os.path.join(TestFolder, 'LeftGray.png')
        rightImagePath = os.path.join(TestFolder, 'RightGray.png')
        targetVideoPath = os.path.join(TestFolder, 'GrayMorph.mp4')

        leftImage = imread(leftImagePath)
        rightImage = imread(rightImagePath)
        leftTriangles, rightTriangles = loadTriangles(leftPointFilePath, rightPointFilePath)

        morpher = Morpher(leftImage, leftTriangles, rightImage, rightTriangles)
        morpher.saveVideo(targetVideoPath, 20, 5, True)

        self.assertTrue(os.path.exists(targetVideoPath))

        os.remove(targetVideoPath)

    def test_generateColorVideo(self):

        leftPointFilePath = os.path.join(TestFolder, "points.left.txt")
        rightPointFilePath = os.path.join(TestFolder, "points.right.txt")
        leftImagePath = os.path.join(TestFolder, 'LeftColor.png')
        rightImagePath = os.path.join(TestFolder, 'RightColor.png')
        targetVideoPath = os.path.join(TestFolder, 'ColorMorph.mp4')

        leftImage = imread(leftImagePath)
        rightImage = imread(rightImagePath)
        leftTriangles, rightTriangles = loadTriangles(leftPointFilePath, rightPointFilePath)

        morpher = ColorMorpher(leftImage, leftTriangles, rightImage, rightTriangles)
        morpher.saveVideo(targetVideoPath, 20, 5, True)

        self.assertTrue(os.path.exists(targetVideoPath))

        os.remove(targetVideoPath)

    @classmethod
    def setUpClass(cls):
        cls.support = Support()


class MorphingPerformanceTestSuite(unittest.TestCase, ImageAssertion): # 15 Points

    threshold = 4.

    def test_GrayPerformance(self):

        canContinue = self.support.probePerformance(self.threshold)

        if not canContinue:
            self.fail("Performance is slow.")

        leftPointFilePath = os.path.join(TestFolder, "points.left.txt")
        rightPointFilePath = os.path.join(TestFolder, "points.right.txt")
        leftImagePath = os.path.join(TestFolder, 'LeftGray.png')
        rightImagePath = os.path.join(TestFolder, 'RightGray.png')

        leftImage = imread(leftImagePath)
        rightImage = imread(rightImagePath)
        leftTriangles, rightTriangles = loadTriangles(leftPointFilePath, rightPointFilePath)

        morpher = Morpher(leftImage, leftTriangles, rightImage, rightTriangles)
        average = checkPerformance(morpher)

        with self.subTest(key="Good"):          # 5 Points

            self.assertLessEqual(average, 1.5)

        with self.subTest(key="Better"):        # 5 Points

            self.assertLessEqual(average, 1.)

    def test_ColorPerformance(self):

        canContinue = self.support.probePerformance(self.threshold)

        if not canContinue:
            self.fail("Performance is slow.")

        leftPointFilePath = os.path.join(TestFolder, "points.left.txt")
        rightPointFilePath = os.path.join(TestFolder, "points.right.txt")
        leftImagePath = os.path.join(TestFolder, 'LeftColor.png')
        rightImagePath = os.path.join(TestFolder, 'RightColor.png')

        leftImage = imread(leftImagePath)
        rightImage = imread(rightImagePath)
        leftTriangles, rightTriangles = loadTriangles(leftPointFilePath, rightPointFilePath)

        morpher = ColorMorpher(leftImage, leftTriangles, rightImage, rightTriangles)
        average = checkPerformance(morpher)

        with self.subTest(key="Good"):          # 2.5 Points

            self.assertLessEqual(average, 4.)

        with self.subTest(key="Better"):        # 2.5 Points

            self.assertLessEqual(average, 2.5)

    @classmethod
    def setUpClass(cls):
        cls.support = Support()


class Support:

    def __init__(self):
        filePath = os.path.join(TestFolder, 'Support.npz')
        with np.load(filePath) as dataFile:
            self.vertices = dataFile["vertices"]
            self.smallVertices = dataFile["smallVertices"]
            self.otherVertices = dataFile["otherVertices"]

            self.pointVertices = dataFile["pointVertices"]
            self.samplePoints = dataFile["samplePoints"]

    @staticmethod
    def probePerformance(threshold):
        """
        Runs a quick transformation to determine is the performance should be checked at all or not.
        """
        s = perf_counter()

        leftPointFilePath = os.path.join(TestFolder, "points.left.txt")
        rightPointFilePath = os.path.join(TestFolder, "points.right.txt")
        leftImagePath = os.path.join(TestFolder, 'LeftGray.png')
        rightImagePath = os.path.join(TestFolder, 'RightGray.png')

        leftImage = imread(leftImagePath)
        rightImage = imread(rightImagePath)
        leftTriangles, rightTriangles = loadTriangles(leftPointFilePath, rightPointFilePath)

        morpher = Morpher(leftImage, leftTriangles, rightImage, rightTriangles)
        targetImage = morpher.getImageAtAlpha(0.50)

        e = perf_counter()

        print("Probe Duration = {}".format(e - s))

        return (e - s) <= threshold

if __name__ == '__main__':
    unittest.main()
