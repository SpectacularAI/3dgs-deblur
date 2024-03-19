"""Parse output metrics from JSON files"""
import os
import json

def parse_metrics(metrics_path):
    with open(metrics_path) as f:
        return json.load(f)

def find_and_parse_directories_containing_splatting_metrics(root_dir):
    matching_dirs = []

    def parse_dir(dirpath, filename):
        run_name = dirpath[len(root_dir)+1:]
        dataset, _, rest = run_name.partition('/')
        
        # if dataset == 'misc': return None

        rest_split = rest.split('/')
        if len(rest_split) != 4: return None
        variant, session, method, ts = rest_split
        if method != 'splatfacto': return None

        m = parse_metrics(os.path.join(dirpath, filename))

        d = {
            #'dataset': dataset[:1],
            'dataset': dataset,
            'variant': variant,
            'session': session,
            'path': dirpath,
            'time': m.get('wall_clock_time_seconds', -1)
        }

        
        for k, v in m['results'].items(): d[k] = v
        # print(d)
        return d

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            # print(dirpath, filename)
            if filename == 'metrics.json':
                parsed = parse_dir(dirpath, filename)
                if parsed is not None:
                    matching_dirs.append(parsed)
                break

    return sorted(matching_dirs, key=lambda x: x['path'])

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', type=str, nargs='?', default=None)
    parser.add_argument('-f', '--output_format', choices=['csv', 'txt'], default='txt')
    args = parser.parse_args()

    import pandas as pd
    pd.set_option("display.max_rows", None)
    df = pd.DataFrame(find_and_parse_directories_containing_splatting_metrics('data/outputs'))
    cols = 'dataset variant session psnr ssim lpips time'.split()
    df = df[cols]
    if args.dataset is not None:
        df = df[df['dataset'] == args.dataset].drop('dataset', axis=1)
        
    if args.output_format == 'csv':
        print(df.to_csv(index=False))
    elif args.output_format == 'txt':
        print(df)
    else:
        raise ValueError(f'Unknown format: {args.output_format}')