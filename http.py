import os
import time
import numpy as np
from urlparse import urlparse

import requests

import backoff


#@backoff.on_exception(backoff.expo,
                      #requests.ConnectionError,
                      #max_tries=5,)
def download_safe(url, binary=False, referer=None, wait=0, verbose=True):
    ret = download(url, binary, referer)

    if not ret or wait == 0:
        return ret

    mul = np.random.normal(loc=1.0, scale=0.1)
    if verbose:
        print 'Sleeping {} seconds'.format(wait * mul)
    time.sleep(wait * mul)
    return ret


def download(url, binary=False, referer=None):
    r = download_gen(url, referer=referer)
    if r is None:
        return None

    if binary:
        return r.content
    else:
        return r.text


def download_gen(url, referer=None):
    """ Download a URL with a fake User-Agent string """

    if not url:
        print "Warning: empty URL"
        return None

    # spoof some headers to make us seem ore like a browser
    headers = {
        'Host': urlparse(url).netloc,
        'User-Agent': (
            'Mozilla/5.0 (X11; Linux x86_64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/34.0.1847.14 '
            'Safari/537.36'
        ),
        'DNT': '1',
        'Cache-Control': 'max-age=0',
        'Accept-Language': 'en-US,en;q=0.8',
    }

    if referer:
        headers['Referer'] = referer

    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        #print "download success: %s" % url
        return r
    else:
        print "download fail: (status %s) %s" % (r.status_code, url)
        print "Response content: %s" % r.content
        return None


def download_save(url, filepath, binary=False, referer=None, verbose=False):
    '''
    Downloads an URL to the specified path.
    Input:
        url -- The URL to download from
        filepath -- The path where we will download to
        binary -- True if the URL has binary content, False otherwise
        referer -- If not None, we set the HTTP Referer header to this value
    Output:
        True in case of success, False otherwise
    '''
    if os.path.exists(filepath):
        if verbose:
            print 'already downloaded %s' % (filepath)
        return True
    else:
        try:
            if verbose:
                print 'downloading %s --> %s...' % (url, filepath)
            data = download(url, binary, referer)
            if not data:
                return False

            with open(filepath, 'wb') as f:
                f.write(data)
            return True
        except Exception as e:
            print e
            if os.path.exists(filepath):
                os.remove(filepath)
            return False
