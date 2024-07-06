# approximate an image by drawing rectangles at random;
# continue forever and save an image every n rounds

import os, sys, time
from itertools import chain
from random import randrange
try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow module required. See https://python-pillow.org")

# maximum width & height of rectangles;
# smaller = better quality for time spent
MAX_RECT_SIZE = 40

# how often to print a status message
PRINT_EVERY_N_ROUNDS = 10

# how often to write an output file
SAVE_EVERY_N_ROUNDS = 100

def read_image(filename):
    # read image file;
    # generate: one pixel row (tuple of tuples of ints) per call
    with open(filename, "rb") as handle:
        handle.seek(0)
        image = Image.open(handle)
        if image.width < MAX_RECT_SIZE:
            sys.exit(f"Must be at least {MAX_RECT_SIZE} pixels wide.")
        if image.height < MAX_RECT_SIZE:
            sys.exit(f"Must be at least {MAX_RECT_SIZE} pixels tall.")
        if image.mode in ("L", "P"):
            image = image.convert("RGB")
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

def get_random_rect(imageWidth, imageHeight):
    # get the properties of a random rectangle
    # return: (dimensions, colors); that is,
    #         ((x, y, width, height), (red, green, blue))
    width  = randrange(1, MAX_RECT_SIZE + 1)
    height = randrange(1, MAX_RECT_SIZE + 1)
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
    # parse arguments
    if len(sys.argv) != 3:
        sys.exit("Arguments: INPUT_FILE OUTPUT_FILE_PREFIX (e.g. in.png rect)")
    (inputFile, outputFilePrefix) = sys.argv[1:3]
    if not os.path.isfile(inputFile):
        sys.exit("Input file not found.")
    if outputFilePrefix == "":
        sys.exit("Output file prefix must not be empty.")

    print("Reading image...")
    # tuple of tuples of tuples of ints
    origImage = tuple(read_image(inputFile))
    imageHeight = len(origImage)
    imageWidth  = len(origImage[0])

    # create canvas filled with average color of original image:
    # list of lists of tuples of ints
    origAverageColor = get_average_color(origImage, imageWidth, imageHeight)
    newImage = [
        [origAverageColor for x in range(imageWidth)]
        for y in range(imageHeight)
    ]

    round_ = 1
    initialDiff = get_image_diff(origImage, newImage)
    currentDiff = initialDiff
    startTime = time.time()

    while True:
        # get a random rectangle that would make the current image less
        # different from the target image
        while True:
            (dimensions, color) = get_random_rect(imageWidth, imageHeight)
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

        # update difference to original image
        currentDiff -= oldRectDiff - newRectDiff

        # print status every n rounds
        if round_ % PRINT_EVERY_N_ROUNDS == 0:
            print(
                "Rectangles: {}; error: {:.1f}% of blank canvas; time "
                "elapsed: {:.1f} s".format(
                    round_,
                    currentDiff * 100 / initialDiff,
                    time.time() - startTime
                )
            )

        # save image every n rounds
        if round_ % SAVE_EVERY_N_ROUNDS == 0:
            filename = f"{outputFilePrefix}{round_:04}.png"
            if os.path.exists(filename):
                print(
                    f"Warning: {filename} already exists, not overwriting",
                    file=sys.stderr
                )
            else:
                print(f"Writing {filename}")
                write_image(newImage, imageWidth, imageHeight, filename)

        round_ += 1

main()
