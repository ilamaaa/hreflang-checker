import requests
from bs4 import BeautifulSoup
import urllib.robotparser as robotparser
import urllib.parse
import time
import re
import validators
import gzip


class page_check:
    # get all the page data, only want to do this once so stuck it in the init to have the data throughout
    def __init__(self, page):
        self.page = page
        self.parsed_uri = urllib.parse.urlparse(page)
        self.home_page = '{uri.scheme}://{uri.netloc}/'.format(uri=self.parsed_uri)
        self.headers = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
        self.r = requests.get(self.page,allow_redirects=False, headers=self.headers)
        self.soup = BeautifulSoup(self.r.content, "lxml")

    # returns true and 200 if 200, otherwise returns false and the status code
    def check_status(self):
        if self.r.status_code == 200:
            return True, self.r.status_code
        else:
            return False, self.r.status_code

    # returns true if none or the same as the page, returns false and the canonical otherwise
    def check_canonical(self):
        canonical_element = self.soup.find("link", {"rel": "canonical"}) if self.soup.find("link", {"rel": "canonical"}) is not None else False
        if canonical_element is not False:
            canonical_link = canonical_element["href"]
            if canonical_link == self.page:
                return True, canonical_link
            else:
                return False, canonical_link
        else:
            return True, "No Canonical"

    # ensures the page is not blocked by robots returns Bool and directive
    def check_robots(self):
        robots_element = self.soup.find("meta", {"name": "robots"}) if self.soup.find("meta", {"name": "robots"}) is not None else False
        if robots_element is not False:
            robot_directive = robots_element["content"]
            blocks = ["no index", "noindex"]
            if any(x in robot_directive.lower() for x in blocks):
                return False, robot_directive
            else:
                return True, robot_directive
        else:
            return True, "No Robots"

    # ensures the page is not blocked by robots txt, is a little awkward cause the library is initialized globally to
    # avoid having to hit again for each page, hopefully will get a better solution later
    def check_txt(self):
        if rp.can_fetch("*", self.page):
            return True, "Not txt Blocked"
        else:
            return False, "txt Blocked"

    # calls the previous few functions to return a simple is it indexable or not
    def indexable(self):
        status = self.check_status()
        canonical = self.check_canonical()
        robots = self.check_robots()
        txt = self.check_txt()
        checks = [status, canonical, robots, txt]
        over = list(map(lambda x: x[0], checks))
        try:
            index = over.index(False)
            return checks[index]
        except ValueError:
            return True

    # takes a few links formats and returns an absolute, may have missed some formats, it should notify if so
    def validate_link(self, link):
        link_parts = urllib.parse.urlparse(link)
        if "#" in link:
            return False, "nope"
        elif self.parsed_uri.scheme == link_parts.scheme and self.parsed_uri.netloc == link_parts.netloc:
            return True, link
        elif link_parts.scheme == "" and link_parts.netloc == "" and link[0] == "/":
            return True, '{}://{}{}'.format(self.parsed_uri.scheme, self.parsed_uri.netloc, link)
        elif link_parts.scheme == "" and link_parts.netloc == "":
            return True, '{}://{}/{}'.format(self.parsed_uri.scheme, self.parsed_uri.netloc, link)
        elif link_parts.scheme == "" and link_parts.netloc == self.parsed_uri.netloc:
            return True, '{}:{}'.format(self.parsed_uri.scheme, link)
        elif link_parts.netloc is not None and link_parts.netloc != self.parsed_uri.netloc:
            return False, "nope"
        else:
            print("did not account for this one:" + link)
            return False, "nope"

    # grabs the links on the page, calls the validation on them so should only produce absolute links
    def get_links(self):
        links = []
        for link in self.soup.find_all("a"):
            try:
                checked_link = self.validate_link(link["href"].strip())
                if checked_link[0] and checked_link[1] not in links:
                    links.append(checked_link[1])
                else:
                    pass
            except:
                pass
        return list(set(links))

    # gets the hreflang data from a page
    def get_hreflang(self):
        hreflang = []
        for tag in self.soup.find_all("link", {"hreflang": re.compile(r".*")}):
            try:
                hreflang.append((tag["hreflang"], tag["href"]))
            except:
                pass
        return list(map(lambda x: x[1], hreflang)), list(map(lambda x: x[0], hreflang))

    # checks the hreflang on a page includes a self referring tag
    def check_self(self):
        links, targets = self.get_hreflang()
        if self.page in links:
            return True
        else:
            return False

    # create a new instance for each of the alts (yea recursion biatch)
    def create_alt_instances(self):
        links, targets = self.get_hreflang()
        alt_instances = {"tar":[], "instance":[]}
        if len(targets) == 0:
            print("No Tags on: " + self.page)
        else:
            for iter, target in enumerate(targets):
                link = links[iter]
                if validators.url(link):
                    current = page_check(link)
                    alt_instances["tar"].append(target)
                    alt_instances["instance"].append(current)
                else:
                    print("badly formed link " + link)
            return alt_instances

    # cheks that alternate pages being pointed to also point back
    def check_return(self, alt_instances):
        wrong = []
        for iter, tar in enumerate(alt_instances["tar"]):
            current = alt_instances["instance"][iter]
            links, targets = current.get_hreflang()
            if self.page in links:
                pass
            else:
                wrong.append(current.page)
        if len(wrong) == 0:
            print(self.page + " has all its return links")
        else:
            print(self.page + " missing return link from " + str(wrong))

    # ensure alts have self referring tags
    def check_alts_self(self, alt_instances):
        wrong = []
        for iter, tar in enumerate(alt_instances["tar"]):
            current = alt_instances["instance"][iter]
            if current.check_self():
                pass
            else:
                wrong.append(current.page)
        if len(wrong) == 0:
            print(self.page + " points to pages that all have their self references")
        else:
            print(self.page + " points to pages which are missing their self references" + str(wrong))

    # ensure pages being pointed to are indexable
    def check_alts_indexable(self, alt_instances):
        wrong = []
        for iter, tar in enumerate(alt_instances["tar"]):
            current = alt_instances["instance"][iter]
            holder = current.indexable()
            if holder == True:
                pass
            else:
                wrong.append((holder, current.page))
        if len(wrong) == 0:
            print(self.page + " points to only indexable pages")
        else:
            print(self.page + " points to pages which are not indexable " + str(wrong))

    # checks if alternate pages all use the same code as the page we are checking when pointing to it
    def check_targeting(self, alt_instances):
        wrong = []
        links, targets = self.get_hreflang()
        try:
            target = targets[links.index(self.page)]
            for iter, tar in enumerate(alt_instances["tar"]):
                current = alt_instances["instance"][iter]
                cur_links, cur_targets = current.get_hreflang()
                try:
                    cur_tar = cur_targets[cur_links.index(self.page)]
                    if cur_tar == target:
                        pass
                    else:
                        wrong.append((current.page, cur_tar))
                except ValueError:
                    pass
            if len(wrong) == 0:
                print(self.page + " has consistent targeting across its alts")
            else:
                print(self.page + " has pages pointing to it with the wrong targeting code " +str(wrong))
        except ValueError:
            pass

    # calls a few hreflang checking functions for the page we are on
    def validate_alts(self):
        alt_instances = self.create_alt_instances()
        if alt_instances is not None:
            self.check_return(alt_instances)
            self.check_alts_self(alt_instances)
            self.check_alts_indexable(alt_instances)
            self.check_targeting(alt_instances)

# the crawler class, initiating just sets the start page, and sorts the starter things out
class crawler:
    def __init__(self, page):
        self.current_page = page
        self.parsed_uri = urllib.parse.urlparse(page)
        self.home_page = '{uri.scheme}://{uri.netloc}/'.format(uri=self.parsed_uri)
        self.to_crawl = [page]
        self.crawled = []

    #  the recursive crawler, it calls the hreflang check module, so if you want a free crawl validation, this is what you need
    def rec_crawl(self):
        print(str(len(self.to_crawl)) + " pages in que and " + str(len(self.crawled)) + " done, now on: " + self.current_page)
        self.crawled.append(self.current_page)
        if validators.url(self.current_page):
            class_instance = page_check(self.current_page)
            indexer = class_instance.indexable()
            if indexer == True:
                class_instance.validate_alts()
                self.to_crawl = list(set(self.to_crawl + class_instance.get_links()))
                self.to_crawl = list(set(self.to_crawl) - set(self.crawled))
                time.sleep(1)
                if len(self.to_crawl) == 0:
                    print("All Done")
                else:
                    self.current_page = self.to_crawl[0]
                    self.rec_crawl()
            else:
                time.sleep(1)
                print(self.current_page + " is not indexable " + str(indexer))
                self.to_crawl = list(set(self.to_crawl) - set(self.crawled))
                if len(self.to_crawl) == 0:
                    print("All Done")
                else:
                    self.current_page = self.to_crawl[0]
                    self.rec_crawl()
        else:
            print("badly formed link " + self.current_page)

            if len(self.to_crawl) == 0:
                print("All Done")
            else:
                self.crawled.append(self.current_page)
                self.to_crawl = list(set(self.to_crawl) - set(self.crawled))
                self.current_page = self.to_crawl[0]
                self.rec_crawl()

# my attempt at hreflang is sitemap validation, this got much more complicated than anticipated
# init just takes a url, gets the robots and from there the sitemap location
class sitemap:
    def __init__(self, page):
        self.current_page = page
        self.parsed_uri = urllib.parse.urlparse(page)
        self.home_page = '{uri.scheme}://{uri.netloc}/'.format(uri=self.parsed_uri)
        self.roboter = self.home_page + "robots.txt"

    # get the sitemaps, this will only return what is pointed to in robots, if they are sitemap indexes then that is what is returned
    def check_robots_for_sitemap(self):
        sitemaps = []
        r = requests.get(self.roboter)
        lines = r.content.split(b"\n")
        for line in lines:
            if "Sitemap:" in line.decode("utf-8"):
                sitemaps.append(line.decode("utf-8").split(" ")[1].replace("\r", ""))
        if len(sitemaps) == 0:
            print("no sitemaps in the robots file")
            return False
        else:
            return sitemaps

    # this checks if the robots sitemaps are sitemap indexes and if so, parses them to get the actual sitemaps
    # it only checks on one level, so if you a sitemap index of sitemap indexes this gets wonky
    def get_sitemaps(self):
        sitemaps_now = self.check_robots_for_sitemap()
        sitemaps = []
        if sitemaps is not False:
            for sitemap in sitemaps_now:
                r = requests.get(sitemap)
                soup = BeautifulSoup(r.content, "lxml")
                if soup.find("sitemapindex"):
                    for loc in soup.find_all("loc"):
                        sitemaps.append(loc.text)
                else:
                    sitemaps.append(sitemap)
            return sitemaps
        else:
            print("no sitemaps in the robots file")
            return False

    # does the heavy lifting, grabs all sitemaps, parses them into a workable dictionary
    def get_data(self):
        sitemaps = self.get_sitemaps()
        if sitemaps is not False:
            data = {"urls":[]}
            for sitemap in sitemaps:
                print("downloading sitemap :" + sitemap)
                r = requests.get(sitemap)
                if "Content-Type" in r.headers and "gz" in r.headers["Content-Type"]:
                    content = gzip.decompress(r.content)
                    soup = BeautifulSoup(content, "lxml")
                    for url in soup.find_all("url"):
                        deet = {"url": url.find("loc").text, "alts": []}
                        for alt in url.find_all(attrs={"rel": "alternate"}):
                            alter = {"target": alt["hreflang"], "link": alt["href"]}
                            deet["alts"].append(alter)
                        data["urls"].append(deet)
                else:
                    soup = BeautifulSoup(r.content, "lxml")
                    for url in soup.find_all("url"):
                        deet = {"url": url.find("loc").text, "alts": []}
                        for alt in url.find_all(attrs={"rel": "alternate"}):
                            alter = {"target": alt["hreflang"], "link": alt["href"]}
                            deet["alts"].append(alter)
                        data["urls"].append(deet)
            return data
        else:
            print("no sitemaps in the robots file")
            return False

    # checks all sitemap urls with hreflang for a self reference
    def check_self_ref(self, url_element):
        url = url_element["url"]
        alts = url_element["alts"]
        links = list(map(lambda x: x["link"], alts))
        if url in links:
            print(url + " has self reference")
        else:
            print(url + " is missing self reference")
            return False

    #  checks that links pointed to in hreflang are also in the sitemap
    def check_link_in_map(self, url_element, data):
        alts = url_element["alts"]
        links = list(map(lambda x: x["link"], alts))
        check = []
        urls = list(map(lambda x: x["url"], data["urls"]))
        for link in links:
            if link in urls:
                print(link + " is in and has a corresponding url element")
            else:
                print(link + " is is pointed to but has to corresponding url element")
                check.append(link)
        if len(check) == 0:
            return True
        else:
            return check

    # checks if alternates exist and have alternates pointing back to the origin
    def check_return(self, url_element, data):
        url = url_element["url"]
        links = list(map(lambda x: x["link"], url_element["alts"]))
        urls = list(map(lambda x: x["url"], data["urls"]))
        check = []
        for link in links:
            if link in urls:
                index = urls.index(link)
                other_element = data["urls"][index]
                other_links = list(map(lambda x: x["link"], other_element["alts"]))
                if url in other_links:
                    print(url + " points to " + link + " and has link pointing back to it")
                else:
                    print(url + " points to " + link + " but not return")
                    check.append(link)
            else:
                pass
        if len(check) == 0:
            return True
        else:
            return check

    # checks if alternates exist, then if they do ensures that the origins targeting is
    # the same as the targeting applied by the alternate
    def check_target(self, url_element, data):
        url = url_element["url"]
        links = list(map(lambda x: x["link"], url_element["alts"]))
        targets = list(map(lambda x: x["target"], url_element["alts"]))
        check = []
        for iter, link in enumerate(links):
            target = targets[iter]
            urls = list(map(lambda x: x["url"], data["urls"]))
            if link in urls:
                index = urls.index(link)
                other_element = data["urls"][index]
                other_links = list(map(lambda x: x["link"], other_element["alts"]))
                if url in other_links:
                    other_index = other_links.index(link)
                    other_targets = list(map(lambda x: x["target"], other_element["alts"]))
                    other_target = other_targets[other_index]
                    if target == other_target:
                        print(url + "url with target " + target + " is pointed to with target " + other_target)
                    else:
                        print(url + "url with target " + target + " is pointed to with target " + other_target)
                        check.append(target)
                else:
                    pass
            else:
                pass
        if len(check) == 0:
            return True
        else:
            return check

    # loops through each url in sitemap applying checks to each, updates dict with "checks" which have data on errors
    def check_data(self):
        data = self.get_data()
        data["checks"] = []
        for url_element in data["urls"]:
            checks = []
            checks.append({"self ref": self.check_self_ref(url_element)})
            checks.append({"points to link in map": self.check_link_in_map(url_element, data)})
            checks.append({"has return": self.check_return(url_element, data)})
            checks.append({"same target": self.check_target(url_element, data)})
            data["checks"].append(checks)
        return data






# just some example urls i was using to test as i coded, some of the bigger ones cause memory error for me
# when checking the sitemap which is fairly understandable, dealing with pretty huge processing requirements

next = "http://www.next.de/de"
canon = "https://www.canon.co.uk/"
balsam = "https://www.balsamhill.co.uk"
google = "https://www.google.com"
macidys = "https://www.mcdonalds.com/"
asics = "https://www.asics.com/"
nuanc = "https://www.nuance.com"


# Just some example calls
# x = crawler(balsam)
# roboter = x.home_page + "robots.txt"
# rp = robotparser.RobotFileParser()
# rp.set_url(roboter)
# rp.read()
a = sitemap(asics)
data = a.check_data()
# x.rec_crawl()

