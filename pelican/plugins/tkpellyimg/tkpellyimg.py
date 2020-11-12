import os, sys
import re
import logging
import hashlib
import base64
import colorsys

import pelican

from bs4 import BeautifulSoup

from PIL import Image, ImageFilter, ImageColor, ImageDraw, ImageFont

log = logging.getLogger(__name__)

# Uncomment this to turn off the misleanding log de-dupe filter
# You can also use --logs-dedup-min-level
# log.disable_filter()

imgInfo = {}
imgCmdTable = {}

_uniqHash = {} # short hash -> full hash

reImgCommand = re.compile( r"@\s*(?P<cmd>[A-Za-z0-9]+)\s*\((?P<args>[A-Za-z0-9\,\.\s\#\-\+\%\[\]]*)\)?" )

kCfgPlaceholderFont = 'TKPELLYIMG_PLACEHOLDER_FONT'
kCfgPlaceholderFontsize = 'TKPELLYIMG_PLACEHOLDER_FONTSIZE'

def RegisterImgCommand( cmdName, cmdFunc ):
    if cmdName in imgCmdTable:
        log.warn( "TkPellyImg: Command %s already registered, will be replaced.", cmdName )

    log.info("Registed command '%s'", cmdName )
    imgCmdTable[ cmdName ] = cmdFunc

def imgCmdResize( cfg, srcImg, imgArgs ):

    # if the user only specifies one value, assume it's the width
    targetSize = tuple( map( lambda x: int(x), (imgArgs + [ 0 ])[:2] ) )

    # If both width/height are 0, do nothing
    if targetSize[0] == 0 and targetSize[1] == 0:
        return srcImg

    # If only one of targetsize is 0, use aspect of original image
    aspect = float(srcImg.size[0]) / float(srcImg.size[1])
    if targetSize[0] == 0:
        targetSize = ( int(targetSize[1] * aspect), targetSize[1] )
    elif targetSize[1] == 0:
        targetSize = ( targetSize[0], int(targetSize[0] * (1.0/aspect) ) )

    log.debug( "Will resize img to %s", str( targetSize ) )
    resultImg = srcImg.resize( targetSize, Image.ANTIALIAS )

    return resultImg

def imgCmdFit( cfg, srcImg, imgArgs ):

    # if the user only specifies one value, assume they want a square
    targetSize = tuple( map( lambda x: int(x), (imgArgs + [ 0 ])[:2] ) )
    if targetSize[1] == 0:
        targetSize = ( targetSize[0], targetSize[0] )

    # Crop the largest size of the source image to fit
    srcAspect = float(srcImg.size[0]) / float(srcImg.size[1])
    targetAspect = float(targetSize[0]) / float(targetSize[1])
    if srcAspect >= targetAspect:
        # Crop horizontally
        cropWidth = int(targetAspect * srcImg.size[1])
        cropOffs = int( (srcImg.size[0] - cropWidth) / 2.0)
        cropRect = (cropOffs, 0, srcImg.size[0] - cropOffs, srcImg.size[1] )
    else:
        # Crop Vertically
        cropHeight = int(srcImg.size[0] / targetAspect)
        cropOffs = int((srcImg.size[1] - cropHeight) / 2.0)
        cropRect = (0, cropOffs, srcImg.size[0], srcImg.size[1] - cropOffs )

    cropImg = srcImg.crop( cropRect ).resize( targetSize, Image.ANTIALIAS )
    return cropImg

def imgCmdBlur( cfg, srcImg, imgArgs ):

    blurSize = int(imgArgs[0])
    resultImg = srcImg.filter( ImageFilter.GaussianBlur(blurSize) )

    return resultImg

def imgCmdPlaceholder( cfg, srcImg, imgArgs ):

    # srcImg is ignored.
    targetWidth = int(imgArgs[0])
    if len(imgArgs) > 1:
        targetHeight = int(imgArgs[1])
    else:
        targetHeight = targetWidth

    # Placeholder text, default to image size
    if len(imgArgs) > 2:
        placeholderText = imgArgs[2]
    else:
        placeholderText = "%dx%d" % (targetWidth, targetHeight)

    if len(imgArgs) > 3:
        targetColor = ImageColor.getrgb( imgArgs[3] )
    else:
        # Default, use a middle grey
        targetColor = ( 100, 100, 100 )

    if len(imgArgs) > 4:
        lineColor = ImageColor.getrgb( imgArgs[4])
    else:
        # By default, generate a close tint for the text
        hsv = colorsys.rgb_to_hsv( float(targetColor[0]) / 255.0, float(targetColor[1]) / 255.0, float(targetColor[2]) / 255.0 )
        if (hsv[2] < 0.5):
            lineHsv = ( hsv[0], hsv[1], hsv[2] + 0.25 )
        else:
            lineHsv = (hsv[0], hsv[1], hsv[2] - 0.25)

        lineColor = tuple(map( lambda x: int( x * 255.0), colorsys.hsv_to_rgb( *lineHsv ) ))

    resultImg = Image.new( "RGB", (targetWidth, targetHeight), targetColor )

    draw = ImageDraw.Draw( resultImg )
    draw.line( (0, 0, targetWidth, targetHeight), fill=lineColor )
    draw.line( (0, targetHeight, targetWidth, 0), fill=lineColor )
    draw.rectangle( (0, 0, targetWidth-1, targetHeight-1), outline=lineColor, width=2 )

    # Get font from settings
    if kCfgPlaceholderFont in cfg:
        fontName = cfg[kCfgPlaceholderFont]
        fontSize = cfg.get( kCfgPlaceholderFontsize, 12 )
        font = ImageFont.truetype( os.path.join( cfg["OUTPUT_PATH"], fontName ), 36 )
    else:
        # No font specificed, use the tiny PIL default font
        font = draw.getfont()

    textSize = font.getsize( placeholderText )
    textPos = ( int( (targetWidth - textSize[0])/2.0), int( (targetHeight - textSize[1])/2.0) )
    draw.text( textPos, placeholderText, fill=lineColor, font = font )

    return resultImg

def imgCmdBlank( cfg, srcImg, imgArgs ):

    # srcImg is ignored.
    targetWidth = int(imgArgs[0])
    if len(imgArgs) > 1:
        targetHeight = int(imgArgs[1])
    else:
        targetHeight = targetWidth

    if len(imgArgs) > 2:
        targetColor = ImageColor.getrgb( imgArgs[2] )
    else:
        targetColor = (0,0,0)

    resultImg = Image.new( "RGB", (targetWidth, targetHeight), targetColor )
    return resultImg


class TkImgProcessStack:

    def __init__(self, imgSrc, cmdList ):
        self.imgSrc = imgSrc
        self.cmdList = cmdList
        self.imgHash = self._tagImage( imgSrc, cmdList )
        self.shortHash = self.makeShortHash( self.imgHash )
        self.usageCount = 0

        # Use the short hash to make the processed filename
        fn, ext = os.path.splitext( self.imgSrc )
        self.processedSrc = fn + "_" + self.shortHash + ext
        #log.debug("short hash is %s, procSrc %s", self.shortHash, self.processedSrc )

    def _tagImage( self, imgSrc, cmdList ):
        # Makes processed image uniquely idenfitiable from command list

        imgHashSrc = imgSrc
        for cmdArgs in cmdList:
            cmd, args = cmdArgs
            imgHashSrc += cmd
            for arg in args:
                imgHashSrc += "-" + str(arg)


        # This doesn't have to be a good hash since it's just used to uniqify the processed filename
        hashChars = "QZ".encode()
        imgHash = base64.b64encode( hashlib.md5( imgHashSrc.encode() ).digest(), hashChars ).decode('ascii')
        imgHash = imgHash.replace('=','X')

        return imgHash

    def makeShortHash( self, fullHash ):
        # Finds the shortest (at least 3) version of this hash among
        # ones we've seen
        hashLen = 3
        shortHash = fullHash[:hashLen]
        while (shortHash in _uniqHash) and (hashLen < len(fullHash)):
            hashLen += 1
            shortHash = fullHash[:hashLen]

        # Got a unique short hash (hopefully), store it
        _uniqHash[shortHash] = fullHash
        return shortHash


def init_img_gen( sender ):
    # Reset the image info
    imgInfo = {}

def _parseImgProcessCmds( imgsrc ):

    suffix = imgsrc.find('@')
    if suffix < 0:
        # No image commands, just return the source tag unmodified
        return imgsrc, []
    else:
        imgName = imgsrc[:suffix]

        cmdList = []
        for m in reImgCommand.finditer( imgsrc ):
            cmd = m.group( 'cmd' )
            args = list( map( lambda x: x.strip(), m.group( 'args' ).split(',') ) )
            cmdList.append( (cmd, args) )

        return imgName, cmdList




def gather_imgs( contentpath, context ):
    # Add our info to context
    fileExt = os.path.splitext( contentpath )[-1]

    # Make sure it's a type of content that we care about
    if not fileExt.lower() in [ '.htm', '.html']:
        return

    # Content should exist because this gets called right after it's written but
    # check just in case
    if not os.path.exists( contentpath ):
        log.warning( 'Content file %s missing, skipping TkPellyImg scan.')
        return

    # Read the original html file
    with open( contentpath, 'r') as htmlfile:
        html = htmlfile.read()

    # Parse the html and look for images
    didProcessImageTag = False
    soup = BeautifulSoup( html, 'html.parser')
    for img in soup( ['img', 'object']):
        strippedSrc, cmdList = _parseImgProcessCmds( img['src'] )

        # Do we need to modify this tag?
        if len(cmdList):
            # There are some commands tagged on this img src, make an ImgProcessStack for it and
            # store it to evaluate later
            imgCmd = TkImgProcessStack( strippedSrc, cmdList )
            didProcessImageTag = True

            # Did we already process an identical cmd stack?
            if imgCmd.imgHash in imgInfo:
                # Use the existing one instead
                imgCmd = imgInfo[imgCmd.imgHash]
            else:
                # Add to our list
                imgInfo[imgCmd.imgHash] = imgCmd

            img['src'] = imgCmd.processedSrc
            imgCmd.usageCount += 1


    # Write out the modified HTML
    if (didProcessImageTag):
        log.debug( "TKPELLYIMG: Writing out updated html for %s", contentpath )
        modifiedHtml = soup.decode()
        with open( contentpath, 'w') as htmlfile:
            htmlfile.write( modifiedHtml )


def dbg_dump_settings( generator ):
    settings = list(generator.settings.keys())
    settings.sort()
    for k in settings:
        print("%40s - %s" % (k, str(generator.settings[k])))

def file_needs_update( srcFile, destFile ):

    if not os.path.exists( destFile ):
        # dest does not exist
        return True

    destmtime = os.path.getmtime( destFile )

    if not os.path.exists(srcFile):
        # No source file exists, e.g. the image is generated.
        return False

    srcmtime = os.path.getmtime( srcFile )

    if srcmtime >= destmtime:
        return True

    # file is up to date
    return False

def generate_imgs( generator ):

    log.debug( 'TKPELLYIMG: in generate_imgs.' )

    outPath = generator.settings["OUTPUT_PATH"]

    for imgProc in list(imgInfo.values()):
        log.debug( 'img: %s (use count %d), %d commands: (%s)',
                   imgProc.processedSrc, imgProc.usageCount, len( imgProc.cmdList ), str(imgProc.cmdList) )

        srcImgPath = outPath + imgProc.imgSrc
        destImgPath = outPath + imgProc.processedSrc

        if not file_needs_update( srcImgPath, destImgPath ):
            log.info("TkPellyImg: %s is up to date.", imgProc.processedSrc )
        else:
            if os.path.exists( srcImgPath ):
                currImg = Image.open( srcImgPath )
            else:
                # If src image doesnt exist, use a 10x10 transparent image
                currImg = Image.new( "RGB", (10,10), (0,0,0))

            for imgCmd in imgProc.cmdList:
                cmdFunc = imgCmdTable.get( imgCmd[0], None )
                if cmdFunc is None:
                    log.warn( "TkPellyImg: No command registered '%s'.", imgCmd[0] )
                else:
                    result = cmdFunc( generator.settings, currImg, imgCmd[1] )
                    currImg = result

            log.info("TkPellyImg: Writing processed Image: '%s'", imgProc.processedSrc )
            currImg.save( destImgPath )

def register_builtin_commands():

    # Register our built-in image commands
    RegisterImgCommand( "resize", imgCmdResize )
    RegisterImgCommand( "fit", imgCmdFit)
    RegisterImgCommand( "blur", imgCmdBlur)
    RegisterImgCommand( "blank", imgCmdBlank)
    RegisterImgCommand( "placeholder", imgCmdPlaceholder)

def register():
    pelican.signals.initialized.connect(init_img_gen)
    pelican.signals.content_written.connect( gather_imgs )
    pelican.signals.finalized.connect( generate_imgs )
    register_builtin_commands()
