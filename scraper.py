import json
import os
import re
import urlparse
import uuid

from lxml import html

from common.http import download_safe
from common.utils import ensuredir


def download_image(root_path, rel_path, img_url, verbose=False):
    img_data = download_safe(img_url, binary=True, wait=4)
    if not img_data:
        print 'No image found at {}, skipping...'.format(img_url)
        return None

    if verbose:
        print 'Saving {}...'.format(img_url)
    _, ext = os.path.splitext(img_url)
    filename = str(uuid.uuid4()) + ext
    full_path = os.path.join(root_path, rel_path, filename)
    ensuredir(os.path.join(root_path, rel_path))
    with open(full_path, 'wb') as f:
        f.write(img_data)

    return filename


def hits_for_filter(url, xpath, verbose=False):
    '''
    Returns all hits on the page specified by :ref:`url` for an xpath filter
    specified by :ref:`xpath`

    :param url: Url of the page to parse

    :param xpath: xpath filter to apply to the page content
    '''
    return hits_for_filters(url, [xpath], verbose)[0]


def hits_for_filters(url, xpath_list, verbose=False):
    '''
    Returns all hits on the page specified by :ref:`url` for an xpath filter
    list specified by :ref:`xpath_list` as a list of lists.

    :param url: Url of the page to parse

    :param xpath_list: xpath filters to apply to the page content
    '''
    if verbose:
        print 'Scraping url: ', url
    page = download_safe(url, wait=4)
    if not page:
        raise ValueError(
            'Couldn\'t download from the provided url: {}'.format(url)
        )

    tree = html.fromstring(page)
    hits_list = []
    for xpath in xpath_list:
        hits = tree.xpath(xpath)
        hits_list.append(hits)

    return hits_list


def scrape_items(root_path, rel_path, url, filter_list, verbose=False):
    '''
    Scrapes all the items specified by @filter_list and saves them under
    @root_path
    params:
        root_path -- The root path where the images and metadata should be
        rel_path -- The relative path where the images will be saved
        saved
        url -- Url of the page to parse
        filter_list -- A list of dictionaries containing the search patterns
        and hierarchy of the webpage
            Optional keys for the dictionaries in filter_list:
                - xpath: specifies an XPath filter which will be used to filter
                the page contents
                - regex: this filter will be used to filter the hits we got
                from using the XPath filter
                - content: True if this filter should save content (image, text
                etc.), False if this is just an intermediate filter in the
                hierarchy
                - type: Only works if content is True, this specifies the type
                of the content. Currently it can be 'img', 'text', 'default'.
                If 'default', we save a prespecified key-value pair (specified
                by 'key', 'value' elements of this dictionary)
                - key: The key we should save the data in the item's dictionary
                - val: The value we should save the data in the item's
                dictionary. This works only if type is 'default'.
    '''
    root_path = os.path.abspath(root_path)
    if verbose:
        print 'Root path:', root_path
    items = []
    if verbose:
        print 'Scraping url: ', url
    page = download_safe(url, wait=4)
    if not page:
        raise ValueError(
            'Couldn\'t download from the provided url: {}'.format(url)
        )

    tree = html.fromstring(page)

    item_excluded = False
    item = {}
    imgs_to_download = []
    for dic in filter_list:
        hits = []
        if 'xpath' in dic:
            if verbose:
                print 'Hits found for xpath pattern: ', dic['xpath']
            hits = tree.xpath(dic['xpath'])
            if verbose:
                for h_idx, h in enumerate(hits):
                    print '{}. -> {}'.format(h_idx + 1, h.encode('utf-8'))

            # Filter with regex
            if 'regex' in dic:
                if verbose:
                    print 'Hits found for regex pattern: ', dic['regex']

                hits_filt = []
                for h in hits:
                    if re.match(dic['regex'], h, flags=re.IGNORECASE):
                        hits_filt.append(h)
                hits = hits_filt

                if verbose:
                    for h_idx, h in enumerate(hits):
                        print '{}. -> {}'.format(h_idx + 1, h.encode('utf-8'))

        # If we want to save any content for this pattern
        if dic['content']:
            if 'type' not in dic:
                raise ValueError('Unspecified type for content!')
            if 'key' not in dic:
                raise ValueError('Unspecified key for content!')

            # if a content filter doesn't have any hits, this item should be
            # excluded
            if not hits and dic['type'] != 'full_html' and dic['type'] != 'default':
                if 'optional' in dic and dic['optional']:
                    if verbose:
                        print 'No hits, but this is optional, continuing...'
                    hits = []
                else:
                    if verbose:
                        print 'All hits excluded, excluding {}...'.format(dic['key'])
                    item_excluded = True
                    continue

            if dic['type'] == 'text':
                item[dic['key']] = '\n'.join(hits)
            elif dic['type'] == 'text_list':
                item[dic['key']] = hits
            elif dic['type'] == 'img':
                imgs_to_download.append((dic['key'], hits))
            elif dic['type'] == 'full_html':
                item[dic['key']] = page
            elif dic['type'] == 'default':
                item[dic['key']] = dic['val']
            else:
                raise ValueError('Invalid type for content!')

            # Add default paramters if we have them
            if 'defaults' in dic:
                for k, v in dic['defaults'].iteritems():
                    item[k] = v
        elif 'children' in dic:
            for h in hits:
                h = urlparse.urljoin(url, h)
                citems = scrape_items(root_path, rel_path, h, dic['children'], verbose)
                items += citems

    if not item_excluded:
        # Download image, now that we know that this item won't be skipped
        for key, hits in imgs_to_download:
            imgs = []
            for h in hits:
                img_url = urlparse.urljoin(url, h)
                filename = download_image(
                    root_path, rel_path, img_url, verbose
                )
                if filename is None:
                    continue

                # Link, relative path
                imgs.append((img_url, os.path.join(rel_path, filename)))
            item[key] = imgs

        if item:
            items.append(item)

    return items


def save_items(items, root_path, metadata_filename, pretty=True):
    if pretty:
        json.dump(
            items, open(os.path.join(root_path, metadata_filename), 'w'),
            sort_keys=True, indent=4, separators=(',', ': ')
        )
    else:
        json.dump(items, open(os.path.join(root_path, metadata_filename), 'w'))


def scrape_items_and_save(root_path, rel_path, url, filter_list,
                          metadata_filename, pretty=True, verbose=False):
        items = scrape_items(root_path, rel_path, url, filter_list, verbose)
        save_items(items, root_path, metadata_filename, pretty)
        return items
