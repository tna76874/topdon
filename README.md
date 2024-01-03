# Topdon Web Viewer

Python Software to use the Topdon TC001 Thermal Camera on Linux via a webserver. Source Code adapted from:

- [https://github.com/leswright1977/PyThermalCamera](https://github.com/leswright1977/PyThermalCamera)
- [https://github.com/LeoDJ/P2Pro-Viewer/blob/23887289d3841fdae25c3a11b8d3eed8cd778800/P2Pro/video.py](https://github.com/LeoDJ/P2Pro-Viewer/blob/23887289d3841fdae25c3a11b8d3eed8cd778800/P2Pro/video.py)

Access local (or via network)  webinterface to control the Topdon thermal cam.

<video width="640" height="360" controls>   <source src="doc/topdon_viewer_demo.m4v" type="video/mp4">   Your browser does not support the video tag. </video>

Video after recording - the temperatures of the spots are also saved within an csv file.

<video width="640" height="360" controls>   <source src="doc/TC001_20240103-101243.m4v" type="video/mp4">   Your browser does not support the video tag. </video>

#### Installation

```bash
pip3 install --upgrade git+https://github.com/tna76874/topdon.git
```

#### Anaconda

```bash
git clone https://github.com/tna76874/topdon.git
cd topdon
conda env create -f environment.yml
```

