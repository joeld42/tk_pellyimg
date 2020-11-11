#!/usr/bin/env python
# -*- coding: utf-8 -*- #

AUTHOR = 'TkPellyImg'
SITENAME = 'Documentation'
SITEURL = ''

PATH = 'content'

TIMEZONE = 'America/Los_Angeles'

DEFAULT_LANG = 'en'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

DEFAULT_PAGINATION = False

MARKDOWN = {
    'extension_configs': {
        'markdown.extensions.codehilite': {'css_class': 'highlight', 'guess_lang': False },
        'markdown.extensions.extra': {},
        'markdown.extensions.meta': {},
    },
    'output_format': 'html5',
}
# Uncomment following line if you want document-relative URLs when developing
RELATIVE_URLS = True

# Supress most of the autogeneraed pages since this is just docs
YEAR_ARCHIVE_SAVE_AS = ''
MONTH_ARCHIVE_SAVE_AS = ''
CATEGORY_SAVE_AS = ''
ARCHIVES_SAVE_AS = ''
AUTHORS_SAVE_AS = ''
CATEGORIES_SAVE_AS = ''
TAGS_SAVE_AS = ''

# Settings for TKPELLYIMG image processor
TKPELLYIMG_PLACEHOLDER_FONT = "theme/fonts/Yanone_Kaffeesatz_400.ttf"
TKPELLYIMG_PLACEHOLDER_FONTSIZE = 24

# Example custom actions for TKPELLYIMG
import os
import pelican.plugins.tkpellyimg as tkimg
from PIL import Image, ImageFilter, ImageColor, ImageDraw, ImageFont
def img_new_badge( cfg, srcImage, imgArgs ):	
	badgeImg = Image.open( os.path.join( cfg["OUTPUT_PATH"], "images", "new_badge.png"))
	srcImage.paste( badgeImg, (0,0), badgeImg )
	return srcImage

def img_caption( cfg, srcImage, imgArgs ):
	captionText = imgArgs[0]
	captionColor = ImageColor.getrgb( imgArgs[1])
	draw = ImageDraw.Draw( srcImage )
	font = ImageFont.truetype( os.path.join( cfg["OUTPUT_PATH"], "theme/fonts/Yanone_Kaffeesatz_400.ttf" ), 30 )
	draw.rectangle( (0, srcImage.size[1]-40, srcImage.size[0], srcImage.size[1]), fill=(0,0,20))
	draw.text( (10, srcImage.size[1]-30), captionText, fill=captionColor, font=font )
	
	return srcImage


tkimg.RegisterImgCommand( "newbadge", img_new_badge )
tkimg.RegisterImgCommand( "caption", img_caption )