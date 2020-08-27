#######################################################
#   Author:     David Dowd
#   Email:      ddowd97@gmail.com
#######################################################

import multiprocessing
import sys
import os
import re
import time
from shutil import copyfile

import imageio
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog
import math

from Morphing import *
from MorphingGUI import *

# Module  level  Variables
#######################################################
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class MorphingApp(QMainWindow, Ui_MainWindow):

    def __init__(self, parent=None):
        super(MorphingApp, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QtGui.QIcon("./Morphing.ico"))

        # Defaults on Startup
        self.chosen_left_points = []                                            # List used to store points confirmed in previous sessions (LEFT)
        self.chosen_right_points = []                                           # List used to store points confirmed in previous sessions (RIGHT)
        self.added_left_points = []                                             # List used to store temporary points added in current session (LEFT)
        self.added_right_points = []                                            # List used to store temporary points added in current session (RIGHT)
        self.confirmed_left_points = []                                         # List used to store existing points confirmed in current session (LEFT)
        self.confirmed_right_points = []                                        # List used to store existing points confirmed in current session (RIGHT)
        self.confirmed_left_points_history = []                                 # List used to log all points confirmed during this session for CTRL + Y (LEFT)
        self.confirmed_right_points_history = []                                # List used to log all points confirmed during this session for CTRL + Y (RIGHT)
        self.leftPolyList = []                                                  # List used to store delaunay triangles (LEFT)
        self.rightPolyList = []                                                 # List used to store delaunay triangles (RIGHT)
        self.blendList = []                                                     # List used to store a variable amount of alpha increment frames for full blending
        self.smoothList = []                                                    # List used to store a variable amount of smoothed alpha increment frames for full blending

        self.startingImagePath = ''                                             # String used to store file path to the left image
        self.endingImagePath = ''                                               # String used to store file path to the right image
        self.startingTextPath = ''                                              # String used to store file path to the left image's text file, if it was pre-made (LEGACY)
        self.endingTextPath = ''                                                # String used to store file path to the right image's text file, if it was pre-made (LEGACY)
        self.startingTextCorePath = ''                                          # String used to store local file path to the left image's corresponding text file
        self.endingTextCorePath = ''                                            # String used to store local file path to the right image's corresponding text file

        self.currentWindow = 0                                                  # Flag used to indicate which image will accept the next mouse click for creating points
        self.enableDeletion = 0                                                 # Flag used to indicate whether the most recently created point can be deleted with Backspace
        self.persistFlag = 0                                                    # Flag used to indicate how points are created during a mouse click event (LEGACY)
        self.triangleUpdate = 0                                                 # Flag used to indicate whether triangles need to be repainted (or removed) in the next paint event
        self.triangleUpdatePref = 0                                             # Flag used to remember whether the user wants to display triangles (in the case that they are forced off)
        self.imageScalar = 0                                                    # Value used to scale created points to where they visually line up with the original images
        self.fullBlendValue = 0.05                                              # Value used for determining the spacing between alpha increments when full blending
        self.gifValue = 100                                                     # Value used for determining the amount of time allotted to each frame of a created .gif file

        self.leftSize = (0, 0)                                                  # Tuple used to store the width and height of the left image
        self.rightSize = (0, 0)                                                 # Tuple used to store the width and height of the right image

        self.fullBlendComplete = False                                          # Flag used to indicate whether a full blend is displayable
        self.changeFlag = False                                                 # Flag used to indicate when the program should repaint (because Qt loves to very frequently call paint events)

        self.blendedImage = None                                                # Pre-made reference to a variable that is used to store a singular blended image
        self.smoothedImage = None                                               # Pre-made reference to a variable that is used to store a singular smoothed image

        # Logic
        self.loadStartButton.clicked.connect(self.loadDataLeft)                 # When the first  load image button is clicked, begins loading logic
        self.loadEndButton.clicked.connect(self.loadDataRight)                  # When the second load image button is clicked, begins loading logic
        self.triangleBox.clicked.connect(self.updateTriangleStatus)             # When the triangle box is clicked, changes flags
        self.transparencyBox.stateChanged.connect(self.transparencyUpdate)      # When the transparency box is checked or unchecked, changes flags
        self.blendButton.clicked.connect(self.blendImages)                      # When the blend button is clicked, begins blending logic
        self.blendBox.stateChanged.connect(self.blendBoxUpdate)                 # When the blend box is checked or unchecked, changes flags
        self.smoothingBox.stateChanged.connect(self.smoothBoxUpdate)            # When the smooth box is checked or unchecked, changes flags
        self.blendText.returnPressed.connect(self.blendTextDone)                # When the return key is pressed, removes focus from the input text window
        self.saveButton.clicked.connect(self.saveImages)                        # When the save button is clicked, begins image saving logic
        self.gifText.returnPressed.connect(self.gifTextDone)                    # When the return key is pressed, removes focus from the input text window
        self.alphaSlider.valueChanged.connect(self.updateAlpha)                 # When the alpha slider is moved, reads and formats the value
        self.triangleRedSlider.valueChanged.connect(self.updateRed)             # When the red   slider is moved, reads the value
        self.triangleGreenSlider.valueChanged.connect(self.updateGreen)         # When the green slider is moved, reads the value
        self.triangleBlueSlider.valueChanged.connect(self.updateBlue)           # When the blue  slider is moved, reads the value
        self.resetPointsButton.clicked.connect(self.resetPoints)                # When the reset points button is clicked, begins logic for removing points
        self.resetSliderButton.clicked.connect(self.resetAlphaSlider)           # When the reset slider button is clicked, begins logic for resetting it to default
        self.autoCornerButton.clicked.connect(self.autoCorner)                  # When the add   corner button is clicked, begins logic for adding corner points

    # Macro function to save unnecessary repetitions of the same few lines of code.
    # Essentially reconfigures the alpha slider as the user works with the GUI.
    def refreshAlphaSlider(self):
        temp = float(self.alphaValue.text())
        self.alphaSlider.setMaximum(int(100 / (self.fullBlendValue / 0.01)))
        self.fullBlendValue = 1.0 / self.alphaSlider.maximum()
        self.blendText.setText(str(self.fullBlendValue))
        self.alphaSlider.setValue(round(temp / self.fullBlendValue))
        if self.alphaSlider.maximum() == 20:
            self.alphaSlider.setTickInterval(2)
            self.resetSliderButton.setEnabled(0)
        else:
            self.alphaSlider.setTickInterval(1)
            self.resetSliderButton.setEnabled(1)

    # QoL function that removes focus from the full blend text window when the user presses Enter.
    # Additionally verifies the user's specified full blending value.
    def blendTextDone(self):
        self.fullBlendComplete = False
        if self.blendText.text() == '.':
            self.fullBlendValue = 0.05
            self.blendText.setText(str(self.fullBlendValue))
            self.refreshAlphaSlider()
        else:
            self.verifyValue("blend")
        self.notificationLine.setFocus()

    # QoL function that removes focus from the gif text window when the user presses Enter.
    # Additionally verifies the user's specified gif frame time value.
    def gifTextDone(self):
        # Obviously there is probably a more professional way of writing this conditional  but for now, it's fine.
        if self.gifText.text() == ' ms' or self.gifText.text() == '  ms' or self.gifText.text() == '   ms' or self.gifText.text() == '    ms':
            self.gifValue = 100
            self.gifText.setText("100 ms")
        else:
            self.verifyValue("gif")
        self.notificationLine.setFocus()

    # Macro function to save unnecessary repetitions of the same few lines of code.
    # Essentially corrects invalid values that the user may enter for full blending and gif frame times..
    # then rounds to the best number that's closest to what the user specified in the input box.
    # (This is required, since Qt can't restrict all bad forms of input.)
    def verifyValue(self, param: str):
        if param == "blend":
            self.fullBlendComplete = False
            self.fullBlendValue = min(float(self.blendText.text()), 0.25)
            self.fullBlendValue = max(self.fullBlendValue, 0.001)
            self.blendText.setText(str(self.fullBlendValue))
            self.refreshAlphaSlider()
        elif param == "gif":
            self.gifValue = min(int(self.gifText.text().replace(' ms', '')), 999)
            self.gifValue = int(max(self.gifValue, 1))
            if len(str(self.gifValue)) == 1:
                self.gifText.setText("00" + str(self.gifValue) + " ms")
            elif len(str(self.gifValue)) == 2:
                self.gifText.setText("0" + str(self.gifValue) + " ms")
            else:
                self.gifText.setText(str(self.gifValue) + " ms")

    # Workaround function that prevents unpredictable behavior with the triangle box
    def updateTriangleStatus(self):
        self.triangleUpdatePref = int(self.triangleBox.isChecked())
        self.displayTriangles()

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
        else:
            self.triangleRed.setText("<font color='black'>Red</font>")
            self.triangleGreen.setText("<font color='black'>Green</font>")
            self.triangleBlue.setText("<font color='black'>Blue</font>")
        self.triangleLabel.setEnabled(val)
        self.triangleRed.setEnabled(val)
        self.triangleGreen.setEnabled(val)
        self.triangleBlue.setEnabled(val)
        self.triangleRedSlider.setEnabled(val)
        self.triangleGreenSlider.setEnabled(val)
        self.triangleBlueSlider.setEnabled(val)

    # Self-contained function that checks for the existence of corner points and adds any that are not already present.
    # Can not be invoked while a point is pending (in order to prevent exploits).
    # Written to dynamically work with triangles without any exploits.
    def autoCorner(self):
        leftMaxX = min(math.ceil((self.startingImage.geometry().topRight().x() - self.startingImage.geometry().topLeft().x() - 1) * self.imageScalar[0]), self.leftSize[0] - 1)
        leftMaxY = min(math.ceil((self.endingImage.geometry().bottomRight().y() - self.startingImage.geometry().topLeft().y() - 1) * self.imageScalar[1]), self.leftSize[1] - 1)
        rightMaxX = min(math.ceil((self.endingImage.geometry().topRight().x() - self.endingImage.geometry().topLeft().x() - 1) * self.imageScalar[0]), self.rightSize[0] - 1)
        rightMaxY = min(math.ceil((self.endingImage.geometry().bottomRight().y() - self.startingImage.geometry().topLeft().y() - 1) * self.imageScalar[1]), self.rightSize[1] - 1)

        tempLeft = [QtCore.QPoint(0, 0), QtCore.QPoint(0, leftMaxY), QtCore.QPoint(leftMaxX, 0), QtCore.QPoint(leftMaxX, leftMaxY)]
        tempRight = [QtCore.QPoint(0, 0), QtCore.QPoint(0, rightMaxY), QtCore.QPoint(rightMaxX, 0), QtCore.QPoint(rightMaxX, rightMaxY)]

        self.triangleBox.setEnabled(1)
        i = 0
        counter = 0
        while i < 4:
            if tempLeft[i] not in self.confirmed_left_points and tempLeft[i] not in self.chosen_left_points and tempRight[i] not in self.confirmed_right_points and tempRight[i] not in self.chosen_right_points:
                counter += 1
                self.confirmed_left_points.append(tempLeft[i])
                self.confirmed_left_points_history.append(tempLeft[i])
                self.confirmed_right_points.append(tempRight[i])
                self.confirmed_right_points_history.append(tempRight[i])

                with open(self.startingTextCorePath, "a") as startingFile:
                    if not os.stat(self.startingTextCorePath).st_size:  # left file is empty
                        startingFile.write('{:>8}{:>8}'.format(str(format(self.confirmed_left_points[len(self.confirmed_left_points) - 1].x(), ".1f")), str(format(self.confirmed_left_points[len(self.confirmed_left_points) - 1].y(), ".1f"))))
                    else:
                        startingFile.write('\n{:>8}{:>8}'.format(str(format(self.confirmed_left_points[len(self.confirmed_left_points) - 1].x(), ".1f")), str(format(self.confirmed_left_points[len(self.confirmed_left_points) - 1].y(), ".1f"))))
                with open(self.endingTextCorePath, "a") as endingFile:
                    if not os.stat(self.endingTextCorePath).st_size:  # if right file is empty
                        endingFile.write('{:>8}{:>8}'.format(str(format(self.confirmed_right_points[len(self.confirmed_right_points) - 1].x(), ".1f")), str(format(self.confirmed_right_points[len(self.confirmed_right_points) - 1].y(), ".1f"))))
                    else:
                        endingFile.write('\n{:>8}{:>8}'.format(str(format(self.confirmed_right_points[len(self.confirmed_right_points) - 1].x(), ".1f")), str(format(self.confirmed_right_points[len(self.confirmed_right_points) - 1].y(), ".1f"))))
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
        self.triangleBox.setChecked(self.triangleUpdatePref)
        self.blendButton.setEnabled(1)
        self.resetPointsButton.setEnabled(1)

    # Function that wipes the slate clean, erasing all placed points from the GUI and relevant files.
    # Similar to autoCorner, this has been written to dynamically work with triangles without any exploits.
    def resetPoints(self):
        self.triangleUpdatePref = int(self.triangleBox.isChecked())
        self.blendButton.setEnabled(0)
        self.resetPointsButton.setEnabled(0)
        self.autoCornerButton.setEnabled(1)
        self.triangleBox.setChecked(0)
        self.triangleBox.setEnabled(0)
        self.added_left_points = []
        self.added_right_points = []
        self.confirmed_left_points = []
        self.confirmed_right_points = []
        self.chosen_left_points = []
        self.chosen_right_points = []
        self.leftPolyList = []
        self.rightPolyList = []

        if os.path.isfile(self.startingTextCorePath):
            os.remove(self.startingTextCorePath)

        if os.path.isfile(self.endingTextCorePath):
            os.remove(self.endingTextCorePath)

        self.enableDeletion = 0
        self.persistFlag = 0
        self.currentWindow = 0
        self.refreshPaint()

        self.notificationLine.setText(" Successfully reset points.")

    # Function that resets the alpha slider (for use after setting a full blend value that has modified the slider).
    # Resets the full blend value as well, just to prevent any weird behavior from ever occurring.
    def resetAlphaSlider(self):
        self.alphaSlider.setMaximum(20)
        self.alphaSlider.setTickInterval(2)
        self.fullBlendValue = 0.05
        self.blendText.setText(str(self.fullBlendValue))
        self.alphaValue.setText(str(0.0))
        self.alphaSlider.setValue(0)
        self.resetSliderButton.setEnabled(0)

    # Function that handles the rendering of points and triangles onto the GUI when manually called.
    # Dynamically handles changes in point and polygon lists to be compatible with resetPoints, autoCorner, etc.
    # TODO: Modify pointWidth to be a function of image size
    def paintEvent(self, paint_event):
        if self.changeFlag:
            leftPic = QtGui.QPixmap(self.startingImagePath)
            rightPic = QtGui.QPixmap(self.endingImagePath)
            pen = QtGui.QPen()
            pen.setWidth(4)
            leftpainter = QtGui.QPainter(leftPic)
            rightpainter = QtGui.QPainter(rightPic)
            pointWidth = 4

            if self.triangleUpdate == 1:
                if len(self.leftPolyList) == len(self.rightPolyList) > 0:
                    pointWidth = 7
                    pen.setColor(QtGui.QColor(self.triangleRedSlider.value(), self.triangleGreenSlider.value(), self.triangleBlueSlider.value(), 255))
                    leftpainter.setPen(pen)
                    for x in self.leftPolyList:
                        leftpainter.drawPolygon(x, 3)

                    pen.setColor(QtGui.QColor(self.triangleRedSlider.value(), self.triangleGreenSlider.value(), self.triangleBlueSlider.value(), 255))
                    rightpainter.setPen(pen)
                    for x in self.rightPolyList:
                        rightpainter.drawPolygon(x, 3)

            leftpainter.setBrush(QtGui.QColor(255, 0, 0, 255))
            for x in self.chosen_left_points:
                leftpainter.drawEllipse(x, pointWidth, pointWidth)

            leftpainter.setBrush(QtGui.QColor(0, 255, 0, 255))
            for x in self.added_left_points:
                leftpainter.drawEllipse(x, pointWidth, pointWidth)

            leftpainter.setBrush(QtGui.QColor(0, 0, 255, 255))
            for x in self.confirmed_left_points:
                leftpainter.drawEllipse(x, pointWidth, pointWidth)

            self.startingImage.setPixmap(leftPic)
            leftpainter.end()

            rightpainter.setBrush(QtGui.QColor(255, 0, 0, 255))
            for x in self.chosen_right_points:
                rightpainter.drawEllipse(x, pointWidth, pointWidth)

            rightpainter.setBrush(QtGui.QColor(0, 255, 0, 255))
            for x in self.added_right_points:
                rightpainter.drawEllipse(x, pointWidth, pointWidth)

            rightpainter.setBrush(QtGui.QColor(0, 0, 255, 255))
            for x in self.confirmed_right_points:
                rightpainter.drawEllipse(x, pointWidth, pointWidth)

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
            if self.startingImage.hasScaledContents() and self.endingImage.hasScaledContents():
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
                            data1[-1] = data1[-1][0:int(len(data1[-1]) - 1)]  # Remove \n from the previously second to last line
                            open(self.startingTextCorePath, 'w').writelines(data1)
                        else:
                            os.remove(self.startingTextCorePath)
                        data2 = open(self.endingTextCorePath, 'r').readlines()
                        del data2[-1]
                        if data2:
                            data2[-1] = data2[-1][0:int(len(data2[-1]) - 1)]  # Remove \n from the previously second to last line
                            open(self.endingTextCorePath, 'w').writelines(data2)
                        else:
                            os.remove(self.endingTextCorePath)
                        # self.currentWindow = 0
                        self.enableDeletion = 0
                        self.persistFlag = 0
                        if len(self.chosen_left_points) + len(self.confirmed_left_points) >= 3:
                            self.displayTriangles()
                            self.blendButton.setEnabled(1)
                        else:
                            self.triangleUpdatePref = int(self.triangleBox.isChecked())
                            self.triangleBox.setChecked(0)
                            self.triangleBox.setEnabled(0)
                            self.blendButton.setEnabled(0)
                            self.displayTriangles()
                            if len(self.chosen_left_points) + len(self.confirmed_left_points) == 0:
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
                        data2 = open(self.endingTextCorePath, 'r').readlines()
                        del data2[-1]
                        if data2:
                            data2[-1] = data2[-1][0:int(len(data2[-1]) - 1)]
                            open(self.endingTextCorePath, 'w').writelines(data2)
                        else:
                            os.remove(self.endingTextCorePath)
                        self.currentWindow = 0
                        self.enableDeletion = 0
                        self.persistFlag = 0

                        if len(self.chosen_left_points) + len(self.confirmed_left_points) >= 3:
                            self.displayTriangles()
                            self.blendButton.setEnabled(1)
                        else:
                            self.triangleUpdatePref = int(self.triangleBox.isChecked())
                            self.triangleBox.setChecked(0)
                            self.triangleBox.setEnabled(0)
                            self.blendButton.setEnabled(0)
                            self.displayTriangles()
                            if len(self.chosen_left_points) + len(self.confirmed_left_points) == 0:
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
            if self.startingImage.hasScaledContents() and self.endingImage.hasScaledContents() and self.enableDeletion == 1:
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
    def resizeEvent(self, event):
        self.imageScalar = (self.leftSize[0] / (self.startingImage.geometry().topRight().x() - self.startingImage.geometry().topLeft().x()), self.leftSize[1] / (self.startingImage.geometry().bottomRight().y() - self.startingImage.geometry().topLeft().y()))

    # Function that handles GUI and file behavior when the mouse is clicked.
    def mousePressEvent(self, cursor_event):
        self.imageScalar = (self.leftSize[0] / (self.startingImage.geometry().topRight().x() - self.startingImage.geometry().topLeft().x()), self.leftSize[1] / (self.startingImage.geometry().bottomRight().y() - self.startingImage.geometry().topLeft().y()))

        if self.startingImage.hasScaledContents() and self.endingImage.hasScaledContents():
            # Check if 3 or more points exist for two corresponding images so that triangles may be displayed
            if (len(self.added_left_points) + len(self.chosen_left_points) + len(self.confirmed_left_points)) == (len(self.added_left_points) + len(self.chosen_left_points) + len(self.confirmed_left_points)) >= 3:
                if self.currentWindow == 0:
                    self.triangleBox.setEnabled(1)
                    self.blendButton.setEnabled(1)
                    if self.triangleUpdatePref == 1:
                        self.triangleUpdate = 1
                        self.triangleBox.setChecked(1)
                        self.refreshPaint()
            if self.currentWindow == 0:
                if not (self.endingImage.geometry().topLeft().x() < cursor_event.pos().x() < self.endingImage.geometry().topRight().x() and self.startingImage.geometry().topLeft().y() < cursor_event.pos().y() < self.endingImage.geometry().bottomRight().y()) and self.added_right_points != [] and self.persistFlag == 2:
                    throwawayLeft = self.added_left_points.pop(len(self.added_left_points)-1)
                    throwawayRight = self.added_right_points.pop(len(self.added_right_points)-1)
                    self.confirmed_left_points.append(throwawayLeft)
                    self.confirmed_left_points_history.append(throwawayLeft)
                    self.confirmed_right_points.append(throwawayRight)
                    self.confirmed_right_points_history.append(throwawayRight)
                    with open(self.startingTextCorePath, "a") as startingFile:
                        if not os.stat(self.startingTextCorePath).st_size:  # left file is empty
                            startingFile.write('{:>8}{:>8}'.format(str(format(self.confirmed_left_points[len(self.confirmed_left_points)-1].x(), ".1f")), str(format(self.confirmed_left_points[len(self.confirmed_left_points)-1].y(), ".1f"))))
                        else:
                            startingFile.write('\n{:>8}{:>8}'.format(str(format(self.confirmed_left_points[len(self.confirmed_left_points)-1].x(), ".1f")), str(format(self.confirmed_left_points[len(self.confirmed_left_points)-1].y(), ".1f"))))
                    with open(self.endingTextCorePath, "a") as endingFile:
                        if not os.stat(self.endingTextCorePath).st_size:  # right file is empty
                            endingFile.write('{:>8}{:>8}'.format(str(format(self.confirmed_right_points[len(self.confirmed_right_points)-1].x(), ".1f")), str(format(self.confirmed_right_points[len(self.confirmed_right_points)-1].y(), ".1f"))))
                        else:
                            endingFile.write('\n{:>8}{:>8}'.format(str(format(self.confirmed_right_points[len(self.confirmed_right_points)-1].x(), ".1f")), str(format(self.confirmed_right_points[len(self.confirmed_right_points)-1].y(), ".1f"))))
                    self.persistFlag = 0
                    self.refreshPaint()
                    self.displayTriangles()
                    self.autoCornerButton.setEnabled(1)
                    self.resetPointsButton.setEnabled(1)
                    self.notificationLine.setText(" Successfully confirmed set of added points.")
                if self.startingImage.geometry().topLeft().x() < cursor_event.pos().x() < self.startingImage.geometry().topRight().x() and self.startingImage.geometry().topLeft().y() < cursor_event.pos().y() < self.endingImage.geometry().bottomRight().y():
                    leftCoord = QtCore.QPoint(int((cursor_event.pos().x()-self.startingImage.geometry().topLeft().x())*self.imageScalar[0]), int((cursor_event.pos().y()-self.startingImage.geometry().topLeft().y())*self.imageScalar[1]))
                    self.added_left_points.append(leftCoord)
                    self.refreshPaint()
                    self.currentWindow = 1
                    self.persistFlag = 0
                    self.enableDeletion = 1
                    self.autoCornerButton.setEnabled(0)
                    self.notificationLine.setText(" Successfully added left temporary point.")
            elif self.currentWindow == 1:
                if self.endingImage.geometry().topLeft().x() < cursor_event.pos().x() < self.endingImage.geometry().topRight().x() and self.startingImage.geometry().topLeft().y() < cursor_event.pos().y() < self.endingImage.geometry().bottomRight().y():
                    rightCoord = QtCore.QPoint(int((cursor_event.pos().x()-self.endingImage.geometry().topLeft().x())*self.imageScalar[0]), int((cursor_event.pos().y()-self.startingImage.geometry().topLeft().y())*self.imageScalar[1]))
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
        if self.transparencyBox.isChecked():
            self.notificationLine.setText(" Successfully enabled transparency layer.")
        else:
            self.notificationLine.setText(" Successfully disabled transparency layer.")

    # Another simple function for updating user preference regarding 'full blending'
    # Full blending is defined as morphing every 0.05 alpha increment of the two images.
    # The alpha slider than becomes an interactive display, showing each blend in realtime.
    # (Naturally, this is disabled by default, as full blending takes 20 times as long to run)
    def blendBoxUpdate(self):
        self.blendText.setEnabled(int(self.blendBox.isChecked()))
        if self.blendBox.isChecked():
            self.notificationLine.setText(" Successfully enabled full blending.")
        else:
            self.notificationLine.setText(" Successfully disabled full blending.")

    # Yet another function for updating user preference; this one pertains to 'image smoothing'
    # Image smoothing removes hot pixels by using the values of neighboring pixels instead.
    # (While it is applied during every blend, smoothing is disabled by default and can be visibly toggled at any time)
    def smoothBoxUpdate(self):
        if self.blendingImage.hasScaledContents():
            if self.fullBlendComplete:     # If it's a full blend
                value_num = ((self.alphaSlider.value() / self.alphaSlider.maximum()) / self.fullBlendValue) * self.fullBlendValue
                if self.smoothingBox.isChecked():
                    temp = self.smoothList[round(value_num / self.fullBlendValue)]
                else:
                    temp = self.blendList[round(value_num / self.fullBlendValue)]
            elif self.smoothingBox.isChecked():
                temp = self.smoothedImage
            else:
                temp = self.blendedImage

            if len(temp.shape) == 2:
                self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], QtGui.QImage.Format_Grayscale8)))
            elif temp.shape[2] == 3:
                self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], temp.shape[1] * 3, QtGui.QImage.Format_RGB888)))
            elif temp.shape[2] == 4:
                self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], QtGui.QImage.Format_RGBA8888)))
            else:
                print("Generic catching error: Something went wrong when loading the image.")

            if self.smoothingBox.isChecked():
                self.notificationLine.setText(" Successfully applied image smoothing.")
            else:
                self.notificationLine.setText(" Successfully removed image smoothing.")
        elif self.smoothingBox.isChecked():
            self.notificationLine.setText(" Successfully enabled image smoothing.")
        else:
            self.notificationLine.setText(" Successfully disabled image smoothing.")

    # Function that dynamically updates the list of triangles for the image pair provided, when manually invoked.
    # When a process wants to see triangles update properly, THIS is what needs to be called (not self.triangleUpdate).
    def displayTriangles(self):
        if self.triangleBox.isEnabled():
            if self.triangleBox.isChecked() or self.triangleUpdatePref:
                # self.triangleBox.setCheckState(2)
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

                    # If the images have any triangles, it is safe to enable the blend button
                    # (The boolean expression isn't really necessary, but it serves as an OK sanity check.)
                    self.blendButton.setEnabled(bool(len(self.leftPolyList) == len(self.rightPolyList) >= 1))
            else:
                self.updateTriangleWidget(0)
                self.triangleUpdate = 0
                self.refreshPaint()
        else:
            self.updateTriangleWidget(0)
            self.triangleUpdate = 0
            self.refreshPaint()

    # Function that handles movement of the alpha slider.
    # Typically will only update the alpha value in use unless a full blend has been completed (and is available).
    # If so, movement of this slider will also display the new alpha value's corresponding morph frame.
    def updateAlpha(self):
        value_num = ((self.alphaSlider.value() / self.alphaSlider.maximum()) / self.fullBlendValue) * self.fullBlendValue
        value = format(value_num, ".3f")
        self.notificationLine.setText(" Alpha value changed from " + self.alphaValue.text() + " to " + str(value) + ".")
        self.alphaValue.setText(str(value))
        if self.fullBlendComplete:
            if self.smoothingBox.isChecked():
                temp = self.smoothList[round(value_num / self.fullBlendValue)]
            else:
                temp = self.blendList[round(value_num / self.fullBlendValue)]

            if len(temp.shape) == 2:
                self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], QtGui.QImage.Format_Grayscale8)))
            elif temp.shape[2] == 3:
                self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], temp.shape[1] * 3, QtGui.QImage.Format_RGB888)))
            elif temp.shape[2] == 4:
                self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], QtGui.QImage.Format_RGBA8888)))
            else:
                print("Generic catching error: Something went wrong when loading the image.")

    # Red/Green/Blue slider functions for the triangle widget in order to select custom colors
    def updateRed(self):
        self.notificationLine.setText(" Red value set to " + str(self.triangleRedSlider.value()) + ".")
        self.refreshPaint()

    def updateGreen(self):
        self.notificationLine.setText(" Green value set to " + str(self.triangleGreenSlider.value()) + ".")
        self.refreshPaint()

    def updateBlue(self):
        self.notificationLine.setText(" Blue value set to " + str(self.triangleBlueSlider.value()) + ".")
        self.refreshPaint()

    # Function that handles behavior when the user wishes to blend the two calibrated images.
    # Currently designed to handle:
    #     > 8-Bit Grayscale                            (QtGui.QImage.Format_Grayscale8)
    #     > 24-Bit Color .JPG / .PNG                   (QtGui.QImage.Format_RGB888)
    #     > 24-Bit Color, 8-Bit Transparency .PNG      (QtGui.QImage.Format_RGBA8888)
    # TODO: Color Blending is not 100% accurate.
    #       Current thoughts: Shouldn't have anything to do with the 8 bit depth.. is this an interpolation issue?
    #       It almost feels like data is just... missing. So how do I determine what is missing???
    def blendImages(self):
        self.blendButton.setEnabled(0)
        self.smoothingBox.setEnabled(0)
        self.blendBox.setEnabled(0)
        triangleTuple = loadTriangles(self.startingTextCorePath, self.endingTextCorePath)
        leftImageRaw = imageio.imread(self.startingImagePath)
        rightImageRaw = imageio.imread(self.endingImagePath)
        leftImageARR = np.asarray(leftImageRaw)
        rightImageARR = np.asarray(rightImageRaw)
        errorFlag = False

        if self.blendBox.isChecked() and self.blendText.text() == '.':
            self.notificationLine.setText(" Failed to morph. Please disable full blending or specify a valid value (0.001 to 1.0)")
            errorFlag = True
        elif len(leftImageRaw.shape) < 3 and len(rightImageRaw.shape) < 3:  # if grayscale
            self.notificationLine.setText(" Calculating grayscale morph...")
            self.repaint()
            grayScale = Morpher(leftImageARR, triangleTuple[0], rightImageARR, triangleTuple[1])
            self.blendList = []
            self.smoothList = []
            start_time = time.time()
            if self.blendBox.isChecked():
                self.verifyValue("blend")
                x = 0
                while x <= self.alphaSlider.maximum():
                    self.notificationLine.setText(" Calculating RGB (.jpg) morph... {Frame " + str(x + 1) + "/" + str(self.alphaSlider.maximum() + 1) + "}")
                    self.repaint()
                    if x == self.alphaSlider.maximum():
                        tempImage = grayScale.getImageAtAlpha(1.0, self.smoothingBox.isChecked())
                    else:
                        tempImage = grayScale.getImageAtAlpha(x * self.fullBlendValue, self.smoothingBox.isChecked())
                    self.blendList.append(tempImage)
                    self.smoothList.append(smoothBlend(tempImage))
                    x += 1
                self.fullBlendComplete = True
                self.gifText.setEnabled(1)
                if self.smoothingBox.isChecked():
                    temp = self.smoothList[int(float(self.alphaValue.text()) / self.fullBlendValue)]
                else:
                    temp = self.blendList[int(float(self.alphaValue.text()) / self.fullBlendValue)]
                self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], QtGui.QImage.Format_Grayscale8)))
            else:
                self.fullBlendComplete = False
                self.gifText.setEnabled(0)
                self.blendedImage = grayScale.getImageAtAlpha(float(self.alphaValue.text()), self.smoothingBox.isChecked())
                self.smoothedImage = smoothBlend(self.blendedImage)
                if self.smoothingBox.isChecked():
                    self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(self.smoothedImage.data, self.smoothedImage.shape[1], self.smoothedImage.shape[0], QtGui.QImage.Format_Grayscale8)))
                else:
                    self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(self.blendedImage.data, self.blendedImage.shape[1], self.blendedImage.shape[0], QtGui.QImage.Format_Grayscale8)))
            self.notificationLine.setText(" Morph took " + "{:.3f}".format(time.time() - start_time) + " seconds.\n")
        elif not self.transparencyBox.isChecked() or (leftImageRaw.shape[2] == 3 and rightImageRaw.shape[2] == 3):  # if color, no alpha (.JPG)
            self.notificationLine.setText(" Calculating RGB (.jpg) morph...")
            self.repaint()
            colorScaleR = Morpher(leftImageARR[:, :, 0], triangleTuple[0], rightImageARR[:, :, 0], triangleTuple[1])
            colorScaleG = Morpher(leftImageARR[:, :, 1], triangleTuple[0], rightImageARR[:, :, 1], triangleTuple[1])
            colorScaleB = Morpher(leftImageARR[:, :, 2], triangleTuple[0], rightImageARR[:, :, 2], triangleTuple[1])
            self.blendList = []
            self.smoothList = []
            start_time = time.time()
            if self.blendBox.isChecked():

                counter = 0
                while counter <= self.alphaSlider.maximum():
                    self.notificationLine.setText(" Calculating RGB (.jpg) morph... {Frame " + str(counter + 1) + "/" + str(self.alphaSlider.maximum() + 1) + "}")
                    self.repaint()
                    if counter == self.alphaSlider.maximum():
                        alphaVal = 1.0
                    else:
                        alphaVal = counter * self.fullBlendValue
                    pool = multiprocessing.Pool(4)
                    results = [pool.apply_async(colorScaleR.getImageAtAlpha, (alphaVal, self.smoothingBox.isChecked())),
                               pool.apply_async(colorScaleG.getImageAtAlpha, (alphaVal, self.smoothingBox.isChecked())),
                               pool.apply_async(colorScaleB.getImageAtAlpha, (alphaVal, self.smoothingBox.isChecked()))]
                    blendR = results[0].get()
                    blendG = results[1].get()
                    blendB = results[2].get()
                    pool.close()
                    pool.terminate()
                    pool.join()
                    self.blendList.append(np.dstack((blendR, blendG, blendB)))
                    self.smoothList.append(np.dstack((smoothBlend(blendR), smoothBlend(blendG), smoothBlend(blendB))))
                    counter += 1
                self.fullBlendComplete = True
                self.gifText.setEnabled(1)
                if self.smoothingBox.isChecked():
                    temp = self.smoothList[int(float(self.alphaValue.text()) / self.fullBlendValue)]
                else:
                    temp = self.blendList[int(float(self.alphaValue.text()) / self.fullBlendValue)]
                self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], temp.shape[1] * 3, QtGui.QImage.Format_RGB888)))
                self.notificationLine.setText(" RGB morph took " + "{:.3f}".format(time.time() - start_time) + " seconds.\n")
            else:
                self.fullBlendComplete = False
                self.gifText.setEnabled(0)
                pool = multiprocessing.Pool(4)
                results = [pool.apply_async(colorScaleR.getImageAtAlpha, (float(self.alphaValue.text()), self.smoothingBox.isChecked())),
                           pool.apply_async(colorScaleG.getImageAtAlpha, (float(self.alphaValue.text()), self.smoothingBox.isChecked())),
                           pool.apply_async(colorScaleB.getImageAtAlpha, (float(self.alphaValue.text()), self.smoothingBox.isChecked()))]
                blendR = results[0].get()
                blendG = results[1].get()
                blendB = results[2].get()
                pool.close()
                pool.terminate()
                pool.join()
                self.blendedImage = np.dstack((blendR, blendG, blendB))
                self.smoothedImage = np.dstack((smoothBlend(blendR), smoothBlend(blendG), smoothBlend(blendB)))
                if self.smoothingBox.isChecked():
                    self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(self.smoothedImage.data, self.smoothedImage.shape[1], self.smoothedImage.shape[0], self.smoothedImage.shape[1] * 3, QtGui.QImage.Format_RGB888)))
                else:
                    self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(self.blendedImage.data, self.blendedImage.shape[1], self.blendedImage.shape[0], self.blendedImage.shape[1] * 3, QtGui.QImage.Format_RGB888)))
                self.notificationLine.setText(" RGB morph took " + "{:.3f}".format(time.time() - start_time) + " seconds.\n")
        elif self.transparencyBox.isChecked() and leftImageRaw.shape[2] == 4 and rightImageRaw.shape[2] == 4:   # if color, alpha (.PNG)
            self.notificationLine.setText(" Calculating RGBA (.png) morph...")
            self.repaint()
            colorScaleR = Morpher(leftImageARR[:, :, 0], triangleTuple[0], rightImageARR[:, :, 0], triangleTuple[1])
            colorScaleG = Morpher(leftImageARR[:, :, 1], triangleTuple[0], rightImageARR[:, :, 1], triangleTuple[1])
            colorScaleB = Morpher(leftImageARR[:, :, 2], triangleTuple[0], rightImageARR[:, :, 2], triangleTuple[1])
            colorScaleA = Morpher(leftImageARR[:, :, 3], triangleTuple[0], rightImageARR[:, :, 3], triangleTuple[1])
            self.blendList = []
            self.smoothList = []
            start_time = time.time()
            if self.blendBox.isChecked():
                counter = 0
                while counter <= self.alphaSlider.maximum():
                    self.notificationLine.setText(" Calculating RGBA (.jpg) morph... {Frame " + str(counter + 1) + "/" + str(self.alphaSlider.maximum() + 1) + "}")
                    self.repaint()
                    if counter == self.alphaSlider.maximum():
                        alphaVal = 1.0
                    else:
                        alphaVal = counter * self.fullBlendValue
                    pool = multiprocessing.Pool(4)
                    results = [pool.apply_async(colorScaleR.getImageAtAlpha, (alphaVal, self.smoothingBox.isChecked())),
                               pool.apply_async(colorScaleG.getImageAtAlpha, (alphaVal, self.smoothingBox.isChecked())),
                               pool.apply_async(colorScaleB.getImageAtAlpha, (alphaVal, self.smoothingBox.isChecked())),
                               pool.apply_async(colorScaleA.getImageAtAlpha, (alphaVal, self.smoothingBox.isChecked()))]
                    blendR = results[0].get()
                    blendG = results[1].get()
                    blendB = results[2].get()
                    blendA = results[3].get()
                    pool.close()
                    pool.terminate()
                    pool.join()

                    self.blendList.append(np.dstack((blendR, blendG, blendB, blendA)))
                    self.smoothList.append(np.dstack((smoothBlend(blendR), smoothBlend(blendG), smoothBlend(blendB), smoothBlend(blendA))))
                    counter += 1
                self.fullBlendComplete = True
                self.gifText.setEnabled(1)
                if self.smoothingBox.isChecked():
                    temp = self.smoothList[int(float(self.alphaValue.text()) / self.fullBlendValue)]
                else:
                    temp = self.blendList[int(float(self.alphaValue.text()) / self.fullBlendValue)]
                self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], QtGui.QImage.Format_RGBA8888)))
                self.notificationLine.setText(" RGBA morph took " + "{:.3f}".format(time.time() - start_time) + " seconds.\n")
            else:
                self.fullBlendComplete = False
                self.gifText.setEnabled(0)
                pool = multiprocessing.Pool(4)
                results = [pool.apply_async(colorScaleR.getImageAtAlpha, (float(self.alphaValue.text()), self.smoothingBox.isChecked())),
                           pool.apply_async(colorScaleG.getImageAtAlpha, (float(self.alphaValue.text()), self.smoothingBox.isChecked())),
                           pool.apply_async(colorScaleB.getImageAtAlpha, (float(self.alphaValue.text()), self.smoothingBox.isChecked())),
                           pool.apply_async(colorScaleA.getImageAtAlpha, (float(self.alphaValue.text()), self.smoothingBox.isChecked()))]
                blendR = results[0].get()
                blendG = results[1].get()
                blendB = results[2].get()
                blendA = results[3].get()
                pool.close()
                pool.terminate()
                pool.join()
                self.blendedImage = np.dstack((blendR, blendG, blendB, blendA))
                self.smoothedImage = np.dstack((smoothBlend(blendR), smoothBlend(blendG), smoothBlend(blendB), smoothBlend(blendA)))
                if self.smoothingBox.isChecked():
                    self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(self.smoothedImage.data, self.smoothedImage.shape[1], self.smoothedImage.shape[0], QtGui.QImage.Format_RGBA8888)))
                else:
                    self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(self.blendedImage.data, self.blendedImage.shape[1], self.blendedImage.shape[0], QtGui.QImage.Format_RGBA8888)))
                self.notificationLine.setText(" RGBA morph took " + "{:.3f}".format(time.time() - start_time) + " seconds.\n")
        else:
            self.notificationLine.setText(" Generic Catching Error: Check image file types..")
            errorFlag = True
        if not errorFlag:
            self.blendingImage.setScaledContents(1)
            self.blendButton.setEnabled(1)
            self.saveButton.setEnabled(1)
        self.smoothingBox.setEnabled(1)
        self.blendBox.setEnabled(1)

    # Function that handles behavior when the user wishes to save the blended image(s)
    # Currently designed to handle generation of the following:
    #     Single Blend → Grayscale .jpg/.jpeg
    #     Single Blend → Color     .jpg/.jpeg/.png
    #     Full Blend → Grayscale/Color .gif (default frame time: 100 ms)
    def saveImages(self):
        if self.blendingImage.hasScaledContents():
            filepath = ""
            if self.fullBlendComplete and self.blendList != []:  # create GIF
                self.gifTextDone()
                filepath, _ = QFileDialog.getSaveFileName(self, 'Save the gif as ...', "Morph.gif", "Images (*.gif)")

                if filepath == "":
                    return

                if self.smoothingBox.isChecked():
                    temp = self.smoothList
                    for frame in reversed(self.smoothList):
                        temp.append(frame)
                    imageio.mimsave(filepath, temp, duration=float(self.gifValue / 1000))
                else:
                    temp = self.blendList
                    for frame in reversed(self.blendList):
                        temp.append(frame)
                    imageio.mimsave(filepath, temp, duration=float(self.gifValue / 1000))
            else:  # create image
                if len(self.blendedImage.shape) < 3:
                    filepath, _ = QFileDialog.getSaveFileName(self, 'Save the image as ...', "Morph.jpg", "Images (*.jpg)")
                elif self.blendedImage.shape[2] == 3:
                    filepath, _ = QFileDialog.getSaveFileName(self, 'Save the image as ...', "Morph.jpg", "Images (*.jpg)")
                elif self.blendedImage.shape[2] == 4:
                    filepath, _ = QFileDialog.getSaveFileName(self, 'Save the image as ...', "Morph.png", "Images (*.png)")

                if filepath == "":
                    return

                if self.smoothingBox.isChecked():
                    imageio.imwrite(filepath, self.smoothedImage)
                else:
                    imageio.imwrite(filepath, self.blendedImage)
        else:
            self.notificationLine.setText(" Generic Catching Error: Image(s) can't be saved..")

    def loadDataLeft(self):
        filePath, _ = QFileDialog.getOpenFileName(self, caption='Open Starting Image File ...', filter="Images (*.png *.jpg)")
        if not filePath:
            return

        self.notificationLine.setText(" Left image loaded.")
        self.triangleUpdatePref = int(self.triangleBox.isChecked())
        self.fullBlendComplete = False
        self.triangleBox.setChecked(0)
        self.triangleBox.setEnabled(0)
        self.displayTriangles()

        # self.leftPixmap = QtGui.QPixmap(filePath)
        self.startingImage.setPixmap(QtGui.QPixmap(filePath))
        self.startingImage.setScaledContents(1)
        self.leftSize = (imageio.imread(filePath).shape[1], imageio.imread(filePath).shape[0])
        self.imageScalar = (self.leftSize[0] / (self.startingImage.geometry().topRight().x() - self.startingImage.geometry().topLeft().x()), self.leftSize[1] / (self.startingImage.geometry().bottomRight().y() - self.startingImage.geometry().topLeft().y()))

        self.startingImagePath = filePath
        self.startingTextPath = filePath + '.txt'  # TODO: Change from ".FILETYPE.txt" to "_FILETYPE.txt"

        # Obtain file's name, removing path and extension
        # Example: C:/Desktop/StartGray1.jpg => StartGray1
        leftFileRegex = re.search('(?<=[/])[^/]+(?=[.])', filePath)

        # Now assign file's name to desired path for information storage (appending .txt at the end)
        # self.startingTextCorePath = 'C:/Users/USER/PycharmProjects/Personal/Morphing/Images_Points/' + leftFileRegex.group() + '.txt'
        self.startingTextCorePath = os.path.join(ROOT_DIR, 'Images_Points\\' + leftFileRegex.group() + '.txt')

        # If there is already a text file at the location of the selected image, the program assumes that it is what
        # the user intends to start with and moves it to the desired path for future manipulation.
        # Otherwise, the program creates an empty file instead.
        # TODO: Strongly recommend re-writing everything beneath this point
        if os.path.isfile(self.startingTextPath):
            copyfile(self.startingTextPath, self.startingTextCorePath)
        else:
            if not os.path.exists(os.path.dirname(self.startingTextCorePath)):  # if Images_Points doesn't exist, create it
                os.makedirs(os.path.dirname(self.startingTextCorePath))
            open(self.startingTextCorePath, 'a').close()

        self.added_left_points = []
        self.added_right_points = []
        self.confirmed_left_points = []
        self.confirmed_left_points_history = []
        self.confirmed_right_points = []
        self.confirmed_right_points_history = []
        self.chosen_left_points = []
        # TODO: Consider changing this to "if self.startingTextCorePath is self.startingTextPath, else"
        if os.path.isfile(self.startingTextCorePath):  # Check new path for text file
            with open(self.startingTextCorePath, "r") as leftFile:
                for x in leftFile:
                    self.chosen_left_points.append(QtCore.QPoint(int(float(x.split()[0])), int(float(x.split()[1]))))
        elif os.path.isfile(self.startingTextPath):  # Check old path for text file
            with open(self.startingTextPath, "r") as leftFile:
                for x in leftFile:
                    self.chosen_left_points.append(QtCore.QPoint(int(float(x.split()[0])), int(float(x.split()[1]))))

        if os.path.isfile(self.startingTextPath):
            os.remove(self.startingTextPath)

        if self.startingImage.hasScaledContents() and self.endingImage.hasScaledContents():
            self.alphaValue.setEnabled(1)
            self.alphaSlider.setEnabled(1)
            if self.chosen_left_points != [] and self.chosen_right_points != []:
                self.resetPointsButton.setEnabled(1)
            self.autoCornerButton.setEnabled(1)

            # Check that the two images are the same size - if they aren't, the user should be notified that this won't work
            if self.leftSize[0] == self.rightSize[0] and self.leftSize[1] == self.rightSize[1]:
                # Check if 3 or more points exist for two corresponding images so that triangles may be displayed
                if (len(self.chosen_left_points) + len(self.confirmed_left_points)) == (len(self.chosen_right_points) + len(self.confirmed_right_points)) >= 3:
                    self.blendButton.setEnabled(1)
                    self.triangleBox.setEnabled(1)
                    self.triangleBox.setChecked(self.triangleUpdatePref)
            else:
                self.notificationLine.setText(" Left image loaded - WARNING: Input images must be the same size!")
        self.displayTriangles()

    def loadDataRight(self):
        filePath, _ = QFileDialog.getOpenFileName(self, caption='Open Ending Image File ...', filter="Images (*.png *.jpg)")
        if not filePath:
            return

        self.notificationLine.setText(" Right image loaded.")
        self.triangleUpdatePref = int(self.triangleBox.isChecked())
        self.fullBlendComplete = False
        self.triangleBox.setChecked(0)
        self.triangleBox.setEnabled(0)
        self.displayTriangles()

        # self.rightPixmap = QtGui.QPixmap(filePath)
        self.endingImage.setPixmap(QtGui.QPixmap(filePath))
        self.endingImage.setScaledContents(1)
        self.rightSize = (imageio.imread(filePath).shape[1], imageio.imread(filePath).shape[0])
        self.imageScalar = (self.rightSize[0] / (self.endingImage.geometry().topRight().x() - self.endingImage.geometry().topLeft().x()), self.rightSize[1] / (self.endingImage.geometry().bottomRight().y() - self.endingImage.geometry().topLeft().y()))

        self.endingImagePath = filePath
        self.endingTextPath = filePath + '.txt'

        # Obtain file's name, removing path and extension
        # Example: C:/Desktop/EndGray1.jpg => EndGray1
        rightFileRegex = re.search('(?<=[/])[^/]+(?=[.])', filePath)

        # Now assign file's name to desired path for information storage (appending .txt at the end)
        # self.endingTextCorePath = 'C:/Users/USER/PycharmProjects/Personal/Morphing/Images_Points/' + rightFileRegex.group() + '.txt'
        self.endingTextCorePath = os.path.join(ROOT_DIR, 'Images_Points\\' + rightFileRegex.group() + '.txt')

        # If there is already a text file at the location of the selected image, the program assumes that it is what
        # the user intends to start with and moves it to the desired path for future manipulation.
        # Otherwise, the program creates an empty file instead.
        # TODO: Strongly recommend re-writing everything beneath this point
        if os.path.isfile(self.endingTextPath):
            copyfile(self.endingTextPath, self.endingTextCorePath)
        else:
            if not os.path.exists(os.path.dirname(self.endingTextCorePath)):  # if Images_Points doesn't exist, create it
                os.makedirs(os.path.dirname(self.endingTextCorePath))
            open(self.endingTextCorePath, 'a').close()

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
                    self.chosen_right_points.append(QtCore.QPoint(int(float(x.split()[0])), int(float(x.split()[1]))))
        elif os.path.isfile(self.endingTextPath):
            with open(self.endingTextPath, "r") as rightFile:
                for x in rightFile:
                    self.chosen_right_points.append(QtCore.QPoint(int(float(x.split()[0])), int(float(x.split()[1]))))

        if os.path.isfile(self.endingTextPath):
            os.remove(self.endingTextPath)

        if self.startingImage.hasScaledContents() and self.endingImage.hasScaledContents():
            self.alphaValue.setEnabled(1)
            self.alphaSlider.setEnabled(1)
            if self.chosen_left_points != [] and self.chosen_right_points != []:
                self.resetPointsButton.setEnabled(1)
            self.autoCornerButton.setEnabled(1)

            # Check that the two images are the same size - if they aren't, the user should be notified that this won't work
            if self.leftSize[0] == self.rightSize[0] and self.leftSize[1] == self.rightSize[1]:
                # Check if 3 or more points exist for two corresponding images so that triangles may be displayed
                if (len(self.chosen_left_points) + len(self.confirmed_left_points)) == (len(self.chosen_right_points) + len(self.confirmed_right_points)) >= 3:
                    self.blendButton.setEnabled(1)
                    self.triangleBox.setEnabled(1)
                    self.triangleBox.setChecked(self.triangleUpdatePref)
            else:
                self.notificationLine.setText(" Right image loaded - WARNING: Input images must be the same size!")
        self.displayTriangles()


if __name__ == "__main__":
    currentApp = QApplication(sys.argv)
    currentForm = MorphingApp()

    currentForm.show()
    currentApp.exec_()
