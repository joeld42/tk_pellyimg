import os, sys
import re
import logging
import hashlib
import base64

import pelican

from bs4 import BeautifulSoup

from PIL import Image

log = logging.getLogger(__name__)

# NOCHECKIN: turn off the log limit bullshit filter
log.disable_filter()

imgInfo = {}
imgCmdTable = {}

_uniqHash = {} # short hash -> full hash

reImgCommand = re.compile( r"@\s*(?P<cmd>[A-Za-z0-9]+)\s*\((?P<args>[A-Za-z0-9\,\.\s\#\-\+]*)\)?" )



def RegisterImgCommand( cmdName, cmdFunc ):
    log.debug("Will register command %s", cmdName )

    if cmdName in imgCmdTable:
        log.warn( "TkPellyImg: Command %s already registered, will be replaced.", cmdName )

    imgCmdTable[ cmdName ] = cmdFunc

def imgCmdResize( srcImg, imgArgs ):

    # if the user only specifies one value, assume it's the width
    print ("imgArgs is ", imgArgs )
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
    resultImg = srcImg.resize( targetSize )

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
        log.debug("short hash is %s, procSrc %s", self.shortHash, self.processedSrc )

    def _tagImage( self, imgSrc, cmdList ):
        # Makes processed image uniquely idenfitiable from command list

        imgHashSrc = imgSrc
        for cmdArgs in cmdList:
            log.debug( "CmdArgs is %s", cmdArgs )
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




def test(sender):
    log.debug("%s initialized !!", sender)

def init_img_gen( sender ):
    # Reset the image info
    imgInfo = {}


def process_generator_imgs( gen ):

    if gen._content is None:
        return

    content = instance._content
    log.debug ('TKPELLYIMG: Content is %d (%s)', len(content), content )
    soup = BeautifulSoup( content, 'html.parser')

    for img in soup( ['img', 'object']):
        log.debug('TKPELLYIMG Image Src: %s', img['src'])



    sys.exit(1)


def _parseImgProcessCmds( imgsrc ):

    suffix = imgsrc.find('@')
    if suffix < 0:
        # No image commands, just return the source tag unmodified
        return imgsrc, []
    else:
        imgName = imgsrc[:suffix]

        cmdList = []
        for m in reImgCommand.finditer( imgsrc.lower() ):
            cmd = m.group( 'cmd' )
            args = list( map( lambda x: x.strip(), m.group( 'args' ).split(',') ) )
            cmdList.append( (cmd, args) )

        return imgName, cmdList




def gather_imgs( contentpath, context ):
    # Add our info to context
    #imgInfo['count'] = imgInfo.get( 'count', 0 ) + 1
    #log.debug( 'TKPELLYIMG, contentpath %s, count is %d', contentpath, imgInfo['count'])
    fileExt = os.path.splitext( contentpath )[-1]
    log.debug( 'TKPELLYIMG, contentpath %s, fileExt is %s', contentpath, fileExt )

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
        log.debug('TKPELLYIMG Image Src: %s', img['src'])
        strippedSrc, cmdList = _parseImgProcessCmds( img['src'] )

        # Do we need to modify this tag?
        if len(cmdList):
            # There are some commands tagged on this img src, make an ImgProcessStack for it and
            # store it to evaluate later
            log.debug("Will Process %s (%s)", strippedSrc, cmdList )
            #taggedImageName = _tagImage( strippedSrc, cmdList )
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
        # Dest file does not exist
        return True

    destmtime = os.path.getmtime( destFile )
    srcmtime = os.path.getmtime( srcFile )

    if srcmtime >= destmtime:
        return True

    # file is up to date
    return False

def generate_imgs( generator ):

    log.debug( 'TKPELLYIMG: in generate_imgs.' )

    outPath = generator.settings["OUTPUT_PATH"]
    #dbg_dump_settings( generator )

    c = 0
    for imgProc in list(imgInfo.values()):
        log.debug( 'img: %s (use count %d), %d commands: (%s)',
                   imgProc.processedSrc, imgProc.usageCount, len( imgProc.cmdList ), str(imgProc.cmdList) )

        srcImgPath = outPath + imgProc.imgSrc
        destImgPath = outPath + imgProc.processedSrc

        if not file_needs_update( srcImgPath, destImgPath ):
            log.info("TkPellyImg: %s is up to date.", imgProc.processedSrc )
        else:
            currImg = Image.open( srcImgPath )
            for imgCmd in imgProc.cmdList:

                print('  CMDz: %s' % str(imgCmd))
                cmdFunc = imgCmdTable.get( imgCmd[0], None )
                if cmdFunc is None:
                    log.warn( "TkPellyImg: No command registered '%s'.", imgCmd[0] )
                else:
                    result = cmdFunc( currImg, imgCmd[1] )
                    currImg = result

            log.info("TkPellyImg: Writing processed Image: '%s'", imgProc.processedSrc )
            currImg.save( destImgPath )


    log.debug("done")

def process_articles( generator, content ):

    for art in generator.articles:
        log.debug("Art: %s (%s)", art, dir(content) )

    sys.exit(1)

def register_builtin_commands():

    # Register our built-in image commands
    RegisterImgCommand( "resize", imgCmdResize )

def register():
    pelican.signals.initialized.connect(init_img_gen)
    pelican.signals.content_written.connect( gather_imgs )
    pelican.signals.finalized.connect( generate_imgs )
    register_builtin_commands()