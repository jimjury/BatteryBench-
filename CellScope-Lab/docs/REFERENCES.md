# Upstream study and source attribution (2026-11-08)

CellScope Lab was designed with **conceptual inspiration** from the following publicly described projects. It does **not** copy or incorporate their original model/data-processing source files. The MIT license on the two primary reference repos permits reuse under attribution, but we deliberately implemented an independent architecture instead.

| Project | What was inspected / why relevant | License observation |
|---|---|---|
| [LMDHQ-0420/BatteryBench](https://github.com/LMDHQ-0420/BatteryBench) | README, task shapes, battery-level splits, Four-Level design, model inventory, preprocessing folder | MIT, copyright LMDHQ-0420 (2026) |
| [Ruifeng-Tan/BatteryLife](https://github.com/Ruifeng-Tan/BatteryLife) | README, standardized data description, preprocessing/training and model folders, version news | MIT, copyright Ruifeng Tan (2025) |
| [microsoft/BatteryML](https://github.com/microsoft/BatteryML) | Reference for extensible data/method interfaces and reproducibility; GitHub indicated archived at inspection | Check its LICENSE if reusing anything |
| [TRI-AMDD/beep](https://github.com/TRI-AMDD/beep) | Related battery experimental ETL and feature engineering ecosystem | Check upstream license |
| [pybamm-team/PyBaMM](https://github.com/pybamm-team/PyBaMM) | Physics-based battery models and simulation ecosystem, **not integrated** | BSD-3-Clause per upstream repository |
| [tum-ees/BatteryDashboard](https://github.com/tum-ees/BatteryDashboard) | Example of health monitoring and operational visualizations, **not integrated** | Check upstream license |

Data catalog entries link to source archives including MATR, HUST, CALCE, RWTH, XJTU, Stanford, Tongji, SDU, BatteryArchive, CALB/Na-ion/Zn-ion, and Farasis. External datasets are **not** included. The catalog is an orientation guide; download availability, license conditions, metadata, citation details and task suitability have not been exhaustively audited. Authors must cite *each original experimental source* when publishing results, as well as relevant benchmark papers when using their protocols.

### Scientific provenance pitfalls

- Do not assume a BatteryLife versioned processed dataset is identical to a BatteryBench preprocessing recipe; resampling, feature channels, SOH/EOL labels and held-out domains can differ.
- Do not compare numbers from different label scales, window alignment, split granularity, training-data access or test-time tuning as if they were a unified leaderboard.
- No copyrighted figures, graphics, logos, datasets, or weights from these repos have been embedded into the CellScope Lab website.
- CellScope Lab's procedural network diagram and UI are new illustrations.

No endorsement by the upstream authors is implied.
