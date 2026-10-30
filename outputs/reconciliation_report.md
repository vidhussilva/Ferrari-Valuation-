# Excel vs Python reconciliation

Workbook: `model/Ferrari_Valuation_Model.xlsx`  
Tolerance: |Excel - Python| <= 1e-06 x max(1, |Excel|)

| Scenario | Area | Items compared | Max abs. difference | Result |
|---|---|---:|---:|---|
| Bear | Revenue build | 10 | 5.09e-11 | PASS |
| Bear | Income statement | 70 | 5.00e-12 | PASS |
| Bear | Balance sheet | 70 | 4.00e-11 | PASS |
| Bear | Cash flow | 50 | 3.64e-12 | PASS |
| Bear | DCF | 30 | 4.55e-12 | PASS |
| Bear | WACC | 4 | 2.78e-17 | PASS |
| Bear | Valuation | 8 | 3.64e-11 | PASS |
| Bear | Sensitivity grid | 126 | 5.09e-11 | PASS |
| Base | Revenue build | 10 | 4.37e-11 | PASS |
| Base | Income statement | 70 | 2.91e-11 | PASS |
| Base | Balance sheet | 70 | 3.64e-11 | PASS |
| Base | Cash flow | 50 | 5.00e-12 | PASS |
| Base | DCF | 30 | 5.00e-12 | PASS |
| Base | WACC | 4 | 2.78e-17 | PASS |
| Base | Valuation | 8 | 5.09e-11 | PASS |
| Base | Sensitivity grid | 126 | 2.91e-10 | PASS |
| Bull | Revenue build | 10 | 4.73e-11 | PASS |
| Bull | Income statement | 70 | 4.37e-11 | PASS |
| Bull | Balance sheet | 70 | 4.73e-11 | PASS |
| Bull | Cash flow | 50 | 5.00e-12 | PASS |
| Bull | DCF | 30 | 4.55e-12 | PASS |
| Bull | WACC | 4 | 2.78e-17 | PASS |
| Bull | Valuation | 8 | 2.91e-11 | PASS |
| Bull | Sensitivity grid | 126 | 4.95e-10 | PASS |

## Key valuation outputs

| Scenario | Output | Excel | Python | Difference |
|---|---|---:|---:|---:|
| Bear | wacc | 6.6781% | 6.6781% | 2.78e-17 |
| Bear | enterprise_value | 37,694.3077 | 37,694.3077 | 1.46e-11 |
| Bear | equity_value | 37,662.3077 | 37,662.3077 | 1.46e-11 |
| Bear | value_per_share | 212.4467 | 212.4467 | 4.26e-13 |
| Bear | upside | -32.4535% | -32.4535% | 3.89e-16 |
| Base | wacc | 6.6781% | 6.6781% | 2.78e-17 |
| Base | enterprise_value | 51,375.4904 | 51,375.4904 | 2.91e-11 |
| Base | equity_value | 51,343.4904 | 51,343.4904 | 2.91e-11 |
| Base | value_per_share | 289.6199 | 289.6199 | 5.12e-13 |
| Base | upside | -7.9166% | -7.9166% | 4.58e-16 |
| Bull | wacc | 6.6781% | 6.6781% | 2.78e-17 |
| Bull | enterprise_value | 63,979.4161 | 63,979.4161 | 0.00e+00 |
| Bull | equity_value | 63,947.4161 | 63,947.4161 | 0.00e+00 |
| Bull | value_per_share | 360.7165 | 360.7165 | 4.55e-13 |
| Bull | upside | 14.6882% | 14.6882% | 2.78e-16 |

**ALL ITEMS RECONCILE** (1,104 comparisons). Full detail: `reconciliation_detail.csv`.
