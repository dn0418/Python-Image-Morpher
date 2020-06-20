# Python Image Morpher
This is my personal project that began as a final assignment in Purdue University's ECE 36400 - Software Engineering Tools Lab. 

What began in Spring 2019 (detailed in <b>readme_general.pdf</b>, <b>readme_phase_1.pdf</b>, and <b>readme_phase_2.pdf</b>) required the usage of <b>delaunay triangulation</b>, <b>projective/affine transformation</b>, <b>application of projections through matrices</b>, <b>masking,</b> and <b>alpha blending</b> - all of which are still maintained with this project - in order to accomplish image morphing. A custom GUI was additionally required in order for users to place their own points to be used with the matrix math involved with this program.

<p align="center">
  <img width="469" height="470" src="https://i.imgur.com/BJkzrfL.jpg"><br>
  <i>Required GUI for ECE 36400</i>
</p>

Now that I'm no longer in this course and the source code is mine to freely modify, I've taken it upon myself to improve this image morphing application in my leisure as a for-fun project. At the time of the creation of this README, meaningful changes include (but are, in no capacity, limited to):

* Color Image Compatibility
* Multiprocessing
* GUI Overhaul
* Resizing
* Added Functionality 
  * Reset, Undo, Add Corners, Transparency Toggle
And other general cleanup, bugfixes, polish, etc.

<p align="center">
  <img width="632" height="622" src="https://i.imgur.com/mT0kTn9.jpg"><br>
  <i>Redesigned & Resizable GUI (WIP)</i>
</p>

In the future, I plan to continue improving on this neat little program. Currently, I have ideas regarding:

- [ ] Color Picker Widget (User may specify color used for added/confirmed/chosen points and triangles)
- [ ] Redo / CTRL + Y (User may redo an action that was previously undone or deleted)
- [ ] Full Blend (User may toggle a flag that tells the program to render each 0.05 alpha increment blend)
- [ ] Improved Performance (Currently, interpolation is the biggest bottleneck, second to the required matrix math)

If you like what you see, feel free to contact me on [LinkedIn](https://www.linkedin.com/in/davidmilesdowd/).
