import os, sys, shutil
from bs4 import BeautifulSoup

SRC_DIR = "./output/"
DEST_DIR = "../docs/"

# This gets prepended to all the image file paths so that it works on
# github pages
SITE_PREFIX = "tk_pellyimg"

def fixLink( origLink ):
    if origLink.startswith("/"):
        return "/" + SITE_PREFIX + origLink
    else:
        return origLink


for (root,dirs,files) in os.walk( SRC_DIR, topdown=True):

    #print (root)
    #print (files)

    destRoot = root.replace( SRC_DIR, DEST_DIR )
    for srcFile in files:
        srcPath = os.path.join( root, srcFile )
        destPath = os.path.join( destRoot, srcFile )

        # Create dest dir if needed
        destDir = os.path.split( destPath )[0]
        os.makedirs( destDir, exist_ok=True )

        fileExt = os.path.splitext( destPath )[-1]
        modifiedHtml = None
        if fileExt == '.html':
            print( srcPath, "Is html, will process..")
            with open(srcPath, 'r') as htmlfile:
                html = htmlfile.read()

                # Parse the html and look for images
                didProcessImageTag = False
                soup = BeautifulSoup(html, 'html.parser')
                for img in soup(['img', 'object']):
                    img['src'] = fixLink( str(img['src']))

                for elem in soup(['link', 'a']):
                    elem['href'] = fixLink(str(elem['href']))

                modifiedHtml = soup.decode()

            if modifiedHtml:
                with open(destPath, 'w') as htmlfile:
                    htmlfile.write(modifiedHtml)
        else:
            # Just copy the file
            shutil.copyfile( srcPath, destPath )
