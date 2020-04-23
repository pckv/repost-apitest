import argparse
import statistics

from apitest.test import test_everything


def test_once(url: str):
    print(f'Starting complete API test on base URL {url}')
    stats = test_everything(url)

    print(f'\nExecuted {stats.count} tests')
    print(f'Passed in {stats.elapsed_seconds} seconds')


def test_multiple(url: str, runs: int):
    total_stats = []
    print(f'Starting {runs} runs for complete API test on {url}')
    for i in range(runs):
        stats = test_everything(url, logging=False)
        print(f'Run {i + 1} passed in {stats.elapsed_seconds} seconds')
        total_stats.append(stats)

    elapsed_seconds = [stats.elapsed_seconds for stats in total_stats]

    print(f'Executed {runs} runs in {sum(elapsed_seconds)} seconds')
    print(f'Performed a total of {sum(stats.count for stats in total_stats)} tests')

    print(f'\nStats:\n'
          f'\tmean: {statistics.mean(elapsed_seconds)}\n'
          f'\tmedian: {statistics.median(elapsed_seconds)}\n')


def main():
    parser = argparse.ArgumentParser(description='Run a full test of a Repost API.')
    parser.add_argument('url', help='The base URL of the API.')
    parser.add_argument('--runs', type=int, default=1, help='Number of full test runs.')
    args = parser.parse_args()

    if args.runs > 1:
        test_multiple(args.url, args.runs)
    else:
        test_once(args.url)


if __name__ == '__main__':
    main()
