# hreflang-chcker
Has a few options on how to check your sites hreflang
works purely on the live site.


Packages to install:
	just install all the imports at the top of the script**

runs on python 3.x

Just added somre sitemap checking functionality, only checks the basic things I could think of for now:
	self reference
	points to url included in sitemap
	has return tag
	return tag has same code/targeting as the self reference

works with the 3 classes.
	page_check which accepts any url and can run some basic checks on that url, including loading the alternates pointed to and ensure they are also valid
	crawler which also accepts any url form the site, whith this you can basically start it going and will follow links on the site checking them as it goes along
		Both the above ^^ require you to rp (robot parser globally), used in the checks that pages are indexable
	The sitemap class loads up all your sitemaps that are pointed to through robots, including sitemaps pointed through sitemap indexes, it then performs some checks on those (this one does not hit any of your live pages)


example usage:

# innit the crawler
a = a.crawler("https://www.example.com")
# get the homepage from there to get the robots link
roboter = a.home_page + "robots.txt"
# get robots parser going
rp = robotparser.RobotFileParser()
rp.set_url(roboter)
rp.read()
# start the crawl
a.rec_crawl()


# this will start the free crawl running, doing the checks as it goes.


There is a compiled dist that can be used by people that don't want to code or install anything, this is limited to just the crawler which checks the live site onpage tags. and its pretty wonky, i fixed a lot of the issues in it when switching to a class based check which has much more functionality.
