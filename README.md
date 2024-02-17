# Topdon Web Viewer

Access local (or via network)  webinterface to control the Topdon thermal cam.

https://github.com/tna76874/topdon/assets/47271687/af8a17ed-03f9-41e8-bd22-39dc8a3c6230

Video after recording - the temperatures of the spots are also saved within an csv file.

https://github.com/tna76874/topdon/assets/47271687/6ee63fcc-4ae0-420e-a82a-20a28b4657a5

#### Installation

```bash
sudo apt-get install libgl1
pip3 install --upgrade git+https://github.com/tna76874/topdon.git
```

#### Anaconda

```bash
git clone https://github.com/tna76874/topdon.git
cd topdon
conda env create -f environment.yml
```

## Acknowledgements

Python Software to use the Topdon TC001 Thermal Camera on Linux via a webserver. Source Code adapted from:

- [https://github.com/leswright1977/PyThermalCamera](https://github.com/leswright1977/PyThermalCamera)
- [https://github.com/LeoDJ/P2Pro-Viewer/blob/23887289d3841fdae25c3a11b8d3eed8cd778800/P2Pro/video.py](https://github.com/LeoDJ/P2Pro-Viewer/blob/23887289d3841fdae25c3a11b8d3eed8cd778800/P2Pro/video.py)
