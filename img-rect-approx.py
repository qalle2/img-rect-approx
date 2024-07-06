# approximate an image by drawing rectangles at random;
# continue forever and save an image every n rounds

import os, sys
from copy import deepcopy
from itertools import chain
from random import randrange
from PIL import Image

# maximum width & height of rectangles;
# smaller = initially slower but later faster
MAX_RECT_SIZE = 50

# how often to write an output file
SAVE_EVERY_N_ROUNDS = 10

def read_image(filename):
    # generate pixel rows (tuple of tuples of ints)
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

def get_average_color(pixels, imageWidth, imageHeight):
    # get average color (tuple of ints);
    # pixels: tuple of tuples of tuples of ints
    componentSums = [0 for i in range(3)]
    for pixel in chain.from_iterable(pixels):
        for i in range(3):
            componentSums[i] += pixel[i]
    return tuple(
        round(s / (imageWidth * imageHeight)) for s in componentSums
    )

def get_color_diff(rgb1, rgb2):
    # get difference of two (red, green, blue) colors
    return sum(
        weight * abs(rgb1[i] - rgb2[i]) for (i, weight) in enumerate((2, 3, 1))
    )

def get_image_diff(image1, image2):
    # image1, image2: tuple of tuples of tuples of ints
    return sum(
        sum(get_color_diff(pix1, pix2) for (pix1, pix2) in zip(row1, row2))
        for (row1, row2) in zip(image1, image2)
    )

def get_random_rect(imageWidth, imageHeight):
    # get properties of a random rectangle
    width  = randrange(1, MAX_RECT_SIZE + 1)
    height = randrange(1, MAX_RECT_SIZE + 1)
    x      = randrange(imageWidth  - width + 1)
    y      = randrange(imageHeight - height + 1)
    red    = randrange(256)
    green  = randrange(256)
    blue   = randrange(256)
    return (x, y, width, height, red, green, blue)

def apply_rect_to_image(
    oldPixels, xStart, yStart, width, height, red, green, blue
):
    # draw rectangle on pixel data, return new pixel data
    newPixels = deepcopy(oldPixels)
    newSlice = width * [(red, green, blue)]
    for y in range(yStart, yStart + height):
        newPixels[y][xStart:xStart+width] = newSlice
    return newPixels

def write_image(pixels, imageWidth, imageHeight, filename):
    # write PNG; pixels: tuple of tuples of tuples of ints

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
    origPixels = tuple(read_image(inputFile))
    imageHeight = len(origPixels)
    imageWidth  = len(origPixels[0])

    # create canvas filled with average color of original image
    origAverageColor = get_average_color(origPixels, imageWidth, imageHeight)
    newPixels = [
        [origAverageColor for x in range(imageWidth)]
        for y in range(imageHeight)
    ]

    initialDiff = get_image_diff(origPixels, newPixels)
    print("Initial difference:", initialDiff)

    round_ = 1
    prevDiff = initialDiff
    while True:
        # get a random rectangle that makes the current image less different
        # from the target image
        while True:
            rect = get_random_rect(imageWidth, imageHeight)
            candidate = apply_rect_to_image(newPixels, *rect)
            diff = get_image_diff(origPixels, candidate)
            if diff < prevDiff:
                break

        # apply the rectangle for real
        newPixels = deepcopy(candidate)
        print(
            "Difference after rectangle {}: {} ({:.1f}% of initial)".format(
                round_, diff, diff * 100 / initialDiff
            )
        )

        # save image every now and then
        if round_ % SAVE_EVERY_N_ROUNDS == 0:
            filename = f"{outputFilePrefix}{round_:03}.png"
            if os.path.exists(filename):
                sys.exit(f"File {filename} already exists; quitting.")
            print(f"Writing {filename}...")
            write_image(newPixels, imageWidth, imageHeight, filename)
        round_ += 1

        prevDiff = diff

main()
