import argparse
from datetime import datetime

from apitest.test import test_everything


def main():
    parser = argparse.ArgumentParser(description='Run a full test of a Repost API.')
    parser.add_argument('url', help='The base URL of the API.')
    args = parser.parse_args()

    print(f'Starting complete API test on base URL {args.url}')
    started = datetime.now()

    stats = test_everything(args.url)

    elapsed = datetime.now() - started

    print(f'\nExecuted {stats.count} tests')
    print(f'Passed in {elapsed.total_seconds()} seconds')


if __name__ == '__main__':
    main()
