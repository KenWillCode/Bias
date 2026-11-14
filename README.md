# Bias
Bias in Occupational and Gender Word Embeddings


Project description & goals:
-----------------------------
The goal of this project is to scrape the U.S. Bureau of Labor Statistics website, specifically using their HTML table for
the Labor Force Statistics from the Current Population Survey data table and compare the percentages of women in occupations
listed against similar words associated with a known gendered word to plot the data in different visualizations.

The revised script, `bias2.py`, extends this to every population in the BLS table. For women, men, Black, Asian and
Hispanic or Latino workers, it compares each group's real share of an occupation with how strongly the occupation's
words lean toward that group in the Google News word2vec embedding.


Files:
------
| File | What it is |
|---|---|
| `bias.py` | The original 2021 project, unchanged. |
| `bias2.py` | Corrected and extended version: all populations, interactive dashboard. |
| `CHANGES.md` | Every change from `bias.py` to `bias2.py` and the reason for it. |
| `run_bias_original.py` | Runs the unchanged `bias.py` with workarounds for problems that now stop it. |
| `fetch_bls.py` | Downloads the BLS page as `occupations.html`. |
| `occupations.html` | Saved copy of the BLS table (2025 annual averages), so the project runs without downloading. |
| `requirements.txt` | Python packages (use Python 3.11). |


Project inputs & expected outputs:
----------------------------------
Inputs: https://www.bls.gov/cps/cpsaat11.htm (saved copy included as `occupations.html`) and the Google News word2vec
model (`word2vec-google-news-300`, about 1.6 GB, downloaded automatically on first run).

Outputs of `bias2.py` (in `output/`):

* `dashboard.html`: an interactive page. Hover any dot to see the occupation or word, zoom in, and switch population from the menu.
* 8 PNG figures (matplotlib, WordCloud, seaborn), the 5 original visualizations among them.
* `correlations.csv`, `occupation_lean.csv`, `word_similarities.csv`, and `Labor_Force.xlsx` (the BLS table).


Instructions for installing required libraries:
-----------------------------------------------
```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
```


Instructions for executing the project:
---------------------------------------
```bash
.venv/bin/python bias2.py --open      # revised version; opens the dashboard when done
.venv/bin/python bias2.py --show      # also open matplotlib windows (zoom/pan), like the original
.venv/bin/python run_bias_original.py # the original bias.py
```

The first run downloads the word2vec model (about 1.6 GB), so it needs roughly 5 GB of free disk space and memory.

To refresh the BLS data: BLS blocks automated downloads that don't include contact information
([BLS robot policy](https://www.bls.gov/bls/pss.htm)), so pass your email:
```bash
.venv/bin/python fetch_bls.py --contact you@example.com --force
```
Or save the page from a browser as `occupations.html`.
