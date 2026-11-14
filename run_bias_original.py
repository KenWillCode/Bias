"""
Runs the ORIGINAL, unmodified bias.py with two workarounds applied from the
outside (bias.py itself is never edited):

1. BLS now answers scripted downloads with "403 Forbidden". The original code
   would save that error page as occupations.html and then fail to parse it.
   This runner refuses to start until a real copy of the page has been saved
   next to bias.py as occupations.html (see the message printed below).

2. bias.py calls sns.scatterplot(..., color=['red', 'orange']). Matplotlib
   rejects a list of two colors for a single scatter series, so the script
   crashes on its first scatter plot. This runner wraps seaborn.scatterplot so
   a list/tuple of colors is replaced by its first color.

Usage (from the project root):
    .venv/bin/python Bias-main/run_bias_original.py
    .venv/bin/python Bias-main/run_bias_original.py --contact you@example.com
        (downloads occupations.html first if it is missing; see fetch_bls.py)
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(HERE, "occupations.html")
BLS_URL = "https://www.bls.gov/cps/cpsaat11.htm"


def check_html():
    """
    Make sure a real copy of the BLS page exists (not a 403 error page).
    If it is missing and a contact email is available (--contact EMAIL or the
    BLS_CONTACT variable), download it the way BLS allows (see fetch_bls.py).
    """
    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "rb") as f:
            content = f.read()
        if b'class="regular"' in content:
            return
        print(f"{HTML_FILE} exists but does not contain the BLS data table "
              "(it is probably a saved '403 Forbidden' page).\n")
    contact = os.environ.get("BLS_CONTACT")
    if "--contact" in sys.argv:
        i = sys.argv.index("--contact")
        contact = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
    if contact:
        sys.path.insert(0, HERE)
        from bias2 import download_bls_page
        download_bls_page(BLS_URL, HTML_FILE, contact)
        return
    print("BLS only allows automated downloads that include a contact email.")
    print("Run again with:  --contact you@example.com   (or set BLS_CONTACT)\n")
    print("Or save the page once from your browser:")
    print(f"  1. Open {BLS_URL}")
    print("  2. Save it as HTML (Chrome: File > Save Page As > 'Webpage, HTML Only';")
    print("     Safari: File > Save As > Format 'Page Source')")
    print(f"  3. Save it as: {HTML_FILE}")
    sys.exit(1)


def patch_seaborn():
    """Accept a list of colors in sns.scatterplot by using the first one."""
    import seaborn as sns

    original_scatterplot = sns.scatterplot

    def scatterplot(*args, color=None, **kwargs):
        if isinstance(color, (list, tuple)):
            color = color[0] if color else None
        return original_scatterplot(*args, color=color, **kwargs)

    sns.scatterplot = scatterplot


def main():
    check_html()
    patch_seaborn()
    os.chdir(HERE)            # bias.py reads/writes files relative to its folder
    sys.path.insert(0, HERE)
    sys.argv = [os.path.join(HERE, "bias.py")]
    runpy.run_path(os.path.join(HERE, "bias.py"), run_name="__main__")


if __name__ == "__main__":
    main()
