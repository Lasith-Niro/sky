import json
from sky.configs import DEFAULT_CRAWL_CONFIG
from sky.scraper import Scrape
from sky.crawler import crawl
import cloudant

class CrawlPlugin():
    def __init__(self, plugin_name):
        self.plugin_name = plugin_name 
        self.crawl_config = None
        self.scrape_config = None
        self.data = {}

    def get_default_plugin(self):
        pass

    def apply_specific_plugin(self):
        pass

    def get_scrape_config(self):    
        scrape_config = self.crawl_config.copy()

        scrape_config.update({ 
            'template_proportion' : 0.09,
            'max_templates' : 1000
        })

        return scrape_config

    def start_crawl(self):
        crawl.start(self.crawl_config)
    
    def scrape_data(self):
        # Create boilerplate recognizer
        skindex = Scrape(self.scrape_config)

        # Process all by removing boilerplate and extracting information
        return skindex.process_all(exclude_data = ['cleaned', 'author'])

    def handle_results(self):
        pass

    def run(self):
        self.crawl_config = self.get_default_plugin()
        self.apply_specific_plugin()
        self.scrape_config = self.get_scrape_config()
        self.start_crawl()
        self.data = self.scrape_data()
        self.handle_results()

class CrawlFilePlugin(CrawlPlugin):
    def __init__(self, plugin_name): 
        super(CrawlFilePlugin, self).__init__(plugin_name)

    def get_default_plugin(self): 
        return DEFAULT_CRAWL_CONFIG
        
    def apply_specific_plugin(self):
        with open(self.plugin_name) as f:
            specific_config = json.load(f)
        self.crawl_config.update(specific_config)        
        
    def handle_results(self):
        with open('results_{}.json'.format(self.plugin_name), 'w') as f:
            json.dump(self.data, f)

class CrawlCloudantPlugin(CrawlPlugin):
    def __init__(self, plugin_name): 
        super(CrawlCloudantPlugin, self).__init__(plugin_name) 
        self.crawler_plugins_db = None
        self.crawler_documents_db = None
        self.plugins = []
        self.login()

    def login(self):
        with open('cloudant.username') as f:
            USERNAME = f.read()
        with open('cloudant.password') as f:
            PASSWORD = f.read()
        account = cloudant.Account(USERNAME)
        account.login(USERNAME, PASSWORD)
        self.crawler_plugins_db = account.database('crawler-plugins') 
        self.crawler_documents_db = account.database('crawler-documents')

    def get_plugins(self):
        db_uri = '{}/_all_docs?include_docs=true'.format(self.crawler_plugins_db.uri)
        self.plugins = [x['doc'] for x in self.crawler_plugins_db.get(db_uri).json()['rows']]
        
    def get_default_plugin(self): 
        self.get_plugins()
        for plugin in self.plugins:
            if plugin['_id'] == 'default':
                return plugin 
        
    def apply_specific_plugin(self): 
        for plugin in self.plugins:
            if plugin['_id'] == self.plugin_name:
                self.crawl_config.update(plugin)        
        
    def handle_results(self): 
        ids = self.data.keys()
        cloudant_data = {}
        cloudant_data['docs'] = [{'id' : k, 'doc' : self.data[v] } for k, v in zip(ids, self.data)]
        self.crawler_documents_db.bulk_docs(cloudant_data)

    def save_config(self, config):
        """
        Example of a specific config:
        
        config = { 
        "seed_urls" : [ 
            "http://www.adformatie.nl/"
        ],

        "collection_name" : "adformatie.nl",

        "crawl_filter_strings" : [ 
            "lynkx", "tab=", "/academie-voor-arbeidsmarktcommunicatie", "events."
        ],

        "crawl_required_strings" : [
            "nieuws/", "channel/"
        ],        

        "index_filter_strings" : [

        ],

        "index_required_strings" : [
            "nieuws/"
        ], 

        "max_saved_responses" : 100

        }
        """
        self.crawler_plugins_db[self.plugin_name] = config
