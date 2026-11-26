# Nomad CSI storage lab

Testing whether self-hosted storage (SeaweedFS, RustFS) can replace Docker
volumes as Nomad CSI volumes, and what it costs in speed and safety.

**Status:** Block 2 complete (Docker-volume baseline, 3 runs). SeaweedFS and
RustFS not started.

## Environment

| Item | Value |
|---|---|
| Host OS | Ubuntu 24.04.5 LTS (WSL2) |
| CPU | 8 vCPU, 11th Gen Intel Core i5-1135G7 |
| RAM | 3.7 GiB total |
| Disk | WSL2 virtual disk backed by Windows host (ROTA flag unreliable; hardware unknown) |
| Docker | 29.10.0 |
| Nomad | v2.1.1 (rev d0f2104) |
| Consul | v2.1.0 |
| fio image | `xridge/fio:latest` |
| /dev/fuse | present |

Lab numbers are relative, not production numbers.

## Repo layout

fio-jobs/ fio job files (shared across all options)
nomad-jobs/ Nomad job and volume HCL
scripts/ helper scripts (metric extraction)
docker-compose/ and raw/ are working dirs (raw/ is gitignored, held locally as evidence)

text

## Reproduce the baseline (Docker volume)

The baseline is a plain Docker volume, run with the shared fio job file
**three times**. The job file hash is:
dc360f5b6ecceee16c1a98abfb8f25f0e56daac691af6b630c4903dc868a35e6 fio-jobs/csi-benchmark.fio

text

### 1. Create the volume

```bash
docker volume create fio-baseline
2. Run fio three times (run1/run2/run3)
bash
for n in 1 2 3; do
  docker run --name fio-baseline-run${n} \
    -v fio-baseline:/data \
    -v "$PWD/fio-jobs:/fio-jobs:ro" \
    xridge/fio:latest \
    --output-format=json \
    /fio-jobs/csi-benchmark.fio \
    --output=/data/fio-baseline-run${n}.json
  docker cp fio-baseline-run${n}:/data/fio-baseline-run${n}.json raw/fio-baseline-run${n}.json
  docker rm fio-baseline-run${n}
done
3. Extract the table
bash
python3 scripts/extract-metrics.py raw/fio-baseline-run1.json raw/fio-baseline-run2.json raw/fio-baseline-run3.json
Expected: 17 metric rows (seq MB/s, 4K IOPS at QD1/QD16, p50/p99 latencies, fsync p50/p99), each with run1/run2/run3, median, spread.

Baseline results (3 runs)
Source: raw/fio-baseline-run{1,2,3}.json, table: raw/baseline-table.txt

Metric	run1	run2	run3	median	spread
seq_read_MBps	375.92	183.12	153.66	183.12	121.4%
seq_write_MBps	408.95	78.02	79.60	79.60	415.7%
rand_read_4k_qd1_iops	2157.42	1875.14	1941.23	1941.23	14.5%
rand_write_4k_qd1_iops	2676.47	2128.14	2319.61	2319.61	23.6%
rand_read_4k_qd16_iops	30624.60	24273.49	23448.71	24273.49	29.6%
rand_write_4k_qd16_iops	30917.02	19977.16	16514.58	19977.16	72.1%
rand_read_4k_qd1_p50_ns	268288	284672	250880	268288	12.6%
rand_read_4k_qd1_p99_ns	3293184	4358144	4423680	4358144	25.9%
rand_write_4k_qd1_p50_ns	199680	203776	175104	199680	14.4%
rand_write_4k_qd1_p99_ns	2965504	3555328	3620864	3555328	18.4%
rand_read_4k_qd16_p50_ns	1449984	2072576	2129920	2072576	32.8%
rand_read_4k_qd16_p99_ns	11763712	11960320	11665408	11763712	2.5%
rand_write_4k_qd16_p50_ns	1273856	1900544	1925120	1900544	34.3%
rand_write_4k_qd16_p99_ns	13467648	22216704	16007168	16007168	54.7%
fsync_p50_ns	502	446	410	446	20.6%
fsync_p99_ns	1768	1544	1208	1544	36.3%
Method notes:

QD16 IOPS is the sum of 4 fio worker jobs (numjobs=4).

fsync-latency is write-only; its read block is all zeros by design.

Variance is high (seq write spread 416%) — WSL2 with 3.7 GiB RAM. First run is not comparable to later runs. Numbers are relative.

Lessons from the job-file setup (failed attempts kept as evidence)
xridge/fio image ENTRYPOINT is already fio. Passing fio /job.fio runs fio fio ... and fails with unable to open 'fio' job file. Pass only the job file path.

output-format is a CLI option, not a job-file option. Putting it in [global] fails with Bad option <output-format=json> and drops the whole job.

group_reporting=1 collapses all jobs into one entry, so per-metric rows cannot be extracted. It was removed.

numjobs=4 produces 4 entries per QD16 job — expected, not a bug.

Next
Block 3: SeaweedFS as a Nomad CSI volume (plugin, volume, test job, privilege notes).
