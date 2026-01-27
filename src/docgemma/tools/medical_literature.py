"""Medical literature search tool using PubMed E-utilities.

Searches the PubMed database for relevant medical articles and retrieves
abstracts. Uses a two-step process: search for IDs, then fetch summaries.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from .schemas import ArticleSummary, MedicalLiteratureInput, MedicalLiteratureOutput

# PubMed E-utilities endpoints
PUBMED_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Request timeout in seconds
REQUEST_TIMEOUT = 30.0


async def search_medical_literature(
    input_data: MedicalLiteratureInput,
) -> MedicalLiteratureOutput:
    """Search PubMed for medical literature and retrieve abstracts.

    Performs a two-step search:
    1. ESearch: Find article IDs matching the query
    2. EFetch: Retrieve article details and abstracts

    Args:
        input_data: Search query and max results configuration.

    Returns:
        MedicalLiteratureOutput containing article summaries with abstracts.
        Results are limited to save context tokens for the agent.

    Example:
        >>> result = await search_medical_literature(
        ...     MedicalLiteratureInput(query="diabetes treatment", max_results=3)
        ... )
        >>> for article in result.articles:
        ...     print(f"{article.title} - {article.journal}")
    """
    query = input_data.query.strip()
    max_results = input_data.max_results

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            # Step 1: Search for article IDs
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json",
                "sort": "relevance",
            }

            search_response = await client.get(PUBMED_ESEARCH_URL, params=search_params)
            search_response.raise_for_status()
            search_data = search_response.json()

            esearch_result = search_data.get("esearchresult", {})
            id_list = esearch_result.get("idlist", [])
            total_count = int(esearch_result.get("count", 0))

            if not id_list:
                return MedicalLiteratureOutput(
                    query=query,
                    total_found=total_count,
                    articles=[],
                    error=None,
                )

            # Step 2: Fetch article details
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(id_list),
                "rettype": "abstract",
                "retmode": "xml",
            }

            fetch_response = await client.get(PUBMED_EFETCH_URL, params=fetch_params)
            fetch_response.raise_for_status()

            # Parse XML response
            articles = _parse_pubmed_xml(fetch_response.text)

            return MedicalLiteratureOutput(
                query=query,
                total_found=total_count,
                articles=articles,
                error=None,
            )

    except httpx.TimeoutException:
        return MedicalLiteratureOutput(
            query=query,
            total_found=0,
            articles=[],
            error=f"Request timed out after {REQUEST_TIMEOUT} seconds",
        )
    except httpx.HTTPStatusError as e:
        return MedicalLiteratureOutput(
            query=query,
            total_found=0,
            articles=[],
            error=f"HTTP error {e.response.status_code}: {e.response.text[:200]}",
        )
    except ET.ParseError as e:
        return MedicalLiteratureOutput(
            query=query,
            total_found=0,
            articles=[],
            error=f"Failed to parse PubMed response: {e}",
        )
    except Exception as e:
        return MedicalLiteratureOutput(
            query=query,
            total_found=0,
            articles=[],
            error=f"Unexpected error: {type(e).__name__}: {e}",
        )


def _parse_pubmed_xml(xml_content: str) -> list[ArticleSummary]:
    """Parse PubMed XML response into ArticleSummary objects.

    Args:
        xml_content: Raw XML string from PubMed EFetch.

    Returns:
        List of parsed ArticleSummary objects.
    """
    articles = []
    root = ET.fromstring(xml_content)

    for article_elem in root.findall(".//PubmedArticle"):
        try:
            # Extract PMID
            pmid_elem = article_elem.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None else "Unknown"

            # Extract title
            title_elem = article_elem.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None else "No title"

            # Extract authors (abbreviated)
            authors = _extract_authors(article_elem)

            # Extract journal
            journal_elem = article_elem.find(".//Journal/Title")
            journal = journal_elem.text if journal_elem is not None else "Unknown journal"

            # Extract publication date
            pub_date = _extract_pub_date(article_elem)

            # Extract abstract
            abstract = _extract_abstract(article_elem)

            articles.append(
                ArticleSummary(
                    pmid=pmid,
                    title=title,
                    authors=authors,
                    journal=journal,
                    pub_date=pub_date,
                    abstract=abstract,
                )
            )
        except Exception:
            # Skip malformed articles
            continue

    return articles


def _extract_authors(article_elem: ET.Element) -> str:
    """Extract and format author list from article element."""
    author_list = article_elem.findall(".//Author")

    if not author_list:
        return "Unknown authors"

    authors = []
    for author in author_list[:3]:  # Limit to first 3 authors
        last_name = author.find("LastName")
        initials = author.find("Initials")

        if last_name is not None:
            name = last_name.text
            if initials is not None:
                name += f" {initials.text}"
            authors.append(name)

    result = ", ".join(authors)
    if len(author_list) > 3:
        result += " et al."

    return result


def _extract_pub_date(article_elem: ET.Element) -> str:
    """Extract publication date from article element."""
    pub_date_elem = article_elem.find(".//PubDate")

    if pub_date_elem is None:
        return "Unknown date"

    year = pub_date_elem.find("Year")
    month = pub_date_elem.find("Month")
    day = pub_date_elem.find("Day")

    parts = []
    if year is not None:
        parts.append(year.text)
    if month is not None:
        parts.append(month.text)
    if day is not None:
        parts.append(day.text)

    return " ".join(parts) if parts else "Unknown date"


def _extract_abstract(article_elem: ET.Element) -> str | None:
    """Extract abstract text from article element."""
    abstract_elem = article_elem.find(".//Abstract")

    if abstract_elem is None:
        return None

    # Abstract can have multiple AbstractText elements (structured abstract)
    abstract_texts = abstract_elem.findall("AbstractText")

    if not abstract_texts:
        return None

    parts = []
    for text_elem in abstract_texts:
        label = text_elem.get("Label")
        text = text_elem.text or ""

        if label:
            parts.append(f"{label}: {text}")
        else:
            parts.append(text)

    return " ".join(parts) if parts else None
