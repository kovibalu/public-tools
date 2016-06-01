import json
import os

from django.core.management.base import BaseCommand
from collectdata.scraper import scrape_items_and_save, save_items


def convert_from_oldformat(root_path):
    mat_path = os.path.join(root_path, 'photos.json')
    metadata = json.load(open(mat_path))
    for i in range(len(metadata)):
        metadata[i]['name'] = 'copper'

    save_items(metadata, root_path, 'photos.json')


class Command(BaseCommand):
    args = ''
    help = 'Scrapes the coppersinksonline webpage and saves the images'

    def handle(self, *args, **option):
        root_path = os.path.abspath('../../../data/scraped/coppersinksonline')

        #convert_from_oldformat(root_path)
        #return

        root_url = 'http://www.coppersinksonline.com/copper-sinks-photo-gallery.aspx'
        filter_list = [
            {
                'xpath': '//div[@id="tnitems"]/div/a[img]/@href',
                'regex': '^((?!ed-and-lisa-home).)*$',
                'content': False,
                'children': [
                    {
                        'xpath': '//div[@id="main"]//div[@id="midcontent"]//img/@src',
                        'content': True,
                        'type': 'img',
                        'key': 'imgs',
                    },
                    {
                        'content': True,
                        'type': 'default',
                        'key': 'type_name',
                        'val': 'copper',
                    },
                    {
                        'content': True,
                        'type': 'default',
                        'key': 'name',
                        'val': 'copper',
                    },
                    {
                        'content': True,
                        'type': 'default',
                        'key': 'application',
                        'val': '',
                    },
                ],
            },
        ]
        scrape_items_and_save(
            root_path, '', root_url, filter_list, 'photos.json',
            verbose=True,
        )
