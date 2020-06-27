#######################################################
#   Author:     David Dowd
#   email:      ddowd@purdue.edu
#   ID:         ee364e06
#   Date:       04/16/19
#######################################################

import multiprocessing
import os
import sys
import re
import time
from shutil import copyfile

import imageio
import numpy as np
from PIL import Image
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog, QGraphicsScene, QGraphicsView
from PyQt5 import QtGui, QtCore
from scipy.spatial.qhull import Delaunay
import copy

from Morphing import *
from Morphing import Triangle, loadTriangles, Morpher
from MorphingGUI import Ui_MainWindow
from MorphingGUI import *

# Module  level  Variables
#######################################################
DataPath = os.path.expanduser('/Users/xzomb/PycharmProjects/Personal/')

class MorphingApp(QMainWindow, Ui_MainWindow):

    def __init__(self, parent=None):

        super(MorphingApp, self).__init__(parent)
        self.setupUi(self)

        # Defaults on Startup
        self.alphaValue.setReadOnly(1)
        self.alphaValue.setPlaceholderText("0.0")
        self.alphaValue.setEnabled(0)
        self.blendButton.setEnabled(0)
        self.alphaSlider.setTickPosition(2)
        self.alphaSlider.setTickInterval(2)
        self.alphaSlider.setTracking(1)
        self.alphaSlider.setMaximum(20)
        self.alphaSlider.setEnabled(0)
        self.triangleBox.setEnabled(0)
        self.loadStartButton.setEnabled(1)
        self.loadEndButton.setEnabled(1)
        self.resetPointsButton.setEnabled(0)
        self.autoCornerButton.setEnabled(0)
        self.triangleRedSlider.setMinimum(0)
        self.triangleRedSlider.setMaximum(255)
        self.triangleRedSlider.setSingleStep(1)
        self.triangleGreenSlider.setMinimum(0)
        self.triangleGreenSlider.setMaximum(255)
        self.triangleGreenSlider.setSingleStep(1)
        self.triangleBlueSlider.setMinimum(0)
        self.triangleBlueSlider.setMaximum(255)
        self.triangleBlueSlider.setSingleStep(1)
        self.updateTriangleWidget(0)
        self.chosen_left_points = []
        self.chosen_right_points = []
        self.added_left_points = []
        self.added_right_points = []
        self.confirmed_left_points = []
        self.confirmed_right_points = []
        self.confirmed_left_points_history = []   # Logging for CTRL + Y (REDO)
        self.confirmed_right_points_history = []  # Logging for CTRL + Y (REDO)
        self.startingImagePath = ''
        self.endingImagePath = ''
        self.startingTextPath = ''
        self.startingTextCorePath = ''
        self.endingTextPath = ''
        self.endingTextCorePath = ''
        self.startingText = []
        self.endingText = []
        self.leftPNG = 0
        self.rightPNG = 0
        self.leftOn = 0
        self.rightOn = 0
        self.currentWindow = 0
        self.enableDeletion = 0
        self.leftSize = 0
        self.rightSize = 0
        self.persistFlag = 0
        self.resetFlag = 0
        self.triangleUpdate = 0
        self.triangleUpdatePref = 0
        self.leftPolyList = []
        self.rightPolyList = []
        self.leftScalar = 0
        self.rightScalar = 0
        self.leftSize = (0, 0)
        self.rightSize = (0, 0)
        self.leftMinX = 9
        self.leftMaxX = 433
        self.rightMinX = 321
        self.rightMaxX = 745
        self.minY = 38
        self.maxY = 356
        self.transparencySetting = 0  # Flag for user preference on blending alpha layer of .PNG images
        self.blendBoxSetting = 0      # Flag for user preference on full blending the two images
        self.blendList = []           # List used to store the 21 frames of 0.05 alpha increments for full blending
        self.redVal = 0
        self.greenVal = 0
        self.blueVal = 0
        self.resizeFlag = False
        self.changeFlag = False
        self.fullBlendComplete = False

        # Logic
        self.loadStartButton.clicked.connect(self.loadDataLeft)
        self.loadStartButton.clicked.connect(self.displayTriangles)
        self.loadEndButton.clicked.connect(self.loadDataRight)
        self.triangleBox.stateChanged.connect(self.displayTriangles)
        self.transparencyBox.stateChanged.connect(self.transparencyUpdate)
        self.blendButton.clicked.connect(self.blendImages)
        self.blendBox.stateChanged.connect(self.blendBoxUpdate)
        self.alphaSlider.valueChanged.connect(self.updateAlpha)
        self.triangleRedSlider.valueChanged.connect(self.updateRed)
        self.triangleGreenSlider.valueChanged.connect(self.updateGreen)
        self.triangleBlueSlider.valueChanged.connect(self.updateBlue)
        self.resetPointsButton.clicked.connect(self.resetPoints)
        self.autoCornerButton.clicked.connect(self.autoCorner)

    # Macro function to save unnecessary repetitions of the same few lines of code.
    # Essentially refreshes the displayed left and right images of the UI.
    def refreshPaint(self):
        self.changeFlag = True
        self.paintEvent(1)

    # Macro function to save unnecessary repetitions of the same few lines of code.
    # Essentially toggles the triangle widget when necessary.
    def updateTriangleWidget(self, val):
        if val:
            self.triangleRed.setText("<b><font color='red'>Red</font></b>")
            self.triangleGreen.setText("<b><font color='green'>Green</font></b>")
            self.triangleBlue.setText("<b><font color='blue'>Blue</font></b>")
            self.triangleLabel.setEnabled(1)
            self.triangleRed.setEnabled(1)
            self.triangleGreen.setEnabled(1)
            self.triangleBlue.setEnabled(1)
            self.triangleRedSlider.setEnabled(1)
            self.triangleGreenSlider.setEnabled(1)
            self.triangleBlueSlider.setEnabled(1)
        else:
            self.triangleRed.setText("<font color='black'>Red</font>")
            self.triangleGreen.setText("<font color='black'>Green</font>")
            self.triangleBlue.setText("<font color='black'>Blue</font>")
            self.triangleLabel.setEnabled(0)
            self.triangleRed.setEnabled(0)
            self.triangleGreen.setEnabled(0)
            self.triangleBlue.setEnabled(0)
            self.triangleRedSlider.setEnabled(0)
            self.triangleGreenSlider.setEnabled(0)
            self.triangleBlueSlider.setEnabled(0)

    # Self-contained function that checks for the existence of corner points and adds any that are not already present.
    # Can not be invoked while a point is pending (in order to prevent exploits).
    # Written to dynamically work with triangles without any exploits.
    def autoCorner(self):
        # Instead of (0,0) to (x, y), this function uses (1,1) to (x-1, y-1) to avoid crashes.
        # Don't revert this unless the behavior can be remedied.
        tempLeft = [QtCore.QPoint(1, 1), QtCore.QPoint(1, int((self.maxY - self.minY - 1) * self.leftScalar[1])), QtCore.QPoint(int((self.leftMaxX - self.leftMinX - 1) * self.leftScalar[0]), 1), QtCore.QPoint(int((self.leftMaxX - self.leftMinX - 1) * self.leftScalar[0]), int((self.maxY - self.minY - 1) * self.leftScalar[1]))]
        tempRight = [QtCore.QPoint(1, 1), QtCore.QPoint(1, int((self.maxY - self.minY - 1) * self.rightScalar[1])), QtCore.QPoint(int((self.rightMaxX - self.rightMinX - 1) * self.rightScalar[0]), 1), QtCore.QPoint(int((self.rightMaxX - self.rightMinX - 1) * self.rightScalar[0]), int((self.maxY - self.minY - 1) * self.rightScalar[1]))]
        # tempLeft = [QtCore.QPoint(0, 0), QtCore.QPoint(0, int((self.maxY - self.minY) * self.leftScalar[1])), QtCore.QPoint(int((self.leftMaxX - self.leftMinX) * self.leftScalar[0]), 0), QtCore.QPoint(int((self.leftMaxX - self.leftMinX) * self.leftScalar[0]), int((self.maxY - self.minY) * self.leftScalar[1]))]
        # tempRight = [QtCore.QPoint(0, 0), QtCore.QPoint(0, int((self.maxY - self.minY) * self.rightScalar[1])), QtCore.QPoint(int((self.rightMaxX - self.rightMinX) * self.rightScalar[0]), 0), QtCore.QPoint(int((self.rightMaxX - self.rightMinX) * self.rightScalar[0]), int((self.maxY - self.minY) * self.rightScalar[1]))]

        self.triangleBox.setEnabled(1)
        i = 0
        counter = 0
        while i < 4:
            if tempLeft[i] not in self.confirmed_left_points and tempLeft[i] not in self.chosen_left_points:
                counter += 1
                self.confirmed_left_points.append(tempLeft[i])
                self.confirmed_left_points_history.append(tempLeft[i])
                self.confirmed_right_points.append(tempRight[i])
                self.confirmed_right_points_history.append(tempRight[i])

                with open(self.startingTextCorePath, "a") as startingFile:
                    if not self.startingText:  # if self.startingText == []
                        startingFile.write('{:>8}{:>8}'.format(str(format(self.confirmed_left_points[len(self.confirmed_left_points) - 1].x(), ".1f")), str(format(self.confirmed_left_points[len(self.confirmed_left_points) - 1].y(), ".1f"))))
                    else:
                        startingFile.write('\n{:>8}{:>8}'.format(str(format(self.confirmed_left_points[len(self.confirmed_left_points) - 1].x(), ".1f")), str(format(self.confirmed_left_points[len(self.confirmed_left_points) - 1].y(), ".1f"))))
                with open(self.endingTextCorePath, "a") as endingFile:
                    if not self.endingText:  # if self.endingText == []
                        endingFile.write('{:>8}{:>8}'.format(str(format(self.confirmed_right_points[len(self.confirmed_right_points) - 1].x(), ".1f")), str(format(self.confirmed_right_points[len(self.confirmed_right_points) - 1].y(), ".1f"))))
                    else:
                        endingFile.write('\n{:>8}{:>8}'.format(str(format(self.confirmed_right_points[len(self.confirmed_right_points) - 1].x(), ".1f")), str(format(self.confirmed_right_points[len(self.confirmed_right_points) - 1].y(), ".1f"))))
                self.startingText.append((self.confirmed_left_points[len(self.confirmed_left_points) - 1].x(), self.confirmed_left_points[len(self.confirmed_left_points) - 1].x()))
                self.endingText.append((self.confirmed_right_points[len(self.confirmed_right_points) - 1].x(), self.confirmed_right_points[len(self.confirmed_right_points) - 1].x()))
                self.refreshPaint()
            i += 1

        if counter:
            if counter == 1:
                self.notificationLine.setText(" Successfully added " + str(counter) + " new corner point.")
            else:
                self.notificationLine.setText(" Successfully added " + str(counter) + " new corner points.")
        else:
            self.notificationLine.setText(" Failed to add any new corner points.")

        self.currentWindow = 0
        self.enableDeletion = 0
        self.persistFlag = 2
        self.displayTriangles()
        self.resetPointsButton.setEnabled(1)

    # Function that wipes the slate clean, erasing all placed points from the GUI and relevant files.
    # Similar to autoCorner, this has been written to dynamically work with triangles without any exploits.
    def resetPoints(self):
        if self.triangleBox.isChecked():
            self.triangleUpdatePref = 1
        else:
            self.triangleUpdatePref = 0
        self.resetPointsButton.setEnabled(0)
        self.triangleBox.setEnabled(0)
        self.triangleBox.setChecked(0)
        self.refreshPaint()
        self.resetFlag = 1
        self.startingText = []
        self.endingText = []
        self.added_left_points = []
        self.added_right_points = []
        self.confirmed_left_points = []
        self.confirmed_right_points = []
        self.chosen_left_points = []
        self.chosen_right_points = []

        if os.path.isfile(self.startingTextCorePath):
            os.remove(self.startingTextCorePath)

        if os.path.isfile(self.endingTextCorePath):
            os.remove(self.endingTextCorePath)

        if self.leftOn and self.rightOn:
            self.enableDeletion = 0
            self.currentWindow = 1
            self.persistFlag = 0
            self.refreshPaint()
            self.currentWindow = 0

        self.notificationLine.setText(" Successfully reset points.")

    # Function that handles the rendering of points and triangles onto the GUI when manually called.
    # Dynamically handles changes in point and polygon lists to be compatible with resetPoints, autoCorner, etc.
    def paintEvent(self, paint_event):
        if self.changeFlag:
            leftPic = QtGui.QPixmap(self.startingImagePath)
            rightPic = QtGui.QPixmap(self.endingImagePath)
            pen = QtGui.QPen()
            pen.setWidth(7)
            leftpainter = QtGui.QPainter(leftPic)
            rightpainter = QtGui.QPainter(rightPic)

            if self.triangleUpdate == 1:
                pen.setColor(QtGui.QColor(self.redVal, self.greenVal, self.blueVal, 255))
                leftpainter.setPen(pen)
                for x in self.leftPolyList:
                    leftpainter.drawPolygon(x, 3)

                pen.setColor(QtGui.QColor(self.redVal, self.greenVal, self.blueVal, 255))
                rightpainter.setPen(pen)
                for x in self.rightPolyList:
                    rightpainter.drawPolygon(x, 3)

            leftpainter.setBrush(QtGui.QColor(255, 0, 0, 255))
            for x in self.chosen_left_points:
                leftpainter.drawEllipse(x, 7, 7)

            leftpainter.setBrush(QtGui.QColor(0, 255, 0, 255))
            for x in self.added_left_points:
                leftpainter.drawEllipse(x, 7, 7)

            leftpainter.setBrush(QtGui.QColor(0, 0, 255, 255))
            for x in self.confirmed_left_points:
                leftpainter.drawEllipse(x, 7, 7)

            self.startingImage.setPixmap(leftPic)
            leftpainter.end()

            rightpainter.setBrush(QtGui.QColor(255, 0, 0, 255))
            for x in self.chosen_right_points:
                rightpainter.drawEllipse(x, 7, 7)

            rightpainter.setBrush(QtGui.QColor(0, 255, 0, 255))
            for x in self.added_right_points:
                rightpainter.drawEllipse(x, 7, 7)

            rightpainter.setBrush(QtGui.QColor(0, 0, 255, 255))
            for x in self.confirmed_right_points:
                rightpainter.drawEllipse(x, 7, 7)

            rightpainter.end()
            self.endingImage.setPixmap(rightPic)
            self.changeFlag = False

    # Event handler for keystrokes
    # CTRL + Z will either:
    #       1) Undo the most recently placed temporary (green) point [NOT "the last placed temporary point"], or
    #       2) Undo the most recent confirmed (blue) point pair
    #           a) If this would cause a change in triangle display, the user's preference is remembered
    # TODO: CTRL + Y
    # Backspace will only delete the last placed temporary point, if there is one to delete.
    #       a) It can not be invoked more than one time in succession, and
    #       b) It has no effect on confirmed (blue) points
    def keyPressEvent(self, key_event):
        # Undo
        if type(key_event) == QtGui.QKeyEvent and key_event.modifiers() == QtCore.Qt.ControlModifier and key_event.key() == QtCore.Qt.Key_Z:
            undoFlag = 0
            if self.leftOn and self.rightOn:
                if self.enableDeletion == 1:
                    if self.currentWindow == 0 and self.added_left_points != []:
                        self.added_right_points.pop(len(self.added_right_points)-1)
                        self.currentWindow = 1
                        self.persistFlag = 0
                        self.refreshPaint()
                        undoFlag = 1
                    elif self.currentWindow == 1:
                        self.added_left_points.pop(len(self.added_left_points) - 1)
                        self.currentWindow = 0
                        self.enableDeletion = 0
                        self.persistFlag = 0
                        self.refreshPaint()
                        self.autoCornerButton.setEnabled(1)
                        undoFlag = 1
                    elif self.confirmed_left_points != [] and self.confirmed_right_points != []:
                        self.confirmed_left_points.pop(len(self.confirmed_left_points) - 1)
                        self.confirmed_right_points.pop(len(self.confirmed_right_points) - 1)
                        data1 = open(self.startingTextCorePath, 'r').readlines()
                        del data1[-1]
                        if data1:
                            data1[-1] = data1[-1][0:int(len(data1[-1]) - 1)]
                            open(self.startingTextCorePath, 'w').writelines(data1)
                        else:
                            os.remove(self.startingTextCorePath)
                            self.startingText = []
                        data2 = open(self.endingTextCorePath, 'r').readlines()
                        del data2[-1]
                        if data2:
                            data2[-1] = data2[-1][0:int(len(data2[-1]) - 1)]
                            open(self.endingTextCorePath, 'w').writelines(data2)
                        else:
                            os.remove(self.endingTextCorePath)
                            self.endingText = []
                        self.currentWindow = 0
                        self.enableDeletion = 0
                        self.persistFlag = 0
                        if len(self.confirmed_right_points) >= 3:
                            self.displayTriangles()
                        else:
                            if self.triangleBox.isChecked():
                                self.triangleUpdatePref = 1
                            else:
                                self.triangleUpdatePref = 0
                            self.triangleBox.setEnabled(0)
                            self.triangleBox.setChecked(0)
                            self.displayTriangles()
                            if len(self.confirmed_right_points) == 0:
                                self.resetPointsButton.setEnabled(0)
                        self.refreshPaint()
                        undoFlag = 1
                else:
                    if self.confirmed_left_points != [] and self.confirmed_right_points != []:
                        self.confirmed_left_points.pop(len(self.confirmed_left_points) - 1)
                        self.confirmed_right_points.pop(len(self.confirmed_right_points) - 1)
                        data1 = open(self.startingTextCorePath, 'r').readlines()
                        del data1[-1]
                        if data1:
                            data1[-1] = data1[-1][0:int(len(data1[-1]) - 1)]
                            open(self.startingTextCorePath, 'w').writelines(data1)
                        else:
                            os.remove(self.startingTextCorePath)
                            self.startingText = []
                        data2 = open(self.endingTextCorePath, 'r').readlines()
                        del data2[-1]
                        if data2:
                            data2[-1] = data2[-1][0:int(len(data2[-1]) - 1)]
                            open(self.endingTextCorePath, 'w').writelines(data2)
                        else:
                            os.remove(self.endingTextCorePath)
                            self.endingText = []
                        self.currentWindow = 0
                        self.enableDeletion = 0
                        self.persistFlag = 0

                        if len(self.confirmed_right_points) >= 3:
                            self.displayTriangles()
                        else:
                            if self.triangleBox.isChecked():
                                self.triangleUpdatePref = 1
                            else:
                                self.triangleUpdatePref = 0
                            self.triangleBox.setEnabled(0)
                            self.triangleBox.setChecked(0)
                            self.displayTriangles()
                            if len(self.confirmed_right_points) == 0:
                                self.resetPointsButton.setEnabled(0)
                        self.refreshPaint()
                        undoFlag = 1
            if undoFlag == 0:
                self.notificationLine.setText(" Can't undo!")

        # Redo
        elif type(key_event) == QtGui.QKeyEvent and key_event.modifiers() == QtCore.Qt.ControlModifier and key_event.key() == QtCore.Qt.Key_Y:
            self.notificationLine.setText(" This hasn't been implemented yet. ;)")
        # Delete recent temp
        elif type(key_event) == QtGui.QKeyEvent and key_event.key() == QtCore.Qt.Key_Backspace:
            if self.leftOn and self.rightOn and self.enableDeletion == 1:
                if self.currentWindow == 0 and self.added_left_points != []:
                    self.added_right_points.pop(len(self.added_right_points)-1)
                    self.enableDeletion = 0
                    self.currentWindow = 1
                    self.persistFlag = 0
                    self.refreshPaint()
                    self.notificationLine.setText(" Successfully deleted recent temporary point.")
                elif self.currentWindow == 1:
                    self.added_left_points.pop(len(self.added_left_points)-1)
                    self.currentWindow = 0
                    self.enableDeletion = 0
                    self.persistFlag = 0
                    self.refreshPaint()
                    self.autoCornerButton.setEnabled(1)
                    self.notificationLine.setText(" Successfully deleted recent temporary point.")

    # Function override of the window resize event. Fairly lightweight.
    # Currently just recalculates the necessary scalar values to keep image displays and point placements accurate.
    # (At this time, I am choosing to keep a scalar for each image in hopes of supporting different ratios/sizes)
    def resizeEvent(self, event):
        self.leftScalar = (self.leftSize[0] / (424 + int((self.width() - 878) / 2)), self.leftSize[1] / (self.height() - 458))
        self.rightScalar = (self.rightSize[0] / (424 + int((self.width() - 878) / 2)), self.rightSize[1] / (self.height() - 458))
        self.leftMaxX = self.leftMinX + 424 + int((self.width() - 878) / 2)
        self.rightMinX = self.leftMaxX + 12
        self.rightMaxX = self.rightMinX + 424 + int((self.width() - 878) / 2)
        self.maxY = self.minY + self.height() - 458  # "self.minY + 225 + (self.height() - 590)" or "self.minY + 318 + (self.height() - 776)"
        self.resizeFlag = True

    # Function that handles GUI and file behavior when the mouse is clicked.
    def mousePressEvent(self, cursor_event):
        if self.leftOn and self.rightOn:
            # Check if 3 or more points exist for two corresponding images so that triangles may be displayed
            if (len(self.chosen_left_points) + len(self.confirmed_left_points)) == (len(self.chosen_right_points) + len(self.confirmed_right_points)):
                if (len(self.chosen_left_points) + len(self.confirmed_left_points)) >= 3:
                    if (len(self.chosen_right_points) + len(self.confirmed_right_points)) >= 3:
                        self.triangleBox.setEnabled(1)
                        if self.triangleUpdatePref == 1:
                            self.triangleUpdate = 1
                            self.triangleBox.setChecked(1)
                            self.refreshPaint()
            self.leftMaxX = self.leftMinX + 424 + int((self.width() - 878) / 2)
            self.rightMinX = self.leftMaxX + 12
            self.rightMaxX = self.rightMinX + 424 + int((self.width() - 878) / 2)
            self.maxY = self.minY + self.height() - 458  # "self.minY + 225 + (self.height() - 590)" or "self.minY + 318 + (self.height() - 776)"
            if self.currentWindow == 0:
                if not (self.rightMinX < cursor_event.pos().x() < self.rightMaxX and self.minY < cursor_event.pos().y() < self.maxY) and self.added_right_points != [] and self.persistFlag == 2:
                    throwawayLeft = self.added_left_points.pop(len(self.added_left_points)-1)
                    throwawayRight = self.added_right_points.pop(len(self.added_right_points)-1)
                    self.confirmed_left_points.append(throwawayLeft)
                    self.confirmed_left_points_history.append(throwawayLeft)
                    self.confirmed_right_points.append(throwawayRight)
                    self.confirmed_right_points_history.append(throwawayRight)
                    with open(self.startingTextCorePath, "a") as startingFile:
                        if not self.startingText:
                            startingFile.write('{:>8}{:>8}'.format(str(format(self.confirmed_left_points[len(self.confirmed_left_points)-1].x(), ".1f")), str(format(self.confirmed_left_points[len(self.confirmed_left_points)-1].y(), ".1f"))))
                        else:
                            startingFile.write('\n{:>8}{:>8}'.format(str(format(self.confirmed_left_points[len(self.confirmed_left_points)-1].x(), ".1f")), str(format(self.confirmed_left_points[len(self.confirmed_left_points)-1].y(), ".1f"))))
                    with open(self.endingTextCorePath, "a") as endingFile:
                        if not self.endingText:
                            endingFile.write('{:>8}{:>8}'.format(str(format(self.confirmed_right_points[len(self.confirmed_right_points)-1].x(), ".1f")), str(format(self.confirmed_right_points[len(self.confirmed_right_points)-1].y(), ".1f"))))
                        else:
                            endingFile.write('\n{:>8}{:>8}'.format(str(format(self.confirmed_right_points[len(self.confirmed_right_points)-1].x(), ".1f")), str(format(self.confirmed_right_points[len(self.confirmed_right_points)-1].y(), ".1f"))))
                    self.startingText.append((self.confirmed_left_points[len(self.confirmed_left_points)-1].x(), self.confirmed_left_points[len(self.confirmed_left_points)-1].x()))
                    self.endingText.append((self.confirmed_right_points[len(self.confirmed_right_points)-1].x(), self.confirmed_right_points[len(self.confirmed_right_points)-1].x()))
                    self.persistFlag = 0
                    self.refreshPaint()
                    self.displayTriangles()
                    self.autoCornerButton.setEnabled(1)
                    self.resetPointsButton.setEnabled(1)
                    self.notificationLine.setText(" Successfully confirmed set of added points.")
                if self.leftMinX < cursor_event.pos().x() < self.leftMaxX and self.minY < cursor_event.pos().y() < self.maxY:
                    leftCoord = QtCore.QPoint(int((cursor_event.pos().x()-self.leftMinX)*self.leftScalar[0]), int((cursor_event.pos().y()-self.minY)*self.leftScalar[1]))
                    self.added_left_points.append(leftCoord)
                    self.refreshPaint()
                    self.currentWindow = 1
                    self.persistFlag = 0
                    self.enableDeletion = 1
                    self.autoCornerButton.setEnabled(0)
                    self.notificationLine.setText(" Successfully added left temporary point.")
            elif self.currentWindow == 1:
                if self.rightMinX < cursor_event.pos().x() < self.rightMaxX and self.minY < cursor_event.pos().y() < self.maxY:
                    rightCoord = QtCore.QPoint(int((cursor_event.pos().x()-self.rightMinX)*self.rightScalar[0]), int((cursor_event.pos().y()-self.minY)*self.rightScalar[1]))
                    self.added_right_points.append(rightCoord)
                    self.refreshPaint()
                    self.currentWindow = 0
                    self.enableDeletion = 1
                    self.persistFlag = 2
                    self.notificationLine.setText(" Successfully added right temporary point.")
            if (len(self.chosen_left_points) + len(self.confirmed_left_points)) == (len(self.chosen_right_points) + len(self.confirmed_right_points)):
                if (len(self.chosen_left_points) + len(self.confirmed_left_points)) >= 3:
                    if (len(self.chosen_right_points) + len(self.confirmed_right_points)) >= 3:
                        self.triangleBox.setEnabled(1)
                        if self.triangleUpdatePref == 1:
                            self.triangleUpdate = 1
                            self.triangleBox.setChecked(1)
                            self.refreshPaint()

    # Very simple function for updating user preference for blending transparency in images
    # (This is disabled by default, as transparency is often unused and reduces performance.)
    def transparencyUpdate(self):
        self.transparencySetting = int(self.transparencyBox.isChecked())
        if self.transparencyBox.isChecked():
            self.notificationLine.setText(" Successfully enabled transparency layer.")
        else:
            self.notificationLine.setText(" Successfully disabled transparency layer.")

    # Another simple function for updating user preference regarding 'full blending'
    # Full blending is defined as morphing every 0.05 alpha increment of the two images.
    # The alpha slider than becomes an interactive display, showing each blend in realtime.
    # (Naturally, this is disabled by default, as full blending takes 20 times as long to run)
    def blendBoxUpdate(self):
        self.blendBoxSetting = int(self.blendBox.isChecked())
        if self.blendBox.isChecked():
            self.notificationLine.setText(" Successfully enabled full blending.")
        else:
            self.notificationLine.setText(" Successfully disabled full blending.")

    # Function that dynamically updates the list of triangles for the image pair provided, when manually invoked.
    # When a process wants to see triangles update properly, THIS is what needs to be called (not self.triangleUpdate).
    def displayTriangles(self):
        if self.triangleBox.isEnabled():
            if self.triangleBox.isChecked() or self.triangleUpdatePref:
                self.triangleBox.checkState = 2
                if os.path.exists(self.startingTextCorePath) and os.path.exists(self.endingTextCorePath):
                    self.updateTriangleWidget(1)
                    leftList = []
                    rightList = []

                    with open(self.startingTextCorePath, "r") as leftFile:
                        for j in leftFile:
                            leftList.append(j.split())
                    with open(self.endingTextCorePath, "r") as rightFile:
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

                    self.leftPolyList = []
                    self.rightPolyList = []
                    for x in leftTriList:
                        temp = QtGui.QPolygon((QtCore.QPoint(int(x.vertices[0][0]), int(x.vertices[0][1])), QtCore.QPoint(int(x.vertices[1][0]), int(x.vertices[1][1])), QtCore.QPoint(int(x.vertices[2][0]), int(x.vertices[2][1])), QtCore.QPoint(int(x.vertices[0][0]), int(x.vertices[0][1]))))
                        self.leftPolyList.append(temp)
                    for y in rightTriList:
                        temp = QtGui.QPolygon((QtCore.QPoint(int(y.vertices[0][0]), int(y.vertices[0][1])), QtCore.QPoint(int(y.vertices[1][0]), int(y.vertices[1][1])), QtCore.QPoint(int(y.vertices[2][0]), int(y.vertices[2][1])), QtCore.QPoint(int(y.vertices[0][0]), int(y.vertices[0][1]))))
                        self.rightPolyList.append(temp)
                    self.triangleUpdate = 1
                    self.refreshPaint()
            else:
                self.updateTriangleWidget(0)
                self.triangleUpdate = 0
                self.refreshPaint()
        else:
            self.updateTriangleWidget(0)
            self.triangleUpdate = 0
            self.refreshPaint()

    # Simple function that rounds the desired alpha value to the nearest 0.05 increment.
    def updateAlpha(self):
        value = format(round((self.alphaSlider.value() / 20) / 0.05) * 0.05, ".2f")
        self.notificationLine.setText(" Alpha value changed from " + self.alphaValue.text() + " to " + str(value) + ".")
        self.alphaValue.setText(str(value))
        if self.blendBoxSetting and self.fullBlendComplete:
            temp = self.blendList[int(float(self.alphaValue.text()) / 0.05)]
            if len(temp.shape) == 2:
                blendImage = QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], QtGui.QImage.Format_Grayscale8)
            elif temp.shape[2] == 3:
                blendImage = QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], QtGui.QImage.Format_RGB888)
            elif temp.shape[2] == 4:
                blendImage = QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], QtGui.QImage.Format_RGBA8888)
            else:
                print("Generic catching error: Something went wrong when loading the image.")
            self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(blendImage))

    # Red/Green/Blue slider functions for the triangle widget in order to select custom colors
    def updateRed(self):
        self.redVal = self.triangleRedSlider.value()
        self.notificationLine.setText(" Red value set to " + str(self.redVal) + ".")
        self.refreshPaint()

    def updateGreen(self):
        self.greenVal = self.triangleGreenSlider.value()
        self.notificationLine.setText(" Green value set to " + str(self.greenVal) + ".")
        self.refreshPaint()

    def updateBlue(self):
        self.blueVal = self.triangleBlueSlider.value()
        self.notificationLine.setText(" Blue value set to " + str(self.blueVal) + ".")
        self.refreshPaint()

    # Function that handles behavior when the user wishes to blend the two calibrated images.
    # Currently designed to handle:
    #     > 8-Bit Grayscale                            (QtGui.QImage.Format_Grayscale8)
    #     > 24-Bit Color .JPG / .PNG                   (QtGui.QImage.Format_RGB888)
    #     > 24-Bit Color, 8-Bit Transparency .PNG      (QtGui.QImage.Format_RGBA8888)
    # TODO: Color Blending is not 100% accurate.
    #       Current thoughts: Shouldn't have anything to do with the 8 bit depth.. is this an interpolation issue?
    #       It almost feels like data is just... missing. So how do I determine what is missing???
    # TODO: Aspect Ratio is a big issue as well. Frames are 4:3, so any images that aren't 4:3 (e.g. 1:1) are warped.     [REMEDIED WITH GUI OVERHAUL      6/17/20]
    # TODO: As a bonus, this takes more than 4x as long as grayscale. Hooray!                                             [REMEDIED WITH MULTI-PROCESSING  6/02/20]
    def blendImages(self):
        self.blendButton.setEnabled(0)
        triangleTuple = loadTriangles(self.startingTextCorePath, self.endingTextCorePath)
        left = imageio.imread(self.startingImagePath)
        right = imageio.imread(self.endingImagePath)
        leftARR = np.asarray(left)
        rightARR = np.asarray(right)
        self.notificationLine.setText(" Beginning morph.")
        if len(left.shape) < 3 and len(right.shape) < 3:  # if grayscale
            self.notificationLine.setText(" Beginning grayscale morph.")
            grayScale = Morpher(leftARR, triangleTuple[0], rightARR, triangleTuple[1])
            backupGrayScale = copy.deepcopy(grayScale)
            start_time = time.time()
            if self.blendBoxSetting:
                self.blendList = []
                x = 0
                while x < 21:  # Every alpha frame: 0.00, 0.05, 0.10 ... 0.90, 0.95, 1.00
                    self.blendList.append(grayScale.getImageAtAlpha(x * 0.05, 0))
                    grayScale = copy.deepcopy(backupGrayScale)
                    x += 1
                self.fullBlendComplete = True
                temp = self.blendList[int(float(self.alphaValue.text()) / 0.05)]
                blendImage = QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], QtGui.QImage.Format_Grayscale8)
            else:
                blendARR = grayScale.getImageAtAlpha(float(self.alphaValue.text()), 0)
                blendImage = QtGui.QImage(blendARR.data, blendARR.shape[1], blendARR.shape[0], QtGui.QImage.Format_Grayscale8)
            self.notificationLine.setText(" Morph took " + "{:.3f}".format(time.time() - start_time) + " seconds.\n")
        elif not self.leftPNG or not self.rightPNG or not self.transparencySetting or (len(left.shape) == 3 and len(right.shape) == 3):  # if color, no alpha (.JPG)
            self.notificationLine.setText(" Beginning RGB (.jpg) morph.")
            leftColorValueR = []
            leftColorValueG = []
            leftColorValueB = []
            rightColorValueR = []
            rightColorValueG = []
            rightColorValueB = []
            for x in leftARR:
                for y in x:
                    leftColorValueR.append(y[0])
                    leftColorValueG.append(y[1])
                    leftColorValueB.append(y[2])
            for x in rightARR:
                for y in x:
                    rightColorValueR.append(y[0])
                    rightColorValueG.append(y[1])
                    rightColorValueB.append(y[2])

            leftColorValueR = np.array(leftColorValueR, np.uint8).reshape(self.leftSize[1], self.leftSize[0])
            leftColorValueG = np.array(leftColorValueG, np.uint8).reshape(self.leftSize[1], self.leftSize[0])
            leftColorValueB = np.array(leftColorValueB, np.uint8).reshape(self.leftSize[1], self.leftSize[0])
            rightColorValueR = np.array(rightColorValueR, np.uint8).reshape(self.rightSize[1], self.rightSize[0])
            rightColorValueG = np.array(rightColorValueG, np.uint8).reshape(self.rightSize[1], self.rightSize[0])
            rightColorValueB = np.array(rightColorValueB, np.uint8).reshape(self.rightSize[1], self.rightSize[0])

            colorScaleR = Morpher(leftColorValueR, triangleTuple[0], rightColorValueR, triangleTuple[1])
            colorScaleG = Morpher(leftColorValueG, triangleTuple[0], rightColorValueG, triangleTuple[1])
            colorScaleB = Morpher(leftColorValueB, triangleTuple[0], rightColorValueB, triangleTuple[1])
            backupColorScaleR = copy.deepcopy(colorScaleR)
            backupColorScaleG = copy.deepcopy(colorScaleG)
            backupColorScaleB = copy.deepcopy(colorScaleB)

            start_time = time.time()
            if self.blendBoxSetting:
                self.blendList = []
                counter = 0
                while counter < 21:  # Every alpha frame: 0.00, 0.05, 0.10 ... 0.90, 0.95, 1.00
                    pool = multiprocessing.Pool(4)
                    results = [pool.apply_async(colorScaleR.getImageAtAlpha, (counter * 0.05, 1)),
                               pool.apply_async(colorScaleG.getImageAtAlpha, (counter * 0.05, 1)),
                               pool.apply_async(colorScaleB.getImageAtAlpha, (counter * 0.05, 1))]
                    blendR = results[0].get()
                    blendG = results[1].get()
                    blendB = results[2].get()
                    pool.close()
                    pool.terminate()
                    pool.join()
                    xCount = 0
                    blendARR = []
                    for x in leftARR:
                        yCount = 0
                        for y in x:
                            blendARR.append([blendR[xCount][yCount], blendG[xCount][yCount], blendB[xCount][yCount]])
                            yCount = yCount + 1
                        xCount = xCount + 1
                    self.blendList.append(np.array(blendARR, np.uint8).reshape(self.leftSize[1], self.leftSize[0], 3))
                    colorScaleR = copy.deepcopy(backupColorScaleR)
                    colorScaleG = copy.deepcopy(backupColorScaleG)
                    colorScaleB = copy.deepcopy(backupColorScaleB)
                    counter += 1
                self.fullBlendComplete = True
                temp = self.blendList[int(float(self.alphaValue.text()) / 0.05)]
                blendImage = QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], QtGui.QImage.Format_RGB888)
                self.notificationLine.setText(" RGB morph took " + "{:.3f}".format(time.time() - start_time) + " seconds.\n")
            else:
                pool = multiprocessing.Pool(4)
                results = [pool.apply_async(colorScaleR.getImageAtAlpha, (float(self.alphaValue.text()), 1)),
                           pool.apply_async(colorScaleG.getImageAtAlpha, (float(self.alphaValue.text()), 1)),
                           pool.apply_async(colorScaleB.getImageAtAlpha, (float(self.alphaValue.text()), 1))]
                blendR = results[0].get()
                blendG = results[1].get()
                blendB = results[2].get()
                pool.close()
                pool.terminate()
                pool.join()
                self.notificationLine.setText(" RGB morph took " + "{:.3f}".format(time.time() - start_time) + " seconds.\n")

                xCount = 0
                blendARR = []
                for x in leftARR:
                    yCount = 0
                    for y in x:
                        blendARR.append([blendR[xCount][yCount], blendG[xCount][yCount], blendB[xCount][yCount]])
                        yCount = yCount + 1
                    xCount = xCount + 1
                blendARR = np.array(blendARR, np.uint8).reshape(self.leftSize[1], self.leftSize[0], 3)
                blendImage = QtGui.QImage(blendARR.data, blendARR.shape[1], blendARR.shape[0], QtGui.QImage.Format_RGB888)
        elif self.leftPNG and self.rightPNG and self.transparencySetting and len(left.shape) == 4 and len(right.shape) == 4:   # if color, alpha (.PNG)
            self.notificationLine.setText(" Beginning RGBA (.png) morph.")
            leftColorValueR = []
            leftColorValueG = []
            leftColorValueB = []
            leftColorValueA = []
            rightColorValueR = []
            rightColorValueG = []
            rightColorValueB = []
            rightColorValueA = []
            for x in leftARR:
                for y in x:
                    leftColorValueR.append(y[0])
                    leftColorValueG.append(y[1])
                    leftColorValueB.append(y[2])
                    leftColorValueA.append(y[3])
            for x in rightARR:
                for y in x:
                    rightColorValueR.append(y[0])
                    rightColorValueG.append(y[1])
                    rightColorValueB.append(y[2])
                    rightColorValueA.append(y[3])

            leftColorValueR = np.array(leftColorValueR, np.uint8).reshape(self.leftSize[1], self.leftSize[0])
            leftColorValueG = np.array(leftColorValueG, np.uint8).reshape(self.leftSize[1], self.leftSize[0])
            leftColorValueB = np.array(leftColorValueB, np.uint8).reshape(self.leftSize[1], self.leftSize[0])
            leftColorValueA = np.array(leftColorValueA, np.uint8).reshape(self.leftSize[1], self.leftSize[0])
            rightColorValueR = np.array(rightColorValueR, np.uint8).reshape(self.rightSize[1], self.rightSize[0])
            rightColorValueG = np.array(rightColorValueG, np.uint8).reshape(self.rightSize[1], self.rightSize[0])
            rightColorValueB = np.array(rightColorValueB, np.uint8).reshape(self.rightSize[1], self.rightSize[0])
            rightColorValueA = np.array(rightColorValueA, np.uint8).reshape(self.rightSize[1], self.rightSize[0])

            colorScaleR = Morpher(leftColorValueR, triangleTuple[0], rightColorValueR, triangleTuple[1])
            colorScaleG = Morpher(leftColorValueG, triangleTuple[0], rightColorValueG, triangleTuple[1])
            colorScaleB = Morpher(leftColorValueB, triangleTuple[0], rightColorValueB, triangleTuple[1])
            colorScaleA = Morpher(leftColorValueA, triangleTuple[0], rightColorValueA, triangleTuple[1])
            backupColorScaleR = copy.deepcopy(colorScaleR)
            backupColorScaleG = copy.deepcopy(colorScaleG)
            backupColorScaleB = copy.deepcopy(colorScaleB)
            backupColorScaleA = copy.deepcopy(colorScaleA)

            start_time = time.time()
            if self.blendBoxSetting:
                self.blendList = []
                counter = 0
                while counter < 21:  # Every alpha frame: 0.00, 0.05, 0.10 ... 0.90, 0.95, 1.00
                    pool = multiprocessing.Pool(4)
                    results = [pool.apply_async(colorScaleR.getImageAtAlpha, (counter * 0.05, 1)),
                               pool.apply_async(colorScaleG.getImageAtAlpha, (counter * 0.05, 1)),
                               pool.apply_async(colorScaleB.getImageAtAlpha, (counter * 0.05, 1)),
                               pool.apply_async(colorScaleA.getImageAtAlpha, (counter * 0.05, 1))]
                    blendR = results[0].get()
                    blendG = results[1].get()
                    blendB = results[2].get()
                    blendA = results[3].get()
                    pool.close()
                    pool.terminate()
                    pool.join()

                    xCount = 0
                    blendARR = []
                    for x in leftARR:
                        yCount = 0
                        for y in x:
                            blendARR.append([blendR[xCount][yCount], blendG[xCount][yCount], blendB[xCount][yCount], blendA[xCount][yCount]])
                            yCount = yCount + 1
                        xCount = xCount + 1
                    self.blendList.append(np.array(blendARR, np.uint8).reshape(self.leftSize[1], self.leftSize[0], 4))
                    colorScaleR = copy.deepcopy(backupColorScaleR)
                    colorScaleG = copy.deepcopy(backupColorScaleG)
                    colorScaleB = copy.deepcopy(backupColorScaleB)
                    colorScaleA = copy.deepcopy(backupColorScaleA)
                    counter += 1
                self.fullBlendComplete = True
                temp = self.blendList[int(float(self.alphaValue.text()) / 0.05)]
                blendImage = QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], QtGui.QImage.Format_RGBA8888)
                self.notificationLine.setText(" RGBA morph took " + "{:.3f}".format(time.time() - start_time) + " seconds.\n")
            else:
                pool = multiprocessing.Pool(4)
                results = [pool.apply_async(colorScaleR.getImageAtAlpha, (float(self.alphaValue.text()), 1)),
                           pool.apply_async(colorScaleG.getImageAtAlpha, (float(self.alphaValue.text()), 1)),
                           pool.apply_async(colorScaleB.getImageAtAlpha, (float(self.alphaValue.text()), 1)),
                           pool.apply_async(colorScaleA.getImageAtAlpha, (float(self.alphaValue.text()), 1))]
                blendR = results[0].get()
                blendG = results[1].get()
                blendB = results[2].get()
                blendA = results[3].get()
                pool.close()
                pool.terminate()
                pool.join()
                self.notificationLine.setText(" RGBA morph took " + "{:.3f}".format(time.time() - start_time) + " seconds.\n")

                xCount = 0
                blendARR = []
                for x in leftARR:
                    yCount = 0
                    for y in x:
                        blendARR.append([blendR[xCount][yCount], blendG[xCount][yCount], blendB[xCount][yCount], blendA[xCount][yCount]])
                        yCount = yCount + 1
                    xCount = xCount + 1
                blendARR = np.array(blendARR, np.uint8).reshape(self.leftSize[1], self.leftSize[0], 4)
                blendImage = QtGui.QImage(blendARR.data, blendARR.shape[1], blendARR.shape[0], QtGui.QImage.Format_RGBA8888)
        else:
            self.notificationLine.setText(" Generic Catching Error: Check image file types..")
        self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(blendImage))
        self.blendingImage.setScaledContents(1)
        self.blendButton.setEnabled(1)

    def loadDataLeft(self):
        filePath, _ = QFileDialog.getOpenFileName(self, caption='Open Starting Image File ...', filter="Images (*.png *.jpg)")
        if not filePath:
            return

        self.notificationLine.setText(" Left image loaded.")
        if self.triangleBox.isChecked():
            self.triangleUpdatePref = 1
        else:
            self.triangleUpdatePref = 0
        self.fullBlendComplete = False
        self.triangleBox.setEnabled(0)
        self.triangleBox.setChecked(0)
        self.displayTriangles()
        self.refreshPaint()

        if self.leftOn == 0:
            self.leftOn = 1
        self.leftPixmap = QtGui.QPixmap(filePath)
        self.startingImage.setPixmap(self.leftPixmap)
        self.startingImage.setScaledContents(1)
        self.leftSize = (imageio.imread(filePath).shape[1], imageio.imread(filePath).shape[0])
        self.leftScalar = (self.leftSize[0] / (424 + int((self.width() - 878) / 2)), self.leftSize[1] / (self.height() - 458))

        self.startingImagePath = filePath
        self.startingTextPath = filePath + '.txt'

        # Obtain file's name, removing path and extension
        # Example: C:/Desktop/StartGray1.jpg => StartGray1
        leftFileRegex = re.search('(?<=[/])[^/]+(?=[.])', filePath)
        leftTypeRegex = re.search('.png$', filePath)

        if leftTypeRegex is None:
            self.leftPNG = 0
        elif leftTypeRegex.group() == '.png':
            self.leftPNG = 1
        else:
            self.leftPNG = 0

        # Now assign file's name to desired path for information storage (appending .txt at the end)
        self.startingTextCorePath = 'C:/Users/xzomb/PycharmProjects/Personal/Morphing/Images_Points/' + leftFileRegex.group() + '.txt'

        # If there is already a text file at the location of the selected image, the program assumes that it is what
        # the user intends to start with and moves it to the desired path for future manipulation.
        # Otherwise, the program creates an empty file instead.
        if os.path.isfile(self.startingTextPath):
            copyfile(self.startingTextPath, self.startingTextCorePath)
        else:
            open(self.startingTextCorePath, 'a').close()

        self.startingText = []
        self.added_left_points = []
        self.added_right_points = []
        self.confirmed_left_points = []
        self.confirmed_left_points_history = []
        self.confirmed_right_points = []
        self.confirmed_right_points_history = []
        self.chosen_left_points = []

        if os.path.isfile(self.startingTextCorePath):
            with open(self.startingTextCorePath, "r") as leftFile:
                for x in leftFile:
                    self.startingText.append(x.split())
                    self.chosen_left_points.append(QtCore.QPoint(int(float(x.split()[0])), int(float(x.split()[1]))))
        elif os.path.isfile(self.startingTextPath):
            with open(self.startingTextPath, "r") as leftFile:
                for x in leftFile:
                    self.startingText.append(x.split())
                    self.chosen_left_points.append(QtCore.QPoint(int(float(x.split()[0])), int(float(x.split()[1]))))

        if os.path.isfile(self.startingTextPath):
            os.remove(self.startingTextPath)

        if self.startingImage.hasScaledContents() and self.endingImage.hasScaledContents():
            self.alphaValue.setEnabled(1)
            self.blendButton.setEnabled(1)
            self.alphaSlider.setEnabled(1)
            if self.chosen_left_points != [] and self.chosen_right_points != []:
                self.resetPointsButton.setEnabled(1)
            self.autoCornerButton.setEnabled(1)
            # Check if 3 or more points exist for two corresponding images so that triangles may be displayed
            if (len(self.chosen_left_points) + len(self.confirmed_left_points)) == (len(self.chosen_right_points) + len(self.confirmed_right_points)):
                if (len(self.chosen_left_points) + len(self.confirmed_left_points)) >= 3:
                    if (len(self.chosen_right_points) + len(self.confirmed_right_points)) >= 3:
                        self.triangleBox.setEnabled(1)
        self.displayTriangles()

    def loadDataRight(self):
        filePath, _ = QFileDialog.getOpenFileName(self, caption='Open Ending Image File ...', filter="Images (*.png *.jpg)")
        if not filePath:
            return

        self.notificationLine.setText(" Right image loaded.")
        if self.triangleBox.isChecked():
            self.triangleUpdatePref = 1
        else:
            self.triangleUpdatePref = 0
        self.fullBlendComplete = False
        self.triangleBox.setEnabled(0)
        self.triangleBox.setChecked(0)
        self.displayTriangles()
        self.refreshPaint()

        if self.rightOn == 0:
            self.rightOn = 1
        self.rightPixmap = QtGui.QPixmap(filePath)
        self.endingImage.setPixmap(self.rightPixmap)
        self.endingImage.setScaledContents(1)
        self.rightSize = (imageio.imread(filePath).shape[1], imageio.imread(filePath).shape[0])
        self.rightScalar = (self.rightSize[0] / (424 + int((self.width() - 878) / 2)), self.rightSize[1] / (self.height() - 458))

        self.endingImagePath = filePath
        self.endingTextPath = filePath + '.txt'

        # Obtain file's name, removing path and extension
        # Example: C:/Desktop/EndGray1.jpg => EndGray1
        rightFileRegex = re.search('(?<=[/])[^/]+(?=[.])', filePath)
        rightTypeRegex = re.search('.png$', filePath)

        if rightTypeRegex is None:
            self.rightPNG = 0
        elif rightTypeRegex.group() == '.png':
            self.rightPNG = 1
        else:
            self.rightPNG = 0

        # Now assign file's name to desired path for information storage (appending .txt at the end)
        self.endingTextCorePath = 'C:/Users/xzomb/PycharmProjects/Personal/Morphing/Images_Points/' + rightFileRegex.group() + '.txt'

        # If there is already a text file at the location of the selected image, the program assumes that it is what
        # the user intends to start with and moves it to the desired path for future manipulation.
        # Otherwise, the program creates an empty file instead.
        if os.path.isfile(self.endingTextPath):
            copyfile(self.endingTextPath, self.endingTextCorePath)
        else:
            open(self.endingTextCorePath, 'a').close()

        self.endingText = []
        self.added_left_points = []
        self.added_right_points = []
        self.confirmed_left_points = []
        self.confirmed_left_points_history = []
        self.confirmed_right_points = []
        self.confirmed_right_points_history = []
        self.chosen_right_points = []

        if os.path.isfile(self.endingTextCorePath):
            with open(self.endingTextCorePath, "r") as rightFile:
                for x in rightFile:
                    self.endingText.append(x.split())
                    self.chosen_right_points.append(QtCore.QPoint(int(float(x.split()[0])), int(float(x.split()[1]))))
        elif os.path.isfile(self.endingTextPath):
            with open(self.endingTextPath, "r") as rightFile:
                for x in rightFile:
                    self.endingText.append(x.split())
                    self.chosen_right_points.append(QtCore.QPoint(int(float(x.split()[0])), int(float(x.split()[1]))))

        if os.path.isfile(self.endingTextPath):
            os.remove(self.endingTextPath)

        if self.startingImage.hasScaledContents() and self.endingImage.hasScaledContents():
            self.alphaValue.setEnabled(1)
            self.blendButton.setEnabled(1)
            self.alphaSlider.setEnabled(1)
            if self.chosen_left_points != [] and self.chosen_right_points != []:
                self.resetPointsButton.setEnabled(1)
            self.autoCornerButton.setEnabled(1)
            # Check if 3 or more points exist for two corresponding images so that triangles may be displayed
            if (len(self.chosen_left_points) + len(self.confirmed_left_points)) == (len(self.chosen_right_points) + len(self.confirmed_right_points)):
                if (len(self.chosen_left_points) + len(self.confirmed_left_points)) >= 3:
                    if (len(self.chosen_right_points) + len(self.confirmed_right_points)) >= 3:
                        self.triangleBox.setEnabled(1)
        self.displayTriangles()


if __name__ == "__main__":
    currentApp = QApplication(sys.argv)
    currentForm = MorphingApp()

    currentForm.show()
    currentApp.exec_()
