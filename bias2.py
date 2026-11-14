"""
Course:        DCS 211 Winter 2021 Module D
Assignment:    Final Project (revised: bias2.py)
Topic:         Occupation Labor Statistics vs. Gendered and Ethnic Word Similarity

Purpose:       Scrape the U.S. Bureau of Labor Statistics (BLS) table "Employed
               persons by detailed occupation, sex, race, and Hispanic or Latino
               ethnicity" and compare, for every population in that table, the
               real share of workers in each occupation with how strongly the
               occupation's words lean toward that population in the Google News
               word2vec embedding.

               Populations compared (BLS column -> embedding word groups):
                 Women    -> 20 female words vs. 20 male words
                 Men      -> 20 male words vs. 20 female words
                 Black    -> Black vs. White first names
                 Asian    -> Asian vs. White surnames
                 Hispanic -> Hispanic vs. White surnames

               This is a corrected and extended rewrite of bias.py. Every change
               and the reason for it is documented in CHANGES.md.

Student Name: Kendall Williams

Citations/links of external references used:
https://dev.to/coderasha/compare-documents-similarity-using-python-nlp-4odp
https://www.pnas.org/content/115/16/E3635   (Garg et al. 2018: word lists, method)
Bertrand & Mullainathan (2004), "Are Emily and Greg More Employable than Lakisha
    and Jamal?", American Economic Review 94(4)  (first-name lists)
https://www.bls.gov/bls/pss.htm             (BLS policy on automated downloads)
https://stackoverflow.com/

Usage:
    python bias2.py                          # all occupations, dashboard + PNGs
    python bias2.py --open                   # also open the dashboard in a browser
    python bias2.py --show                   # also open matplotlib plot windows
    python bias2.py --subset last20          # reproduce bias.py (last 20% only)
    python bias2.py --contact you@example.com --refresh   # re-download from BLS
    python bias2.py --help
"""
import argparse
import os
import re
import webbrowser
from dataclasses import dataclass, field

import matplotlib
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

BLS_URL = "https://www.bls.gov/cps/cpsaat11.htm"
HTML_FILE = "occupations.html"
EXCEL_FILE = "Labor_Force.xlsx"
DEFAULT_MODEL = "word2vec-google-news-300"   # ~1.6 GB download on first use

# Numeric columns of the BLS table, in the order they appear after the
# occupation name. "Total Employed" is in thousands; the rest are percents.
BLS_COLUMNS = [
    "Total Employed",
    "Women",
    "White",
    "Black or African American",
    "Asian",
    "Hispanic or Latino",
]

################################################################################
# Word groups
#
# Each population is represented by a list of words. A group's "centroid" is
# the average of its words' unit vectors. An occupation word's lean toward a
# population is
#       cos(word, centroid of group) - cos(word, centroid of comparison group)
# Averaging many words is much steadier than comparing with one word ("she").
################################################################################

# Gendered words: the lists from the original bias.py, which come from Garg et
# al. (2018). The original typo "femen" is corrected to "females".
WOMAN_WORDS = [
    "she", "daughter", "hers", "her", "mother", "woman", "girl", "herself",
    "female", "sister", "daughters", "mothers", "women", "girls", "females",
    "sisters", "aunt", "aunts", "niece", "nieces",
]
MAN_WORDS = [
    "he", "son", "his", "him", "father", "man", "boy", "himself", "male",
    "brother", "sons", "fathers", "men", "boys", "males", "brothers", "uncle",
    "uncles", "nephew", "nephews",
]

# Surnames, following the method of Garg et al. (2018): common U.S. surnames
# held overwhelmingly by one group in Census surname data. Names that are also
# everyday words or common first names (Park, Sun, Le, Young, Scott, ...) are
# left out because their vectors mostly reflect the other meaning.
WHITE_SURNAMES = [
    "olson", "schmidt", "meyer", "snyder", "hansen", "larson", "schultz",
    "mueller", "becker", "erickson", "yoder", "novak", "kowalski", "schneider",
    "weber", "hoffman", "sullivan", "mccarthy",
]
HISPANIC_SURNAMES = [
    "garcia", "rodriguez", "martinez", "hernandez", "lopez", "gonzalez",
    "perez", "sanchez", "ramirez", "torres", "flores", "rivera", "gomez",
    "diaz", "morales", "gutierrez", "ortiz", "chavez", "ruiz", "alvarez",
    "mendoza", "castillo", "vasquez",
]
ASIAN_SURNAMES = [
    "nguyen", "tran", "pham", "huynh", "vu", "chen", "wang", "zhang", "liu",
    "huang", "wu", "zhou", "xu", "patel", "kim", "choi", "cho", "tanaka",
    "nakamura", "yamamoto", "singh",
]

# First names from Bertrand & Mullainathan (2004), the resume field experiment
# also used by Caliskan et al. (2017) to measure race bias in embeddings.
# Black surnames are not used: the most distinctive ones (Washington, Jefferson,
# Booker, Banks) are dominated by their meanings as places and words in news.
WHITE_FIRST_NAMES = [
    "allison", "anne", "carrie", "emily", "jill", "laurie", "kristen",
    "meredith", "sarah", "brad", "brendan", "geoffrey", "greg", "brett",
    "jay", "matthew", "neil", "todd",
]
BLACK_FIRST_NAMES = [
    "aisha", "ebony", "keisha", "kenya", "lakisha", "latonya", "latoya",
    "tamika", "tanisha", "darnell", "hakim", "jamal", "jermaine", "kareem",
    "leroy", "rasheed", "tremayne", "tyrone",
]


@dataclass
class Comparison:
    """One population from the BLS table and the word groups that stand for it."""
    key: str             # short name, also used in column names
    bls_column: str      # BLS percent column for this population
    words: list          # words/names representing the population
    baseline: list       # words/names of the comparison group
    baseline_name: str
    method: str
    color: str
    found: list = field(default_factory=list)          # filled by prepare_comparisons
    missing: list = field(default_factory=list)
    baseline_found: list = field(default_factory=list)

    @property
    def lean_column(self):
        return f"Lean_{self.key}"


COMPARISONS = [
    Comparison("Women", "Women", WOMAN_WORDS, MAN_WORDS, "Men",
               "20 female vs. 20 male words (Garg et al. 2018)", "#1f77b4"),
    Comparison("Men", "Men", MAN_WORDS, WOMAN_WORDS, "Women",
               "20 male vs. 20 female words (Garg et al. 2018)", "#ff7f0e"),
    Comparison("Black", "Black or African American", BLACK_FIRST_NAMES,
               WHITE_FIRST_NAMES, "White",
               "Black vs. White first names (Bertrand & Mullainathan 2004)", "#2ca02c"),
    Comparison("Asian", "Asian", ASIAN_SURNAMES, WHITE_SURNAMES, "White",
               "Asian vs. White surnames (Garg et al. 2018 method)", "#d62728"),
    Comparison("Hispanic", "Hispanic or Latino", HISPANIC_SURNAMES,
               WHITE_SURNAMES, "White",
               "Hispanic vs. White surnames (Garg et al. 2018 method)", "#9467bd"),
]

# Words that appear in many occupation titles but say nothing about the job.
# They are skipped so they do not pull every occupation's score toward neutral.
TITLE_FILLER_WORDS = {
    "occupations", "occupation", "workers", "worker", "related", "other",
    "miscellaneous", "except", "including", "total", "years", "nec", "first",
    "line", "all",
}


################################################################################
# 1. Labor statistics
################################################################################
def download_bls_page(url=BLS_URL, fname=HTML_FILE, contact=None):
    """
    Download the BLS page once and save it as fname.

    BLS's robot policy (https://www.bls.gov/bls/pss.htm) says it blocks
    automated programs that do not include information that can be used to
    contact their owner, so the request's User-Agent names this script and a
    contact email. Without one, BLS answers "403 Forbidden".

    Only an HTTP 200 response that contains the data table is saved, so an
    error page can never be mistaken for the data later.
    """
    contact = contact or os.environ.get("BLS_CONTACT")
    if not contact:
        raise SystemExit(
            "BLS only allows automated downloads that include contact information.\n"
            "Pass your email:  --contact you@example.com   (or set BLS_CONTACT)\n"
            "or save the page from your browser instead:\n"
            f"  {url}\n"
            "  Chrome: File > Save Page As > 'Webpage, HTML Only'\n"
            "  Safari: File > Save As > Format 'Page Source'\n"
            f"  as '{os.path.abspath(fname)}'"
        )
    user_agent = f"bias2.py/2.0 (educational research project; contact: {contact})"
    print(f"Downloading {url} ...")
    response = requests.get(url, timeout=30, headers={
        "User-Agent": user_agent,
        "From": contact,                 # standard HTTP header for a contact email
        "Accept": "text/html",
    })
    if response.status_code != 200 or b'class="regular"' not in response.content:
        raise SystemExit(
            f"BLS refused the download (HTTP {response.status_code}). "
            f"Save the page from your browser as '{os.path.abspath(fname)}' instead."
        )
    with open(fname, "wb") as outfile:
        outfile.write(response.content)
    print(f"Saved {fname} ({len(response.content) / 1024:.0f} KB)")
    return response.content


def load_html(url=BLS_URL, fname=HTML_FILE, contact=None, refresh=False):
    """
    Return the BLS page HTML. A saved copy is used when it exists, so BLS is
    contacted at most once (or again only with refresh=True).
    """
    if os.path.exists(fname) and not refresh:
        with open(fname, "rb") as infile:
            content = infile.read()
        if b'class="regular"' in content:
            return content
        print(f"'{fname}' does not contain the BLS table; downloading again.")
    return download_bls_page(url, fname, contact)


def parse_bls_table(content):
    """
    Turn the BLS HTML table into a DataFrame.

    Each data row is read as one unit: its <th> is the occupation and its
    first six <td> cells are the numbers. Cells shown as "–" (data does not
    meet BLS publication standards) become NaN rather than 0.
    """
    soup = BeautifulSoup(content, "html.parser")
    table = soup.find("table", attrs={"class": "regular"})
    if table is None:
        raise ValueError("No <table class='regular'> found in the HTML.")

    body = table.find("tbody") or table
    records = []
    for tr in body.find_all("tr"):
        header = tr.find("th")
        cells = tr.find_all("td")
        if header is None or len(cells) < len(BLS_COLUMNS):
            continue   # title rows, footnotes, spacer rows
        occupation = header.get_text(" ", strip=True)
        values = [td.get_text(strip=True) for td in cells[:len(BLS_COLUMNS)]]
        if not occupation or all(v == "" for v in values):
            continue
        records.append([occupation] + values)

    df = pd.DataFrame(records, columns=["Occupations"] + BLS_COLUMNS)
    for col in BLS_COLUMNS:
        df[col] = pd.to_numeric(
            df[col].str.replace(",", "", regex=False), errors="coerce")
    return df


def add_gender_columns(df):
    """Add the number of women employed (thousands) and the percent of men."""
    df = df.copy()
    df["Total Employed Women"] = (df["Women"] / 100 * df["Total Employed"]).round(1)
    df["Men"] = (100 - df["Women"]).round(1)
    order = ["Occupations", "Total Employed", "Women", "Total Employed Women",
             "Men", "White", "Black or African American", "Asian",
             "Hispanic or Latino"]
    return df[order]


def report_missing(df):
    """Print how many values BLS did not publish, per column."""
    rows, cols = df.shape
    nulls = int(df.isnull().sum().sum())
    print("***" * 20)
    print(f"Rows x Cols = {rows} x {cols} | cells = {rows * cols}")
    print(f"Values not published by BLS (kept as blank/NaN): {nulls} "
          f"({nulls / (rows * cols) * 100:.2f}%)")
    print(df.isnull().sum()[lambda s: s > 0].to_string())
    print("***" * 20)


def get_dataframe(url=BLS_URL, fname=HTML_FILE, excel_file=EXCEL_FILE,
                  contact=None, refresh=False):
    """Download/parse the BLS table, add gender columns and save it to Excel."""
    df = add_gender_columns(parse_bls_table(load_html(url, fname, contact, refresh)))
    print(df.dtypes)
    report_missing(df)
    print(df.describe())
    df.to_excel(excel_file, index=False)
    print(f"Saved table to {excel_file}")
    return df


################################################################################
# 2. Occupation vocabulary
################################################################################
def occupation_words(occupation, stop_words):
    """Lower-case content words in one occupation title."""
    # Splitting on anything that is not a letter also splits "first-line" and
    # "and/or" into separate words instead of gluing them together.
    return [w for w in re.findall(r"[a-z]+", occupation.lower())
            if w not in stop_words and w not in TITLE_FILLER_WORDS and len(w) > 1]


def build_vocabulary(occupations, stop_words):
    """Unique occupation words, in first-seen order."""
    vocab = {}
    for occupation in occupations:
        for word in occupation_words(occupation, stop_words):
            vocab.setdefault(word, None)
    return list(vocab)


def select_subset(df, subset):
    """Pick which occupation rows to analyze ('all', 'first80' or 'last20')."""
    cut = int(0.8 * len(df))
    if subset == "first80":
        return df.iloc[:cut]
    if subset == "last20":
        return df.iloc[cut:]
    return df


def get_stop_words():
    """English stop words from NLTK, downloading the list if needed."""
    import nltk
    try:
        from nltk.corpus import stopwords
        return set(stopwords.words("english"))
    except LookupError:
        nltk.download("stopwords", quiet=True)
        from nltk.corpus import stopwords
        return set(stopwords.words("english"))


################################################################################
# 3. Word-embedding measurements
################################################################################
def load_word_vectors(name=DEFAULT_MODEL):
    """Load a gensim-data model (downloaded and cached on first use)."""
    import gensim.downloader as api
    print(f"Loading word vectors '{name}' "
          "(the Google News model is ~1.6 GB the first time)...")
    return api.load(name)


def resolve_words(words, word_vectors):
    """
    Map each word or name to the form the embedding knows. Google News vectors
    are case-sensitive, and names appear capitalized ("Garcia", "Jamal").
    Returns (found, missing).
    """
    found, missing = [], []
    for word in words:
        for candidate in (word, word.capitalize(), word.lower()):
            if candidate in word_vectors.key_to_index:
                found.append(candidate)
                break
        else:
            missing.append(word)
    return found, missing


def centroid(words, word_vectors):
    """Unit-length average of the words' unit vectors."""
    mean = np.mean([word_vectors.get_vector(w, norm=True) for w in words], axis=0)
    return mean / np.linalg.norm(mean)


def prepare_comparisons(word_vectors, comparisons=COMPARISONS):
    """Resolve each group's words in the embedding and report any missing."""
    for comp in comparisons:
        comp.found, comp.missing = resolve_words(comp.words, word_vectors)
        base_found, base_missing = resolve_words(comp.baseline, word_vectors)
        comp.baseline_found = base_found
        if len(comp.found) < 3 or len(base_found) < 3:
            raise ValueError(f"Too few {comp.key} words in the embedding.")
        note = f" (missing: {', '.join(comp.missing + base_missing)})" \
            if comp.missing or base_missing else ""
        print(f"  {comp.key:9s} {len(comp.found)} vs. {len(base_found)} "
              f"{comp.baseline_name} words found{note}")
    return comparisons


def similarity_table(words, word_vectors, comparisons=COMPARISONS):
    """
    One row per occupation word found in the embedding:
      Woman_Similarity_of_Job  cosine similarity to "she"
      Man_Similarity_of_Job    cosine similarity to "he"
      Difference               she minus he (positive = leans female)
      Abs_Difference           size of the she/he lean, ignoring direction
      Lean_<group>             cos(word, group centroid) - cos(word, baseline
                               centroid) for every comparison in COMPARISONS
      She_Analogy              top answer to  he : word :: she : ?
    Words missing from the embedding are listed and skipped.
    """
    from alive_progress import alive_bar

    present = [w for w in words if w in word_vectors.key_to_index]
    missing = [w for w in words if w not in word_vectors.key_to_index]
    if missing:
        print(f"{len(missing)} word(s) not in the embedding: {', '.join(missing)}")

    vectors = np.vstack([word_vectors.get_vector(w, norm=True) for w in present])
    she = vectors @ word_vectors.get_vector("she", norm=True)
    he = vectors @ word_vectors.get_vector("he", norm=True)
    table = pd.DataFrame({
        "Job_Words": present,
        "Woman_Similarity_of_Job": she,
        "Man_Similarity_of_Job": he,
        "Difference": she - he,
        "Abs_Difference": np.abs(she - he),
    })
    for comp in comparisons:
        table[comp.lean_column] = (
            vectors @ centroid(comp.found, word_vectors)
            - vectors @ centroid(comp.baseline_found, word_vectors))

    analogies, scores = [], []
    with alive_bar(len(present), title="Analogies") as bar:
        for word in present:
            answer, score = word_vectors.most_similar(
                positive=["she", word], negative=["he"], topn=1)[0]
            analogies.append(answer)
            scores.append(float(score))
            bar()
    table["She_Analogy"] = analogies
    table["She_Analogy_Score"] = scores
    return table


def occupation_lean(df, sims, stop_words, comparisons=COMPARISONS):
    """
    Score each occupation by the average lean of the words in its title, for
    every population, next to that population's real share from BLS.
    """
    lookup = sims.set_index("Job_Words")
    lean_cols = [c.lean_column for c in comparisons]
    records = []
    for _, row in df.iterrows():
        words = [w for w in occupation_words(row["Occupations"], stop_words)
                 if w in lookup.index]
        if not words:
            continue
        record = {"Occupations": row["Occupations"],
                  "Total Employed": row["Total Employed"]}
        for comp in comparisons:
            record[comp.bls_column] = row[comp.bls_column]
        record.update(lookup.loc[words, lean_cols].mean().to_dict())
        record["Words_Used"] = " ".join(words)
        records.append(record)
    return pd.DataFrame(records)


def correlation_table(occ, comparisons=COMPARISONS):
    """Pearson and Spearman correlation of BLS share vs. embedding lean."""
    rows = []
    for comp in comparisons:
        sub = occ[[comp.bls_column, comp.lean_column]].dropna()
        rows.append({
            "Population": comp.key,
            "BLS column": comp.bls_column,
            "Word groups": comp.method,
            "Occupations": len(sub),
            "Pearson r": sub[comp.bls_column].corr(sub[comp.lean_column]),
            "Spearman rho": sub[comp.bls_column].corr(sub[comp.lean_column],
                                                      method="spearman"),
        })
    return pd.DataFrame(rows)


################################################################################
# 4. Static figures (PNG; opened in windows with --show)
################################################################################
def _save(fig, outdir, name):
    path = os.path.join(outdir, name)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    print(f"  saved {path}")


def _label_points(ax, data, x, y, max_labels):
    """Label the points with the strongest gender lean (all if few enough)."""
    picked = data.reindex(data["Abs_Difference"].sort_values(ascending=False).index)
    for _, r in picked.head(max_labels).iterrows():
        ax.text(r[x] + 0.005, r[y], r["Job_Words"], fontsize=7,
                ha="left", va="center", color="black")


def make_plots(df, sims, occ, outdir, comparisons=COMPARISONS, max_labels=60,
               show=False):
    """Create and save every static figure into outdir."""
    import matplotlib.pyplot as plt
    import seaborn as sns
    from wordcloud import WordCloud

    os.makedirs(outdir, exist_ok=True)
    print("Saving figures:")

    # 1. Word cloud of occupation titles
    text = " ".join(df["Occupations"])
    cloud = WordCloud(background_color="white", width=1200, height=800).generate(text)
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.imshow(cloud, interpolation="bilinear")
    ax.axis("off")
    ax.set_title("Words in BLS Occupation Titles")
    _save(fig, outdir, "Occupation Word Cloud.png")

    # 2. Percent women vs. men for the most female- and male-dominated jobs
    ranked = df.dropna(subset=["Women"]).sort_values("Women")
    extremes = pd.concat([ranked.head(20), ranked.tail(20)])
    extremes = extremes[~extremes.index.duplicated()]   # small tables overlap
    fig, ax = plt.subplots(figsize=(10, 12))
    ypos = np.arange(len(extremes))
    ax.barh(ypos, extremes["Women"], color="tab:blue", label="Women %")
    ax.barh(ypos, extremes["Men"], left=extremes["Women"],
            color="tab:orange", label="Men %")
    ax.set_yticks(ypos)
    ax.set_yticklabels(extremes["Occupations"], fontsize=7)
    ax.axvline(50, color="black", linewidth=0.8, linestyle="--")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Percent of workers")
    ax.set_title("Percent of Men & Women in Occupations\n"
                 "(20 most male- and 20 most female-dominated)")
    ax.legend(loc="lower right")
    _save(fig, outdir, "Percent of Men & Women in Occupations.png")

    # 3-4. Joint histograms of gender similarity vs. difference
    for column, color, title, fname in [
        ("Man_Similarity_of_Job", "orange", "Man Word Similarity & Difference",
         "Histogram of Diff Man Similarity.png"),
        ("Woman_Similarity_of_Job", "blue", "Woman Word Similarity & Difference",
         "Histogram of Diff Woman Similarity.png"),
    ]:
        grid = sns.jointplot(data=sims, x="Difference", y=column,
                             kind="hist", color=color)
        grid.fig.suptitle(title, y=1.02)
        _save(grid.fig, outdir, fname)

    # 5-6. Labeled scatter plots of gender similarity vs. difference
    for column, color, who in [("Man_Similarity_of_Job", "orange", "Man"),
                               ("Woman_Similarity_of_Job", "blue", "Woman")]:
        fig, ax = plt.subplots(figsize=(10, 10))
        sns.scatterplot(data=sims, x="Difference", y=column, color=color,
                        s=25, ax=ax)
        _label_points(ax, sims, "Difference", column, max_labels)
        ax.axvline(0, color="grey", linewidth=0.8, linestyle="--")
        ax.set_title(f"Occupation Words vs. {who} Word Similarity")
        ax.set_xlabel("Difference: sim('she', word) - sim('he', word)")
        ax.set_ylabel(f"{who} Similarity and Job")
        _save(fig, outdir, f"Occupation Labor Statistics vs. {who} Word Similarity.png")

    # 7. Woman similarity vs. man similarity
    fig, ax = plt.subplots(figsize=(14, 10))
    sns.scatterplot(data=sims, x="Man_Similarity_of_Job",
                    y="Woman_Similarity_of_Job", hue="Difference",
                    palette="coolwarm_r", s=25, ax=ax, legend=False)
    _label_points(ax, sims, "Man_Similarity_of_Job",
                  "Woman_Similarity_of_Job", max_labels)
    low = min(sims["Man_Similarity_of_Job"].min(), sims["Woman_Similarity_of_Job"].min())
    high = max(sims["Man_Similarity_of_Job"].max(), sims["Woman_Similarity_of_Job"].max())
    ax.plot([low, high], [low, high], color="grey", linestyle="--", linewidth=0.8,
            label="equal similarity")
    ax.legend()
    ax.set_title("Woman Similarity vs. Man Similarity")
    ax.set_xlabel("Man_Similarity_of_Job")
    ax.set_ylabel("Woman_Similarity_of_Job")
    _save(fig, outdir, "Woman Similarity vs. Man Similarity.png")

    # 8. Every population: BLS share vs. embedding lean, one panel each
    fig, axes = plt.subplots(1, len(comparisons), figsize=(5 * len(comparisons), 5),
                             squeeze=False)
    for ax, comp in zip(axes[0], comparisons):
        sub = occ[[comp.bls_column, comp.lean_column]].dropna()
        if len(sub) >= 3:
            sns.regplot(data=sub, x=comp.bls_column, y=comp.lean_column, ax=ax,
                        color=comp.color, scatter_kws={"s": 10, "alpha": 0.5})
            r = sub[comp.bls_column].corr(sub[comp.lean_column])
            ax.set_title(f"{comp.key}: r = {r:.2f} (n = {len(sub)})")
        ax.axhline(0, color="grey", linewidth=0.8, linestyle="--")
        ax.set_xlabel(f"% {comp.key} in occupation (BLS)")
        ax.set_ylabel(f"Lean toward {comp.key} vs. {comp.baseline_name}")
    fig.suptitle("Share of Each Population in an Occupation vs. "
                 "Word-Embedding Lean of the Occupation's Title", y=1.03)
    fig.tight_layout()
    _save(fig, outdir, "Population Share vs. Embedding Lean.png")

    if show:
        plt.show()
    plt.close("all")


################################################################################
# 5. Interactive dashboard (HTML, Plotly)
################################################################################
def _population_buttons(buttons, y):
    """A row of population buttons placed above the chart title."""
    return dict(type="buttons", direction="right", buttons=buttons, active=0,
                x=0, xanchor="left", y=y, yanchor="top", showactive=True,
                pad=dict(r=4, t=0))


def _group_scatter(occ, comparisons):
    """Occupation scatter with a dropdown to switch population."""
    import plotly.graph_objects as go

    fig = go.Figure()
    buttons = []
    n = len(comparisons)
    for i, comp in enumerate(comparisons):
        sub = occ.dropna(subset=[comp.bls_column, comp.lean_column])
        x, y = sub[comp.bls_column].to_numpy(), sub[comp.lean_column].to_numpy()
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="markers", name=comp.key, visible=(i == 0),
            marker=dict(color=comp.color, opacity=0.65,
                        size=np.clip(np.sqrt(sub["Total Employed"]) / 4, 5, 22)),
            customdata=np.stack([sub["Occupations"], sub["Words_Used"],
                                 sub["Total Employed"]], axis=-1),
            hovertemplate=("<b>%{customdata[0]}</b><br>"
                           f"% {comp.key}: " "%{x:.1f}%<br>"
                           "Lean: %{y:.3f}<br>"
                           "Employed: %{customdata[2]:,.0f} thousand<br>"
                           "Words: %{customdata[1]}<extra></extra>"),
        ))
        if len(sub) >= 3:
            slope, intercept = np.polyfit(x, y, 1)
            xs = np.array([x.min(), x.max()])
            r = np.corrcoef(x, y)[0, 1]
        else:
            xs, slope, intercept, r = np.array([0, 100]), 0.0, 0.0, float("nan")
        fig.add_trace(go.Scatter(
            x=xs, y=slope * xs + intercept, mode="lines", visible=(i == 0),
            name=f"trend (r = {r:.2f})", line=dict(color=comp.color, width=3),
            hoverinfo="skip"))
        visible = [False] * (2 * n)
        visible[2 * i] = visible[2 * i + 1] = True
        buttons.append(dict(
            label=comp.key, method="update",
            args=[{"visible": visible},
                  {"title.text": f"% {comp.key} in occupation vs. lean toward "
                                 f"{comp.key} (r = {r:.2f}, n = {len(sub)})",
                   "xaxis.title.text": f"% of workers who are {comp.key} (BLS)",
                   "yaxis.title.text": f"Lean toward {comp.key} vs. "
                                       f"{comp.baseline_name} ({comp.method})"}]))
    first = comparisons[0]
    fig.update_layout(
        updatemenus=[_population_buttons(buttons, y=1.35)],
        title=dict(text=buttons[0]["args"][1]["title.text"], y=0.86),
        xaxis_title=buttons[0]["args"][1]["xaxis.title.text"],
        yaxis_title=f"Lean toward {first.key} vs. {first.baseline_name}",
        height=620, template="plotly_white", margin=dict(t=150),
        legend=dict(orientation="h", y=-0.15))
    fig.add_hline(y=0, line_dash="dash", line_color="grey")
    return fig


def _word_leans(sims, comparisons, top=15):
    """Bar chart of the words leaning most toward / away from each group."""
    import plotly.graph_objects as go

    fig = go.Figure()
    buttons = []
    n = len(comparisons)
    for i, comp in enumerate(comparisons):
        ranked = sims.sort_values(comp.lean_column)
        picked = pd.concat([ranked.head(top), ranked.tail(top)])
        fig.add_trace(go.Bar(
            x=picked[comp.lean_column], y=picked["Job_Words"], orientation="h",
            visible=(i == 0), name=comp.key,
            marker_color=np.where(picked[comp.lean_column] > 0, comp.color, "#999999"),
            hovertemplate="<b>%{y}</b><br>Lean: %{x:.3f}<extra></extra>"))
        visible = [False] * n
        visible[i] = True
        buttons.append(dict(label=comp.key, method="update", args=[
            {"visible": visible},
            {"title.text": f"Occupation words leaning most toward {comp.key} "
                           f"(colored) and toward {comp.baseline_name} (grey)"}]))
    fig.update_layout(
        updatemenus=[_population_buttons(buttons, y=1.21)],
        title=dict(text=buttons[0]["args"][1]["title.text"], y=0.9), height=820,
        template="plotly_white", showlegend=False, margin=dict(t=150),
        xaxis_title="Lean (cosine to group minus cosine to comparison group)")
    return fig


def _gender_words(sims):
    """Every occupation word: similarity to 'she' vs. 'he', hover for details."""
    import plotly.graph_objects as go

    low = float(min(sims["Man_Similarity_of_Job"].min(),
                    sims["Woman_Similarity_of_Job"].min()))
    high = float(max(sims["Man_Similarity_of_Job"].max(),
                     sims["Woman_Similarity_of_Job"].max()))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sims["Man_Similarity_of_Job"], y=sims["Woman_Similarity_of_Job"],
        mode="markers", name="occupation words",
        marker=dict(color=sims["Difference"], colorscale="RdBu", cmid=0,
                    colorbar=dict(title="she − he"), size=8, opacity=0.8),
        customdata=np.stack([sims["Job_Words"], sims["Difference"],
                             sims["She_Analogy"]], axis=-1),
        hovertemplate=("<b>%{customdata[0]}</b><br>sim('she'): %{y:.3f}<br>"
                       "sim('he'): %{x:.3f}<br>she − he: %{customdata[1]:.3f}<br>"
                       "he : %{customdata[0]} :: she : %{customdata[2]}"
                       "<extra></extra>")))
    fig.add_trace(go.Scatter(x=[low, high], y=[low, high], mode="lines",
                             name="equal similarity",
                             line=dict(color="grey", dash="dash"), hoverinfo="skip"))
    fig.update_layout(
        title="Every occupation word: similarity to 'she' vs. 'he' "
              "(zoom in and hover to read words)",
        xaxis_title="Similarity to 'he'", yaxis_title="Similarity to 'she'",
        height=700, template="plotly_white", legend=dict(orientation="h", y=-0.12))
    return fig


def _gender_spectrum(df):
    """All occupations sorted by percent women, stacked women/men."""
    import plotly.graph_objects as go

    ranked = df.dropna(subset=["Women"]).sort_values("Women")
    fig = go.Figure()
    for col, color in [("Women", "#1f77b4"), ("Men", "#ff7f0e")]:
        fig.add_trace(go.Bar(
            x=ranked["Occupations"], y=ranked[col], name=f"{col} %",
            marker_color=color,
            customdata=ranked["Total Employed"],
            hovertemplate=("<b>%{x}</b><br>" f"{col}: " "%{y:.1f}%<br>"
                           "Employed: %{customdata:,.0f} thousand<extra></extra>")))
    fig.update_layout(
        barmode="stack", bargap=0, height=520, template="plotly_white",
        title=f"All {len(ranked)} occupations with published data, "
              "sorted by percent women (hover for names)",
        yaxis_title="Percent of workers", xaxis=dict(showticklabels=False,
                                                    title="Occupations"),
        legend=dict(orientation="h", y=1.08))
    fig.add_hline(y=50, line_dash="dash", line_color="black")
    return fig


def make_dashboard(df, sims, occ, corr, outdir, comparisons=COMPARISONS):
    """Write output/dashboard.html: one self-contained interactive page."""
    figures = [
        ("Population share vs. word-embedding lean",
         "Each dot is an occupation. The x-axis is the real share of workers "
         "from BLS; the y-axis is how strongly the words in its title lean "
         "toward that population in word2vec. Dot size is the number "
         "employed. Use the menu to switch population.",
         _group_scatter(occ, comparisons)),
        ("Which occupation words lean the most?",
         "The 15 words leaning most toward each group and the 15 leaning most "
         "toward its comparison group.",
         _word_leans(sims, comparisons)),
        ("Gender: every occupation word",
         "Words above the dashed line are closer to 'she' than to 'he'. Drag "
         "to zoom; double-click to reset.",
         _gender_words(sims)),
        ("Gender: the real workforce",
         "Every occupation BLS publishes, from most male to most female.",
         _gender_spectrum(df)),
    ]
    table = corr.copy()
    for col in ["Pearson r", "Spearman rho"]:
        table[col] = table[col].map(lambda v: f"{v:.2f}")
    sections = []
    for i, (title, blurb, fig) in enumerate(figures):
        html = fig.to_html(full_html=False, include_plotlyjs="cdn" if i == 0 else False,
                           config={"responsive": True, "displaylogo": False})
        sections.append(f"<section><h2>{title}</h2><p>{blurb}</p>{html}</section>")
    groups = "".join(
        f"<li><b>{c.key}</b>: {c.method}. "
        f"Words: {', '.join(c.found)}. Compared with: {', '.join(c.baseline_found)}.</li>"
        for c in comparisons)
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Occupation Bias Dashboard</title>
<style>
 body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 0 auto;
        max-width: 1200px; padding: 16px; color: #222; background: #fff; }}
 h1 {{ margin-bottom: 4px; }} h2 {{ margin-top: 40px; }}
 p, li {{ line-height: 1.5; }} .note {{ color: #555; }}
 table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
 th, td {{ border-bottom: 1px solid #ddd; padding: 6px 8px; text-align: left; }}
 th {{ background: #f5f5f5; }}
</style></head><body>
<h1>Occupations vs. word-embedding bias</h1>
<p class="note">BLS Current Population Survey table 11 ({len(df)} occupations)
compared with the Google News word2vec embedding. Generated by bias2.py.</p>
<h2>Summary: does the embedding mirror the real workforce?</h2>
<p>Correlation between each population's real share in an occupation and how
strongly the occupation's title words lean toward that population. Positive
values mean the embedding associates the occupation with the groups that
actually hold those jobs.</p>
{table.to_html(index=False, border=0)}
{''.join(sections)}
<h2>Word groups used</h2><ul>{groups}</ul>
<h2>Limitations</h2><ul>
<li>Lean scores come from news text (Google News, about 2013) and measure how
words were used there, not anything about the people in these jobs.</li>
<li>Names carry other associations in news (countries, celebrities,
politics), so race/ethnicity measures are noisier than the gender measure.</li>
<li>Hispanic or Latino is an ethnicity in BLS data and overlaps the race
columns; the race columns are percent of all workers in the occupation.</li>
<li>An occupation's score is the average of its title words, and BLS does not
publish percentages for small occupations, which are left out.</li>
</ul></body></html>"""
    path = os.path.join(outdir, "dashboard.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"  saved {path}")
    return path


################################################################################
# 6. Main
################################################################################
def run(df, word_vectors, subset="all", outdir="output", max_labels=60,
        show=False, open_dashboard=False, comparisons=COMPARISONS):
    """Run the analysis on an already-loaded table and embedding."""
    stop_words = get_stop_words()
    chosen = select_subset(df, subset)
    words = build_vocabulary(chosen["Occupations"], stop_words)
    print(f"Occupations analyzed ({subset}): {len(chosen)} | unique words: {len(words)}")
    print("Word groups:")
    prepare_comparisons(word_vectors, comparisons)

    sims = similarity_table(words, word_vectors, comparisons)
    occ = occupation_lean(chosen, sims, stop_words, comparisons)
    corr = correlation_table(occ, comparisons)

    os.makedirs(outdir, exist_ok=True)
    sims.sort_values("Difference").to_csv(
        os.path.join(outdir, "word_similarities.csv"), index=False)
    occ.to_csv(os.path.join(outdir, "occupation_lean.csv"), index=False)
    corr.to_csv(os.path.join(outdir, "correlations.csv"), index=False)
    print("***" * 20)
    print("BLS share vs. embedding lean:")
    print(corr[["Population", "Occupations", "Pearson r", "Spearman rho"]]
          .to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print("***" * 20)

    make_plots(chosen, sims, occ, outdir, comparisons, max_labels, show)
    dashboard = make_dashboard(chosen, sims, occ, corr, outdir, comparisons)
    if open_dashboard:
        webbrowser.open("file://" + os.path.abspath(dashboard))
    return sims, occ, corr


def parse_args():
    p = argparse.ArgumentParser(description=__doc__.split("Usage:")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default=BLS_URL, help="BLS table URL")
    p.add_argument("--html", default=HTML_FILE, help="local copy of the BLS page")
    p.add_argument("--contact", default=None,
                   help="your email, sent to BLS so automated downloads are allowed "
                        "(or set BLS_CONTACT)")
    p.add_argument("--refresh", action="store_true",
                   help="download the BLS page again even if a saved copy exists")
    p.add_argument("--subset", choices=["all", "first80", "last20"], default="all",
                   help="which occupation rows to analyze (bias.py used last20)")
    p.add_argument("--model", default=DEFAULT_MODEL, help="gensim-data model name")
    p.add_argument("--output-dir", default="output", help="folder for figures/CSVs")
    p.add_argument("--max-labels", type=int, default=60,
                   help="max word labels per static scatter plot")
    p.add_argument("--show", action="store_true",
                   help="open matplotlib windows (zoom/pan) at the end")
    p.add_argument("--open", action="store_true", dest="open_dashboard",
                   help="open the interactive dashboard in your browser")
    return p.parse_args()


def main():
    args = parse_args()
    if not args.show:
        matplotlib.use("Agg")   # save files only; no windows that block the script
    df = get_dataframe(args.url, args.html, contact=args.contact, refresh=args.refresh)
    word_vectors = load_word_vectors(args.model)
    run(df, word_vectors, args.subset, args.output_dir, args.max_labels,
        args.show, args.open_dashboard)


if __name__ == "__main__":
    main()
