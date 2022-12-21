from PIL import Image
import data_classes
import generator

def main():
    points = []
    for i in range(10):
        points.append(data_classes.Point(i,0))
    
    for p in data_classes.Points(points):
        print(p)
    for p in data_classes.Path(points):
        print(p)

if __name__ == "__main__":
    main()
