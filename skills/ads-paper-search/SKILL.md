---
name: ads-paper-search
description: Use when looking up astronomy or physics papers by bibcode, arXiv ID, DOI, title, author, abstract, citation metadata, or when repairing BibTeX/reference entries with ADS/SciX or arXiv records.
---

# ADS Paper Search

Use ADS/SciX first when you need authoritative paper metadata such as bibcode, DOI, journal, volume, and page. Use arXiv when you need public search without a token or want preprint metadata.

## Data sources

- ADS/SciX API endpoint: `https://api.adsabs.harvard.edu/v1/search/query`
- arXiv public API endpoint: `https://export.arxiv.org/api/query`

## Authentication

- ADS requires the environment variable `ADS_API_TOKEN`
- arXiv public search does not require a token
- If ADS token is missing, do not guess metadata; fall back to arXiv only when arXiv is suitable

## Good use cases

- Find paper metadata from a bibcode such as `2020PhRvD.101h3520Y`
- Resolve title, author list, DOI, abstract, journal, volume, page
- Search preprints by arXiv query or arXiv ID
- Generate or fix BibTeX entries in `ref.bib`
- Check whether two bib entries are duplicates

## Minimal ADS query pattern

```bash
curl -sS -H "Authorization: Bearer $ADS_API_TOKEN" \
  "https://api.adsabs.harvard.edu/v1/search/query?q=bibcode:2020PhRvD.101h3520Y&fl=title,author,year,bibcode,doi,abstract,pub,volume,page"
```

## Minimal arXiv query patterns

Search by keywords:

```bash
curl -sS "https://export.arxiv.org/api/query?search_query=all:21cm&start=0&max_results=5"
```

Search by arXiv ID:

```bash
curl -sS "https://export.arxiv.org/api/query?id_list=1911.07442"
```

## Recommended ADS fields

Use `fl=` with these fields when repairing references:

- `title`
- `author`
- `year`
- `bibcode`
- `doi`
- `abstract`
- `pub`
- `volume`
- `page`

## Workflow

1. Query ADS by bibcode when available.
2. If no bibcode, query ADS by DOI or exact title.
3. If ADS token is unavailable or the paper is only a preprint, use arXiv.
4. Read the response carefully and do not invent missing fields.
5. When creating BibTeX, keep the citation key already used by the project unless the user asks to rename it.
6. If replacing a duplicate or wrong entry, explain which old entry was wrong and which API record replaces it.

## Notes

- Prefer ADS for published-paper metadata.
- Prefer arXiv for public searching and preprints.
- arXiv returns Atom XML, not JSON; parse carefully.

## Example task

For a broken `yoshiura2020b` entry, query ADS by the target bibcode, then rewrite only that BibTeX block with the returned metadata. If a user instead gives an arXiv ID, query arXiv first and only add journal metadata if ADS is also available.
