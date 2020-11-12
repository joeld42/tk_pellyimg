# TK PellyImg: Pelican Image Processing Plugin

On demand image processing and thumbnailing for the Pelican static site generator.

TkPellyImg adds image-processing features that you can apply during static site generation. For example,
it can generate thumbnails from images, or add badges or text. It is customizable so you can add your 
own custom image processing operations using [Python PIL](https://pillow.readthedocs.io/en/stable/) code.

Using TkPellyImg
------------

To apply TkPellyImg, just add the operations as a suffix to any image path.

For example, this will take a couple high resolution images and generate small, square 200px thumbnails:

```
![Sandwich](/images/sandwich.jpg@fit(200))
![Cake](/images/cake.jpg@fit(200))
```

![Sandwich](https://joeld42.github.io/tk_pellyimg/images/sandwich_FSx.jpg)
![Cake](https://joeld42.github.io/tk_pellyimg/images/cake_BO7.jpg)

For more examples and details, see the [Documentation](https://joeld42.github.io/tk_pellyimg/pages/docs.html)
