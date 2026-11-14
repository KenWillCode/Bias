# Changes from `bias.py` to `bias2.py`

`bias.py` has not been changed. `bias2.py` is a corrected rewrite with the same goal: compare how many women work in each occupation (BLS data) with how strongly each occupation word leans toward "she" or "he" in the Google News word2vec model.

This file lists every change and why it was made. Line numbers refer to `bias.py`.

---

## How to run

From the repository folder, with the virtual environment from the README:

```bash
# 1. The BLS page is included as occupations.html. To refresh it
#    (BLS only allows automated downloads that include a contact email):
.venv/bin/python fetch_bls.py --contact you@example.com --force
#    ...or save it from your browser as occupations.html
#    (Chrome: Save Page As > "Webpage, HTML Only"; Safari: Save As > "Page Source")

# 2. Revised script (dashboard, figures and CSVs go to output/)
.venv/bin/python bias2.py --open

# Original script, unmodified, with the workarounds applied from outside
.venv/bin/python run_bias_original.py
```

`bias2.py --contact you@example.com` and `run_bias_original.py --contact you@example.com` also download the page themselves if it is missing. Setting the `BLS_CONTACT` environment variable works too.

Useful `bias2.py` options:

| Option | Meaning |
|---|---|
| `--subset last20` | Analyze only the last 20% of occupations. This is what `bias.py` did. |
| `--subset first80` | Analyze only the first 80%. This is the commented-out option in `bias.py`. |
| `--open` | Open the interactive dashboard (`output/dashboard.html`) in your browser when the run finishes. |
| `--show` | Also open matplotlib plot windows (zoom and pan) at the end. Without it, figures are only saved. |
| `--max-labels N` | Label at most N points on each scatter plot. The default is 60. |
| `--model NAME` | Use a different gensim-data model, such as `glove-wiki-gigaword-100`, which is a much smaller download. |

---

## Problems that stopped the original from running

| # | Where in `bias.py` | Problem | Fix in `bias2.py` |
|---|---|---|---|
| 1 | `getDataframe`, lines 79–89 | BLS now returns **403 Forbidden** to scripts. Its [robot policy](https://www.bls.gov/bls/pss.htm) says it may block automated programs that don't include a way to contact their owner, and `requests` sends none. The original also saves the error page as `occupations.html` without checking the status code. That bad file is reused on every later run, so the script keeps failing even after the cause is fixed. | `download_bls_page` (also available as the standalone `fetch_bls.py`) sends a User-Agent that names the script and includes the contact email you pass with `--contact`, plus the standard `From` header. It saves the page only when the response is HTTP 200 and contains the data table. It downloads only when no good saved copy exists, so BLS is contacted at most once. If BLS still refuses, the script stops and explains how to save the page from a browser. |
| 2 | Lines 416–422, 446–452, 477–483 | `sns.scatterplot(..., color=['red','orange'])`: a single scatter series can only have one color, so matplotlib raises `ValueError` on the first scatter plot. | Each plot uses one color. The man-vs-woman plot is colored by the she−he difference instead. |
| 3 | Lines 396, 405, 416, 446, 477 | `x` and `y` are passed to seaborn positionally. seaborn 0.12 and later reject this, which forced the old seaborn 0.11.2, which in turn forced pandas 1.x, matplotlib < 3.9 and Python 3.11. | Every seaborn call uses `data=`, `x=` and `y=` keywords. This works with seaborn 0.11 and with current versions. |

`run_bias_original.py` works around #1 and #2 without editing `bias.py`. It refuses to start until a real `occupations.html` is present, and it wraps `seaborn.scatterplot` so a list of colors becomes its first color.

---

## Wrong results (the script ran but the output was misleading)

| # | Where | Problem | Fix |
|---|---|---|---|
| 4 | Lines 106–131 | The table is rebuilt by position. The code takes every `<th>` after the 9th as an occupation and slices all `<td>` cells into groups of 6 (`[0::6]`, `[1::6]`, ...). One missing or extra cell, or a header change on the BLS page, shifts every later value into the wrong column or occupation without any error. | `parse_bls_table` reads the page row by row. In each `<tr>`, the `<th>` is the occupation and the next 6 `<td>` cells are its numbers. A row can only ever affect itself. |
| 5 | Lines 120–121 | Empty cells are removed from the list before slicing, which shifts the remaining values by position (same failure as #4). | Fixed by the row-by-row parsing. |
| 6 | Lines 123–124 and 190 | Values BLS shows as "–" ("does not meet publication standards") become `0`. In the 2025 table, 199 of the 595 occupations have no published percentages. The original reports all 199 as 0% women (alongside the 2 that really are 0%), which drags down every average and fills the bar chart with false zeros. | These values are kept as missing (NaN): blank in Excel and skipped in calculations. `report_missing` prints how many there are per column. |
| 7 | Lines 157–159 | The `Men` column is labeled as if it were a count of men, but it holds a percentage. | `Men` is defined as `100 − Women` (a percentage). `Total Employed Women` is labeled as thousands. |
| 8 | Lines 266–270 | `Difference` is the absolute value of she − he, so it no longer says which way a word leans. "nurse" and "carpenter" can get the same score. | `Difference = sim('she', w) − sim('he', w)`: positive leans female, negative leans male. `Abs_Difference` keeps the old measure. |
| 9 | Lines 252–256 | The analogy result is stored as `job_sims[answer] = score`, keyed by the answer word. When two jobs give the same answer, one overwrites the other, and the dictionary was never used afterward anyway. | `She_Analogy` and `She_Analogy_Score` are stored on each word's row in the results table. |
| 10 | Lines 377–385 | The bar chart's y-axis labels are the men's percentages instead of occupation names, the x-axis is labeled "x", and it plots more than 500 bars, which can't be read (the code comment admits this). | A stacked bar chart of women % and men % for the 20 most male- and 20 most female-dominated occupations, labeled with occupation names and a 50% line. |
| 11 | Line 486 | The third scatter plot writes its labels with `p2.text(...)`, so the labels land on the previous figure, not the man-vs-woman plot. | Labels are written on the plot being drawn. |
| 12 | Lines 360–364 | The tokenizing loop is indented wrong, so it only processes the last sentence, and its result (`data`) is never used. | Removed. The word cloud is built directly from the occupation titles. |
| 13 | Lines 367–370 | The word cloud is drawn but never saved, and the figure background is set to black. | Saved as `output/Occupation Word Cloud.png`. |
| 14 | Lines 557–563 | Punctuation is deleted from inside words, so "first-line" becomes "firstline" and "and/or" becomes "andor". These merged words aren't in word2vec and get dropped. | Titles are split on anything that isn't a letter, so "first-line" becomes "first" and "line", and both are looked up. |
| 15 | Line 553 | `corpus1[1:]` drops the first occupation of the 80% subset without explanation. | No rows are silently dropped. |

---

## The project's main question was never tested

The stated goal is to compare the percentage of women in each occupation with the gender lean of its words. `bias.py` computes both but never puts them side by side: none of its plots uses the BLS percentages together with the similarity scores. It also scrapes the Men, White, Black, Asian and Hispanic or Latino columns but never uses them.

`bias2.py` makes this comparison for every population in the table.

### Word groups instead of single words

`bias.py` defines `woman_words` and `man_words` (20 words each, from Garg et al. 2018) but never uses them. Every measurement uses only "she" and "he". `bias2.py` uses the lists, with the typo "femen" corrected to "females".

* Each population is represented by a group of words. The group's **centroid** is the average of the words' unit vectors.
* A word's **lean** toward a population is `cos(word, group centroid) − cos(word, comparison-group centroid)`.
* Averaging 20 words is much steadier than one word. "he" and "she" alone also pick up grammar, such as how often a word follows a pronoun in news sentences.
* The original she/he `Difference` is still computed, so the original figures can be reproduced.

| Population | BLS column | Group words | Compared with | Source of the method |
|---|---|---|---|---|
| Women | Women | 20 female words | 20 male words | Garg et al. 2018 (your original lists) |
| Men | Men (100 − Women) | 20 male words | 20 female words | Same lists, the other direction |
| Black | Black or African American | 18 Black first names | 18 White first names | Bertrand & Mullainathan 2004 résumé study, used for embeddings by Caliskan et al. 2017 |
| Asian | Asian | 21 Asian surnames | 18 White surnames | Garg et al. 2018 surname method |
| Hispanic | Hispanic or Latino | 23 Hispanic surnames | 18 White surnames | Garg et al. 2018 surname method |

Why the word groups were chosen this way:

* **Surnames** are common U.S. surnames held overwhelmingly by one group in Census surname data, following Garg et al. Names that are also everyday words or common first names, such as Park, Sun, Le, Young and Scott, are left out because their vectors mostly reflect the other meaning.
* **Black Americans are measured with first names, not surnames.** The most distinctive Black surnames (Washington, Jefferson, Booker, Banks) are dominated by their meanings as places and words in news text. Garg et al. leave this group out for the same reason. The first names come from the well-known résumé field experiment and have been used in embedding-bias research before.
* **Google News vectors are case-sensitive**, so each name is looked up as written, then capitalized ("Garcia", "Jamal"). Missing names are reported when the script runs.

### Comparing with BLS

* **`occupation_lean`** scores each occupation by averaging the lean of the words in its title. For example, "Registered nurses" gets the mean of "registered" and "nurses".
* **`correlation_table`** gives, for each population, the Pearson and Spearman correlation between the group's real share of an occupation and the occupation's lean toward the group.
* **Filler words** that appear in hundreds of titles but say nothing about the job ("occupations", "workers", "related", "other", "miscellaneous", "except", "first-line", ...) are no longer scored. Before, they pulled every occupation's score toward neutral.
* **New figure:** `Population Share vs. Embedding Lean.png` has one panel per population, each with a regression line and r.
* **New CSVs:** `word_similarities.csv` (one row per word, with every lean), `occupation_lean.csv` (one row per occupation, with BLS shares and leans) and `correlations.csv`.

---

## Interactive output

`bias.py` was interactive only through `plt.show()` windows (zoom and pan, no hover). The windows blocked the script, and the scatter plots had hundreds of overlapping labels. `bias2.py` keeps that option and adds a dashboard:

* **`output/dashboard.html`**, built with Plotly, opens in any browser. Hovering any dot shows the occupation or word, its numbers and the words used. Drag to zoom, and switch population from the menu. It contains:
  1. A summary table of correlations for every population.
  2. Share vs. lean per occupation (dot size = number employed), with a population menu.
  3. The words leaning most toward each group and toward its comparison group.
  4. Every occupation word plotted by similarity to "she" vs. "he", with the analogy result on hover. This replaces the overlapping labels.
  5. All occupations with published data, sorted from most male to most female.
* **`--open`** opens the dashboard when the run finishes.
* **`--show`** opens matplotlib windows with zoom and pan, like the original.

---

## Speed, resource use and cleanup

| # | Where | Problem | Fix |
|---|---|---|---|
| 16 | Lines 272, 304, 550, 596 and the `time.sleep(3)` calls in `main` | Built-in delays: 0.5 s per word and 0.03 s per occupation, plus 3 s pauses. On the full data this adds several minutes of waiting. | Removed. |
| 17 | Lines 546 and 592 | `stopwords.words()` with no language loads stop words for every language (about 11,000 words) and is called again for every token. It is slow, and it also removes English words that happen to be stop words in other languages. The English set built on lines 533 and 579 is never used. | Uses the English stop word set, loaded once. |
| 18 | Lines 242–305 | `similarityFunc` contains two identical 30-line blocks that differ only in a hard-coded number of expected missing words (4 or 7) for the progress bar. With current BLS data those numbers are wrong, so the bar shows warnings like "7/1 [700%]". | One loop, and the progress bar total is the real number of words. |
| 19 | Lines 539 and 585 | Progress bar totals are hard-coded (476 and 119), which no longer match the current BLS table. | Totals are computed from the data. |
| 20 | Lines 526–531 and 572–577 | The occupation column is extracted by deleting column 1 eight times from a NumPy array. | `df["Occupations"]`. |
| 21 | Lines 541–551 | A `while` loop wraps a `for` loop that already does all the work. | Removed. |
| 22 | Lines 351–357 | Writes `jobs_file.txt` only to read it straight back, without closing the file it reads. | The text is joined in memory. |
| 23 | Lines 474 and 505 | `plt.show()` in the middle of `model()` blocks the script until each window is closed, and figures are never closed, so memory grows. | Figures are saved and closed. Windows open only with `--show`. |
| 24 | Line 348 | `print(df2.describe)` prints the method itself, not the summary. | `print(sims.describe())`. |
| 25 | Lines 29, 31, 35, 43–45, 47–49 | Unused imports, including `RPA.Tables`, which brings in the whole `rpaframework` package (more than 100 dependencies) and is never used. `gensim` and `nltk` are each imported twice. | Only what is used is imported. Heavy libraries are imported inside the functions that need them. |
| 26 | Line 193 | The output file is named `Labor_Force_2020.xlsx` whatever year the BLS data is from, and it includes the pandas index as an extra column. | Saved as `Labor_Force.xlsx` without the index column. |
| 27 | Whole file | Tabs mixed with very long lines, no command-line options, and the 80/20 subset can only be changed by editing the code (line 618). | 4-space indentation (PEP 8), functions grouped by step, `argparse` options, and `--subset` replaces the comment-out switch. |
| 28 | Lines 222–223 | Each call to `similarityFunc` loads the 1.6 GB model. | The model is loaded once in `main` and passed in, so `run()` can also be tested with small stand-in vectors. |

---

## Things that stayed the same

* The data source (BLS `cpsaat11`) and the Google News word2vec model `word2vec-google-news-300`.
* The "she" and "he" similarity measures and the "he : job :: she : ?" analogy.
* The same 5 figure types with the same file names, plus the word cloud (which `bias.py` never saved), the new population figure and the dashboard.
* `--subset last20` reproduces the original choice of analyzing only the last 20% of occupations. The default is now all occupations.

## Known limitations

* Some BLS rows are totals or group headings, such as "Total, 16 years and over" and "Management, professional, and related occupations". Both scripts treat them like any other occupation.
* An occupation's score is a plain average of its title words. Common filler words are skipped, but every remaining word counts equally.
* Cosine similarity in one model trained on news text from about 2013 measures how words were used in that text, not anything about the people in those jobs.
* Names carry other associations in news, such as countries, celebrities and politics ("Kim", "Patel", "Singh"). This makes the race/ethnicity measures noisier than the gender measure.
* BLS counts Hispanic or Latino as an ethnicity that overlaps the race columns. The race columns are percentages of all workers in the occupation.
* White is used as the comparison group for the race/ethnicity measures rather than analyzed as a population of its own.
