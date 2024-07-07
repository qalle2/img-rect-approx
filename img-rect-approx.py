# approximate an image by drawing rectangles at random

import os, sys, time
from itertools import chain
from random import randrange
try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow module required. See https://python-pillow.org")

# how often to print a status message
PRINT_EVERY_N_ROUNDS = 100

def parse_integer(stri, minValue, descr):
    try:
        value = int(stri, 10)
        if value < minValue:
            raise ValueError
    except ValueError:
        sys.exit(f"{descr} must be an integer and {minValue} or greater.")
    return value

def parse_args():
    # parse command line arguments

    if not 3 <= len(sys.argv) <= 5:
        sys.exit(
            "Arguments: inputFile outputFile [numberOfRectangles "
            "[maxRectangleSize]]"
        )
    (inputFile, outputFile) = sys.argv[1:3]
    rectCount = sys.argv[3]   if len(sys.argv) >= 4 else "1000"
    maxRectSize = sys.argv[4] if len(sys.argv) >= 5 else "20"

    rectCount   = parse_integer(rectCount,   0, "Number of rectangles")
    maxRectSize = parse_integer(maxRectSize, 1, "Maximum rectangle size")

    if not os.path.isfile(inputFile):
        sys.exit("Input file not found.")
    if os.path.exists(outputFile):
        sys.exit("Output file already exists.")

    return {
        "inputFile":   inputFile,
        "outputFile":  outputFile,
        "rectCount":   rectCount,
        "maxRectSize": maxRectSize,
    }

def read_image(filename, minWidthAndHeight):
    # read image file;
    # generate: one pixel row (tuple of tuples of ints) per call
    with open(filename, "rb") as handle:
        handle.seek(0)
        image = Image.open(handle)

        if image.width < minWidthAndHeight:
            sys.exit(f"Must be at least {minWidthAndHeight} pixels wide.")
        if image.height < minWidthAndHeight:
            sys.exit(f"Must be at least {minWidthAndHeight} pixels tall.")
        if image.mode in ("L", "P"):
            image = image.convert("RGB")
        elif image.mode != "RGB":
            sys.exit(
                "Unrecognized pixel format (try removing the alpha channel)."
            )

        for y in range(image.height):
            yield tuple(image.crop((0, y, image.width, y + 1)).getdata())

def get_average_color(image, imageWidth, imageHeight):
    # get the average color of an image
    # image:  iterable of iterables of tuples of ints
    # return: (red, green, blue)
    componentSums = [0 for i in range(3)]
    for pixel in chain.from_iterable(image):
        for i in range(3):
            componentSums[i] += pixel[i]
    return tuple(
        round(s / (imageWidth * imageHeight)) for s in componentSums
    )

def get_color_diff(color1, color2):
    # get difference of two colors
    # color1, color2: (red, green, blue)
    # return:         difference (int)
    return (
          2 * abs(color1[0] - color2[0])
        + 3 * abs(color1[1] - color2[1])
        +     abs(color1[2] - color2[2])
    )

def get_image_diff(image1, image2):
    # get difference between two images
    # image1: iterable of iterables of tuples of ints
    # image2: iterable of iterables of tuples of ints
    # return: difference (int)
    return sum(
        sum(get_color_diff(pix1, pix2) for (pix1, pix2) in zip(row1, row2))
        for (row1, row2) in zip(image1, image2)
    )

def get_image_and_color_diff(image, color):
    # get difference between an image and a color (as if one of two images was
    # filled with that color)
    # image:  iterable of iterables of tuples of ints
    # color:  (red, green, blue)
    # return: total difference
    return sum(
        sum(get_color_diff(pix, color) for pix in row) for row in image
    )

def get_random_rect(imageWidth, imageHeight, maxRectSize):
    # get the properties of a random rectangle
    # return: (dimensions, colors); that is,
    #         ((x, y, width, height), (red, green, blue))
    width  = randrange(1, maxRectSize + 1)
    height = randrange(1, maxRectSize + 1)
    x      = randrange(imageWidth  - width + 1)
    y      = randrange(imageHeight - height + 1)
    color  = tuple(randrange(256) for i in range(3))
    return ((x, y, width, height), color)

def crop_image(image, dimensions):
    # image:      iterable of iterables of tuples of ints
    # dimensions: (x, y, width, height)
    # return:     tuple of tuples of tuples of ints
    (xStart, yStart, width, height) = dimensions
    return tuple(
        tuple(row[xStart:xStart+width]) for (y, row) in enumerate(image)
        if yStart <= y < yStart + height
    )

def write_image(pixels, imageWidth, imageHeight, filename):
    # write a PNG file
    # pixels: iterable of iterables of tuples of ints

    # copy pixels to image via temporary image
    image = Image.new("RGB", (imageWidth, imageHeight))
    pixelRowImg = Image.new("RGB", (imageWidth, 1))
    for (y, pixelRow) in enumerate(pixels):
        pixelRowImg.putdata(pixelRow)
        image.paste(pixelRowImg, (0, y))
    # save image
    with open(filename, "wb") as handle:
        handle.seek(0)
        image.save(handle, "png")

def main():
    startTime = time.time()
    args = parse_args()

    print("Reading {}...".format(args["inputFile"]))
    # tuple of tuples of tuples of ints
    origImage = tuple(read_image(args["inputFile"], args["maxRectSize"]))
    imageHeight = len(origImage)
    imageWidth  = len(origImage[0])

    # create canvas filled with average color of original image:
    # list of lists of tuples of ints
    origAverageColor = get_average_color(origImage, imageWidth, imageHeight)
    print("Creating a blank canvas filled with color {}...".format(
        origAverageColor
    ))
    newImage = [
        [origAverageColor for x in range(imageWidth)]
        for y in range(imageHeight)
    ]

    initialImageDiff = get_image_diff(origImage, newImage)
    currentImageDiff = initialImageDiff

    print(
        "Painting {} rectangle(s) of maximum width & height {} on canvas..."
        .format(args["rectCount"], args["maxRectSize"])
    )

    for round_ in range(1, args["rectCount"] + 1):
        # get a random rectangle that would make the current image less
        # different from the target image
        while True:
            (dimensions, color) = get_random_rect(
                imageWidth, imageHeight, args["maxRectSize"]
            )
            origCropped = crop_image(origImage, dimensions)
            newCropped  = crop_image(newImage,  dimensions)
            oldRectDiff = get_image_diff(origCropped, newCropped)
            newRectDiff = get_image_and_color_diff(origCropped, color)
            if newRectDiff < oldRectDiff:
                break

        # apply rectangle to current image
        (xStart, yStart, width, height) = dimensions
        for y in range(yStart, yStart + height):
            newImage[y][xStart:xStart+width] = width * [color]

        # update difference from original image
        currentImageDiff -= oldRectDiff - newRectDiff

        # print status every n rounds
        if round_ % PRINT_EVERY_N_ROUNDS == 0:
            print(
                "{:6} rectangle(s) painted. Canvas differs from original "
                "image {:4.1f}% less than blank canvas did.".format(
                    round_, (1 - currentImageDiff / initialImageDiff) * 100
                )
            )

    print("Writing canvas to {}...".format(args["outputFile"]))
    write_image(newImage, imageWidth, imageHeight, args["outputFile"])

    print("Time elapsed: {:.1f} second(s).".format(time.time() - startTime))

main()
