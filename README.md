# hreflang-chcker
Has a few options on how to check your sites hreflang
works purely on the live site.


Packages to install:
just install all the imports at the top of the script**
runs on python 3.x

Just added some sitemap checking functionality, have not acutally come accross much that does this so maybe useful for some people. It struggles with massive sites since i have not done any real optimisation, i think the biggest that worked for me was about 50k pages:

works with the 3 classes.

1. page_check: takes a URL, checks that the URL has correct hreflang (also checks the alternates pointed to).
2. crawler: takes a URL, starts a free crawler from there which will check all the pages it finds (also checks the alternates pointed to).
3. sitemap: takes the homepage, downloads and parses all the sitemaps and runs the various checks on them as it goes.

example usage of the crawler (checks on page hreflang):

- innit the crawler
```
a = a.crawler("https://www.example.com")

```
- get the homepage from there to get the robots link... ugly i know, but it works

```
roboter = a.home_page + "robots.txt"

```
- get robots parser going
```
rp = robotparser.RobotFileParser()
rp.set_url(roboter)
rp.read()
```
- start the crawl

```
a.rec_crawl()

```

^^This will start the free crawl running, doing the checks as it goes and loggin the results as it goes.

example usage of the sitemap checker (checks sitemap hreflang):

- innit the whole jobby
```
a = sitemap("https://www.example.com")
```
- this part does everything else from downloading all the sitemaps to running all the checks and storing them in a dictionary
```
data = a.check_data()
```

