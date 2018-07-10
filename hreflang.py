import requests
from bs4 import BeautifulSoup
import urllib.robotparser as robotparser
import time

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}


def indexable(page, homepage):
    raw_home = homepage if homepage[len(homepage) - 1] != "/" else homepage[:-1]
    r = requests.get(page, allow_redirects=False, headers=headers)
    if r.status_code == 200:
        soup = BeautifulSoup(r.content, "lxml")
        canonicalEl = soup.find("link", {"rel": "canonical"}) if soup.find("link", {"rel": "canonical"}) is not None else ""
        canonical = canonicalEl["href"] if canonicalEl is not "" else ""
        if canonical == page or raw_home + canonical == page or canonical == "":
            robotsEl = soup.find("meta", {"name":"robots"}) if soup.find("meta", {"name":"robots"}) is not None else ""
            robots = robotsEl["content"] if robotsEl is not "" else ""
            if "noindex" not in robots.lower() or "no index" not in robots.lower():
                rp = robotparser.RobotFileParser()
                rp.set_url(raw_home + "/robots.txt")
                rp.read()
                return [rp.can_fetch("Googlebot", page), r]
            else:
                return [False, r]
        else:
            return [False, r]
    else:
        return [False, r]


def check_hreflang(page, homepage, soup):
    try:
        is_page_ok = 0
        checked = []
        source_hreflang_links = []
        source_hreflang_targets = []
        for tag in soup.find_all("link", {"rel": "alternate"}):
            try:
                source_hreflang_targets.append(tag["hreflang"])
                source_hreflang_links.append(tag["href"])
            except:
                pass
        if len(source_hreflang_links) == 0:
            print(page + " has no hreflang links")
            is_page_ok = is_page_ok + 1
        if page not in source_hreflang_links:
            print(page + " is missing self referring tag")
            is_page_ok = is_page_ok + 1
        for source_link in source_hreflang_links:
            source_target = source_hreflang_targets[source_hreflang_links.index(source_link)]
            x = indexable(source_link, homepage)
            checked.append(source_link)
            if x[0]:
                soup = BeautifulSoup(x[1].content, "lxml")
                current_hreflang_links = list(map(lambda y: y["href"], soup.find_all("link", {"rel": "alternate"})))
                if source_link not in source_hreflang_links:
                    print(source_link + " with target " + source_target + " is missing self referring tag")
                    is_page_ok = is_page_ok + 1
                if page not in current_hreflang_links:
                    print(source_link + " is not pointing back to " + page)
                    is_page_ok = is_page_ok + 1
            else:
                print(page + " has a tag that points to " + source_link + " which is not indexable")
                is_page_ok = is_page_ok + 1
        if is_page_ok == 0:
            print(page + " is OK")
        return checked
    except:
        print("error error")



def rec_crawl(cur, to_crawl, homepage, crawled):
    if len(to_crawl) == 0:
        print("All done")
    else:
        print(str(len(to_crawl)) + " to_crawl " + str(len(crawled)) + " crawled " + cur)
        crawled.append(cur)
        to_crawl.remove(cur)
        x = indexable(cur, homepage)
        if x[0]:
            raw_home = homepage if homepage[len(homepage) - 1] != "/" else homepage[:-1]
            r = x[1]
            soup = BeautifulSoup(r.content, "lxml")
            checked = check_hreflang(cur, homepage, soup)
            crawled = list(set(crawled + checked))
            to_crawl = list(set(to_crawl) - set(checked))
            for link in soup.find_all("a"):
                try:
                    link = raw_home + link["href"] if link["href"] == "" or link["href"][:1] == "/" else link["href"]
                    link = link[:link.index("#")] if "#" in link else link
                    if link not in to_crawl and link not in crawled and link[:len(homepage)] == homepage:
                        to_crawl.append(link)
                    else:
                        pass
                except:
                    pass
            time.sleep(1)
            rec_crawl(to_crawl[0], to_crawl, homepage, crawled)
        else:
            time.sleep(1)
            print(cur + " is not indexable")
            rec_crawl(to_crawl[0], to_crawl, homepage, crawled)


def check_sitemap(homepage):
    # raw_home = homepage if homepage[len(homepage) - 1] != "/" else homepage[:-1]
    # r = requests.get(raw_home + "/robots.txt")
    # lines = r.content.split(b"\n")
    # sitemaps = []
    # for line in lines:
    #     if "Sitemap:" in line.decode("utf-8"):
    #          sitemaps.append(line.decode("utf-8").split(" ")[1])
    # for sitemap in sitemaps:
    #     r = requests.get(sitemap)
    #     soup = BeautifulSoup(r.content, 'lxml')
    #     sub_maps = soup.find_all("sitemap")
    #     if len(sub_maps) == 0:
    #          for url in soup.find_all("url"):
    #              print(url.text)
    #     else:
    #         for sub_map in sub_maps:
    #             y = requests.get(sub_map.loc.text)
    #             soup = BeautifulSoup(y.content, "lxml")
    #             for url in soup.find_all("url"):
    #                 print(url.text)


    return True


def start_crawl(homepage, start_page):
    if check_sitemap(homepage):
        x = indexable(start_page, homepage)
        if x[0]:
            to_crawl = []
            raw_home = homepage if homepage[len(homepage) - 1] != "/" else homepage[:-1]
            r = x[1]
            soup = BeautifulSoup(r.content, "lxml")
            check_hreflang(start_page, homepage, soup)
            for link in soup.find_all("a"):
                try:
                    link = raw_home + link["href"] if link["href"] == "" or link["href"][:1] == "/" else link["href"]
                    link = link[:link.index("#")] if "#" in link else link
                    if link not in to_crawl and link != homepage and link[:len(homepage)] == homepage:
                        to_crawl.append(link)
                    else:
                        pass
                except:
                    pass
            rec_crawl(to_crawl[0], to_crawl, homepage, [])
        else:
            print("your home page is not indexable why... just why???")


start_crawl("https://www.cloudflare.com/", "https://www.cloudflare.com/")

# check_sitemap("https://www.google.com")