import requests
from bs4 import BeautifulSoup
import urllib.robotparser as robotparser
import urllib.parse
import time
import re
import validators


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
                checked_link = self.validate_link(link["href"])
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


class crawler:
    def __init__(self, page):
        self.current_page = page
        self.parsed_uri = urllib.parse.urlparse(page)
        self.home_page = '{uri.scheme}://{uri.netloc}/'.format(uri=self.parsed_uri)
        self.to_crawl = [page]
        self.crawled = []

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


x = crawler("https://www.balsamhill.co.uk")
rp = robotparser.RobotFileParser()
rp.set_url(x.home_page + "robots.txt")
rp.read()
x.rec_crawl()






# def check_sitemap(homepage):
#     # raw_home = homepage if homepage[len(homepage) - 1] != "/" else homepage[:-1]
#     # r = requests.get(raw_home + "/robots.txt")
#     # lines = r.content.split(b"\n")
#     # sitemaps = []
#     # for line in lines:
#     #     if "Sitemap:" in line.decode("utf-8"):
#     #          sitemaps.append(line.decode("utf-8").split(" ")[1])
#     # for sitemap in sitemaps:
#     #     r = requests.get(sitemap)
#     #     soup = BeautifulSoup(r.content, 'lxml')
#     #     sub_maps = soup.find_all("sitemap")
#     #     if len(sub_maps) == 0:
#     #          for url in soup.find_all("url"):
#     #              print(url.text)
#     #     else:
#     #         for sub_map in sub_maps:
#     #             y = requests.get(sub_map.loc.text)
#     #             soup = BeautifulSoup(y.content, "lxml")
#     #             for url in soup.find_all("url"):
#     #                 print(url.text)
#
#
#     return True
