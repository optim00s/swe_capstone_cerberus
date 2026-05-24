# Offline CLI Sample

Command:

```bash
python -m foodanalyzer analyze data/rice_chicken_broccoli.png --offline --no-storage
```

Output:

```text
ingredient              g    kcal  protein  carbs  fat  status
--------------------------------------------------------------
white rice (cooked)     180  234   4.9      50.4   0.5  ok
grilled chicken breast  150  248   46.5     0.0    5.4  ok
broccoli                80   27    2.2      5.6    0.3  ok
--------------------------------------------------------------
TOTAL                   410  509   53.6     56.0   6.3  ok
```
