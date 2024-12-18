# NCGenerator
A simple .nc file generator I'm working on for my CNC.

It is configured via code, set it up by modifying nc_generator.py and then running it. There are 3 typical ways to use this. They all start off by creating a generator object, for example:
```python
nc_generator = generator.Generator(MM_RATIO, BIT_SIZE)
```
In the constructor, set how wide the bit is and how many mm to move per pixel. More options can be set by the constants in generator.py.  

To carve along the edges of any color changes, first create a list of points for each pixel near an edge, for example:  
```python
image = Image.open(INPUT_FILE)
points = data_classes.Points.from_image_color_edge(image)
```
Afterwards, create paths that go through these points, for example:
```python
paths = data_classes.Paths.from_points(points)
# optional, removes redundant points from the paths
paths.compress()
```
Finally, pass these points to the generator and export the nc file.
```python
nc_generator.carve_paths(paths, DEPTH)
nc_generator.export(OUTPUT_FILE)
```

To instead carve along the center of lines, replace the line that gets the points as follows:
```python
points = data_classes.Points.from_image_trace(image)
```
This function converts the image to a 1 bit black and white image, and attempts to trace along the center of any lines.

A heightmap is similar, but instead of creating paths, create a heightmap as follows:
```python
heightmap = data_classes.Heightmap.from_image(image)
nc_generator.carve_heigtmap(heightmap, MIN_DEPTH, MAX_DEPTH, both_directions=True)
```
Follow the same steps are before the create the generator and export the nc file.
