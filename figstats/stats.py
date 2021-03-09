from os.path import join
import pandas as pd

from .commons import issue_request

counter_list = ['views', 'downloads', 'shares']


class Figshare:
    """
    Purpose:
      A Python interface to work with Figshare statistics endpoint

    """

    def __init__(self, api_token='', basic_token='', institution=False, institute=''):

        # For stats API
        self.stats_baseurl = 'https://stats.figshare.com'
        self.institution = institution
        if institute:
            self.institute = institute
            self.stats_baseurl_institute = join(self.stats_baseurl, self.institute)

        # Base64 token
        self.basic_headers = {'Content-Type': 'application/json'}
        self.basic_token = basic_token
        if self.basic_token:
            self.basic_headers['Authorization'] = f'Basic {self.basic_token}'

        # For Figshare API
        self.main_baseurl = 'https://api.figshare.com/v2/account/'
        if self.institution:
            self.main_baseurl_institute = join(self.main_baseurl, "institution")

        # API token
        self.api_headers = {'Content-Type': 'application/json'}
        self.api_token = api_token
        if self.api_token:
            self.api_headers['Authorization'] = f'token {self.api_token}'

    def stats_endpoint(self, link, institution=False):
        if institution:
            return join(self.stats_baseurl_institute, link)
        else:
            return join(self.stats_baseurl, link)

    def get_totals(self, item_id, item='article', institution=False):
        """
        Retrieve totals of views, downloads, and share for an "item"
        Item can be 'article', 'author', 'collection', 'group' or 'project'
        Note: This does not require authenticating credentials for institution accounts

        See: https://docs.figshare.com/#stats_totals
        """

        if item not in ['article', 'author', 'collection', 'group', 'project']:
            raise ValueError("Incorrect item type")

        total_dict = {}
        for counter in counter_list:
            # Using non-institution one since that seems to give correct stats
            url = self.stats_endpoint(join('total', counter, item, str(item_id)),
                                      institution=institution)
            result = issue_request('GET', url, headers=self.basic_headers)
            total_dict[counter] = result['totals']
        return total_dict

    def get_user_totals(self, author_id):
        """
        Retrieve an author's total using get_totals()

        :param author_id: This is not the same as the institution_user_id for institutional accounts
        :return: total_dict: dict containing total views, downloads, and shares
        Note: This does not require authenticating credentials for institution accounts
        """
        total_dict = self.get_totals(author_id, item='author',
                                     institution=False)
        return total_dict

    def get_timeline(self, item_id, item='article', granularity='day',
                     institution=False):
        timeline_dict = {}
        for counter in counter_list:
            # Using non-institution one since that seems to give correct stats
            urls = ['timeline', granularity, counter, item, str(item_id)]
            url = self.stats_endpoint(join(*urls), institution=institution)
            result = issue_request('GET', url, headers=self.basic_headers)
            # Sort contents by date
            result_sort = {}
            cum_dict = {}
            count = 0
            # Use views record for timeline (most populated generally)
            if counter == 'views':
                save_date = sorted(result['timeline'])
            for key in save_date:
                if isinstance(result['timeline'], type(None)):
                    # Handle when counter is not available (NoneType)
                    result_sort[key] = 0
                else:
                    try:
                        result_sort[key] = result['timeline'][key]
                        count += result['timeline'][key]
                    except KeyError:
                        result_sort[key] = 0
                cum_dict[key] = count
            timeline_dict[counter] = result_sort
            timeline_dict[f"{counter}-cum"] = cum_dict
        return timeline_dict

    def get_figshare_id(self, accounts_df):
        """
        Retrieve Figshare account ID(s)
        Note: This is not the institutional ID, but one associated with
              the unique profile

        :param accounts_df: pandas DataFrame containing institution ID
        :return: accounts_df: The input DataFrame with an additional column
        """

        endpoint = join(self.main_baseurl_institute, "users")

        author_id = []
        for institute_id in accounts_df['id']:
            url = f"{endpoint}/{institute_id}"
            response = issue_request('GET', url, self.api_headers)
            author_id.append(response['id'])
        accounts_df['author_id'] = author_id
        return accounts_df

    def retrieve_institution_users(self, ignore_admin=False):
        """
        Retrieve accounts within institutional instance

        This is based on LD-Cool-P get_account_list method of FigshareInstituteAdmin
        It includes retrieving the default author_id

        It uses:
        https://docs.figshare.com/#private_institution_accounts_list
        https://docs.figshare.com/#private_account_institution_user
        """
        url = join(self.main_baseurl_institute, "accounts")

        # Figshare API is limited to a maximum of 1000 per page
        params = {'page': 1, 'page_size': 1000}
        accounts = issue_request('GET', url, self.api_headers, params=params)

        accounts_df = pd.DataFrame(accounts)
        accounts_df = accounts_df.drop(columns='institution_id')

        if ignore_admin:
            print("Excluding administrative and test accounts")

            drop_index = list(accounts_df[accounts_df['email'] ==
                                          'data-management@email.arizona.edu'].index)
            drop_index += list(accounts_df[accounts_df['email'].str.contains('-test@email.arizona.edu')].index)

            accounts_df = accounts_df.drop(drop_index).reset_index(drop=True)

        accounts_df = self.get_figshare_id(accounts_df)

        return accounts_df

    def retrieve_institution_articles(self):

        url = join(self.main_baseurl_institute, "articles")

        # Figshare API is limited to a maximum of 1000 per page
        params = {'page': 1,
                  'page_size': 1000}
        articles = issue_request('GET', url, self.api_headers, params=params)

        articles_df = pd.DataFrame(articles)

        # Only consider published dataset
        articles_df = articles_df.loc[articles_df['published_date'].notnull()]
        articles_df = articles_df.reset_index()
        return articles_df

    def retrieve_article_details(self, article_id):
        """Retrieve article details"""
        url = join('https://api.figshare.com/v2/', f"articles/{article_id}")

        article_dict = issue_request('GET', url, self.basic_headers)
        return article_dict

    def get_institution_totals(self, df=None, by_method='author'):
        """
        Retrieve total views, downloads, and shares by either authors or articles
        """

        if isinstance(df, type(None)):
            if by_method == 'author':
                df = self.retrieve_institution_users(ignore_admin=False)
            if by_method == 'article':
                df = self.retrieve_institution_articles()

        total_dict = dict()
        for i in df.index:
            print(f"{i+1} of {len(df.index)}")
            record = df.loc[i]
            if by_method == 'author':
                first_name = record['first_name']
                last_name = record['last_name']
                author_id = record['author_id']
                total_dict[f"{first_name} {last_name} ({author_id})"] = self.get_user_totals(author_id)
            if by_method == 'article':
                total_dict[f"{record['id']}"] = self.get_totals(record['id'],
                                                                item='article',
                                                                institution=False)
        # Construct pandas DataFrame
        total_df = pd.DataFrame.from_dict(total_dict, orient='index')
        return total_df
