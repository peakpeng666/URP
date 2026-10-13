from scholarly import scholarly

def fetch_scholar_papers_bib(query, max_results, output_file):
    """
    Fetches Google Scholar papers based on the query and saves them as a BibTeX file.

    Args:
        query (str): The search query string.
        max_results (int): Maximum number of results to fetch.
        output_file (str): File name to save the results in BibTeX format.
    """
    try:
        search_results = scholarly.search_pubs(query)
        results = []

        with open(output_file, "w", encoding="utf-8") as bib_file:
            for i, result in enumerate(search_results):
                if i >= max_results:
                    break

                # Extract BibTeX details
                bib = result.get("bib", {})
                title = bib.get("title", "Unknown Title")
                author = " and ".join(bib.get("author", []))
                year = bib.get("pub_year", "Unknown Year")
                venue = bib.get("venue", "Unknown Venue")
                url = result.get("pub_url", None)
                key = f"{author.split()[0]}_{year}" if author else f"key_{i}"

                # Format BibTeX entry
                bib_entry = f"""
@article{{{key},
  title = {{{title}}},
  author = {{{author}}},
  year = {{{year}}},
  journal = {{{venue}}},
  url = {{{url}}}
}}
"""
                # Write to file
                bib_file.write(bib_entry)
                print(f"Saved entry {i + 1}")

        print(f"Saved all results to {output_file}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    query = "heuristic pre-marshalling problem"
    max_results = 20
    output_file = "../../../../data/ideas/lit_review_scholar_results_premarshalling.bib"
    fetch_scholar_papers_bib(query, max_results, output_file)
