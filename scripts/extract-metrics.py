#!/usr/bin/env python3
import json, sys, statistics

def lat_pct(job, io, p):
    """io = 'read' | 'write' | 'sync'. Try lat_ns then clat_ns."""
    for ns in ('lat_ns', 'clat_ns'):
        v = job.get(io, {}).get(ns, {}).get('percentile', {}).get(f'{p:.6f}')
        if v is not None:
            return v
    return None

def summarize(path):
    d = json.load(open(path))
    jobs = d['jobs']
    by = {}
    for j in jobs:
        by.setdefault(j['jobname'], []).append(j)

    def first(name):
        return by[name][0]

    def sum_iops(name, io):
        return sum(j[io]['iops'] for j in by[name])

    def avg_lat(name, io, p):
        vals = [lat_pct(j, io, p) for j in by[name]]
        vals = [v for v in vals if v is not None]
        return sum(vals)/len(vals) if vals else None

    m = {}
    m['seq_read_MBps']  = first('seq-read')['read']['bw'] / 1024
    m['seq_write_MBps'] = first('seq-write')['write']['bw'] / 1024
    m['rand_read_4k_qd1_iops']  = first('rand-read-4k-qd1')['read']['iops']
    m['rand_write_4k_qd1_iops'] = first('rand-write-4k-qd1')['write']['iops']
    m['rand_read_4k_qd16_iops']  = sum_iops('rand-read-4k-qd16', 'read')
    m['rand_write_4k_qd16_iops'] = sum_iops('rand-write-4k-qd16', 'write')
    m['rand_read_4k_qd1_p50_ns']  = lat_pct(first('rand-read-4k-qd1'), 'read', 50)
    m['rand_read_4k_qd1_p99_ns']  = lat_pct(first('rand-read-4k-qd1'), 'read', 99)
    m['rand_write_4k_qd1_p50_ns'] = lat_pct(first('rand-write-4k-qd1'), 'write', 50)
    m['rand_write_4k_qd1_p99_ns'] = lat_pct(first('rand-write-4k-qd1'), 'write', 99)
    m['rand_read_4k_qd16_p50_ns']  = avg_lat('rand-read-4k-qd16', 'read', 50)
    m['rand_read_4k_qd16_p99_ns']  = avg_lat('rand-read-4k-qd16', 'read', 99)
    m['rand_write_4k_qd16_p50_ns'] = avg_lat('rand-write-4k-qd16', 'write', 50)
    m['rand_write_4k_qd16_p99_ns'] = avg_lat('rand-write-4k-qd16', 'write', 99)
    m['fsync_p50_ns'] = lat_pct(first('fsync-latency'), 'sync', 50)
    m['fsync_p99_ns'] = lat_pct(first('fsync-latency'), 'sync', 99)
    return m

if __name__ == '__main__':
    files = sys.argv[1:]
    runs = [summarize(f) for f in files]
    keys = list(runs[0].keys())
    header = f"{'metric':<30}" + ''.join(f"{'run'+str(i+1):>12}" for i in range(len(runs))) + f"{'median':>12}{'spread':>10}"
    print(header)
    print('-' * len(header))
    for k in keys:
        vals = [r[k] for r in runs if r[k] is not None]
        if not vals:
            print(f"{k:<30}" + ''.join(f"{'N/A':>12}" for _ in runs) + f"{'N/A':>12}{'N/A':>10}")
            continue
        med = statistics.median(vals)
        spread = (max(vals) - min(vals)) / med * 100 if med else 0
        cells = ''.join(f"{(r[k] if r[k] is not None else 0):>12.2f}" for r in runs)
        print(f"{k:<30}{cells}{med:>12.2f}{spread:>9.1f}%")
