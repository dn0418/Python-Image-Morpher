#######################################################
#            Author:     David Dowd
#            Email:      ddowd97@gmail.com
#######################################################

# Built-in Modules #
import queue
import multiprocessing
import sys
import os
import warnings
import time
import shutil
import requests
import math
import webbrowser

# External Modules - These require installation via the command: "pip install -r requirements.txt" #
import PyQt5.QtCore
import cv2
import imageio
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog
from pynput import mouse

from Morphing import *
from MorphingGUI import *

# Module  level  Variables
#######################################################
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
grayScale = None
colorScaleR = None
colorScaleG = None
colorScaleB = None
colorScaleA = None
start_time = 0.00
alphaValue = None


# OS independent solution for tracking mouse release on window resize events (because Qt can't detect this)
def on_click(x, y, button, pressed):
    if not pressed:
        currentForm.resizeImages()
        return False


class ImagerThread(QtCore.QThread):
    image_complete = QtCore.pyqtSignal(list)

    def run(self):
        global grayScale, colorScaleR, colorScaleG, colorScaleB, colorScaleA, alphaValue, start_time
        pool = multiprocessing.Pool(4)
        if grayScale is not None:
            blendGray = grayScale.getImageAtAlpha(alphaValue)
        elif colorScaleA is None:
            results = [pool.apply_async(colorScaleR.getImageAtAlpha, (alphaValue,)),
                       pool.apply_async(colorScaleG.getImageAtAlpha, (alphaValue,)),
                       pool.apply_async(colorScaleB.getImageAtAlpha, (alphaValue,))]
            blendR = results[0].get()
            blendG = results[1].get()
            blendB = results[2].get()
        else:
            results = [pool.apply_async(colorScaleR.getImageAtAlpha, (alphaValue,)),
                       pool.apply_async(colorScaleG.getImageAtAlpha, (alphaValue,)),
                       pool.apply_async(colorScaleB.getImageAtAlpha, (alphaValue,)),
                       pool.apply_async(colorScaleA.getImageAtAlpha, (alphaValue,))]
            blendR = results[0].get()
            blendG = results[1].get()
            blendB = results[2].get()
            blendA = results[3].get()
        pool.close()
        pool.terminate()
        pool.join()
        if grayScale is not None:
            self.image_complete.emit([blendGray])
        elif colorScaleA is None:
            self.image_complete.emit([blendR, blendG, blendB])
        else:
            self.image_complete.emit([blendR, blendG, blendB, blendA])


class FrameThread(QtCore.QThread):
    def __init__(self, threadQueue, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.queue = threadQueue
    frame_complete = QtCore.pyqtSignal(list)
    update_progress = QtCore.pyqtSignal(int)

    def run(self):
        global grayScale, colorScaleR, colorScaleG, colorScaleB, colorScaleA, start_time
        while True:
            value = self.queue.get()
            pool = multiprocessing.Pool(4)
            if grayScale is not None:
                blendGray = grayScale.getImageAtAlpha(value)
            elif colorScaleA is None:
                results = [pool.apply_async(colorScaleR.getImageAtAlpha, (value,)),
                           pool.apply_async(colorScaleG.getImageAtAlpha, (value,)),
                           pool.apply_async(colorScaleB.getImageAtAlpha, (value,))]
                blendR = results[0].get()
                blendG = results[1].get()
                blendB = results[2].get()
            else:
                results = [pool.apply_async(colorScaleR.getImageAtAlpha, (value,)),
                           pool.apply_async(colorScaleG.getImageAtAlpha, (value,)),
                           pool.apply_async(colorScaleB.getImageAtAlpha, (value,)),
                           pool.apply_async(colorScaleA.getImageAtAlpha, (value,))]
                blendR = results[0].get()
                blendG = results[1].get()
                blendB = results[2].get()
                blendA = results[3].get()
            pool.close()
            pool.terminate()
            pool.join()
            if grayScale is not None:
                self.frame_complete.emit([blendGray])
            elif colorScaleA is None:
                self.frame_complete.emit([blendR, blendG, blendB])
            else:
                self.frame_complete.emit([blendR, blendG, blendB, blendA])
            self.update_progress.emit(1)
            self.queue.task_done()


class MorphingApp(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MorphingApp, self).__init__(parent)
        self.setupUi(self)
        # self.progressBar.setVisible(False)
        self.progressBar.setFixedWidth(0)
        self.setWindowIcon(QtGui.QIcon("./Morphing.ico"))
        self.saveTab_folderDisplayText.setText(ROOT_DIR)
        self.setAcceptDrops(True)
        self.triangleRedValue.installEventFilter(self)
        self.triangleGreenValue.installEventFilter(self)
        self.triangleBlueValue.installEventFilter(self)

        # QtDesigner is (really) bad at setting fixed sizes. This is a simple fix.
        self.blendingImage.setMinimumHeight(259)
        self.tabWidget.setMinimumHeight(307)

        # Defaults on Startup
        self.chosen_left_points = []                                                    # List used to store points confirmed in previous sessions (LEFT)
        self.chosen_right_points = []                                                   # List used to store points confirmed in previous sessions (RIGHT)
        self.added_left_points = []                                                     # List used to store temporary points added in current session (LEFT)
        self.added_right_points = []                                                    # List used to store temporary points added in current session (RIGHT)
        self.confirmed_left_points = []                                                 # List used to store existing points confirmed in current session (LEFT)
        self.confirmed_right_points = []                                                # List used to store existing points confirmed in current session (RIGHT)
        self.placed_points_history = []                                                 # List used to log recent points placed during this session for CTRL + Y
        self.clicked_window_history = [-1]                                              # List used to log the order in which the image windows have been clicked - functions as a "stack"
        self.leftPolyList = []                                                          # List used to store delaunay triangles (LEFT)
        self.rightPolyList = []                                                         # List used to store delaunay triangles (RIGHT)
        self.blendList = []                                                             # List used to store a variable amount of alpha increment frames for full blending
        self.zoomPanRef = []                                                            # List used to store the source image and coordinate that initiate a zoom panning event
        self.movingPoint = ['', '', 0, QtCore.QPoint(-1, -1), QtCore.QPoint(-1, -1)]    # List used to store the type of point being moved as well as it's source, index, previous & current coordinates

        self.startingImagePath = ''                                             # String used to store file path to the left image
        self.endingImagePath = ''                                               # String used to store file path to the right image
        self.startingTextPath = ''                                              # String used to store file path to the left image's text file, if it was pre-made (LEGACY)
        self.endingTextPath = ''                                                # String used to store file path to the right image's text file, if it was pre-made (LEGACY)
        self.startingTextCorePath = ''                                          # String used to store local file path to the left image's corresponding text file
        self.endingTextCorePath = ''                                            # String used to store local file path to the right image's corresponding text file
        self.startingImageName = ''                                             # String used to store the left image's file name
        self.endingImageName = ''                                               # String used to store the right image's file name
        self.startingImageType = ''                                             # String used to store the left image's file type
        self.endingImageType = ''                                               # String used to store the right image's file type
        self.leftTempPath = ''                                                  # String used to store temp file path for resizing left image in GUI
        self.rightTempPath = ''                                                 # String used to store temp file path for resizing right image in GUI
        self.leftTempTextPath = ''                                              # String used to store temp file path for resizing left image in GUI
        self.rightTempTextPath = ''                                             # String used to store temp text file path for resizing right image in GUI
        self.configFilePath = os.path.join(ROOT_DIR, 'configuration.txt')       # String used to store path for PIM's configuration file (GUI defaults)

        self.enableDeletion = 0                                                 # Flag used to indicate whether the most recently created point can be deleted with Backspace
        self.triangleUpdate = 0                                                 # Flag used to indicate whether triangles need to be repainted (or removed) in the next paint event
        self.triangleUpdatePref = 0                                             # Flag used to remember whether the user wants to display triangles (in the case that they are forced off)
        self.imageScalar = 0                                                    # Value used to scale created points to where they visually line up with the original images
        self.fullBlendValue = 0.05                                              # Value used for determining the spacing between alpha increments when full blending
        self.gifValue = 100                                                     # Value used for determining the amount of time allotted to each frame of a created .gif file

        self.leftSize = (0, 0)                                                  # Tuple used to store the width and height of the displayed left image
        self.rightSize = (0, 0)                                                 # Tuple used to store the width and height of the displayed right image
        self.trueLeftSize = (0, 0)                                              # Tuple used to store the width and height of the original left image
        self.trueRightSize = (0, 0)                                             # Tuple used to store the width and height of the original right image
        self.lastLeftSize = (0, 0)                                              # Tuple used to store the previous size of the left image window before a resize
        self.lastRightSize = (0, 0)                                             # Tuple used to store the previous size of the right image window before a resize
        self.leftZoomData = None                                                # Tuple used to store the coordinates of the user's zoom on the left image. None when zoomed out, (a, b, c, d) when zoomed in
        self.rightZoomData = None                                               # Tuple used to store the coordinates of the user's zoom on the right image. None when zoomed out, (e, f, g, h) when zoomed in

        self.fullBlendComplete = False                                          # Flag used to indicate whether a full blend is displayable
        self.changeFlag = False                                                 # Flag used to indicate when the program should repaint (because Qt loves to very frequently call paint events)
        self.openFlag = True                                                    # Flag used to indicate whether the GUI is open
        self.resizeFlag = False                                                 # Flag used to indicate whether the GUI is being resized
        self.hoverFlag = False                                                  # Flag used to indicate whether a point is being hovered by moveMode (i.e., the user is deciding where to place it again)
        self.deleteMode = False                                                 # Flag used to indicate whether the user is currently attempting to delete specific points via GUI
        self.moveMode = False                                                   # Flag used to indicate whether the user is currently attempting to move specific points via GUI

        self.blendedImage = None                                                # Pre-made reference to a variable that is used to store a singular blended image
        self.threadQueue = queue.Queue()                                        # Constructed queue of all image frames and their RGB[A] layers to be morphed when user starts a full blend. Aids in performance as well as preventing GUI lockup.
        self.imager = ImagerThread()                                            # Object for handling asynchronous execution of blends for the layers of a single-frame blend
        self.framer = FrameThread(self.threadQueue)                             # Object for handling asynchronous execution of blends for the layers of a multiple-frame blend (full blend)
        self.framer.frame_complete.connect(self.frameFinished)                  # Method signal definition to handle and render GUI updates as image frames are blended
        self.framer.update_progress.connect(self.updateProgress)                # Method signal definition to handle and render GUI updates as image frames are blended

        # Logic
        self.loadStartButton.clicked.connect(self.loadDataLeft)                                                                                             # When the first  load image button is clicked, begins loading logic
        self.loadEndButton.clicked.connect(self.loadDataRight)                                                                                              # When the second load image button is clicked, begins loading logic
        self.resizeLeftButton.clicked.connect(self.resizeLeft)                                                                                              # When the left resize button is clicked, begins resizing logic
        self.resizeRightButton.clicked.connect(self.resizeRight)                                                                                            # When the right resize button is clicked, begins resizing logic
        self.triangleBox.clicked.connect(self.updateTriangleStatus)                                                                                         # When the triangle box is clicked, changes flags
        self.comboBox.currentIndexChanged.connect(self.updateTriangleFields)                                                                                # When the RGB data type is changed, update fields accordingly
        self.transparencyBox.stateChanged.connect(self.transparencyUpdate)                                                                                  # When the transparency box is checked or unchecked, changes flags
        self.blendButton.clicked.connect(self.blendImages)                                                                                                  # When the blend button is clicked, begins blending logic
        self.blendBox.stateChanged.connect(self.blendBoxUpdate)                                                                                             # When the blend box is checked or unchecked, changes flags
        self.blendText.returnPressed.connect(self.blendTextDone)                                                                                            # When the return key is pressed, removes focus from the input text window
        self.saveButton.clicked.connect(self.saveMorph)                                                                                                     # When the save button is clicked, begins image saving logic
        self.gifText.returnPressed.connect(self.gifTextDone)                                                                                                # When the return key is pressed, removes focus from the input text window
        self.triangleRedValue.returnPressed.connect(lambda: self.verifyValue('red'))                                                                        # When the user attempts to confirm a new Red   value, validate it
        self.triangleGreenValue.returnPressed.connect(lambda: self.verifyValue('green'))                                                                    # When the user attempts to confirm a new Green value, validate it
        self.triangleBlueValue.returnPressed.connect(lambda: self.verifyValue('blue'))                                                                      # When the user attempts to confirm a new Blue  value, validate it
        self.alphaSlider.valueChanged.connect(self.updateAlpha)                                                                                             # When the alpha slider is moved, reads and formats the value
        self.saveTab_gifQualitySlider.valueChanged.connect(self.updateGifQuality)                                                                           # When the gif   slider is moved, writes the value into indicator
        self.triangleRedSlider.valueChanged.connect(lambda: self.updateColorSlider(self.triangleRedSlider, self.triangleRedValue))                          # When the red   slider is moved, reads the value
        self.triangleGreenSlider.valueChanged.connect(lambda: self.updateColorSlider(self.triangleGreenSlider, self.triangleGreenValue))                    # When the green slider is moved, reads the value
        self.triangleBlueSlider.valueChanged.connect(lambda: self.updateColorSlider(self.triangleBlueSlider, self.triangleBlueValue))                       # When the blue  slider is moved, reads the value
        self.resetPointsButton.clicked.connect(self.resetPoints)                                                                                            # When the reset points button is clicked, begins logic for removing points
        self.resetSliderButton.clicked.connect(self.resetAlphaSlider)                                                                                       # When the reset slider button is clicked, begins logic for resetting it to default
        self.autoCornerButton.clicked.connect(self.autoCorner)                                                                                              # When the add   corner button is clicked, begins logic for adding corner points
        self.saveTab_singleRadio.clicked.connect(self.updateSaveTab)
        self.saveTab_multiRadio.clicked.connect(self.updateSaveTab)
        self.saveTab_frameRadio.clicked.connect(self.updateSaveTab)
        self.saveTab_gifRadio.clicked.connect(self.updateSaveTab)
        self.saveTab_jpgRadio.clicked.connect(self.updateSaveTab)
        self.saveTab_pngRadio.clicked.connect(self.updateSaveTab)
        self.saveTab_folderSelectButton.clicked.connect(self.selectSaveFolder)

        # self.loadConfiguration()
        self.checkUpdate()

    # Simple function for checking whether you are up-to-date. :)
    def checkUpdate(self):
        try:
            resp = requests.get('https://api.github.com/repos/ddowd97/Python-Image-Morpher/releases/latest')
        except requests.exceptions.ConnectionError:
            print('Connection to GitHub API failed due to network connectivity.\nSkipping update check...')
            return
        except:
            print('Failed to check for updates.')
            return

        try:
            with open('version.txt', 'r') as file:
                localVer = file.readline()[1:]

            if resp.status_code == 200 and localVer is not None:
                gitVer = resp.json()["tag_name"][1:]

                for x, y in zip(gitVer.split('.'), localVer.split('.')):
                    if int(x) > int(y):
                        verStr = "Installed: {0}\tAvailable: {1}".format(localVer, gitVer)
                        userResponse = QtWidgets.QMessageBox.question(self, "Update Available", verStr + "\n\nDo you want to update now? This will close the program and open the latest release on your browser. Please extract the zip file over your current installation.", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                        if userResponse == QtWidgets.QMessageBox.Yes:
                            webbrowser.open('https://github.com/ddowd97/Python-Image-Morpher/releases/latest')
                            sys.exit()
                        return
            elif resp.status_code != 200:
                verStr = "Installed: {0}\tAvailable: {1}".format(localVer, 'NULL')
                userResponse = QtWidgets.QMessageBox.question(self, "Unexpected Error", verStr + "\n\nFailed to check for updates - Unable to retrieve latest GitHub version number.\nDo you want to open  Python Image Morpher's latest release page now?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                if userResponse == QtWidgets.QMessageBox.Yes:
                    webbrowser.open('https://github.com/ddowd97/Python-Image-Morpher/releases/latest')
                    sys.exit()
                return
            else:
                userResponse = QtWidgets.QMessageBox.question(self, "Unexpected Error", "Failed to check for updates - Unable to retrieve local version number.\nPlease check whether version.txt is present and unmodified.\n\nDo you want to open  Python Image Morpher's latest release page now?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                if userResponse == QtWidgets.QMessageBox.Yes:
                    webbrowser.open('https://github.com/ddowd97/Python-Image-Morpher/releases/latest')
                    sys.exit()
                return
        except FileNotFoundError:
            print('Cannot obtain installed version number. Is version.txt missing?')
        except UnboundLocalError:
            print('Cannot obtain online version number due to network connectivity issue.')
        except:
            print('There was an error while checking for updates.')

    # TODO
    # Function executed on startup that either generates or loads (and corrects, if needed) configuration.txt to store default parameters
    def loadConfiguration(self):
        configVars = {'ImagePath': os.path.join(ROOT_DIR, 'Images_Points')}
        if not os.path.exists(self.configFilePath):
            with open(self.configFilePath, 'w') as file:
                for x in configVars:
                    file.write("{:>8}='{:>8}'".format(x, configVars[x]))
            self.configImagePathString.setText(configVars['ImagePath'])

    # TODO
    # Function that validates and saves new configuration parameters set by the user in PIM's GUI
    def saveConfiguration(self):
        ...

    # TODO
    # Function that resets configuration parameters to default values
    def resetConfiguration(self):
        ...

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if source == self.triangleRedValue:
                self.triangleRedValue.setFocus(QtCore.Qt.MouseFocusReason)
                self.triangleRedValue.setCursorPosition(0)
                return True
            elif source == self.triangleGreenValue:
                self.triangleGreenValue.setFocus(QtCore.Qt.MouseFocusReason)
                self.triangleGreenValue.setCursorPosition(0)
                return True
            elif source == self.triangleBlueValue:
                self.triangleBlueValue.setFocus(QtCore.Qt.MouseFocusReason)
                self.triangleBlueValue.setCursorPosition(0)
                return True
        if event.type() == QtCore.QEvent.FocusOut:
            if source == self.triangleRedValue:     self.verifyValue('red')
            elif source == self.triangleGreenValue: self.verifyValue('green')
            elif source == self.triangleBlueValue:  self.verifyValue('blue')
        return super().eventFilter(source, event)

    def imageFinished(self, blendList):
        global start_time
        if len(blendList) == 1:
            self.blendedImage = blendList[0]
            self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(self.blendedImage.data, self.blendedImage.shape[1], self.blendedImage.shape[0], QtGui.QImage.Format_Grayscale8)))
            self.notificationLine.setText(" Morph took " + "{:.3f}".format(time.time() - start_time) + " seconds.\n")
        elif len(blendList) == 3:
            self.blendedImage = np.dstack((blendList[0], blendList[1], blendList[2]))
            self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(self.blendedImage.data, self.blendedImage.shape[1], self.blendedImage.shape[0], self.blendedImage.shape[1] * 3, QtGui.QImage.Format_RGB888)))
            self.notificationLine.setText(" RGB morph took " + "{:.3f}".format(time.time() - start_time) + " seconds.\n")
        else:
            self.blendedImage = np.dstack((blendList[0], blendList[1], blendList[2], blendList[3]))
            self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(self.blendedImage.data, self.blendedImage.shape[1], self.blendedImage.shape[0], QtGui.QImage.Format_RGBA8888)))
            self.notificationLine.setText(" RGBA morph took " + "{:.3f}".format(time.time() - start_time) + " seconds.\n")
        self.updateMorphingWidget(True)
        self.updateSaveTab()
        self.setFocus()

    def frameFinished(self, blendList):
        global start_time
        if len(blendList) == 1:
            self.blendList.append(blendList[0])
            try:
                temp = self.blendList[-1]
                self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], QtGui.QImage.Format_Grayscale8)))
            except IndexError:
                pass
        elif len(blendList) == 3:
            self.blendList.append(np.dstack((blendList[0], blendList[1], blendList[2])))
            try:
                temp = self.blendList[-1]
                self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], temp.shape[1] * 3, QtGui.QImage.Format_RGB888)))
            except IndexError:
                pass
        else:
            self.blendList.append(np.dstack((blendList[0], blendList[1], blendList[2], blendList[3])))
            try:
                temp = self.blendList[-1]
                self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], QtGui.QImage.Format_RGBA8888)))
            except IndexError:
                pass

        if self.threadQueue.empty() and len(self.blendList) == math.ceil(1 / self.fullBlendValue) + 1:
            temp = self.blendList[int(float(self.alphaValue.text()) / self.fullBlendValue)]
            if len(blendList) == 1:
                self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], QtGui.QImage.Format_Grayscale8)))
                self.notificationLine.setText(" Morph took " + "{:.3f}".format(time.time() - start_time) + " seconds.\n")
            if len(blendList) == 3:
                self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], temp.shape[1] * 3, QtGui.QImage.Format_RGB888)))
                self.notificationLine.setText(" RGB morph took " + "{:.3f}".format(time.time() - start_time) + " seconds.\n")
            else:
                self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], QtGui.QImage.Format_RGBA8888)))
                self.notificationLine.setText(" RGBA morph took " + "{:.3f}".format(time.time() - start_time) + " seconds.\n")
            self.updateMorphingWidget(True)
            self.fullBlendComplete = True
            self.updateSaveTab()
            self.animateProgressBar()
        self.setFocus()

    # Animation for updates of the progress bar during full blends
    def updateProgress(self):
        if self.fullBlendComplete is not True:
            self.animationProgress = QtCore.QPropertyAnimation(self.progressBar, b"value")
            self.animationProgress.setDuration(125)
            self.animationProgress.setStartValue(self.progressBar.value())
            self.animationProgress.setEndValue(self.progressBar.value() + round(1 / (1 / self.fullBlendValue + 1) * 100))
            self.animationProgress.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animationProgress.start()

    # Animation for showing and hiding the progress bar during full blends
    def animateProgressBar(self):
        if self.progressBar.minimumWidth() == 0:
            self.animationGrow = QtCore.QPropertyAnimation(self.progressBar, b"minimumWidth")
            self.animationGrow.setDuration(350)
            self.animationGrow.setStartValue(self.progressBar.minimumWidth())
            self.animationGrow.setEndValue(self.tabWidget.width() + 2)
            self.animationGrow.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animationGrow.start()
        else:
            self.animationShrink = QtCore.QPropertyAnimation(self.progressBar, b"minimumWidth")
            self.animationShrink.setDuration(350)
            self.animationShrink.setStartValue(self.progressBar.minimumWidth())
            self.animationShrink.setEndValue(0)
            self.animationShrink.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animationShrink.start()

    # Function override for when the program is closed.
    # Ensures that the asynchronous resize event observer terminates and removes any temporary files generated.
    def closeEvent(self, event):
        self.openFlag = False
        for file in os.listdir(ROOT_DIR):
            if file.startswith("PIM_Temp_"):
                os.remove(os.path.join(ROOT_DIR, file))

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
        if self.gifText.text().strip() == 'ms':
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
        elif param == "red":
            value = 0
            if self.comboBox.currentText() == 'Binary':
                if self.triangleRedValue.text() != '': value = min(int(self.triangleRedValue.text(), 2), 255)
                self.triangleRedSlider.setValue(value)
                self.triangleRedValue.setText(bin(value)[2:].zfill(8))
            elif self.comboBox.currentText() == 'Decimal':
                if self.triangleRedValue.text() != '': value = min(int(self.triangleRedValue.text()), 255)
                self.triangleRedSlider.setValue(value)
                self.triangleRedValue.setText(str(value).zfill(3))
            elif self.comboBox.currentText() == 'Hexadecimal':
                if self.triangleRedValue.text() not in {'', '0x'}: value = min(int(self.triangleRedValue.text()[2:], 16), 255)
                self.triangleRedSlider.setValue(value)
                self.triangleRedValue.setText('0x' + hex(value)[2:].zfill(2).upper())
            self.triangleRedValue.clearFocus()
        elif param == "green":
            value = 0
            if self.comboBox.currentText() == 'Binary':
                if self.triangleGreenValue.text() != '': value = min(int(self.triangleGreenValue.text(), 2), 255)
                self.triangleGreenSlider.setValue(value)
                self.triangleGreenValue.setText(bin(value)[2:].zfill(8))
            elif self.comboBox.currentText() == 'Decimal':
                if self.triangleGreenValue.text() != '': value = min(int(self.triangleGreenValue.text()), 255)
                self.triangleGreenSlider.setValue(value)
                self.triangleGreenValue.setText(str(value).zfill(3))
            elif self.comboBox.currentText() == 'Hexadecimal':
                if self.triangleGreenValue.text() not in {'', '0x'}: value = min(int(self.triangleGreenValue.text()[2:], 16), 255)
                self.triangleGreenSlider.setValue(value)
                self.triangleGreenValue.setText('0x' + hex(value)[2:].zfill(2).upper())
            self.triangleGreenValue.clearFocus()
        elif param == "blue":
            value = 0
            if self.comboBox.currentText() == 'Binary':
                if self.triangleBlueValue.text() != '': value = min(int(self.triangleBlueValue.text(), 2), 255)
                self.triangleBlueSlider.setValue(value)
                self.triangleBlueValue.setText(bin(value)[2:].zfill(8))
            elif self.comboBox.currentText() == 'Decimal':
                if self.triangleBlueValue.text() != '': value = min(int(self.triangleBlueValue.text()), 255)
                self.triangleBlueSlider.setValue(value)
                self.triangleBlueValue.setText(str(value).zfill(3))
            elif self.comboBox.currentText() == 'Hexadecimal':
                if self.triangleBlueValue.text() not in {'', '0x'}: value = min(int(self.triangleBlueValue.text()[2:], 16), 255)
                self.triangleBlueSlider.setValue(value)
                self.triangleBlueValue.setText('0x' + hex(value)[2:].zfill(2).upper())
            self.triangleBlueValue.clearFocus()

    # Just for fun - a combo box function that dynamically changes the format of triangle color values.
    # Currently works with Binary, Decimal, and Hexadecimal, but more could potentially be added later.
    def updateTriangleFields(self):
        if self.comboBox.currentText() == 'Binary':
            redValue = '00000000'
            greenValue = '00000000'
            blueValue = '00000000'
            # Decimal to Binary
            if self.triangleRedValue.width() == self.triangleGreenValue.width() == self.triangleBlueValue.width() == 40:
                if self.triangleRedValue.text() != '': redValue = bin(int(self.triangleRedValue.text()))[2:].zfill(8)
                if self.triangleGreenValue.text() != '': greenValue = bin(int(self.triangleGreenValue.text()))[2:].zfill(8)
                if self.triangleBlueValue.text() != '': blueValue = bin(int(self.triangleBlueValue.text()))[2:].zfill(8)
            # Hexadecimal to Binary
            elif self.triangleRedValue.width() == self.triangleGreenValue.width() == self.triangleBlueValue.width() == 50:
                if self.triangleRedValue.text() not in {'', '0x'}: redValue = bin(int(self.triangleRedValue.text()[2:], 16))[2:].zfill(8)
                if self.triangleGreenValue.text() not in {'', '0x'}: greenValue = bin(int(self.triangleGreenValue.text()[2:], 16))[2:].zfill(8)
                if self.triangleBlueValue.text() not in {'', '0x'}: blueValue = bin(int(self.triangleBlueValue.text()[2:], 16))[2:].zfill(8)
            self.triangleRedValue.setMinimumWidth(80)
            self.triangleRedSlider.setMinimumWidth(160)
            self.triangleGreenValue.setMinimumWidth(80)
            self.triangleGreenSlider.setMinimumWidth(160)
            self.triangleBlueValue.setMinimumWidth(80)
            self.triangleBlueSlider.setMinimumWidth(160)
            self.triangleRedValue.setInputMask("BBBBBBBB")
            self.triangleGreenValue.setInputMask("BBBBBBBB")
            self.triangleBlueValue.setInputMask("BBBBBBBB")
            self.triangleRedValue.setText(redValue)
            self.triangleGreenValue.setText(greenValue)
            self.triangleBlueValue.setText(blueValue)
        elif self.comboBox.currentText() == 'Decimal':
            redValue = '000'
            greenValue = '000'
            blueValue = '000'
            # Binary to Decimal:
            if self.triangleRedValue.width() == self.triangleGreenValue.width() == self.triangleBlueValue.width() == 80:
                if self.triangleRedValue.text() != '': redValue = str(int(self.triangleRedValue.text(), 2)).zfill(3)
                if self.triangleGreenValue.text() != '': greenValue = str(int(self.triangleGreenValue.text(), 2)).zfill(3)
                if self.triangleBlueValue.text() != '': blueValue = str(int(self.triangleBlueValue.text(), 2)).zfill(3)
            # Hexadecimal to Decimal
            elif self.triangleRedValue.width() == self.triangleGreenValue.width() == self.triangleBlueValue.width() == 50:
                if self.triangleRedValue.text() not in {'', '0x'}: redValue = str(int(self.triangleRedValue.text()[2:], 16)).zfill(3)
                if self.triangleGreenValue.text() not in {'', '0x'}: greenValue = str(int(self.triangleGreenValue.text()[2:], 16)).zfill(3)
                if self.triangleBlueValue.text() not in {'', '0x'}: blueValue = str(int(self.triangleBlueValue.text()[2:], 16)).zfill(3)
            self.triangleRedValue.setMinimumWidth(40)
            self.triangleRedSlider.setMinimumWidth(200)
            self.triangleGreenValue.setMinimumWidth(40)
            self.triangleGreenSlider.setMinimumWidth(200)
            self.triangleBlueValue.setMinimumWidth(40)
            self.triangleBlueSlider.setMinimumWidth(200)
            self.triangleRedValue.setInputMask("000")
            self.triangleGreenValue.setInputMask("000")
            self.triangleBlueValue.setInputMask("000")
            self.triangleRedValue.setText(redValue)
            self.triangleGreenValue.setText(greenValue)
            self.triangleBlueValue.setText(blueValue)
        elif self.comboBox.currentText() == 'Hexadecimal':
            redValue = '0x00'
            greenValue = '0x00'
            blueValue = '0x00'
            # Binary to Hexadecimal
            if self.triangleRedValue.width() == self.triangleGreenValue.width() == self.triangleBlueValue.width() == 80:
                if self.triangleRedValue.text() != '': redValue = '0x' + hex(int(self.triangleRedValue.text(), 2))[2:].zfill(2).upper()
                if self.triangleGreenValue.text() != '': greenValue = '0x' + hex(int(self.triangleGreenValue.text(), 2))[2:].zfill(2).upper()
                if self.triangleBlueValue.text() != '': blueValue = '0x' + hex(int(self.triangleBlueValue.text(), 2))[2:].zfill(2).upper()
            # Decimal to Hexadecimal
            elif self.triangleRedValue.width() == self.triangleGreenValue.width() == self.triangleBlueValue.width() == 40:
                if self.triangleRedValue.text() != '': redValue = '0x' + hex(int(self.triangleRedValue.text()))[2:].zfill(2).upper()
                if self.triangleGreenValue.text() != '': greenValue = '0x' + hex(int(self.triangleGreenValue.text()))[2:].zfill(2).upper()
                if self.triangleBlueValue.text() != '': blueValue = '0x' + hex(int(self.triangleBlueValue.text()))[2:].zfill(2).upper()
            self.triangleRedValue.setMinimumWidth(50)
            self.triangleRedSlider.setMinimumWidth(190)
            self.triangleGreenValue.setMinimumWidth(50)
            self.triangleGreenSlider.setMinimumWidth(190)
            self.triangleBlueValue.setMinimumWidth(50)
            self.triangleBlueSlider.setMinimumWidth(190)
            self.triangleRedValue.setInputMask("\\0\\xHH")
            self.triangleGreenValue.setInputMask("\\0\\xHH")
            self.triangleBlueValue.setInputMask("\\0\\xHH")
            self.triangleRedValue.setText(redValue)
            self.triangleGreenValue.setText(greenValue)
            self.triangleBlueValue.setText(blueValue)

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
        self.comboBox.setEnabled(val)
        self.triangleLabel.setEnabled(val)
        self.triangleRed.setEnabled(val)
        self.triangleGreen.setEnabled(val)
        self.triangleBlue.setEnabled(val)
        self.triangleRedSlider.setEnabled(val)
        self.triangleGreenSlider.setEnabled(val)
        self.triangleBlueSlider.setEnabled(val)
        self.triangleRedValue.setEnabled(val)
        self.triangleGreenValue.setEnabled(val)
        self.triangleBlueValue.setEnabled(val)

    # Macro function to save unnecessary repetitions of the same few lines of code.
    # Essentially toggles all functions within the morphing widget when necessary and where applicable.
    def updateMorphingWidget(self, val):
        self.blendButton.setEnabled(val and self.startingImage.hasScaledContents() and self.endingImage.hasScaledContents())
        self.alphaSlider.setEnabled(val)
        self.blendBox.setEnabled(val)
        self.blendText.setEnabled(val and self.blendBox.isChecked())
        self.saveButton.setEnabled(val and (len(self.blendList) or self.blendedImage is not None))
        self.resetSliderButton.setEnabled(val and self.alphaSlider.maximum() != 20)
        self.resizeLeftButton.setEnabled(val)
        self.resizeRightButton.setEnabled(val)
        self.autoCornerButton.setEnabled(val and not (len(self.added_left_points) or len(self.added_right_points)))
        self.resetPointsButton.setEnabled(val and (len(self.confirmed_left_points) or len(self.chosen_left_points) or len(self.confirmed_right_points) or len(self.chosen_right_points)))
        self.transparencyBox.setEnabled(val)
        self.alphaValue.setEnabled(val)
        self.gifText.setEnabled(val and len(self.blendList))

    # Macro function to save unnecessary repetitions of the same few lines of code.
    # Handles dynamic GUI behavior of save tab with respect to morphing and user input
    def updateSaveTab(self):
        isOutput = self.blendingImage.hasScaledContents()
        self.saveTab_outputFormatGroup.setEnabled(isOutput)
        self.saveTab_fileSettingsGroup.setEnabled(isOutput)
        # self.saveTab_fileEstimateLabel.setEnabled(isOutput)
        # self.saveTab_filenameText.setEnabled(isOutput)
        self.saveTab_folderDisplayText.setEnabled(isOutput)
        self.saveTab_folderSelectButton.setEnabled(isOutput)
        self.saveButton.setEnabled(isOutput)
        self.saveTab_multiRadio.setEnabled(isOutput and self.saveTab_outputFormatGroup.isEnabled() and self.fullBlendComplete)
        self.saveTab_fullBlendGroup.setEnabled(isOutput and self.saveTab_outputFormatGroup.isEnabled() and self.fullBlendComplete and self.saveTab_multiRadio.isChecked())
        self.saveTab_gifSettingsGroup.setEnabled(isOutput and self.saveTab_fullBlendGroup.isEnabled() and self.fullBlendComplete and self.saveTab_gifRadio.isChecked())
        self.gifText.setEnabled(isOutput and self.saveTab_fullBlendGroup.isEnabled() and self.fullBlendComplete and self.saveTab_gifRadio.isChecked())
        self.saveTab_checkBoxGroup.setEnabled(isOutput and self.saveTab_fullBlendGroup.isEnabled() and self.fullBlendComplete and self.saveTab_gifRadio.isChecked())
        self.saveTab_loopBox.setEnabled(isOutput and self.saveTab_fullBlendGroup.isEnabled() and self.fullBlendComplete and self.saveTab_gifRadio.isChecked())
        self.saveTab_reverseBox.setEnabled(isOutput and self.saveTab_fullBlendGroup.isEnabled() and self.fullBlendComplete and self.saveTab_gifRadio.isChecked())
        self.saveTab_rewindBox.setEnabled(isOutput and self.saveTab_fullBlendGroup.isEnabled() and self.fullBlendComplete and self.saveTab_gifRadio.isChecked())
        self.saveTab_gifIntervalLabel.setEnabled(isOutput and self.saveTab_fullBlendGroup.isEnabled() and self.fullBlendComplete and self.saveTab_gifRadio.isChecked())
        self.saveTab_gifQualityBox.setEnabled(isOutput and self.saveTab_fullBlendGroup.isEnabled() and self.fullBlendComplete and self.saveTab_gifRadio.isChecked())
        self.saveTab_gifQualityLabel.setEnabled(isOutput and self.saveTab_fullBlendGroup.isEnabled() and self.fullBlendComplete and self.saveTab_gifRadio.isChecked())
        self.saveTab_gifQualitySlider.setEnabled(isOutput and self.saveTab_fullBlendGroup.isEnabled() and self.fullBlendComplete and self.saveTab_gifRadio.isChecked())
        self.saveTab_singleRadio.setChecked(self.saveTab_multiRadio.isChecked() and not self.saveTab_fullBlendGroup.isEnabled())
        self.saveTab_imageExtensionGroup.setEnabled(isOutput and (self.saveTab_singleRadio.isChecked() or (self.saveTab_multiRadio.isChecked() and self.saveTab_frameRadio.isChecked())))
        # self.updateSaveEstimate()

    ''' Scrapping this idea for now due to feature creep slowing down development
    # Calculates the expected file size of current blend output (with defined parameters from user), if saved
    def updateSaveEstimate(self):
        val = '0.00'
        if self.blendingImage.hasScaledContents():
            if self.saveTab_singleRadio.isChecked() and self.saveTab_jpgRadio.isChecked():
                if self.fullBlendComplete:
                    temp = self.blendList[round(((self.alphaSlider.value() / self.alphaSlider.maximum()) / self.fullBlendValue) * self.fullBlendValue / self.fullBlendValue)]
                    val = format((temp.shape[0] * temp.shape[1] * temp.shape[2]) / (1048576 * 12), ".2f")
                else:
                    val = format((self.blendedImage.shape[0] * self.blendedImage.shape[1] * self.blendedImage.shape[2]) / (1048576 * 12), ".2f")
            elif self.saveTab_singleRadio.isChecked() and self.saveTab_pngRadio.isChecked():
                if self.fullBlendComplete:
                    temp = self.blendList[round(((self.alphaSlider.value() / self.alphaSlider.maximum()) / self.fullBlendValue) * self.fullBlendValue / self.fullBlendValue)]
                    val = format((temp.shape[0] * temp.shape[1] * temp.shape[2]) / (1048576 * 1.8), ".2f")
                else:
                    val = format((self.blendedImage.shape[0] * self.blendedImage.shape[1] * self.blendedImage.shape[2]) / (1048576 * 1.8), ".2f")
        self.saveTab_fileEstimateLabel.setText('<b>Estimate:</b> ' + val + ' MB')
    '''

    # Self-contained function that checks for the existence of corner points and adds any that are not already present.
    # Can not be invoked while a point is pending (in order to prevent exploits).
    # Written to dynamically work with triangles without any exploits.
    def autoCorner(self):
        tempLeft = [QtCore.QPoint(0, 0), QtCore.QPoint(0, self.startingImage.height() - 1), QtCore.QPoint(self.startingImage.width() - 1, 0), QtCore.QPoint(self.startingImage.width() - 1, self.startingImage.height() - 1)]
        tempRight = [QtCore.QPoint(0, 0), QtCore.QPoint(0, self.endingImage.height() - 1), QtCore.QPoint(self.endingImage.width() - 1, 0), QtCore.QPoint(self.endingImage.width() - 1, self.endingImage.height() - 1)]

        self.triangleBox.setEnabled(1)

        counter = 0
        for leftPoint, rightPoint in zip(tempLeft, tempRight):
            if leftPoint not in self.confirmed_left_points and leftPoint not in self.chosen_left_points and rightPoint not in self.confirmed_right_points and rightPoint not in self.chosen_right_points:
                counter += 1
                self.confirmed_left_points.append(leftPoint)
                self.confirmed_right_points.append(rightPoint)
                self.clicked_window_history.append(0)
                self.clicked_window_history.append(1)

                with open(self.startingTextCorePath, "a") as startingFile:
                    if not os.stat(self.startingTextCorePath).st_size:  # left file is empty
                        startingFile.write('{:>8}{:>8}'.format(str(format(self.confirmed_left_points[-1].x() * self.trueLeftSize[0] / self.leftSize[0], ".1f")), str(format(self.confirmed_left_points[-1].y() * self.trueLeftSize[1] / self.leftSize[1], ".1f"))))
                    else:
                        startingFile.write('\n{:>8}{:>8}'.format(str(format(self.confirmed_left_points[-1].x() * self.trueLeftSize[0] / self.leftSize[0], ".1f")), str(format(self.confirmed_left_points[-1].y() * self.trueLeftSize[1] / self.leftSize[1], ".1f"))))
                with open(self.leftTempTextPath, "a") as startingTempFile:
                    if not os.stat(self.leftTempTextPath).st_size:  # left file is empty
                        startingTempFile.write('{:>8}{:>8}'.format(str(format(self.confirmed_left_points[-1].x(), ".1f")), str(format(self.confirmed_left_points[-1].y(), ".1f"))))
                    else:
                        startingTempFile.write('\n{:>8}{:>8}'.format(str(format(self.confirmed_left_points[-1].x(), ".1f")), str(format(self.confirmed_left_points[-1].y(), ".1f"))))
                with open(self.endingTextCorePath, "a") as endingFile:
                    if not os.stat(self.endingTextCorePath).st_size:  # right file is empty
                        endingFile.write('{:>8}{:>8}'.format(str(format(self.confirmed_right_points[-1].x() * self.trueRightSize[0] / self.rightSize[0], ".1f")), str(format(self.confirmed_right_points[-1].y() * self.trueRightSize[1] / self.rightSize[1], ".1f"))))
                    else:
                        endingFile.write('\n{:>8}{:>8}'.format(str(format(self.confirmed_right_points[-1].x() * self.trueRightSize[0] / self.rightSize[0], ".1f")), str(format(self.confirmed_right_points[-1].y() * self.trueRightSize[1] / self.rightSize[1], ".1f"))))
                with open(self.rightTempTextPath, "a") as endingTempFile:
                    if not os.stat(self.rightTempTextPath).st_size:  # right file is empty
                        endingTempFile.write('{:>8}{:>8}'.format(str(format(self.confirmed_right_points[-1].x(), ".1f")), str(format(self.confirmed_right_points[-1].y(), ".1f"))))
                    else:
                        endingTempFile.write('\n{:>8}{:>8}'.format(str(format(self.confirmed_right_points[-1].x(), ".1f")), str(format(self.confirmed_right_points[-1].y(), ".1f"))))
        if counter:
            self.refreshPaint()
            if counter == 1:
                self.notificationLine.setText(" Successfully added a new corner point.")
            else:
                self.notificationLine.setText(" Successfully added " + str(counter) + " new corner points.")
        else:
            self.notificationLine.setText(" Failed to add any new corner points.")

        self.enableDeletion = 0
        self.displayTriangles()
        self.triangleBox.setChecked(self.triangleUpdatePref)
        self.blendButton.setEnabled(1)
        self.resetPointsButton.setEnabled(1)

    # When confirmed, wipes the slate clean, erasing all placed points from the GUI and relevant files.
    def resetPoints(self):
        userResponse = QtWidgets.QMessageBox.question(self, "Warning", "Are you sure you want to reset points?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel)
        if userResponse == QtWidgets.QMessageBox.Yes:
            self.triangleUpdatePref = int(self.triangleBox.isChecked())
            self.blendButton.setEnabled(0)
            self.resetPointsButton.setEnabled(0)
            self.autoCornerButton.setEnabled(1)
            self.triangleBox.setChecked(0)
            self.triangleBox.setEnabled(0)
            self.added_left_points.clear()
            self.added_right_points.clear()
            self.confirmed_left_points.clear()
            self.confirmed_right_points.clear()
            self.chosen_left_points.clear()
            self.chosen_right_points.clear()
            self.leftPolyList.clear()
            self.rightPolyList.clear()

            if os.path.isfile(self.startingTextCorePath):
                os.remove(self.startingTextCorePath)

            if os.path.isfile(self.endingTextCorePath):
                os.remove(self.endingTextCorePath)

            if os.path.isfile(self.leftTempTextPath):
                os.remove(self.leftTempTextPath)

            if os.path.isfile(self.rightTempTextPath):
                os.remove(self.rightTempTextPath)

            self.enableDeletion = 0
            self.refreshPaint()

            self.notificationLine.setText(" Successfully reset points.")

    # Macro function to save unnecessary repetitions of the same few lines of code.
    # Deletes the user's highlighted point pair (in delete mode) from all four relevant files in use.
    def deletePoint(self, filePath):
        index = self.movingPoint[2] + (0 if self.movingPoint[0] == 'red' else (len(self.chosen_left_points) if 'left' in filePath else len(self.chosen_right_points)))
        data = open(filePath, 'r').readlines()
        del data[index]
        if data:
            if len(data) - 1 > index:
                data[index] = data[index][0:int(len(data[index]) - 1)] + '\n'
            else:
                data[-1] = data[-1][0:int(len(data[-1]) - 1)]  # Remove \n
            open(filePath, 'w').writelines(data)
        else:
            os.remove(filePath)

    # Function that resets the alpha slider (for use after setting a full blend value that has modified the slider).
    # Resets the full blend value as well, just to prevent any weird behavior from ever occurring.
    def resetAlphaSlider(self):
        self.fullBlendComplete = False
        self.alphaSlider.setMaximum(20)
        self.alphaSlider.setTickInterval(2)
        self.fullBlendValue = 0.05
        self.blendText.setText('0.05')
        self.alphaValue.setText('0.5')
        self.alphaSlider.setValue(10)
        self.resetSliderButton.setEnabled(0)

    # Function that handles the rendering of points and triangles onto the GUI when manually called.
    # Dynamically handles changes in point and polygon lists to be compatible with resetPoints, autoCorner, etc.
    def paintEvent(self, paint_event):
        if self.changeFlag or self.pointSlider.valueChanged or self.zoomSlider.valueChanged:
            if os.path.exists(self.leftTempPath):
                leftPic = QtGui.QPixmap(self.leftTempPath)
            else:
                leftPic = QtGui.QPixmap(self.startingImagePath)
            if os.path.exists(self.rightTempPath):
                rightPic = QtGui.QPixmap(self.rightTempPath)
            else:
                rightPic = QtGui.QPixmap(self.endingImagePath)
            pen = QtGui.QPen()
            pen.setWidth(self.pointSlider.value())
            leftpainter = QtGui.QPainter(leftPic)
            rightpainter = QtGui.QPainter(rightPic)
            pointWidth = self.pointSlider.value()

            # Handles drawing the currently loaded images' delaunay triangles, if enabled
            if self.triangleUpdate == 1:
                if len(self.leftPolyList) == len(self.rightPolyList) > 0:
                    pointWidth *= 1.7
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

            rightpainter.setBrush(QtGui.QColor(255, 0, 0, 255))
            for x in self.chosen_right_points:
                rightpainter.drawEllipse(x, pointWidth, pointWidth)

            rightpainter.setBrush(QtGui.QColor(0, 255, 0, 255))
            for x in self.added_right_points:
                rightpainter.drawEllipse(x, pointWidth, pointWidth)

            rightpainter.setBrush(QtGui.QColor(0, 0, 255, 255))
            for x in self.confirmed_right_points:
                rightpainter.drawEllipse(x, pointWidth, pointWidth)

            # When in Move Mode: Handles "dragging" of the point that is being moved elsewhere
            # Additionally highlights the other image's corresponding point affected by the current change in order to aid the user's understanding of their action
            if self.hoverFlag:
                if self.movingPoint[1] == 'LEFT':
                    leftpainter.setBrush(QtGui.QColor('black'))
                    leftpainter.drawEllipse(self.movingPoint[4], pointWidth + 1, pointWidth + 1)
                    leftpainter.setBrush(QtGui.QColor(self.movingPoint[0]))
                    leftpainter.drawEllipse(self.movingPoint[4], pointWidth, pointWidth)
                    rightpainter.setBrush(QtGui.QColor('black'))
                    rightpainter.drawEllipse((self.confirmed_right_points if self.movingPoint[0] == 'blue' else self.chosen_right_points)[self.movingPoint[2]], pointWidth + 1, pointWidth + 1)
                    rightpainter.setBrush(QtGui.QColor('yellow'))
                    rightpainter.drawEllipse((self.confirmed_right_points if self.movingPoint[0] == 'blue' else self.chosen_right_points)[self.movingPoint[2]], pointWidth, pointWidth)
                elif self.movingPoint[1] == 'RIGHT':
                    rightpainter.setBrush(QtGui.QColor('black'))
                    rightpainter.drawEllipse(self.movingPoint[4], pointWidth + 1, pointWidth + 1)
                    rightpainter.setBrush(QtGui.QColor(self.movingPoint[0]))
                    rightpainter.drawEllipse(self.movingPoint[4], pointWidth, pointWidth)
                    leftpainter.setBrush(QtGui.QColor('black'))
                    leftpainter.drawEllipse((self.confirmed_left_points if self.movingPoint[0] == 'blue' else self.chosen_left_points)[self.movingPoint[2]], pointWidth + 1, pointWidth + 1)
                    leftpainter.setBrush(QtGui.QColor('yellow'))
                    leftpainter.drawEllipse((self.confirmed_left_points if self.movingPoint[0] == 'blue' else self.chosen_left_points)[self.movingPoint[2]], pointWidth, pointWidth)

            # Determines how the image is ultimately rendered onto the GUI, depending on whether or not there is any zoom applied to either image
            if not self.leftZoomData:
                self.startingImage.setPixmap(leftPic)
            else:
                self.leftZoomData[2] = min(max(0, self.leftZoomData[0] - int(self.leftSize[0] / int(self.zoomSlider.value() * 2))), self.leftSize[0] - int(self.leftSize[0] / self.zoomSlider.value()))
                self.leftZoomData[3] = min(max(0, self.leftZoomData[1] - int(self.leftSize[1] / int(self.zoomSlider.value() * 2))), self.leftSize[1] - int(self.leftSize[1] / self.zoomSlider.value()))
                temp = leftPic.copy(QtCore.QRect(int(self.leftZoomData[2]), int(self.leftZoomData[3]), int(self.leftSize[0] / self.zoomSlider.value()), int(self.leftSize[1] / self.zoomSlider.value())))
                self.startingImage.setPixmap(temp)
            if not self.rightZoomData:
                self.endingImage.setPixmap(rightPic)
            else:
                self.rightZoomData[2] = min(max(0, self.rightZoomData[0] - int(self.rightSize[0] / int(self.zoomSlider.value() * 2))), self.rightSize[0] - int(self.rightSize[0] / self.zoomSlider.value()))
                self.rightZoomData[3] = min(max(0, self.rightZoomData[1] - int(self.rightSize[1] / int(self.zoomSlider.value() * 2))), self.rightSize[1] - int(self.rightSize[1] / self.zoomSlider.value()))
                temp = rightPic.copy(QtCore.QRect(int(self.rightZoomData[2]), int(self.rightZoomData[3]), int(self.rightSize[0] / self.zoomSlider.value()), int(self.rightSize[1] / self.zoomSlider.value())))
                self.endingImage.setPixmap(temp)

            leftpainter.end()
            rightpainter.end()
            self.changeFlag = False

    # Event handler that allows the GUI to react to when the user hovers a file over the GUI
    # If the file is a supported image type, the GUI acknowledges it as acceptable; otherwise, the GUI rejects it
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls:
            if os.path.splitext(e.mimeData().urls()[0].toLocalFile())[1] in ('.jpg', '.jpeg', '.png'):
                e.accept()
                return
        e.ignore()  # else condition, for when the dragged file is not a supported image (e.g. a text file)

    # Event handler that loads supported images if they are dropped onto one of the input windows
    def dropEvent(self, e):
        if 15 < e.pos().x() < self.startingImage.geometry().topRight().x() + 15 and 38 < e.pos().y() < self.startingImage.geometry().bottomRight().y() + 38:
            self.startingImagePath = str(e.mimeData().urls()[0].toLocalFile())
            self.loadDataLeft(True)
        elif self.endingImage.geometry().topLeft().x() + 12 < e.pos().x() < self.endingImage.geometry().topRight().x() + 12 and 38 < e.pos().y() < self.endingImage.geometry().bottomRight().y() + 38:
            self.endingImagePath = str(e.mimeData().urls()[0].toLocalFile())
            self.loadDataRight(True)

    # Event handler for mouse scrolling
    #   Mouse Wheel Up   → Value Increase
    #   Mouse Wheel Down → Value Decrease
    #       CTRL  + Wheel: Macro for the zoom  slider
    #       Shift + Wheel: Macro for the point slider
    #       Alt   + Wheel: Macro for the alpha slider
    def wheelEvent(self, wheel_event):
        # Zoom Slider Macro
        if wheel_event.modifiers() == QtCore.Qt.ControlModifier:
            if wheel_event.angleDelta().y() > 0:
                self.zoomSlider.setValue(self.zoomSlider.value() + 1)
            elif wheel_event.angleDelta().y() < 0:
                self.zoomSlider.setValue(self.zoomSlider.value() - 1)
            self.refreshPaint()
        # Point Slider Macro
        if wheel_event.modifiers() == QtCore.Qt.ShiftModifier:
            if wheel_event.angleDelta().y() > 0:
                self.pointSlider.setValue(self.pointSlider.value() + 1)
            elif wheel_event.angleDelta().y() < 0:
                self.pointSlider.setValue(self.pointSlider.value() - 1)
            self.refreshPaint()
        # Alpha Slider Macro
        if wheel_event.modifiers() == QtCore.Qt.AltModifier:
            if self.alphaSlider.isEnabled():
                if wheel_event.angleDelta().x() > 0:
                    self.alphaSlider.setValue(self.alphaSlider.value() + 1)
                elif wheel_event.angleDelta().x() < 0:
                    self.alphaSlider.setValue(self.alphaSlider.value() - 1)

    # Event handler for keystrokes
    # D toggles the display of delaunay triangles, when possible
    # Q toggles Delete Mode, which is used with the mouse to manually delete specific point pairs
    # E toggles Move Mode, which is used with the mouse to manually move specific points
    # Tab and Shift + Tab will non-circularly switch to the next and previous tab, respectively
    # CTRL + Z will either:
    #       1) Undo the most recently placed temporary (green) point [NOT "the last placed temporary point"], or
    #       2) Undo the most recent confirmed (blue) point pair
    #           a) If this would cause a change in triangle display, the user's preference is remembered
    # CTRL + Y will restore the most recently deleted / undone point(s) in the cache, which is cleared when a new point is placed
    # Backspace will only delete the last placed temporary point, if there is one to delete.
    #       a) It can not be invoked more than one time in succession, and
    #       b) It has no effect on confirmed (blue) points
    def keyPressEvent(self, key_event):
        # Display Triangles Toggle
        if type(key_event) == QtGui.QKeyEvent and key_event.modifiers() == QtCore.Qt.NoModifier and key_event.key() == QtCore.Qt.Key_D and self.triangleBox.isEnabled():
            self.triangleBox.setChecked(not self.triangleBox.isChecked())
            self.displayTriangles()
        # Delete Mode Toggle
        if type(key_event) == QtGui.QKeyEvent and key_event.modifiers() == QtCore.Qt.NoModifier and key_event.key() == QtCore.Qt.Key_Q:
            if self.deleteMode:
                self.deleteMode = False
                QApplication.restoreOverrideCursor()
                QApplication.setOverrideCursor(QtCore.Qt.CursorShape.ArrowCursor)
                QApplication.restoreOverrideCursor()
                self.cursorModeLine.setStyleSheet("background : lightgreen;")
                self.setMouseTracking(False)
                self.notificationLine.setText(" Delete Mode: Disabled")
            else:
                self.deleteMode = True
                QApplication.restoreOverrideCursor()
                QApplication.setOverrideCursor(QtCore.Qt.CursorShape.CrossCursor)
                self.cursorModeLine.setStyleSheet("background : red;")
                self.setMouseTracking(True)
                if self.moveMode:
                    self.moveMode = False
                    self.notificationLine.setText(" Switched Mode: Delete Mode")
                else:
                    self.notificationLine.setText(" Delete Mode: Enabled")
        # Move Move Toggle
        if type(key_event) == QtGui.QKeyEvent and key_event.modifiers() == QtCore.Qt.NoModifier and key_event.key() == QtCore.Qt.Key_E:
            if self.moveMode:
                self.moveMode = False
                QApplication.restoreOverrideCursor()
                QApplication.setOverrideCursor(QtCore.Qt.CursorShape.ArrowCursor)
                QApplication.restoreOverrideCursor()
                self.cursorModeLine.setStyleSheet("background : lightgreen;")
                self.setMouseTracking(False)
                self.notificationLine.setText(" Move Mode: Disabled")
            else:
                self.moveMode = True
                QApplication.restoreOverrideCursor()
                QApplication.setOverrideCursor(QtCore.Qt.CursorShape.PointingHandCursor)
                self.cursorModeLine.setStyleSheet("background : lightblue;")
                self.setMouseTracking(True)
                if self.deleteMode:
                    self.deleteMode = False
                    self.notificationLine.setText(" Switched Mode: Move Mode")
                else:
                    self.notificationLine.setText(" Move Mode: Enabled")

        # Next Tab
        if type(key_event) == QtGui.QKeyEvent and key_event.modifiers() == QtCore.Qt.NoModifier and key_event.key() == QtCore.Qt.Key_Tab:
            self.tabWidget.setCurrentIndex(min(self.tabWidget.currentIndex() + 1, self.tabWidget.count()))
        # Previous Tab
        if type(key_event) == QtGui.QKeyEvent and key_event.modifiers() == QtCore.Qt.ShiftModifier and key_event.key() == QtCore.Qt.Key_Tab:
            self.tabWidget.setCurrentIndex(max(self.tabWidget.currentIndex() - 1, 0))
        # Undo
        if type(key_event) == QtGui.QKeyEvent and key_event.modifiers() == QtCore.Qt.ControlModifier and key_event.key() == QtCore.Qt.Key_Z:
            undoFlag = 0
            if self.startingImage.hasScaledContents() and self.endingImage.hasScaledContents():
                if self.clicked_window_history[-1] == 1 and len(self.added_right_points):
                    self.placed_points_history.append([self.added_right_points.pop(), self.clicked_window_history.pop()])
                    undoFlag = 1
                    self.notificationLine.setText(" Removed right temporary point!")
                elif self.clicked_window_history[-1] == 0 and len(self.added_left_points):
                    self.placed_points_history.append([self.added_left_points.pop(), self.clicked_window_history.pop()])
                    undoFlag = 1
                    self.notificationLine.setText(" Removed left temporary point!")
                elif len(self.confirmed_left_points) and len(self.confirmed_right_points):
                    self.clicked_window_history.pop()
                    self.clicked_window_history.pop()
                    self.placed_points_history.append((self.confirmed_left_points.pop(), self.confirmed_right_points.pop()))

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

                    data3 = open(self.leftTempTextPath, 'r').readlines()
                    del data3[-1]
                    if data3:
                        data3[-1] = data3[-1][0:int(len(data3[-1]) - 1)]  # Remove \n from the previously second to last line
                        open(self.leftTempTextPath, 'w').writelines(data3)
                    else:
                        os.remove(self.leftTempTextPath)
                    data4 = open(self.rightTempTextPath, 'r').readlines()
                    del data4[-1]
                    if data4:
                        data4[-1] = data4[-1][0:int(len(data4[-1]) - 1)]  # Remove \n from the previously second to last line
                        open(self.rightTempTextPath, 'w').writelines(data4)
                    else:
                        os.remove(self.rightTempTextPath)

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
                    undoFlag = 1
                    self.notificationLine.setText(" Removed confirmed point pair!")
                self.refreshPaint()
            self.autoCornerButton.setEnabled(len(self.added_left_points) == len(self.added_right_points) == 0)
            if undoFlag == 0:
                self.notificationLine.setText(" Can't undo!")

        # Redo
        elif type(key_event) == QtGui.QKeyEvent and key_event.modifiers() == QtCore.Qt.ControlModifier and key_event.key() == QtCore.Qt.Key_Y:
            if not len(self.placed_points_history) > 0:
                self.notificationLine.setText(" Can't redo!")
                return

            recoveredData = self.placed_points_history.pop()
            if type(recoveredData) is list:  # Restore added point
                if recoveredData[1] == 0:
                    self.added_left_points.append(recoveredData[0])
                    self.clicked_window_history.append(0)
                    self.notificationLine.setText(" Recovered left temporary point!")
                elif recoveredData[1] == 1:
                    self.added_right_points.append(recoveredData[0])
                    self.clicked_window_history.append(1)
                    self.notificationLine.setText(" Recovered right temporary point!")
                self.refreshPaint()
                self.enableDeletion = 1
                self.autoCornerButton.setEnabled(0)
            elif type(recoveredData) is tuple:  # Restore confirmed point pair
                self.confirmed_left_points.append(recoveredData[0])
                self.confirmed_right_points.append(recoveredData[1])
                self.clicked_window_history.append(0)
                self.clicked_window_history.append(1)

                with open(self.startingTextCorePath, "a") as startingFile:
                    if not os.stat(self.startingTextCorePath).st_size:  # left file is empty
                        startingFile.write('{:>8}{:>8}'.format(
                            str(format(self.confirmed_left_points[-1].x(), ".1f")),
                            str(format(self.confirmed_left_points[-1].y(), ".1f"))))
                    else:
                        startingFile.write('\n{:>8}{:>8}'.format(
                            str(format(self.confirmed_left_points[-1].x(), ".1f")),
                            str(format(self.confirmed_left_points[-1].y(), ".1f"))))
                with open(self.endingTextCorePath, "a") as endingFile:
                    if not os.stat(self.endingTextCorePath).st_size:  # right file is empty
                        endingFile.write('{:>8}{:>8}'.format(
                            str(format(self.confirmed_right_points[-1].x(), ".1f")),
                            str(format(self.confirmed_right_points[-1].y(), ".1f"))))
                    else:
                        endingFile.write('\n{:>8}{:>8}'.format(
                            str(format(self.confirmed_right_points[-1].x(), ".1f")),
                            str(format(self.confirmed_right_points[-1].y(), ".1f"))))
                self.refreshPaint()
                self.displayTriangles()
                self.autoCornerButton.setEnabled(1)
                self.resetPointsButton.setEnabled(1)
                self.notificationLine.setText(" Recovered confirmed point pair!")

        # Delete recent temp
        elif type(key_event) == QtGui.QKeyEvent and key_event.key() == QtCore.Qt.Key_Backspace:
            if self.startingImage.hasScaledContents() and self.endingImage.hasScaledContents() and self.enableDeletion == 1:
                if self.clicked_window_history[-1] == 1 and len(self.added_right_points):
                    self.placed_points_history.append([self.added_right_points.pop(), self.clicked_window_history.pop()])
                    self.enableDeletion = 0
                    self.refreshPaint()
                    self.notificationLine.setText(" Successfully deleted recent temporary point.")
                elif self.clicked_window_history[-1] == 0 and len(self.added_left_points):
                    self.placed_points_history.append([self.added_left_points.pop(), self.clicked_window_history.pop()])
                    self.enableDeletion = 0
                    self.refreshPaint()
                    self.notificationLine.setText(" Successfully deleted recent temporary point.")
                self.autoCornerButton.setEnabled(len(self.added_left_points) == len(self.added_right_points) == 0)

    # Function override of the window resize event.
    # On invocation, recalculates the necessary scalar and size values to keep image displays and point placements accurate.
    # Additionally triggers an "observer" that watches for when resizeEvent() stops firing in order to call resizeImages().
    def resizeEvent(self, event):
        if self.startingImage.hasScaledContents() and self.endingImage.hasScaledContents():
            self.imageScalar = (self.leftSize[0] / (self.startingImage.geometry().topRight().x() - self.startingImage.geometry().topLeft().x()), self.leftSize[1] / (self.startingImage.geometry().bottomRight().y() - self.startingImage.geometry().topLeft().y()))

            if not self.resizeFlag:
                self.resizeFlag = True

                # Instantiate pynput's mouse listener to track when the mouse is released (i.e., when the user stops resizing)
                listener = mouse.Listener(
                    on_click=on_click)
                listener.start()
                # self.checkMouse()

    # Function that resizes the source image + point data to the current size of the GUI's image windows.
    def resizeImages(self):
        if self.startingImage.hasScaledContents() and self.endingImage.hasScaledContents():
            self.resizeFlag = False

            try:
                temp1 = cv2.imread(self.startingImagePath, cv2.IMREAD_UNCHANGED)
                tempLeft = cv2.resize(temp1, (self.startingImage.width(), self.startingImage.height()), interpolation=cv2.INTER_AREA)
            except:
                temp1 = cv2.imdecode(np.fromfile(self.startingImagePath, dtype=np.uint8), -1)
                tempLeft = cv2.resize(temp1, (self.startingImage.width(), self.startingImage.height()), interpolation=cv2.INTER_AREA)
            cv2.imwrite(self.leftTempPath, tempLeft)
            self.leftSize = (tempLeft.shape[1], tempLeft.shape[0])

            try:
                temp2 = cv2.imread(self.endingImagePath, cv2.IMREAD_UNCHANGED)
                tempRight = cv2.resize(temp2, (self.endingImage.width(), self.endingImage.height()), interpolation=cv2.INTER_AREA)
            except:
                temp2 = cv2.imdecode(np.fromfile(self.endingImagePath, dtype=np.uint8), -1)
                tempRight = cv2.resize(temp2, (self.endingImage.width(), self.endingImage.height()), interpolation=cv2.INTER_AREA)
            cv2.imwrite(self.rightTempPath, tempRight)
            self.rightSize = (tempRight.shape[1], tempRight.shape[0])

            # Update Text Files (for Triangle Display)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                if os.path.isfile(self.leftTempTextPath):
                    tempData = np.loadtxt(self.leftTempTextPath)
                    for x in tempData:
                        x *= (self.leftSize[0] / self.lastLeftSize[0], self.leftSize[1] / self.lastLeftSize[1])
                    np.savetxt(self.leftTempTextPath, tempData, fmt='%.1f')
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                if os.path.isfile(self.rightTempTextPath):
                    tempData = np.loadtxt(self.rightTempTextPath)
                    for y in tempData:
                        y *= (self.rightSize[0] / self.lastRightSize[0], self.rightSize[1] / self.lastRightSize[1])
                    np.savetxt(self.rightTempTextPath, tempData, fmt='%.1f')

            # Scale Green Points
            if self.added_left_points:
                self.added_left_points[0] = QtCore.QPoint(int(self.added_left_points[0].x() * self.leftSize[0] / self.lastLeftSize[0]), int(self.added_left_points[0].y() * self.leftSize[1] / self.lastLeftSize[1]))
            if self.added_right_points:
                self.added_right_points[0] = QtCore.QPoint(int(self.added_right_points[0].x() * self.rightSize[0] / self.lastRightSize[0]), int(self.added_right_points[0].y() * self.rightSize[1] / self.lastRightSize[1]))

            # Scale Blue Points
            for index, (leftPointPair, rightPointPair) in enumerate(zip(self.confirmed_left_points, self.confirmed_right_points)):
                self.confirmed_left_points[index] = QtCore.QPoint(round(leftPointPair.x() * self.leftSize[0] / self.lastLeftSize[0]), round(leftPointPair.y() * self.leftSize[1] / self.lastLeftSize[1]))
                self.confirmed_right_points[index] = QtCore.QPoint(round(rightPointPair.x() * self.rightSize[0] / self.lastRightSize[0]), round(rightPointPair.y() * self.rightSize[1] / self.lastRightSize[1]))

            # Scale Red Points
            for index, (leftPointPair, rightPointPair) in enumerate(zip(self.chosen_left_points, self.chosen_right_points)):
                self.chosen_left_points[index] = QtCore.QPoint(round(leftPointPair.x() * self.leftSize[0] / self.lastLeftSize[0]), round(leftPointPair.y() * self.leftSize[1] / self.lastLeftSize[1]))
                self.chosen_right_points[index] = QtCore.QPoint(round(rightPointPair.x() * self.rightSize[0] / self.lastRightSize[0]), round(rightPointPair.y() * self.rightSize[1] / self.lastRightSize[1]))

            self.lastLeftSize = (self.startingImage.width(), self.startingImage.height())
            self.lastRightSize = (self.endingImage.width(), self.endingImage.height())
            self.imageScalar = (self.leftSize[0] / self.startingImage.width(), self.leftSize[1] / self.startingImage.height())
            self.displayTriangles()
            self.refreshPaint()

    # Function that resizes a copy of the left image to the right image's dimensions
    def resizeLeft(self):
        if self.trueLeftSize != self.trueRightSize:
            try:
                img = cv2.imread(self.startingImagePath, cv2.IMREAD_UNCHANGED)
                img = cv2.resize(img, (self.trueRightSize[0], self.trueRightSize[1]), interpolation=cv2.INTER_AREA)
            except:
                img = cv2.imdecode(np.fromfile(self.startingImagePath, dtype=np.uint8), -1)
                img = cv2.resize(img, (self.trueRightSize[0], self.trueRightSize[1]), interpolation=cv2.INTER_AREA)

            for index, pointPair in enumerate(self.chosen_left_points):
                self.chosen_left_points[index] = QtCore.QPoint(int(pointPair.x() * self.trueRightSize[0] / self.leftSize[0]), int(pointPair.y() * self.trueRightSize[1] / self.leftSize[1]))
            for index, pointPair in enumerate(self.confirmed_left_points):
                self.confirmed_left_points[index] = QtCore.QPoint(int(pointPair.x() * self.trueRightSize[0] / self.leftSize[0]), int(pointPair.y() * self.trueRightSize[1] / self.leftSize[1]))
            for index, pointPair in enumerate(self.added_left_points):
                self.added_left_points[index] = QtCore.QPoint(int(pointPair.x() * self.trueRightSize[0] / self.leftSize[0]), int(pointPair.y() * self.trueRightSize[1] / self.leftSize[1]))

            path = ROOT_DIR + '/Images_Points/' + self.startingImageName + '-' + str(self.trueRightSize[0]) + 'x' + str(self.trueRightSize[1]) + self.startingImageType
            textPath = ROOT_DIR + '/Images_Points/' + self.startingImageName + '-' + str(self.trueRightSize[0]) + 'x' + str(self.trueRightSize[1]) + '-' + self.startingImageType[1:] + '.txt'
            cv2.imwrite(path, img)

            open(textPath, 'w').close()
            writeFlag = False
            with open(textPath, "a") as startingFile:
                for pointPair in self.chosen_left_points:
                    if not writeFlag:
                        startingFile.write('{:>8}{:>8}'.format(str(format(pointPair.x(), ".1f")), str(format(pointPair.y(), ".1f"))))
                        writeFlag = True
                    else:
                        startingFile.write('\n{:>8}{:>8}'.format(str(format(pointPair.x(), ".1f")), str(format(pointPair.y(), ".1f"))))
                for pointPair in self.confirmed_left_points:
                    if not writeFlag:
                        startingFile.write('{:>8}{:>8}'.format(str(format(pointPair.x(), ".1f")), str(format(pointPair.y(), ".1f"))))
                        writeFlag = True
                    else:
                        startingFile.write('\n{:>8}{:>8}'.format(str(format(pointPair.x(), ".1f")), str(format(pointPair.y(), ".1f"))))
            self.startingImageName += '-' + str(self.rightSize[0]) + 'x' + str(self.rightSize[1])
            self.startingImagePath = path
            self.startingTextCorePath = textPath
            self.startingImage.setPixmap(QtGui.QPixmap(self.startingImagePath))
            self.notificationLine.setText(" Successfully resized left image from " + str(self.leftSize[0]) + "x" + str(self.trueLeftSize[1]) + " to " + str(self.trueRightSize[0]) + "x" + str(self.rightSize[1]))
            self.trueLeftSize = self.trueRightSize
            self.checkResize()
        else:
            self.notificationLine.setText(" Can't resize the left image - both images share the same dimensions!")

    # Function that resizes a copy of the right image to the left image's dimensions
    def resizeRight(self):
        if self.trueLeftSize != self.trueRightSize:
            try:
                img = cv2.imread(self.endingImagePath, cv2.IMREAD_UNCHANGED)
                img = cv2.resize(img, (self.trueLeftSize[0], self.trueLeftSize[1]), interpolation=cv2.INTER_AREA)
            except:
                img = cv2.imdecode(np.fromfile(self.endingImagePath, dtype=np.uint8), -1)
                img = cv2.resize(img, (self.trueLeftSize[0], self.trueLeftSize[1]), interpolation=cv2.INTER_AREA)

            for index, pointPair in enumerate(self.chosen_right_points):
                self.chosen_right_points[index] = QtCore.QPoint(int(pointPair.x() * self.trueLeftSize[0] / self.rightSize[0]), int(pointPair.y() * self.trueLeftSize[1] / self.rightSize[1]))
            for index, pointPair in enumerate(self.confirmed_right_points):
                self.confirmed_right_points[index] = QtCore.QPoint(int(pointPair.x() * self.trueLeftSize[0] / self.rightSize[0]), int(pointPair.y() * self.trueLeftSize[1] / self.rightSize[1]))
            for index, pointPair in enumerate(self.added_right_points):
                self.added_right_points[index] = QtCore.QPoint(int(pointPair.x() * self.trueLeftSize[0] / self.rightSize[0]), int(pointPair.y() * self.trueLeftSize[1] / self.rightSize[1]))

            path = ROOT_DIR + '/Images_Points/' + self.endingImageName + '-' + str(self.trueLeftSize[0]) + 'x' + str(self.trueLeftSize[1]) + self.endingImageType
            textPath = ROOT_DIR + '/Images_Points/' + self.endingImageName + '-' + str(self.trueLeftSize[0]) + 'x' + str(self.trueLeftSize[1]) + '-' + self.endingImageType[1:] + '.txt'
            cv2.imwrite(path, img)

            open(textPath, 'w').close()
            writeFlag = False
            with open(textPath, "a") as endingFile:
                for pointPair in self.chosen_right_points:
                    if not writeFlag:
                        endingFile.write('{:>8}{:>8}'.format(str(format(pointPair.x(), ".1f")), str(format(pointPair.y(), ".1f"))))
                        writeFlag = True
                    else:
                        endingFile.write('\n{:>8}{:>8}'.format(str(format(pointPair.x(), ".1f")), str(format(pointPair.y(), ".1f"))))
                for pointPair in self.confirmed_right_points:
                    if not writeFlag:
                        endingFile.write('{:>8}{:>8}'.format(str(format(pointPair.x(), ".1f")), str(format(pointPair.y(), ".1f"))))
                        writeFlag = True
                    else:
                        endingFile.write('\n{:>8}{:>8}'.format(str(format(pointPair.x(), ".1f")), str(format(pointPair.y(), ".1f"))))
            self.endingImageName += '-' + str(self.trueLeftSize[0]) + 'x' + str(self.trueLeftSize[1])
            self.endingImagePath = path
            self.endingTextCorePath = textPath
            self.endingImage.setPixmap(QtGui.QPixmap(self.endingImagePath))
            self.notificationLine.setText(" Successfully resized right image from " + str(self.rightSize[0]) + "x" + str(self.trueRightSize[1]) + " to " + str(self.trueLeftSize[0]) + "x" + str(self.leftSize[1]))
            self.trueRightSize = self.trueLeftSize
            self.checkResize()
        else:
            self.notificationLine.setText(" Can't resize the right image - both images share the same dimensions!")

    # Macro function to save unnecessary repetitions of the same few lines of code called in resizeLeft() and resizeRight()
    # Simply toggles some program flags and repaints any GUI changes afterwards.
    def checkResize(self):
        self.imageScalar = (self.leftSize[0] / (self.startingImage.geometry().topRight().x() - self.startingImage.geometry().topLeft().x()), self.leftSize[1] / (self.startingImage.geometry().bottomRight().y() - self.startingImage.geometry().topLeft().y()))
        if (len(self.chosen_left_points) + len(self.confirmed_left_points)) == (len(self.chosen_right_points) + len(self.confirmed_right_points)) >= 3:
            self.alphaValue.setEnabled(1)
            self.alphaSlider.setEnabled(1)
            self.blendButton.setEnabled(1)
            self.triangleBox.setEnabled(1)
            self.triangleBox.setChecked(self.triangleUpdatePref)
        else:
            self.alphaValue.setEnabled(0)
            self.alphaSlider.setEnabled(0)
            self.blendButton.setEnabled(0)
            self.triangleBox.setEnabled(0)
            self.triangleBox.setChecked(0)
        self.autoCornerButton.setEnabled(1)
        self.displayTriangles()
        self.resizeLeftButton.setStyleSheet("")
        self.resizeRightButton.setStyleSheet("")

    # Function that handles GUI and file behavior when the mouse is clicked.
    def mousePressEvent(self, cursor_event):
        if (self.deleteMode or self.moveMode) and cursor_event.button() == QtCore.Qt.LeftButton:
            if 15 < cursor_event.pos().x() < self.startingImage.geometry().topRight().x() + 15 and 38 < cursor_event.pos().y() < self.startingImage.geometry().bottomRight().y() + 38 and os.path.exists(self.leftTempTextPath):
                if not self.leftZoomData:
                    leftCoord = QtCore.QPoint(int(cursor_event.pos().x() * self.imageScalar[0]), int(cursor_event.pos().y() * self.imageScalar[1]))
                else:
                    # TODO: Determine correct math for grabbing points during zoom
                    xPos = int(self.leftZoomData[2] + int(cursor_event.pos().x() * self.imageScalar[0] / self.zoomSlider.value()))
                    yPos = int(self.leftZoomData[3] + int(cursor_event.pos().y() * self.imageScalar[1] / self.zoomSlider.value()))
                    leftCoord = QtCore.QPoint(xPos, yPos)
                self.movingPoint[3] = QtCore.QPoint(-1, -1)
                for index, x in enumerate(self.confirmed_left_points):
                    if abs(float(x.x()) - (leftCoord.x() - 15)) <= self.pointSlider.value() - 1 and abs(float(x.y()) - (leftCoord.y() - 38)) <= self.pointSlider.value() - 1:
                        if self.movingPoint[3] == QtCore.QPoint(-1, -1) or (self.movingPoint[3] != QtCore.QPoint(-1, -1) and math.sqrt(math.pow(leftCoord.x() - 15 - x.x(), 2) + math.pow(leftCoord.y() - 38 - x.y(), 2) < math.sqrt(math.pow(leftCoord.x() - 15 - self.movingPoint[3].x(), 2) + math.pow(leftCoord.y() - 38 - self.movingPoint[3].y(), 2)))):
                            if not self.leftZoomData:
                                self.movingPoint = ['blue', 'LEFT', index, x, QtCore.QPoint(leftCoord.x() - 15, leftCoord.y() - 38)]
                            else:
                                self.movingPoint = ['blue', 'LEFT', index, x, QtCore.QPoint(int(self.leftZoomData[2] + int((cursor_event.pos().x() - 15) * self.imageScalar[0] / self.zoomSlider.value())), int(self.leftZoomData[3] + int((cursor_event.pos().y() - 38) * self.imageScalar[1] / self.zoomSlider.value())))]
                for index, x in enumerate(self.chosen_left_points):
                    if abs(float(x.x()) - (leftCoord.x() - 15)) <= self.pointSlider.value() - 1 and abs(float(x.y()) - (leftCoord.y() - 38)) <= self.pointSlider.value() - 1:
                        if self.movingPoint[3] == QtCore.QPoint(-1, -1) or (self.movingPoint[3] != QtCore.QPoint(-1, -1) and math.sqrt(math.pow(leftCoord.x() - 15 - x.x(), 2) + math.pow(leftCoord.y() - 38 - x.y(), 2) < math.sqrt(math.pow(leftCoord.x() - 15 - self.movingPoint[3].x(), 2) + math.pow(leftCoord.y() - 38 - self.movingPoint[3].y(), 2)))):
                            if not self.leftZoomData:
                                self.movingPoint = ['red', 'LEFT', index, x, QtCore.QPoint(leftCoord.x() - 15, leftCoord.y() - 38)]
                            else:
                                self.movingPoint = ['red', 'LEFT', index, x, QtCore.QPoint(leftCoord.x() - 15, leftCoord.y() - 38)]
            elif self.endingImage.geometry().topLeft().x() + 12 < cursor_event.pos().x() < self.endingImage.geometry().topRight().x() + 12 and 38 < cursor_event.pos().y() < self.endingImage.geometry().bottomRight().y() + 38 and os.path.exists(self.rightTempTextPath):
                if not self.rightZoomData:
                    rightCoord = QtCore.QPoint(int(cursor_event.pos().x() * self.imageScalar[0]), int(cursor_event.pos().y() * self.imageScalar[1]))
                else:
                    # TODO: Determine correct math for grabbing points during zoom
                    xPos = int(self.rightZoomData[2] + int(cursor_event.pos().x() * self.imageScalar[0] / self.zoomSlider.value()))
                    yPos = int(self.rightZoomData[3] + int(cursor_event.pos().y() * self.imageScalar[1] / self.zoomSlider.value()))
                    rightCoord = QtCore.QPoint(xPos, yPos)
                self.movingPoint[3] = QtCore.QPoint(-1, -1)
                for index, x in enumerate(self.confirmed_right_points):
                    if abs(float(x.x()) - (rightCoord.x() - (self.endingImage.geometry().topLeft().x() + 12))) <= self.pointSlider.value() - 1 and abs(float(x.y()) - (rightCoord.y() - 38)) <= self.pointSlider.value() - 1:
                        if self.movingPoint[3] == QtCore.QPoint(-1, -1) or (self.movingPoint[3] != QtCore.QPoint(-1, -1) and math.sqrt(math.pow(rightCoord.x() - (self.endingImage.geometry().topLeft().x() + 12) - x.x(), 2) + math.pow(rightCoord.y() - 38 - x.y(), 2) < math.sqrt(math.pow(rightCoord.x() - (self.endingImage.geometry().topLeft().x() + 12) - self.movingPoint[3].x(), 2) + math.pow(rightCoord.y() - 38 - self.movingPoint[3].y(), 2)))):
                            if not self.rightZoomData:
                                self.movingPoint = ['blue', 'RIGHT', index, x, QtCore.QPoint(rightCoord.x() - (self.endingImage.geometry().topLeft().x() + 12), rightCoord.y() - 38)]
                            else:
                                self.movingPoint = ['blue', 'RIGHT', index, x, QtCore.QPoint(int(self.rightZoomData[2] + int((cursor_event.pos().x() - (self.endingImage.geometry().topLeft().x() + 12)) * self.imageScalar[0] / self.zoomSlider.value())), int(self.rightZoomData[3] + int((cursor_event.pos().y() - 38) * self.imageScalar[1] / self.zoomSlider.value())))]
                for index, x in enumerate(self.chosen_right_points):
                    if abs(float(x.x()) - (rightCoord.x() - (self.endingImage.geometry().topLeft().x() + 12))) <= self.pointSlider.value() - 1 and abs(float(x.y()) - (rightCoord.y() - 38)) <= self.pointSlider.value() - 1:
                        if self.movingPoint[3] == QtCore.QPoint(-1, -1) or (self.movingPoint[3] != QtCore.QPoint(-1, -1) and math.sqrt(math.pow(rightCoord.x() - (self.endingImage.geometry().topLeft().x() + 12) - x.x(), 2) + math.pow(rightCoord.y() - 38 - x.y(), 2) < math.sqrt(math.pow(rightCoord.x() - (self.endingImage.geometry().topLeft().x() + 12) - self.movingPoint[3].x(), 2) + math.pow(rightCoord.y() - 38 - self.movingPoint[3].y(), 2)))):
                            if not self.rightZoomData:
                                self.movingPoint = ['red', 'RIGHT', index, x, QtCore.QPoint(rightCoord.x() - (self.endingImage.geometry().topLeft().x() + 12), rightCoord.y() - 38)]
                            else:
                                self.movingPoint = ['red', 'RIGHT', index, x, QtCore.QPoint(rightCoord.x() - (self.endingImage.geometry().topLeft().x() + 12), rightCoord.y() - 38)]
            if self.movingPoint[3] != QtCore.QPoint(-1, -1):
                if self.movingPoint[1] == 'LEFT': (self.confirmed_left_points if self.movingPoint[0] == 'blue' else self.chosen_left_points).remove(self.movingPoint[3])
                elif self.movingPoint[1] == 'RIGHT': (self.confirmed_right_points if self.movingPoint[0] == 'blue' else self.chosen_right_points).remove(self.movingPoint[3])
                if self.deleteMode:
                    if self.movingPoint[1] == 'LEFT': (self.confirmed_right_points if self.movingPoint[0] == 'blue' else self.chosen_right_points).pop(self.movingPoint[2])
                    elif self.movingPoint[1] == 'RIGHT': (self.confirmed_left_points if self.movingPoint[0] == 'blue' else self.chosen_left_points).pop(self.movingPoint[2])
                    self.deletePoint(self.startingTextCorePath)
                    self.deletePoint(self.leftTempTextPath)
                    self.deletePoint(self.endingTextCorePath)
                    self.deletePoint(self.rightTempTextPath)

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
                    self.autoCornerButton.setEnabled(len(self.added_left_points) == len(self.added_right_points) == 0)
                elif self.moveMode:
                    self.setMouseTracking(True)
                    self.hoverFlag = True
                self.displayTriangles()
        # LMB (Place Point)
        elif cursor_event.button() == QtCore.Qt.LeftButton:
            if self.trueLeftSize == self.trueRightSize:
                self.imageScalar = (self.leftSize[0] / self.startingImage.width(), self.leftSize[1] / self.startingImage.height())

                if self.startingImage.hasScaledContents() and self.endingImage.hasScaledContents():
                    # If there are a set of points to confirm
                    if len(self.added_left_points) == len(self.added_right_points) == 1:
                        self.placed_points_history.clear()
                        self.confirmed_left_points.append(self.added_left_points.pop())
                        self.confirmed_right_points.append(self.added_right_points.pop())
                        with open(self.startingTextCorePath, "a") as startingFile:
                            if not os.stat(self.startingTextCorePath).st_size:  # left file is empty
                                startingFile.write('{:>8}{:>8}'.format(str(format(self.confirmed_left_points[-1].x() * self.trueLeftSize[0] / self.leftSize[0], ".1f")), str(format(self.confirmed_left_points[-1].y() * self.trueLeftSize[1] / self.leftSize[1], ".1f"))))
                            else:
                                startingFile.write('\n{:>8}{:>8}'.format(str(format(self.confirmed_left_points[-1].x() * self.trueLeftSize[0] / self.leftSize[0], ".1f")), str(format(self.confirmed_left_points[-1].y() * self.trueLeftSize[1] / self.leftSize[1], ".1f"))))
                        with open(self.leftTempTextPath, "a") as startingTempFile:
                            if not os.stat(self.leftTempTextPath).st_size:  # left file is empty
                                startingTempFile.write('{:>8}{:>8}'.format(str(format(self.confirmed_left_points[-1].x(), ".1f")), str(format(self.confirmed_left_points[-1].y(), ".1f"))))
                            else:
                                startingTempFile.write('\n{:>8}{:>8}'.format(str(format(self.confirmed_left_points[-1].x(), ".1f")), str(format(self.confirmed_left_points[-1].y(), ".1f"))))
                        with open(self.endingTextCorePath, "a") as endingFile:
                            if not os.stat(self.endingTextCorePath).st_size:  # right file is empty
                                endingFile.write('{:>8}{:>8}'.format(str(format(self.confirmed_right_points[-1].x() * self.trueRightSize[0] / self.rightSize[0], ".1f")), str(format(self.confirmed_right_points[-1].y() * self.trueRightSize[1] / self.rightSize[1], ".1f"))))
                            else:
                                endingFile.write('\n{:>8}{:>8}'.format(str(format(self.confirmed_right_points[-1].x() * self.trueRightSize[0] / self.rightSize[0], ".1f")), str(format(self.confirmed_right_points[-1].y() * self.trueRightSize[1] / self.rightSize[1], ".1f"))))
                        with open(self.rightTempTextPath, "a") as endingTempFile:
                            if not os.stat(self.rightTempTextPath).st_size:  # right file is empty
                                endingTempFile.write('{:>8}{:>8}'.format(str(format(self.confirmed_right_points[-1].x(), ".1f")), str(format(self.confirmed_right_points[-1].y(), ".1f"))))
                            else:
                                endingTempFile.write('\n{:>8}{:>8}'.format(str(format(self.confirmed_right_points[-1].x(), ".1f")), str(format(self.confirmed_right_points[-1].y(), ".1f"))))
                        self.refreshPaint()
                        self.displayTriangles()
                        self.autoCornerButton.setEnabled(1)
                        self.resetPointsButton.setEnabled(1)
                        self.notificationLine.setText(" Successfully confirmed set of added points.")
                    # LMB was clicked inside left image
                    if 15 < cursor_event.pos().x() < self.startingImage.geometry().topRight().x() + 15 and 38 < cursor_event.pos().y() < self.startingImage.geometry().bottomRight().y() + 38 and len(self.added_left_points) == 0:
                        self.placed_points_history.clear()
                        if not self.leftZoomData:
                            leftCoord = QtCore.QPoint(int((cursor_event.pos().x() - 15) * self.imageScalar[0]), int((cursor_event.pos().y() - 38) * self.imageScalar[1]))
                        else:
                            xPos = int(self.leftZoomData[2] + int((cursor_event.pos().x() - 15) * self.imageScalar[0] / self.zoomSlider.value()))
                            yPos = int(self.leftZoomData[3] + int((cursor_event.pos().y() - 38) * self.imageScalar[1] / self.zoomSlider.value()))
                            leftCoord = QtCore.QPoint(xPos, yPos)
                        self.added_left_points.append(leftCoord)
                        self.refreshPaint()
                        self.clicked_window_history.append(0)
                        self.enableDeletion = 1
                        self.autoCornerButton.setEnabled(0)
                        self.notificationLine.setText(" Successfully added left temporary point.")
                    # LMB was clicked inside right image
                    elif self.endingImage.geometry().topLeft().x() + 12 < cursor_event.pos().x() < self.endingImage.geometry().topRight().x() + 12 and 38 < cursor_event.pos().y() < self.endingImage.geometry().bottomRight().y() + 38 and len(self.added_right_points) == 0:
                        self.placed_points_history.clear()
                        if not self.rightZoomData:
                            rightCoord = QtCore.QPoint(int((cursor_event.pos().x() - (self.endingImage.geometry().topLeft().x() + 12)) * self.imageScalar[0]), int((cursor_event.pos().y() - 38) * self.imageScalar[1]))
                        else:
                            xPos = int(self.rightZoomData[2] + int((cursor_event.pos().x() - (self.endingImage.geometry().topLeft().x() + 12)) * self.imageScalar[0] / self.zoomSlider.value()))
                            yPos = int(self.rightZoomData[3] + int((cursor_event.pos().y() - 38) * self.imageScalar[1] / self.zoomSlider.value()))
                            rightCoord = QtCore.QPoint(xPos, yPos)
                        self.added_right_points.append(rightCoord)
                        self.refreshPaint()
                        self.clicked_window_history.append(1)
                        self.enableDeletion = 1
                        self.notificationLine.setText(" Successfully added right temporary point.")

                    # Check if 3 or more points exist for two corresponding images so that triangles may be displayed
                    if (len(self.chosen_left_points) + len(self.confirmed_left_points)) == (len(self.chosen_right_points) + len(self.confirmed_right_points)) >= 3:
                        self.triangleBox.setEnabled(1)
                        self.blendButton.setEnabled(1)
                        if self.triangleUpdatePref == 1:
                            self.triangleUpdate = 1
                            self.triangleBox.setChecked(1)
                            self.refreshPaint()
                            self.displayTriangles()
            else:
                if (self.startingImage.geometry().topLeft().x() < cursor_event.pos().x() < self.startingImage.geometry().topRight().x() and self.startingImage.geometry().topLeft().y() < cursor_event.pos().y() < self.startingImage.geometry().bottomRight().y() and len(self.added_left_points) == 0) or (self.endingImage.geometry().topLeft().x() < cursor_event.pos().x() < self.endingImage.geometry().topRight().x() and self.endingImage.geometry().topLeft().y() < cursor_event.pos().y() < self.endingImage.geometry().bottomRight().y() and len(self.added_right_points) == 0):
                    if self.startingImage.hasScaledContents() and self.endingImage.hasScaledContents():
                        self.notificationLine.setText(" Images must be the same size before points can be drawn!")
                    else:
                        self.notificationLine.setText(" Both images must be loaded before points can be drawn!")
        # MMB (Zoom Panning)
        elif cursor_event.button() == QtCore.Qt.MidButton:
            if self.leftZoomData or self.rightZoomData:
                if self.leftZoomData and 15 < cursor_event.pos().x() < self.startingImage.geometry().topRight().x() + 15 and 38 < cursor_event.pos().y() < self.startingImage.geometry().bottomRight().y() + 38:
                    self.zoomPanRef = ['LEFT', cursor_event.pos()]
                elif self.rightZoomData and self.endingImage.geometry().topLeft().x() + 12 < cursor_event.pos().x() < self.endingImage.geometry().topRight().x() + 12 and 38 < cursor_event.pos().y() < self.endingImage.geometry().bottomRight().y() + 38:
                    self.zoomPanRef = ['RIGHT', cursor_event.pos()]
                else:
                    self.zoomPanRef.clear()
                    return
                QApplication.setOverrideCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
                self.setMouseTracking(True)
        # RMB (Toggle Zoom)
        elif cursor_event.button() == QtCore.Qt.RightButton:
            # RMB was clicked inside left image
            if 15 < cursor_event.pos().x() < self.startingImage.geometry().topRight().x() + 15 and 38 < cursor_event.pos().y() < self.startingImage.geometry().bottomRight().y() + 38:
                if not self.leftZoomData:
                    self.leftZoomData = [int((cursor_event.pos().x() - 15) * self.imageScalar[0]), int((cursor_event.pos().y() - 38) * self.imageScalar[1]), 0, 0]
                    self.notificationLine.setText(" Zoomed in on left image.")
                else:
                    self.leftZoomData = None
                    self.notificationLine.setText(" Zoomed out of left image.")
                self.refreshPaint()
            # RMB was clicked inside right image
            elif self.endingImage.geometry().topLeft().x() + 12 < cursor_event.pos().x() < self.endingImage.geometry().topRight().x() + 12 and 38 < cursor_event.pos().y() < self.endingImage.geometry().bottomRight().y() + 38:
                if not self.rightZoomData:
                    self.rightZoomData = [int((cursor_event.pos().x() - (self.endingImage.geometry().topLeft().x() + 12)) * self.imageScalar[0]), int((cursor_event.pos().y() - 38) * self.imageScalar[1]), 0, 0]
                    self.notificationLine.setText(" Zoomed in on right image.")
                else:
                    self.rightZoomData = None
                    self.notificationLine.setText(" Zoomed out of right image.")
                self.refreshPaint()

    # Function that handles zoom panning with MMB for the currently chosen image
    def mouseMoveEvent(self, move_event):
        if self.zoomPanRef:
            if self.zoomPanRef[0] == 'LEFT':
                self.leftZoomData[0] -= (move_event.pos().x() - self.zoomPanRef[1].x()) * (1 / self.zoomSlider.value())
                self.leftZoomData[1] -= (move_event.pos().y() - self.zoomPanRef[1].y()) * (1 / self.zoomSlider.value())
            elif self.zoomPanRef[0] == 'RIGHT':
                self.rightZoomData[0] -= (move_event.pos().x() - self.zoomPanRef[1].x()) * (1 / self.zoomSlider.value())
                self.rightZoomData[1] -= (move_event.pos().y() - self.zoomPanRef[1].y()) * (1 / self.zoomSlider.value())
            self.zoomPanRef[1] = move_event.pos()
            self.refreshPaint()
        elif self.moveMode and self.movingPoint[3] != QtCore.QPoint(-1, -1):
            if (15 < move_event.pos().x() < self.startingImage.geometry().topRight().x() + 15 and 38 < move_event.pos().y() < self.startingImage.geometry().bottomRight().y() + 38) or (self.endingImage.geometry().topLeft().x() + 12 < move_event.pos().x() < self.endingImage.geometry().topRight().x() + 12 and 38 < move_event.pos().y() < self.endingImage.geometry().bottomRight().y() + 38):
                if self.movingPoint[1] == 'LEFT':
                    if not self.leftZoomData:
                        self.movingPoint[4] = QtCore.QPoint(max(0, min(int((move_event.pos().x() - 15) * self.imageScalar[0]), self.startingImage.geometry().topRight().x())),
                                                            max(0, min(int((move_event.pos().y() - 38) * self.imageScalar[1]), self.startingImage.geometry().bottomRight().y() + 38)))
                    else:
                        self.movingPoint[4] = QtCore.QPoint(int(self.leftZoomData[2] + int((move_event.pos().x() - 15) * self.imageScalar[0] / self.zoomSlider.value())),
                                                            int(self.leftZoomData[3] + int((move_event.pos().y() - 38) * self.imageScalar[1] / self.zoomSlider.value())))
                elif self.movingPoint[1] == 'RIGHT':
                    if not self.rightZoomData:
                        self.movingPoint[4] = QtCore.QPoint(max(0, min(int((move_event.pos().x() - (self.endingImage.geometry().topLeft().x() + 12)) * self.imageScalar[0]), self.endingImage.geometry().topRight().x())),
                                                            max(0, min(int((move_event.pos().y() - 38) * self.imageScalar[1]), self.endingImage.geometry().bottomRight().y() + 38)))
                    else:
                        self.movingPoint[4] = QtCore.QPoint(int(self.rightZoomData[2] + int((move_event.pos().x() - 15) * self.imageScalar[0] / self.zoomSlider.value())),
                                                            int(self.rightZoomData[3] + int((move_event.pos().y() - 38) * self.imageScalar[1] / self.zoomSlider.value())))
                self.refreshPaint()

    # Function that ends the zoom panning process when MMB is released
    def mouseReleaseEvent(self, release_event):
        if release_event.button() == QtCore.Qt.MidButton and self.zoomPanRef:
            QApplication.restoreOverrideCursor()
            self.setMouseTracking(False)
            self.zoomPanRef.clear()
        elif release_event.button() == QtCore.Qt.LeftButton and self.hoverFlag:
            self.setMouseTracking(False)
            self.hoverFlag = False
            if self.movingPoint[1] == 'LEFT':
                if self.movingPoint[0] == 'blue':
                    self.confirmed_left_points.insert(self.movingPoint[2], self.movingPoint[4])
                    origData = open(self.startingTextCorePath, 'r').readlines()
                    if origData:
                        origData[len(self.chosen_left_points) + self.movingPoint[2]] = ('\n' if len(self.chosen_left_points) + self.movingPoint[2] == 0 else '') + '{:>8}{:>8}'.format(str(format(self.confirmed_left_points[self.movingPoint[2]].x() * self.trueLeftSize[0] / self.leftSize[0], ".1f")), str(format(self.confirmed_left_points[self.movingPoint[2]].y() * self.trueLeftSize[1] / self.leftSize[1], ".1f"))) + ('\n' if len(self.chosen_left_points) + self.movingPoint[2] != len(origData) - 1 else '')
                        open(self.startingTextCorePath, 'w').writelines(origData)
                    tempData = open(self.leftTempTextPath, 'r').readlines()
                    if tempData:
                        tempData[len(self.chosen_left_points) + self.movingPoint[2]] = ('\n' if len(self.chosen_left_points) + self.movingPoint[2] == 0 else '') + '{:>8}{:>8}'.format(str(format(self.confirmed_left_points[self.movingPoint[2]].x(), ".1f")), str(format(self.confirmed_left_points[self.movingPoint[2]].y(), ".1f"))) + ('\n' if len(self.chosen_left_points) + self.movingPoint[2] != len(origData) - 1 else '')
                        open(self.leftTempTextPath, 'w').writelines(tempData)
                elif self.movingPoint[0] == 'red':
                    self.chosen_left_points.insert(self.movingPoint[2], self.movingPoint[4])
                    origData = open(self.startingTextCorePath, 'r').readlines()
                    if origData:
                        origData[self.movingPoint[2]] = ('\n' if self.movingPoint[2] == 0 else '') + '{:>8}{:>8}'.format(str(format(self.chosen_left_points[self.movingPoint[2]].x() * self.trueLeftSize[0] / self.leftSize[0], ".1f")), str(format(self.chosen_left_points[self.movingPoint[2]].y() * self.trueLeftSize[1] / self.leftSize[1], ".1f"))) + ('\n' if self.movingPoint[2] != len(origData) - 1 else '')
                        open(self.startingTextCorePath, 'w').writelines(origData)
                    tempData = open(self.leftTempTextPath, 'r').readlines()
                    if tempData:
                        tempData[self.movingPoint[2]] = ('\n' if self.movingPoint[2] == 0 else '') + '{:>8}{:>8}'.format(str(format(self.chosen_left_points[self.movingPoint[2]].x(), ".1f")), str(format(self.chosen_left_points[self.movingPoint[2]].y(), ".1f"))) + ('\n' if self.movingPoint[2] != len(origData) - 1 else '')
                        open(self.leftTempTextPath, 'w').writelines(tempData)
            elif self.movingPoint[1] == 'RIGHT':
                if self.movingPoint[0] == 'blue':
                    self.confirmed_right_points.insert(self.movingPoint[2], self.movingPoint[4])
                    origData = open(self.endingTextCorePath, 'r').readlines()
                    if origData:
                        origData[len(self.chosen_right_points) + self.movingPoint[2]] = ('\n' if len(self.chosen_right_points) + self.movingPoint[2] == 0 else '') + '{:>8}{:>8}'.format(str(format(self.confirmed_right_points[self.movingPoint[2]].x() * self.trueRightSize[0] / self.rightSize[0], ".1f")), str(format(self.confirmed_right_points[self.movingPoint[2]].y() * self.trueRightSize[1] / self.rightSize[1], ".1f"))) + ('\n' if len(self.chosen_right_points) + self.movingPoint[2] != len(origData) - 1 else '')
                        open(self.endingTextCorePath, 'w').writelines(origData)
                    tempData = open(self.rightTempTextPath, 'r').readlines()
                    if tempData:
                        tempData[len(self.chosen_right_points) + self.movingPoint[2]] = ('\n' if len(self.chosen_right_points) + self.movingPoint[2] == 0 else '') + '{:>8}{:>8}'.format(str(format(self.confirmed_right_points[self.movingPoint[2]].x(), ".1f")), str(format(self.confirmed_right_points[self.movingPoint[2]].y(), ".1f"))) + ('\n' if len(self.chosen_right_points) + self.movingPoint[2] != len(origData) - 1 else '')
                        open(self.rightTempTextPath, 'w').writelines(tempData)
                elif self.movingPoint[0] == 'red':
                    self.chosen_right_points.insert(self.movingPoint[2], self.movingPoint[4])
                    origData = open(self.endingTextCorePath, 'r').readlines()
                    if origData:
                        origData[self.movingPoint[2]] = ('\n' if self.movingPoint[2] == 0 else '') + '{:>8}{:>8}'.format(str(format(self.chosen_right_points[self.movingPoint[2]].x() * self.trueRightSize[0] / self.rightSize[0], ".1f")), str(format(self.chosen_right_points[self.movingPoint[2]].y() * self.trueRightSize[1] / self.rightSize[1], ".1f"))) + ('\n' if self.movingPoint[2] != len(origData) - 1 else '')
                        open(self.endingTextCorePath, 'w').writelines(origData)
                    tempData = open(self.rightTempTextPath, 'r').readlines()
                    if tempData:
                        tempData[self.movingPoint[2]] = ('\n' if self.movingPoint[2] == 0 else '') + '{:>8}{:>8}'.format(str(format(self.chosen_right_points[self.movingPoint[2]].x(), ".1f")), str(format(self.chosen_right_points[self.movingPoint[2]].y(), ".1f"))) + ('\n' if self.movingPoint[2] != len(origData) - 1 else '')
                        open(self.rightTempTextPath, 'w').writelines(tempData)
            self.displayTriangles()

    # Very simple function for updating user preference for blending transparency in images
    # (This is disabled by default, as transparency is often unused and reduces performance.)
    def transparencyUpdate(self):
        self.notificationLine.setText(" Successfully " + ('enabled' if self.transparencyBox.isChecked() else 'disabled') + " transparency layer.")

    # Another simple function for updating user preference regarding 'full blending'
    # Full blending is defined as morphing every 0.05 alpha increment of the two images.
    # The alpha slider than becomes an interactive display, showing each blend in realtime.
    # (Naturally, this is disabled by default, as full blending takes much longer to run)
    def blendBoxUpdate(self):
        self.blendText.setEnabled(int(self.blendBox.isChecked()))
        self.notificationLine.setText(" Successfully " + ('enabled' if self.blendBox.isChecked() else 'disabled') + " full blending.")

    # Function that dynamically updates the list of triangles for the image pair provided, when manually invoked.
    # When a process wants to see triangles update properly, THIS is what needs to be called (not self.triangleUpdate).
    def displayTriangles(self):
        if self.triangleBox.isEnabled() and (self.triangleBox.isChecked() or self.triangleUpdatePref):
            if os.path.exists(self.leftTempTextPath) and os.path.exists(self.rightTempTextPath):
                self.updateTriangleWidget(1)
                leftTriList, rightTriList = loadTriangles(self.leftTempTextPath, self.rightTempTextPath)
                self.leftPolyList.clear()
                self.rightPolyList.clear()

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
            return
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
            temp = self.blendList[round(value_num / self.fullBlendValue)]
            if len(temp.shape) == 2:
                self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], QtGui.QImage.Format_Grayscale8)))
            elif temp.shape[2] == 3:
                self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], temp.shape[1] * 3, QtGui.QImage.Format_RGB888)))
            elif temp.shape[2] == 4:
                self.blendingImage.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(temp.data, temp.shape[1], temp.shape[0], QtGui.QImage.Format_RGBA8888)))
            else:
                print("Generic catching error: Something went wrong when loading the image.")

    # Function that handles movement of the quality slider
    def updateGifQuality(self):
        self.saveTab_gifQualityBox.setText(str(self.saveTab_gifQualitySlider.value()) + '%')

    # Red/Green/Blue slider functions for the triangle widget in order to select custom colors
    def updateColorSlider(self, colorSlider, colorValue):
        if self.comboBox.currentText() == 'Decimal': value = str(colorSlider.value()).zfill(3)
        elif self.comboBox.currentText() == 'Binary': value = str(bin(colorSlider.value())[2:].zfill(8))
        elif self.comboBox.currentText() == 'Hexadecimal': value = str('0x' + hex(colorSlider.value())[2:].zfill(2).upper())
        colorValue.setText(value)
        self.refreshPaint()

    # Function that handles behavior when the user wishes to blend the two calibrated images.
    # Currently designed to handle:
    #     > 8-Bit Grayscale                            (QtGui.QImage.Format_Grayscale8)
    #     > 24-Bit Color .JPG / .PNG                   (QtGui.QImage.Format_RGB888)
    #     > 24-Bit Color, 8-Bit Transparency .PNG      (QtGui.QImage.Format_RGBA8888)
    def blendImages(self):
        global grayScale, colorScaleR, colorScaleG, colorScaleB, colorScaleA, alphaValue, start_time
        self.updateMorphingWidget(False)
        triangleTuple = loadTriangles(self.startingTextCorePath, self.endingTextCorePath)
        leftImageRaw = cv2.imread(self.startingImagePath)
        rightImageRaw = cv2.imread(self.endingImagePath)
        leftImageARR = np.asarray(leftImageRaw)
        rightImageARR = np.asarray(rightImageRaw)
        self.progressBar.setValue(0)
        self.blendedImage = None
        grayScale = None
        colorScaleR = None
        colorScaleG = None
        colorScaleB = None
        colorScaleA = None
        errorFlag = False

        if self.blendBox.isChecked() and self.blendText.text() == '.':
            self.notificationLine.setText(" Failed to morph. Please disable full blending or specify a valid value (0.001 to 0.25)")
            errorFlag = True
        elif len(leftImageRaw.shape) != len(rightImageRaw.shape):
            self.notificationLine.setText(" Failed to morph due to difference in image formats. Check image file types..")
            errorFlag = True
        elif len(leftImageRaw.shape) == len(rightImageRaw.shape) < 3:  # if grayscale
            self.notificationLine.setText(" Calculating grayscale morph...")
            grayScale = Morpher(leftImageARR, triangleTuple[0], rightImageARR, triangleTuple[1])
            alphaValue = float(self.alphaValue.text())
            self.fullBlendComplete = False
            self.blendList.clear()
            start_time = time.time()
            if self.blendBox.isChecked():
                self.animateProgressBar()
                self.verifyValue("blend")
                for x in range(0, math.ceil(1 / self.fullBlendValue) + 1, 1):
                    x *= self.fullBlendValue
                    self.threadQueue.put(x)
                self.framer.start()
            else:
                self.gifText.setEnabled(0)
                self.imager.start()
                self.imager.image_complete.connect(self.imageFinished)
        elif not self.transparencyBox.isChecked() or (leftImageRaw.shape[2] == rightImageRaw.shape[2] == 3):  # if color, no alpha (.JPG)
            self.notificationLine.setText(" Calculating RGB (.jpg) morph...")
            self.fullBlendComplete = False
            self.blendList.clear()
            colorScaleB = Morpher(leftImageARR[:, :, 0], triangleTuple[0], rightImageARR[:, :, 0], triangleTuple[1])
            colorScaleG = Morpher(leftImageARR[:, :, 1], triangleTuple[0], rightImageARR[:, :, 1], triangleTuple[1])
            colorScaleR = Morpher(leftImageARR[:, :, 2], triangleTuple[0], rightImageARR[:, :, 2], triangleTuple[1])
            alphaValue = float(self.alphaValue.text())
            start_time = time.time()
            if self.blendBox.isChecked():
                self.animateProgressBar()
                for x in range(0, math.ceil(1 / self.fullBlendValue) + 1, 1):
                    x *= self.fullBlendValue
                    self.threadQueue.put(x)
                self.framer.start()
            else:
                self.gifText.setEnabled(0)
                self.imager.start()
                self.imager.image_complete.connect(self.imageFinished)
        elif self.transparencyBox.isChecked() and leftImageRaw.shape[2] == rightImageRaw.shape[2] == 4:   # if color, alpha (.PNG)
            self.notificationLine.setText(" Calculating RGBA (.png) morph...")
            QtCore.QCoreApplication.processEvents()
            colorScaleB = Morpher(leftImageARR[:, :, 0], triangleTuple[0], rightImageARR[:, :, 0], triangleTuple[1])
            colorScaleG = Morpher(leftImageARR[:, :, 1], triangleTuple[0], rightImageARR[:, :, 1], triangleTuple[1])
            colorScaleR = Morpher(leftImageARR[:, :, 2], triangleTuple[0], rightImageARR[:, :, 2], triangleTuple[1])
            colorScaleA = Morpher(leftImageARR[:, :, 3], triangleTuple[0], rightImageARR[:, :, 3], triangleTuple[1])
            alphaValue = float(self.alphaValue.text())
            self.fullBlendComplete = False
            self.blendList.clear()
            start_time = time.time()
            if self.blendBox.isChecked():
                self.animateProgressBar()
                for x in range(0, math.ceil(1 / self.fullBlendValue) + 1, 1):
                    x *= self.fullBlendValue
                    self.threadQueue.put(x)
                self.framer.start()
            else:
                self.gifText.setEnabled(0)
                self.imager.start()
                self.imager.image_complete.connect(self.imageFinished)
        else:
            errorFlag = True
        if not errorFlag:
            self.blendingImage.setScaledContents(1)
        else:
            self.updateMorphingWidget(True)

    def selectSaveFolder(self):
        filepath = QFileDialog.getExistingDirectory(self, 'Save morph to ...')

        if filepath != '':
            self.saveTab_folderDisplayText.setText(os.path.abspath(filepath))
        else:
            self.saveTab_folderDisplayText.setText(ROOT_DIR)

    # Function that handles behavior when the user wishes to save the rendered morph
    # Currently designed to handle generation of the following:
    #     Single Blend → Grayscale .jpg/.jpeg
    #     Single Blend → Color     .jpg/.jpeg/.png
    #     Full Blend → Grayscale/Color .gif (default frame time: 100 ms)
    def saveMorph(self):
        if self.blendingImage.hasScaledContents():
            # GIF
            if self.saveTab_multiRadio.isChecked() and self.saveTab_gifRadio.isChecked() and self.blendList != []:
                self.gifTextDone()
                filepath, _ = QFileDialog.getSaveFileName(self, 'Save the gif as ...', "Morph.gif", "Images (*.gif)")
                if filepath == "":
                    return

                temp = copy.deepcopy(self.blendList)
                #temp = []
                scalar = int(self.saveTab_gifQualityBox.text()[:-1]) / 100
                #for x in temp1:
                #    temp.append(cv2.resize(x, (x.width() * scalar, x.height() * scalar), interpolation=cv2.INTER_AREA))

                if self.saveTab_reverseBox.isChecked():
                    temp = list(reversed(temp))

                if self.saveTab_rewindBox.isChecked():
                    temp += list(reversed(temp))

                imageio.mimsave(filepath, temp, duration=float(self.gifValue / 1000), loop=int(not self.saveTab_loopBox.isChecked()))

                self.notificationLine.setText(" Full blend successfully saved as .gif")
                if os.path.exists(filepath):
                    self.notificationLine.setText(" Full blend successfully saved as .gif")
                else:
                    self.notificationLine.setText(" Generic Catching Error: Full blend can't be saved as .gif..")
            # Image(s)
            else:
                if self.saveTab_pngRadio.isChecked():
                    imageformat = cv2.COLOR_RGBA2BGRA
                    savePath, _ = QFileDialog.getSaveFileName(self, 'Save the image as ...', "Morph.png", "Images (*.png)")
                else:
                    imageformat = cv2.COLOR_RGB2BGR
                    savePath, _ = QFileDialog.getSaveFileName(self, 'Save the image as ...', "Morph.jpg", "Images (*.jpg)")

                if savePath == "":
                    return

                filename = os.path.basename(savePath)
                filepath = os.path.dirname(savePath)

                # Multiple Images
                if self.saveTab_multiRadio.isChecked() and self.saveTab_frameRadio.isChecked():
                    for index, x in enumerate(self.blendList, 1):
                        self.saveImage(x, filepath, filename, imageformat, index)
                # Single Image
                elif self.saveTab_singleRadio.isChecked():
                    if self.fullBlendComplete:
                        currImage = self.blendList[round(((self.alphaSlider.value() / self.alphaSlider.maximum()) / self.fullBlendValue) * self.fullBlendValue / self.fullBlendValue)]
                    else:
                        currImage = self.blendedImage
                    self.saveImage(currImage, filepath, filename, imageformat)
        else:
            self.notificationLine.setText(" Generic Catching Error: Image(s) can't be saved..")

    # Function that handles behavior for individual image output to specified path
    def saveImage(self, image, filepath, filename, imageformat, seq=0):
        if seq != 0:
            filename, filenameExtension = os.path.splitext(filename)
            filename += '_' + str(seq) + filenameExtension
        try:
            cv2.imwrite(filepath + os.path.sep + filename, cv2.cvtColor(image, imageformat))
            self.validateSave(filepath, filename, seq)
        except Exception:
            self.notificationLine.setText(" Generic Catching Error: Image(s) can't be saved..")

    # Function that returns whether morph was successfully saved on user execution
    def validateSave(self, filepath, filename, seq=0):
        if seq != 0: var = ' Frame ' + str(seq) + ' '
        else: var = ' Morph '
        if os.path.exists(filepath + os.path.sep + filename):
            self.notificationLine.setText(var + "successfully saved as image (" + filename[-4:] + ")")
        else:
            self.notificationLine.setText(" Generic Catching Error: " + var + "can't be saved as (" + filename[-4:] + ")..")

    # Function that handles behavior for loading the user's left image
    def loadDataLeft(self, fromDrag=False):
        self.triangleUpdatePref = int(self.triangleBox.isChecked())
        self.fullBlendComplete = False
        self.alphaValue.setEnabled(0)
        self.alphaSlider.setEnabled(0)
        self.autoCornerButton.setEnabled(0)
        self.resetPointsButton.setEnabled(0)
        self.resizeLeftButton.setEnabled(0)
        self.resizeRightButton.setEnabled(0)
        self.blendButton.setEnabled(0)
        self.triangleBox.setChecked(0)
        self.triangleBox.setEnabled(0)
        if fromDrag is False:
            self.startingImagePath, _ = QFileDialog.getOpenFileName(self, caption='Open Starting Image File ...', directory=os.path.join(ROOT_DIR, 'Images_Points'), filter="Images (*.png *.jpg *.jpeg)")
        if not self.startingImagePath:
            self.leftTempPath = ''
            self.leftTempTextPath = ''
            self.startingImage.setScaledContents(0)
            return

        self.notificationLine.setText(" Left image loaded.")
        self.displayTriangles()

        # Obtain file's name and extension
        self.startingImageName, self.startingImageType = os.path.splitext(os.path.basename(self.startingImagePath))  # Example: C:/Desktop/TestImage.jpg => ('TestImage', '.jpg')

        self.leftTempPath = ROOT_DIR + os.path.sep + 'PIM_Temp_Left' + self.startingImageType
        self.lastLeftSize = (self.startingImage.width(), self.startingImage.height())
        try:
            temp1 = cv2.imread(self.startingImagePath, cv2.IMREAD_UNCHANGED)
            tempLeft = cv2.resize(temp1, (self.startingImage.width(), self.startingImage.height()), interpolation=cv2.INTER_AREA)
        except:
            temp1 = cv2.imdecode(np.fromfile(self.startingImagePath, dtype=np.uint8), -1)
            tempLeft = cv2.resize(temp1, (self.startingImage.width(), self.startingImage.height()), interpolation=cv2.INTER_AREA)
        cv2.imwrite(self.leftTempPath, tempLeft)
        self.startingImage.setPixmap(QtGui.QPixmap(self.leftTempPath))
        self.startingImage.setScaledContents(1)
        self.trueLeftSize = (cv2.imread(self.startingImagePath).shape[1], cv2.imread(self.startingImagePath).shape[0])
        self.leftSize = (cv2.imread(self.leftTempPath).shape[1], cv2.imread(self.leftTempPath).shape[0])
        self.imageScalar = (self.leftSize[0] / (self.startingImage.geometry().topRight().x() - self.startingImage.geometry().topLeft().x()), self.leftSize[1] / (self.startingImage.geometry().bottomRight().y() - self.startingImage.geometry().topLeft().y()))

        # Create local path to check for the image's text file
        # Example: C:/Desktop/TestImage.jpg => C:/Desktop/TestImage-jpg.txt
        self.startingTextPath = self.startingImagePath[:-(len(self.startingImageName + self.startingImageType))] + self.startingImageName + '-' + self.startingImageType[1:] + '.txt'

        # Now assign file's name to desired path for information storage (appending .txt at the end)
        # self.startingTextCorePath = 'C:/Users/USER/PycharmProjects/Personal/Morphing/Images_Points/' + 'TestImage' + '-' + 'jpg' + '.txt'
        self.startingTextCorePath = os.path.join(ROOT_DIR, 'Images_Points' + os.path.sep + self.startingImageName + '-' + self.startingImageType[1:] + '.txt')
        self.leftTempTextPath = os.path.join(ROOT_DIR, 'PIM_Temp_Left-' + self.startingImageType[1:] + '.txt')

        self.checkFiles('loadDataLeft', self.startingTextPath, self.startingTextCorePath, self.leftTempTextPath)

    # Function that handles behavior for loading the user's right image
    def loadDataRight(self, fromDrag=False):
        self.triangleUpdatePref = int(self.triangleBox.isChecked())
        self.fullBlendComplete = False
        self.alphaValue.setEnabled(0)
        self.alphaSlider.setEnabled(0)
        self.autoCornerButton.setEnabled(0)
        self.resetPointsButton.setEnabled(0)
        self.resizeLeftButton.setEnabled(0)
        self.resizeRightButton.setEnabled(0)
        self.blendButton.setEnabled(0)
        self.triangleBox.setChecked(0)
        self.triangleBox.setEnabled(0)
        if fromDrag is False:
            self.endingImagePath, _ = QFileDialog.getOpenFileName(self, caption='Open Ending Image File ...', directory=os.path.join(ROOT_DIR, 'Images_Points'), filter="Images (*.png *.jpg *.jpeg)")
        if not self.endingImagePath:
            self.rightTempPath = ''
            self.rightTempTextPath = ''
            self.endingImage.setScaledContents(0)
            return

        self.notificationLine.setText(" Right image loaded.")
        self.displayTriangles()

        # Obtain file's name and extension
        self.endingImageName, self.endingImageType = os.path.splitext(os.path.basename(self.endingImagePath))  # Example: C:/Desktop/TestImage.jpg => ('TestImage', '.jpg')

        self.rightTempPath = ROOT_DIR + os.path.sep + 'PIM_Temp_Right' + self.endingImageType
        self.lastRightSize = (self.endingImage.width(), self.endingImage.height())
        try:
            temp2 = cv2.imread(self.endingImagePath, cv2.IMREAD_UNCHANGED)
            tempRight = cv2.resize(temp2, (self.endingImage.width(), self.endingImage.height()), interpolation=cv2.INTER_AREA)
        except:
            temp2 = cv2.imdecode(np.fromfile(self.endingImagePath, dtype=np.uint8), -1)
            tempRight = cv2.resize(temp2, (self.endingImage.width(), self.endingImage.height()), interpolation=cv2.INTER_AREA)
        cv2.imwrite(self.rightTempPath, tempRight)
        self.endingImage.setPixmap(QtGui.QPixmap(self.rightTempPath))
        self.endingImage.setScaledContents(1)
        self.trueRightSize = (cv2.imread(self.endingImagePath).shape[1], cv2.imread(self.endingImagePath).shape[0])
        self.rightSize = (cv2.imread(self.rightTempPath).shape[1], cv2.imread(self.rightTempPath).shape[0])
        self.imageScalar = (self.rightSize[0] / (self.endingImage.geometry().topRight().x() - self.endingImage.geometry().topLeft().x()), self.rightSize[1] / (self.endingImage.geometry().bottomRight().y() - self.endingImage.geometry().topLeft().y()))

        # Create local path to check for the image's text file
        # Example: C:/Desktop/TestImage.jpg => C:/Desktop/TestImage-jpg.txt
        self.endingTextPath = self.endingImagePath[:-(len(self.endingImageName + self.endingImageType))] + self.endingImageName + '-' + self.endingImageType[1:] + '.txt'

        # Now assign file's name to desired path for information storage (appending .txt at the end)
        # self.endingTextCorePath = 'C:/Users/USER/PycharmProjects/Personal/Morphing/Images_Points/' + 'TestImage' + '-' + 'jpg' + '.txt'
        self.endingTextCorePath = os.path.join(ROOT_DIR, 'Images_Points' + os.path.sep + self.endingImageName + '-' + self.endingImageType[1:] + '.txt')
        self.rightTempTextPath = os.path.join(ROOT_DIR, 'PIM_Temp_Right-' + self.endingImageType[1:] + '.txt')

        self.checkFiles('loadDataRight', self.endingTextPath, self.endingTextCorePath, self.rightTempTextPath)

    # Helper function for loadDataLeft and loadDataRight to reduce duplication of code
    # Handles text file generation, loads data, and sets flags where appropriate
    def checkFiles(self, sourceFunc, basePath, rootPath, tempPath):
        # If there is already a text file at the location of the selected image, the program assumes that it is what
        # the user intends to start with and moves it to the root path for future manipulation.
        # Otherwise, the program creates an empty file at the root path instead.
        if os.path.isfile(basePath):
            try:
                shutil.copy(basePath, rootPath)
                os.remove(basePath)
            except shutil.SameFileError:
                pass
        else:
            if not os.path.exists(os.path.dirname(rootPath)):  # if Images_Points doesn't exist, create it
                os.makedirs(os.path.dirname(rootPath))
            open(rootPath, 'a').close()

        # Copy source data to scaled temp file
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tempData = np.loadtxt(rootPath)
            with open(tempPath, 'w') as file:
                if sourceFunc == 'loadDataLeft':
                    if len(tempData.shape) == 1 and len(tempData) > 0:  # only one point pair in files (this requires different loading syntax...)
                        if not os.stat(tempPath).st_size:  # left file is empty
                            file.write('{:>8}{:>8}'.format(str(format(tempData[0] * (self.leftSize[0] / self.trueLeftSize[0]), ".1f")), str(format(tempData[1] * (self.leftSize[1] / self.trueLeftSize[1]), ".1f"))))
                        else:
                            file.write('\n{:>8}{:>8}'.format(str(format(tempData[0] * (self.leftSize[0] / self.trueLeftSize[0]), ".1f")), str(format(tempData[1] * (self.leftSize[1] / self.trueLeftSize[1]), ".1f"))))
                    else:
                        for index, x in enumerate(tempData):
                            if not index and not os.stat(tempPath).st_size:  # left file is empty
                                file.write('{:>8}{:>8}'.format(str(format(x[0] * (self.leftSize[0] / self.trueLeftSize[0]), ".1f")), str(format(x[1] * (self.leftSize[1] / self.trueLeftSize[1]), ".1f"))))
                            else:
                                file.write('\n{:>8}{:>8}'.format(str(format(x[0] * (self.leftSize[0] / self.trueLeftSize[0]), ".1f")), str(format(x[1] * (self.leftSize[1] / self.trueLeftSize[1]), ".1f"))))
                elif sourceFunc == 'loadDataRight':
                    if len(tempData.shape) == 1 and len(tempData) > 0:  # only one point pair in files (this requires different loading syntax...)
                        if not os.stat(tempPath).st_size:  # left file is empty
                            file.write('{:>8}{:>8}'.format(str(format(tempData[0] * (self.rightSize[0] / self.trueRightSize[0]), ".1f")), str(format(tempData[1] * (self.rightSize[1] / self.trueRightSize[1]), ".1f"))))
                        else:
                            file.write('\n{:>8}{:>8}'.format(str(format(tempData[0] * (self.rightSize[0] / self.trueRightSize[0]), ".1f")), str(format(tempData[1] * (self.rightSize[1] / self.trueRightSize[1]), ".1f"))))
                    else:
                        for index, y in enumerate(tempData):
                            if not index and not os.stat(tempPath).st_size:  # left file is empty
                                file.write('{:>8}{:>8}'.format(str(format(y[0] * (self.rightSize[0] / self.trueRightSize[0]), ".1f")), str(format(y[1] * (self.rightSize[1] / self.trueRightSize[1]), ".1f"))))
                            else:
                                file.write('\n{:>8}{:>8}'.format(str(format(y[0] * (self.rightSize[0] / self.trueRightSize[0]), ".1f")), str(format(y[1] * (self.rightSize[1] / self.trueRightSize[1]), ".1f"))))

        # if sourceFunc == 'loadDataLeft':
        #     for x in tempData:
        #         x *= (self.leftSize[0] / self.trueLeftSize[0], self.leftSize[1] / self.trueLeftSize[1])
        # elif sourceFunc == 'loadDataRight':
        #     for y in tempData:
        #         y *= (self.rightSize[0] / self.trueRightSize[0], self.rightSize[1] / self.trueRightSize[1])
        # np.savetxt(tempPath, tempData, fmt='%.1f')

        self.added_left_points.clear()
        self.added_right_points.clear()
        self.confirmed_left_points.clear()
        self.confirmed_right_points.clear()

        # TODO: Do the same thing here with tempPath & self.tempChosen_left_points or some variable like that.
        with open(tempPath, "r") as textFile:
            if sourceFunc == 'loadDataLeft':
                self.chosen_left_points.clear()
                for x in textFile:
                    self.chosen_left_points.append(QtCore.QPoint(int(float(x.split()[0])), int(float(x.split()[1]))))
            elif sourceFunc == 'loadDataRight':
                self.chosen_right_points.clear()
                for x in textFile:
                    self.chosen_right_points.append(QtCore.QPoint(int(float(x.split()[0])), int(float(x.split()[1]))))

        if self.startingImage.hasScaledContents() and self.endingImage.hasScaledContents():
            self.resizeLeftButton.setEnabled(1)
            self.resizeRightButton.setEnabled(1)
            if self.chosen_left_points != [] and self.chosen_right_points != []:
                self.resetPointsButton.setEnabled(1)

            # Check that the two images are the same size - if they aren't, the user should be notified that this won't work
            if self.trueLeftSize == self.trueRightSize:
                self.resizeLeftButton.setStyleSheet("")
                self.resizeRightButton.setStyleSheet("")
                self.alphaValue.setEnabled(1)
                self.alphaSlider.setEnabled(1)
                self.autoCornerButton.setEnabled(1)
                # Check if 3 or more points exist for two corresponding images so that triangles may be displayed
                if (len(self.chosen_left_points) + len(self.confirmed_left_points)) == (len(self.chosen_right_points) + len(self.confirmed_right_points)) >= 3:
                    self.blendButton.setEnabled(1)
                    self.triangleBox.setEnabled(1)
                    self.triangleBox.setChecked(self.triangleUpdatePref)

            else:
                self.resizeLeftButton.setStyleSheet("font: bold;")
                self.resizeRightButton.setStyleSheet("font: bold;")
                if sourceFunc == 'loadDataLeft':
                    self.notificationLine.setText(" Left image loaded - WARNING: Input images must be the same size!")
                elif sourceFunc == 'loadDataRight':
                    self.notificationLine.setText(" Right image loaded - WARNING: Input images must be the same size!")
        self.displayTriangles()


if __name__ == "__main__":
    currentApp = QApplication(sys.argv)
    currentForm = MorphingApp()

    currentForm.show()
    currentApp.exec_()
