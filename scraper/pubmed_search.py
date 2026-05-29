#!/usr/bin/env python3
"""
PubMed search script for NYC DOHMH publications
Searches for publications from the last 30 days and exports to CSV
"""

import os
import csv
from datetime import datetime, timedelta
from Bio import Entrez
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
PUBMED_RESULTS_PATH = os.path.join(REPO_ROOT, "pubmed_results.csv")
PEER_CSV_PATH = os.path.join(REPO_ROOT, "peer.csv")
README_PATH = os.path.join(REPO_ROOT, "README.md")

# Set your email for NCBI (required by Entrez)
Entrez.email = "mmontesano@health.nyc.gov"  # Change this to your email

def search_pubmed(query, start_date_str="2026/01/01"):
    """
    Search PubMed with the given query for articles published from start_date to now
    """
    # Calculate date range
    end_date = datetime.now()
    end_date_str = end_date.strftime("%Y/%m/%d")
    
    # Add date filter to query
    date_query = f"{query} AND {start_date_str}:{end_date_str}[Date - Publication]"
    
    print(f"Searching PubMed for articles from {start_date_str} to {end_date_str}")
    print(f"Query: {date_query}\n")
    
    # Search PubMed
    try:
        handle = Entrez.esearch(db="pubmed", term=date_query, retmax=1000)
        record = Entrez.read(handle)
        handle.close()
        
        id_list = record["IdList"]
        print(f"Found {len(id_list)} articles\n")
        
        return id_list
    except Exception as e:
        print(f"Error searching PubMed: {e}")
        return []

def fetch_details(id_list):
    """
    Fetch detailed information for a list of PubMed IDs
    """
    if not id_list:
        return []
    
    articles = []
    
    # Fetch in batches to avoid overwhelming the API
    batch_size = 100
    for i in range(0, len(id_list), batch_size):
        batch = id_list[i:i+batch_size]
        ids = ",".join(batch)
        
        try:
            handle = Entrez.efetch(db="pubmed", id=ids, rettype="medline", retmode="xml")
            records = Entrez.read(handle)
            handle.close()
            
            for record in records['PubmedArticle']:
                article = extract_article_info(record)
                if article:
                    articles.append(article)
            
            # Be nice to NCBI servers
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Error fetching details for batch: {e}")
            continue
    
    return articles

def extract_article_info(record):
    """
    Extract relevant information from a PubMed record
    """
    try:
        medline = record['MedlineCitation']
        article = medline['Article']
        
        # Extract PMID
        pmid = str(medline['PMID'])
        
        # Extract title
        title = article.get('ArticleTitle', 'N/A')
        
        # Extract authors
        author_list = article.get('AuthorList', [])
        authors = []
        for author in author_list:
            if 'LastName' in author and 'Initials' in author:
                authors.append(f"{author['LastName']} {author['Initials']}")
            elif 'CollectiveName' in author:
                authors.append(author['CollectiveName'])
        authors_str = "; ".join(authors) if authors else "N/A"
        
        # Extract journal
        journal = article.get('Journal', {})
        journal_title = journal.get('Title', 'N/A')
        
        # Extract publication date
        pub_date = article.get('Journal', {}).get('JournalIssue', {}).get('PubDate', {})
        year = pub_date.get('Year', '')
        month = pub_date.get('Month', '01')
        day = pub_date.get('Day', '01')
        
        # Convert month name to number if needed
        month_map = {
            'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
            'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
            'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
        }
        if month in month_map:
            month = month_map[month]
        
        # Format date
        try:
            date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        except:
            date_str = year if year else "N/A"
        
        # Extract DOI
        doi = "N/A"
        id_list = article.get('ELocationID', [])
        for eid in id_list:
            if eid.attributes.get('EIdType') == 'doi':
                doi = str(eid)
                break
        
        # If DOI not found in ELocationID, check ArticleIdList
        if doi == "N/A" and 'PubmedData' in record:
            article_ids = record['PubmedData'].get('ArticleIdList', [])
            for aid in article_ids:
                if aid.attributes.get('IdType') == 'doi':
                    doi = str(aid)
                    break
        
        # Extract keywords
        keywords = []
        keyword_list = medline.get('KeywordList', [])
        for kw_group in keyword_list:
            for kw in kw_group:
                keywords.append(str(kw))
        keywords_str = "; ".join(keywords) if keywords else "N/A"
        
        # Create PubMed link
        link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        
        return {
            'PMID': pmid,
            'Title': title,
            'Authors': authors_str,
            'Year': year,
            'Date': date_str,
            'Link': link,
            'Journal': journal_title,
            'DOI': doi,
            'Keywords': keywords_str
        }
        
    except Exception as e:
        print(f"Error extracting article info: {e}")
        return None

def create_csv(articles, filename=PUBMED_RESULTS_PATH):
    """
    Create or update a CSV file with the article data, avoiding duplicates.
    """
    # Define headers
    headers = ['PMID', 'Title', 'Authors', 'Year', 'Date', 'Link', 'Journal', 'DOI', 'Keywords']
    
    # Read existing articles if file exists
    existing_pmids = set()
    existing_articles = []
    if os.path.exists(filename):
        try:
            with open(filename, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    existing_articles.append(row)
                    existing_pmids.add(row.get('PMID', ''))
        except Exception as e:
            print(f"Warning: Could not read existing CSV: {e}")
    
    # Filter new articles (not already in existing)
    new_articles = [article for article in articles if article['PMID'] not in existing_pmids]
    
    if not new_articles:
        print(f"\nNo new articles found. CSV file unchanged: {filename}")
        print(f"Total articles: {len(existing_articles)}")
        return
    
    # Combine existing and new articles
    all_articles = existing_articles + new_articles
    
    # Sort by date (most recent first)
    all_articles.sort(key=lambda x: x.get('Date', ''), reverse=True)
    
    # Write to CSV
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for article in all_articles:
            writer.writerow(article)
    
    print(f"\nCSV file updated: {filename}")
    print(f"Added {len(new_articles)} new articles")
    print(f"Total articles: {len(all_articles)}")


def merge_into_peer_csv(pubmed_filename=PUBMED_RESULTS_PATH, peer_filename=PEER_CSV_PATH):
    """
    Append the contents of pubmed_results.csv to peer.csv and deduplicate on PMID.
    """
    if not os.path.exists(pubmed_filename):
        print(f"PubMed results file not found: {pubmed_filename}")
        return

    repair_peer_csv(peer_filename)

    peer_rows = []
    peer_fieldnames = []
    peer_pmids = set()

    if os.path.exists(peer_filename):
        with open(peer_filename, 'r', newline='', encoding='utf-8') as peerfile:
            reader = csv.DictReader(peerfile)
            if reader.fieldnames:
                for field in reader.fieldnames:
                    if field not in peer_fieldnames:
                        peer_fieldnames.append(field)
            for row in reader:
                normalized = {k: v for k, v in row.items() if k}
                pmid = normalized.get('PMID', '').strip()
                if not pmid:
                    continue
                peer_rows.append(normalized)
                peer_pmids.add(pmid)

    pub_fieldnames = []
    with open(pubmed_filename, 'r', newline='', encoding='utf-8') as pubfile:
        reader = csv.DictReader(pubfile)
        if reader.fieldnames:
            for field in reader.fieldnames:
                if field not in pub_fieldnames:
                    pub_fieldnames.append(field)
        pub_rows = [row for row in reader if row.get('PMID', '') and row['PMID'] not in peer_pmids]

    if not pub_rows:
        print(f"No new PubMed entries to add to {peer_filename}.")
        return

    if peer_fieldnames:
        combined_fieldnames = peer_fieldnames[:]
        for field in pub_fieldnames:
            if field not in combined_fieldnames:
                combined_fieldnames.append(field)
    else:
        combined_fieldnames = pub_fieldnames

    with open(peer_filename, 'w', newline='', encoding='utf-8') as peerfile:
        writer = csv.DictWriter(peerfile, fieldnames=combined_fieldnames)
        writer.writeheader()
        for row in peer_rows:
            writer.writerow({k: row.get(k, '') for k in combined_fieldnames})
        for row in pub_rows:
            writer.writerow({k: row.get(k, '') for k in combined_fieldnames})

    print(f"Added {len(pub_rows)} new entries to {peer_filename}.")
    print(f"Updated {peer_filename} total entries: {len(peer_rows) + len(pub_rows)}")


def repair_peer_csv(peer_filename):
    if not os.path.exists(peer_filename):
        return

    with open(peer_filename, 'r', newline='', encoding='utf-8') as peerfile:
        reader = csv.reader(peerfile)
        rows = list(reader)

    if not rows:
        return

    header = [field.replace('\ufeff', '') for field in rows[0]]
    seen = []
    for field in header:
        if field not in seen:
            seen.append(field)

    cleaned_rows = [seen]
    seen_pmids = set()
    for row in rows[1:]:
        if len(row) > len(seen):
            if not row[0].strip() and row[-1].strip():
                row = [row[-1]] + row[1:-1]
            else:
                row = row[:len(seen)]

        if len(row) < len(seen):
            row += [''] * (len(seen) - len(row))

        pmid = row[0].strip()
        if not pmid:
            continue
        if pmid in seen_pmids:
            continue

        seen_pmids.add(pmid)
        cleaned_rows.append(row)

    if len(cleaned_rows) == len(rows) and len(seen) == len(header):
        return

    with open(peer_filename, 'w', newline='', encoding='utf-8') as peerfile:
        writer = csv.writer(peerfile)
        writer.writerows(cleaned_rows)


def update_readme_timestamp(readme_filename=README_PATH):
    """
    Update the README last-updated line with the current date.
    """
    if not os.path.exists(readme_filename):
        print(f"README not found: {readme_filename}")
        return

    current_date = datetime.now().strftime("%Y-%m-%d")
    updated_line = f"- peer.csv (and its variants) is the result of a search of PubMed for manuscripts that include a listed affiliation to the NYC Health Department, dating back to 2010, through 2026. This was last updated {current_date}."

    with open(readme_filename, 'r', encoding='utf-8') as readme_file:
        lines = readme_file.readlines()

    line_updated = False
    for index, line in enumerate(lines):
        if line.strip().startswith("- peer.csv (and its variants) is the result of a search of PubMed"):
            lines[index] = updated_line + "\n"
            line_updated = True
            break
    if not line_updated:
        for index, line in enumerate(lines):
            if line.strip().startswith("This was last updated"):
                lines[index] = f"This was last updated {current_date}.\n"
                line_updated = True
                break

    if line_updated:
        with open(readme_filename, 'w', encoding='utf-8') as readme_file:
            readme_file.writelines(lines)
        print(f"Updated README last-updated date to {current_date}.")
    else:
        print("Last-updated line not found in README; no change made.")


def main():
    """
    Main execution function
    """
    # NYC DOHMH affiliation query
    query = """(((new york city department of health and mental hygiene[Affiliation]) OR 
    NYC department of health and mental hygiene[Affiliation]) OR 
    NYC DOHMH[Affiliation]) OR 
    NYCDOHMH[Affiliation]"""
    
    # Search PubMed
    id_list = search_pubmed(query)
    
    if not id_list:
        print("No articles found. Checking if CSV needs creation.")
        if not os.path.exists(PUBMED_RESULTS_PATH):
            # Create empty CSV with headers
            with open(PUBMED_RESULTS_PATH, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['PMID', 'Title', 'Authors', 'Year', 'Date', 'Link', 'Journal', 'DOI', 'Keywords'])
            print(f"Created empty CSV file: {PUBMED_RESULTS_PATH}")
        else:
            print("CSV file already exists, no changes made.")
        return
    
    # Fetch article details
    print("Fetching article details...")
    articles = fetch_details(id_list)
    
    # Create/update CSV file
    create_csv(articles, PUBMED_RESULTS_PATH)

    # Merge PubMed results into peer.csv, deduplicating on PMID
    merge_into_peer_csv(PUBMED_RESULTS_PATH, PEER_CSV_PATH)

    # Update README timestamp
    update_readme_timestamp(README_PATH)


if __name__ == "__main__":
    main()
