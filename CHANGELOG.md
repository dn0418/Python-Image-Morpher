# Version 2.0.2 - (2021-12-29)
### This update includes dependency changes - Please run the command "pip install -r requirements.txt" or equivalent after downloading.

## Added
- <b>Configuration Tab (Work in Progress)</b>
  - Initial GUI implementation for saving, loading, and handling default parameters requested by the user, such as default image search path
  - All widgets are currently disabled and will be enabled in a future update when ready
    - Comment: <i>Releasing the current implementation for this tab as-is in hopes of receiving feedback on the interface before full release.</i>
## Changes
- Image loading methods <b>loadDataLeft()</b> and <b>loadDataRight()</b> now default to the Images_Points folder when the user is prompted to select an image
  - This will be configurable when the Configuration tab is fully implemented and released
- Code cleanup: Merged and removed duplicate methods for various GUI tasks to reduce unnecessary bloat - more planned in the future
  - <b>updateRed()</b> / <b>updateGreen()</b> / <b>updateBlue()</b> → <b>updateColorSlider</b>
  - <b>triangleRedValueDone()</b> / <b>triangleGreenValueDone()</b> / <b>triangleBlueValueDone()</b> → Removed in favor of directly calling <b>verifyValue</b>
- Rewrote <b>checkUpdate()</b> to instead parse api.github.com as well as silently terminate on exception or failure
- Modified requirements.txt: 
  - Added Requests - missing from 2.0 release, required for <b>checkUpdate()</b>
  - Removed BeautifulSoup - no longer needed due to <b>checkUpdate()</b> changes
- Miscellaneous: Updated comments for initialized GUI variables and signal connections

# Version 2.0.1 - (2021-08-15)
## Fixes
- Resolved crash when the total point pair count was brought below three through Delete Mode
- Corrected issue with Delete Mode that caused points to be improperly deleted (eventually cascaded into crashes)
- Fixed bug with image loading that caused PIM to crash when only one point pair was previously saved
- Removed unnecessary print statement on startup

# Version 2.0.0 - (2021-07-28)
<i>As no issues have been reported with 2.0.0 Beta, it is now being released as Stable with a couple additions.</i>
# This update includes new dependencies - Please run the command "pip install -r requirements.txt" or equivalent after downloading.

## Added
- <b>New Mouse Modes</b>
  - In addition to point placement, the user can now switch between two other modes when clicking on input images: <b>Move Mode</b> and <b>Delete Mode</b>
    - (E) - Move Mode allows the user to drag any previously confirmed point to a new location
    - (Q) - Delete Mode allows the user to delete any previously confirmed point
    - Special thanks to GitHub user <b>jankaWIS</b> for [creating this feature request](https://github.com/ddowd97/Python-Image-Morpher/issues/6), which got me to finally add these functionalities to PIM's GUI 
- <b>Dynamic Image Loading</b>
  - The user can now load images into the GUI from their OS by dragging and dropping them into the desired window
  - Input images are now dynamically resized to match the size of their windows in the GUI, <b>greatly</b> improving GUI responsiveness
    - Larger images (e.g. 1080p, 4K, etc.) are downscaled, smaller images are upscaled
    - The user's files themselves are unchanged - PIM instead manipulates copies that get cleaned up during termination
    - Comment: <i> Implementing this was - by far - the most painful thing I have experienced with software development as this ended up impacting pretty much
      every single part of PIM and it's code... which is also why this release was delayed for so long. I expect that any hotfixes needed for this update will arise
      from this unexpectedly complicated change, but I will be more than happy if that  isn't the case (please work for others besides me...).</i>
- <b>Zoom Panning</b>
  - The user can now pan images while zoomed in by clicking and dragging with the middle-mouse button
- <b>Zoom Slider</b>
  - QoL: The user can now manually set the strength of the zoom applied to GUI images (in realtime) for ease of use
    - Zoom strength is defaulted to 2x during initialization but can now range from 2x to 10x!
- <b>Automatic Versioning Checker</b>
  - On startup, PIM now checks your currently installed version against the latest stable release hosted on GitHub
  - A prompt is provided to automatically navigate the user to the latest release, if not up to date
      - PIM does not support automatic update installation at this time
- <b>Triangle Widget Enhancements</b>
  - In addition to the sliders, the user can now manually enter RGB values for the displayed triangles
    -  The user can now choose between binary, decimal, or hexadecimal format when setting RGB values
- <b>More Macros</b>
  - The following key combinations have been added to support the user's interactions with the GUI:
    - D = Toggle Display of Delaunay Triangles
    - E = Toggle Move Mode (for moving individual points)
    - Q = Toggle Delete Mode (for deleting individual points)
    - Ctrl + Mouse Wheel =  Adjust Zoom Slider
        - Comment: <i>Yes, this can be used with zoom panning simultaneously, so go nuts ;)</i>
    - Shift + Mouse Wheel = Adjust Point Slider
    - Alt + Mouse Wheel = Adjust Alpha Slider
## Changes
- PIM's GUI has received many needed internal changes. The following elements have been changed:
  - <b>Redesign:</b>
    - The GUI has been restructured from scratch to containerize separate blocks
      - As this allows for far more refined control over resizing behavior - which has historically been a very problematic piece of development for this project - <b>EVERY</b> documented resizing bug has been fixed with this change (more details in <b>Fixes</b>)
  - <b>Miscellaneous:</b>
    - Minimum size of the main window has changed from <b>(788 x 690)</b> to <b>(844 x 763)</b>
      - Comment: <i>Still trying to find that sweet spot for the GUI as it is refined and enhanced over time.</i>
- Optimization: <b>MorphingApp.py</b> no longer conditionally sets minimum/maximum/fixed size rules for the image windows (as Qt handles resizing correctly now)
- Complete rewrite of <b>blendImages()</b> to support proper QThreading during morphing, preventing GUI lockup
  - To accompany this change, all functions related to morphing are disabled during the process to prevent exploits
  - Comment: <i>Trading some performance for stability here since GUI threading during long calculations is good practice anyways. This opened the door to a proper progress bar as well, since that signal can now be emitted.</i>
- Implemented a proper progress bar for full blending - the notification bar is no longer used for this
- Full blending now displays frames as they are rendered
  - PIM will still display the user's specified frame when finished morphing
- Alpha is now assigned 50% instead of 0% when reset
- PIM now prompts for confirmation when the Reset Points button is pressed
- Added queue & warnings to <b>MorphingApp.py</b>'s imports
- Removed Matplotlib and itertools from <b>Morphing.py</b>'s imports
  - As it was a dependency that is no longer in use, removed Matplotlib from requirements.txt as well
  - Comment: <i>This additionally translates to a small performance improvement during Morphing.</i>
- Added pynput, beautifulsoup, & opencv-python to requirements.txt
  - Comment: <i>The addition of pynput is to accommodate changes to resizing with this update due to Qt being unable to detect kernel level 
    interrupts from mouse events in the running OS. This change shouldn't introduce any OS incompatibilities, but please create
    an issue if resizing the GUI leads to any unexpected issues or crashes. BeautifulSoup allows PIM to check for updates online.
    Opencv-python has finally been included for it's superior image reading/saving compared to Pillow & Imageio (both of which
    are planned to be phased out in a future update).</i>
- Added version.txt to facilitate automatic versioning checks.
  - Comment: <i>Modifying, deleting, or moving this file will confuse PIM and ruin its day, but should not cause issues for you.</i>
- Removed NumPy's version restriction in requirements.txt (as the [fmod() issue](https://developercommunity.visualstudio.com/content/problem/1207405/fmod-after-an-update-to-windows-2004-is-causing-a.html) in v1.19.4 has been resolved)
- Simplified all remaining instances of legacy code where the last index of a list was being accessed
  - x[len(x)-1] → x[-1]
- Removed an instance of self.repaint() inside <b>MorphingApp.py</b>'s checkResize()
- Removed multiple instances of self.refreshPaint() inside <b>MorphingApp.py</b>'s keyPressEvent()
- Updated README.md
- And much, much more

## Fixes
- Every single documented resizing bug has been hit with this update's GUI changes, including but not limited to:
  - <b>Fixed</b>: Input images would expand (or rarely shrink) by 2 pixels when loaded or each time the GUI was resized (very common)
  - <b>Fixed</b>: The bottom half of the GUI would often vertically expand/collapse before the top half (very common)
  - <b>Fixed</b>: The left half of the GUI would often horizontally expand/collapse before the right half (uncommon)
  - <b>Fixed</b>: Zooming into input images would cause random, incorrect resizing behavior (common)
  - <b>Fixed</b>: When maximized, the GUI would resize incorrectly with conditionally varying severity (very common)
  - <b>Fixed</b>: Inconsistent resizing behavior before and after a morph had been executed (very common)
- Fixed a <b>long</b>-standing bug where the GUI could temporarily become unresponsive while morphing
  - Additionally, fixed a bug where inputs to the GUI would be propagated during morphing
    - Example: This could lead to chain-morphing if the blend button was clicked more than once
- Fixed a bug where PIM could treat certain incompatible images as standard .jpg, causing a crash during morphing
- Fixed a bug where zooming in on the lower third of either input image would be visibly distorted 
- Prioritized GUI parameter assignment to come first in the loadImage functions - thereby resolving several bugs & crashes
- Fixed an amusing bug where the Help tab could be edited by the user
- Fixed a crash that could occur upon resetting the alpha slider after executing a full blend
- Resolved a minor GUI issue where, when enabled, Green/Blue triangle color value text would remain grey until updated
- Fixed a bug where the <b>Add Corners</b> button would sometimes not enable after clicking <b>Resize Left Image</b> or <b>Resize Right Image</b>
- Corrected a notification bar bug when one image has been loaded and user tries to add point
- Other general code cleanup

## Known Bugs
- While zoomed in, issue with highlighting points to be manually moved or deleted
- After clicking Resize Left/Right, points on the GUI do not visibly scale correctly
  - Comment: <i>This is a purely visual bug. For now, this issue can be circumvented by just reloading the affected image. </i>
  
## Unreleased
- Key Macro: Tab / Shift + Tab = Switch Morphing Tab
- Configuration Tab
  - Comment: <i>In the future, this tab will be used to set/reload default parameters for PIM to use on initialization. Still planning out what I do 
    and don't want to be included in this tab though, so it has been excluded from this release.</i>

# Version 1.1.2 - (2021-05-02)
# Hotfix:
- Fixed a bug where the absolute path to Images_Points was incorrectly assigned for non-Windows machines
  - '\\\\' → os.path.sep
  
# Version 1.1.1 - (2021-04-29)
# Hotfix:
- Fixed a bug where starting/ending image names could be incorrectly assigned when certain OS conditions were met
  - re.search('(?<=[/])[^/]+(?=[.])', x).group() → os.path.splitext(os.path.basename(x))


# Version 1.1.0 - (2021-01-16)
## Known Bugs
- The GUI can sometimes become unresponsive during morphing calculations (but eventually returns to normal)
    - QtCore.QCoreApplication.processEvents() is a potential workaround but currently produces buggy results
    
## Added
- <b>Point Size Slider</b>
    - QoL: The user can now manually change the size of points rendered onto the GUI (in realtime) for ease of use
    - Point width values still default to 4 during initialization but can now range from 1 to 10
## Changes
- PIM's GUI has received another facelift with this update! The following elements have been changed:
  - <b>Redesign:</b>
    - Along with a streamlined layout, buttons & settings have been moved to categorized tabs
  - <b>Accessibility:</b> 
    - PIM now includes a Help manual for new users! Check the Help tab in the GUI for more.
    - Minimum size of the main window has changed from <b>(878 x 809)</b> to <b>(788 x 690)</b>
      - Comment: <i>I realize that there are still people in the world using 720p monitors.. this one's for you.</i>
  - <b>Miscellaneous:</b>
    - Added dedicated value boxes for each of the triangle color sliders
      - Changes in value will no longer be announced in the notification bar
    - Alpha is now initialized at 50% instead of 0%
      - Comment: <i>Honestly, not really sure why this wasn't always the case.</i>
- Updated README.md

## Fixes
- Fixed an ugly bug where zooming in to only one image could reshape the GUI
- Fixed a notification bar bug regarding mouse clicks when only one image was loaded

# Version 1.0.0 - <i> Finally! </i> - (2020-12-13)
## Known Bugs
- The GUI can sometimes become unresponsive during morphing calculations (but eventually returns to normal)
    - QtCore.QCoreApplication.processEvents() is a potential workaround but currently produces buggy results
    
## Added
- <b>Image Zoom</b> - Because sometimes, it's hard to get that one point just right.
  - The user can now right-click on either [or both] of the input images to toggle zoom for more accurate point placement
    - Comment: <i>Sheesh, this was difficult to implement correctly with Qt. Currently this feature is using a default (and moderate) 
      zoom strength of 2x, but this may be subject to change in the future - might use 2.5x or 3x if it seems that 2x isn't cutting it.</i>

## Removed
- As of v0.3.0.1's hot pixel fix, PIM's image smoothing feature is deprecated and will now be removed
    - Removed Morphing.py's <b>smoothBlend()</b> method as well as the "smoothMode" parameter in <b>getImageAtAlpha()</b>
    - Removed Morphing.py's sub-module import for SciPy's <i>median_filter</i>
    - Removed all code related to smoothing in MorphingApp.py (a reduction of 77 SLOC)
    - Removed <b>self.smoothingBox</b> from MorphingGUI.ui and MorphingGUI.py
        - Comment: <i>It's likely that this checkbox will be replaced with an automatic correspondence button at some point.</i>

## Changes
- Improved morphing performance (a huge <b>90%</b> speedup) by modifying Morphing.py's implementation of <b>getPoints()</b> as well as tweaking <b>interpolatePoints()</b> to utilize RectBivariateSpline's .ev() method instead of manually interpolating the image data
  - <b>Huge thanks to GitHub user [zhifeichen097](https://github.com/zhifeichen097) for his source code which can be found [here](https://github.com/zhifeichen097/Image-Morphing) - excellent work!</b>
- Optimized the conditional logic found in MorphingApp.py's <b>displayTriangles()</b>
- Optimized point assignment in Morphing.py's <b>loadTriangles()</b> by utilizing np.loadtxt()
- Optimized conditional logic and list pop statements in MorphingApp.py's <b>keyPressEvent()</b>
- Changed the loop in MorphingApp.py's <b>autoCorner()</b> to be less C-like and more Pythonic
  - "i = 0; while i < 4: ... i++" → "for leftPoint, rightPoint in zip(tempLeft, tempRight): ..."
- Moved <b>autoCorner()</b>'s invocation of <b>refreshPaint()</b> out of it's loop (i.e. the GUI is now updated once instead of up to four times)
- Changed the notification message displayed when <b>autoCorner()</b> adds one point pair
- Removed a conditional in MorphingApp.py's <b>resizeLeft()</b> and <b>resizeRight()</b> that was unnecessarily reassigning their image type variable
- Converted the syntax of all instances where lists were being reset in MorphingApp.py
  - "self.blendList = []" → "self.blendList.clear()"
- Updated a couple source code comments that became deprecated due to recent updates (oops)

## Fixes
- Resolved an oversight where .jpeg images couldn't be loaded into the program
  - Comment: <i>To clarify, while it can probably accept other types, PIM is specifically written to work with .jpg, .jpeg, and .png images.</i>
- Corrected unintended behavior in <b>mousePressEvent()</b> where points could also be drawn with the middle and right mouse buttons

# Version 0.3.0.1 - (2020-12-01)
## Fixes
- Fixed a long-standing bug where hot pixels frequently appeared in blended images [[before](https://i.imgur.com/W8RniY5.jpg) and [after](https://i.imgur.com/B5dLjRn.jpg)]
    - Comment: <i>While researching 2D interpolation methods in Python for what feels like the hundredth time (and still concluding that
    RectBivariateSpline is apparently the best method I can use), I noticed the optional 'kx' and 'ky' parameters that this method supports.
    Naturally, the [documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.RectBivariateSpline.html) on them
    isn't very helpful (and honestly, I'm too lazy to put my computer engineering hat back on to understand what [Wikipedia](https://en.wikipedia.org/wiki/Spline_(mathematics))
    makes of them), but it does mention that the default value for each parameter is 3 degrees.. which got me thinking that a change here could lead
    to a potential performance improvement for PIM! In an unexpected turn of events, from what I can tell, setting 'kx' and 'ky' to 1 completely removes ALL 
    hot/dead pixels that were appearing during interpolation. As a bonus, it also gives a 1-2% performance improvement based on surface level analysis.. win-win.</i>

# Version 0.3.0.0 - (2020-11-21)
## Known Bugs
- The GUI can sometimes become unresponsive during morphing calculations (but eventually returns to normal)
    - QtCore.QCoreApplication.processEvents() is a potential workaround but currently produces buggy results

## Unreleased
- <b>Image Zoom</b>
    - The user may right click on an image to zoom in and out of it to place more accurate points
    - Comment: <i>Currently, image zoom functionality has been (somewhat) implemented but point placement will require additional changes.</i>
    
## Added
- <b>Freestyle Point Placement</b> - Gone are the days when point pairs had to begin with the left image!
    - QoL: The user can now place point pairs on the images in whatever order they wish
    - Keyboard/mouse input logic has been rewritten to maintain previous behavior with Undo, Delete, OUT, etc.
- <b>Redo (CTRL+Y) Functionality</b> 
    - The user may now redo any point placement that was previously undone or deleted
        - Points are recovered in the order they were undone or deleted
        - The cache is cleared whenever a new point is placed by the user
        
## Changes
- Added logging that was previously missing from MorphingApp.py's Undo logic
- Polished the string comparator found in MorphingApp.py's <b>gifTextDone()</b>
- Optimized out ~34 SLOC from the Undo logic found in MorphingApp.py's <b>keyPressEvent()</b>
- Optimized out ~25 SLOC from MorphingApp.py's <b>displayTriangles()</b> where Morphing.py's <b>loadTriangles()</b> should have been used
- Triangle display behavior during MorphingApp.py's <b>mousePressEvent()</b> has been further consolidated and streamlined
- To accommodate this update, all instances of <b>self.currentWindow</b> have been removed
    - Since much of <b>mousePressEvent()</b> and <b>keyPressEvent()</b> depended on this variable, these methods have been changed accordingly
    - Comment: <i>The 'current window' variable was unintuitive legacy code written to get a working prototype out and, therefore, has not been very maintainable.
    This update replaces it with a much more useful <b>self.clicked_window_history</b>, it's spiritual successor!</i>
- All instances of <b>self.persistFlag</b> have been removed
    - Comment: <i>More unintuitive legacy code. Since this variable is no longer used - and to improve maintainability - it is being removed.</i>
- All instances of <b>self.confirmed_left_points_history</b> and <b>self.confirmed_right_points_history</b> have been removed
    - Comment: <i>These were placeholders for prototyping redo functionality a while back - this is now handled by <b>self.placed_points_history</b>.</i>

## Fixes
- Fixed a bug where the alpha slider and auto-corner button were not enabling when new images were loaded
    - Comment: <i>Just an oversight that spawned from the changes to the image loading methods in v0.2.9.0</i>

# Version 0.2.9.0 - (2020-09-05)
#### Note: Since I am taking up a software developer role next week, releases are going to slow down for the foreseeable future.
## Known Bugs
- The GUI can sometimes become unresponsive during morphing calculations (but eventually returns to normal)
    - QtCore.QCoreApplication.processEvents() is a potential workaround but currently produces buggy results
    
## Added
- <b>Source Image Resizing</b>
    - Since PIM requires the user's images to be the same size, it can now create and hotswap resized copies of the left/right images at the click of a button
    - For simplicity, one button resizes the left image to the right image's dimensions and the other button does the opposite
        - Both images must be loaded to enable this functionality
        - Additionally scales any added/confirmed/chosen points to the new image dimensions
        - Buttons will be set to <b>bold</b> whenever the user's images aren't the same size
    - Resized image files are stored under: <b>ROOT_DIR/Images_Points/filename-[width]x[height].filetype</b>
    - Resized text files are stored under: <b>ROOT_DIR/Images_Points/filename-[width]x[height]-filetype.txt</b>
        
## Changes
- The program now locks out usage of point placement as well as the <b>Add Corners</b> button when the user's images aren't the same size
    - Comment: <i> This is to really drive the point home: fix one of your images or you'll just be wasting your time!</i>
- Moderate rewrite of <b>loadDataLeft()</b> and <b>loadDataRight()</b>
    - New helper function: <b>checkFiles(sourceFunc, basePath, rootPath)</b>
    - Text files are now stored under: <b>ROOT_DIR/Images_Points/filename-filetype.txt</b>
    - Comment: <i> While polishing these, I found that due to how the functions were written, it was possible for the program to 
    generate text files with varying naming schemes.. some ended with 'filename.txt', others ended with 'filename.FILETYPE.txt'.
    This has been streamlined into a more readable 'filename-filetype.txt' - images that share a name but differ in type should
    play more nicely with this change.</i>

# Version 0.2.8.2 - (2020-08-26)
## Changes
- Support for morphing two images of different sizes, while initially left up in the air as a potential feature, is no longer being considered
    - Consequently, the variables <b>self.leftScalar</b> and <b>self.rightScalar</b> have been converted to <b>self.imageScalar</b>
        - Since only one scalar is calculated now, <b>resizeEvent()</b> has received a performance boost as a result
    - The program will now warn the user (via the notification bar) when they load two images of different sizes
        - Comment: <i> I'm considering adding two buttons to the GUI that resize the left image to the right image and vice versa.</i>
- Memory Optimization: Removed <b>all</b> instances of the variables used to:
    - Flag when the GUI was being resized: <b>self.resizeFlag</b>
    - Flag when left/right images were loaded: <b>self.leftOn</b>, <b>self.rightOn</b>
    - Flag whether left/right images were PNGs: <b>self.leftPNG</b>, <b>self.rightPNG</b>, <b>leftTypeRegex</b>, <b>rightTypeRegex</b>
    - Flag whether the smoothing box was checked: <b>self.smoothBoxSetting</b>
    - Flag whether the transparency box was checked: <b>self.transparencySetting</b>
    - Flag whether the full blend box was checked: <b>self.blendBoxSetting</b>
    - Flag whether the user has performed a morph in the current session: <b>self.blendExecuted</b>
    - Store triangle color slider values: <b>self.redVal</b>, <b>self.blueVal</b>, <b>self.greenVal</b>
    - Store an ADDITIONAL COPY (!!!) of each image's chosen points: <b>self.startingText</b>, <b>self.endingText</b>
        - Comment: <i> This was legacy code, for sure, but it took me a bit to even understand that these LISTS (not boolean flags.. lists!) 
        existed purely to indicate whether each input image's text file was empty or not. The memory cost for implementing that check this way was 
        laughable, so the program now uses "if not os.stat(filename).st_size:" instead. Much better!</i>
- Variables declared during <b>MorphingApp.py</b>'s initialization have been re-arranged by type (for source code clarity)
    - Additionally, detailed comments have now been given to all variables (and Qt signals) found under initialization (for source code clarity)

## Fixes
- Fixed a long-standing bug where .jpg blends could sometimes appear in the GUI to be wildly distorted and - occasionally - grayscale
    - Comment: <i> When saved, these images were perfectly fine.. the problem was coming from a Qt pixmap conversion error.
    A BPL (bytes per line) parameter has been added to .jpg QImage construction syntax to resolve the issue.</i>
- <b>autoCorner()</b> now checks that <i>neither</i> image contains each corner point before adding it
    - Comment: <i> Originally, the function was only checking that the left image didn't have each particular corner point; in retrospect, 
    this could potentially cause problems if the right image DID have that corner point (as this would then lead to duplication for the right image).</i>
- Removed a conflicting legacy initialization of self.leftSize and self.rightSize in <b>MorphingApp.py</b>
    
# Version 0.2.8.1 - (2020-08-25)
## Fixes
- Hotfixed a bug where <b>verifyValue()</b> for the frame time textbox was accepting 0 as a valid number

# Version 0.2.8.0 - (2020-08-24)
## Known Bugs
- The GUI can sometimes become unresponsive during morphing calculations
    - QtCore.QCoreApplication.processEvents() is a potential workaround but currently produces buggy results
    
## Added
- <b>Morphed Image Saving</b>
    - Normal blends can now be saved as their respective image types; full blends can now be saved as dynamic GIFs
        - Generated GIFs are subject to the user's preference for the amount of time (default: 100 ms) given to each frame
        
## Changes
- To accommodate this update, the following elements in MorphingGUI.ui and MorphingGUI.py have been changed:
    - Added a "Save Image(s)" button alongside a smaller frame time textbox
        - A fairly air-tight Qt mask is used to restrict letter and symbol input - format is "[0-9][0-9][0-9] ms"
        - The program handles other invalid inputs (000, no input)
    - Minimum size of the main window has changed from <b>(878 x 797)</b> to <b>(878 x 850)</b>
- To accommodate this update, MorphingApp.py's <b>verifyBlendValue()</b> has been changed to <b>verifyValue(str)</b>
    - This new function is now used for checking both full blend and gif values

# Version 0.2.7.0 - (2020-08-22)
## Known Bugs
- The GUI can sometimes become unresponsive during morphing calculations
    - QtCore.QCoreApplication.processEvents() is a potential workaround but currently produces buggy results

## Added
- <b>Morphed Image Smoothing</b>
    - A toggleable median filter is now applied to every blend and full blend
        - This filter attempts to remove hot pixels in morphed images by utilizing neighboring pixel values instead
        - Very little to no impact on program performance

Comment: <i> Since this isn't always necessary (and very slightly degrades image quality), it is disabled by default.</i>

## Changes
- The GUI now displays the current image frame being generated when full blending is enabled
- Morphing.py's <b>getPoints()</b> no longer calculates the minimum X and Y values for creating a sub-mask - this is now
handled during initialization of Triangle objects to save computation time during blending
- Removed two more sub-module imports (Qt's <i>QGraphicsScene</i> & <i>QGraphicsView</i>) that were no longer in use
- Optimized out a line in MorphingApp.py's <b>updateAlpha()</b> and <b>blendImages()</b>
    - Comment: <i>PyCharm's code inspector may finally relax (for now).</i>
- Simplified four instances of syntax for defining the interpolated images
    - np.arange(0, self.leftImage.shape[0], 1) → np.arange(self.leftImage.shape[0])
    
## Fixes
- Corrected an instance where the notification bar stated that the program was blending was in RGB mode instead of RGBA

# Version 0.2.6.1 - (2020-07-27)
## Changes
- Optimizations to Morphing.py's <b>loadTriangles()</b> and <b>getPoints()</b> functions
    - Declarations, re-assignments, loops, and return statements have been streamlined to be more efficient
- Optimized MorphingApp.py's <b>blendImages()</b> function to no longer have to [repeatedly] deepcopy each array slice
    - Initialization of a Morpher object will now deepcopy the passed arguments to its left and right image variables 
- Overhauled README.md to now support this program's releases
- Once again, removed more unnecessary module dependencies that were accidentally included in the last commit
## Fixes
- Fixed a bug where .png (RGBA) images could only be morphed into .jpg images (RGB)

# Version 0.2.6.0 - (2020-07-21)
## Changes
- Optimized out <i>several</i> for loops (both nested and not) in <b>blendImages()</b> in favor of more efficient NumPythonic syntax
    - Image deconstruction is now handled by dimension slicing, i.e., "leftColorValueR = leftARR[:, :, 0]"
    - Image reconstruction is now handled by this simple one-liner: "np.dstack((blendR, blendG, blendB, [blendA]))"</i>
    - Comment: <i>When recreating color images, the program will work with 3 or 4 array slices which later need to combine into one
    final image. My initial (inexperienced) approach was to create for loops in order to read the initial layers of data from the 
    two images into multiple lists (which were then converted and reshaped into arrays) and <b>then</b> to later create double for loops in order to iterate over the blended array
    data and append it all into one ordered list (which was then converted and reshaped into an array for image processing)...
    obviously, this lengthy explanation should highlight that this was all a very inefficient use of space and time.
    This has now been remedied.</i>
- Removed several module dependencies as well as the main block in Morphing.py in preparation for this program's first
release candidate
## Fixes
- <b>Resolved a known issue with point placement via the GUI where points were [often vertically] off center</b>
    - Comment: <i>TL;DR: The corner coordinates and scalar values (!!) for the left and right images weren't being calculated
    accurately enough. The methodology I adopted for this implementation (with the resize update) was a bit sloppy anyways,
    so variables such as <b>self.leftMinX</b>, <b>self.rightMaxX</b>, <b>self.maxY</b>, and more have all been removed in 
    favor of more dynamic Qt methods - e.g., <b>self.startingImage.geometry().topLeft().x()</b>.</i>
- Fixed an I/O crash where, if the Images_Points folder didn't exist, the program couldn't create new text files
- Fixed an index out of bounds crash when accessing images in <b>autoCorner()</b>
- Fixed a crash where the user could press the blend button before morphing was even enabled
    - Comment: <i>I actually laughed when I accidentally caught this during debugging.. what an entertaining oversight.</i>
- Fixed a bug where the GUI would fail to visibly update during the morphing process
    - The blend button now locks up, and the notification bar displays a relevant message while the program operates
    - Comment: <i>These things were already happening in the background; visible changes to the QtGui just wouldn't apply
    due to the fact that the MainWindow "wasn't responding." Qt's repaint() method serves as a simple workaround here.</i>
- Fixed a bug where regex in <b>loadDataLeft()</b> and <b>loadDataRight()</b> wasn't correctly detecting '.PNG' images
    - ".png$" → ".(PNG|png)$" 
- Fixed a bug where, after invoking <b>resetPoints()</b> with triangleUpdatePref on, the first set of added points would 
use the wrong size & style before being confirmed
- Fixed a bug where <b>resetPoints()</b> wasn't properly enabling the Add Corners button of the GUI
- Fixed a bug where the Reset Points button was sometimes incorrectly disabled after invoking Undo (CTRL + Z) on a newly 
confirmed set of points
    - "if len(confirmed_x) >= 3:" → "if len(chosen_x) + len(confirmed_x) >= 3:"
- Fixed a bug where old triangles would still display on the GUI after invoking <b>resetPoints()</b> with triangleUpdatePref on
- Fixed a bug where, when triangleUpdatePref was on but the triangle box was disabled, triangles were not displaying
during certain mousePressEvents
    - Comment: <i>There was an.. admittedly ugly.. triple nested conditional in <b>mousePressEvent()</b> that received
    a fair amount of cleanup with this update. The point of it was to check if the total number of chosen and confirmed
    points was at least 3 and then enable triangles - this doesn't work well after a reset with triangleUpdatePref, so now the conditional
    checks if the total number of added, chosen, and confirmed points is at least 3 (but only invokes when currentWindow
    is set to the left image).</i>
- Fixed a bug where invoking <b>autoCorner()</b> wasn't re-checking the triangle box when triangleUpdatePref was on
- "Fixed" a bug where triangle color values weren't being remembered by the program when disabled/enabled
    - Comment: <i>The moment I began debugging this, the issue mysteriously resolved itself without any lasting change 
    to the source code.</i>
- Removed an instance where self.currentWindow was unnecessarily set in <b>resetPoints()</b>
- Removed an instance where <b>refreshPaint()</b> was being invoked twice in <b>resetPoints()</b>
- Removed the self.resetFlag variable
    - Comment: <i>With this update's implementation of bug fixes for <b>resetPoints()</b>, this variable became obsolete
    and is consequently being removed.</i>
- Other general code cleanup

# Version 0.2.5.1 - (2020-07-07)
## Known Bugs
- Instances where points added through the GUI are vertically off center
    - Especially apparent after the first blend has been executed (which reshapes the GUI by a bit)
## Unreleased
- Multithreading / multiprocessing implementation for <b>getImageAtAlpha()</b> in order to improve performance
    - Comment: <i>Multiprocessing is applicable to the matrix math while multithreading is applicable to sharing the
    same image variable for assigning interpolated values.</i>
## Changes
- <b>The morphing algorithm has received a significant increase in performance</b>
    - Matrix multiplication is now conducted across each triangle's entire set of points at once (as opposed to 
    multiplying each individual point at a time)
    - Roughly translates to a 20% speedup
- Assignment of self.leftInterpolation and self.rightInterpolation has been moved from <b>getImageAtAlpha()</b> to the
 initialization of the given Morpher object in order to reduce the number of calls to RectBivariateSpline()
- Moved image interpolation from <b>getImageAtAlpha()</b> to the new <b>interpolatePoints()</b>

# Version 0.2.5.0 - <i>Endless Polishing</i> (2020-07-01)
## Known Bugs
- Instances where points added through the GUI are vertically off center
    - Especially apparent after the first blend has been executed (which reshapes the GUI by a bit)
## Added
- <b>Full Blending Input</b>
    - When the full blending box is checked, a new text box is enabled for the user to specify their desired alpha
    increment to be used for generating and displaying frames
    - The default full blending value is still 0.05 but can now be set as low as 0.001 or as high as 0.25
        - A Qt mask is used to restrict some (but not all) letter and symbol input - format is [0-1].[0-9][0-9]{0,1,2}
        - The program handles all other invalid inputs (1.0, 0.000, etc)
    - The alpha slider and it's tick marks will now dynamically change in response to changes to the full blend value
        - The program will intelligently modify the user's given value to one that best fits the slider
            - For example, if given 0.14, the program will automatically change it to 0.142 for the user's convenience
- <b>Reset Alpha Slider</b>
    - Since the user is now able to cause changes to the alpha slider's parameters, there is now a reset button for it
        - Resetting the alpha slider will also reset the full blend value to default as well
## Changes
- Revised and created additional tooltips in MorphingGUI.ui and MorphingGUI.py
- Revised when self.fullBlendComplete is set to False in order to safely accommodate feature update
    - For example, after a full blend, changing the input value disables self.fullBlendComplete
- Revised all five array declarations in Morphing.py's <b>getImageAtAlpha()</b> so that they no longer require reshaping afterwards 
- Rewrote x & y min/max statements in Morphing.py's <b>getPoints()</b> to be more NumPythonic
    - "min(self.vertices[0][0], self.vertices[1][0], self.vertices[2][0]))" → "self.vertices[:, 0].min()"
- Rewrote a conditional in <b>loadDataLeft()</b> and <b>loadDataRight()</b> to check whether the two images are on instead
of whether the two images have scaled contents
    - Comment: <i>This effectively doesn't change behavior at all, but it makes more sense to be written this way. If
    the two images have scaled contents, they're both on anyways.. so just check for that.</i>
- Moved all "self.triangleBox.setEnabled(0)" lines to come after "self.triangleBox.setChecked(0)" instead of the other way around
- Updated the GUI's MainWindow icon from Qt's default icon to "Morphing.ico"
    - Comment: <i>This is currently locked at an awkward size of <b>24</b> x <b>24</b>... If that can't be changed, the
    icon will be redesigned. Still attempting to set an application icon as well.</i>
- Optimized: Removed 3 SLOC each from MorphingApp.py's <b>keyPressEvent()</b> (2x), <b>resetPoints()</b>, <b>loadDataLeft()</b>, and <b>loadDataRight()</b>
    - "if tri.isChecked(): triPref = 1 else: triPref = 0" → "triPref = int(tri.isChecked())"
- Optimized: Removed 24 SLOC (26% reduction) from MorphingApp.py's MainWindow constructor. All GUI initializations have 
been shifted from MorphingApp.py to MorphingGUI.ui & MorphingGUI.py.
    - Comment: <i>These were pretty much just a waste of space - some lines accomplished nothing at all. 
    Other times, MorphingGUI.ui and MorphingGUI.py were enabling elements just for the initializer to immediately 
    disable them afterwards.</i>
- Optimized: Removed 7 SLOC (32% reduction) from MorphingApp.py's <b>updateTriangleWidget()</b>
    - "if val: x.setEnabled(1) else: x.setEnabled(0)" → "x.setEnabled(val)"
- Updated README.md
## Fixes
- Fixed an issue where the right image's triangle vertices were being loaded from type List instead of type Array
- Fixed an issue where tooltips could appear over blank space, as some GUI elements were "wider" than they actually were
- Fixed a bug where loading new images with Show Triangles checked would break both the checkbox and the triangle
painter
    - Comment: <i>This was a particularly nasty bug. It ended up mainly being caused by a state change method that triggered
    whenever the triangle box was modified. This method was setting flags at the same time as the calling block, which
    led to really weird and unpredictable behavior that was difficult to debug.</i>
- Removed an event signal where invoking <b>loadDataLeft()</b> would simultaneously invoke <b>displayTriangles()</b>
    - Comment: <i>This may have also contributed to the aforementioned bug, above.</i>
- Removed several imported modules that were no longer being utilized by the program
- Fixed a bug where the user's triangle preference wasn't being set to 0 when the box was unchecked
- Fixed a bug where <b>autoCorner()</b> had to place corner points that were off by a pixel
    - (1, 1), (1, y - 1), (x - 1, 1), (x - 1, y - 1) → (0, 0), (0, y), (x, 0), (x, y)
- Replaced a global (and hard-coded) DataPath variable that wasn't being used with a dynamic root directory variable. Hard coded
text file paths in <b>loadDataLeft()</b> and <b>loadDataRight()</b> now instead build on ROOT_DIR
    - Comment: <i>Now this program can start having release candidates! Once module import woes get sorted out, anyways.</i>
- Removed an unnecessary call to <b>refreshPaint()</b> in <b>loadDataLeft()</b> and <b>loadDataRight()</b>
- Removed a conditional in both <b>loadDataLeft()</b> and <b>loadDataRight()</b> that wasn't necessary
    - "if self.leftOn == 0: self.leftOn = 1" → "self.leftOn = 1"
- Removed a chained conditional in both <b>loadDataLeft()</b> and <b>loadDataRight()</b> that wasn't being used
    - "if x is None; else if x is PNG; else" → "if x is None; else"
        - Comment: <i>In this pseudo-example, x is the return of a regex search for ".png", so it will either be None or it won't.
        Both cases are indicative of what behavior should follow, so there is no need for a second conditional.</i>
- Removed two nested conditionals in <b>loadDataLeft()</b> and <b>loadDataRight()</b> that could have been simplified
into the parent
    - "if x == y: if x >= 3: if y >= 3: ..." → "if x == y >= 3"
- Removed a conditional in <b>resetPoints()</b> that wasn't necessary
    - Comment: <i>Checking for whether the two images are on is redundant in this case as the two images must be on for
    <b>resetPoints()</b> to be called anyways.</i>
- The self.fullBlendComplete flag now gets set to 0 after a normal blend is executed
    - Comment: <i>This was a harmless oversight at the time of full blending's creation but became a potentially 
    dangerous bug with the addition of user input.</i>
- Other general code cleanup

# Version 0.2.4.0 - (2020-06-27)
## Added
- <b>Full Blending</b>
    - The user can now check the Full Blend box before clicking blend to have the program generate a frame for each 0.05
    alpha increment blend of the two images
    - Once the program finishes full blending, the user can use the alpha slider to display (in realtime) the 
    corresponding frame for each alpha increment.

Comment: <i> Since full blending renders 21 frames instead of 1, it is naturally slower than normal blending and,
because of this, is disabled by default.</i>
## Changes
- Additional performance improvements to MorphingApp.py's paintEvent():
    - Removed all calls to set the QPen and its color when drawing points
        - Comment: <i> The QPainter by itself is more than enough for this task.</i>
- Added notification line condition for toggling the Full Blend box:
    - "Successfully enabled/disabled full blending."
- Updated README.md
## Removed
- Removed unrelated and unnecessary folders/files from the repository (oops!)
## Fixes
- Removed an extra (unnecessary) call to refreshPaint() in mousePressEvent()

# Version 0.2.3.0 - <i> The Cleanup Update </i> (2020-06-26)
## Unreleased
- Potential incomplete fix for interpolation performance by way of manual pixel calculation (instead of using scipy's
RectBivariateSpline function, which is ~58% of this program's runtime)
## Changes
- Completely rewrote MorphingApp.py's paintEvent() to be far more efficient and much smaller (91 lines removed - a 60% 
reduction in SLOC)
    - Added "resize" and "change" flags to prevent paintEvent from unnecessarily triggering
        - Resize performance (especially with larger/color images) has been significantly improved by this
    - Restructured the function to try drawing triangles first (with a conditional) and then draw points after 
    (instead of either drawing all triangles and all points or only drawing all points)
        - This reduces the size of the function without changing behavior
    - Moved all re-declarations of QPainter, QPen(), and it's width to initialization; removed unnecessary QPainter.end() calls
        - Comment: <i> At the time of creation of Version 1.0, there could only be one QPainter at a time (for whatever
        reason, most likely through fault of my own), so multiple initializations/terminations were required. 
        Version 0.2.3.0 can have multiple QPainters active at a time and, consequently, has no need for this behavior.</i>
    - Removed all "if QPainter.isactive" checks
        - Comment: <i> As far as I'm aware, these never did anything to begin with.</i>
    - Removed unnecessary "changes" to the left/right images after painting
        - Enabling the image and the scaling of its contents is handled by the image loaders and doesn't need to be here
- Slightly modified how the notification line reacts to changes with the red/blue/green sliders as well as blend status
    - "Red value changed from X to Y." → "Red value set to X."
    - "Morph took X seconds." → "RGB morph took X seconds."
## Fixes
- Interpolated data is now saved directly to the image variables in Morphing.py's getImageAtAlpha()
    - The function was assigning all final interpolated image values to a left and right "copy", which was 
then saved to the corresponding image variables. This "copy" was redundant and unnecessary, so it has been removed.
- New points are now added directly to the confirmed list in MorphingApp.py's autoCorner()
    - Similar to the fix above, newly added points were being appended to the list of temporary points and then
    immediately popped out and appended to the list of confirmed points. This "copying" behavior was, again, redundant
    and unnecessary, so it has been removed.
- Removed a redundant nested conditional in resetPoints() where both conditions disabled deletion and called the painter
- Oftentimes, paintEvent() was being invoked <b>twice</b> for each change (a relic of Version 1.0's poorly implemented 
painter behavior). This has been fixed in the following functions:
    - autoCorner()
    - resetPoints()
    - <b>refreshPaint()</b> 
        - Comment: <i> Obviously, this one is a big deal. Paint events were being called twice as often as was necessary,
        so resolving this issue has significantly improved GUI performance (especially with the RGB sliders).</i>
- Removed all remaining instances of self.update(), self.leftUpdate, and self.rightUpdate
    - Comment: <i> These were relics of Version 1.0's poorly implemented painter behavior (self.update() may have even
    been redundant). Truthfully, I don't know what self.update() was even supposed to do - even then - as I can't find 
    anything about it online. There may have been a time when it somehow invoked paintEvent(), but this is no longer 
    needed (as a new function expressly exists for this purpose). Thus, self.update() has been replaced with 
    self.refreshPaint() for clarity's sake.</i>
- Instances where other functions were directly calling paintEvent() have been replaced with calls to refreshPaint() instead
- Other general code cleanup

# Version 0.2.2.0 (2020-06-21)
## Added
- <b>Triangle Widget</b>
    - When the user enables Show Triangles, there is now an accessible widget that provides RGB sliders to change the
    color of the triangles in realtime

Comment: <i>This is strictly a QoL change for users, whether they have a preferred color or that a different color may
be easier to see on top of the two images. Clarity is key.</i>
## Changed
- Changed the following elements in MorphingGUI.ui and MorphingGUI.py:
    - Changed the main window's title from "MainWindow" to "Python Image Morpher"
    - Minimum size of the main window has changed from <b>(630 x 611)</b> to <b>(878 x 797)</b>
    - Minimum size of the image panels has changed from <b>(300 x 225)</b> to <b>(424 x 318)</b>
    - Added labeled red, green, and blue sliders to the "Morphing Functions" container
        - These sliders respectively invoke the new updateRed(), updateGreen(), and updateBlue() functions, which are
        used to modify the painter
## Fixes
- The blend button is now disabled during the time that the program is executing a blend command

# Version 0.2.1.0 (2020-06-20)
## Added
- <b>Notification Bar</b>
    - The GUI now displays an information panel at the bottom left that outputs the status of the user's actions
        - For example, using Add Corners will evoke either: "Successfully added X new corner point(s)" or "Failed to add
        any new corner points."
## Changed
- Added notification conditions for:
    - Adding corners
    - Resetting points
    - Pressing backspace
    - Entering CTRL+Z
    - Entering CTRL+Y
    - Toggling transparency
    - Modifying alpha
    - Loading images
    - Blending images
## Removed
- Removed all console print statements
## Fixes
- Add Corners no longer creates additional points that already existed

# Version 0.2.0.0 - <i>The GUI Overhaul</i> (2020-06-17)
## Added
- <b>Resizing</b>
    - The user is now able to freely resize the window along with its contents
        - Image windows will now dynamically resize themselves to be as large as possible
- <b>Triangle Preference</b>
    - The program now remembers the user's preference for the "Show Triangles" setting
        - If an action causes this setting to become disabled, the program will re-enable it the next time it is available
- <b>Transparency Blending Toggle</b>
    - The user is now able to specify whether they want to blend the alpha layer of images
        - This setting only affects .PNG images
## Changed
- Changed the following elements in MorphingGUI.ui and MorphingGUI.py:
    - Applied a grid layout to the main window
        - Restructured the entire GUI based on the grid layout
    - Added a spacer to the main window
    - Added a "Morphing Functions" container for buttons, sliders, etc.
    - Added self.transparencyBox to the main window
    - Minimum size of the main window has changed from <b>(740 x 705)</b> to <b>(630 x 611)</b>

## Removed
- Removed the following elements from MorphingGUI.ui and MorphingGUI.py:
    - self.startingFrame
    - self.endingFrame
    - self.blendingFrame
    - self.startingImageTriangles
    - self.endingImageTriangles

Comment: <i> This update rewrote paintEvent() such that the input images no longer need a
separate triangle layer. The frames served as containers for both the images as well as their respective triangle layers 
(in this regard, there was no point in self.blendingFrame anyways). Thus, all of these elements are being removed.</i>
    
## Fixes
- Removed instances of self.update() when loading images
- Other general code cleanup
