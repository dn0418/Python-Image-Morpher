<p align="center">
  <img src="https://i.imgur.com/SLDEtSR.png"><br>
</p>

Python Image Morpher (PIM) is a program that can take two images and blend them to whatever extent or precision that you like!
It is designed to emulate some of Python's OpenCV image processing from scratch without reference.

This project began in Spring 2019 (detailed in <b>readme_general.pdf</b>, <b>readme_phase_1.pdf</b>, and <b>readme_phase_2.pdf</b>),
 requiring the usage of <b>delaunay triangulation</b>, <b>projective/affine transformation</b>, <b>application of projections 
 through matrices</b>, <b>masking,</b> and <b>alpha blending</b> - all of which are still maintained with this project - in order 
 to accomplish image morphing. Thus, this repository is more of a 'proof of concept' than it is the most efficient way of 
 accomplishing the given task of image morphing. 
 
 So far, this program has only been tested on separate Windows environments; 
 if it does not already, later releases are likely to support Mac and Linux.

<p align="center">
  <img width="650" height="651" src="https://i.imgur.com/1yO5slA.png"><br>
</p>

## Installation:
This program has dependencies that do not come packaged with Python 3.8. For each module below that your machine does not have installed, enter the respective command using the terminal supplied by Windows or your choice of IDE (such as PyCharm).

<b>PyQt5</b> - ```pip install pyqt5```

<b>SciPy</b> - ```pip install scipy```

<b>NumPy</b> - ```pip install numpy```

<b>Imageio</b> - ```pip install imageio```

<b>Matplotlib</b> - ```pip install matplotlib```

If pip, for whatever reason, is not installed on your machine, enter the following line in a terminal:
```
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
```
Then navigate to the folder where get-pip.py was downloaded and enter the following line in a terminal:
```
python get-pip.py
```

## Usage:
- Run MorphingApp.py either through the terminal or using an IDE
- Use the graphical interface to select your two images to morph
- Click on points of interest in your images to create correspondences
- When satisfied, click on blend and observe the result!

## Development 'To-Do' List:
- :heavy_check_mark: Color Picker Widget (User may specify color used for triangles)
- Redo / CTRL + Y (User may redo an action that was previously undone or deleted)
- :heavy_check_mark: Full Blend (User may toggle a flag that tells the program to render each specified alpha increment blend and the alpha slider instead displays each frame)
- Improved Performance (Currently, interpolation is the biggest bottleneck, second to the required matrix math)

If you encounter an error, a bug, or if you simply wish to request a change/feature, please file an issue using the tracker that GitHub provides, [here](https://github.com/ddowd97/Morphing/issues).

If you like what you see, feel free to contact me on [LinkedIn](https://www.linkedin.com/in/davidmilesdowd/).
