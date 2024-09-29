# approximate an image by drawing rectangles at random

import os, sys, time
from random import randrange
try:
    from PIL import Image, ImageDraw
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

def parse_arguments():
    # parse command line arguments

    if not 3 <= len(sys.argv) <= 5:
        sys.exit(
            "Arguments: inputFile outputFile [numberOfRectangles "
            "[maxRectangleSize]] ; see README.md for details"
        )
    (inputFile, outputFile) = sys.argv[1:3]
    rectCount   = sys.argv[3] if len(sys.argv) >= 4 else "1000"
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

def get_average_color(image):
    # get the average color (red, green, blue) of an image object
    pixelCount = image.width * image.height
    return tuple(
        round(sum(color[i] for color in image.getdata()) / pixelCount)
        for i in range(3)
    )

def get_color_diff(color1, color2):
    # get difference between two colors (red, green, blue)
    return (
          2 * abs(color1[0] - color2[0])
        + 3 * abs(color1[1] - color2[1])
        +     abs(color1[2] - color2[2])
    )

def get_image_difference(image1, image2):
    # get difference between two images
    return sum(
        get_color_diff(color1, color2) for (color1, color2)
        in zip(image1.getdata(), image2.getdata())
    )

def get_image_and_color_difference(image, color):
    # get difference between an image and a color (red, green, blue);
    # equivalent to difference of two images as if one of them was filled with
    # the color
    return sum(get_color_diff(pix, color) for pix in image.getdata())

def get_new_image(origImage, args):
    # origImage: original Pillow image
    # args:      command line arguments (dict)
    # return:    new Pillow image

    # validate original image
    if origImage.width < args["maxRectSize"]:
        sys.exit("Image is not wide enough for maximum rectangle size.")
    if origImage.height < args["maxRectSize"]:
        sys.exit("Image is not tall enough for maximum rectangle size.")

    # convert original image into RGB
    if origImage.mode in ("L", "P"):
        origImage = origImage.convert("RGB")
    elif origImage.mode != "RGB":
        sys.exit("Unrecognized pixel format (try removing the alpha channel).")

    # create image filled with average color of original image
    origAvgColor = get_average_color(origImage)
    newImage = Image.new(
        "RGB", (origImage.width, origImage.height), origAvgColor
    )
    newImageDrawObj = ImageDraw.Draw(newImage)

    initialImageDiff = get_image_difference(origImage, newImage)
    currentImageDiff = initialImageDiff

    # paint specified number of rectangles on new image
    for round_ in range(1, args["rectCount"] + 1):
        while True:
            # get a random rectangle
            width  = randrange(1, args["maxRectSize"] + 1)
            height = randrange(1, args["maxRectSize"] + 1)
            x      = randrange(origImage.width  - width  + 1)
            y      = randrange(origImage.height - height + 1)
            color  = tuple(randrange(256) for i in range(3))
            # if it would make the current image less different from the target
            # image, proceed with it, otherwise get another rectangle
            origRect = origImage.crop((x, y, x + width, y + height))
            currRect =  newImage.crop((x, y, x + width, y + height))
            oldRectDiff = get_image_difference(origRect, currRect)
            candidateRectDiff = get_image_and_color_difference(origRect, color)
            if candidateRectDiff < oldRectDiff:
                break
        # actually paint the new rectangle
        newImageDrawObj.rectangle(
            (x, y, x + width - 1, y + height - 1), fill=color, width=0
        )
        # update difference from original image
        currentImageDiff -= oldRectDiff - candidateRectDiff
        # print status every n rounds
        if round_ % PRINT_EVERY_N_ROUNDS == 0:
            print(
                "{:6} rectangle(s) painted. Canvas differs from original "
                "image {:4.1f}% less than blank canvas did.".format(
                    round_, (1 - currentImageDiff / initialImageDiff) * 100
                )
            )

    return newImage

def main():
    startTime = time.time()
    args = parse_arguments()

    try:
        with open(args["inputFile"], "rb") as inHandle:
            inHandle.seek(0)
            origImage = Image.open(inHandle)
            newImage = get_new_image(origImage, args)
            with open(args["outputFile"], "wb") as outHandle:
                outHandle.seek(0)
                newImage.save(outHandle, "png")
    except OSError:
        sys.exit("Error reading/writing files.")

    print("Time elapsed: {:.1f} second(s).".format(time.time() - startTime))

main()
