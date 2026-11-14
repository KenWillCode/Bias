"""
Download https://www.bls.gov/cps/cpsaat11.htm and save it as occupations.html
next to this file -- the step that used to be done by hand in a browser.

BLS blocks automated downloads that do not say who is making them
(https://www.bls.gov/bls/pss.htm), so pass a contact email:

    python fetch_bls.py --contact you@example.com
    BLS_CONTACT=you@example.com python fetch_bls.py

Both bias.py (through run_bias_original.py) and bias2.py read the saved file.
"""
import argparse
import os

from bias2 import BLS_URL, download_bls_page

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--contact", help="your email (or set BLS_CONTACT)")
    p.add_argument("--url", default=BLS_URL)
    p.add_argument("--out", default=os.path.join(HERE, "occupations.html"))
    p.add_argument("--force", action="store_true",
                   help="overwrite an existing occupations.html")
    args = p.parse_args()

    if os.path.exists(args.out) and not args.force:
        print(f"{args.out} already exists; use --force to download it again.")
        return
    download_bls_page(args.url, args.out, args.contact)


if __name__ == "__main__":
    main()
