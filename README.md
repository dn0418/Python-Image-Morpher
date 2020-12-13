<p align="center">
  <img src="https://i.imgur.com/SLDEtSR.png"><br>
</p>

Python Image Morpher (PIM) is a program that can take two images and blend them to whatever extent or precision that you like!
It is designed to emulate some of Python's OpenCV image processing from scratch without reference.

<p align="center">
  <img src="https://media3.giphy.com/media/ibAOyLgNhxnWHuKvZn/giphy.gif"><br>
</p>

This project began in Spring 2019 (detailed in <b>readme_general.pdf</b>, <b>readme_phase_1.pdf</b>, and <b>readme_phase_2.pdf</b>),
 requiring the usage of <b>delaunay triangulation</b>, <b>projective/affine transformation</b>, <b>application of projections 
 through matrices</b>, <b>masking,</b> and <b>alpha blending</b> - all of which are still maintained - in order to accomplish image 
 morphing. Thus, this repository is more of a 'proof of concept' than it is the most efficient way of accomplishing the given task of image morphing. 

 So far, this program has only been tested on separate Windows environments; 
 if it does not already, later releases are likely to support Mac and Linux.

<p align="center">
  <img width="650" height="651" src="https://i.imgur.com/fXZN3om.png"><br>
</p>

## Installation:
This program has dependencies that do not come packaged with Python 3. To install the required modules, enter the following command using the terminal supplied by Windows or your choice of IDE (such as PyCharm):

```pip install -r requirements.txt```

Alternatively, for each module below that your machine does not have installed, enter the respective command(s):

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

<p align="center">
  <img src="https://i.imgur.com/j7JStm4.gif"><br>
</p>
<p align="center"><i>Proof of Concept - Perspective Shifting</i><p align="center">

## Development 'To-Do' List:
- <b>Change:</b> Improved Morphing Performance
    - <i>Currently, interpolation is the biggest bottleneck, second to the required matrix math. Some steps have already been taken but this is a complicated issue with the project that stems from the very nature of its existence - see Paragraph 2 of README.</i>
- <b>Feature:</b> Automatic Correspondence Determination
    - The user may click a button to have PIM automatically generate points by scanning for similar features between images
- <b>Feature:</b> Resizable Image Points
    - Placed points now scale in size with their respective image (i.e. smaller images will use smaller points by default)
    - Additionally, the user may manually scale point size with a slider on the GUI

If you encounter an error, a bug, or if you simply wish to request a change/feature, please file an issue using the tracker that GitHub provides, [here](https://github.com/ddowd97/Morphing/issues).

If you like what you see, feel free to contact me on [LinkedIn](https://www.linkedin.com/in/davidmilesdowd/).
