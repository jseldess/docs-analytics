from bokeh.plotting import figure, output_file, show, ColumnDataSource
from bokeh.transform import jitter
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials


SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
KEY_FILE_LOCATION = '<REPLACE_WITH_JSON_FILE>'
VIEW_ID = '<REPLACE_WITH_VIEW_ID>'
PAGE_METRICS = []
PAGE_TITLES = []


def initialize_analyticsreporting():
    """Initializes an Analytics Reporting API V4 service object.

    Returns:
    An authorized Analytics Reporting API V4 service object.
    """
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        KEY_FILE_LOCATION, SCOPES)

    # Build the service object.
    analytics = build('analyticsreporting', 'v4', credentials=credentials)

    return analytics


def get_no_votes(analytics):
    """Queries the Analytics Reporting API V4.

    Args:
        analytics: An authorized Analytics Reporting API V4 service object.
    Returns:
        The Analytics Reporting API V4 response.
    """
    return analytics.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': VIEW_ID,
                    'dateRanges': [{'startDate': '60daysAgo', 'endDate': 'today'}],
                    'metrics': [
                        {'expression': 'ga:totalEvents'}
                    ],
                    'dimensions': [
                        {'name': 'ga:pageTitle'}
                        # {'name': 'ga:eventAction'}
                    ],
                    'dimensionFilterClauses': [
                        {
                            'filters': [
                                {
                                    'dimensionName': 'ga:eventAction',
                                    'operator': 'REGEXP',
                                    'expressions': ['/docs.*#no-feedback']
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ).execute()


def get_yes_votes(analytics):
    return analytics.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': VIEW_ID,
                    'dateRanges': [{'startDate': '60daysAgo', 'endDate': 'today'}],
                    'metrics': [
                        {'expression': 'ga:totalEvents'}
                    ],
                    'dimensions': [
                        {'name': 'ga:pageTitle'}
                        # {'name': 'ga:eventAction'}
                    ],
                    'dimensionFilterClauses': [
                        {
                            'filters': [
                                {
                                    'dimensionName': 'ga:eventAction',
                                    'operator': 'REGEXP',
                                    'expressions': ['/docs.*#yes-feedback']
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ).execute()


def get_unique_pageviews(analytics):
    titles = '|'.join(PAGE_TITLES)
    # print(titles)
    return analytics.reports().batchGet(
        body= {
            'reportRequests': [
                {
                    'viewId': VIEW_ID,
                    'dateRanges': [{'startDate': '60daysAgo', 'endDate': 'today'}],
                    'metrics': [
                        {'expression': 'ga:uniquePageviews'},
                    ],
                    'dimensions': [
                        {'name': 'ga:pageTitle'},
                    ],
                    'dimensionFilterClauses': [
                        {
                            'filters': [
                                {
                                    'dimensionName': 'ga:pageTitle',
                                    # 'dimensionName': 'ga:pagePath',
                                    'operator': 'REGEXP',
                                    # 'expressions': ['/docs']
                                    'expressions': [titles]
                                }
                            ]
                        }
                    ]

                }
            ]
        }
    ).execute()


def no_response(response):
    for report in response.get('reports', []):
        # print(report)
        for row in report.get('data', {}).get('rows', []):
            # print(row)
            PAGE = {}
            TITLES = ''
            for dimension in row.get('dimensions', {}):
                PAGE['page'] = dimension.replace(' | CockroachDB Docs','')
                PAGE_TITLES.append(dimension.replace(' | CockroachDB Docs',''))
            for metric in row.get('metrics', {}):
                for item in metric.values():
                    PAGE['no_votes'] = item[0]
            PAGE_METRICS.append(PAGE)


def yes_response(response):
    for report in response.get('reports', []):
        # print(report)
        for row in report.get('data', {}).get('rows', []):
            # print(row)
            for n in PAGE_METRICS:
                for dimension in row.get('dimensions', {}):
                    if dimension.replace(' | CockroachDB Docs','') in n.values():
                        for metric in row.get('metrics', {}):
                            for item in metric.values():
                                n['yes_votes'] = item[0]


def pageviews_response(response):
    for report in response.get('reports', []):
        # print(report)
        for row in report.get('data', {}).get('rows', []):
            # print(row)
            for n in PAGE_METRICS:
                for dimension in row.get('dimensions', {}):
                    if dimension.replace(' | CockroachDB Docs','') in n.values():
                        for metric in row.get('metrics', {}):
                            for item in metric.values():
                                n['unique_pageviews'] = item[0]


def build_graph():
    x = []
    y = []
    pageviews = []
    pages = []
    for n in PAGE_METRICS:
        # print(n)
        x.append(int(n['no_votes']))
        pages.append(n['page'])
        try:
            pageviews.append(int(n['unique_pageviews']))
        except:
            pageviews.append(int('0'))
        try:
            y.append(int(n['yes_votes']))
        except:
            y.append(int('0'))
    # print(x, y, pageviews, pages)
    data = dict(
        x = x,
        y = y,
        pageviews = pageviews,
        pages = pages,
    )

    output_file("toolbar.html")

    # Dynamically size markers based on pageviews.
    size = list()
    for n in data['pageviews']:
        size.append(10*round(n/1000))
        # if n < 1000:
        #     size.append(10)
        # elif n < 2000:
        #     size.append(20)
        # elif n < 3000:
        #     size.append(30)
        # elif n < 4000:
        #     size.append(40)
        # else:
        #     size.append(50)

    # Add size markers to data source.
    data['size'] = size

    source = ColumnDataSource(data=data)

    TOOLTIPS = [
        # ("index", "$index"),
        ("Page", "@pages"),
        ("Unique Pageviews", "@pageviews"),
        ("Negative Votes", "$x"),
        ("Positive Votes", "$y"),
    ]

    p = figure(plot_width=700, plot_height=700, tooltips=TOOLTIPS,
               title="Hover to see page details")

    p.circle(x='x', fill_alpha=0.2, y=jitter('y', width=0.6), size='size', source=source)

    p.xaxis.axis_label = "Negative Votes"
    p.xaxis.axis_label_text_color = "#aa6666"
    p.xaxis.axis_label_standoff = 30

    p.yaxis.axis_label = "Positive Votes"
    p.yaxis.axis_label_text_color = "#aa6666"
    p.yaxis.axis_label_standoff = 30

    show(p)


def main():
    analytics = initialize_analyticsreporting()
    no_response(get_no_votes(analytics))
    yes_response(get_yes_votes(analytics))
    pageviews_response(get_unique_pageviews(analytics))
    build_graph()
    print(PAGE_METRICS)


if __name__ == '__main__':
    main()
