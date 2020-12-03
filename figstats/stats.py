from os.path import join
import pandas as pd

from .commons import issue_request


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
        for counter in ['views', 'downloads', 'shares']:
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
        total_dict = {}
        for counter in ['views', 'downloads', 'shares']:
            # Using non-institution one since that seems to give correct stats
            urls = ['timeline', granularity, counter, item, str(item_id)]
            url = self.stats_endpoint(join(*urls), institution=institution)
            result = issue_request('GET', url, headers=self.basic_headers)
            total_dict[counter] = result['timeline']
        return total_dict

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

    def get_institution_totals(self, df=None, by_method='author'):
        """
        Retrieve total views, downloads, and shares by either authors or articles
        """

        if isinstance(df, type(None)):
            if by_method == 'author':
                df = self.retrieve_institution_users(ignore_admin=False)
            if by_method == 'article':
                print("Need to retrieve articles")

        total_dict = dict()
        for author_id in df.loc[0:5, 'author_id']:
            total_dict[str(author_id)] = self.get_user_totals(author_id)

        # Construct pandas DataFrame
        total_df = pd.DataFrame.from_dict(total_dict, orient='index')
        return total_df
