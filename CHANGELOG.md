# Version 2.5 - <i>Endless Polishing</i> (2020-07-01)
## Known Bugs
- Instances where points added through the GUI are vertically off center
    - Especially apparent after the first blend has been executed (which reshapes the GUI by a bit)
##Added
- <b>Full Blending Input</b>
    - When the full blending box is checked, a new text box is enabled for the user to specify their desired alpha
    increment to be used for generating and displaying frames.
    - The default full blending value is still 0.05 but can now be set as low as 0.001 or as high as 0.25
        - A Qt mask is used to restrict some (but not all) letter and symbol input - format is [0-1].[0-9][0-9]{0,1,2}
        - The program handles all other invalid inputs (1.0, 0.000, etc)
    - The alpha slider and it's tick marks will now dynamically change in response to changes to the full blend value
        - The program will intelligently modify the user's given value to one that best fits the slider
            - For example, if given 0.14, the program will automatically change it to 0.142 for the user's convenience
- <b>Reset Alpha Slider</b>
    - Since the user is now able to cause changes to the alpha slider's parameters, there is now a reset button for it
        - Resetting the alpha slider will also reset the full blend value to default as well
        
##Changes
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
    - Comment: <i>These were pretty much just a waste of space - some of the lines accomplished nothing at all. 
    Other times, MorphingGUI.ui and MorphingGUI.py were enabling elements just for the initializer to immediately 
    disable them afterwards.</i>
- Optimized: Removed 7 SLOC (32% reduction) from MorphingApp.py's <b>updateTriangleWidget()</b>
    - "if val: x.setEnabled(1) else: x.setEnabled(0)" → "x.setEnabled(val)"
- Updated README.md
## Fixes
- Fixed an issue where the right image's triangle vertices were being loaded from type List instead of type Array
- Fixed an issue where tooltips could appear over blank space, as some GUI elements were "wider" than they actually were
- Fixed a bug where loading new images with Show Triangles checked would break both the checkbox as well as the triangle
painter
    - Comment: <i>This was a particularly nasty bug. It ended up mainly being caused by a state change method that triggered
    whenever the triangle box was modified. This method was setting flags at the same time as the calling block, which
    led to really weird and unpredictable behavior that was difficult to debug.</i>
- Removed several package imports that were no longer being utilized by the program
- Removed an event signal where invoking <b>loadDataLeft()</b> would simultaneously invoke <b>displayTriangles()</b>
    - Comment: <i>This may have also contributed to the aforementioned bug, above.</i>
- Fixed a bug where the user's triangle preference wasn't being set to 0 when the box was unchecked
- Fixed a bug where <b>autoCorner()</b> had to place corner points that were off by a pixel
    - (1, 1), (1, y - 1), (x - 1, 1), (x - 1, y - 1) → (0, 0), (0, y), (x, 0), (x, y)
- Replaced a global (and hard-coded) DataPath variable that wasn't being used with a dynamic root directory variable. Hard coded
text file paths in <b>loadDataLeft()</b> and <b>loadDataRight()</b> now instead build off of ROOT_DIR
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
    - Comment: <i>Checking for whether the two images are on is redundant in this case as the two image must be on for
    <b>resetPoints()</b> to be called anyways.</i>
- The self.fullBlendComplete flag now gets set to 0 after a normal blend is executed
    - Comment: <i>This was a harmless oversight at the time of full blending's creation but became a dangerous bug 
    with the addition of user input.</i>
- Other general code cleanup

# Version 2.4 - (2020-06-27)
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

# Version 2.3 - <i> The Cleanup Update </i> (2020-06-26)
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
        Version 2.3 can have multiple QPainters active at a time and, consequently, has no need for this behavior.</i>
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

# Version 2.2 (2020-06-21)
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

# Version 2.1 (2020-06-20)
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

# Version 2.0 - <i>The GUI Overhaul</i> (2020-06-17)
## Added
- <b>Resizing</b>
    - The user is now able to freely resize the window along with its contents
        - Image windows will now dynamically resize themselves to be as large as possible
- <b>Triangle Preference</b>
    - The program now remembers the user's preference for the "Show Triangles" setting
        - If an action causes this setting to become disabled, the program will re-enable it the next time it is available
- <b>Transparency Blending Toggle</b>
    - The user is now able to specify whether or not they want to blend the alpha layer of images
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
