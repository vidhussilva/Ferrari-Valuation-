"""Python companion to the Ferrari N.V. Excel valuation model.

- excel_io:    read inputs (by row label) and calculated outputs from the workbook
- engine:      independent pandas / NumPy re-implementation of the three statements and DCF
- sensitivity: automated scenario, WACC x g, tornado and growth x margin analysis
- reconcile:   line-by-line comparison of Python vs Excel outputs
- libreoffice: headless recalculation so the workbook can be re-scored without Excel
"""
