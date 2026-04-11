# Performance Analysis of Buffer Management and B+ Tree Indexing in a Simulated Database System
## B561: Advanced Database Concepts (SP-26)


# Student Guide

## 1. Overview

This is the student version of the project. Students are expected to complete specific components only, while the rest of the repository is provided so the system can run consistently during testing, benchmarking, and grading.

## 2. Files You SHOULD Modify

Focus your work on these files:

- `./src/buffer_pool_manager.py`
- `./src/replacement.py` 
- `./src/bplustree.py` (core logic improvements)

## 3. Files You MUST NOT Modify

Do not modify these files:

- `./src/disk_manager.py`
- `./src/models.py`
- `./src/simulator.py`
- `./src/benchmark.py`
- `./src/plot_results.py`

`./src/simulator.py` is fully implemented by the instructor and is part of the grading pipeline. Modifying it may break evaluation.

## 4. Understanding Code Markers

`[STUDENT TODO]`

- These markers show the places where student implementation work is expected.
- These sections define the intended assignment boundary.

`[INSTRUCTOR ONLY]`

- These markers identify protected code that should remain unchanged.
- These sections usually contain shared infrastructure or grading-sensitive logic.

## 5. How to Run the Project

```bash
python -m src.main
```

## 6. How to Run Tests

```bash
pytest ./tests/
```

The public test suite is shared with the instructor reference. Before the TODO
sections are implemented, it is expected that tests covering replacement
policies, buffer pool behavior, B+ tree behavior, integration, and benchmark
execution will fail in `DBMS_Project`.

## 7. How to Run Benchmarks

```bash
python -m src.benchmark
```

The benchmark script runs the instructor-provided simulation pipeline across small workload and buffer-size sweeps.

## 8. Where Results Are Stored

- `results/benchmark_results.csv`
- `results/plots/`

## 9. Important Notes

- Do not change function signatures.
- Do not modify instructor-only files.
- Only TODO sections will be evaluated.
