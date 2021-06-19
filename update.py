import datetime
import json
import logging
import os
from collections import defaultdict

import requests
from pyquery import PyQuery
from requests.auth import HTTPBasicAuth

# https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token
TOKEN = os.environ['GH_TOKEN']
USER = os.environ['GH_USER']

REQUESTS_RETRY_CNT = 3


def retry(func, cnt=REQUESTS_RETRY_CNT):
    for _ in range(cnt):
        try:
            return func()
        except Exception as e:
            logging.exception('Error in %s: %s', func, e)

    raise RuntimeError('Task failed')


def gen_dependents(repo):
    url = 'https://github.com/%s/network/dependents/' % repo.lstrip('/')
    cnt = -1
    while url:
        print(url)

        html = retry(lambda: requests.get(url, timeout=20).text)
        doc = PyQuery(html)
        if cnt == -1:
            cnt = int(
                doc('#dependents a.selected').text().replace('Repositories', '').replace('Dependents', '').strip())

        repos = doc('#dependents a[data-hovercard-type="repository"]')
        for repo in repos.items():
            name = repo.attr.href
            yield cnt, name
            cnt -= 1

        if doc('.paginate-container a').eq(-1).text() == 'Next':
            url = doc('.paginate-container a').eq(-1).attr.href
        else:
            url = None


def dependents_info(repo, days, cache={}):
    """
    累计used
    :param repo:
    :param days:
    :param cache: {repo->create_time}
    :return: [{'date': '2021-05-17', 'total': 1}, {'date': '2021-05-18', 'total': 2}, ...] 时间是连续递增的
    """
    date_cnt = defaultdict(int)
    for d in cache.values():
        date_cnt[d] += 1

    cache_hit_cnt = 0
    total_cnt = 0
    for num, repo in gen_dependents(repo=repo):
        total_cnt = max(total_cnt, num)
        res = ''
        try:
            if repo in cache:
                cache_hit_cnt += 1
            else:
                res = retry(lambda: requests.get('https://api.github.com/repos/' + repo.lstrip('/'),
                                                 auth=HTTPBasicAuth(USER, TOKEN), timeout=20).json())
                create_date = res['created_at'][:len("2020-02-29")]
                cache[repo] = create_date
                date_cnt[create_date] += 1
                print('repo[%s] create at: %s' % (repo, create_date))

        except Exception as e:
            print(e, res)

        if cache_hit_cnt > 10:
            break

    counts = [{
        'date': datetime.datetime.today().strftime("%Y-%m-%d"),
        'total': total_cnt
    }]
    for dur in range(1, days):
        curr = (datetime.datetime.today() - datetime.timedelta(days=dur)).strftime("%Y-%m-%d")
        tomorrow = (datetime.datetime.today() - datetime.timedelta(days=dur - 1)).strftime("%Y-%m-%d")
        cnt = counts[-1]['total'] - date_cnt[tomorrow]
        counts.append({'date': curr, 'total': cnt})

    return list(reversed(counts))


def CDN_hits_info(days=60):
    """
    获取每日cdn点击数
    :param days:
    :return: [{'date': '2021-05-17', 'count': 150}, {'date': '2021-05-18', 'count': 149}, ...] 时间是连续递增的
    """
    url = "https://data.jsdelivr.com/v1/package/gh/wang0618/PyWebIO-assets/stats/date/year"
    date_cnt = requests.get(url, timeout=20).json()['dates']
    date_cnt = [{'date': k, 'count': v['total']} for k, v in date_cnt.items()]
    date_cnt.sort(key=lambda i: i['date'])
    return date_cnt[-days:]


def star_count(repo):
    res = retry(
        lambda: requests.get('https://api.github.com/repos/' + repo.lstrip('/'), auth=HTTPBasicAuth(USER, TOKEN),
                             timeout=20).json())
    return res['stargazers_count']


def star_info(repo, days=60):
    """获取近days天每日累计start

    :param repo:
    :param days:
    :return: list of {'date': '2021-05-18', 'total': },  时间是连续递增的
    """
    headers = {
        'authority': 'api.github.com',
        'accept': 'application/vnd.github.v3.star+json',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
    }
    last_day = (datetime.datetime.today() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    date_cnt = defaultdict(int)
    all_cnt = star_count(repo)
    page_size = 100
    stop = False
    for page in range(all_cnt // page_size + 1, 0, -1):
        print('star_info() request page:', page)
        params = (
            ('per_page', page_size),
            ('page', page),
        )

        response = retry(lambda: requests.get('https://api.github.com/repos/wang0618/PyWebIO/stargazers',
                                              headers=headers, params=params, auth=HTTPBasicAuth(USER, TOKEN),
                                              timeout=20))
        for i in response.json():
            d = i['starred_at'][:len('2021-03-23')]
            if d < last_day:
                stop = True
            date_cnt[d] += 1

        if stop:
            break

    res = [{'date': datetime.datetime.today().strftime("%Y-%m-%d"), 'total': all_cnt}]
    for i in range(1, days):
        curr = (datetime.datetime.today() - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        tomorrow = (datetime.datetime.today() - datetime.timedelta(days=i - 1)).strftime("%Y-%m-%d")
        res.append({'date': curr, 'total': res[-1]['total'] - date_cnt[tomorrow]})

    return list(reversed(res))


def total2daily(data):
    """
    累计转每天
    :param data: 按照日期升序排列的
    :return:
    """
    res = []
    for idx, i in enumerate(data[1:], 1):
        res.append(i['total'] - data[idx - 1]['total'])
    return res


def traffic_data(repo):
    # https://docs.github.com/en/rest/reference/repos#traffic
    views = retry(lambda: requests.get('https://api.github.com/repos/%s/traffic/views' % repo.strip('/'),
                                       auth=HTTPBasicAuth(USER, TOKEN),
                                       timeout=20).json())['views']
    clones = retry(lambda: requests.get('https://api.github.com/repos/%s/traffic/clones' % repo.strip('/'),
                                       auth=HTTPBasicAuth(USER, TOKEN),
                                       timeout=20).json())['clones']
    referrers = retry(lambda: requests.get('https://api.github.com/repos/%s/traffic/popular/referrers' % repo.strip('/'),
                                       auth=HTTPBasicAuth(USER, TOKEN),
                                       timeout=20).json())
    return views, clones, referrers





if __name__ == '__main__':
    """
    Github Stars
    Github Used
    Week New Stars
    Week CDN Hits (Until xxx)
    Week New Used
    
    累计/每日start
    累计/每日used
    每天cdn hit
    """

    here_dir = os.path.dirname(os.path.abspath(__file__))
    repo = 'wang0618/PyWebIO'
    days = 50  # 至少为一周8

    used_cache = json.load(open(os.path.join(here_dir, 'data', 'cache-used.json')))
    used = dependents_info(repo, days, cache=used_cache)
    json.dump(used_cache, open(os.path.join(here_dir, 'data', 'cache-used.json'), 'w'))

    star = star_info(repo=repo, days=days)

    cdn_hits = CDN_hits_info(days)

    views, clones, referrers = traffic_data('wang0618/PyWebIO')

    data = {
        'GithubStars': star[-1]['total'],
        'GithubUsed': used[-1]['total'],
        'WeekNewStars': star[-1]['total'] - star[-8]['total'],
        'WeekCDNHits': sum(i['count'] for i in cdn_hits[-7:]),
        'WeekNewUsed': used[-1]['total'] - used[-8]['total'],

        'star-dates': [i['date'] for i in star[1:]],
        'star-total': [i['total'] for i in star[1:]],
        'star-daily': total2daily(star),

        'used-dates': [i['date'] for i in used[1:]],
        'used-total': [i['total'] for i in used[1:]],
        'used-daily': total2daily(used),

        'cdn-dates': [i['date'] for i in cdn_hits],
        'cdn-daily': [i['count'] for i in cdn_hits],

        'views-dates': [v['timestamp'][:len('yyyy-dd-mm')] for v in views],
        'views-count': [v['count'] for v in views],
        'views-uniques': [v['uniques'] for v in views],

        'clones-dates': [c['timestamp'][:len('yyyy-dd-mm')] for c in clones],
        'clones-count': [c['count'] for c in clones],
        'clones-uniques': [c['uniques'] for c in clones],

        'referrers': referrers,
        'referrers-chart': [dict(name=r['referrer'], value=r['count']) for r in referrers],
    }
    json_str = json.dumps(data, indent=4)
    open(os.path.join(here_dir, 'data', 'data.json'), 'w').write(json_str)
    open(os.path.join(here_dir, 'data', 'data.js'), 'w').write('var data = %s;' % json_str)
