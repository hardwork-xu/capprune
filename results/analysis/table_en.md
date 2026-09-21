Measured results; requested one CPU thread, float64, online batch=1. Medians include all repeats; no tail-latency claim.

| Case / 场景 | Scan ms | Blocked ms | Pruned ms | Speedup / 加速比 | Scored / 评分比例 | Build ms |
|---|---:|---:|---:|---:|---:|---:|
| clustered_n5000_d64 | 0.1015 | 0.3225 | 0.0464 | 2.19× | 4.9% | 16.2 |
| clustered_n50000_d64 | 0.9159 | 1.6033 | 0.0898 | 10.20× | 2.3% | 177.2 |
| clustered_n50000_d128 | 1.4321 | 2.0885 | 0.1140 | 12.56× | 3.1% | 311.5 |
| isotropic_n50000_d64 | 1.0157 | 1.6096 | 1.6252 | 0.62× | 100.0% | 168.6 |
| clustered_n50000_k100 | 0.9809 | 1.8960 | 0.0981 | 10.00× | 2.8% | 170.6 |
| digits_real | 0.0512 | 0.2590 | 0.2251 | 0.23× | 84.4% | 6.6 |
| tiny_k_equals_n | 0.0170 | 0.0512 | 0.0629 | 0.27× | 100.0% | 0.6 |
